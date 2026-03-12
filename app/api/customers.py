"""
Customers API - CRUD operations for customer records.

Admin-protected endpoints using X-Admin-Key header.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.core import Customer
from app.schemas.core import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["customers"])


# ============================================================
# Admin Key Configuration
# ============================================================

ADMIN_KEY = os.getenv("ADMIN_KEY", "")


def verify_admin_key(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    """
    Dependency that verifies the X-Admin-Key header.
    Returns 401 if ADMIN_KEY is not configured or header doesn't match.
    """
    if not ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Admin operations are disabled (ADMIN_KEY not configured)"
        )
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin key"
        )
    return True


# ============================================================
# Customer Endpoints
# ============================================================

@router.get("", response_model=List[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    """List all customers."""
    return db.query(Customer).order_by(Customer.id.desc()).all()


@router.get("/{id}", response_model=CustomerResponse)
def get_customer(id: int, db: Session = Depends(get_db)):
    """Get a single customer by ID."""
    customer = db.query(Customer).filter(Customer.id == id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("", response_model=CustomerResponse)
def create_customer(
    data: CustomerCreate, 
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """Create a new customer. Admin-protected."""
    customer = Customer(
        name=data.name,
        first_name=data.first_name,
        last_name=data.last_name,
        buyer_email=data.buyer_email,
        phone=data.phone,
        mobile_phone=data.mobile_phone,
        work_phone=data.work_phone,
        other_phone=data.other_phone,
        address=data.address,
        billing_address1=data.billing_address1,
        billing_address2=data.billing_address2,
        billing_city=data.billing_city,
        billing_state=data.billing_state,
        billing_postal_code=data.billing_postal_code,
        billing_country=data.billing_country,
        shipping_name=data.shipping_name,
        shipping_address1=data.shipping_address1,
        shipping_address2=data.shipping_address2,
        shipping_city=data.shipping_city,
        shipping_state=data.shipping_state,
        shipping_postal_code=data.shipping_postal_code,
        shipping_country=data.shipping_country,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/{id}", response_model=CustomerResponse)
def update_customer(
    id: int, 
    data: CustomerUpdate, 
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """Update a customer. Admin-protected. Only updates provided fields."""
    customer = db.query(Customer).filter(Customer.id == id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{id}")
def delete_customer(
    id: int, 
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """Delete a customer. Admin-protected."""
    customer = db.query(Customer).filter(Customer.id == id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted"}
