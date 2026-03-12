import csv
import io
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.core import Model, Series, Manufacturer, EquipmentType
from app.models.templates import ReverbTemplate, ReverbField, ReverbEquipmentTypeFieldOverride
from app.services.reverb_template_asset_store import ReverbTemplateAssetMissingError, materialize_reverb_template_asset
from app.services.reverb_template_io import load_reverb_runtime_template
from app.services.shared_template_tokens import (
    REVERB_LEGACY_PRICE_VARIANT_MAP,
    apply_base_sku_tokens,
    resolve_structured_tokens_in_value,
    resolve_price_placeholders_in_value as resolve_shared_price_placeholders_in_value,
    resolve_single_price_placeholder as resolve_shared_single_price_placeholder,
)

UNRESOLVED_BRACKET_TOKEN_PATTERN = re.compile(r"\[[^\[\]]+\]")
REVERB_INDEX_TOKENS = ("[t_index]", "[INDEX]")

def normalize_for_url(name: str) -> str:
    """Normalize a name for use in filenames."""
    if not name:
        return ''
    result = re.sub(r'[^a-zA-Z0-9]', '', name)
    return result


def normalize_reverb_url_value(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _resolve_single_price_placeholder(
    *,
    spec_text: str,
    db: Session,
    model_id: int,
    field_name: str,
    numeric_zero_default: bool = False,
) -> str:
    return resolve_shared_single_price_placeholder(
        spec_text=spec_text,
        db=db,
        model_id=model_id,
        field_name=field_name,
        numeric_zero_default=numeric_zero_default,
    )


def _resolve_price_placeholders_in_value(
    *,
    value: str,
    db: Session,
    model_id: int,
    field_name: str,
    numeric_zero_default: bool = False,
) -> str:
    return resolve_shared_price_placeholders_in_value(
        value=value,
        db=db,
        model_id=model_id,
        field_name=field_name,
        numeric_zero_default=numeric_zero_default,
    )


def _design_option_placeholder_variants(raw_token: str) -> List[str]:
    token = str(raw_token or "").strip()
    if not token:
        return []
    if token.startswith("[") and token.endswith("]"):
        return [token]
    # Reverb templates use bracketed placeholders. Supporting the wrapped form
    # avoids destructive substring replacement when a stored token is short
    # (for example "M") while preserving legacy rows stored without brackets.
    return [f"[{token}]"]


def _resolve_reverb_image_index(field_name: str) -> Optional[str]:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(field_name or "").strip().lower()).strip("_")
    if not normalized:
        return None
    if "photo" not in normalized and "image" not in normalized:
        return None

    if "main" in normalized or "primary" in normalized:
        return "001"

    match = re.search(r"(?:photo|image)(?:_url)?_?([0-9]{1,3})", normalized)
    if not match:
        match = re.search(r"([0-9]{1,3})$", normalized)
    if match:
        return str(int(match.group(1))).zfill(3)

    return "001"


def _apply_reverb_index_tokens(value: str, field_name: str) -> str:
    text = str(value or "")
    if not any(token in text for token in REVERB_INDEX_TOKENS):
        return text

    image_index = _resolve_reverb_image_index(field_name)
    if not image_index:
        return text

    out = text
    for token in REVERB_INDEX_TOKENS:
        out = out.replace(token, image_index)
    return out


