from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict, List, Set
from datetime import datetime
from app.database import get_db
from app.models.core import (
    Material,
    Color,
    MaterialColor,
    MaterialColourSurcharge,
    SupplierMaterial,
    Supplier,
    MaterialRoleAssignment,
    MaterialRoleConfig,
    EbayVariationPresetAsset,
)
from app.schemas.core import (
    MaterialCreate, MaterialResponse,
    MaterialColorAssignmentCreate, MaterialColorAssignmentUpdate, MaterialColorAssignmentResponse,
    MaterialColourSurchargeCreate, MaterialColourSurchargeResponse,
    SupplierMaterialWithSupplierResponse, SetPreferredSupplierRequest
)

router = APIRouter(prefix="/materials", tags=["materials"])


def _normalize_role_key(value: str | None) -> str:
    return (value or "").replace("\u00A0", " ").replace("_", " ").strip().lower()


def _dedupe_ints(values: List[int]) -> List[int]:
    seen: Set[int] = set()
    out: List[int] = []
    for raw in values:
        try:
            num = int(raw)
        except (TypeError, ValueError):
            continue
        if num in seen:
            continue
        seen.add(num)
        out.append(num)
    return out


def _sync_ebay_preset_color_membership(
    db: Session,
    *,
    material_id: int,
    surcharge_id: int,
    should_include: bool,
) -> None:
    now = datetime.utcnow()
    active_assignments = (
        db.query(MaterialRoleAssignment)
        .filter(
            MaterialRoleAssignment.material_id == material_id,
            (MaterialRoleAssignment.end_date.is_(None)) | (MaterialRoleAssignment.end_date > now),
        )
        .all()
    )
    if not active_assignments:
        return

    ebay_enabled_role_norms = {
        _normalize_role_key(row.role)
        for row in (
            db.query(MaterialRoleConfig)
            .filter(MaterialRoleConfig.ebay_variation_enabled == True)  # noqa: E712
            .all()
        )
    }
    assigned_role_norms = {_normalize_role_key(row.role) for row in active_assignments}
    relevant_role_norms = {
        role_norm for role_norm in assigned_role_norms if role_norm and role_norm in ebay_enabled_role_norms
    }
    if not relevant_role_norms:
        return

    presets = (
        db.query(EbayVariationPresetAsset)
        .filter(EbayVariationPresetAsset.marketplace == "EBAY")
        .all()
    )
    for preset in presets:
        payload_raw = preset.payload if isinstance(preset.payload, dict) else {}
        payload: Dict[str, Any] = dict(payload_raw)
        preset_role_keys = payload.get("role_keys") or []
        preset_role_norms = {
            _normalize_role_key(str(role_key))
            for role_key in preset_role_keys
            if str(role_key or "").strip()
        }
        if not (preset_role_norms & relevant_role_norms):
            continue

        current_color_ids = _dedupe_ints(list(payload.get("color_surcharge_ids") or []))
        if should_include:
            if surcharge_id in current_color_ids:
                continue
            current_color_ids.append(int(surcharge_id))
            payload["color_surcharge_ids"] = _dedupe_ints(current_color_ids)
            preset.payload = payload
        else:
            if surcharge_id not in current_color_ids:
                continue
            payload["color_surcharge_ids"] = [cid for cid in current_color_ids if cid != int(surcharge_id)]
            preset.payload = payload

@router.get("", response_model=List[MaterialResponse])
def list_materials(db: Session = Depends(get_db)):
    return db.query(Material).all()

