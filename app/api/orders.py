from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.core import Order, OrderLine
from app.schemas.core import OrderCreate, OrderResponse, OrderLineCreate, OrderLineResponse

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("", response_model=List[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()

@router.get("/{id}", response_model=OrderResponse)
def get_order(id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("", response_model=OrderResponse)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    order = Order(
        customer_id=data.customer_id,
        marketplace=data.marketplace,
        marketplace_order_number=data.marketplace_order_number
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    for line_data in data.order_lines:
        line = OrderLine(
            order_id=order.id,
            model_id=line_data.model_id,
            material_id=line_data.material_id,
            colour=line_data.colour,
            quantity=line_data.quantity,
            handle_zipper=line_data.handle_zipper,
            two_in_one_pocket=line_data.two_in_one_pocket,
            music_rest_zipper=line_data.music_rest_zipper,
            unit_price=line_data.unit_price
        )
        db.add(line)
    
    db.commit()
    db.refresh(order)
    return order

@router.delete("/{id}")
def delete_order(id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": "Order deleted"}

@router.post("/{id}/lines", response_model=OrderLineResponse)
def add_order_line(id: int, data: OrderLineCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    line = OrderLine(
        order_id=id,
        model_id=data.model_id,
        material_id=data.material_id,
        colour=data.colour,
        quantity=data.quantity,
        handle_zipper=data.handle_zipper,
        two_in_one_pocket=data.two_in_one_pocket,
        music_rest_zipper=data.music_rest_zipper,
        unit_price=data.unit_price
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line
