"""
Marketplace Orders API - Canonical Order Import Tables

Provides endpoints for:
- Upserting orders from marketplace API imports
- Creating manual orders
- Querying orders with filters
- Deduplicating shipments (admin-only maintenance)
"""
import os
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models import templates  # Ensure AmazonCustomizationTemplate is registered for SQLAlchemy relationships
from app.models.core import (
    MarketplaceOrder, MarketplaceOrderAddress, MarketplaceOrderLine, 
    MarketplaceOrderShipment, MarketplaceImportRun, Model, MarketplaceListing
)
from app.api.models import lookup_models_by_marketplace_listing
from app.models.enums import OrderSource, NormalizedOrderStatus, Marketplace
from app.schemas.core import (
    MarketplaceOrderCreate, MarketplaceOrderUpdate, MarketplaceOrderResponse,
    MarketplaceOrderDetailResponse, MarketplaceOrderAddressCreate,
    MarketplaceOrderLineCreate, MarketplaceOrderShipmentCreate,
    MarketplaceOrderLineResponse
)
from app.services.customer_service import upsert_customer_from_marketplace_order, extract_address_dict

router = APIRouter(prefix="/marketplace-orders", tags=["marketplace-orders"])


# ============================================================
# Admin Key Configuration (same pattern as marketplace_credentials.py)
# ============================================================

ADMIN_KEY = os.getenv("ADMIN_KEY", "")


def verify_admin_key(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    """
    Dependency that verifies the X-Admin-Key header.
    Returns 401 if ADMIN_KEY is not configured or header doesn't match.
    """
    if not ADMIN_KEY:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_KEY environment variable not configured"
        )
    
    if not x_admin_key:
        raise HTTPException(
            status_code=401,
            detail="X-Admin-Key header required"
        )
    
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin key"
        )
    
    return True


# ============================================================
# Shipment Cleanup Request/Response Models
# ============================================================

class CleanupShipmentsRequest(BaseModel):
    marketplace: str = "reverb"
    order_id: Optional[int] = None
    dry_run: bool = True
    mode: Literal["strict", "prefer_tracked"] = "strict"


class CleanupShipmentsResponse(BaseModel):
    dry_run: bool
    marketplace: str
    order_id: Optional[int]
    mode: str
    rows_scanned: int
    duplicate_groups_found: int
    rows_to_delete: int
    rows_deleted: int
    affected_order_ids_sample: List[int]


def _replace_children_if_provided(
    db: Session, 
    order: MarketplaceOrder, 
    data: MarketplaceOrderCreate,
    raw_data: dict
):
    """
    Replace child records only when the field is explicitly provided in the request.
    
    Rules:
    - If field is missing/not in payload → leave existing children unchanged
    - If field is present as [] → delete all children of that type
    - If field is present with N items → delete all then insert N
    """
    
    # Handle addresses - only if 'addresses' key exists in raw payload
    if 'addresses' in raw_data:
        deleted_count = db.query(MarketplaceOrderAddress).filter(
            MarketplaceOrderAddress.order_id == order.id
        ).delete(synchronize_session=False)
        
        inserted_count = 0
        for addr_data in data.addresses:
            addr = MarketplaceOrderAddress(
                order_id=order.id,
                address_type=addr_data.address_type,
                name=addr_data.name,
                phone=addr_data.phone,
                company=addr_data.company,
                line1=addr_data.line1,
                line2=addr_data.line2,
                city=addr_data.city,
                state_or_region=addr_data.state_or_region,
                postal_code=addr_data.postal_code,
                country_code=addr_data.country_code,
                raw_payload=addr_data.raw_payload
            )
            db.add(addr)
            inserted_count += 1
        
        print(f"[MARKETPLACE_ORDERS]   addresses: deleted={deleted_count}, inserted={inserted_count}")
    
    # Handle lines - only if 'lines' key exists in raw payload
    if 'lines' in raw_data:
        deleted_count = db.query(MarketplaceOrderLine).filter(
            MarketplaceOrderLine.order_id == order.id
        ).delete(synchronize_session=False)
        
        inserted_count = 0
        for line_data in data.lines:
            line = MarketplaceOrderLine(
                order_id=order.id,
                external_line_item_id=line_data.external_line_item_id,
                marketplace_item_id=line_data.marketplace_item_id,
                sku=line_data.sku,
                asin=line_data.asin,
                listing_id=line_data.listing_id,
                product_id=line_data.product_id,
                title=line_data.title,
                variant=line_data.variant,
                quantity=line_data.quantity,
                currency_code=line_data.currency_code,
                unit_price_cents=line_data.unit_price_cents,
                line_subtotal_cents=line_data.line_subtotal_cents,
                tax_cents=line_data.tax_cents,
                discount_cents=line_data.discount_cents,
                line_total_cents=line_data.line_total_cents,
                fulfillment_status_raw=line_data.fulfillment_status_raw,
                fulfillment_status_normalized=line_data.fulfillment_status_normalized,
                model_id=line_data.model_id,
                customization_data=line_data.customization_data,
                raw_marketplace_data=line_data.raw_marketplace_data
            )
            db.add(line)
            inserted_count += 1
        
        print(f"[MARKETPLACE_ORDERS]   lines: deleted={deleted_count}, inserted={inserted_count}")
    
    # Handle shipments - only if 'shipments' key exists in raw payload
    if 'shipments' in raw_data:
        deleted_count = db.query(MarketplaceOrderShipment).filter(
            MarketplaceOrderShipment.order_id == order.id
        ).delete(synchronize_session=False)
        
        inserted_count = 0
        for ship_data in data.shipments:
            shipment = MarketplaceOrderShipment(
                order_id=order.id,
                external_shipment_id=ship_data.external_shipment_id,
                carrier=ship_data.carrier,
                service=ship_data.service,
                tracking_number=ship_data.tracking_number,
                shipped_at=ship_data.shipped_at,
                delivered_at=ship_data.delivered_at,
                raw_marketplace_data=ship_data.raw_marketplace_data
            )
            db.add(shipment)
            inserted_count += 1
        
        print(f"[MARKETPLACE_ORDERS]   shipments: deleted={deleted_count}, inserted={inserted_count}")


