from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app.models.core import EquipmentType, EquipmentTypePricingOption, PricingOption, EquipmentTypeDesignOption, DesignOption
from app.schemas.core import EquipmentTypeCreate, EquipmentTypeResponse, PricingOptionResponse, DesignOptionResponse

router = APIRouter(prefix="/equipment-types", tags=["equipment-types"])

class PricingOptionAssignment(BaseModel):
    pricing_option_ids: List[int]

class DesignOptionAssignment(BaseModel):
    design_option_ids: List[int]

@router.get("", response_model=List[EquipmentTypeResponse])
def list_equipment_types(db: Session = Depends(get_db)):
    return db.query(EquipmentType).options(
        joinedload(EquipmentType.amazon_customization_template),
        joinedload(EquipmentType.reverb_template)
    ).all()

@router.get("/{id}", response_model=EquipmentTypeResponse)
def get_equipment_type(id: int, db: Session = Depends(get_db)):
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    return equipment_type

@router.post("", response_model=EquipmentTypeResponse)
def create_equipment_type(data: EquipmentTypeCreate, db: Session = Depends(get_db)):
    try:
        equipment_type = EquipmentType(name=data.name)
        db.add(equipment_type)
        db.commit()
        db.refresh(equipment_type)
        return equipment_type
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Equipment type with this name already exists")

@router.put("/{id}", response_model=EquipmentTypeResponse)
def update_equipment_type(id: int, data: EquipmentTypeCreate, db: Session = Depends(get_db)):
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    try:
        equipment_type.name = data.name
        db.commit()
        db.refresh(equipment_type)
        return equipment_type
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Equipment type with this name already exists")

@router.delete("/{id}")
def delete_equipment_type(id: int, db: Session = Depends(get_db)):
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    db.delete(equipment_type)
    db.commit()
    return {"message": "Equipment type deleted"}

@router.get("/{id}/pricing-options", response_model=List[PricingOptionResponse])
def get_equipment_type_pricing_options(id: int, db: Session = Depends(get_db)):
    """Get all pricing options assigned to an equipment type."""
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    
    assignments = db.query(EquipmentTypePricingOption).filter(
        EquipmentTypePricingOption.equipment_type_id == id
    ).all()
    
    option_ids = [a.pricing_option_id for a in assignments]
    if not option_ids:
        return []
    
    return db.query(PricingOption).filter(PricingOption.id.in_(option_ids)).all()

@router.put("/{id}/pricing-options")
def set_equipment_type_pricing_options(id: int, data: PricingOptionAssignment, db: Session = Depends(get_db)):
    """Set the pricing options for an equipment type (replaces existing assignments)."""
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    
    for option_id in data.pricing_option_ids:
        option = db.query(PricingOption).filter(PricingOption.id == option_id).first()
        if not option:
            raise HTTPException(status_code=404, detail=f"Pricing option {option_id} not found")
    
    try:
        db.query(EquipmentTypePricingOption).filter(
            EquipmentTypePricingOption.equipment_type_id == id
        ).delete()
        
        for option_id in data.pricing_option_ids:
            assignment = EquipmentTypePricingOption(
                equipment_type_id=id,
                pricing_option_id=option_id
            )
            db.add(assignment)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update pricing options: {str(e)}")
    
    return {"message": "Pricing options updated"}

@router.get("/{id}/design-options", response_model=List[DesignOptionResponse])
def get_equipment_type_design_options(id: int, db: Session = Depends(get_db)):
    """Get all design options assigned to an equipment type."""
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    
    assignments = db.query(EquipmentTypeDesignOption).filter(
        EquipmentTypeDesignOption.equipment_type_id == id
    ).all()
    
    option_ids = [a.design_option_id for a in assignments]
    if not option_ids:
        return []
    
    return db.query(DesignOption).filter(DesignOption.id.in_(option_ids)).all()

@router.put("/{id}/design-options")
def set_equipment_type_design_options(id: int, data: DesignOptionAssignment, db: Session = Depends(get_db)):
    """Set the design options for an equipment type (replaces existing assignments)."""
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    
    for option_id in data.design_option_ids:
        option = db.query(DesignOption).filter(DesignOption.id == option_id).first()
        if not option:
            raise HTTPException(status_code=404, detail=f"Design option {option_id} not found")
    
    try:
        db.query(EquipmentTypeDesignOption).filter(
            EquipmentTypeDesignOption.equipment_type_id == id
        ).delete()
        
        for option_id in data.design_option_ids:
            assignment = EquipmentTypeDesignOption(
                equipment_type_id=id,
                design_option_id=option_id
            )
            db.add(assignment)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update design options: {str(e)}")
    
    return {"message": "Design options updated"}
