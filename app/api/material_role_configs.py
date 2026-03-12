from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app.database import get_db
from app.models.core import MaterialRoleConfig
from app.schemas.core import (
    MaterialRoleConfigCreate,
    MaterialRoleConfigUpdate,
    MaterialRoleConfigResponse
)

router = APIRouter(prefix="/material-role-configs", tags=["material-role-configs"])


def normalize_string(value: str | None) -> str | None:
    """Normalize string: trim whitespace and convert empty strings to None."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def validate_abbreviation(abbrev: str | None, field_name: str) -> str | None:
    """Validate and normalize abbreviation: uppercase and check length."""
    if abbrev is None:
        return None
    
    abbrev = abbrev.upper().strip()
    
    if len(abbrev) > 4:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be 4 characters or less (got: '{abbrev}')"
        )
    
    return abbrev if abbrev else None


@router.get("", response_model=List[MaterialRoleConfigResponse])
def list_material_role_configs(db: Session = Depends(get_db)):
    """
    Get all material role configurations.
    Ordered by sort_order ASC, then role ASC.
    """
    configs = db.query(MaterialRoleConfig).order_by(
        MaterialRoleConfig.sort_order.asc(),
        MaterialRoleConfig.role.asc()
    ).all()
    
    return configs


@router.post("", response_model=MaterialRoleConfigResponse)
def create_material_role_config(data: MaterialRoleConfigCreate, db: Session = Depends(get_db)):
    """
    Create a new material role configuration.
    Role must be unique and non-empty.
    """
    # Normalize role and convert to uppercase
    role = normalize_string(data.role)
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Role is required and cannot be blank"
        )
    role = role.upper()
    
    # Validate sort_order is non-negative
    if data.sort_order < 0:
        raise HTTPException(
            status_code=400,
            detail="sort_order cannot be negative"
        )
    
    # Normalize other fields
    display_name = normalize_string(data.display_name)
    display_name_with_padding = normalize_string(data.display_name_with_padding)
    
    # Validate and normalize abbreviations
    try:
        sku_abbrev_no_padding = validate_abbreviation(
            data.sku_abbrev_no_padding,
            "sku_abbrev_no_padding"
        )
        sku_abbrev_with_padding = validate_abbreviation(
            data.sku_abbrev_with_padding,
            "sku_abbrev_with_padding"
        )
    except HTTPException:
        raise
    
    # Create config
    config = MaterialRoleConfig(
        role=role,
        display_name=display_name,
        display_name_with_padding=display_name_with_padding,
        sku_abbrev_no_padding=sku_abbrev_no_padding,
        sku_abbrev_with_padding=sku_abbrev_with_padding,
        ebay_variation_enabled=data.ebay_variation_enabled,
        sort_order=data.sort_order
    )
    
    try:
        db.add(config)
        db.commit()
        db.refresh(config)
        return config
    
    except IntegrityError as e:
        db.rollback()
        if "uq_material_role_config_role" in str(e) or "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=400,
                detail=f"Material role config with role '{role}' already exists"
            )
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")


@router.put("/{id}", response_model=MaterialRoleConfigResponse)
def update_material_role_config(
    id: int,
    data: MaterialRoleConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing material role configuration.
    Only provided fields will be updated.
    """
    config = db.query(MaterialRoleConfig).filter(MaterialRoleConfig.id == id).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Material role config not found")
    
    # Get fields that were explicitly set
    update_data = data.model_dump(exclude_unset=True)
    
    # Validate sort_order is non-negative if provided
    if "sort_order" in update_data and update_data["sort_order"] < 0:
        raise HTTPException(
            status_code=400,
            detail="sort_order cannot be negative"
        )
    
    # Normalize and validate fields if provided
    if "display_name" in update_data:
        config.display_name = normalize_string(update_data["display_name"])

    if "display_name_with_padding" in update_data:
        config.display_name_with_padding = normalize_string(update_data["display_name_with_padding"])
    
    if "sku_abbrev_no_padding" in update_data:
        try:
            config.sku_abbrev_no_padding = validate_abbreviation(
                update_data["sku_abbrev_no_padding"],
                "sku_abbrev_no_padding"
            )
        except HTTPException:
            raise
    
    if "sku_abbrev_with_padding" in update_data:
        try:
            config.sku_abbrev_with_padding = validate_abbreviation(
                update_data["sku_abbrev_with_padding"],
                "sku_abbrev_with_padding"
            )
        except HTTPException:
            raise
    
    if "ebay_variation_enabled" in update_data:
        config.ebay_variation_enabled = update_data["ebay_variation_enabled"]
    
    if "sort_order" in update_data:
        config.sort_order = update_data["sort_order"]
    
    try:
        db.commit()
        db.refresh(config)
        return config
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.delete("/{id}")
def delete_material_role_config(id: int, db: Session = Depends(get_db)):
    """
    Delete a material role configuration.
    """
    config = db.query(MaterialRoleConfig).filter(MaterialRoleConfig.id == id).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Material role config not found")
    
    try:
        db.delete(config)
        db.commit()
        return {"deleted": True, "id": id}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
