import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from typing import Optional, List, Dict, Any
import os
import hashlib
from datetime import datetime
from pathlib import Path

from app.database import get_db
# We might need a service class later, but for now implementing logic here or reuse ebay service concepts
from app.schemas.templates import (
    ReverbTemplateResponse,
    ReverbTemplateUpdateRequest,
    ReverbTemplateParseSummary,
    ReverbTemplateFieldsResponse,
    ReverbFieldResponse,
    ReverbFieldUpdateRequest,
    ReverbValidValueCreateRequest,
    ReverbTemplatePreviewResponse,
    ReverbFieldOverrideResponse,
    ReverbFieldOverrideCreateRequest
    # ReverbTemplateIntegrityResponse, # Not defined yet, skipping for now
    # ReverbTemplateVerificationResponse # Not defined yet, skipping for now
)
from app.models.templates import ReverbTemplate, ReverbField, ReverbFieldValue, ReverbEquipmentTypeFieldOverride
from app.models.core import EquipmentType
from app.services.reverb_template_asset_store import (
    ReverbTemplateAssetMissingError,
    get_reverb_template_media_type,
    get_reverb_template_storage_key,
    load_reverb_template_asset_bytes,
    materialize_reverb_template_asset,
)
from app.services.reverb_template_io import (
    load_reverb_runtime_template,
    read_reverb_template_preview,
)

router = APIRouter(
    prefix="/reverb-templates",
    tags=["Reverb Templates"]
)

REVERB_ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".xlsx"}


def _validate_reverb_template_filename(filename: str) -> str:
    clean_name = os.path.basename(str(filename or "").strip())
    ext = os.path.splitext(clean_name.lower())[1]
    if ext not in REVERB_ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are allowed")
    return clean_name


def _default_reverb_template_display_name(filename: str) -> str:
    stem = Path(str(filename or "").strip()).stem.strip()
    return stem or str(filename or "").strip() or "Reverb Template"


