from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime
import traceback
from app.utils.normalization import normalize_marketplace, normalize_identifier
from app.database import get_db
from app.models.core import (
    Model,
    Series,
    Manufacturer,
    ModelPricingSnapshot,
    ModelPricingHistory,
    DesignOption,
    MarketplaceListing,
    ModelAmazonAPlusContent,
    ModelVariationSKU,
    OrderLine,
)
from app.schemas.core import ModelCreate, ModelResponse, ModelPricingSnapshotResponse, ModelPricingHistoryResponse, MarketplaceListingCreate
from app.schemas.pricing_diff import PricingDiffResponse

from app.services.pricing_calculator import PricingCalculator
from app.services.pricing_diff_service import PricingDiffService

router = APIRouter(prefix="/models", tags=["models"])

WASTE_FACTOR = 0.05

def calculate_surface_area(width: float, depth: float, height: float) -> float:
    """
    Calculate surface area in square inches including waste factor.
    Formula: 2 * (width*depth + width*height + depth*height) * (1 + WASTE_FACTOR)
    """
    base_area = 2 * (width * depth + width * height + depth * height)
    return base_area * (1 + WASTE_FACTOR)

def generate_parent_sku(manufacturer_name: str, series_name: str, model_name: str, version: str = "V1") -> str:
    """
    Generate a 40-character parent SKU.
    Format: MFGR(8)-SERIES(8)-MODEL(13)V1 + zeros
    Multi-word names are concatenated and camelCased.
    """
    def process_name(name: str, max_len: int, pad_char: str = "X") -> str:
        # Split by spaces and camelCase each word
        words = name.split()
        if len(words) > 1:
            # CamelCase: capitalize first letter of each word
            result = "".join(word.capitalize() for word in words)
        else:
            result = name.capitalize()
        
        # Remove any non-alphanumeric characters
        result = "".join(c for c in result if c.isalnum())
        
        # Truncate to max length
        result = result[:max_len].upper()
        
        # Pad with pad_char if shorter than max_len
        result = result.ljust(max_len, pad_char)
        
        return result
    
    # Process each part
    mfgr_part = process_name(manufacturer_name, 8)  # 8 chars
    series_part = process_name(series_name, 8)      # 8 chars
    model_part = process_name(model_name, 13)       # 13 chars
    
    # Ensure version is 2 chars
    version_part = version[:2].upper()
    
    # Build SKU: MFGR-SERIES-MODEL+VERSION (8+1+8+1+13+2 = 33)
    sku = f"{mfgr_part}-{series_part}-{model_part}{version_part}"
    
    # Pad with zeros to reach 40 characters
    sku = sku.ljust(40, "0")
    
    return sku