def substitute_placeholders(value: str, model: Model, series: Series, manufacturer: Manufacturer, equipment_type: EquipmentType, db: Session = None, context: Dict[str, Any] = None, numeric_zero_default: bool = False, is_image_url: bool = False) -> str:
    """
    Replace [PLACEHOLDERS] in the value string with actual data.
    Supported: [MANUFACTURER_NAME], [SERIES_NAME], [MODEL_NAME], [EQUIPMENT_TYPE], [REVERB_PRICE]
    and [PRICE:marketplace=<name>:variant=<variant_key> +/- <dollars>].
    Dynamic Design Option placeholders (e.g. [SIDE_POCKET]).
    AND [SUM: [Option A] + [Option B] ] logic.
    """
    if not value:
        return ""
        
    result = value
    
    # 0. Handle [SUM: ...] blocks first via Manual Parsing (to handle nested brackets)
    while '[SUM:' in result:
        start_idx = result.find('[SUM:')
        if start_idx == -1:
            break
            
        # Find matching closing bracket
        balance = 0
        end_idx = -1
        content_start = start_idx + 5 # Length of "[SUM:"
        
        for i in range(start_idx, len(result)):
            char = result[i]
            if char == '[':
                balance += 1
            elif char == ']':
                balance -= 1
                
            if balance == 0:
                end_idx = i
                break
        
        if end_idx != -1:
            # We found the block
            full_match = result[start_idx:end_idx+1] # [SUM:...]
            content = result[content_start:end_idx]  # Inner content
            
            # Recursive call with numeric mode forced to True
            resolved_content = substitute_placeholders(
                content, model, series, manufacturer, equipment_type, db, context, 
                numeric_zero_default=True
            )
            
            replacement = full_match # Fallback
            
            try:
                # Split by | (pipe), strip whitespace
                parts = [p.strip() for p in resolved_content.split('|')]
                unresolved_parts = [p for p in parts if p and UNRESOLVED_BRACKET_TOKEN_PATTERN.search(p)]
                if unresolved_parts:
                    replacement = f"[SUM_ERROR: {content} -> unresolved token(s): {' | '.join(unresolved_parts)}]"
                else:
                    # Filter empty parts and parse floats
                    total = sum(float(p) for p in parts if p)
                    replacement = f"{total:.2f}"
            except Exception as e:
                replacement = f"[SUM_ERROR: {content} -> {str(e)}]"
            
            # Replace only the first occurrence (safe because we loop)
            result = result.replace(full_match, replacement, 1)
        else:
            # Malformed/Unclosed SUM block - break to avoid infinite loop
            break

    mfr_name = manufacturer.name if manufacturer else ''
    series_name = series.name if series else ''
    model_name = model.name if model else ''
    equip_type = equipment_type.name if equipment_type else ''
    
    # Apply URL normalization if requested (matches Amazon export logic)
    if is_image_url:
        def img_norm(s):
            if not s: return ''
            # Replace whitespace sequences with underscore, keep other chars including punctuation
            return re.sub(r'\s+', '_', s.strip())

        mfr_name = img_norm(mfr_name)
        series_name = img_norm(series_name)
        model_name = img_norm(model_name)
        equip_type = img_norm(equip_type)
    
    # 1. Handle Dynamic Design Option Placeholders
    # Context must contain 'design_option_map' (Token->Obj) and 'et_assignments' (Set[DO_ID])
    if context and 'design_option_map' in context:
        do_map = context['design_option_map']
        et_assignments = context.get('et_assignments', set())
        
        for token, option in do_map.items():
            for placeholder_token in _design_option_placeholder_variants(token):
                if placeholder_token not in result:
                    continue
                # Found a placeholder!
                # Check if this option is assigned to this Equipment Type
                replacement = ""
                if option.id in et_assignments:
                    # It is assigned! Format price.
                    replacement = f"{(option.price_cents / 100):.2f}"
                elif numeric_zero_default:
                   # Inside SUM block, unassigned = 0
                   replacement = "0"

                # Replace only the exact placeholder token, never raw substrings.
                result = result.replace(placeholder_token, replacement)

    if db:
        # Backward compatibility: legacy fixed Reverb placeholders are resolved
        # through the shared PRICE token resolver, with the historic fallback of
        # empty string (or "0" in numeric mode) when snapshots are missing.
        for legacy_token, variant_key in REVERB_LEGACY_PRICE_VARIANT_MAP.items():
            if legacy_token not in result:
                continue
            try:
                replacement = _resolve_single_price_placeholder(
                    spec_text=f"marketplace=reverb:variant={variant_key}",
                    db=db,
                    model_id=model.id,
                    field_name="reverb_template_value",
                    numeric_zero_default=numeric_zero_default,
                )
            except HTTPException as exc:
                if exc.status_code == 400 and "Missing pricing snapshot for PRICE placeholder" in str(exc.detail):
                    replacement = "0" if numeric_zero_default else ""
                else:
                    raise
            result = result.replace(legacy_token, replacement)

        # Support Amazon-style marketplace/variant price tokens in Reverb templates.
        result = _resolve_price_placeholders_in_value(
            value=result,
            db=db,
            model_id=model.id,
            field_name="reverb_template_value",
            numeric_zero_default=numeric_zero_default,
        )
    
    # Text-based substitution (no special image handling needed for Reverb CSV usually)
    result = result.replace('[MANUFACTURER_NAME]', mfr_name)
    result = result.replace('[SERIES_NAME]', series_name)
    result = result.replace('[MODEL_NAME]', model_name)
    result = result.replace('[EQUIPMENT_TYPE]', equip_type)
    
    # [SKU] placeholder - Maps to model.parent_sku
    sku_val = model.parent_sku if model.parent_sku else "0" if numeric_zero_default else ""
    result = result.replace('[SKU]', sku_val)
    result = result.replace('[Sku]', sku_val)
    result = result.replace('[sku]', sku_val)
    result = apply_base_sku_tokens(result, model, numeric_zero_default=numeric_zero_default)
    result = resolve_structured_tokens_in_value(
        result,
        model=model,
        manufacturer=manufacturer,
        series=series,
        equipment_type=equipment_type,
        design_option_map=(context or {}).get('design_option_map'),
        numeric_zero_default=numeric_zero_default,
    )
    
    result = result.replace('[Manufacturer_Name]', mfr_name)
    result = result.replace('[Series_Name]', series_name)
    result = result.replace('[Model_Name]', model_name)
    result = result.replace('[Equipment_Type]', equip_type)
    
    return result