def _get_reverb_template_or_404(template_id: int, db: Session) -> ReverbTemplate:
    template = db.query(ReverbTemplate).filter(ReverbTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


def _latest_reverb_template(db: Session) -> Optional[ReverbTemplate]:
    return (
        db.query(ReverbTemplate)
        .order_by(ReverbTemplate.uploaded_at.desc(), ReverbTemplate.id.desc())
        .first()
    )


def _build_reverb_template_download_response(template: ReverbTemplate, db: Session, mode: str = "inline") -> StreamingResponse:
    try:
        payload = load_reverb_template_asset_bytes(template, db=db)
    except ReverbTemplateAssetMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    disposition = "inline" if mode == "inline" else "attachment"
    media_type = get_reverb_template_media_type(template)

    response = StreamingResponse(
        io.BytesIO(payload),
        media_type=media_type
    )
    response.headers["Content-Disposition"] = f'{disposition}; filename="{template.original_filename}"'
    return response


def _build_reverb_template_preview_response(
    template: ReverbTemplate,
    db: Session,
    preview_rows: int = 25,
    preview_cols: int = 20,
) -> ReverbTemplatePreviewResponse:
    try:
        with materialize_reverb_template_asset(template, db=db) as runtime_path:
            preview = read_reverb_template_preview(
                file_path=runtime_path,
                original_filename=template.original_filename,
                preview_rows=preview_rows,
                preview_cols=preview_cols,
            )
    except ReverbTemplateAssetMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ReverbTemplatePreviewResponse(
        template_id=template.id,
        original_filename=template.original_filename,
        sheet_name=str(preview.get("sheet_name", "csv")),
        max_row=int(preview.get("max_row", 0)),
        max_column=int(preview.get("max_column", 0)),
        preview_row_count=len(preview.get("grid", [])),
        preview_column_count=int(preview.get("max_column", 0)),
        grid=list(preview.get("grid", [])),
    )


def _persist_reverb_template_asset(
    *,
    template: ReverbTemplate,
    clean_name: str,
    file_bytes: bytes,
    upload_sha256: str,
    db: Session,
) -> ReverbTemplate:
    persisted_sha256 = hashlib.sha256(file_bytes).hexdigest()
    if persisted_sha256 != upload_sha256:
        raise HTTPException(status_code=500, detail="Reverb template write verification failed (sha256 mismatch).")

    template.original_filename = clean_name
    template.file_path = get_reverb_template_storage_key(int(template.id), clean_name)
    template.asset_blob = file_bytes
    template.file_size = len(file_bytes)
    template.sha256 = upload_sha256
    template.uploaded_at = datetime.utcnow()
    db.commit()
    db.refresh(template)

    return template


def _snapshot_existing_reverb_field_state(template_id: int, db: Session) -> Dict[str, Dict[str, Any]]:
    fields = (
        db.query(ReverbField)
        .options(selectinload(ReverbField.valid_values), selectinload(ReverbField.overrides))
        .filter(ReverbField.reverb_template_id == template_id)
        .all()
    )
    state: Dict[str, Dict[str, Any]] = {}
    for field in fields:
        field_name = str(field.field_name or "").strip()
        if not field_name:
            continue
        state[field_name] = {
            "required": bool(field.required),
            "selected_value": field.selected_value,
            "custom_value": field.custom_value,
            "valid_values": [
                str(v.value or "").strip()
                for v in (field.valid_values or [])
                if str(v.value or "").strip()
            ],
            "overrides": [
                {
                    "equipment_type_id": int(o.equipment_type_id),
                    "default_value": o.default_value,
                }
                for o in (field.overrides or [])
                if o.equipment_type_id is not None
            ],
        }
    return state


def _clear_reverb_fields_for_template(template_id: int, db: Session) -> None:
    field_ids = [
        int(row[0])
        for row in db.query(ReverbField.id).filter(ReverbField.reverb_template_id == template_id).all()
    ]
    if field_ids:
        db.query(ReverbEquipmentTypeFieldOverride).filter(
            ReverbEquipmentTypeFieldOverride.reverb_field_id.in_(field_ids)
        ).delete(synchronize_session=False)
        db.query(ReverbFieldValue).filter(
            ReverbFieldValue.reverb_field_id.in_(field_ids)
        ).delete(synchronize_session=False)
    db.query(ReverbField).filter(ReverbField.reverb_template_id == template_id).delete(synchronize_session=False)
    db.commit()


def _create_reverb_fields_from_headers(template_id: int, headers: List[str], db: Session) -> List[ReverbField]:
    created: List[ReverbField] = []
    for idx, header in enumerate(headers):
        header_name = str(header or "").strip()
        if not header_name:
            continue

        field = ReverbField(
            reverb_template_id=template_id,
            field_name=header_name,
            display_name=header_name.replace("_", " ").title(),
            required=False,
            order_index=idx,
        )
        lower_name = header_name.lower()
        if lower_name in ["make", "model", "price", "condition", "categories"]:
            field.required = True

        db.add(field)
        created.append(field)

    db.flush()
    return created


def _restore_reverb_field_state(
    created_fields: List[ReverbField],
    previous_state: Dict[str, Dict[str, Any]],
    explicit_required_by_field: Dict[str, bool],
    db: Session,
) -> Dict[str, int]:
    values_restored = 0
    overrides_restored = 0

    previous_state_lower = {k.lower(): v for k, v in previous_state.items()}
    explicit_required_lower = {k.lower(): v for k, v in (explicit_required_by_field or {}).items()}
    for field in created_fields:
        field_name = str(field.field_name or "")
        prior = previous_state.get(field_name) or previous_state_lower.get(field_name.lower())
        explicit_required = explicit_required_by_field.get(field_name)
        if explicit_required is None:
            explicit_required = explicit_required_lower.get(field_name.lower())

        if explicit_required is not None:
            field.required = bool(explicit_required)
        elif prior:
            field.required = bool(prior.get("required", field.required))

        if not prior:
            continue

        prior_selected_value = str(prior.get("selected_value") or "").strip()
        if prior_selected_value:
            field.selected_value = prior_selected_value

        prior_custom_value = str(prior.get("custom_value") or "").strip()
        if prior_custom_value:
            field.custom_value = prior_custom_value

        existing_values = {
            str(row[0] or "").strip()
            for row in db.query(ReverbFieldValue.value).filter(ReverbFieldValue.reverb_field_id == field.id).all()
            if str(row[0] or "").strip()
        }
        for value in prior.get("valid_values", []) or []:
            clean_value = str(value or "").strip()
            if not clean_value or clean_value in existing_values:
                continue
            db.add(ReverbFieldValue(reverb_field_id=field.id, value=clean_value))
            existing_values.add(clean_value)
            values_restored += 1

        for override in prior.get("overrides", []) or []:
            equipment_type_id = override.get("equipment_type_id")
            default_value = override.get("default_value")
            if equipment_type_id is None:
                continue
            db.add(
                ReverbEquipmentTypeFieldOverride(
                    reverb_field_id=field.id,
                    equipment_type_id=int(equipment_type_id),
                    default_value=default_value,
                )
            )
            overrides_restored += 1

    return {"values_restored": values_restored, "overrides_restored": overrides_restored}


def _parse_reverb_template_file(template: ReverbTemplate, db: Session) -> ReverbTemplateParseSummary:
    previous_state = _snapshot_existing_reverb_field_state(template.id, db)

    with materialize_reverb_template_asset(template, db=db) as runtime_path:
        parsed = load_reverb_runtime_template(
            file_path=runtime_path,
            original_filename=template.original_filename,
        )
    _clear_reverb_fields_for_template(template.id, db)

    fields_inserted = 0
    values_inserted = 0
    defaults_applied = 0
    headers = list(parsed.get("headers", []) or [])
    created_fields = _create_reverb_fields_from_headers(template.id, headers, db)
    field_by_name = {str(f.field_name): f for f in created_fields}
    field_by_name_lower = {str(f.field_name).lower(): f for f in created_fields}
    fields_inserted = len(created_fields)

    valid_values_by_field = parsed.get("valid_values_by_field", {}) or {}
    for field_name, values in valid_values_by_field.items():
        lookup_key = str(field_name)
        field = field_by_name.get(lookup_key) or field_by_name_lower.get(lookup_key.lower())
        if not field:
            continue
        seen = set()
        for raw_value in values or []:
            value = str(raw_value or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            db.add(ReverbFieldValue(reverb_field_id=field.id, value=value))
            values_inserted += 1

    defaults_by_field = parsed.get("defaults_by_field", {}) or {}
    for field_name, payload in defaults_by_field.items():
        lookup_key = str(field_name)
        field = field_by_name.get(lookup_key) or field_by_name_lower.get(lookup_key.lower())
        if not field:
            continue
        selected_value = str(payload.get("selected_value", "") or "").strip()
        custom_value = str(payload.get("custom_value", "") or "").strip()
        applied_any = False
        if selected_value:
            field.selected_value = selected_value
            applied_any = True
        if custom_value:
            field.custom_value = custom_value
            applied_any = True
        if applied_any:
            defaults_applied += 1

    explicit_required_by_field = parsed.get("required_by_field", {}) or {}
    restored = _restore_reverb_field_state(created_fields, previous_state, explicit_required_by_field, db)
    values_inserted += int(restored.get("values_restored", 0))

    db.commit()

    return ReverbTemplateParseSummary(
        template_id=template.id,
        fields_inserted=fields_inserted,
        values_inserted=values_inserted,
        defaults_applied=defaults_applied,
        values_ignored_not_in_template=0,
        defaults_ignored_not_in_template=0,
    )

def _build_reverb_template_fields_response(template_id: int, db: Session) -> ReverbTemplateFieldsResponse:
    """
    Internal helper: Load fields + valid values for a template and map to API response models.
    """
    # 1) Verify template exists
    template = db.query(ReverbTemplate).filter(ReverbTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 2) Query fields and eagerly load valid_values
    fields: List[ReverbField] = (
        db.query(ReverbField)
        .options(
            selectinload(ReverbField.valid_values),
            selectinload(ReverbField.overrides)
        )
        .filter(ReverbField.reverb_template_id == template_id)
        .order_by(func.coalesce(ReverbField.order_index, 10**9), ReverbField.id)
        .all()
    )

    # 3) Map to response
    response_fields: List[ReverbFieldResponse] = []
    for f in fields:
        sorted_values = sorted((f.valid_values or []), key=lambda v: v.id)
        
        allowed_strs = [v.value for v in sorted_values]
        allowed_detailed = [{"id": v.id, "value": v.value} for v in sorted_values]

        # Map Overrides
        # We need to manually construct the Pydantic model for overrides because of forward ref?
        # Or just pass the ORM objects if the schema is correct.
        overrides_list = f.overrides or []

        response_fields.append(
            ReverbFieldResponse(
                id=f.id,
                reverb_template_id=f.reverb_template_id,
                field_name=f.field_name,
                display_name=f.display_name,
                required=f.required,
                order_index=f.order_index,
                selected_value=f.selected_value,
                custom_value=f.custom_value,
                allowed_values=allowed_strs,
                allowed_values_detailed=allowed_detailed,
                overrides=overrides_list
            )
        )

    return ReverbTemplateFieldsResponse(
        template_id=template_id,
        fields=response_fields
    )


def _reconcile_reverb_field_value_state(field: ReverbField, db: Session) -> None:
    valid_values = [
        str(row[0] or "").strip()
        for row in (
            db.query(ReverbFieldValue.value)
            .filter(ReverbFieldValue.reverb_field_id == field.id)
            .order_by(ReverbFieldValue.id)
            .all()
        )
        if str(row[0] or "").strip()
    ]
    unique_valid_values: List[str] = list(dict.fromkeys(valid_values))

    selected_value = str(field.selected_value or "").strip()
    custom_value = str(field.custom_value or "").strip()

    if selected_value and selected_value not in unique_valid_values:
        field.selected_value = None
        selected_value = ""

    if custom_value and custom_value not in unique_valid_values:
        field.custom_value = None
        custom_value = ""

    if not selected_value and not custom_value and len(unique_valid_values) == 1:
        field.selected_value = unique_valid_values[0]


@router.post("/upload", response_model=ReverbTemplateResponse)
async def upload_reverb_template(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and store the Reverb template asset (.csv or .xlsx).
    """
    clean_name = _validate_reverb_template_filename(file.filename)

    await file.seek(0)
    file_bytes = await file.read()
    upload_sha256 = hashlib.sha256(file_bytes).hexdigest()
    mem_size = len(file_bytes)

    template = ReverbTemplate(
        display_name=_default_reverb_template_display_name(clean_name),
        original_filename=clean_name,
        file_path="",
        file_size=mem_size,
        sha256=upload_sha256,
        uploaded_at=datetime.utcnow(),
    )

    try:
        # Keep DB and file persistence in one transaction; avoid orphan rows on write failure.
        db.add(template)
        db.flush()
        return _persist_reverb_template_asset(
            template=template,
            clean_name=clean_name,
            file_bytes=file_bytes,
            upload_sha256=upload_sha256,
            db=db,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to persist Reverb template upload: {str(e)}")


@router.get("/current", response_model=Optional[ReverbTemplateResponse])
def get_current_reverb_template(db: Session = Depends(get_db)):
    """
    Get the most recently uploaded Reverb template metadata.
    """
    return _latest_reverb_template(db)


@router.get("/", response_model=List[ReverbTemplateResponse])
def list_reverb_templates(db: Session = Depends(get_db)):
    """
    List all uploaded Reverb templates.
    """
    return db.query(ReverbTemplate).order_by(ReverbTemplate.uploaded_at.desc(), ReverbTemplate.id.desc()).all()


@router.get("/{template_id}", response_model=ReverbTemplateResponse)
def get_reverb_template(template_id: int, db: Session = Depends(get_db)):
    """
    Get a specific Reverb template by ID.
    """
    return _get_reverb_template_or_404(template_id, db)


@router.patch("/{template_id}", response_model=ReverbTemplateResponse)
def update_reverb_template(
    template_id: int,
    updates: ReverbTemplateUpdateRequest,
    db: Session = Depends(get_db),
):
    template = _get_reverb_template_or_404(template_id, db)
    template.display_name = updates.display_name
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_reverb_template(
    template_id: int,
    remove_assignments: bool = Query(False),
    db: Session = Depends(get_db),
):
    template = _get_reverb_template_or_404(template_id, db)
    linked_equipment_types = (
        db.query(EquipmentType)
        .filter(EquipmentType.reverb_template_id == template.id)
        .all()
    )
    assignment_count = len(linked_equipment_types)

    if assignment_count > 0 and not remove_assignments:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Reverb template id={template.id} is assigned to {assignment_count} equipment type(s). "
                "Retry with remove_assignments=true to clear assignments and delete the template."
            ),
        )

    try:
        if assignment_count > 0:
            for equipment_type in linked_equipment_types:
                equipment_type.reverb_template_id = None

        db.delete(template)
        db.commit()
        return {
            "deleted_template_id": template_id,
            "cleared_assignment_count": assignment_count,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete Reverb template: {str(exc)}")


@router.post("/{template_id}/replace-file", response_model=ReverbTemplateResponse)
async def replace_reverb_template_file(
    template_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Replace the stored file for an existing Reverb template while preserving
    the template row identity and any linked assignments.
    """
    template = _get_reverb_template_or_404(template_id, db)
    clean_name = _validate_reverb_template_filename(file.filename)

    await file.seek(0)
    file_bytes = await file.read()
    upload_sha256 = hashlib.sha256(file_bytes).hexdigest()

    try:
        return _persist_reverb_template_asset(
            template=template,
            clean_name=clean_name,
            file_bytes=file_bytes,
            upload_sha256=upload_sha256,
            db=db,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to replace Reverb template file: {str(e)}")


@router.post("/{template_id}/parse", response_model=ReverbTemplateParseSummary)
def parse_reverb_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    Parse the Reverb template asset and populate metadata in the database.
    Supported formats: CSV and XLSX.
    """
    template = _get_reverb_template_or_404(template_id, db)
    try:
        return _parse_reverb_template_file(template, db)
    except ReverbTemplateAssetMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse template: {str(e)}")


@router.get("/current/fields", response_model=ReverbTemplateFieldsResponse)
def get_current_reverb_template_fields(db: Session = Depends(get_db)):
    """
    Get the parsed fields for the MOST RECENT template.
    """
    latest = _latest_reverb_template(db)

    if not latest:
        raise HTTPException(status_code=404, detail="No Reverb template uploaded")

    return _build_reverb_template_fields_response(latest.id, db)


@router.get("/{template_id}/fields", response_model=ReverbTemplateFieldsResponse)
def get_reverb_template_fields(template_id: int, db: Session = Depends(get_db)):
    return _build_reverb_template_fields_response(template_id, db)


@router.patch("/fields/{field_id}", response_model=ReverbFieldResponse)
def update_reverb_field(
    field_id: int,
    updates: ReverbFieldUpdateRequest,
    db: Session = Depends(get_db)
):
    field = (
        db.query(ReverbField)
        .options(
            selectinload(ReverbField.valid_values),
            selectinload(ReverbField.overrides)
        )
        .filter(ReverbField.id == field_id)
        .first()
    )
    
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    if updates.required is not None:
        field.required = updates.required
    
    if updates.selected_value is not None:
        if updates.selected_value == "Any" or updates.selected_value == "":
            field.selected_value = None
        else:
            valid_values_list = [v.value for v in field.valid_values]
            if updates.selected_value in valid_values_list or updates.custom_value is not None:
                field.selected_value = updates.selected_value
            else:
                # If custom value is set, we strictly shouldn't fail, but let's be safe
                pass
                
    if updates.custom_value is not None:
        field.custom_value = updates.custom_value if updates.custom_value else None

    _reconcile_reverb_field_value_state(field, db)
    
    db.commit()
    db.refresh(field)
    
    # Return updated field
    sorted_values = sorted((field.valid_values or []), key=lambda v: v.id)
    allowed_strs = [v.value for v in sorted_values]
    allowed_detailed = [{"id": v.id, "value": v.value} for v in sorted_values]
    
    return ReverbFieldResponse(
        id=field.id,
        reverb_template_id=field.reverb_template_id,
        field_name=field.field_name,
        display_name=field.display_name,
        required=field.required,
        order_index=field.order_index,
        selected_value=field.selected_value,
        custom_value=field.custom_value,
        allowed_values=allowed_strs,
        allowed_values_detailed=allowed_detailed,
        overrides=field.overrides or []
    )


@router.post("/fields/{field_id}/valid-values", response_model=ReverbFieldResponse)
def add_valid_value_to_reverb_field(
    field_id: int,
    request: ReverbValidValueCreateRequest,
    db: Session = Depends(get_db)
):
    value = request.value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Value cannot be empty")
    
    field = db.query(ReverbField).filter(ReverbField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    existing = (
        db.query(ReverbFieldValue)
        .filter(ReverbFieldValue.reverb_field_id == field_id)
        .all()
    )
    existing_value = next(
        (row for row in existing if str(row.value or "").strip() == value),
        None
    )
    
    if not existing_value:
        new_value = ReverbFieldValue(reverb_field_id=field_id, value=value)
        db.add(new_value)
        db.flush()

    _reconcile_reverb_field_value_state(field, db)
    db.commit()
    db.refresh(field)
    
    # Re-fetch for response
    return update_reverb_field(field_id, ReverbFieldUpdateRequest(), db)


@router.delete("/fields/{field_id}/valid-values/{value_id}", response_model=ReverbFieldResponse)
def delete_valid_value_from_reverb_field(
    field_id: int,
    value_id: int,
    db: Session = Depends(get_db)
):
    value_obj = db.query(ReverbFieldValue).filter(
        ReverbFieldValue.id == value_id,
        ReverbFieldValue.reverb_field_id == field_id
    ).first()
    
    if not value_obj:
        raise HTTPException(status_code=404, detail="Value not found")
    
    field = db.query(ReverbField).filter(ReverbField.id == field_id).first()
    deleted_value = str(value_obj.value or "")
    if field.selected_value == deleted_value:
        field.selected_value = None
    if field.custom_value == deleted_value:
        field.custom_value = None
    
    db.delete(value_obj)
    db.flush()

    _reconcile_reverb_field_value_state(field, db)

    db.commit()
    
    return update_reverb_field(field_id, ReverbFieldUpdateRequest(), db)


@router.post("/fields/{field_id}/overrides", response_model=ReverbFieldResponse)
def create_reverb_field_override(
    field_id: int,
    request: ReverbFieldOverrideCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create or update an override for a specific field and equipment type.
    """
    field = db.query(ReverbField).filter(ReverbField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    # Check if override exists
    existing = db.query(ReverbEquipmentTypeFieldOverride).filter(
        ReverbEquipmentTypeFieldOverride.reverb_field_id == field_id,
        ReverbEquipmentTypeFieldOverride.equipment_type_id == request.equipment_type_id
    ).first()

    if existing:
        existing.default_value = request.default_value
    else:
        new_override = ReverbEquipmentTypeFieldOverride(
            reverb_field_id=field_id,
            equipment_type_id=request.equipment_type_id,
            default_value=request.default_value
        )
        db.add(new_override)
    
    db.commit()
    db.refresh(field)
    
    # Return updated field
    # We reuse the update logic? No, just call the helper or update_reverb_field
    return update_reverb_field(field_id, ReverbFieldUpdateRequest(), db)


@router.delete("/fields/{field_id}/overrides/{override_id}", response_model=ReverbFieldResponse)
def delete_reverb_field_override(
    field_id: int,
    override_id: int,
    db: Session = Depends(get_db)
):
    override = db.query(ReverbEquipmentTypeFieldOverride).filter(
        ReverbEquipmentTypeFieldOverride.id == override_id,
        ReverbEquipmentTypeFieldOverride.reverb_field_id == field_id
    ).first()
    
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
        
    db.delete(override)
    db.commit()
    
    return update_reverb_field(field_id, ReverbFieldUpdateRequest(), db)


@router.get("/current/download")
def download_current_reverb_template(mode: str = "inline", db: Session = Depends(get_db)):
    latest = _latest_reverb_template(db)

    if not latest:
        raise HTTPException(status_code=404, detail="Template not found")
    return _build_reverb_template_download_response(latest, db, mode=mode)


@router.get("/{template_id}/download")
def download_reverb_template(template_id: int, mode: str = "inline", db: Session = Depends(get_db)):
    template = _get_reverb_template_or_404(template_id, db)
    return _build_reverb_template_download_response(template, db, mode=mode)


@router.get("/current/preview", response_model=ReverbTemplatePreviewResponse)
def preview_current_reverb_template(
    preview_rows: int = 25,
    preview_cols: int = 20,
    db: Session = Depends(get_db)
):
    latest = _latest_reverb_template(db)

    if not latest:
        raise HTTPException(status_code=404, detail="Template not found")
    return _build_reverb_template_preview_response(latest, db, preview_rows=preview_rows, preview_cols=preview_cols)


@router.get("/{template_id}/preview", response_model=ReverbTemplatePreviewResponse)
def preview_reverb_template(
    template_id: int,
    preview_rows: int = 25,
    preview_cols: int = 20,
    db: Session = Depends(get_db),
):
    template = _get_reverb_template_or_404(template_id, db)
    return _build_reverb_template_preview_response(template, db, preview_rows=preview_rows, preview_cols=preview_cols)
