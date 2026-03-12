import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from app.database import SessionLocal
import app.models.templates  # Required for mappers
from app.models.core import Model, ModelPricingHistory, ModelPricingSnapshot

# Deterministic Seed Data provided in Phase 10 Prompt
# Row 1 — now - 28 days
ROW_1 = {
    "offset_days": 28,
    "raw_cost_cents": 7800,
    "material_cost_cents": 4200,
    "labor_cost_cents": 2100,
    "shipping_cost_cents": 900,
    "base_cost_cents": 9200,
    "marketplace_fee_cents": 1800,
    "profit_cents": 2000,
    "retail_price_cents": 13000,
    "weight_oz": 48.0
}
# Row 2 — now - 21 days
ROW_2 = {
    "offset_days": 21,
    "raw_cost_cents": 8100,
    "material_cost_cents": 4500,
    "labor_cost_cents": 2100,
    "shipping_cost_cents": 900,
    "base_cost_cents": 9500,
    "marketplace_fee_cents": 1850,
    "profit_cents": 2000,
    "retail_price_cents": 13350,
    "weight_oz": 48.0
}
# Row 3 — now - 14 days
ROW_3 = {
    "offset_days": 14,
    "raw_cost_cents": 8300,
    "material_cost_cents": 4500,
    "labor_cost_cents": 2100,
    "shipping_cost_cents": 1100,
    "base_cost_cents": 9700,
    "marketplace_fee_cents": 1900,
    "profit_cents": 2000,
    "retail_price_cents": 13600,
    "weight_oz": 50.0
}
# Row 4 — now - 7 days
ROW_4 = {
    "offset_days": 7,
    "raw_cost_cents": 8300,
    "material_cost_cents": 4500,
    "labor_cost_cents": 2100,
    "shipping_cost_cents": 1100,
    "base_cost_cents": 9700,
    "marketplace_fee_cents": 1950,
    "profit_cents": 2300,
    "retail_price_cents": 13950,
    "weight_oz": 50.0
}
# Row 5 — now (latest/current)
ROW_5 = {
    "offset_days": 0,
    "raw_cost_cents": 8600,
    "material_cost_cents": 4800,
    "labor_cost_cents": 2100,
    "shipping_cost_cents": 1200,
    "base_cost_cents": 10100,
    "marketplace_fee_cents": 2000,
    "profit_cents": 2400,
    "retail_price_cents": 14500,
    "weight_oz": 52.0
}

SEED_ROWS = [ROW_1, ROW_2, ROW_3, ROW_4, ROW_5]

def seed_pricing_history():
    parser = argparse.ArgumentParser(description="Seed deterministic pricing history for dev testing.")
    parser.add_argument("--model-ids", type=str, help="Comma separated model IDs")
    parser.add_argument("--count-models", type=int, default=5, help="Number of models to seed if IDs not specified")
    parser.add_argument("--force", action="store_true", help="Force run in non-dev environment")
    parser.add_argument("--append", action="store_true", help="Append new rows even if history exists")
    
    args = parser.parse_args()
    
    # Dev Guard
    # (Simplified for this environment since we are devs, but good practice)
    if not args.force and os.getenv("ENV") == "production":
        print("Blocked in production without --force")
        return

    db = SessionLocal()
    try:
        models = []
        if args.model_ids:
            ids = [int(x) for x in args.model_ids.split(",")]
            models = db.query(Model).filter(Model.id.in_(ids)).all()
        else:
            models = db.query(Model).order_by(Model.id).limit(args.count_models).all()
            
        print(f"Seeding history for {len(models)} models...")
        
        for model in models:
            variant = "choice_no_padding"
            marketplace = "amazon"
            
            # Check existing
            existing_count = db.query(ModelPricingHistory).filter(
                ModelPricingHistory.model_id == model.id,
                ModelPricingHistory.marketplace == marketplace,
                ModelPricingHistory.variant_key == variant
            ).count()
            
            if existing_count > 0 and not args.append:
                print(f"Skipping Model {model.id} (history exists: {existing_count} rows)")
                continue

            print(f"Generating history for Model {model.id}...")
            
            now = datetime.utcnow()
            
            for row_data in SEED_ROWS:
                calc_at = now - timedelta(days=row_data["offset_days"])
                
                # Insert History
                h = ModelPricingHistory(
                    model_id=model.id,
                    marketplace=marketplace,
                    variant_key=variant,
                    calculated_at=calc_at,
                    reason="seed_demo",
                    
                    raw_cost_cents=row_data["raw_cost_cents"],
                    material_cost_cents=row_data["material_cost_cents"],
                    labor_cost_cents=row_data["labor_cost_cents"],
                    shipping_cost_cents=row_data["shipping_cost_cents"],
                    base_cost_cents=row_data["base_cost_cents"],
                    marketplace_fee_cents=row_data["marketplace_fee_cents"],
                    profit_cents=row_data["profit_cents"],
                    retail_price_cents=row_data["retail_price_cents"],
                    weight_oz=row_data["weight_oz"]
                )
                db.add(h)
                
            # Upsert Snapshot (Row 5 - Latest)
            last = SEED_ROWS[-1]
            
            existing_snap = db.query(ModelPricingSnapshot).filter(
                ModelPricingSnapshot.model_id == model.id,
                ModelPricingSnapshot.marketplace == marketplace,
                ModelPricingSnapshot.variant_key == variant
            ).first()
            
            if existing_snap:
                # Update
                existing_snap.raw_cost_cents = last["raw_cost_cents"]
                existing_snap.material_cost_cents = last["material_cost_cents"]
                existing_snap.labor_cost_cents = last["labor_cost_cents"]
                existing_snap.shipping_cost_cents = last["shipping_cost_cents"]
                existing_snap.base_cost_cents = last["base_cost_cents"]
                existing_snap.marketplace_fee_cents = last["marketplace_fee_cents"]
                existing_snap.profit_cents = last["profit_cents"]
                existing_snap.retail_price_cents = last["retail_price_cents"]
                existing_snap.weight_oz = last["weight_oz"]
                existing_snap.calculated_at = now
            else:
                # Create
                snap = ModelPricingSnapshot(
                    model_id=model.id,
                    marketplace=marketplace,
                    variant_key=variant,
                    calculated_at=now,
                    
                    raw_cost_cents=last["raw_cost_cents"],
                    material_cost_cents=last["material_cost_cents"],
                    labor_cost_cents=last["labor_cost_cents"],
                    shipping_cost_cents=last["shipping_cost_cents"],
                    base_cost_cents=last["base_cost_cents"],
                    marketplace_fee_cents=last["marketplace_fee_cents"],
                    profit_cents=last["profit_cents"],
                    retail_price_cents=last["retail_price_cents"],
                    weight_oz=last["weight_oz"]
                )
                db.add(snap)
            
            db.commit()
            print(f"Model {model.id} seeded successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_pricing_history()
