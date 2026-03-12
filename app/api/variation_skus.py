"""
eBay Variation SKU API Endpoints

Endpoints for generating and managing eBay variation SKUs for models.

DEPRECATED / legacy endpoints:
Persisted child variation SKUs are not authoritative for eBay export.
eBay child SKUs are computed at export time; parent SKU is the only persistent SKU.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
import logging

from app.database import get_db
from app.models.core import Model, ModelVariationSKU
from app.schemas.core import ModelVariationSKUResponse
from app.services.variation_sku_generator import generate_and_persist_model_variation_skus

router = APIRouter(prefix="/api/variation-skus", tags=["Variation SKUs"])
logger = logging.getLogger(__name__)


@router.post("/generate/{model_id}")
def generate_variation_skus(model_id: int, db: Session = Depends(get_db)):
    """
    Generate all variation SKUs for a model based on its parent SKU.
    
    This will:
    1. Parse the model's parent SKU
    2. Get all enabled materials, colors, and design options for the equipment type
    3. Generate all possible combinations
    4. Save variations to the database
    
    Returns:
        {
            "model_id": int,
            "parent_sku": str,
            "variations_generated": int,
            "variations": [...]
        }
    """
    logger.warning(
        "Deprecated: child SKUs are computed at export time; parent SKU is the only persistent SKU."
    )
    # Get the model
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")
    
    if not model.parent_sku:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model.name}' does not have a parent SKU"
        )
    
    try:
        # Generate and persist variations
        saved_count = generate_and_persist_model_variation_skus(db, model_id)
        db.commit()
        
        # Get saved variations for response
        variations = db.query(ModelVariationSKU).filter(
            ModelVariationSKU.model_id == model_id
        ).all()
        
        return {
            "model_id": model_id,
            "parent_sku": model.parent_sku,
            "variations_generated": saved_count,
            "variations": [
                {
                    "id": v.id,
                    "variation_sku": v.variation_sku,
                    "variation_payload": v.variation_payload
                }
                for v in variations
            ]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating variations: {str(e)}")


@router.get("/{model_id}", response_model=List[ModelVariationSKUResponse])
def get_model_variations(model_id: int, db: Session = Depends(get_db)):
    """
    Get all variation SKUs for a model.
    
    Returns a list of all generated variation SKUs for the specified model,
    including the parent SKU.
    """
    logger.warning(
        "Deprecated: child SKUs are computed at export time; parent SKU is the only persistent SKU."
    )
    # Verify model exists
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")
    
    variations = db.query(ModelVariationSKU).filter(
        ModelVariationSKU.model_id == model_id
    ).order_by(
        ModelVariationSKU.is_parent.desc(),  # Parent first
        ModelVariationSKU.variation_sku
    ).all()
    
    return variations


@router.delete("/{model_id}")
def delete_model_variations(model_id: int, db: Session = Depends(get_db)):
    """
    Delete all variation SKUs for a model.
    
    This is useful for regenerating variations after changing materials,
    colors, or design options.
    
    Returns:
        {"model_id": int, "deleted_count": int}
    """
    logger.warning(
        "Deprecated: child SKUs are computed at export time; parent SKU is the only persistent SKU."
    )
    # Verify model exists
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")
    
    deleted_count = db.query(ModelVariationSKU).filter(
        ModelVariationSKU.model_id == model_id
    ).delete()
    
    db.commit()
    
    return {
        "model_id": model_id,
        "deleted_count": deleted_count
    }


@router.get("/{model_id}/preview")
def preview_variations(model_id: int, db: Session = Depends(get_db)):
    """
    Preview what variation SKUs would be generated for a model
    WITHOUT saving to the database.
    
    Returns:
        {
            "model_id": int,
            "parent_sku": str,
            "preview_count": int,
            "variations": [...]
        }
    """
    logger.warning(
        "Deprecated: child SKUs are computed at export time; parent SKU is the only persistent SKU."
    )
    # Get the model
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")
    
    if not model.parent_sku:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model.name}' does not have a parent SKU"
        )
    
    try:
        # Note: Preview functionality requires separate implementation
        # For now, return empty preview with helpful message
        raise HTTPException(
            status_code=501,
            detail="Preview endpoint not yet implemented with new generator. Use POST /generate to create variations."
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing variations: {str(e)}")
