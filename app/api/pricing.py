from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from app.database import get_db
from app.models.core import PricingOption, ShippingRate, EquipmentType, EquipmentTypePricingOption
from app.schemas.core import (
    PricingOptionCreate, PricingOptionResponse,
    ShippingRateCreate, ShippingRateResponse,
    PricingOptionCreate, PricingOptionResponse,
    ShippingRateCreate, ShippingRateResponse,
    PricingCalculateRequest, PricingCalculateResponse,
    PricingRecalculateBulkRequest, PricingRecalculateBulkResponse, PricingRecalculateResult
)
from app.services.pricing_service import PricingService
from app.services.pricing_calculator import PricingCalculator, PricingConfigError
from app.models.core import Model, Series, ModelPricingSnapshot, ShippingDefaultSetting
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

# New Schemas for Targeted Recalc
class PricingRecalculateRequest(BaseModel):
    all: bool = False
    manufacturer_id: Optional[int] = None
    series_id: Optional[int] = None
    model_ids: Optional[List[int]] = None
    only_if_stale: bool = True

class PricingRecalculateResponse(BaseModel):
    requested_models: int
    evaluated_models: int
    recalculated_models: int
    skipped_models: int
    skipped_not_stale: int
    errors: List[Dict[str, str | int]] = Field(default_factory=list)

class PricingSnapshotStatusRequest(BaseModel):
    model_ids: List[int]
    marketplace: str = "amazon"

class PricingSnapshotStatusResponse(BaseModel):
    missing_snapshots: Dict[int, List[str]]
    complete: bool

router = APIRouter(prefix="/pricing", tags=["pricing"])

