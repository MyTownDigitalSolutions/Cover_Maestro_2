"""
DEPRECATED / legacy endpoint module.

Persisted child variation SKUs are not authoritative for eBay export.
eBay child SKUs are computed at export time; parent SKU is the only persistent SKU.
"""

from typing import List, Optional
import re
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models.core import (
    Model, Material, MaterialColourSurcharge, DesignOption,
    PricingOption, ModelVariationSKU, MaterialRoleAssignment, MaterialRoleConfig
)

router = APIRouter(prefix="/ebay-variations", tags=["eBay Variations"])
logger = logging.getLogger(__name__)


class GenerateVariationsRequest(BaseModel):
    model_ids: List[int]
    material_id: Optional[int] = None  # Made optional - will be resolved from role_key if provided
    role_key: Optional[str] = None  # New: role key like "CHOICE_WATERPROOF_FABRIC"
    material_colour_surcharge_id: Optional[int] = None
    design_option_ids: List[int] = []
    pricing_option_ids: List[int] = []
    with_padding: bool = False  # New: select padded vs non-padded abbreviation


class VariationRow(BaseModel):
    model_id: int
    sku: str
    material_id: int
    material_colour_surcharge_id: Optional[int]
    design_option_ids: List[int]
    pricing_option_ids: List[int]


class GenerateVariationsResponse(BaseModel):
    created: int
    updated: int
    errors: List[str]
    rows: List[VariationRow]