def _insert_children(db: Session, order: MarketplaceOrder, data: MarketplaceOrderCreate):
    """
    Insert child records for a new order (no replacement logic needed).
    Used for manual orders and initial create.
    """
    # Insert addresses
    for addr_data in data.addresses:
        addr = MarketplaceOrderAddress(
            order_id=order.id,
            address_type=addr_data.address_type,
            name=addr_data.name,
            phone=addr_data.phone,
            company=addr_data.company,
            line1=addr_data.line1,
            line2=addr_data.line2,
            city=addr_data.city,
            state_or_region=addr_data.state_or_region,
            postal_code=addr_data.postal_code,
            country_code=addr_data.country_code,
            raw_payload=addr_data.raw_payload
        )
        db.add(addr)
    
    # Insert lines
    for line_data in data.lines:
        line = MarketplaceOrderLine(
            order_id=order.id,
            external_line_item_id=line_data.external_line_item_id,
            marketplace_item_id=line_data.marketplace_item_id,
            sku=line_data.sku,
            asin=line_data.asin,
            listing_id=line_data.listing_id,
            product_id=line_data.product_id,
            title=line_data.title,
            variant=line_data.variant,
            quantity=line_data.quantity,
            currency_code=line_data.currency_code,
            unit_price_cents=line_data.unit_price_cents,
            line_subtotal_cents=line_data.line_subtotal_cents,
            tax_cents=line_data.tax_cents,
            discount_cents=line_data.discount_cents,
            line_total_cents=line_data.line_total_cents,
            fulfillment_status_raw=line_data.fulfillment_status_raw,
            fulfillment_status_normalized=line_data.fulfillment_status_normalized,
            model_id=line_data.model_id,
            customization_data=line_data.customization_data,
            raw_marketplace_data=line_data.raw_marketplace_data
        )
        db.add(line)
    
    # Insert shipments
    for ship_data in data.shipments:
        shipment = MarketplaceOrderShipment(
            order_id=order.id,
            external_shipment_id=ship_data.external_shipment_id,
            carrier=ship_data.carrier,
            service=ship_data.service,
            tracking_number=ship_data.tracking_number,
            shipped_at=ship_data.shipped_at,
            delivered_at=ship_data.delivered_at,
            raw_marketplace_data=ship_data.raw_marketplace_data
        )
        db.add(shipment)
    
    child_summary = f"addresses={len(data.addresses)}, lines={len(data.lines)}, shipments={len(data.shipments)}"
    print(f"[MARKETPLACE_ORDERS]   children inserted: {child_summary}")


