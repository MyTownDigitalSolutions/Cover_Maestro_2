from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, text
from typing import List
import logging
from app.database import get_db
from app.models.core import DesignOption, EquipmentTypeDesignOption
from app.schemas.core import DesignOptionCreate, DesignOptionResponse

router = APIRouter(prefix="/design-options", tags=["design-options"])
logger = logging.getLogger(__name__)
DESIGN_OPTIONS_API_VERSION_MARKER = "design_options_api_v2026_02_24_constraint_probe_1"
logger.info("design_options.py version marker: %s", DESIGN_OPTIONS_API_VERSION_MARKER)


def _normalize_name(value: str) -> str:
    return (value or "").strip()


def _normalize_placeholder_token(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if not v or v.lower() == "none":
        return None
    return v


def _normalize_sku_abbreviation(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    return v.upper()


def _normalize_equipment_type_ids(values: List[int]) -> List[int]:
    deduped: List[int] = []
    seen: set[int] = set()
    for x in values or []:
        if x is None:
            continue
        try:
            et_id = int(x)
        except (TypeError, ValueError):
            continue
        if et_id in seen:
            continue
        seen.add(et_id)
        deduped.append(et_id)
    return deduped


def _sync_equipment_type_design_options_pk_sequence(db: Session) -> None:
    # Staging/production can drift sequence state after imports/restores; realign before inserts.
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    db.execute(text("""
        SELECT setval(
            pg_get_serial_sequence('equipment_type_design_options', 'id'),
            COALESCE((SELECT MAX(id) FROM equipment_type_design_options), 0) + 1,
            false
        )
    """))


def _raise_design_option_integrity_error(exc: IntegrityError) -> None:
    constraint_name = getattr(getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", None)
    err_text = str(getattr(exc, "orig", exc))
    logger.exception(
        "DesignOption IntegrityError type=%s repr=%r constraint=%s error=%s",
        type(getattr(exc, "orig", exc)).__name__,
        getattr(exc, "orig", exc),
        constraint_name,
        err_text,
    )

    source = f"{constraint_name or ''} {err_text}".lower()
    short_msg = "Design option violates a unique constraint"
    if "uq_equip_type_design_option" in source:
        short_msg = "Duplicate equipment type assignment for this design option"
    elif "placeholder_token" in source:
        short_msg = "Design option placeholder_token already exists"
    elif "sku_abbreviation" in source:
        short_msg = "Design option sku_abbreviation already exists"
    elif "name" in source:
        short_msg = "Design option with this name already exists"
    raise HTTPException(
        status_code=400,
        detail=f"IntegrityError constraint={constraint_name or 'unknown'} message={short_msg}",
    )

@router.get("", response_model=List[DesignOptionResponse])
def list_design_options(db: Session = Depends(get_db)):
    return db.query(DesignOption).all()

@router.get("/{id}", response_model=DesignOptionResponse)
def get_design_option(id: int, db: Session = Depends(get_db)):
    option = db.query(DesignOption).filter(DesignOption.id == id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Design option not found")
    return option

@router.post("", response_model=DesignOptionResponse)
def create_design_option(data: DesignOptionCreate, db: Session = Depends(get_db)):
    logger.info("design_options.py version marker: %s", DESIGN_OPTIONS_API_VERSION_MARKER)
    normalized_name = _normalize_name(data.name)
    normalized_sku_abbreviation = _normalize_sku_abbreviation(data.sku_abbreviation)
    normalized_placeholder_token = _normalize_placeholder_token(data.placeholder_token)
    normalized_equipment_type_ids = _normalize_equipment_type_ids(data.equipment_type_ids)
    logger.info(
        "DesignOption POST payload name=%r placeholder_token=%r sku_abbreviation=%r equipment_type_ids=%s",
        normalized_name,
        normalized_placeholder_token,
        normalized_sku_abbreviation,
        normalized_equipment_type_ids,
    )
    try:
        option = DesignOption(
            name=normalized_name,
            description=data.description, 
            option_type=data.option_type,
            is_pricing_relevant=data.is_pricing_relevant,
            sku_abbreviation=normalized_sku_abbreviation,
            ebay_variation_enabled=data.ebay_variation_enabled,
            price_cents=data.price_cents,
            placeholder_token=normalized_placeholder_token
        )
        db.add(option)
        db.flush()

        _sync_equipment_type_design_options_pk_sequence(db)
        for et_id in normalized_equipment_type_ids:
            assoc = EquipmentTypeDesignOption(design_option_id=option.id, equipment_type_id=et_id)
            db.add(assoc)
            
        db.commit()
        db.refresh(option)
        return option
    except IntegrityError as e:
        db.rollback()
        _raise_design_option_integrity_error(e)

@router.put("/{id}", response_model=DesignOptionResponse)
def update_design_option(id: int, data: DesignOptionCreate, db: Session = Depends(get_db)):
    logger.info("design_options.py version marker: %s", DESIGN_OPTIONS_API_VERSION_MARKER)
    option = db.query(DesignOption).filter(DesignOption.id == id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Design option not found")
    normalized_name = _normalize_name(data.name)
    normalized_sku_abbreviation = _normalize_sku_abbreviation(data.sku_abbreviation)
    normalized_placeholder_token = _normalize_placeholder_token(data.placeholder_token)
    normalized_equipment_type_ids = _normalize_equipment_type_ids(data.equipment_type_ids)
    logger.info(
        "DesignOption PUT payload id=%s name=%r placeholder_token=%r sku_abbreviation=%r equipment_type_ids=%s",
        id,
        normalized_name,
        normalized_placeholder_token,
        normalized_sku_abbreviation,
        normalized_equipment_type_ids,
    )
    existing = db.query(DesignOption).filter(
        func.lower(DesignOption.name) == normalized_name.lower(),
        DesignOption.id != id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Design option with this name already exists")
    try:
        option.name = normalized_name
        option.description = data.description
        option.option_type = data.option_type
        option.is_pricing_relevant = data.is_pricing_relevant
        option.sku_abbreviation = normalized_sku_abbreviation
        option.ebay_variation_enabled = data.ebay_variation_enabled
        option.price_cents = data.price_cents
        option.placeholder_token = normalized_placeholder_token
        
        # Update associations
        db.query(EquipmentTypeDesignOption).filter(
            EquipmentTypeDesignOption.design_option_id == id
        ).delete(synchronize_session=False)
        # Flush deletes before re-inserts to avoid PK collisions in the same transaction.
        db.flush()
        _sync_equipment_type_design_options_pk_sequence(db)
        for et_id in normalized_equipment_type_ids:
            assoc = EquipmentTypeDesignOption(design_option_id=id, equipment_type_id=et_id)
            db.add(assoc)

        db.commit()
        db.refresh(option)
        return option
    except IntegrityError as e:
        db.rollback()
        _raise_design_option_integrity_error(e)

@router.delete("/{id}")
def delete_design_option(id: int, db: Session = Depends(get_db)):
    option = db.query(DesignOption).filter(DesignOption.id == id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Design option not found")
    db.query(EquipmentTypeDesignOption).filter(
        EquipmentTypeDesignOption.design_option_id == id
    ).delete()
    db.delete(option)
    db.commit()
    return {"message": "Design option deleted"}
