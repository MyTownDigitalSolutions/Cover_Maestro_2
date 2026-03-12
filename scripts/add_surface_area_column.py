import sys
import os

# Add the project root to the python path so we can import app modules
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, configure_mappers
import app.models.core

# Ensure all models are registered and relationships resolved
configure_mappers()

from app.database import Base

WASTE_FACTOR = 0.05

def calculate_surface_area(width, depth, height):
    base_area = 2 * (width * depth + width * height + depth * height)
    return base_area * (1 + WASTE_FACTOR)

def migrate():
    # Database URL
    SQLALCHEMY_DATABASE_URL = "sqlite:///./cover_app.db"
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    print("Checking if 'surface_area_sq_in' column exists...")
    try:
        # Try to select the column to see if it exists
        db.execute(text("SELECT surface_area_sq_in FROM models LIMIT 1"))
        print("Column 'surface_area_sq_in' already exists.")
    except Exception:
        print("Column does not exist. Adding...")
        # Add the column
        try:
            db.execute(text("ALTER TABLE models ADD COLUMN surface_area_sq_in FLOAT"))
            db.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
            return

    print("Backfilling surface area calculations...")
    models = db.query(app.models.core.Model).all()
    count = 0
    for model in models:
        # Calculate new area
        area = calculate_surface_area(model.width, model.depth, model.height)
        
        # Update if it's currently None or we just want to ensure it's correct
        if model.surface_area_sq_in is None:
             model.surface_area_sq_in = area
             count += 1
    
    db.commit()
    print(f"Updated {count} models with surface area calculations.")
    db.close()

if __name__ == "__main__":
    migrate()