@router.get("/{id}", response_model=MaterialResponse)
def get_material(id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material

@router.post("", response_model=MaterialResponse)
def create_material(data: MaterialCreate, db: Session = Depends(get_db)):
    try:
        material = Material(
            name=data.name,
            base_color=data.base_color,
            material_type=data.material_type,
            linear_yard_width=data.linear_yard_width,
            weight_per_linear_yard=data.weight_per_linear_yard,
            unit_of_measure=data.unit_of_measure,
            package_quantity=data.package_quantity,
            sku_abbreviation=data.sku_abbreviation,
            ebay_variation_enabled=data.ebay_variation_enabled
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        return material
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Material with this name already exists")

@router.put("/{id}", response_model=MaterialResponse)
def update_material(id: int, data: MaterialCreate, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    try:
        material.name = data.name
        material.base_color = data.base_color
        material.material_type = data.material_type
        material.linear_yard_width = data.linear_yard_width
        material.weight_per_linear_yard = data.weight_per_linear_yard
        material.unit_of_measure = data.unit_of_measure
        material.package_quantity = data.package_quantity
        material.sku_abbreviation = data.sku_abbreviation
        material.ebay_variation_enabled = data.ebay_variation_enabled
        db.commit()
        db.refresh(material)
        return material
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Material with this name already exists")

@router.delete("/{id}")
def delete_material(id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    try:
        db.delete(material)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete material because it is referenced by other records (e.g. orders)."
        )
    return {"message": "Material deleted"}

@router.get("/{id}/color-assignments", response_model=List[MaterialColorAssignmentResponse])
def list_material_color_assignments(id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return (
        db.query(MaterialColor)
        .options(joinedload(MaterialColor.color))
        .filter(MaterialColor.material_id == id)
        .order_by(
            MaterialColor.sort_order.is_(None).asc(),
            MaterialColor.sort_order.asc(),
            MaterialColor.id.asc(),
        )
        .all()
    )

@router.post("/color-assignments", response_model=MaterialColorAssignmentResponse)
def create_material_color_assignment(data: MaterialColorAssignmentCreate, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == data.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    color = db.query(Color).filter(Color.id == data.color_id).first()
    if not color:
        raise HTTPException(status_code=404, detail="Color not found")

    existing = (
        db.query(MaterialColor)
        .filter(
            MaterialColor.material_id == data.material_id,
            MaterialColor.color_id == data.color_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This color is already assigned to the material")

    assignment = MaterialColor(
        material_id=data.material_id,
        color_id=data.color_id,
        surcharge=data.surcharge,
        ebay_variation_enabled=data.ebay_variation_enabled,
        sort_order=data.sort_order,
    )

    try:
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        assignment = (
            db.query(MaterialColor)
            .options(joinedload(MaterialColor.color))
            .filter(MaterialColor.id == assignment.id)
            .first()
        )
        return assignment
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="This color is already assigned to the material")

@router.patch("/color-assignments/{id}", response_model=MaterialColorAssignmentResponse)
def update_material_color_assignment(id: int, data: MaterialColorAssignmentUpdate, db: Session = Depends(get_db)):
    assignment = (
        db.query(MaterialColor)
        .options(joinedload(MaterialColor.color))
        .filter(MaterialColor.id == id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Material color assignment not found")

    update_data = data.model_dump(exclude_unset=True)
    if "surcharge" in update_data:
        assignment.surcharge = update_data["surcharge"]
    if "ebay_variation_enabled" in update_data:
        assignment.ebay_variation_enabled = bool(update_data["ebay_variation_enabled"])
    if "sort_order" in update_data:
        assignment.sort_order = update_data["sort_order"]

    db.commit()
    db.refresh(assignment)
    assignment = (
        db.query(MaterialColor)
        .options(joinedload(MaterialColor.color))
        .filter(MaterialColor.id == assignment.id)
        .first()
    )
    return assignment

@router.delete("/color-assignments/{id}")
def delete_material_color_assignment(id: int, db: Session = Depends(get_db)):
    assignment = db.query(MaterialColor).filter(MaterialColor.id == id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Material color assignment not found")

    db.delete(assignment)
    db.commit()
    return {"message": "Material color assignment removed"}

@router.get("/{id}/surcharges", response_model=List[MaterialColourSurchargeResponse])
def list_material_surcharges(id: int, db: Session = Depends(get_db)):
    return db.query(MaterialColourSurcharge).filter(MaterialColourSurcharge.material_id == id).all()

@router.post("/surcharges", response_model=MaterialColourSurchargeResponse)
def create_surcharge(data: MaterialColourSurchargeCreate, db: Session = Depends(get_db)):
    surcharge = MaterialColourSurcharge(
        material_id=data.material_id,
        colour=data.colour,
        surcharge=data.surcharge,
        color_friendly_name=data.color_friendly_name,
        sku_abbreviation=data.sku_abbreviation,
        ebay_variation_enabled=data.ebay_variation_enabled
    )
    db.add(surcharge)
    db.flush()
    if surcharge.ebay_variation_enabled:
        _sync_ebay_preset_color_membership(
            db,
            material_id=int(surcharge.material_id),
            surcharge_id=int(surcharge.id),
            should_include=True,
        )
    db.commit()
    db.refresh(surcharge)
    return surcharge

@router.put("/surcharges/{id}", response_model=MaterialColourSurchargeResponse)
def update_surcharge(id: int, data: MaterialColourSurchargeCreate, db: Session = Depends(get_db)):
    surcharge = db.query(MaterialColourSurcharge).filter(MaterialColourSurcharge.id == id).first()
    if not surcharge:
        raise HTTPException(status_code=404, detail="Surcharge not found")
    was_ebay_enabled = bool(surcharge.ebay_variation_enabled)
    
    # Check for duplicate colour name within the same material, excluding current record
    existing = db.query(MaterialColourSurcharge).filter(
        MaterialColourSurcharge.material_id == surcharge.material_id,
        MaterialColourSurcharge.colour == data.colour,
        MaterialColourSurcharge.id != id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Color '{data.colour}' already exists for this material"
        )

    surcharge.colour = data.colour
    surcharge.surcharge = data.surcharge
    surcharge.color_friendly_name = data.color_friendly_name
    surcharge.sku_abbreviation = data.sku_abbreviation
    surcharge.ebay_variation_enabled = data.ebay_variation_enabled
    is_ebay_enabled = bool(surcharge.ebay_variation_enabled)
    if (not was_ebay_enabled) and is_ebay_enabled:
        _sync_ebay_preset_color_membership(
            db,
            material_id=int(surcharge.material_id),
            surcharge_id=int(surcharge.id),
            should_include=True,
        )
    elif was_ebay_enabled and (not is_ebay_enabled):
        _sync_ebay_preset_color_membership(
            db,
            material_id=int(surcharge.material_id),
            surcharge_id=int(surcharge.id),
            should_include=False,
        )

    db.commit()
    db.refresh(surcharge)
    return surcharge

@router.get("/{id}/suppliers", response_model=List[SupplierMaterialWithSupplierResponse])
def list_material_suppliers(id: int, db: Session = Depends(get_db)):
    """Get all suppliers who provide this material with their pricing."""
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    supplier_materials = db.query(SupplierMaterial).filter(
        SupplierMaterial.material_id == id
    ).all()
    
    result = []
    for sm in supplier_materials:
        supplier = db.query(Supplier).filter(Supplier.id == sm.supplier_id).first()
        qty = sm.quantity_purchased or 1.0
        shipping = sm.shipping_cost or 0.0
        unit = sm.unit_cost
        
        cost_per_linear_yard = unit + (shipping / qty) if qty > 0 else unit
        linear_yard_width = material.linear_yard_width or 54.0
        linear_yard_area = linear_yard_width * 36
        cost_per_square_inch = cost_per_linear_yard / linear_yard_area if linear_yard_area > 0 else 0
        
        result.append(SupplierMaterialWithSupplierResponse(
            id=sm.id,
            supplier_id=sm.supplier_id,
            material_id=sm.material_id,
            unit_cost=unit,
            shipping_cost=shipping,
            quantity_purchased=qty,
            is_preferred=sm.is_preferred or False,
            supplier_name=supplier.name if supplier else "Unknown",
            material_type=material.material_type,
            cost_per_linear_yard=cost_per_linear_yard,
            cost_per_square_inch=cost_per_square_inch
        ))
    return result

@router.patch("/{id}/set-preferred-supplier")
def set_preferred_supplier(id: int, data: SetPreferredSupplierRequest, db: Session = Depends(get_db)):
    """Set a supplier as the preferred source for this material.
    Toggles all other suppliers for this material to is_preferred=False.
    """
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    target_link = db.query(SupplierMaterial).filter(
        SupplierMaterial.material_id == id,
        SupplierMaterial.supplier_id == data.supplier_id
    ).first()
    
    if not target_link:
        raise HTTPException(
            status_code=404, 
            detail="This supplier is not linked to this material"
        )
    
    db.query(SupplierMaterial).filter(
        SupplierMaterial.material_id == id
    ).update({"is_preferred": False})
    
    target_link.is_preferred = True
    db.commit()
    
    return {"message": f"Supplier set as preferred for {material.name}"}

@router.get("/{id}/preferred-supplier")
def get_preferred_supplier(id: int, db: Session = Depends(get_db)):
    """Get the preferred supplier for this material."""
    preferred = db.query(SupplierMaterial).filter(
        SupplierMaterial.material_id == id,
        SupplierMaterial.is_preferred == True
    ).first()
    
    if not preferred:
        return {"preferred_supplier": None, "unit_cost": None, "shipping_cost": None}
    
    supplier = db.query(Supplier).filter(Supplier.id == preferred.supplier_id).first()
    return {
        "preferred_supplier": supplier.name if supplier else None,
        "supplier_id": preferred.supplier_id,
        "unit_cost": preferred.unit_cost,
        "shipping_cost": preferred.shipping_cost or 0.0
    }
