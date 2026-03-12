from fastapi import APIRouter
from app.models.enums import HandleLocation, AngleType, Carrier, Marketplace

router = APIRouter(prefix="/enums", tags=["enums"])

@router.get("/handle-locations")
def get_handle_locations():
    return [{"value": e.value, "name": e.name} for e in HandleLocation]

@router.get("/angle-types")
def get_angle_types():
    return [{"value": e.value, "name": e.name} for e in AngleType]

@router.get("/carriers")
def get_carriers():
    return [{"value": e.value, "name": e.name} for e in Carrier]

@router.get("/marketplaces")
def get_marketplaces():
    return [{"value": e.value, "name": e.name} for e in Marketplace]