@router.post("/calculate", response_model=PricingCalculateResponse)
def calculate_pricing(data: PricingCalculateRequest, db: Session = Depends(get_db)):
    try:
        service = PricingService(db)
        result = service.calculate_total(
            model_id=data.model_id,
            material_id=data.material_id,
            colour=data.colour,
            quantity=data.quantity,
            handle_zipper=data.handle_zipper,
            two_in_one_pocket=data.two_in_one_pocket,
            music_rest_zipper=data.music_rest_zipper,
            carrier=data.carrier,
            zone=data.zone
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PricingConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/recalculate", response_model=PricingRecalculateResponse)
def recalculate_targeted(data: PricingRecalculateRequest, db: Session = Depends(get_db)):
    def classify_recalc_error(message: str) -> str:
        msg = (message or "").lower()
        if "missing active material assignment for role" in msg:
            return "MISSING_MATERIAL_ROLE_ASSIGNMENT"
        if "surface_area_sq_in" in msg or "dimensions" in msg:
            return "MISSING_DIMENSIONS"
        if "fee rate not configured" in msg:
            return "MISSING_MARKETPLACE_FEE_RATE"
        if "shipping profile not configured" in msg:
            return "MISSING_SHIPPING_PROFILE"
        if "fixed cell" in msg or "assumed tier" in msg or "assumed zone" in msg:
            return "MISSING_FIXED_CELL_RATE"
        if "profit config missing" in msg:
            return "MISSING_VARIANT_PROFIT"
        if "labor settings not configured" in msg:
            return "MISSING_LABOR_SETTINGS"
        if "no preferred supplier found" in msg:
            return "MISSING_PREFERRED_SUPPLIER"
        return "PRICING_CONFIG_ERROR"

    # 1. Validate Target Mode
    modes = [
        data.all,
        data.manufacturer_id is not None,
        data.series_id is not None,
        data.model_ids is not None
    ]
    if sum(modes) != 1:
        raise HTTPException(status_code=400, detail="Must provide exactly ONE targeting mode: all, manufacturer_id, series_id, or model_ids")
        
    # 2. Resolve Model IDs
    target_ids = []
    
    if data.all:
        target_ids = [m.id for m in db.query(Model.id).all()]
    elif data.manufacturer_id:
        target_ids = [m.id for m in db.query(Model.id).join(Series).filter(Series.manufacturer_id == data.manufacturer_id).all()]
    elif data.series_id:
        target_ids = [m.id for m in db.query(Model.id).filter(Model.series_id == data.series_id).all()]
    elif data.model_ids:
        target_ids = data.model_ids

    if not target_ids:
        return PricingRecalculateResponse(
            requested_models=0,
            evaluated_models=0,
            recalculated_models=0,
            skipped_models=0,
            skipped_not_stale=0,
            errors=[],
        )
        
    # 3. Filter if Stale
    ids_to_process = []
    
    if data.only_if_stale:
        # Get current version
        defaults = db.query(ShippingDefaultSetting).first()
        current_ver = defaults.shipping_settings_version if defaults else 1
        
        # We need to find models where ANY variant snapshot is stale.
        # Stale = snapshot missing OR snapshot.version != current_ver
        
        # Strategy:
        # A. Get all snapshots for these models
        # B. Check logic in python (easier than complex SQL for "any variant stale" grouping)
        
        # Optimize: Query models that HAVE a stale snapshot.
        # But we also need models that have NO snapshot.
        
        # Let's verify existing snapshots
        # select distinct model_id from snapshots where version != current or version is null
        stale_snapshots_q = db.query(ModelPricingSnapshot.model_id).filter(
            ModelPricingSnapshot.model_id.in_(target_ids),
            (ModelPricingSnapshot.shipping_settings_version_used == None) | 
            (ModelPricingSnapshot.shipping_settings_version_used != current_ver)
        ).distinct()
        stale_model_ids = {r[0] for r in stale_snapshots_q.all()}
        
        # For models with NO snapshots, they won't appear above.
        # But they are "stale" (never calculated).
        # Find who has snapshots?
        existing_snapshot_owners_q = db.query(ModelPricingSnapshot.model_id).filter(
            ModelPricingSnapshot.model_id.in_(target_ids)
        ).distinct()
        existing_owners = {r[0] for r in existing_snapshot_owners_q.all()}
        
        models_without_snapshots = set(target_ids) - existing_owners
        
        ids_to_process = list(stale_model_ids.union(models_without_snapshots))
        
    else:
        ids_to_process = target_ids

    # 4. Calculate
    recalculated_count = 0
    skipped_count = 0
    errors: List[Dict[str, str | int]] = []
    
    marketplaces = ["amazon", "reverb", "ebay", "etsy"] # Explicit list of supported marketplaces

    for mid in ids_to_process:
        model_success = False
        model_errors: List[Dict[str, str | int]] = []
        # Calculate each marketplace independently so one failure doesn't block others
        for mp in marketplaces:
            try:
                with db.begin_nested():
                    PricingCalculator(db).calculate_model_prices(mid, marketplace=mp)
                model_success = True
            except ValueError as e:
                model_errors.append({
                    "model_id": mid,
                    "marketplace": mp,
                    "code": classify_recalc_error(str(e)),
                    "message": str(e),
                })
            except PricingConfigError as e:
                model_errors.append({
                    "model_id": mid,
                    "marketplace": mp,
                    "code": classify_recalc_error(str(e)),
                    "message": str(e),
                })
            except Exception as e:
                print(f"Failed to recalc model {mid} for {mp}: {e}")
                model_errors.append({
                    "model_id": mid,
                    "marketplace": mp,
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                })
        
        if model_success:
            # If at least one marketplace succeeded, we consider the model processed/committed
            try:
                db.commit()
                recalculated_count += 1
            except Exception as e:
                print(f"Failed to commit model {mid}: {e}")
                db.rollback()
                skipped_count += 1
                errors.append({
                    "model_id": mid,
                    "marketplace": "all",
                    "code": "COMMIT_FAILED",
                    "message": str(e),
                })
            errors.extend(model_errors)
        else:
            skipped_count += 1
            errors.extend(model_errors)

    return PricingRecalculateResponse(
        requested_models=len(target_ids),
        evaluated_models=len(target_ids),
        recalculated_models=recalculated_count,
        skipped_models=skipped_count,
        skipped_not_stale=len(target_ids) - len(ids_to_process),
        errors=errors,
    )

@router.post("/snapshots/status", response_model=PricingSnapshotStatusResponse)
def check_snapshot_status(data: PricingSnapshotStatusRequest, db: Session = Depends(get_db)):
    logger.info("[SNAPSHOTS-STATUS] Checking %s models for marketplace %s", len(data.model_ids), data.marketplace)
    missing = {}
    required_variants = {
        "choice_no_padding", "choice_padded",
        "premium_no_padding", "premium_padded"
    }
    
    snapshots = db.query(ModelPricingSnapshot.model_id, ModelPricingSnapshot.variant_key).filter(
        ModelPricingSnapshot.model_id.in_(data.model_ids),
        ModelPricingSnapshot.marketplace == data.marketplace
    ).all()
    
    found_map = {}
    for mid, vkey in snapshots:
        if mid not in found_map:
            found_map[mid] = set()
        found_map[mid].add(vkey)
        
    for mid in data.model_ids:
        found = found_map.get(mid, set())
        missing_variants = required_variants - found
        if missing_variants:
            missing[mid] = list(missing_variants)
            
    return PricingSnapshotStatusResponse(
        missing_snapshots=missing,
        complete=len(missing) == 0
    )

@router.get("/options", response_model=List[PricingOptionResponse])
def list_pricing_options(db: Session = Depends(get_db)):
    return db.query(PricingOption).all()

@router.get("/options/{id}", response_model=PricingOptionResponse)
def get_pricing_option(id: int, db: Session = Depends(get_db)):
    option = db.query(PricingOption).filter(PricingOption.id == id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Pricing option not found")
    return option

@router.post("/options", response_model=PricingOptionResponse)
def create_pricing_option(data: PricingOptionCreate, db: Session = Depends(get_db)):
    try:
        option = PricingOption(
            name=data.name,
            price=data.price,
            sku_abbreviation=data.sku_abbreviation,
            ebay_variation_enabled=data.ebay_variation_enabled,
            linked_design_option_id=data.linked_design_option_id
        )
        db.add(option)
        db.commit()
        db.refresh(option)
        return option
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Pricing option with this name already exists")

@router.put("/options/{id}", response_model=PricingOptionResponse)
def update_pricing_option(id: int, data: PricingOptionCreate, db: Session = Depends(get_db)):
    option = db.query(PricingOption).filter(PricingOption.id == id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Pricing option not found")
    try:
        option.name = data.name
        option.price = data.price
        option.sku_abbreviation = data.sku_abbreviation
        option.ebay_variation_enabled = data.ebay_variation_enabled
        option.linked_design_option_id = data.linked_design_option_id
        db.commit()
        db.refresh(option)
        return option
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Pricing option with this name already exists")

@router.delete("/options/{id}")
def delete_pricing_option(id: int, db: Session = Depends(get_db)):
    option = db.query(PricingOption).filter(PricingOption.id == id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Pricing option not found")
    db.delete(option)
    db.commit()
    return {"message": "Pricing option deleted"}

@router.get("/options/by-equipment-type/{equipment_type_id}", response_model=List[PricingOptionResponse])
def get_options_for_equipment_type(equipment_type_id: int, db: Session = Depends(get_db)):
    """Get all pricing options assigned to a specific equipment type."""
    equipment_type = db.query(EquipmentType).filter(EquipmentType.id == equipment_type_id).first()
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Equipment type not found")
    
    option_ids = db.query(EquipmentTypePricingOption.pricing_option_id).filter(
        EquipmentTypePricingOption.equipment_type_id == equipment_type_id
    ).all()
    option_ids = [o[0] for o in option_ids]
    
    if not option_ids:
        return []
    
    return db.query(PricingOption).filter(PricingOption.id.in_(option_ids)).all()

@router.get("/shipping-rates", response_model=List[ShippingRateResponse])
def list_shipping_rates(db: Session = Depends(get_db)):
    return db.query(ShippingRate).all()

@router.post("/shipping-rates", response_model=ShippingRateResponse)
def create_shipping_rate(data: ShippingRateCreate, db: Session = Depends(get_db)):
    rate = ShippingRate(
        carrier=data.carrier,
        min_weight=data.min_weight,
        max_weight=data.max_weight,
        zone=data.zone,
        rate=data.rate,
        surcharge=data.surcharge
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate

@router.post("/recalculate/bulk", response_model=PricingRecalculateBulkResponse)
def recalculate_bulk(data: PricingRecalculateBulkRequest, db: Session = Depends(get_db)):
    """
    Recalculate pricing for a scoped set of models.
    Scope: manufacturer | series | models
    Marketplaces: currently defaults to ["amazon"]
    Variant Set: currently only "baseline4" supported (implied/strict)
    """
    
    # 1. Resolve Models
    models_to_process = []
    
    if data.scope == "models":
        if not data.model_ids:
            # If empty list, do nothing? Or error? Let's assume empty list is valid but results in 0
            if data.model_ids is None:
                 raise HTTPException(status_code=400, detail="model_ids required for 'models' scope")
        
        models_to_process = db.query(Model).filter(Model.id.in_(data.model_ids)).all()

    elif data.scope == "series":
        if not data.manufacturer_id or not data.series_id:
            raise HTTPException(status_code=400, detail="manufacturer_id and series_id required for 'series' scope")
        
        # Verify valid series
        series = db.query(Series).filter(
            Series.id == data.series_id, 
            Series.manufacturer_id == data.manufacturer_id
        ).first()
        if not series:
             raise HTTPException(status_code=404, detail="Series not found or does not belong to Manufacturer")
             
        models_to_process = db.query(Model).filter(Model.series_id == data.series_id).all()

    elif data.scope == "manufacturer":
        if not data.manufacturer_id:
             raise HTTPException(status_code=400, detail="manufacturer_id required for 'manufacturer' scope")
        
        # Determine all series for manufacturer, then all models
        # Or join
        models_to_process = db.query(Model).join(Series).filter(
            Series.manufacturer_id == data.manufacturer_id
        ).all()
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {data.scope}")

    # 2. Results Container
    results_map = {}
    
    marketplaces = data.marketplaces if data.marketplaces else ["amazon"]
    
    for mp in marketplaces:
        results_map[mp] = {
            "succeeded": [],
            "failed": []
        }
        
    # 3. Processing Loop
    processed_count = 0
    
    if data.dry_run:
        # Just return count
        return PricingRecalculateBulkResponse(
            marketplaces=marketplaces,
            scope=data.scope,
            resolved_model_count=len(models_to_process),
            results=results_map
        )
        
    for model in models_to_process:
        processed_count += 1
        for mp in marketplaces:
            try:
                # Use PricingCalculator
                # This commits internally? No, check models.py: db.commit() is OUTSIDE calculator.
                # models.py: PricingCalculator(db).calculate_model_prices(...) -> db.commit()
                # calculator.py has self.db.flush() but NO commit.
                
                # We should catch per model, rollback per model if needed?
                # But we share a session 'db'. If we rollback, we lose everything?
                # Standard pattern: nested transaction or savepoint?
                # SQLAlchemy: db.begin_nested()
                
                with db.begin_nested():
                     PricingCalculator(db).calculate_model_prices(model.id, marketplace=mp)
                
                results_map[mp]["succeeded"].append(model.id)
                
            except PricingConfigError as e:
                 results_map[mp]["failed"].append(
                    PricingRecalculateResult(model_id=model.id, error=str(e))
                )
            except Exception as e:
                # Capture error
                results_map[mp]["failed"].append(
                    PricingRecalculateResult(model_id=model.id, error=str(e))
                )
    
    # Final Commit (persists successful nested transactions)
    # Failed nested transactions were rolled back when context exited with exception?
    # Wait, begin_nested() rollback logic depends on usage.
    # If using context manager, it rollbacks on exception automatically.
    
    try:
        db.commit()
    except Exception as e:
        # If commit fails (rare here due to flush?), fail specific items? 
        # Hard to map back.
        # But if we used nested, we should be okay.
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Global commit failed: {str(e)}")

    return PricingRecalculateBulkResponse(
        marketplaces=marketplaces,
        scope=data.scope,
        resolved_model_count=len(models_to_process),
        results=results_map
    )
