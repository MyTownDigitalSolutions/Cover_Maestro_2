import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from app.database import SessionLocal
import app.models.templates # Required for mapper configuration
from app.models.core import Model, LaborSetting, ModelPricingHistory, ModelPricingSnapshot
from app.services.pricing_calculator import PricingCalculator
import datetime

def verify_phase7():
    db = SessionLocal()
    try:
        model = db.query(Model).first()
        if not model:
            print("No model found. Seed data first.")
            return

        print(f"Testing Model: {model.name} (ID: {model.id})")

        # --- Test 1: Strict Surface Area ---
        print("\n[Test 1] Strict Surface Area Validation...")
        original_area = model.surface_area_sq_in
        
        # Set to invalid
        model.surface_area_sq_in = 0
        db.commit()
        
        try:
            PricingCalculator(db).calculate_model_prices(model.id)
            print("FAIL: Expected ValueError for missing surface area, but got success.")
        except ValueError as e:
            if "surface_area_sq_in is missing or invalid" in str(e):
                print("PASS: Caught expected error:", e)
            else:
                print("FAIL: Caught unexpected error:", e)
        except Exception as e:
            print("FAIL: Caught unexpected exception type:", type(e), e)
            
        # Restore
        model.surface_area_sq_in = original_area
        db.commit()
        
        # --- Test 2: History Insertion on Change ---
        print("\n[Test 2] History Insertion on Change...")
        
        # 1. Ensure baseline (recalc once, should generally be stable if no changes)
        PricingCalculator(db).calculate_model_prices(model.id)
        initial_history_count = db.query(ModelPricingHistory).filter(ModelPricingHistory.model_id == model.id).count()
        print(f"Initial History Count: {initial_history_count}")
        
        # 2. Modify Labor Settings to force a price change
        labor = db.query(LaborSetting).first()
        if not labor:
            labor = LaborSetting(hourly_rate_cents=2000)
            db.add(labor)
            db.commit()
            
        original_rate = labor.hourly_rate_cents
        labor.hourly_rate_cents += 500 # Increase rate
        db.commit()
        print(f"Changed Labor Rate from {original_rate} to {labor.hourly_rate_cents}")
        
        # 3. Recalculate
        PricingCalculator(db).calculate_model_prices(model.id)
        
        # 4. Verify History Increased by 4 (1 per variant)
        new_history_count = db.query(ModelPricingHistory).filter(ModelPricingHistory.model_id == model.id).count()
        print(f"New History Count: {new_history_count}")
        
        if new_history_count == initial_history_count + 4:
            print("PASS: History rows added correctly.")
        else:
            print(f"FAIL: Expected {initial_history_count + 4} rows, got {new_history_count}")

        # --- Test 3: Idempotency (No Change -> No History) ---
        print("\n[Test 3] Idempotency (No Change)...")
        PricingCalculator(db).calculate_model_prices(model.id)
        final_history_count = db.query(ModelPricingHistory).filter(ModelPricingHistory.model_id == model.id).count()
        print(f"Final History Count: {final_history_count}")
        
        if final_history_count == new_history_count:
            print("PASS: No extra history rows added on untriggered recalc.")
        else:
            print(f"FAIL: History count changed! Expected {new_history_count}, got {final_history_count}")

            
        # Restore Labor
        labor.hourly_rate_cents = original_rate
        db.commit()

        # Check Data Integrity
        history_rows = db.query(ModelPricingHistory).filter(ModelPricingHistory.model_id == model.id).order_by(ModelPricingHistory.calculated_at.desc()).limit(4).all()
        if history_rows:
            print("\nLatest History Row Sample:")
            r = history_rows[0]
            print(f"Variant: {r.variant_key}")
            print(f"Retail: {r.retail_price_cents}")
            print(f"Reason: {r.reason}")
            if r.reason == "recalculate":
                print("PASS: Reason field populated.")
            else:
                print("FAIL: Reason field incorrect.")

    except Exception as e:
        print(f"CRITICAL FAIL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_phase7()