def generate_reverb_export_csv(db: Session, model_ids: List[int]) -> tuple[io.BytesIO, str]:
    """
    Generate a Reverb CSV export for the given models.
    Returns (csv_buffer, filename).
    """
    if not model_ids:
        raise HTTPException(status_code=400, detail="No models selected")

    # 1. Fetch Models
    models = db.query(Model).filter(Model.id.in_(model_ids)).all()
    if not models:
        raise HTTPException(status_code=404, detail="No models found")

    # 2. Resolve Reverb Template via explicit equipment type assignment.
    if any(m.equipment_type_id is None for m in models):
        raise HTTPException(status_code=400, detail="Selected models include rows without equipment type assignments.")
    equipment_type_ids = sorted({int(m.equipment_type_id) for m in models if m.equipment_type_id is not None})
    if not equipment_type_ids:
        raise HTTPException(status_code=400, detail="Selected models are missing equipment type assignments.")

    equipment_types = db.query(EquipmentType).filter(EquipmentType.id.in_(equipment_type_ids)).all()
    equipment_type_by_id = {int(et.id): et for et in equipment_types}
    missing_equipment_type_ids = [et_id for et_id in equipment_type_ids if et_id not in equipment_type_by_id]
    if missing_equipment_type_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Equipment type(s) not found for export: {missing_equipment_type_ids}",
        )

    missing_template_assignments = [str(et.name or et.id) for et in equipment_types if et.reverb_template_id is None]
    if missing_template_assignments:
        raise HTTPException(
            status_code=400,
            detail=(
                "Reverb template is not assigned for equipment type(s): "
                f"{sorted(missing_template_assignments)}"
            ),
        )

    assigned_template_ids = sorted({int(et.reverb_template_id) for et in equipment_types if et.reverb_template_id is not None})
    if len(assigned_template_ids) != 1:
        assignment_map = {
            str(et.name or et.id): int(et.reverb_template_id) if et.reverb_template_id is not None else None
            for et in equipment_types
        }
        raise HTTPException(
            status_code=400,
            detail=(
                "Selected models span multiple Reverb templates. "
                f"Assignments: {assignment_map}"
            ),
        )

    template_id = int(assigned_template_ids[0])
    template = db.query(ReverbTemplate).filter(ReverbTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=400,
            detail=f"Assigned Reverb template not found (template_id={template_id}).",
        )

    try:
        with materialize_reverb_template_asset(template, db=db) as runtime_path:
            runtime_template = load_reverb_runtime_template(
                file_path=runtime_path,
                original_filename=template.original_filename,
            )
    except ReverbTemplateAssetMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read assigned Reverb template file: {str(e)}")

    export_headers = [str(h).strip() for h in (runtime_template.get("headers", []) or []) if str(h).strip()]
    if not export_headers:
        raise HTTPException(status_code=400, detail="Assigned Reverb template has no export headers.")
    runtime_defaults_by_field = runtime_template.get("defaults_by_field", {}) or {}
    runtime_defaults_by_field_lower = {str(k).lower(): v for k, v in runtime_defaults_by_field.items()}

    # 3. Load Template Fields
    fields = db.query(ReverbField).filter(ReverbField.reverb_template_id == template_id).order_by(ReverbField.order_index).all()
    fields_by_name = {str(f.field_name): f for f in fields}
    fields_by_name_lower = {str(f.field_name).lower(): f for f in fields}
    
    # 3.5 Load Field Overrides for these Equipment Types
    field_ids = [f.id for f in fields]
    overrides = []
    if field_ids and equipment_type_ids:
        overrides = db.query(ReverbEquipmentTypeFieldOverride).filter(
            ReverbEquipmentTypeFieldOverride.reverb_field_id.in_(field_ids),
            ReverbEquipmentTypeFieldOverride.equipment_type_id.in_(equipment_type_ids)
        ).all()
    
    # Map: (equipment_type_id, field_id) -> override_value
    override_map = {(o.equipment_type_id, o.reverb_field_id): o.default_value for o in overrides}

    # 3.6 Determine "Strict Mode" for specific fields
    # If Product Type, Subcategory, or Description has ANY overrides defined in the system
    # (even for ETs not currently being exported), we disable 'Global Default' fallback.
    # This prevents e.g. "Accessories" default from applying to "Guitar Amps" just because
    # "Guitar Amps" wasn't explicitly assigned yet.
    
    strict_fields = ['product_type', 'subcategory_1', 'description']
    strict_field_ids = {f.id for f in fields if f.field_name.lower() in strict_fields}
    
    fields_with_overrides = set()
    if strict_field_ids:
        # Check if these fields have ANY overrides in the entire DB?
        # Or just trust that if the user started overriding, they mean it.
        # Efficient query:
        rows = db.query(ReverbEquipmentTypeFieldOverride.reverb_field_id).filter(
            ReverbEquipmentTypeFieldOverride.reverb_field_id.in_(strict_field_ids)
        ).distinct().all()
        fields_with_overrides = {r[0] for r in rows}

    # 3.7 Load Design Option Placeholders
    # Optimization: Pre-load all design options with tokens and their ET assignments
    from app.models.core import DesignOption, EquipmentTypeDesignOption
    
    design_options_with_tokens = db.query(DesignOption).filter(
        DesignOption.placeholder_token.isnot(None),
        DesignOption.placeholder_token != ''
    ).all()
    
    # Map: Token -> DesignOption
    do_token_map = {opt.placeholder_token: opt for opt in design_options_with_tokens}
    
    # Map: EquipmentTypeID -> Set of DesignOptionIDs
    # Only for the options that have tokens
    do_ids = [opt.id for opt in design_options_with_tokens]
    
    # We only care about models in this batch, so filter by their ETs?
    # Or just query all for these options (safer/simpler if list is small)
    et_do_links = db.query(EquipmentTypeDesignOption).filter(
        EquipmentTypeDesignOption.design_option_id.in_(do_ids)
    ).all()
    
    et_do_map = {} # ET_ID -> Set(DO_ID)
    for link in et_do_links:
        if link.equipment_type_id not in et_do_map:
            et_do_map[link.equipment_type_id] = set()
        et_do_map[link.equipment_type_id].add(link.design_option_id)

    # 4. Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header Row
    writer.writerow(export_headers)
    
    # Data Rows
    for model in models:
        # Resolve related entities for substitution
        series = db.query(Series).filter(Series.id == model.series_id).first()
        manufacturer = db.query(Manufacturer).filter(Manufacturer.id == series.manufacturer_id).first() if series else None
        eq_type = db.query(EquipmentType).filter(EquipmentType.id == model.equipment_type_id).first()
        
        # Prepare context for substitution
        context = {
            'design_option_map': do_token_map,
            'et_assignments': et_do_map.get(model.equipment_type_id, set())
        }
        
        row = []
        for header_name in export_headers:
            lookup_key = str(header_name or "").strip()
            field = fields_by_name.get(lookup_key) or fields_by_name_lower.get(lookup_key.lower())

            base_payload = runtime_defaults_by_field.get(lookup_key) or runtime_defaults_by_field_lower.get(lookup_key.lower())
            base_value = ""
            if isinstance(base_payload, dict):
                default_custom = str(base_payload.get("custom_value", "") or "").strip()
                default_selected = str(base_payload.get("selected_value", "") or "").strip()
                base_value = default_custom if default_custom else default_selected
            elif base_payload is not None:
                base_value = str(base_payload or "").strip()

            value = ""
            
            # Check for Override first (Always Priority)
            override_val = override_map.get((model.equipment_type_id, field.id)) if field is not None else None
            
            # Determine if this is likely an image URL field/value for underscore normalization
            is_potential_image = (
                'photo' in lookup_key.lower() or
                'image' in lookup_key.lower() or
                'url' in lookup_key.lower()
            )

            if base_value:
                is_url_val = is_potential_image or base_value.strip().lower().startswith(('http', 'www', 'ftp'))
                value = substitute_placeholders(base_value, model, series, manufacturer, eq_type, db, context, is_image_url=is_url_val)

            if field is not None:
                if override_val is not None:
                    is_url_val = is_potential_image or (override_val and override_val.strip().lower().startswith(('http', 'www', 'ftp')))
                    value = substitute_placeholders(override_val, model, series, manufacturer, eq_type, db, context, is_image_url=is_url_val)
                else:
                    # No override found. Should we use DB-managed field defaults?
                    # Check Strict Mode
                    is_strict = (field.id in fields_with_overrides)
                    
                    if not is_strict:
                        if field.custom_value:
                            is_url_val = is_potential_image or (field.custom_value and field.custom_value.strip().lower().startswith(('http', 'www', 'ftp')))
                            value = substitute_placeholders(field.custom_value, model, series, manufacturer, eq_type, db, context, is_image_url=is_url_val)
                        elif field.selected_value:
                            is_url_val = is_potential_image or (field.selected_value and field.selected_value.strip().lower().startswith(('http', 'www', 'ftp')))
                            value = substitute_placeholders(field.selected_value, model, series, manufacturer, eq_type, db, context, is_image_url=is_url_val)

            value = _apply_reverb_index_tokens(value, lookup_key)
            if is_potential_image:
                value = normalize_reverb_url_value(value)
            
            # Special Logic: new_listing
            # If the model has an existing Reverb listing (MarketplaceListing), new_listing must be FALSE
            if field is not None and field.field_name == 'new_listing':
                 has_reverb_listing = False
                 if model.marketplace_listings:
                     for listing in model.marketplace_listings:
                         if listing.marketplace and listing.marketplace.lower() == 'reverb' and listing.external_id:
                             has_reverb_listing = True
                             break
                 
                 if has_reverb_listing:
                     value = "FALSE"

            row.append(value)
            

            
        writer.writerow(row)
        
    # 5. Prepare Output
    output.seek(0)
    bytes_buffer = io.BytesIO()
    bytes_buffer.write(output.getvalue().encode('utf-8'))
    bytes_buffer.seek(0)
    
    # Filename generation
    # Use first model metadata
    first_model = models[0]
    first_series = db.query(Series).filter(Series.id == first_model.series_id).first()
    first_mfr = db.query(Manufacturer).filter(Manufacturer.id == first_series.manufacturer_id).first() if first_series else None
    
    mfr_token = normalize_for_url(first_mfr.name) if first_mfr else "Unknown"
    series_token = normalize_for_url(first_series.name) if first_series else "Unknown"
    
    from datetime import datetime
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"Reverb_{mfr_token}_{series_token}_{date_str}.csv"
    
    return bytes_buffer, filename