@router.get("/by-models", response_model=List[VariationRow])
def get_existing_variations(
    model_ids: str,  # Comma-separated list like "1,2,3"
    db: Session = Depends(get_db)
):
    """
    Fetch existing variation SKUs for the given model IDs.
    Read-only endpoint for viewing what's already persisted.
    """
    logger.warning(
        "Deprecated: child SKUs are computed at export time; parent SKU is the only persistent SKU."
    )
    # Parse comma-separated model IDs
    try:
        parsed_ids = [int(id.strip()) for id in model_ids.split(',') if id.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model_ids format. Expected comma-separated integers.")

    if not parsed_ids:
        return []

    # Fetch existing variations, ordered deterministically
    variations = db.query(ModelVariationSKU).filter(
        ModelVariationSKU.model_id.in_(parsed_ids)
    ).order_by(
        ModelVariationSKU.model_id.asc(),
        ModelVariationSKU.sku.asc()
    ).all()

    # Convert to response format
    rows = []
    for var in variations:
        rows.append(VariationRow(
            model_id=var.model_id,
            sku=var.sku,
            material_id=var.material_id,
            material_colour_surcharge_id=var.material_colour_surcharge_id,
            design_option_ids=var.design_option_ids or [],
            pricing_option_ids=var.pricing_option_ids or []
        ))

    return rows


@router.post("/generate", response_model=GenerateVariationsResponse)
def generate_variations(
    data: GenerateVariationsRequest,
    db: Session = Depends(get_db)
):
    """
    Generate and persist variation SKUs for selected models and options.

    Returns a preview of the generated SKUs and persists them to the database.
    """
    logger.warning(
        "Deprecated: child SKUs are computed at export time; parent SKU is the only persistent SKU."
    )

    # Normalize option IDs for determinism (sorted + deduplicated)
    design_ids = sorted(set(data.design_option_ids or []))
    pricing_ids = sorted(set(data.pricing_option_ids or []))

    # Helper for abbreviation validation (1-3 chars)
    def _is_valid_abbrev(s):
        return bool(s and s.strip()) and 1 <= len(s.strip()) <= 3

    # Helper: return the base prefix up to the END of the last V# marker (e.g., "...V1")
    # We intentionally DROP any template trailing zeros after V# for child SKU generation.
    def _slice_to_version_prefix(base_sku: str) -> Optional[str]:
        if not base_sku:
            return None

        # Find last occurrence of V<number> (case-insensitive), keep exact original slice
        matches = list(re.finditer(r"V\d+", base_sku, flags=re.IGNORECASE))
        if not matches:
            return None

        last = matches[-1]
        return base_sku[:last.end()]

    # Resolve material_id from role_key if provided
    resolved_material_id = data.material_id
    role_config = None

    if data.role_key:
        # Find active assignment for this role
        active_assignment = db.query(MaterialRoleAssignment).filter(
            and_(
                MaterialRoleAssignment.role == data.role_key,
                MaterialRoleAssignment.end_date.is_(None)
            )
        ).first()

        if not active_assignment:
            raise HTTPException(
                status_code=400,
                detail=f"No active assignment found for role '{data.role_key}'"
            )

        resolved_material_id = active_assignment.material_id

        # Load role config for abbreviations
        role_config = db.query(MaterialRoleConfig).filter(
            MaterialRoleConfig.role == data.role_key
        ).first()

        if not role_config:
            raise HTTPException(
                status_code=400,
                detail=f"No role config found for role '{data.role_key}'"
            )

    # Ensure we have a material_id (either from role resolution or direct input)
    if not resolved_material_id:
        raise HTTPException(
            status_code=400,
            detail="Either 'material_id' or 'role_key' must be provided"
        )

    # Validation: Track invalid IDs
    error_detail = {"message": "Invalid/missing abbreviations"}
    has_errors = False

    # Validate material
    material = db.query(Material).filter(Material.id == resolved_material_id).first()
    if not material:
        raise HTTPException(status_code=400, detail=f"Material {resolved_material_id} not found")

    # Decide which abbreviation source to use (role config is authoritative when present)
    if role_config:
        # Use role config abbreviations based on padding flag
        if data.with_padding:
            material_abbrev = role_config.sku_abbrev_with_padding
            if not _is_valid_abbrev(material_abbrev):
                error_detail["missing_role_config_abbrev_with_padding"] = data.role_key
                has_errors = True
        else:
            material_abbrev = role_config.sku_abbrev_no_padding
            if not _is_valid_abbrev(material_abbrev):
                error_detail["missing_role_config_abbrev_no_padding"] = data.role_key
                has_errors = True
    else:
        # Fallback to material abbreviation for backward compatibility
        material_abbrev = material.sku_abbreviation
        if not _is_valid_abbrev(material_abbrev):
            error_detail["invalid_material_id"] = resolved_material_id
            has_errors = True

    # Validate color if provided
    material_surcharge = None
    if data.material_colour_surcharge_id:
        material_surcharge = db.query(MaterialColourSurcharge).filter(
            MaterialColourSurcharge.id == data.material_colour_surcharge_id
        ).first()
        if not material_surcharge:
            raise HTTPException(status_code=400, detail=f"Material colour surcharge {data.material_colour_surcharge_id} not found")

        if not _is_valid_abbrev(material_surcharge.sku_abbreviation):
            error_detail["invalid_color_id"] = data.material_colour_surcharge_id
            has_errors = True

    # Validate design options (using normalized IDs)
    design_options = []
    invalid_design_ids = []
    if design_ids:
        design_options = db.query(DesignOption).filter(
            DesignOption.id.in_(design_ids)
        ).all()

        if len(design_options) != len(design_ids):
            found_ids = {opt.id for opt in design_options}
            missing_ids = set(design_ids) - found_ids
            raise HTTPException(status_code=400, detail=f"Design options not found: {list(missing_ids)}")

        for opt in design_options:
            if not _is_valid_abbrev(opt.sku_abbreviation):
                invalid_design_ids.append(opt.id)

        if invalid_design_ids:
            error_detail["invalid_design_option_ids"] = invalid_design_ids
            has_errors = True

    # Validate pricing options (using normalized IDs)
    pricing_options = []
    invalid_pricing_ids = []
    if pricing_ids:
        pricing_options = db.query(PricingOption).filter(
            PricingOption.id.in_(pricing_ids)
        ).all()

        if len(pricing_options) != len(pricing_ids):
            found_ids = {opt.id for opt in pricing_options}
            missing_ids = set(pricing_ids) - found_ids
            raise HTTPException(status_code=400, detail=f"Pricing options not found: {list(missing_ids)}")

        for opt in pricing_options:
            if not _is_valid_abbrev(opt.sku_abbreviation):
                invalid_pricing_ids.append(opt.id)

        if invalid_pricing_ids:
            error_detail["invalid_pricing_option_ids"] = invalid_pricing_ids
            has_errors = True

    # If validation errors found, return structured 400
    if has_errors:
        raise HTTPException(status_code=400, detail=error_detail)

    # Fetch models
    models = db.query(Model).filter(Model.id.in_(data.model_ids)).all()
    if len(models) != len(data.model_ids):
        found_ids = {m.id for m in models}
        missing_ids = set(data.model_ids) - found_ids
        raise HTTPException(status_code=400, detail=f"Models not found: {list(missing_ids)}")

    # Generate SKUs and upsert
    created_count = 0
    updated_count = 0
    rows = []

    # Deterministic ordering:
    # - Design options: alpha by name (case-insensitive), then by ID
    # - Pricing options: alpha by name (case-insensitive), then by ID
    sorted_design_opts = sorted(design_options, key=lambda x: ((x.name or "").lower(), x.id))
    sorted_pricing_opts = sorted(pricing_options, key=lambda x: ((x.name or "").lower(), x.id))

    for model in models:
        # Base: use SKU override if present, else generated parent SKU, else fallback
        base_sku = (model.sku_override or model.parent_sku or f"MODEL-{model.id}")

        # Slice base SKU to the end of the last V# marker (drops template trailing zeros)
        version_prefix = _slice_to_version_prefix(base_sku)

        # Compose suffix (NO separators, NO trailing zeros)
        color_abbrev = material_surcharge.sku_abbreviation if (material_surcharge and material_surcharge.sku_abbreviation) else ""
        design_suffix = "".join([opt.sku_abbreviation.strip() for opt in sorted_design_opts]) if sorted_design_opts else ""
        pricing_suffix = "".join([opt.sku_abbreviation.strip() for opt in sorted_pricing_opts]) if sorted_pricing_opts else ""

        composed_suffix = f"{material_abbrev.strip()}{color_abbrev.strip()}{design_suffix}{pricing_suffix}"

        if version_prefix:
            # Slot/suffix-based SKU: prefix includes V#, then abbreviations directly
            final_sku = f"{version_prefix}{composed_suffix}"
        else:
            # Fallback for unexpected base SKUs without V# marker:
            # Preserve the previous tokenized behavior to avoid breaking exports.
            sku_parts = [base_sku, f"M{material_abbrev}"]
            if color_abbrev:
                sku_parts.append(f"C{color_abbrev}")
            for opt in sorted_design_opts:
                sku_parts.append(f"D{opt.sku_abbreviation}")
            for opt in sorted_pricing_opts:
                sku_parts.append(f"P{opt.sku_abbreviation}")
            final_sku = "-".join(sku_parts)

        # Check if variation already exists (using normalized IDs)
        existing = db.query(ModelVariationSKU).filter(
            and_(
                ModelVariationSKU.model_id == model.id,
                ModelVariationSKU.material_id == resolved_material_id,
                ModelVariationSKU.material_colour_surcharge_id == data.material_colour_surcharge_id,
                ModelVariationSKU.design_option_ids == design_ids,
                ModelVariationSKU.pricing_option_ids == pricing_ids,
                ModelVariationSKU.with_padding == data.with_padding
            )
        ).first()

        if existing:
            existing.sku = final_sku
            existing.role_key = data.role_key
            updated_count += 1
        else:
            new_variation = ModelVariationSKU(
                model_id=model.id,
                sku=final_sku,
                material_id=resolved_material_id,
                material_colour_surcharge_id=data.material_colour_surcharge_id,
                design_option_ids=design_ids,
                pricing_option_ids=pricing_ids,
                is_parent=False,
                with_padding=data.with_padding,
                retail_price_cents=None,
                role_key=data.role_key
            )
            db.add(new_variation)
            created_count += 1

        rows.append(VariationRow(
            model_id=model.id,
            sku=final_sku,
            material_id=resolved_material_id,
            material_colour_surcharge_id=data.material_colour_surcharge_id,
            design_option_ids=design_ids,
            pricing_option_ids=pricing_ids
        ))

    db.commit()

    return GenerateVariationsResponse(
        created=created_count,
        updated=updated_count,
        errors=[],
        rows=rows
    )
