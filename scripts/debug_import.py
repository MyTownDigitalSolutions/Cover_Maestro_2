import sys
import os
sys.path.append(os.getcwd())

from app.database import Base
from app.models.core import *
from sqlalchemy.orm import configure_mappers

print("Imported models successfully.")
try:
    configure_mappers()
    print("Mappers configured successfully.")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
