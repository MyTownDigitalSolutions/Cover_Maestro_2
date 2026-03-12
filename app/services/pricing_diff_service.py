from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.core import ModelPricingHistory
from app.schemas.pricing_diff import PricingDiffResponse, PricingFieldDiff
from typing import Optional, List, Any

class PricingDiffService:
    def __init__(self, db: Session):
        self.db = db

    def diff_latest(self, model_id: int, marketplace: str, variant_key: str) -> Optional[PricingDiffResponse]:
        """
        Compares the two most recent history rows for a given model, marketplace, and variant.
        Returns a diff response or None if insufficient history exists.
        """
        
        # 1. Fetch latest 2 rows
        history_rows = self.db.query(ModelPricingHistory).filter(
            ModelPricingHistory.model_id == model_id,
            ModelPricingHistory.marketplace == marketplace,
            ModelPricingHistory.variant_key == variant_key
        ).order_by(desc(ModelPricingHistory.calculated_at)).limit(2).all()
        
        if len(history_rows) < 2:
            # Need at least 2 rows to compare
            # If only 1 row exists, we could arguably return it as "New Entry", 
            # but the Prompt Step 1 says: "If fewer than 2 rows: Return None or empty diff"
            return None
            
        new_row = history_rows[0]
        old_row = history_rows[1]
        
        changes = []
        
        # 2. Compare fields
        fields_to_compare = [
            'raw_cost_cents', 'base_cost_cents', 'retail_price_cents',
            'marketplace_fee_cents', 'profit_cents', 'material_cost_cents',
            'shipping_cost_cents', 'labor_cost_cents', 'weight_oz'
        ]
        
        for field in fields_to_compare:
            new_val = getattr(new_row, field)
            old_val = getattr(old_row, field)
            
            # Simple equality check with tolerance for float
            if isinstance(new_val, float) or isinstance(old_val, float):
                is_diff = abs(new_val - old_val) > 0.0001
            else:
                is_diff = new_val != old_val
                
            if is_diff:
                delta = new_val - old_val
                if delta > 0:
                    direction = "increase"
                elif delta < 0:
                    direction = "decrease"
                else:
                    direction = "unchanged" # Should not happen given is_diff check but safe fallback
                    
                changes.append(PricingFieldDiff(
                    field_name=field,
                    old_value=old_val,
                    new_value=new_val,
                    delta=delta,
                    direction=direction
                ))
                
        return PricingDiffResponse(
            model_id=model_id,
            marketplace=marketplace,
            variant_key=variant_key,
            calculated_at_old=old_row.calculated_at,
            calculated_at_new=new_row.calculated_at,
            changes=changes
        )
