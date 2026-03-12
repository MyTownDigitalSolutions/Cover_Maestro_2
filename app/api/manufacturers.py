from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from app.database import get_db
from app.models.core import Manufacturer
from app.schemas.core import ManufacturerCreate, ManufacturerResponse

router = APIRouter(prefix="/manufacturers", tags=["manufacturers"])

@router.get("", response_model=List[ManufacturerResponse])
def list_manufacturers(db: Session = Depends(get_db)):
    return db.query(Manufacturer).all()

@router.get("/{id}", response_model=ManufacturerResponse)
def get_manufacturer(id: int, db: Session = Depends(get_db)):
    manufacturer = db.query(Manufacturer).filter(Manufacturer.id == id).first()
    if not manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    return manufacturer

@router.post("", response_model=ManufacturerResponse)
def create_manufacturer(data: ManufacturerCreate, db: Session = Depends(get_db)):
    try:
        manufacturer = Manufacturer(name=data.name)
        db.add(manufacturer)
        db.commit()
        db.refresh(manufacturer)
        return manufacturer
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Manufacturer with this name already exists")

@router.put("/{id}", response_model=ManufacturerResponse)
def update_manufacturer(id: int, data: ManufacturerCreate, db: Session = Depends(get_db)):
    manufacturer = db.query(Manufacturer).filter(Manufacturer.id == id).first()
    if not manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    try:
        manufacturer.name = data.name
        db.commit()
        db.refresh(manufacturer)
        return manufacturer
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Manufacturer with this name already exists")

@router.delete("/{id}")
def delete_manufacturer(id: int, db: Session = Depends(get_db)):
    manufacturer = db.query(Manufacturer).filter(Manufacturer.id == id).first()
    if not manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    db.delete(manufacturer)
    db.commit()
    return {"message": "Manufacturer deleted"}