def _update_order_fields_selective(order: MarketplaceOrder, data: MarketplaceOrderCreate, raw_data: dict):
    """
    Update order fields selectively - only update fields that are explicitly provided.
    Preserves existing values when incoming is None/missing.
    """
    # Always update these core identification fields
    if 'source' in raw_data:
        order.source = data.source
    if 'marketplace' in raw_data:
        order.marketplace = data.marketplace
    if 'external_order_id' in raw_data:
        order.external_order_id = data.external_order_id
    if 'external_order_number' in raw_data:
        order.external_order_number = data.external_order_number
    if 'external_store_id' in raw_data:
        order.external_store_id = data.external_store_id
    
    # Date fields
    if 'order_date' in raw_data:
        order.order_date = data.order_date
    if 'created_at_external' in raw_data:
        order.created_at_external = data.created_at_external
    if 'updated_at_external' in raw_data:
        order.updated_at_external = data.updated_at_external
    
    # Status fields
    if 'status_raw' in raw_data:
        order.status_raw = data.status_raw
    if 'status_normalized' in raw_data:
        order.status_normalized = data.status_normalized
    
    # Buyer fields
    if 'buyer_name' in raw_data:
        order.buyer_name = data.buyer_name
    if 'buyer_email' in raw_data:
        order.buyer_email = data.buyer_email
    if 'buyer_phone' in raw_data:
        order.buyer_phone = data.buyer_phone
    
    # Money fields
    if 'currency_code' in raw_data:
        order.currency_code = data.currency_code
    if 'items_subtotal_cents' in raw_data:
        order.items_subtotal_cents = data.items_subtotal_cents
    if 'shipping_cents' in raw_data:
        order.shipping_cents = data.shipping_cents
    if 'tax_cents' in raw_data:
        order.tax_cents = data.tax_cents
    if 'discount_cents' in raw_data:
        order.discount_cents = data.discount_cents
    if 'fees_cents' in raw_data:
        order.fees_cents = data.fees_cents
    if 'refunded_cents' in raw_data:
        order.refunded_cents = data.refunded_cents
    if 'order_total_cents' in raw_data:
        order.order_total_cents = data.order_total_cents
    
    # Fulfillment fields
    if 'fulfillment_channel' in raw_data:
        order.fulfillment_channel = data.fulfillment_channel
    if 'shipping_service_level' in raw_data:
        order.shipping_service_level = data.shipping_service_level
    if 'ship_by_date' in raw_data:
        order.ship_by_date = data.ship_by_date
    if 'deliver_by_date' in raw_data:
        order.deliver_by_date = data.deliver_by_date
    
    # Ops fields
    if 'notes' in raw_data:
        order.notes = data.notes
    if 'import_error' in raw_data:
        order.import_error = data.import_error
    if 'raw_marketplace_data' in raw_data:
        order.raw_marketplace_data = data.raw_marketplace_data
    if 'import_run_id' in raw_data:
        order.import_run_id = data.import_run_id


