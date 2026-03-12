from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class PricingFieldDiff(BaseModel):
    field_name: str
    old_value: Any
    new_value: Any
    delta: Any
    direction: str # "increase", "decrease", "unchanged"

class PricingDiffResponse(BaseModel):
    model_id: int
    marketplace: str
    variant_key: str
    calculated_at_old: Optional[datetime]
    calculated_at_new: Optional[datetime]
    changes: List[PricingFieldDiff]
