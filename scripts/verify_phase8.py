import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from app.database import SessionLocal
import app.models.templates 
from app.models.core import Model, LaborSetting, ModelPricingHistory
from app.services.pricing_calculator import PricingCalculator
from app.services.pricing_diff_service import PricingDiffService
from app.schemas.pricing_diff import PricingDiffResponse

def verify_phase8():
    db = SessionLocal()
    try:
        model = db.query(Model).first()
        if not model:
            print("No model found. Seed data first.")
            return
            
        print(f"Testing Diff on Model: {model.name} (ID: {model.id})")
        marketplace = "DEFAULT"
        variant_key = "premium_with_padding" # Pick one
        
        # 1. Baseline
        PricingCalculator(db).calculate_model_prices(model.id)
        
        # 2. Change Inputs to force NEW history
        labor = db.query(LaborSetting).first()
        original_rate = labor.hourly_rate_cents
        labor.hourly_rate_cents += 1000 # Big Jump
        db.commit()
        print(f"Changed Labor Rate: {original_rate} -> {labor.hourly_rate_cents}")
        
        # 3. Recalculate (Generates new history row)
        PricingCalculator(db).calculate_model_prices(model.id)
        
        # 4. Call Diff Service
        diff_service = PricingDiffService(db)
        diff = diff_service.diff_latest(model.id, marketplace, variant_key)
        
        if not diff:
            print("FAIL: No diff returned. Check history usage.")
            return
            
        print(f"Diff Detected: {len(diff.changes)} changes.")
        
        valid_fields = ["labor_cost_cents", "raw_cost_cents", "retail_price_cents"]
        
        for change in diff.changes:
             print(f"  Field: {change.field_name} | {change.old_value} -> {change.new_value} ({change.direction})")
             
             if change.field_name == "labor_cost_cents":
                 if change.direction != "increase":
                     print("FAIL: Labor cost should increase.")
                 else:
                     print("PASS: Labor cost increase detected.")
                     
        # 5. Restore & Recalculate (New History Row, prices go down)
        labor.hourly_rate_cents = original_rate
        db.commit()
        PricingCalculator(db).calculate_model_prices(model.id)
        
        # 6. Call Diff Again (Should see Decrease)
        diff2 = diff_service.diff_latest(model.id, marketplace, variant_key)
        print(f"\nDiff 2 (Restore): {len(diff2.changes)} changes.")
        for change in diff2.changes:
             if change.field_name == "labor_cost_cents":
                 print(f"  Field: {change.field_name} ({change.direction})")
                 if change.direction == "decrease":
                     print("PASS: Labor cost decrease detected.")
                 else:
                     print("FAIL: Labor cost should decrease.")

    except Exception as e:
        print(f"CRITICAL FAIL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_phase8()
