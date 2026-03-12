from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Color
from app.schemas.core import ColorCreate, ColorResponse, ColorUpdate


router = APIRouter(prefix="/colors", tags=["colors"])


def _validate_required_string(value: str | None, field_name: str) -> str:
    if value is None or str(value).strip() == "":
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    return str(value)


@router.get("", response_model=list[ColorResponse])
def list_colors(db: Session = Depends(get_db)):
    return db.query(Color).order_by(Color.friendly_name.asc(), Color.id.asc()).all()


@router.get("/{id}", response_model=ColorResponse)
def get_color(id: int, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == id).first()
    if not color:
        raise HTTPException(status_code=404, detail="Color not found")
    return color


@router.post("", response_model=ColorResponse)
def create_color(data: ColorCreate, db: Session = Depends(get_db)):
    internal_name = _validate_required_string(data.internal_name, "internal_name")
    friendly_name = _validate_required_string(data.friendly_name, "friendly_name")
    sku_abbrev = _validate_required_string(data.sku_abbrev, "sku_abbrev")

    duplicate = db.query(Color).filter(Color.internal_name == internal_name).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="Color with this internal_name already exists")

    color = Color(
        internal_name=internal_name,
        friendly_name=friendly_name,
        sku_abbrev=sku_abbrev,
        is_active=bool(data.is_active),
    )
    try:
        db.add(color)
        db.commit()
        db.refresh(color)
        return color
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Color with this internal_name already exists")


@router.patch("/{id}", response_model=ColorResponse)
def update_color(id: int, data: ColorUpdate, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == id).first()
    if not color:
        raise HTTPException(status_code=404, detail="Color not found")

    update_data = data.model_dump(exclude_unset=True)
    if "internal_name" in update_data:
        internal_name = _validate_required_string(update_data.get("internal_name"), "internal_name")
        duplicate = (
            db.query(Color)
            .filter(Color.internal_name == internal_name, Color.id != id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Color with this internal_name already exists")
        color.internal_name = internal_name
    if "friendly_name" in update_data:
        color.friendly_name = _validate_required_string(update_data.get("friendly_name"), "friendly_name")
    if "sku_abbrev" in update_data:
        color.sku_abbrev = _validate_required_string(update_data.get("sku_abbrev"), "sku_abbrev")
    if "is_active" in update_data:
        color.is_active = bool(update_data.get("is_active"))

    try:
        db.commit()
        db.refresh(color)
        return color
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Color with this internal_name already exists")
