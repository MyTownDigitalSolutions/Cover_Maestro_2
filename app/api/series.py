from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.database import get_db
from app.models.core import Series
from app.schemas.core import SeriesCreate, SeriesResponse

router = APIRouter(prefix="/series", tags=["series"])

@router.get("", response_model=List[SeriesResponse])
def list_series(manufacturer_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Series)
    if manufacturer_id:
        query = query.filter(Series.manufacturer_id == manufacturer_id)
    return query.order_by(Series.name.asc()).all()

@router.get("/{id}", response_model=SeriesResponse)
def get_series(id: int, db: Session = Depends(get_db)):
    series = db.query(Series).filter(Series.id == id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return series

@router.post("", response_model=SeriesResponse)
def create_series(data: SeriesCreate, db: Session = Depends(get_db)):
    try:
        series = Series(name=data.name, manufacturer_id=data.manufacturer_id)
        db.add(series)
        db.commit()
        db.refresh(series)
        return series
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Series with this name already exists for this manufacturer")

@router.put("/{id}", response_model=SeriesResponse)
def update_series(id: int, data: SeriesCreate, db: Session = Depends(get_db)):
    series = db.query(Series).filter(Series.id == id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    try:
        series.name = data.name
        series.manufacturer_id = data.manufacturer_id
        db.commit()
        db.refresh(series)
        return series
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Series with this name already exists for this manufacturer")

@router.delete("/{id}")
def delete_series(id: int, db: Session = Depends(get_db)):
    series = db.query(Series).filter(Series.id == id).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    # Check for dependent models
    model_count = len(series.models)
    if model_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete series '{series.name}' because it has {model_count} models listed under it."
        )

    db.delete(series)
    db.commit()
    return {"message": "Series deleted"}