def _base36_2(n: int) -> str:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n < 0 or n >= 36 * 36:
        raise ValueError("base36_2 out of range")
    return alphabet[n // 36] + alphabet[n % 36]

def _process_name_full(name: str) -> str:
    # Match generate_parent_sku's process_name behavior but without truncation/padding
    words = name.split()
    if len(words) > 1:
        result = "".join(word.capitalize() for word in words)
    else:
        result = name.capitalize()
    result = "".join(c for c in result if c.isalnum())
    return result.upper()

def generate_unique_parent_sku(
    db: Session,
    series_id: int,
    manufacturer_name: str,
    series_name: str,
    model_name: str,
    version: str = "V1",
    exclude_model_id: Optional[int] = None
) -> str:
    """
    Generate a unique parent SKU for a model within a series.
    Uses Option 4: Tail Borrowing then Counter Overwrite.
    """
    # 1. Base SKU
    base_sku = generate_parent_sku(manufacturer_name, series_name, model_name, version)
    
    # Check collision
    query = db.query(Model).filter(
        Model.series_id == series_id,
        Model.parent_sku == base_sku
    )
    if exclude_model_id is not None:
        query = query.filter(Model.id != exclude_model_id)
        
    if not query.first():
        return base_sku

    print(f"[SKU_COLLISION] Base SKU '{base_sku}' collides in series {series_id}")

    # 2. Prepare for modifiers
    # SKU Format: MFGR(8)-SERIES(8)-MODEL(13)V1(2) -> Model segment starts at index 18
    # MFGR(8) + dash(1) + SERIES(8) + dash(1) = 18 chars prefix
    MODEL_START_IDX = 18
    MODEL_LEN = 13
    
    processed_full = _process_name_full(model_name)
    tail = processed_full[MODEL_LEN:] # chars usually truncated
    
    # 3. Strategy A: Tail Borrowing (Replace end of model segment with hidden tail chars)
    K = 5
    for i in range(1, min(K, len(tail)) + 1):
        # Construct candidate: replace last i chars of model segment (which is base_sku[18:31])
        # base_sku[18:31] is the padded model chunk.
        # We want to keep the first (13-i) chars of the segment, then append tail[:i]
        
        current_segment = base_sku[MODEL_START_IDX : MODEL_START_IDX + MODEL_LEN]
        new_segment = current_segment[:MODEL_LEN - i] + tail[:i]
        
        # New SKU
        prefix = base_sku[:MODEL_START_IDX]
        suffix = base_sku[MODEL_START_IDX + MODEL_LEN:] # Version + padding
        candidate = prefix + new_segment + suffix
        
        # Check collision
        q_coll = db.query(Model).filter(Model.series_id == series_id, Model.parent_sku == candidate)
        if exclude_model_id is not None:
            q_coll = q_coll.filter(Model.id != exclude_model_id)
            
        if not q_coll.first():
            if len(candidate) != 40:
                 raise HTTPException(500, f"SKU length integrity violation: {len(candidate)}")
            print(f"[SKU_RESOLVED] Strategy: Tail Borrowing ({i} chars). Final: {candidate}")
            return candidate

    # 4. Strategy B: Counter Overwrite (Replace last 2 chars of model segment with Base36)
    # 00..ZZ (1296 variants)
    for c in range(1296):
        counter_str = _base36_2(c)
        
        current_segment = base_sku[MODEL_START_IDX : MODEL_START_IDX + MODEL_LEN]
        # Replace last 2 chars
        new_segment = current_segment[:MODEL_LEN - 2] + counter_str
        
        prefix = base_sku[:MODEL_START_IDX]
        suffix = base_sku[MODEL_START_IDX + MODEL_LEN:]
        candidate = prefix + new_segment + suffix
        
        q_coll = db.query(Model).filter(Model.series_id == series_id, Model.parent_sku == candidate)
        if exclude_model_id is not None:
            q_coll = q_coll.filter(Model.id != exclude_model_id)
            
        if not q_coll.first():
            if len(candidate) != 40:
                 raise HTTPException(500, f"SKU length integrity violation: {len(candidate)}")
            print(f"[SKU_RESOLVED] Strategy: Counter Overwrite ({counter_str}). Final: {candidate}")
            return candidate
            
    # Fallback (Should be unreachable practically)
    print(f"[SKU_FAILED] Could not resolve collision for {base_sku}")
    return base_sku # Return base and let DB constraint fail if it must

def validate_design_option(option_id: Optional[int], expected_type: str, db: Session) -> None:
    """Validate that a design option exists and has the correct type."""
    if option_id is not None:
        option = db.query(DesignOption).filter(DesignOption.id == option_id).first()
        if not option:
            raise HTTPException(
                status_code=400,
                detail=f"Design option with id {option_id} not found"
            )
        if option.option_type != expected_type:
            raise HTTPException(
                status_code=400,
                detail=f"Design option {option_id} has type '{option.option_type}', expected '{expected_type}'"
            )

def sync_marketplace_listings(model_id: int, listings_data: List[MarketplaceListingCreate], db: Session) -> None:
    """
    Sync marketplace listings for a model.
    For core UI marketplaces (amazon/ebay/reverb/etsy), the payload is authoritative:
    - Non-empty external_id -> keep exactly one row per marketplace (replace any existing rows)
    - Missing/empty external_id -> remove rows for that marketplace
    For non-core marketplaces, preserve legacy upsert behavior.
    """
    core_marketplaces = {"amazon", "ebay", "reverb", "etsy"}
    latest_by_marketplace: dict[str, MarketplaceListingCreate] = {}

    for listing_data in listings_data or []:
        marketplace = str(listing_data.marketplace or "").strip().lower()
        if not marketplace:
            continue
        latest_by_marketplace[marketplace] = listing_data

    # Core marketplaces: authoritative replacement semantics.
    for marketplace in core_marketplaces:
        entry = latest_by_marketplace.get(marketplace)
        external_id = str(getattr(entry, "external_id", "") or "").strip() if entry is not None else ""

        # Remove all existing rows for this model+marketplace first to prevent stale duplicates.
        db.query(MarketplaceListing).filter(
            MarketplaceListing.model_id == model_id,
            MarketplaceListing.marketplace == marketplace
        ).delete(synchronize_session=False)

        if external_id:
            db.add(MarketplaceListing(
                model_id=model_id,
                marketplace=marketplace,
                external_id=external_id,
                listing_url=getattr(entry, "listing_url", None)
            ))

    # Non-core marketplaces: keep prior upsert behavior.
    for listing_data in listings_data or []:
        marketplace = str(listing_data.marketplace or "").strip().lower()
        if not marketplace or marketplace in core_marketplaces:
            continue
        external_id = str(listing_data.external_id or "").strip()
        if not external_id:
            continue

        existing = db.query(MarketplaceListing).filter(
            MarketplaceListing.model_id == model_id,
            MarketplaceListing.marketplace == marketplace
        ).first()
        if existing:
            existing.external_id = external_id
            existing.listing_url = listing_data.listing_url
            existing.updated_at = datetime.utcnow()
        else:
            db.add(MarketplaceListing(
                model_id=model_id,
                marketplace=marketplace,
                external_id=external_id,
                listing_url=listing_data.listing_url
            ))

@router.get("", response_model=List[ModelResponse])
def list_models(series_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    # Eager load relationships to prevent N+1 queries
    query = db.query(Model).options(
        joinedload(Model.series),
        joinedload(Model.equipment_type),
        selectinload(Model.marketplace_listings),
        selectinload(Model.amazon_a_plus_content)
    )
    if series_id:
        query = query.filter(Model.series_id == series_id)
    return query.all()


@router.get("/search")
def search_models(
    q: str = Query("", description="Search query for model name, series name, or manufacturer name"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lightweight model search for UI autocomplete.
    Returns: id, name, manufacturer_name, series_name, reverb_product_id
    """
    from sqlalchemy import or_, func
    
    query = db.query(Model).join(Series, Model.series_id == Series.id).join(
        Manufacturer, Series.manufacturer_id == Manufacturer.id
    )
    
    # Search if query provided
    if q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Model.name.ilike(search_term),
                Series.name.ilike(search_term),
                Manufacturer.name.ilike(search_term),
                Model.reverb_product_id.ilike(search_term)
            )
        )
    
    # Order by manufacturer, series, model name
    query = query.order_by(Manufacturer.name, Series.name, Model.name)
    query = query.limit(limit)
    
    results = []
    for model in query.all():
        results.append({
            "id": model.id,
            "name": model.name,
            "manufacturer_name": model.series.manufacturer.name if model.series and model.series.manufacturer else None,
            "series_name": model.series.name if model.series else None,
            "reverb_product_id": model.reverb_product_id
        })
    
    return results


def lookup_models_by_marketplace_listing(db: Session, marketplace: str, identifier: str, limit: int = 25):
    """
    Helper function to find models by marketplace listing external_id.
    Used by both the API endpoint and order detail resolution.
    
    Args:
        db: Database session
        marketplace: Marketplace name (case-insensitive, e.g., "reverb")
        identifier: External listing ID (e.g., "77054514")
        limit: Maximum results to return
        
    Returns:
        List of dicts with model info and matched listing data
    """
    from sqlalchemy import func
    
    # Normalize inputs using centralized helpers
    marketplace_normalized = normalize_marketplace(marketplace)
    identifier_normalized = normalize_identifier(identifier)
    
    if not marketplace_normalized or not identifier_normalized:
        return []
    
    # Query marketplace_listings table joined with model, series, manufacturer
    query = db.query(MarketplaceListing, Model, Series, Manufacturer).join(
        Model, MarketplaceListing.model_id == Model.id
    ).join(
        Series, Model.series_id == Series.id
    ).join(
        Manufacturer, Series.manufacturer_id == Manufacturer.id
    ).filter(
        func.lower(func.trim(MarketplaceListing.marketplace)) == marketplace_normalized,
        # Match external_id as string (both trimmed)
        func.trim(MarketplaceListing.external_id) == identifier_normalized
    ).limit(limit)
    
    # Collect results, dedupe by model_id
    seen_model_ids = set()
    results = []
    
    for listing, model, series, manufacturer in query.all():
        if model.id in seen_model_ids:
            continue
        seen_model_ids.add(model.id)
        
        results.append({
            "model_id": model.id,
            "model_name": model.name,
            "manufacturer_name": manufacturer.name,
            "series_name": series.name,
            "sku": model.parent_sku,
            "matched_listing_marketplace": listing.marketplace,
            "matched_listing_identifier": listing.external_id
        })
    
    return results


@router.get("/marketplace-lookup")
def lookup_models_by_marketplace(
    marketplace: str = Query(..., description="Marketplace name (e.g., 'reverb')"),
    identifier: str = Query(..., description="External listing ID (e.g., '77054514')"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Find models by marketplace listing identifier (external_id).
    Searches the marketplace_listings table used by the Models UI.
    
    Returns: list of models with matched listing info
    """
    results = lookup_models_by_marketplace_listing(db, marketplace, identifier, limit)
    return results


@router.get("/{id}", response_model=ModelResponse)
def get_model(id: int, db: Session = Depends(get_db)):
    model = db.query(Model).filter(Model.id == id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model

@router.post("", response_model=ModelResponse)
def create_model(data: ModelCreate, db: Session = Depends(get_db)):
    try:
        print("=" * 80)
        print("🔥 CREATE_MODEL START 🔥")
        print(f"[DEBUG] Received data: {data.dict()}")
        
        print("[DEBUG] Step 1: Validate minimum requirements")
        # Validate minimum save requirements
        validation_errors = []
        if not data.series_id:
            validation_errors.append("Series is required")
        if not data.name or not data.name.strip():
            validation_errors.append("Model name is required")
        if not data.equipment_type_id:
            validation_errors.append("Equipment type is required")
        
        if validation_errors:
            print(f"[DEBUG] Validation failed: {validation_errors}")
            raise HTTPException(
                status_code=400, 
                detail={"message": "Validation failed", "errors": validation_errors}
            )
        print("[DEBUG] Step 1: PASSED ✓")
        
        print("[DEBUG] Step 2: Fetch series & manufacturer")
        # Get series and manufacturer names for SKU generation
        series = db.query(Series).filter(Series.id == data.series_id).first()
        if not series:
            print(f"[DEBUG] Series not found: {data.series_id}")
            raise HTTPException(status_code=400, detail="Series not found")
        print(f"[DEBUG] Found series: {series.name}")
        
        manufacturer = db.query(Manufacturer).filter(Manufacturer.id == series.manufacturer_id).first()
        if not manufacturer:
            print(f"[DEBUG] Manufacturer not found: {series.manufacturer_id}")
            raise HTTPException(status_code=400, detail="Manufacturer not found")
        print(f"[DEBUG] Found manufacturer: {manufacturer.name}")
        print("[DEBUG] Step 2: PASSED ✓")
        
        print("[DEBUG] Step 3: Validate design options")
        # Validate design option selections
        validate_design_option(data.handle_location_option_id, "handle_location", db)
        validate_design_option(data.angle_type_option_id, "angle_type", db)
        print("[DEBUG] Step 3: PASSED ✓")
        
        print("[DEBUG] Step 4: Generate SKU")
        # Generate UNIQUE parent SKU
        parent_sku = generate_unique_parent_sku(
            db=db,
            series_id=series.id,
            manufacturer_name=manufacturer.name,
            series_name=series.name,
            model_name=data.name,
            exclude_model_id=None
        )
        print(f"[DEBUG] Generated SKU: {parent_sku}")
        print("[DEBUG] Step 4: PASSED ✓")
        
        print("[DEBUG] Step 5: Calculate surface area")
        # Calculate surface area
        surface_area = calculate_surface_area(data.width, data.depth, data.height)
        print(f"[DEBUG] Surface area: {surface_area}")
        print("[DEBUG] Step 5: PASSED ✓")
        
        print("[DEBUG] Step 6: Create Model object")
        model = Model(
            name=data.name,
            series_id=data.series_id,
            equipment_type_id=data.equipment_type_id,
            width=data.width,
            depth=data.depth,
            height=data.height,
            handle_length=data.handle_length,
            handle_width=data.handle_width,
            handle_location=data.handle_location,
            angle_type=data.angle_type,
            image_url=data.image_url,
            parent_sku=parent_sku,
            sku_override=data.sku_override,
            surface_area_sq_in=surface_area,
            top_depth_in=data.top_depth_in,
            angle_drop_in=data.angle_drop_in,
            handle_location_option_id=data.handle_location_option_id,
            angle_type_option_id=data.angle_type_option_id,
            top_handle_length_in=data.top_handle_length_in,
            top_handle_height_in=data.top_handle_height_in,
            top_handle_rear_edge_to_center_in=data.top_handle_rear_edge_to_center_in
        )
        print(f"[DEBUG] Model object created: {model.name}")
        print("[DEBUG] Step 6: PASSED ✓")
        
        print("[DEBUG] Step 7: db.add(model)")
        db.add(model)
        print("[DEBUG] Step 7: PASSED ✓")
        
        print("[DEBUG] Step 8: db.flush()")
        db.flush() # Get ID for pricing
        print(f"[DEBUG] Model flushed with ID: {model.id}")
        print("[DEBUG] Step 8: PASSED ✓")
        
        print("[DEBUG] Step 9: Sync marketplace listings")
        # Sync marketplace listings if provided
        if data.marketplace_listings:
            print(f"[DEBUG] Syncing {len(data.marketplace_listings)} marketplace listings")
            sync_marketplace_listings(model.id, data.marketplace_listings, db)
            print("[DEBUG] Marketplace listings synced")
        else:
            print("[DEBUG] No marketplace listings to sync")
        print("[DEBUG] Step 9: PASSED ✓")

        print("[DEBUG] Step 10: Calculate pricing (optional)")
        # Check if we have sufficient data for pricing calculation
        has_dimensions = (
            data.width and data.width > 0 and
            data.depth and data.depth > 0 and
            data.height and data.height > 0
        )
        has_surface_area = surface_area and surface_area > 0
        
        if has_dimensions and has_surface_area:
            # Auto-recalculate pricing (Optional - only if dimensions exist)
            try:
                print(f"[DEBUG] Calculating pricing for model ID: {model.id}")
                marketplaces = ["amazon", "reverb", "ebay", "etsy"]
                for mp in marketplaces:
                    try:
                        with db.begin_nested():
                            PricingCalculator(db).calculate_model_prices(model.id, marketplace=mp)
                    except Exception as e:
                        print(f"[PRICING] Snapshot calc failed for {mp}: {e}")

                print("[DEBUG] Pricing calculated successfully for configured marketplaces")
            except Exception as e:
                # Log but DO NOT block model creation
                print(f"[PRICING] Warning: Pricing calculation failed: {str(e)}")
                print(f"[PRICING] Model will be saved without pricing. Pricing can be calculated later.")
                traceback.print_exc()
                # DO NOT raise HTTPException - allow model to save
        else:
            print(f"[PRICING] Skipped – insufficient dimensions (w={data.width}, d={data.depth}, h={data.height}, sa={surface_area})")
            print(f"[PRICING] Model will be saved as draft. Pricing can be calculated later when dimensions are added.")
        
        print("[DEBUG] Step 10: PASSED ✓")
        
        print("[DEBUG] Step 11: db.commit()")
        db.commit() # Commit model (with or without pricing)
        print("[DEBUG] Step 11: PASSED ✓")
        
        print("[DEBUG] Step 12: db.refresh(model)")
        db.refresh(model)
        print(f"[DEBUG] Model refreshed. ID: {model.id}, SKU: {model.parent_sku}")
        print("[DEBUG] Step 12: PASSED ✓")
        
        print("[DEBUG] Step 13: Return model")
        print(f"[DEBUG] Returning model: ID={model.id}, name={model.name}, parent_sku={model.parent_sku}")
        print("🔥 CREATE_MODEL SUCCESS 🔥")
        print("=" * 80)
        return model
        
    except HTTPException:
        print("[DEBUG] HTTPException raised (re-raising)")
        raise
    except IntegrityError as e:
        print(f"🔥 DATABASE INTEGRITY ERROR 🔥")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database Integrity Error: {str(e)}")
    except Exception as e:
        print("🔥 CREATE_MODEL FAILED 🔥")
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{id}", response_model=ModelResponse)
def update_model(id: int, data: ModelCreate, db: Session = Depends(get_db)):
    print("=" * 80)
    print("🔥🔥🔥 UPDATE_MODEL HIT 🔥🔥🔥")
    print(f"Model ID: {id}")
    print(f"Data received: name={data.name}, width={data.width}, depth={data.depth}, height={data.height}")
    print("=" * 80)
    
    model = db.query(Model).filter(Model.id == id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    try:
        # Validate minimum save requirements
        validation_errors = []
        if not data.series_id:
            validation_errors.append("Series is required")
        if not data.name or not data.name.strip():
            validation_errors.append("Model name is required")
        if not data.equipment_type_id:
            validation_errors.append("Equipment type is required")
        
        if validation_errors:
            raise HTTPException(
                status_code=400, 
                detail={"message": "Validation failed", "errors": validation_errors}
            )
        
        # Get series and manufacturer names for SKU regeneration
        series = db.query(Series).filter(Series.id == data.series_id).first()
        if not series:
            raise HTTPException(status_code=400, detail="Series not found")
        manufacturer = db.query(Manufacturer).filter(Manufacturer.id == series.manufacturer_id).first()
        if not manufacturer:
            raise HTTPException(status_code=400, detail="Manufacturer not found")
        
        # Validate design option selections
        validate_design_option(data.handle_location_option_id, "handle_location", db)
        validate_design_option(data.angle_type_option_id, "angle_type", db)
        
        # Regenerate parent SKU if name, series, or manufacturer changed
        parent_sku = generate_unique_parent_sku(
            db=db,
            series_id=data.series_id,
            manufacturer_name=manufacturer.name,
            series_name=series.name,
            model_name=data.name,
            exclude_model_id=id
        )
        
        # Recalculate surface area
        surface_area = calculate_surface_area(data.width, data.depth, data.height)
        
        # Temporary logging for verification
        print(f"[models.py] Updating Model ID: {id}")
        print(f"[models.py] Update payload fields: {list(data.dict().keys())}")
        print(f"[models.py] Received enum values - handle_location: {data.handle_location}, angle_type: {data.angle_type}")
        print(f"[models.py] Received FK IDs - handle_location_option_id: {data.handle_location_option_id}, angle_type_option_id: {data.angle_type_option_id}")
        
        model.name = data.name
        model.series_id = data.series_id
        model.equipment_type_id = data.equipment_type_id
        model.width = data.width
        model.depth = data.depth
        model.height = data.height
        model.handle_length = data.handle_length
        model.handle_width = data.handle_width
        # Always assign enums explicitly - they have defaults so never None from schema
        model.handle_location = data.handle_location
        model.angle_type = data.angle_type
        model.image_url = data.image_url
        model.parent_sku = parent_sku
        model.surface_area_sq_in = surface_area
        model.top_depth_in = data.top_depth_in
        model.angle_drop_in = data.angle_drop_in
        
        # Update sku_override if provided in fields_set
        fields_set = getattr(data, 'model_fields_set', getattr(data, '__fields_set__', set()))
        if 'sku_override' in fields_set:
            model.sku_override = data.sku_override
        
        # Assign FK-based design option selections
        if data.handle_location_option_id is not None:
            model.handle_location_option_id = data.handle_location_option_id
        if data.angle_type_option_id is not None:
            model.angle_type_option_id = data.angle_type_option_id
        
        # Assign top handle measurements (check presence to allow clearing to None)
        # Using model_fields_set (Pydantic v2) or __fields_set__ (v1)
        fields_set = getattr(data, 'model_fields_set', getattr(data, '__fields_set__', set()))
        
        print(f"[models.py] Top Handle Update - Provided fields: {fields_set}")
        print(f"[models.py] Top Handle Update - Values: length={data.top_handle_length_in}, height={data.top_handle_height_in}, rear={data.top_handle_rear_edge_to_center_in}")

        if 'top_handle_length_in' in fields_set:
            model.top_handle_length_in = data.top_handle_length_in
        if 'top_handle_height_in' in fields_set:
            model.top_handle_height_in = data.top_handle_height_in
        if 'top_handle_rear_edge_to_center_in' in fields_set:
            model.top_handle_rear_edge_to_center_in = data.top_handle_rear_edge_to_center_in
        
        # Update model_notes if provided
        fields_set = getattr(data, 'model_fields_set', getattr(data, '__fields_set__', set()))
        if 'model_notes' in fields_set:
            model.model_notes = data.model_notes
        
        # Update export exclusion flags
        model.exclude_from_amazon_export = data.exclude_from_amazon_export
        model.exclude_from_ebay_export = data.exclude_from_ebay_export
        model.exclude_from_reverb_export = data.exclude_from_reverb_export
        model.exclude_from_etsy_export = data.exclude_from_etsy_export
        
        # Sync marketplace listings if provided
        if data.marketplace_listings is not None:
            sync_marketplace_listings(model.id, data.marketplace_listings, db)
            
        # Sync Amazon A+ Content if provided
        if data.amazon_a_plus_content is not None:
             print(f"[MODEL] Syncing {len(data.amazon_a_plus_content)} A+ Content items")
             for content_data in data.amazon_a_plus_content:
                # Find existing
                existing_content = db.query(ModelAmazonAPlusContent).filter(
                    ModelAmazonAPlusContent.model_id == model.id,
                    ModelAmazonAPlusContent.content_type == content_data.content_type
                ).first()
                
                if existing_content:
                    existing_content.is_uploaded = content_data.is_uploaded
                    existing_content.notes = content_data.notes
                    existing_content.updated_at = datetime.utcnow()
                else:
                    new_content = ModelAmazonAPlusContent(
                        model_id=model.id,
                        content_type=content_data.content_type,
                        is_uploaded=content_data.is_uploaded,
                        notes=content_data.notes
                    )
                    db.add(new_content)
        
        print("[MODEL] Committing model changes...")
        # CRITICAL: Commit model changes BEFORE pricing logic
        db.commit()
        db.refresh(model)
        print(f"[MODEL] Update committed. ID: {model.id}, SKU: {model.parent_sku}")
        
        # Log what was actually saved
        print(f"[MODEL] Saved - dimensions: w={model.width}, d={model.depth}, h={model.height}")
        print(f"[MODEL] Saved - handle_location: {model.handle_location}, angle_type: {model.angle_type}")
        print(f"[MODEL] Saved - handle_location_option_id: {model.handle_location_option_id}, angle_type_option_id: {model.angle_type_option_id}")
        print(f"[MODEL] Saved - top_handle measurements: length={model.top_handle_length_in}, height={model.top_handle_height_in}, rear_edge={model.top_handle_rear_edge_to_center_in}")
        
        # ========================================
        # PRICING LOGIC (OPTIONAL - NEVER BLOCKS SAVE)
        # ========================================
        try:
            # Check if we have dimensions for pricing
            has_dimensions = (
                model.width and model.width > 0 and
                model.depth and model.depth > 0 and
                model.height and model.height > 0
            )
            
            if not has_dimensions:
                print(f"[PRICING] Skipped – insufficient dimensions (w={model.width}, d={model.depth}, h={model.height})")
            else:
                # ALWAYS recalculate pricing when dimensions exist
                # SAVE is the authoritative trigger for pricing
                print(f"[PRICING] Dimensions present (w={model.width}, d={model.depth}, h={model.height})")
                print(f"[PRICING] Running baseline recalculation for model ID: {model.id}")
                
                try:
                    marketplaces = ["amazon", "reverb", "ebay", "etsy"]
                    for mp in marketplaces:
                        try:
                            with db.begin_nested():
                                PricingCalculator(db).calculate_model_prices(model.id, marketplace=mp)
                        except Exception as e:
                            print(f"[PRICING] Snapshot calc failed for {mp}: {e}")
                    
                    # CRITICAL: Commit pricing snapshots to make them visible
                    db.commit()
                    print("[PRICING] Pricing snapshots committed to database")
                    
                    # Query the created snapshots for logging
                    created_snapshots = db.query(ModelPricingSnapshot).filter(
                        ModelPricingSnapshot.model_id == model.id,
                        ModelPricingSnapshot.marketplace == "amazon"
                    ).order_by(ModelPricingSnapshot.created_at.desc()).limit(4).all()
                    
                    print(f"[PRICING] Recalculation successful - created/updated {len(created_snapshots)} snapshots")
                    for snapshot in created_snapshots:
                        print(f"[PRICING] Snapshot: id={snapshot.id}, variant={snapshot.variant_key}, created_at={snapshot.created_at}")
                        
                except Exception as pricing_error:
                    # Log but DO NOT block (model already saved)
                    print(f"[PRICING] Recalculation failed: {str(pricing_error)}")
                    print(f"[PRICING] Model saved anyway - pricing can be calculated later")
                    traceback.print_exc()
                    # DO NOT raise - pricing failure is not a save failure
        
        except Exception as pricing_check_error:
            # Catch ANY error in pricing logic to ensure it never blocks save
            print(f"[PRICING] Error in pricing logic: {str(pricing_check_error)}")
            print(f"[PRICING] Model saved successfully despite pricing error")
            traceback.print_exc()
            # DO NOT raise - model is already committed

        return model
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Model with this name already exists in this series")

@router.get("/{id}/pricing", response_model=List[ModelPricingSnapshotResponse])
def get_model_pricing(id: int, marketplace: str = "DEFAULT", db: Session = Depends(get_db)):
    """Get pricing snapshots for a model."""
    snapshots = db.query(ModelPricingSnapshot).filter(
        ModelPricingSnapshot.model_id == id,
        ModelPricingSnapshot.marketplace == marketplace
    ).all()

@router.get("/{id}/pricing/snapshots", response_model=List[ModelPricingSnapshotResponse])
def get_model_baseline_snapshots(
    id: int, 
    marketplace: str = Query("amazon"), 
    db: Session = Depends(get_db)
):
    """
    Get the 4 baseline pricing snapshots (Choice/Premium x Padded/NoPadding).
    Sorted in stable order: Choice NoPad, Choice Pad, Premium NoPad, Premium Pad.
    """
    BASELINE_KEYS = [
        "choice_no_padding", 
        "choice_padded", 
        "premium_no_padding", 
        "premium_padded"
    ]
    
    rows = db.query(ModelPricingSnapshot).filter(
        ModelPricingSnapshot.model_id == id,
        ModelPricingSnapshot.marketplace == marketplace,
        ModelPricingSnapshot.variant_key.in_(BASELINE_KEYS)
    ).all()
    
    # Sort in Python to ensure stable order
    sort_map = {key: i for i, key in enumerate(BASELINE_KEYS)}
    sorted_rows = sorted(rows, key=lambda x: sort_map.get(x.variant_key, 999))
    
    return sorted_rows

@router.post("/{id}/pricing/recalculate", response_model=List[ModelPricingSnapshotResponse])
def recalculate_model_pricing(id: int, marketplace: str = Query("amazon"), db: Session = Depends(get_db)):
    """
    Manually trigger pricing recalculation for a model.

    IMPORTANT BEHAVIOR:
    - Recalculates ALL supported marketplaces every time (amazon, reverb, ebay, etsy).
    - Returns snapshots ONLY for the requested marketplace so the UI stays stable.
    """
    marketplaces = ["amazon", "reverb", "ebay", "etsy"]  # keep aligned with app/api/pricing.py

    any_success = False
    errors = []

    for mp in marketplaces:
        try:
            # Nested transaction so one marketplace failure doesn't block others
            with db.begin_nested():
                PricingCalculator(db).calculate_model_prices(id, marketplace=mp)
            any_success = True
        except Exception as e:
            # Collect errors but continue other marketplaces
            errors.append(f"{mp}: {str(e)}")
            continue

    if not any_success:
        # If nothing succeeded, return a clean 400 with combined errors
        raise HTTPException(status_code=400, detail="Recalculation failed for all marketplaces. " + " | ".join(errors))

    # Commit all successful marketplace recalcs
    db.commit()

    # Return updated snapshots for the currently selected marketplace (UI expects this)
    return db.query(ModelPricingSnapshot).filter(
        ModelPricingSnapshot.model_id == id,
        ModelPricingSnapshot.marketplace == marketplace
    ).all()

@router.get("/{id}/pricing/history", response_model=List[ModelPricingHistoryResponse])
def get_model_pricing_history(
    id: int, 
    marketplace: Optional[str] = None, 
    variant_key: Optional[str] = None,
    limit: int = 200, 
    db: Session = Depends(get_db)
):
    """Get pricing history for a model."""
    query = db.query(ModelPricingHistory).filter(ModelPricingHistory.model_id == id)
    
    if marketplace:
        query = query.filter(ModelPricingHistory.marketplace == marketplace)
    
    if variant_key:
        query = query.filter(ModelPricingHistory.variant_key == variant_key)
        
    return query.order_by(ModelPricingHistory.calculated_at.desc()).limit(limit).all()

@router.get("/{id}/pricing/diff", response_model=Optional[PricingDiffResponse])
def get_model_pricing_diff(
    id: int,
    variant_key: str,
    marketplace: str = "DEFAULT",
    db: Session = Depends(get_db)
):
    """
    Get the difference between the two most recent pricing history entries.
    Returns null if insufficient history exists (fewer than 2 rows).
    """
    return PricingDiffService(db).diff_latest(id, marketplace, variant_key)

@router.post("/pricing/recalculate-all")
def recalculate_all_models(marketplace: str = "DEFAULT", db: Session = Depends(get_db)):
    """Admin endpoint to recalculate pricing for ALL models."""
    models = db.query(Model).all()
    success_count = 0
    errors = []
    
    for model in models:
        try:
            PricingCalculator(db).calculate_model_prices(model.id, marketplace=marketplace)
            success_count += 1
        except Exception as e:
             errors.append(f"Model {model.id}: {str(e)}")
    
    db.commit() # Commit all successful ones
    
    return {
        "message": f"Recalculated {success_count}/{len(models)} models",
        "errors": errors
    }

@router.delete("/{id}")
def delete_model(
    id: int,
    purge_pricing_dependencies: bool = Query(False, description="If true, delete model pricing snapshot/history rows first."),
    db: Session = Depends(get_db),
):
    model = db.query(Model).filter(Model.id == id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Check for known blocking dependencies first to return actionable messages.
    blockers = []
    order_line_count = db.query(OrderLine).filter(OrderLine.model_id == id).count()
    if order_line_count > 0:
        blockers.append(f"used in {order_line_count} order line(s)")

    snapshot_count = db.query(ModelPricingSnapshot).filter(ModelPricingSnapshot.model_id == id).count()
    history_count = db.query(ModelPricingHistory).filter(ModelPricingHistory.model_id == id).count()
    if snapshot_count > 0:
        if purge_pricing_dependencies:
            db.query(ModelPricingSnapshot).filter(ModelPricingSnapshot.model_id == id).delete(synchronize_session=False)
        else:
            blockers.append(f"referenced by {snapshot_count} pricing snapshot row(s)")
    if history_count > 0:
        if purge_pricing_dependencies:
            db.query(ModelPricingHistory).filter(ModelPricingHistory.model_id == id).delete(synchronize_session=False)
        else:
            blockers.append(f"referenced by {history_count} pricing history row(s)")

    listing_count = db.query(MarketplaceListing).filter(MarketplaceListing.model_id == id).count()
    if listing_count > 0:
        blockers.append(f"linked to {listing_count} marketplace listing row(s)")

    variation_count = db.query(ModelVariationSKU).filter(ModelVariationSKU.model_id == id).count()
    if variation_count > 0:
        blockers.append(f"linked to {variation_count} variation SKU row(s)")

    if blockers:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot delete model '{model.name}' because it is " + "; ".join(blockers) + ". "
                "If pricing snapshot/history references are the only blockers, retry delete with purge_pricing_dependencies=true."
            ),
        )

    try:
        db.delete(model)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raw_error = str(getattr(e, "orig", e))
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot delete model '{model.name}' due to related records in another table. "
                f"Database message: {raw_error}"
            ),
        )

    return {"message": "Model deleted"}

@router.post("/regenerate-skus")
def regenerate_all_skus(db: Session = Depends(get_db)):
    """Regenerate parent SKUs for all models that don't have one."""
    models = db.query(Model).all()
    updated_count = 0
    
    for model in models:
        series = db.query(Series).filter(Series.id == model.series_id).first()
        if not series:
            continue
        manufacturer = db.query(Manufacturer).filter(Manufacturer.id == series.manufacturer_id).first()
        if not manufacturer:
            continue
        
        parent_sku = generate_unique_parent_sku(
            db=db,
            series_id=model.series_id,
            manufacturer_name=manufacturer.name,
            series_name=series.name,
            model_name=model.name,
            exclude_model_id=model.id
        )
        if model.parent_sku != parent_sku:
            model.parent_sku = parent_sku
            updated_count += 1
    
    db.commit()
    return {"message": f"Regenerated SKUs for {updated_count} models"}
