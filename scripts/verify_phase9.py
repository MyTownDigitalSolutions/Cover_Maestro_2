import sys
import os
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.core import Model, ModelPricingSnapshot
from app.api.export import build_export_data
from fastapi import HTTPException
import datetime

# Mock Request class
class MockRequest:
    def __init__(self, model_ids, listing_type="individual"):
        self.model_ids = model_ids
        self.listing_type = listing_type

def verify_phase9_export_logic():
    print("Testing Amazon Export Logic (Phase 9)...")
    db = SessionLocal()
    snapshot = None
    try:
        model = db.query(Model).first()
        if not model:
            print("No model found. Seed data first.")
            return

        # 1. Manually Insert Snapshot (Bypass Calc complexity)
        print(f"Bypassing calc, inserting mock snapshot for Model {model.id}...")
        
        # Clean up existing if any
        existing = db.query(ModelPricingSnapshot).filter(
            ModelPricingSnapshot.model_id == model.id,
            ModelPricingSnapshot.marketplace == "amazon",
            ModelPricingSnapshot.variant_key == "choice_no_padding"
        ).first()
        if existing:
            db.delete(existing)
            db.commit()

        snapshot = ModelPricingSnapshot(
            model_id=model.id,
            marketplace="amazon",
            variant_key="choice_no_padding",
            raw_cost_cents=1000,
            base_cost_cents=2000,
            retail_price_cents=12345, # $123.45
            marketplace_fee_cents=500,
            profit_cents=500,
            material_cost_cents=500,
            shipping_cost_cents=500,
            labor_cost_cents=500,
            weight_oz=100.0,
            calculated_at=datetime.datetime.utcnow()
        )
        db.add(snapshot)
        db.commit()
        print("Mock snapshot inserted.")

        expected_price_str = "123.45"
        
        # 2. Test Export Preview (Success Case)
        print("\n[Test 1] Export with existing snapshot...")
        req = MockRequest(model_ids=[model.id])
        
        try:
            headers, data_rows, filename = build_export_data(req, db)
            
            row = data_rows[0]
            # We look for the exact string value in the row
            if expected_price_str in row:
                print(f"PASS: Found expected price '{expected_price_str}' in export data.")
            else:
                print(f"FAIL: Price '{expected_price_str}' NOT found in export data.")
                # print("Row Data sample:", row) 
        except Exception as e:
            print(f"FAIL: Export generation failed: {e}")
            import traceback
            traceback.print_exc()

        # 3. Test Failure Case (Missing Snapshot)
        print("\n[Test 2] Export with MISSING snapshot (Strict Mode)...")
        
        db.delete(snapshot)
        db.commit()
        snapshot = None # Marker that it's gone
        
        try:
            build_export_data(req, db)
            print("FAIL: Export should have raised HTTPException but succeeded.")
        except HTTPException as e:
            if e.status_code == 400 and "Missing baseline pricing snapshot" in e.detail:
                print("PASS: Caught expected 400 error for missing snapshot.")
            else:
                print(f"FAIL: Caught unexpected exception: {e}")
        except Exception as e:
            print(f"FAIL: Caught unexpected exception type: {type(e)}")

    finally:
        if snapshot:
            # Cleanup if verification crashed before delete
            try:
                db.delete(snapshot)
                db.commit()
            except: pass
        db.close()

if __name__ == "__main__":
    verify_phase9_export_logic()