@router.post("/upsert", response_model=MarketplaceOrderDetailResponse)
def upsert_marketplace_order(data: MarketplaceOrderCreate, db: Session = Depends(get_db)):
    """
    Upsert a marketplace order.
    
    - If marketplace + external_order_id exists: update existing order
    - Otherwise: create new order
    - Only replaces children (addresses, lines, shipments) if those fields are present in request
    - Only updates scalar fields that are explicitly provided
    """
    try:
        now = datetime.utcnow()
        
        # Get the raw dict to check which fields were actually provided
        raw_data = data.model_dump(exclude_unset=True)
        
        # Validation: if marketplace is set, external_order_id is required
        if data.marketplace is not None and not data.external_order_id:
            raise HTTPException(
                status_code=400,
                detail="external_order_id is required when marketplace is set"
            )
        
        existing_order = None
        if data.marketplace is not None and data.external_order_id:
            existing_order = db.query(MarketplaceOrder).filter(
                MarketplaceOrder.marketplace == data.marketplace,
                MarketplaceOrder.external_order_id == data.external_order_id
            ).first()
        
        if existing_order:
            # UPDATE path
            print(f"[MARKETPLACE_ORDERS] action=UPDATE marketplace={data.marketplace} external_order_id={data.external_order_id} order_id={existing_order.id}")
            
            _update_order_fields_selective(existing_order, data, raw_data)
            existing_order.last_synced_at = now
            
            # Replace children only if provided in payload
            _replace_children_if_provided(db, existing_order, data, raw_data)
            
            # Upsert customer and link to order (if marketplace order)
            if data.marketplace:
                # Extract source_customer_id from raw_marketplace_data if available
                source_customer_id = None
                if data.raw_marketplace_data:
                    # Try common buyer ID field names from various marketplaces
                    source_customer_id = (
                        data.raw_marketplace_data.get('buyer_id') or
                        data.raw_marketplace_data.get('buyer', {}).get('id') or
                        data.raw_marketplace_data.get('BuyerInfo', {}).get('BuyerEmail')  # Amazon uses email as ID
                    )
                
                # Get addresses from existing order or data
                shipping_addr = extract_address_dict(
                    [a.model_dump() for a in data.addresses] if data.addresses else [], 
                    'shipping'
                )
                billing_addr = extract_address_dict(
                    [a.model_dump() for a in data.addresses] if data.addresses else [], 
                    'billing'
                )
                
                customer, _ = upsert_customer_from_marketplace_order(
                    db=db,
                    marketplace=data.marketplace.value if hasattr(data.marketplace, 'value') else str(data.marketplace),
                    source_customer_id=source_customer_id,
                    marketplace_buyer_email=data.buyer_email,
                    buyer_name=data.buyer_name,
                    buyer_phone=data.buyer_phone,
                    shipping_address=shipping_addr,
                    billing_address=billing_addr
                )
                if customer and not existing_order.customer_id:
                    existing_order.customer_id = customer.id
            
            db.commit()
            db.refresh(existing_order)
            return existing_order
        else:
            # CREATE path
            order = MarketplaceOrder(
                import_run_id=data.import_run_id,
                source=data.source,
                marketplace=data.marketplace,
                external_order_id=data.external_order_id,
                external_order_number=data.external_order_number,
                external_store_id=data.external_store_id,
                order_date=data.order_date,
                created_at_external=data.created_at_external,
                updated_at_external=data.updated_at_external,
                imported_at=now,
                last_synced_at=now,
                status_raw=data.status_raw,
                status_normalized=data.status_normalized,
                buyer_name=data.buyer_name,
                buyer_email=data.buyer_email,
                buyer_phone=data.buyer_phone,
                currency_code=data.currency_code,
                items_subtotal_cents=data.items_subtotal_cents,
                shipping_cents=data.shipping_cents,
                tax_cents=data.tax_cents,
                discount_cents=data.discount_cents,
                fees_cents=data.fees_cents,
                refunded_cents=data.refunded_cents,
                order_total_cents=data.order_total_cents,
                fulfillment_channel=data.fulfillment_channel,
                shipping_service_level=data.shipping_service_level,
                ship_by_date=data.ship_by_date,
                deliver_by_date=data.deliver_by_date,
                notes=data.notes,
                import_error=data.import_error,
                raw_marketplace_data=data.raw_marketplace_data
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            
            print(f"[MARKETPLACE_ORDERS] action=CREATE marketplace={data.marketplace} external_order_id={data.external_order_id} order_id={order.id}")
            
            # Insert children for new order
            _insert_children(db, order, data)
            
            # Upsert customer and link to order (if marketplace order)
            if data.marketplace:
                # Extract source_customer_id from raw_marketplace_data if available
                source_customer_id = None
                if data.raw_marketplace_data:
                    source_customer_id = (
                        data.raw_marketplace_data.get('buyer_id') or
                        data.raw_marketplace_data.get('buyer', {}).get('id') or
                        data.raw_marketplace_data.get('BuyerInfo', {}).get('BuyerEmail')
                    )
                
                # Get addresses from data
                shipping_addr = extract_address_dict(
                    [a.model_dump() for a in data.addresses] if data.addresses else [], 
                    'shipping'
                )
                billing_addr = extract_address_dict(
                    [a.model_dump() for a in data.addresses] if data.addresses else [], 
                    'billing'
                )
                
                customer, _ = upsert_customer_from_marketplace_order(
                    db=db,
                    marketplace=data.marketplace.value if hasattr(data.marketplace, 'value') else str(data.marketplace),
                    source_customer_id=source_customer_id,
                    marketplace_buyer_email=data.buyer_email,
                    buyer_name=data.buyer_name,
                    buyer_phone=data.buyer_phone,
                    shipping_address=shipping_addr,
                    billing_address=billing_addr
                )
                if customer:
                    order.customer_id = customer.id
            
            db.commit()
            db.refresh(order)
            
            return order
    except Exception as e:
        print("[MARKETPLACE_ORDERS] Unhandled exception in upsert_marketplace_order:", repr(e))
        print(traceback.format_exc())
        raise


@router.post("/manual", response_model=MarketplaceOrderDetailResponse)
def create_manual_order(data: MarketplaceOrderCreate, db: Session = Depends(get_db)):
    """
    Create a manual order (not from marketplace import).
    
    - Forces source = MANUAL
    - Forces marketplace = None
    - Ignores any provided marketplace/external_order_id
    """
    try:
        now = datetime.utcnow()
        
        order = MarketplaceOrder(
            import_run_id=None,
            source=OrderSource.MANUAL,
            marketplace=None,
            external_order_id=None,
            external_order_number=None,
            external_store_id=None,
            order_date=data.order_date,
            created_at_external=None,
            updated_at_external=None,
            imported_at=now,
            last_synced_at=None,
            status_raw=None,
            status_normalized=data.status_normalized or NormalizedOrderStatus.PENDING,
            buyer_name=data.buyer_name,
            buyer_email=data.buyer_email,
            buyer_phone=data.buyer_phone,
            currency_code=data.currency_code,
            items_subtotal_cents=data.items_subtotal_cents,
            shipping_cents=data.shipping_cents,
            tax_cents=data.tax_cents,
            discount_cents=data.discount_cents,
            fees_cents=data.fees_cents,
            refunded_cents=data.refunded_cents,
            order_total_cents=data.order_total_cents,
            fulfillment_channel=data.fulfillment_channel,
            shipping_service_level=data.shipping_service_level,
            ship_by_date=data.ship_by_date,
            deliver_by_date=data.deliver_by_date,
            notes=data.notes,
            import_error=None,
            raw_marketplace_data=None
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        print(f"[MARKETPLACE_ORDERS] action=CREATE_MANUAL order_id={order.id}")
        
        # Insert children for new order
        _insert_children(db, order, data)
        db.commit()
        db.refresh(order)
        
        return order
    except Exception as e:
        print("[MARKETPLACE_ORDERS] Unhandled exception in create_manual_order:", repr(e))
        print(traceback.format_exc())
        raise


@router.get("", response_model=List[MarketplaceOrderResponse])
def list_marketplace_orders(
    marketplace: Optional[Marketplace] = None,
    status_normalized: Optional[NormalizedOrderStatus] = None,
    buyer_email: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db)
):
    """
    List marketplace orders with optional filters.
    
    Returns flat order list (no nested children).
    """
    try:
        query = db.query(MarketplaceOrder)
        
        if marketplace is not None:
            query = query.filter(MarketplaceOrder.marketplace == marketplace)
        
        if status_normalized is not None:
            query = query.filter(MarketplaceOrder.status_normalized == status_normalized)
        
        if buyer_email:
            query = query.filter(MarketplaceOrder.buyer_email.ilike(f"%{buyer_email}%"))
        
        if date_from:
            query = query.filter(MarketplaceOrder.order_date >= date_from)
        
        if date_to:
            query = query.filter(MarketplaceOrder.order_date <= date_to)
        
        if customer_id is not None:
            query = query.filter(MarketplaceOrder.customer_id == customer_id)
        
        query = query.order_by(MarketplaceOrder.order_date.desc())
        query = query.limit(limit)
        
        return query.all()
    except Exception as e:
        print("[MARKETPLACE_ORDERS] Unhandled exception in list_marketplace_orders:", repr(e))
        print(traceback.format_exc())
        raise


@router.get("/{id}", response_model=MarketplaceOrderDetailResponse)
def get_marketplace_order(id: int, db: Session = Depends(get_db)):
    """
    Get a single marketplace order by ID with nested children.
    Resolves line items to internal Models when possible.
    """
    try:
        order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Marketplace order not found")
        
        # Build response with resolved model information for each line
        # Convert order to dict for response construction
        order_data = {
            "id": order.id,
            "import_run_id": order.import_run_id,
            "source": order.source,
            "marketplace": order.marketplace,
            "external_order_id": order.external_order_id,
            "external_order_number": order.external_order_number,
            "external_store_id": order.external_store_id,
            "order_date": order.order_date,
            "created_at_external": order.created_at_external,
            "updated_at_external": order.updated_at_external,
            "status_raw": order.status_raw,
            "status_normalized": order.status_normalized,
            "buyer_name": order.buyer_name,
            "buyer_email": order.buyer_email,
            "buyer_phone": order.buyer_phone,
            "currency_code": order.currency_code,
            "items_subtotal_cents": order.items_subtotal_cents,
            "shipping_cents": order.shipping_cents,
            "tax_cents": order.tax_cents,
            "discount_cents": order.discount_cents,
            "fees_cents": order.fees_cents,
            "refunded_cents": order.refunded_cents,
            "order_total_cents": order.order_total_cents,
            "fulfillment_channel": order.fulfillment_channel,
            "shipping_service_level": order.shipping_service_level,
            "ship_by_date": order.ship_by_date,
            "deliver_by_date": order.deliver_by_date,
            "notes": order.notes,
            "import_error": order.import_error,
            "raw_marketplace_data": order.raw_marketplace_data,
            "last_synced_at": order.last_synced_at,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "addresses": order.addresses,
            "shipments": order.shipments,
            "lines": []
        }
        
        # Resolve each line item
        for line in order.lines:
            resolved_model = None
            resolved_model_id = None
            resolved_model_name = None
            resolved_manufacturer_name = None
            resolved_series_name = None
            
            # Resolution priority:
            # 1. If line.model_id is set, use that model
            # 2. Else if marketplace is "reverb" and line.product_id exists, 
            #    lookup via MarketplaceListing.external_id (auto-persist if unique match)
            
            auto_persisted = False
            
            if line.model_id:
                resolved_model = db.query(Model).filter(Model.id == line.model_id).first()
            elif order.marketplace == Marketplace.REVERB and line.product_id:
                # Use marketplace listings lookup (same as /api/models/marketplace-lookup)
                matches = lookup_models_by_marketplace_listing(
                    db, 
                    marketplace="reverb", 
                    identifier=str(line.product_id),
                    limit=5
                )
                
                if len(matches) == 1:
                    # Exactly one match - auto-persist model_id
                    matched_model_id = matches[0]["model_id"]
                    line.model_id = matched_model_id
                    resolved_model = db.query(Model).filter(Model.id == matched_model_id).first()
                    auto_persisted = True
                elif len(matches) > 1:
                    # Multiple matches - take first for display but don't persist
                    matched_model_id = matches[0]["model_id"]
                    resolved_model = db.query(Model).filter(Model.id == matched_model_id).first()
                # else: no matches, resolved_model stays None
            
            if resolved_model:
                resolved_model_id = resolved_model.id
                resolved_model_name = resolved_model.name
                if resolved_model.series:
                    resolved_series_name = resolved_model.series.name
                    if resolved_model.series.manufacturer:
                        resolved_manufacturer_name = resolved_model.series.manufacturer.name
            
            # Build line response with resolved fields
            line_data = {
                "id": line.id,
                "order_id": line.order_id,
                "external_line_item_id": line.external_line_item_id,
                "marketplace_item_id": line.marketplace_item_id,
                "sku": line.sku,
                "asin": line.asin,
                "listing_id": line.listing_id,
                "product_id": line.product_id,
                "title": line.title,
                "variant": line.variant,
                "quantity": line.quantity,
                "currency_code": line.currency_code,
                "unit_price_cents": line.unit_price_cents,
                "line_subtotal_cents": line.line_subtotal_cents,
                "tax_cents": line.tax_cents,
                "discount_cents": line.discount_cents,
                "line_total_cents": line.line_total_cents,
                "fulfillment_status_raw": line.fulfillment_status_raw,
                "fulfillment_status_normalized": line.fulfillment_status_normalized,
                "model_id": line.model_id,
                "customization_data": line.customization_data,
                "raw_marketplace_data": line.raw_marketplace_data,
                "resolved_model_id": resolved_model_id,
                "resolved_model_name": resolved_model_name,
                "resolved_manufacturer_name": resolved_manufacturer_name,
                "resolved_series_name": resolved_series_name,
            }
            order_data["lines"].append(line_data)
        
        # Commit any auto-persisted model_id changes
        try:
            db.commit()
        except Exception as commit_err:
            print(f"[MARKETPLACE_ORDERS_DETAIL] Warning: Failed to commit auto-resolved model_ids: {commit_err}")
            db.rollback()
        
        return order_data
    except Exception as e:
        print(f"[MARKETPLACE_ORDERS_DETAIL] id={id} ERROR: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise


@router.delete("/{id}")
def delete_marketplace_order(id: int, db: Session = Depends(get_db)):
    """
    Delete a marketplace order and all its children.
    """
    try:
        order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Marketplace order not found")
        
        db.delete(order)
        db.commit()
        return {"message": "Marketplace order deleted"}
    except Exception as e:
        print("[MARKETPLACE_ORDERS] Unhandled exception in delete_marketplace_order:", repr(e))
        print(traceback.format_exc())
        raise


# ============================================================
# Line Item Update Request/Response Models
# ============================================================

class UpdateLineRequest(BaseModel):
    product_id: Optional[str] = None
    model_id: Optional[int] = None


class UpdateLineResponse(BaseModel):
    id: int
    order_id: int
    product_id: Optional[str] = None
    model_id: Optional[int] = None
    message: str


@router.put("/lines/{line_id}", response_model=UpdateLineResponse)
def update_order_line(
    line_id: int,
    request: UpdateLineRequest,
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """
    Admin-protected endpoint to update a single marketplace order line.
    Allows setting product_id and/or model_id for manual resolution.
    """
    try:
        line = db.query(MarketplaceOrderLine).filter(MarketplaceOrderLine.id == line_id).first()
        if not line:
            raise HTTPException(status_code=404, detail="Order line not found")
        
        updated_fields = []
        
        # Update product_id if provided
        if request.product_id is not None:
            line.product_id = request.product_id if request.product_id else None
            updated_fields.append("product_id")
        
        # Update model_id if provided
        if request.model_id is not None:
            # Validate model exists if non-zero
            if request.model_id > 0:
                model = db.query(Model).filter(Model.id == request.model_id).first()
                if not model:
                    raise HTTPException(status_code=400, detail=f"Model with id {request.model_id} not found")
                line.model_id = request.model_id
            else:
                # Allow clearing by setting to 0 or None
                line.model_id = None
            updated_fields.append("model_id")
        
        db.commit()
        db.refresh(line)
        
        print(f"[MARKETPLACE_ORDER_LINE_UPDATE] line_id={line_id} updated_fields={updated_fields}")
        
        return UpdateLineResponse(
            id=line.id,
            order_id=line.order_id,
            product_id=line.product_id,
            model_id=line.model_id,
            message=f"Updated fields: {', '.join(updated_fields) if updated_fields else 'none'}"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MARKETPLACE_ORDER_LINE_UPDATE] line_id={line_id} ERROR: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update line: {str(e)}")


# ============================================================
# Admin-Only Maintenance Endpoints
# ============================================================

@router.post("/cleanup-shipments", response_model=CleanupShipmentsResponse)
def cleanup_duplicate_shipments(
    request: CleanupShipmentsRequest,
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """
    Admin-only endpoint to deduplicate shipment rows in marketplace_order_shipments.
    
    Modes:
    - "strict" (default): Dedupe on full key (order_id, carrier, tracking_number, shipped_at)
      Keep row with smallest id in each group.
    - "prefer_tracked": Remove empty-tracking rows when a tracked row exists for same (order_id, carrier)
      Keeps all tracked rows, removes only untracked ones.
    
    Default: dry_run=true (no deletes)
    """
    try:
        # Build query for shipments
        query = db.query(MarketplaceOrderShipment).join(
            MarketplaceOrder,
            MarketplaceOrderShipment.order_id == MarketplaceOrder.id
        )
        
        # Filter by marketplace if provided
        if request.marketplace:
            # Convert string to enum for comparison
            try:
                marketplace_enum = Marketplace(request.marketplace.lower())
                query = query.filter(MarketplaceOrder.marketplace == marketplace_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid marketplace: {request.marketplace}"
                )
        
        # Filter by order_id if provided
        if request.order_id is not None:
            query = query.filter(MarketplaceOrderShipment.order_id == request.order_id)
        
        # Fetch all matching shipments
        shipments = query.all()
        rows_scanned = len(shipments)
        
        ids_to_delete: List[int] = []
        affected_order_ids: set[int] = set()
        duplicate_groups_found = 0
        
        if request.mode == "prefer_tracked":
            # ============================================================
            # prefer_tracked mode: Remove untracked rows when tracked exists
            # ============================================================
            # Group by (order_id, carrier)
            groups: dict[tuple, list[MarketplaceOrderShipment]] = {}
            
            for ship in shipments:
                carrier_key = (ship.carrier or "").strip().lower()
                key = (ship.order_id, carrier_key)
                
                if key not in groups:
                    groups[key] = []
                groups[key].append(ship)
            
            # For each group, check if tracked row exists and mark untracked for deletion
            for key, group in groups.items():
                # Separate tracked vs untracked
                tracked = [s for s in group if s.tracking_number and s.tracking_number.strip()]
                untracked = [s for s in group if not s.tracking_number or not s.tracking_number.strip()]
                
                # Only delete untracked if at least one tracked exists
                if tracked and untracked:
                    duplicate_groups_found += 1
                    for ship in untracked:
                        ids_to_delete.append(ship.id)
                        affected_order_ids.add(ship.order_id)
        
        else:
            # ============================================================
            # strict mode (default): Dedupe on full 4-tuple key
            # ============================================================
            # Group shipments by dedupe key: (order_id, carrier, tracking_number, shipped_at)
            groups: dict[tuple, list[MarketplaceOrderShipment]] = {}
            
            for ship in shipments:
                # Build key with NULL handling
                carrier_key = (ship.carrier or "").strip().lower()
                tracking_key = (ship.tracking_number or "").strip()
                shipped_at_key = ship.shipped_at.isoformat() if ship.shipped_at else ""
                
                key = (ship.order_id, carrier_key, tracking_key, shipped_at_key)
                
                if key not in groups:
                    groups[key] = []
                groups[key].append(ship)
            
            # Find groups with duplicates (len > 1)
            duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
            duplicate_groups_found = len(duplicate_groups)
            
            # Determine rows to delete (all except the one with smallest id)
            for key, group in duplicate_groups.items():
                # Sort by id ascending
                sorted_group = sorted(group, key=lambda s: s.id)
                # Keep first (smallest id), mark rest for deletion
                for ship in sorted_group[1:]:
                    ids_to_delete.append(ship.id)
                    affected_order_ids.add(ship.order_id)
        
        rows_to_delete = len(ids_to_delete)
        rows_deleted = 0
        
        # Perform delete if not dry_run
        if not request.dry_run and ids_to_delete:
            rows_deleted = db.query(MarketplaceOrderShipment).filter(
                MarketplaceOrderShipment.id.in_(ids_to_delete)
            ).delete(synchronize_session=False)
            db.commit()
        
        # Build sample of affected order IDs (max 20)
        affected_order_ids_sample = sorted(list(affected_order_ids))[:20]
        
        # Log summary
        print(f"[SHIPMENT_DEDUPE] mode={request.mode} marketplace={request.marketplace} order_id={request.order_id} dry_run={request.dry_run} scanned={rows_scanned} groups={duplicate_groups_found} to_delete={rows_to_delete} deleted={rows_deleted}")
        
        return CleanupShipmentsResponse(
            dry_run=request.dry_run,
            marketplace=request.marketplace,
            order_id=request.order_id,
            mode=request.mode,
            rows_scanned=rows_scanned,
            duplicate_groups_found=duplicate_groups_found,
            rows_to_delete=rows_to_delete,
            rows_deleted=rows_deleted,
            affected_order_ids_sample=affected_order_ids_sample
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SHIPMENT_DEDUPE] ERROR: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Shipment cleanup failed: {str(e)}"
        )


# ============================================================
# Invoice Generation Endpoints
# ============================================================

class InvoiceRequest(BaseModel):
    order_ids: List[int]
    mode: Literal["html"] = "html"  # Only HTML for now; PDF in future chunks


class InvoiceResponse(BaseModel):
    html: str
    order_count: int


@router.post("/invoice", response_model=InvoiceResponse)
def generate_invoice(
    request: InvoiceRequest,
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """
    Admin-protected endpoint to generate an invoice for selected marketplace orders.
    
    Returns HTML content that can be displayed in a new tab or printed.
    Uses resolved model identity for line items with safe fallbacks.
    """
    from app.services.invoice_generator import generate_invoice_html
    
    try:
        if not request.order_ids:
            raise HTTPException(status_code=400, detail="No order IDs provided")
        
        # Fetch all requested orders
        orders = db.query(MarketplaceOrder).filter(
            MarketplaceOrder.id.in_(request.order_ids)
        ).all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="No orders found with provided IDs")
        
        # Generate HTML invoice
        html = generate_invoice_html(orders, db)
        
        print(f"[INVOICE] Generated invoice for {len(orders)} orders: {request.order_ids}")
        
        return InvoiceResponse(
            html=html,
            order_count=len(orders)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[INVOICE] ERROR: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Invoice generation failed: {str(e)}"
        )
