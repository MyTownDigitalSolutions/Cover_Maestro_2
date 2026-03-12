from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import EbayStoreCategory, EquipmentType, Manufacturer, Series
from app.schemas.core import (
    EbayStoreCategoryCreate,
    EbayStoreCategoryUpdate,
    EbayStoreCategoryResponse,
)


router = APIRouter(prefix="/ebay-store-categories", tags=["eBay Store Categories"])

VALID_LEVELS = {"equipment_type", "manufacturer", "series"}


def _clean_optional_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def _normalize_system(value: Optional[str]) -> str:
    system = (value or "").strip()
    if not system:
        raise HTTPException(status_code=400, detail="system is required")
    return system


def _validate_exists(db: Session, model_cls, obj_id: int, label: str):
    obj = db.query(model_cls).filter(model_cls.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")
    return obj


def _validate_category_state(
    db: Session,
    payload: Dict[str, Any],
    existing_id: Optional[int] = None,
) -> Dict[str, Any]:
    state = dict(payload)
    state["system"] = _normalize_system(state.get("system"))
    state["level"] = (state.get("level") or "").strip()
    state["category_id"] = (state.get("category_id") or "").strip()
    state["category_name"] = _clean_optional_string(state.get("category_name"))

    if state["level"] not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid level")
    if not state["category_id"]:
        raise HTTPException(status_code=400, detail="category_id is required")

    equipment_type_id = state.get("equipment_type_id")
    manufacturer_id = state.get("manufacturer_id")
    series_id = state.get("series_id")
    parent_id = state.get("parent_id")

    if equipment_type_id is None:
        raise HTTPException(status_code=400, detail="equipment_type_id is required")

    _validate_exists(db, EquipmentType, equipment_type_id, "equipment_type_id")

    if state["level"] == "equipment_type":
        if manufacturer_id is not None or series_id is not None:
            raise HTTPException(status_code=400, detail="equipment_type level requires manufacturer_id and series_id to be null")
        if parent_id is not None:
            raise HTTPException(status_code=400, detail="equipment_type level requires parent_id to be null")
    elif state["level"] == "manufacturer":
        if manufacturer_id is None:
            raise HTTPException(status_code=400, detail="manufacturer level requires manufacturer_id")
        if series_id is not None:
            raise HTTPException(status_code=400, detail="manufacturer level requires series_id to be null")
        _validate_exists(db, Manufacturer, manufacturer_id, "manufacturer_id")
    elif state["level"] == "series":
        if series_id is None:
            raise HTTPException(status_code=400, detail="series level requires series_id")
        if manufacturer_id is not None:
            raise HTTPException(status_code=400, detail="series level requires manufacturer_id to be null")
        series_obj = _validate_exists(db, Series, series_id, "series_id")
        state["_series_manufacturer_id"] = series_obj.manufacturer_id

    if parent_id is not None:
        if existing_id is not None and parent_id == existing_id:
            raise HTTPException(status_code=400, detail="parent_id cannot equal id")

        parent = db.query(EbayStoreCategory).filter(EbayStoreCategory.id == parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Invalid parent_id")
        if parent.system != state["system"]:
            raise HTTPException(status_code=400, detail="parent_id must match system")
        if parent.equipment_type_id != equipment_type_id:
            raise HTTPException(status_code=400, detail="parent_id must match equipment_type_id")

        if state["level"] == "manufacturer":
            if parent.level != "equipment_type":
                raise HTTPException(status_code=400, detail="manufacturer level parent must be equipment_type level")
        elif state["level"] == "series":
            if parent.level != "manufacturer":
                raise HTTPException(status_code=400, detail="series level parent must be manufacturer level")
            series_manufacturer_id = state.get("_series_manufacturer_id")
            if series_manufacturer_id is not None and parent.manufacturer_id != series_manufacturer_id:
                raise HTTPException(status_code=400, detail="series parent_id manufacturer does not match series")

    state.pop("_series_manufacturer_id", None)
    return state


@router.get("", response_model=List[EbayStoreCategoryResponse])
@router.get("/", response_model=List[EbayStoreCategoryResponse])
def list_ebay_store_categories(
    system: Optional[str] = None,
    level: Optional[str] = None,
    equipment_type_id: Optional[int] = None,
    manufacturer_id: Optional[int] = None,
    series_id: Optional[int] = None,
    parent_id: Optional[int] = None,
    include_disabled: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(EbayStoreCategory)

    if system is not None:
        query = query.filter(EbayStoreCategory.system == system)
    if level is not None:
        query = query.filter(EbayStoreCategory.level == level)
    if equipment_type_id is not None:
        query = query.filter(EbayStoreCategory.equipment_type_id == equipment_type_id)
    if manufacturer_id is not None:
        query = query.filter(EbayStoreCategory.manufacturer_id == manufacturer_id)
    if series_id is not None:
        query = query.filter(EbayStoreCategory.series_id == series_id)
    if parent_id is not None:
        query = query.filter(EbayStoreCategory.parent_id == parent_id)
    if not include_disabled:
        query = query.filter(EbayStoreCategory.is_enabled == True)  # noqa: E712

    return query.order_by(
        EbayStoreCategory.system.asc(),
        EbayStoreCategory.level.asc(),
        EbayStoreCategory.equipment_type_id.asc(),
        EbayStoreCategory.manufacturer_id.asc(),
        EbayStoreCategory.series_id.asc(),
        EbayStoreCategory.id.asc(),
    ).all()


@router.post("", response_model=EbayStoreCategoryResponse)
@router.post("/", response_model=EbayStoreCategoryResponse)
def create_ebay_store_category(data: EbayStoreCategoryCreate, db: Session = Depends(get_db)):
    payload = _validate_category_state(db, data.dict())
    row = EbayStoreCategory(**payload)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate eBay store category mapping for this scope")
    db.refresh(row)
    return row


@router.put("/{category_id}", response_model=EbayStoreCategoryResponse)
def update_ebay_store_category(
    category_id: int,
    data: EbayStoreCategoryUpdate,
    db: Session = Depends(get_db),
):
    row = db.query(EbayStoreCategory).filter(EbayStoreCategory.id == category_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="eBay store category not found")

    current_state = {
        "system": row.system,
        "level": row.level,
        "equipment_type_id": row.equipment_type_id,
        "manufacturer_id": row.manufacturer_id,
        "series_id": row.series_id,
        "parent_id": row.parent_id,
        "category_id": row.category_id,
        "category_name": row.category_name,
        "store_category_number": row.store_category_number,
        "ebay_category_id": row.ebay_category_id,
        "is_enabled": row.is_enabled,
    }
    incoming = data.dict(exclude_unset=True)
    merged = {**current_state, **incoming}
    validated = _validate_category_state(db, merged, existing_id=row.id)

    for key, value in validated.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate eBay store category mapping for this scope")
    db.refresh(row)
    return row


@router.delete("/{category_id}")
def delete_ebay_store_category(category_id: int, db: Session = Depends(get_db)):
    row = db.query(EbayStoreCategory).filter(EbayStoreCategory.id == category_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="eBay store category not found")

    db.delete(row)
    db.commit()
    return {"message": "Deleted", "id": category_id}
