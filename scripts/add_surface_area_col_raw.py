import sys
import os
import sqlite3

# Add the project root to the python path
sys.path.append(os.getcwd())

WASTE_FACTOR = 0.05

def calculate_surface_area(width, depth, height):
    base_area = 2 * (width * depth + width * height + depth * height)
    return base_area * (1 + WASTE_FACTOR)

def migrate():
    # Connect directly to SQLite
    db_path = "cover_app.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Connected to database: {db_path}")

    # 1. Add Column
    print("Checking if 'surface_area_sq_in' column exists...")
    try:
        # Check by trying to select it
        cursor.execute("SELECT surface_area_sq_in FROM models LIMIT 1")
        print("Column 'surface_area_sq_in' already exists.")
    except sqlite3.OperationalError:
        print("Column does not exist. Adding...")
        try:
            cursor.execute("ALTER TABLE models ADD COLUMN surface_area_sq_in FLOAT")
            conn.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
            return

    # 2. Backfill Data
    print("Backfilling surface area calculations...")
    
    # Get all models
    cursor.execute("SELECT id, width, depth, height, surface_area_sq_in FROM models")
    rows = cursor.fetchall()
    
    count = 0
    for row in rows:
        model_id, width, depth, height, existing_area = row
        
        # Calculate
        area = calculate_surface_area(width, depth, height)
        
        # Always update to ensure accuracy
        cursor.execute(
            "UPDATE models SET surface_area_sq_in = ? WHERE id = ?",
            (area, model_id)
        )
        count += 1
            
    conn.commit()
    print(f"Updated {count} models with surface area calculations.")
    conn.close()

if __name__ == "__main__":
    migrate()
