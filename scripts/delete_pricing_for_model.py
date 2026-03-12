import sys
import os

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.core import Model, ModelPricingSnapshot

def delete_pricing(model_id):
    db = SessionLocal()
    try:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            print(f"Model {model_id} not found.")
            return

        snapshots = db.query(ModelPricingSnapshot).filter(ModelPricingSnapshot.model_id == model_id).all()
        count = len(snapshots)
        for s in snapshots:
            db.delete(s)
        
        db.commit()
        print(f"Deleted {count} pricing snapshots for Model {model_id} '{model.name}'.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_pricing_for_model.py <model_id>")
        sys.exit(1)
    
    delete_pricing(int(sys.argv[1]))
