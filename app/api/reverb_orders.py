"""
Reverb Orders API - Import orders from Reverb marketplace.

Provides endpoints for:
- POST /api/reverb/orders/import - Import orders from Reverb into normalized tables
- GET /api/reverb/orders/sample - Fetch a sample order for debugging/validation
"""
import traceback
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import (
    MarketplaceImportRun, MarketplaceOrder, MarketplaceOrderAddress,
    MarketplaceOrderLine, MarketplaceOrderShipment, MarketplaceConversation, MarketplaceMessage
)
from app.models.enums import Marketplace, OrderSource, NormalizedOrderStatus
from app.services.reverb_service import (
    get_reverb_credentials, fetch_reverb_orders, fetch_single_reverb_order,
    map_reverb_order_to_schema, FetchResult, get_order_detail, parse_order_detail_for_enrichment,
    CredentialsNotConfiguredError, CredentialsDisabledError, ReverbAPIError,
    fetch_reverb_conversations, fetch_reverb_conversation_detail
)
from app.services.customer_service import upsert_customer_from_marketplace_order, extract_address_dict


router = APIRouter(prefix="/reverb/orders", tags=["reverb-orders"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ImportOrdersRequest(BaseModel):
    """Request body for order import."""
    days_back: int = 30
    since_iso: Optional[str] = None  # ISO datetime string, overrides days_back if provided
    date_to: Optional[datetime] = None
    limit: int = 50
    dry_run: bool = False  # If true, fetch and map but do not write to DB
    debug: bool = False  # If true, include debug diagnostics in response


class ImportOrdersResponse(BaseModel):
    """Response for order import operation."""
    import_run_id: Optional[int] = None  # None for dry_run
    dry_run: bool = False
    total_fetched: int
    total_created: int
    total_updated: int
    total_failed: int
    failed_order_ids: List[str]
    preview_orders: Optional[List[dict]] = None  # For dry_run mode
    # Debug fields (only populated when debug=true)
    filter_since_utc: Optional[str] = None
    filter_mode: Optional[str] = None  # "days_back" or "since_iso"
    timestamp_field_used: Optional[str] = None
    raw_fetched: Optional[int] = None
    filtered: Optional[int] = None
    pages_fetched: Optional[int] = None
    early_stop: Optional[bool] = None
    undated_count: Optional[int] = None
    customers_matched: Optional[int] = 0
    customers_created: Optional[int] = 0
    orders_linked_to_customers: Optional[int] = 0
    orders_missing_buyer_identity: Optional[int] = 0
    orders_enriched_for_shipping: Optional[int] = 0
    debug_samples: Optional[List[dict]] = None
    customer_debug: Optional[dict] = None


class ImportMessagesResponse(BaseModel):
    """Response for message import operation."""
    import_run_id: Optional[int] = None
    dry_run: bool = False
    conversations_fetched: int
    conversations_created: int
    conversations_updated: int
    messages_fetched: int
    messages_created: int
    customers_linked: int
    debug_samples: Optional[List[dict]] = None


class SampleOrderResponse(BaseModel):
    """Response for sample order endpoint."""
    order: Optional[dict] = None
    mapped: Optional[dict] = None
    message: str


class NormalizeOrdersRequest(BaseModel):
    """Request body for normalize orders endpoint."""
    days_back: int = 30
    limit: int = 200
    dry_run: bool = True
    debug: bool = False
    force_rebuild_lines: bool = False  # If true, rebuild lines even if they exist


class NormalizeOrdersResponse(BaseModel):
    """Response for normalize orders endpoint."""
    dry_run: bool
    orders_scanned: int
    orders_updated: int
    addresses_upserted: int
    lines_upserted: int
    orders_skipped: int
    preview: Optional[List[dict]] = None
    debug: Optional[dict] = None


class EnrichOrdersRequest(BaseModel):
    """Request body for enrich orders endpoint."""
    days_back: int = 30
    since_iso: Optional[str] = None
    limit: int = 50
    dry_run: bool = True
    debug: bool = False
    force: bool = False  # If true, overwrite existing non-null fields


class EnrichOrdersResponse(BaseModel):
    """Response for enrich orders endpoint."""
    dry_run: bool
    orders_scanned: int
    orders_enriched: int
    orders_skipped: int
    lines_upserted: int
    addresses_upserted: int
    shipments_upserted: int
    failed_order_ids: Optional[dict] = None
    preview_orders: Optional[List[dict]] = None
    debug: Optional[dict] = None


# =============================================================================
# Helper Functions
# =============================================================================

def _sanitize_order_for_preview(mapped_order: dict) -> dict:
    """
    Sanitize a mapped order for dry_run preview.
    Removes raw_marketplace_data to reduce size and removes any sensitive info.
    """
    preview = {
        "external_order_id": mapped_order.get("external_order_id"),
        "external_order_number": mapped_order.get("external_order_number"),
        "order_date": mapped_order.get("order_date"),
        "status_raw": mapped_order.get("status_raw"),
        "status_normalized": mapped_order.get("status_normalized"),
        "buyer_name": mapped_order.get("buyer_name"),
        "currency_code": mapped_order.get("currency_code"),
        "order_total_cents": mapped_order.get("order_total_cents"),
        "line_count": len(mapped_order.get("lines", [])),
        "address_count": len(mapped_order.get("addresses", [])),
    }
    return preview


def _parse_since_iso(since_iso: str) -> datetime:
    """
    Parse since_iso string to datetime.
    Raises ValueError if invalid.
    """
    # Try common ISO formats
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(since_iso, fmt)
        except ValueError:
            continue

    # Try fromisoformat as fallback
    try:
        return datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass

    raise ValueError(f"Invalid ISO datetime format: {since_iso}")


def _upsert_order(db: Session, order_data: dict, import_run_id: int) -> tuple:
    """
    Upsert a single order into the database.

    Uses (marketplace, external_order_id) as unique identity.

    Returns:
        Tuple of (success: bool, is_new: bool, error_message: str or None, order_obj: MarketplaceOrder or None)
    """
    try:
        external_order_id = order_data.get("external_order_id")
        if not external_order_id:
            return False, False, "Missing external_order_id", None

        # Check for existing order using unique identity (marketplace, external_order_id)
        existing = db.query(MarketplaceOrder).filter(
            MarketplaceOrder.marketplace == Marketplace.REVERB,
            MarketplaceOrder.external_order_id == external_order_id
        ).first()

        is_new = existing is None

        if existing:
            order = existing
            # Update existing order fields
            order.import_run_id = import_run_id
            order.external_order_number = order_data.get("external_order_number")
            order.status_raw = order_data.get("status_raw")
            status_str = order_data.get("status_normalized", "unknown")
            order.status_normalized = NormalizedOrderStatus(status_str) if status_str in [e.value for e in NormalizedOrderStatus] else NormalizedOrderStatus.UNKNOWN
            order.buyer_name = order_data.get("buyer_name")
            order.buyer_email = order_data.get("buyer_email")
            order.currency_code = order_data.get("currency_code", "USD")
            order.items_subtotal_cents = order_data.get("items_subtotal_cents")
            order.shipping_cents = order_data.get("shipping_cents")
            order.tax_cents = order_data.get("tax_cents")
            order.order_total_cents = order_data.get("order_total_cents")
            order.raw_marketplace_data = order_data.get("raw_marketplace_data")
            order.last_synced_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
            
            # Expanded fields updates
            if order_data.get("raw_marketplace_detail_data"):
                order.raw_marketplace_detail_data = order_data.get("raw_marketplace_detail_data")
            if order_data.get("payment_method"):
                order.payment_method = order_data.get("payment_method")
            if order_data.get("shipping_provider"):
                order.shipping_provider = order_data.get("shipping_provider")
            if order_data.get("shipping_code"):
                order.shipping_code = order_data.get("shipping_code")
            if order_data.get("reverb_buyer_id"):
                order.reverb_buyer_id = order_data.get("reverb_buyer_id")
            if order_data.get("reverb_order_status"):
                 order.reverb_order_status = order_data.get("reverb_order_status")
        else:
            status_str = order_data.get("status_normalized", "unknown")
            status_normalized = NormalizedOrderStatus(status_str) if status_str in [e.value for e in NormalizedOrderStatus] else NormalizedOrderStatus.UNKNOWN

            order = MarketplaceOrder(
                import_run_id=import_run_id,
                source=OrderSource.API_IMPORT,
                marketplace=Marketplace.REVERB,
                external_order_id=external_order_id,
                external_order_number=order_data.get("external_order_number"),
                order_date=datetime.fromisoformat(order_data["order_date"]) if order_data.get("order_date") else datetime.utcnow(),
                imported_at=datetime.utcnow(),
                status_raw=order_data.get("status_raw"),
                status_normalized=status_normalized,
                buyer_name=order_data.get("buyer_name"),
                buyer_email=order_data.get("buyer_email"),
                currency_code=order_data.get("currency_code", "USD"),
                items_subtotal_cents=order_data.get("items_subtotal_cents"),
                shipping_cents=order_data.get("shipping_cents"),
                tax_cents=order_data.get("tax_cents"),
                order_total_cents=order_data.get("order_total_cents"),
                raw_marketplace_data=order_data.get("raw_marketplace_data"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Expanded fields
            order.raw_marketplace_detail_data = order_data.get("raw_marketplace_detail_data")
            order.payment_method = order_data.get("payment_method")
            order.payment_status = order_data.get("payment_status")
            order.shipping_provider = order_data.get("shipping_provider")
            order.shipping_code = order_data.get("shipping_code")
            order.shipping_method = order_data.get("shipping_method")
            order.reverb_buyer_id = order_data.get("reverb_buyer_id")
            if order_data.get("reverb_order_status"):
                 order.reverb_order_status = order_data.get("reverb_order_status")
            
            db.add(order)

        db.flush()  # Get order ID

        # Handle addresses - delete existing and insert new
        addresses = order_data.get("addresses", [])
        if addresses:
            db.query(MarketplaceOrderAddress).filter(
                MarketplaceOrderAddress.order_id == order.id
            ).delete(synchronize_session=False)

            for addr_data in addresses:
                addr = MarketplaceOrderAddress(
                    order_id=order.id,
                    address_type=addr_data.get("address_type", "shipping"),
                    name=addr_data.get("name"),
                    phone=addr_data.get("phone"),
                    company=addr_data.get("company"),
                    line1=addr_data.get("line1"),
                    line2=addr_data.get("line2"),
                    city=addr_data.get("city"),
                    state_or_region=addr_data.get("state_or_region"),
                    postal_code=addr_data.get("postal_code"),
                    country_code=addr_data.get("country_code"),
                    raw_payload=addr_data.get("raw_payload")
                )
                db.add(addr)

        # Handle lines - delete existing and insert new
        lines = order_data.get("lines", [])
        if lines:
            db.query(MarketplaceOrderLine).filter(
                MarketplaceOrderLine.order_id == order.id
            ).delete(synchronize_session=False)

            for line_data in lines:
                line = MarketplaceOrderLine(
                    order_id=order.id,
                    external_line_item_id=line_data.get("external_line_item_id"),
                    sku=line_data.get("sku"),
                    title=line_data.get("title"),
                    quantity=line_data.get("quantity", 1),
                    unit_price_cents=line_data.get("unit_price_cents"),
                    line_total_cents=line_data.get("line_total_cents"),
                    customization_data=line_data.get("customization_data"),
                    raw_marketplace_data=line_data.get("raw_marketplace_data")
                )
                db.add(line)

        return True, is_new, None, order

    except Exception as e:
        return False, False, str(e), None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/import", response_model=ImportOrdersResponse)
def import_reverb_orders(
    request: ImportOrdersRequest,
    db: Session = Depends(get_db)
):
    """
    Import orders from Reverb into the normalized marketplace orders tables.

    - Creates a MarketplaceImportRun record (unless dry_run=true)
    - Fetches orders from Reverb API
    - Maps and upserts each order
    - Returns import summary

    Parameters:
    - days_back: Number of days back to fetch (default 30)
    - since_iso: ISO datetime string, overrides days_back if provided
    - limit: Maximum orders to fetch (default 50)
    - dry_run: If true, fetch and map but do not write to DB
    - debug: If true, include debug diagnostics in response
    """
    try:
        # Determine filter mode and parse since_iso if provided
        date_from = None
        filter_mode = "days_back"
        since_str = "N/A"

        if request.since_iso:
            try:
                date_from = _parse_since_iso(request.since_iso)
                filter_mode = "since_iso"
                since_str = request.since_iso
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        elif request.days_back:
            date_from = datetime.now(timezone.utc) - timedelta(days=request.days_back)
            filter_mode = "days_back"
            since_str = f"{request.days_back} days back"

        # Log start (no secrets)
        print(f"[REVERB_IMPORT] action=START days_back={request.days_back} since={since_str} limit={request.limit} dry_run={request.dry_run} debug={request.debug}")

        # Get credentials
        try:
            credentials = get_reverb_credentials(db)
        except CredentialsNotConfiguredError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except CredentialsDisabledError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Create import run record (only if not dry_run)
        import_run = None
        import_run_id = None
        if not request.dry_run:
            import_run = MarketplaceImportRun(
                marketplace=Marketplace.REVERB,
                started_at=datetime.utcnow(),
                status="running",
                orders_fetched=0,
                orders_upserted=0,
                errors_count=0
            )
            db.add(import_run)
            db.flush()
            import_run_id = import_run.id

        # Fetch orders from Reverb (returns FetchResult with metadata)
        try:
            fetch_result: FetchResult = fetch_reverb_orders(
                credentials,
                date_from=date_from,
                date_to=request.date_to,
                days_back=None,  # Already handled via date_from
                limit=request.limit
            )
        except ReverbAPIError as e:
            if import_run:
                import_run.status = "failed"
                import_run.finished_at = datetime.utcnow()
                import_run.error_summary = {"error": str(e)}  # Safe, no tokens
                db.commit()
            # Return 502 for upstream API errors
            raise HTTPException(status_code=502, detail=f"Reverb API error: {str(e)}")

        raw_orders = fetch_result.orders

        # Handle no orders case
        if len(raw_orders) == 0:
            if import_run:
                import_run.orders_fetched = 0
                import_run.orders_upserted = 0
                import_run.errors_count = 0
                import_run.status = "success"
                import_run.finished_at = datetime.utcnow()
                db.commit()

            print(f"[REVERB_IMPORT] fetched=0 created=0 updated=0 failed=0 import_run_id={import_run_id}")

            response = ImportOrdersResponse(
                import_run_id=import_run_id,
                dry_run=request.dry_run,
                total_fetched=0,
                total_created=0,
                total_updated=0,
                total_failed=0,
                failed_order_ids=[],
                preview_orders=[] if request.dry_run else None
            )

            # Add debug fields if requested
            if request.debug:
                response.filter_since_utc = fetch_result.filter_since_utc
                response.filter_mode = filter_mode
                response.timestamp_field_used = fetch_result.timestamp_field_used
                response.raw_fetched = fetch_result.raw_fetched
                response.filtered = fetch_result.filtered
                response.pages_fetched = fetch_result.pages_fetched
                response.early_stop = fetch_result.early_stop
                response.undated_count = fetch_result.undated_count

            return response

        if import_run:
            import_run.orders_fetched = len(raw_orders)

        # Process each order
        created_count = 0
        updated_count = 0
        failed_count = 0
        failed_ids = []
        preview_orders = []

        # Diagnostics
        customers_matched_count = 0
        customers_created_count = 0
        orders_linked_count = 0
        orders_missing_identity_count = 0
        orders_enriched_for_shipping_count = 0
        orders_detail_fetched_count = 0
        
        # New counters
        customers_updated_shipping_name_count = 0
        customers_updated_address1_count = 0
        customers_updated_phone_count = 0
        
        debug_customer_attempted = 0
        debug_customer_returned = 0
        debug_customer_none = 0
        debug_samples = []

        for raw_order in raw_orders:
            order_id = str(raw_order.get("order_number") or raw_order.get("id", "unknown"))

            try:
                mapped_order = map_reverb_order_to_schema(raw_order)
                external_order_id = mapped_order.get("external_order_id")

                # Check for missing shipping details and enrich if needed
                shipping_addr_check = extract_address_dict(mapped_order.get("addresses", []), "shipping")
                has_shipping_name = bool(shipping_addr_check and shipping_addr_check.get("name"))
                has_shipping_line1 = bool(shipping_addr_check and shipping_addr_check.get("line1"))
                has_shipping_phone = bool(shipping_addr_check and shipping_addr_check.get("phone"))
                has_shipping_postal = bool(shipping_addr_check and shipping_addr_check.get("postal_code"))
                
                used_detail_fetch = False
                
                # Fetch logic: If missing ANY key valid field, try to get better data
                # But ensure we don't spam if we know it's not likely to be there
                if not (has_shipping_name and has_shipping_line1 and has_shipping_phone and has_shipping_postal):
                    try:
                         # Small delay to respect rate limits
                         time.sleep(0.15)
                         detail = get_order_detail(credentials, external_order_id)
                         
                         if not detail.get("error"):
                             orders_detail_fetched_count += 1
                             enrichment = parse_order_detail_for_enrichment(detail, external_order_id)
                             enriched_addr = enrichment.get("shipping_address")
                             
                             if enriched_addr:
                                 # Reverb detail often has "display_location" if address is sparse
                                 # We want to use it ONLY if it provides better structured data (lines, etc)
                                 # If detail payload ONLY has display_location (and no street_address), parse_order_detail usually returns partial dict
                                 
                                 used_detail_fetch = True
                                 # Get or create shipping dict in mapped_order
                                 addresses = mapped_order.setdefault("addresses", [])
                                 target_addr = next((a for a in addresses if a.get("address_type") == "shipping"), None)
                                 
                                 if not target_addr:
                                     target_addr = {"address_type": "shipping"}
                                     addresses.append(target_addr)
                                 
                                 # Fill blanks
                                 for k, v in enriched_addr.items():
                                     if v and not target_addr.get(k):
                                         target_addr[k] = v
                                         
                                 # Re-evaluate flags for debug
                                 has_shipping_name = bool(target_addr.get("name"))
                                 has_shipping_line1 = bool(target_addr.get("line1"))
                                 has_shipping_phone = bool(target_addr.get("phone"))
                                 
                                 has_shipping_phone = bool(target_addr.get("phone"))
                                 
                                 orders_enriched_for_shipping_count += 1
                             
                             # Store FULL detail payload for "Store Everything" requirement
                             mapped_order["raw_marketplace_detail_data"] = detail
                             
                             # Enrich mapped_order with extended fields from detail if present
                             extended = enrichment.get("extended_fields", {})
                             for k, v in extended.items():
                                 if v and not mapped_order.get(k):
                                     mapped_order[k] = v
                                     
                             # Also update buyer ID if found in enrichment
                             if enrichment.get("buyer", {}).get("reverb_buyer_id") and not mapped_order.get("reverb_buyer_id"):
                                 mapped_order["reverb_buyer_id"] = enrichment.get("buyer", {}).get("reverb_buyer_id")

                    except Exception as enrich_err:
                        print(f"[REVERB_IMPORT] enrichment_warning order={external_order_id} error={enrich_err}")

                # Dry run: just collect preview, don't write
                if request.dry_run:
                    if len(preview_orders) < 3:  # Cap preview at 3 orders
                        preview_orders.append(_sanitize_order_for_preview(mapped_order))

                    # Simulate what would happen
                    existing = db.query(MarketplaceOrder).filter(
                        MarketplaceOrder.marketplace == Marketplace.REVERB,
                        MarketplaceOrder.external_order_id == mapped_order.get("external_order_id")
                    ).first()

                    if existing:
                        updated_count += 1
                    else:
                        created_count += 1
                    continue

                # Real run: upsert to DB
                success, is_new, error, order = _upsert_order(db, mapped_order, import_run_id)

                if success:
                    if is_new:
                        created_count += 1
                    else:
                        updated_count += 1

                    # ---------------------------------------------------------
                    # Customer Upsert Linkage
                    # ---------------------------------------------------------
                    if order:
                        try:
                            # 1. Extract source identity
                            # Prefer reliable reverb_buyer_id if mapped, else valid email
                            source_customer_id = mapped_order.get("reverb_buyer_id")
        
                            # 2. Extract addresses if available
                            # Use mapped_order data to ensure we have the latest payload without needing DB refresh
                            shipping_addr = extract_address_dict(mapped_order.get("addresses", []), "shipping")
                            billing_addr = extract_address_dict(mapped_order.get("addresses", []), "billing")

                            buyer_phone = shipping_addr.get("phone") if shipping_addr else None

                            # 3. Call Service
                            debug_customer_attempted += 1
                            # UNPACK TUPLE NOW
                            customer, cust_stats = upsert_customer_from_marketplace_order(
                                db=db,
                                marketplace=Marketplace.REVERB.value,
                                source_customer_id=source_customer_id,
                                marketplace_buyer_email=order.buyer_email,
                                buyer_name=order.buyer_name,
                                buyer_phone=buyer_phone,
                                shipping_address=shipping_addr,
                                billing_address=billing_addr
                            )

                            match_type = "none"

                            # Ensure customer has ID (if newly created)
                            if customer and customer.id is None:
                                db.flush()

                            if customer:
                                debug_customer_returned += 1

                                # Perform Linkage
                                if order.customer_id != customer.id:
                                    order.customer_id = customer.id
                                    db.add(order)

                                orders_linked_count += 1

                                # Update counters from stats
                                if cust_stats.get("created"):
                                    customers_created_count += 1
                                    match_type = "created"
                                else:
                                    customers_matched_count += 1
                                    match_type = "matched"
                                
                                if cust_stats.get("updated_shipping_name"): customers_updated_shipping_name_count += 1
                                if cust_stats.get("updated_address1"): customers_updated_address1_count += 1
                                if cust_stats.get("updated_phone"): customers_updated_phone_count += 1
                                    
                            else:
                                debug_customer_none += 1

                                # Only count as "missing identity" if BOTH are missing
                                if not source_customer_id and not (order.buyer_email and str(order.buyer_email).strip()):
                                    orders_missing_identity_count += 1

                            # Debug Sampling
                            if request.debug and len(debug_samples) < 10:
                                debug_samples.append({
                                    "external_order_id": order.external_order_id,
                                    "order_row_id": order.id,
                                    "buyer_email_from_payload": order.buyer_email,
                                    "source_customer_id_from_payload": source_customer_id,
                                    "customer_id_linked": customer.id if customer else None,
                                    "match_strategy": match_type,
                                    "notes": "Missing buyer identity" if (not customer and not source_customer_id and not (order.buyer_email and str(order.buyer_email).strip())) else ("Linked" if customer else "No customer returned"),
                                    "shipping_has_name": has_shipping_name,
                                    "shipping_has_line1": has_shipping_line1,
                                    "shipping_has_phone": has_shipping_phone,
                                    "used_detail_fetch": used_detail_fetch,
                                    "cust_updated_phone": cust_stats.get("updated_phone", False) if customer else False
                                })

                        except Exception as cust_err:
                            print(f"[REVERB_IMPORT] customer_link_error order_id={order.id} err={cust_err}")
                            if request.debug and len(debug_samples) < 10:
                                debug_samples.append({
                                    "external_order_id": order.external_order_id,
                                    "error": str(cust_err),
                                    "notes": "Exception during link"
                                })

                else:
                    failed_count += 1
                    if len(failed_ids) < 20:  # Cap failed IDs list
                        failed_ids.append(order_id)
                    print(f"[REVERB_IMPORT] upsert_failed order_id={order_id} error={error}")

            except Exception as e:
                failed_count += 1
                if len(failed_ids) < 20:
                    failed_ids.append(order_id)
                print(f"[REVERB_IMPORT] mapping_error order_id={order_id} error={repr(e)}")

        # Update import run (only if not dry_run)
        if import_run:
            import_run.orders_upserted = created_count + updated_count
            import_run.errors_count = failed_count
            import_run.status = "success" if failed_count == 0 else ("partial" if created_count + updated_count > 0 else "failed")
            import_run.finished_at = datetime.utcnow()

            if failed_ids:
                import_run.error_summary = {"failed_order_ids": failed_ids}

            db.commit()

        # Log completion (no secrets)
        print(f"[REVERB_IMPORT] fetched={len(raw_orders)} created={created_count} updated={updated_count} failed={failed_count} linked={orders_linked_count} import_run_id={import_run_id} dry_run={request.dry_run}")

        response = ImportOrdersResponse(
            import_run_id=import_run_id,
            dry_run=request.dry_run,
            total_fetched=len(raw_orders),
            total_created=created_count,
            total_updated=updated_count,
            total_failed=failed_count,
            failed_order_ids=failed_ids,
            preview_orders=preview_orders if request.dry_run else None
        )

        # Add debug fields if requested
        if request.debug:
            response.filter_since_utc = fetch_result.filter_since_utc
            response.filter_mode = filter_mode
            response.timestamp_field_used = fetch_result.timestamp_field_used
            response.raw_fetched = fetch_result.raw_fetched
            response.filtered = fetch_result.filtered
            response.pages_fetched = fetch_result.pages_fetched
            response.early_stop = fetch_result.early_stop
            response.undated_count = fetch_result.undated_count
            # Extended debug
            response.customers_matched = customers_matched_count
            response.customers_created = customers_created_count
            response.orders_linked_to_customers = orders_linked_count
            response.orders_missing_buyer_identity = orders_missing_identity_count
            response.orders_enriched_for_shipping = orders_enriched_for_shipping_count
            response.debug_samples = debug_samples
            response.customer_debug = {
                "attempted": debug_customer_attempted,
                "returned": debug_customer_returned,
                "none": debug_customer_none,
                "enrichment_fetches": orders_detail_fetched_count
            }
            
            # Using dict insertion for fields not in schema for quick debug if Pydantic allows, else might be skipped
            # To be safer we could add them to schema in next chunk or just stick to allowed fields
            # The user asked for "debug counters" but didn't explicitly demand Schema changes, 
            # so I'll put them in a loose dict or reuse the debug_dict pattern if available
            response.customer_debug.update({
                "updated_shipping_name": customers_updated_shipping_name_count,
                "updated_address1": customers_updated_address1_count,
                "updated_phone": customers_updated_phone_count
            })

        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[REVERB_IMPORT] unhandled_exception error={repr(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sample", response_model=SampleOrderResponse)
def get_sample_reverb_order(
    db: Session = Depends(get_db)
):
    """
    Fetch a single sample order from Reverb for mapping validation.

    Returns raw order JSON and mapped version for admin debugging.
    """
    try:
        # Get credentials
        try:
            credentials = get_reverb_credentials(db)
        except CredentialsNotConfiguredError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except CredentialsDisabledError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Fetch single order
        try:
            raw_order = fetch_single_reverb_order(credentials)
        except ReverbAPIError as e:
            raise HTTPException(status_code=502, detail=f"Reverb API error: {str(e)}")

        if not raw_order:
            return SampleOrderResponse(
                order=None,
                mapped=None,
                message="No orders found in Reverb account"
            )

        # Map the order
        mapped = map_reverb_order_to_schema(raw_order)

        return SampleOrderResponse(
            order=raw_order,
            mapped=mapped,
            message="Sample order retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[REVERB_IMPORT] sample_error error={repr(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/messages/import", response_model=ImportMessagesResponse)
def import_reverb_messages(
    request: ImportOrdersRequest,  # Reuse same params (days_back, etc)
    db: Session = Depends(get_db)
):
    """
    Import messages/conversations from Reverb.
    """
    try:
        # Get credentials
        try:
            credentials = get_reverb_credentials(db)
        except (CredentialsNotConfiguredError, CredentialsDisabledError) as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 1. Fetch Conversations List (with debug for raw samples)
        print(f"[REVERB_MESSAGES] action=START limit={request.limit} dry_run={request.dry_run}")
        
        list_result = fetch_reverb_conversations(credentials, limit=request.limit, debug=request.debug)
        conversations = list_result.get("conversations", [])
        
        conversations_fetched = len(conversations)
        conversations_created = 0
        conversations_updated = 0
        messages_fetched = 0
        messages_created = 0
        customers_linked = 0
        skipped_missing_id = 0
        debug_samples: List[Dict[str, Any]] = []
        
        # Include raw samples from service if debug
        if request.debug and "raw_samples" in list_result:
            for raw_sample in list_result["raw_samples"]:
                debug_samples.append({
                    "_raw_conversation_sample": True,
                    "keys": list(raw_sample.keys()),
                    "id": raw_sample.get("id"),
                    "_links": raw_sample.get("_links"),
                })
        
        # Create import run only if not dry run (optional, reusing MarketplaceImportRun could vary)
        import_run_id = None 

        for idx, conv in enumerate(conversations):
            # Use normalized ID from service
            external_id = conv.get("_normalized_id")
            raw_has_id = conv.get("id") is not None
            self_href = conv.get("_links", {}).get("self", {}).get("href", "")
            
            # Handle missing conversation ID
            if not external_id:
                skipped_missing_id += 1
                if request.debug:
                    debug_samples.append({
                        "missing_conversation_id": True,
                        "raw_has_id": raw_has_id,
                        "self_href": self_href,
                        "available_keys": list(conv.keys()),
                    })
                continue
            
            # Rate limit: sleep between detail calls (except first)
            if idx > 0:
                time.sleep(0.15)
            
            # 2. Fetch Detail (to get messages)
            detail = fetch_reverb_conversation_detail(credentials, external_id)
            if detail.get("error"):
                print(f"[REVERB_MESSAGES] error fetching detail id={external_id} err={detail.get('error')}")
                if request.debug:
                    debug_samples.append({
                        "conversation_id": external_id,
                        "error": detail.get("error"),
                        "status_code": detail.get("status_code"),
                    })
                continue
            
            # Count messages in this conversation
            msgs = detail.get("messages", []) or []
            messages_fetched += len(msgs)
            
            # Find last_message_at if present
            last_message_at = None
            if msgs:
                # Try to find the most recent message timestamp
                for msg in msgs:
                    msg_time = msg.get("created_at") or msg.get("sent_at")
                    if msg_time and (last_message_at is None or msg_time > last_message_at):
                        last_message_at = msg_time
                 
            # 3. Upsert Logic
            if request.dry_run:
                # Build debug sample with consistent structure
                sample: Dict[str, Any] = {
                    "conversation_id": external_id,
                    "raw_has_id": raw_has_id,
                    "self_href": self_href,
                    "messages_found": len(msgs),
                    "last_message_at": last_message_at,
                }
                # Look for order references in the conversation data
                for key in detail.keys():
                    if "order" in key.lower():
                        sample[key] = detail[key]
                # Also check listing info which may link to orders
                if "listing" in detail:
                    sample["listing"] = detail.get("listing")
                    
                debug_samples.append(sample)
            else:
                # Helper to process conversation (pass debug for first 3)
                collect_debug = request.debug and len(debug_samples) < 3
                res = _upsert_conversation(db, detail, debug=collect_debug)
                if res["created"]: conversations_created += 1
                else: conversations_updated += 1
                 
                messages_created += res["msg_created"]
                 
                if res["linked_customer"]:
                    customers_linked += 1
                
                # Collect debug stats for first 3 conversations
                if collect_debug and "debug_stats" in res:
                    debug_samples.append({
                        "conversation_id": external_id,
                        "upsert_stats": res["debug_stats"]
                    })

        if not request.dry_run:
            db.commit()
        
        print(f"[REVERB_MESSAGES] action=DONE fetched={conversations_fetched} created={conversations_created} updated={conversations_updated} msgs_fetched={messages_fetched} msgs_created={messages_created} skipped_missing_id={skipped_missing_id}")

        return ImportMessagesResponse(
            import_run_id=None,
            dry_run=request.dry_run,
            conversations_fetched=conversations_fetched,
            conversations_created=conversations_created,
            conversations_updated=conversations_updated,
            messages_fetched=messages_fetched,
            messages_created=messages_created,
            customers_linked=customers_linked,
            debug_samples=debug_samples if request.debug else []
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[REVERB_MESSAGES] unhandled_exception error={repr(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

import re as _re_module  # Use module-level import to avoid re-importing

def _normalize_text(s: Optional[str]) -> str:
    """
    Normalize text for stable hashing.
    
    - None -> ""
    - Convert \\r\\n to \\n
    - Strip leading/trailing whitespace
    - Collapse all internal whitespace (spaces, tabs, newlines) to single space
    """
    if s is None:
        return ""
    text = str(s)
    # Convert Windows line endings to Unix
    text = text.replace("\r\n", "\n")
    # Strip leading/trailing whitespace
    text = text.strip()
    # Collapse all internal whitespace to single space
    text = _re_module.sub(r'\s+', ' ', text)
    return text


def _parse_dt_utc(dt_raw: Optional[str]) -> str:
    """
    Parse an ISO datetime string and convert to normalized UTC string.
    
    - If dt_raw missing/None/empty -> ""
    - Parse ISO string with timezone offsets (-06:00, +01:00, Z)
    - Convert to UTC
    - Return isoformat(timespec="seconds"), e.g., "2026-01-15T00:24:55+00:00"
    
    This prevents drift from different timezone representations of the same instant.
    """
    if not dt_raw:
        return ""
    try:
        dt_str = str(dt_raw).strip()
        if not dt_str:
            return ""
        # Handle 'Z' suffix (UTC)
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        # Parse the datetime
        dt = datetime.fromisoformat(dt_str)
        # Convert to UTC
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(timezone.utc)
        else:
            # If no timezone, assume UTC
            dt_utc = dt.replace(tzinfo=timezone.utc)
        # Return normalized format
        return dt_utc.isoformat(timespec="seconds")
    except Exception:
        # If parsing fails, return empty string (will still hash but won't be stable)
        return ""


def _stable_synthetic_message_id(conversation_external_id: str, msg: Dict[str, Any]) -> str:
    """
    Generate a stable, deterministic synthetic message ID.
    
    Seed components (in exact order, newline-separated):
    1. conversation_external_id (string)
    2. created_at_utc = _parse_dt_utc(msg.get("created_at"))
    3. author_stable = first non-empty from author.id/user_id/username/name, sender_id, user_id
    4. body_norm = normalized body text (try body, message, text fields)
    5. photos_count = len(msg.get("photos") or [])
    
    Returns: "synthetic:{24-char-hex}"
    """
    # 1. conversation_external_id
    conv_id = str(conversation_external_id).strip() if conversation_external_id else ""
    
    # 2. created_at_utc - NORMALIZE TO UTC
    created_at_utc = _parse_dt_utc(msg.get("created_at"))
    
    # 3. author_stable - pick first non-empty
    author_stable = ""
    author = msg.get("author")
    if author and isinstance(author, dict):
        for key in ["id", "user_id", "username", "name"]:
            val = author.get(key)
            if val is not None and str(val).strip():
                author_stable = str(val).strip()
                break
    if not author_stable:
        # Try top-level sender_id or user_id
        if msg.get("sender_id"):
            author_stable = str(msg.get("sender_id")).strip()
        elif msg.get("user_id"):
            author_stable = str(msg.get("user_id")).strip()
    
    # 4. body_norm - normalized body text (try multiple fields)
    body_raw = msg.get("body") or msg.get("message") or msg.get("text") or ""
    body_norm = _normalize_text(body_raw)
    
    # 5. photos_count
    photos = msg.get("photos") or []
    photos_count = len(photos) if isinstance(photos, list) else 0
    
    # Build seed as newline-separated parts (as specified)
    seed_parts = [
        conv_id,
        created_at_utc,
        author_stable,
        body_norm,
        str(photos_count)
    ]
    seed = "\n".join(seed_parts)
    
    # Hash with SHA256, take first 24 chars
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    
    return f"synthetic:{digest}"


def _upsert_conversation(db: Session, data: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    """Upsert conversation and its messages."""
    
    # Extract conversation ID - try normalized ID first, then raw id
    external_id = data.get("_normalized_id") or data.get("id")
    if external_id:
        external_id = str(external_id).strip()
    else:
        # Fallback: should not happen if caller validates
        external_id = "unknown"
    
    marketplace = Marketplace.REVERB.value
    
    # Check exist
    conv = db.query(MarketplaceConversation).filter(
        MarketplaceConversation.marketplace == marketplace,
        MarketplaceConversation.external_conversation_id == external_id
    ).first()
    
    is_new = False
    if not conv:
        is_new = True
        conv = MarketplaceConversation(
            marketplace=marketplace,
            external_conversation_id=external_id
        )
        db.add(conv)
    
    # Update fields
    conv.raw_conversation_data = data
    
    # Process Messages
    msgs = data.get("messages", []) or []
    
    # Debug stats
    messages_total_in_payload = len(msgs)
    messages_skipped_existing_db = 0
    messages_skipped_duplicate_in_payload = 0
    messages_inserted = 0
    synthetic_ids_used_count = 0
    messages_skipped_no_data = 0
    synthetic_id_preview: List[Dict[str, str]] = []  # For debug
    
    # Sort messages by date to find last message time deterministically
    def parse_msg_time(t):
        if not t: return datetime.min
        try: return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        except: return datetime.min
        
    sorted_msgs = sorted(msgs, key=lambda x: parse_msg_time(x.get("created_at")))
    if sorted_msgs:
        last_msg = sorted_msgs[-1]
        conv.last_message_at = parse_msg_time(last_msg.get("created_at"))
    
    # Try to link Order ID
    if data.get("order_id"):
        conv.external_order_id = str(data.get("order_id"))
    
    db.flush()  # Get conv.id
    
    # Fetch existing message IDs from DB for this conversation (once)
    existing_msg_ids: set = set()
    existing_rows = db.query(MarketplaceMessage.external_message_id).filter(
        MarketplaceMessage.conversation_id == conv.id
    ).all()
    for r in existing_rows:
        if r and r[0] is not None and str(r[0]).strip():
            existing_msg_ids.add(str(r[0]).strip())
    
    # In-memory dedupe for this payload
    payload_seen_ids: set = set()
        
    for m in msgs:
        raw_id = m.get("id")
        
        # Determine external_message_id
        if raw_id is not None and str(raw_id).strip() and str(raw_id).strip() != "None":
            m_id = str(raw_id).strip()
            is_synthetic = False
        else:
            # Check if we have any data to create stable ID
            created_at_raw = m.get("created_at") or ""
            body_raw = m.get("body") or m.get("message") or m.get("text") or ""
            if not created_at_raw and not body_raw:
                # Cannot generate stable synthetic ID - skip
                messages_skipped_no_data += 1
                continue
            
            m_id = _stable_synthetic_message_id(external_id, m)
            is_synthetic = True
            synthetic_ids_used_count += 1
            
            # Collect preview for debug (first 3 only)
            if debug and len(synthetic_id_preview) < 3:
                created_at_utc = _parse_dt_utc(created_at_raw)
                synthetic_id_preview.append({
                    "synthetic_id": m_id,
                    "created_at_raw": str(created_at_raw) if created_at_raw else "",
                    "created_at_utc": created_at_utc,
                    "body_preview": (_normalize_text(body_raw)[:50] + "...") if len(_normalize_text(body_raw)) > 50 else _normalize_text(body_raw)
                })
        
        # Ensure m_id is valid (never empty, None, or "None")
        m_id = str(m_id).strip() if m_id else ""
        if not m_id or m_id == "None":
            messages_skipped_no_data += 1
            continue
        
        # DB dedupe: skip if already exists in database
        if m_id in existing_msg_ids:
            messages_skipped_existing_db += 1
            continue
        
        # In-memory dedupe: skip if already seen in this payload
        if m_id in payload_seen_ids:
            messages_skipped_duplicate_in_payload += 1
            continue
        
        # Mark as seen in this payload
        payload_seen_ids.add(m_id)
        
        # Insert the message
        body = m.get("body") or ""
        sent_ts = parse_msg_time(m.get("created_at"))
        sender_type = "unknown"
        
        new_msg = MarketplaceMessage(
            conversation_id=conv.id,
            external_message_id=m_id,
            body_text=body,
            raw_message_data=m,
            sender_type=sender_type,
            sent_at=sent_ts
        )
        db.add(new_msg)
        messages_inserted += 1
        
        # Add to existing set to prevent re-inserting in same run
        existing_msg_ids.add(m_id)
        
    result: Dict[str, Any] = {
        "created": is_new,
        "msg_count": messages_total_in_payload,
        "msg_created": messages_inserted,
        "linked_customer": False
    }
    
    # Add debug stats if requested
    if debug:
        result["debug_stats"] = {
            "conversation_external_id": external_id,
            "messages_total_in_payload": messages_total_in_payload,
            "messages_inserted": messages_inserted,
            "messages_skipped_existing_db": messages_skipped_existing_db,
            "messages_skipped_duplicate_in_payload": messages_skipped_duplicate_in_payload,
            "messages_skipped_no_data": messages_skipped_no_data,
            "synthetic_ids_used": synthetic_ids_used_count,
            "synthetic_id_preview": synthetic_id_preview
        }
        
    return result


# =============================================================================
# Normalization Helpers
# =============================================================================

def _extract_reverb_buyer_info(raw: dict) -> dict:
    """Extract buyer info from Reverb raw_marketplace_data."""
    return {
        "buyer_email": raw.get("buyer_email"),
        "buyer_name": raw.get("buyer", {}).get("first_name") if raw.get("buyer") else None,
    }


def _extract_reverb_totals(raw: dict) -> dict:
    """Extract monetary totals from Reverb raw_marketplace_data."""
    totals = {}

    # amount_product → items_subtotal_cents
    amount_product = raw.get("amount_product", {})
    if amount_product and amount_product.get("amount_cents") is not None:
        totals["items_subtotal_cents"] = amount_product.get("amount_cents")

    # shipping → shipping_cents
    shipping = raw.get("shipping", {})
    if shipping and shipping.get("amount_cents") is not None:
        totals["shipping_cents"] = shipping.get("amount_cents")

    # amount_tax → tax_cents
    amount_tax = raw.get("amount_tax", {})
    if amount_tax and amount_tax.get("amount_cents") is not None:
        totals["tax_cents"] = amount_tax.get("amount_cents")

    # total → order_total_cents
    total = raw.get("total", {})
    if total and total.get("amount_cents") is not None:
        totals["order_total_cents"] = total.get("amount_cents")

    # Currency code (prefer from total, fallback to amount_product)
    currency = None
    if total and total.get("currency"):
        currency = total.get("currency")
    elif amount_product and amount_product.get("currency"):
        currency = amount_product.get("currency")

    if currency:
        totals["currency_code"] = currency

    return totals


def _extract_reverb_shipping_address(raw: dict, external_order_id: str) -> Optional[dict]:
    """Extract shipping address from Reverb raw_marketplace_data."""
    shipping_addr = raw.get("shipping_address")
    if not shipping_addr:
        return None

    return {
        "address_type": "shipping",
        "name": shipping_addr.get("name"),
        "line1": shipping_addr.get("street_address"),
        "line2": shipping_addr.get("extended_address"),
        "city": shipping_addr.get("locality"),
        "state_or_region": shipping_addr.get("region"),
        "postal_code": shipping_addr.get("postal_code"),
        "country_code": shipping_addr.get("country_code"),
        "phone": shipping_addr.get("phone"),
        "raw_payload": shipping_addr,  # Store original for debugging
    }


def _extract_reverb_line_item(raw: dict, external_order_id: str) -> dict:
    """Create a minimal line item from Reverb raw_marketplace_data."""
    product_id = raw.get("product_id") or raw.get("product", {}).get("id")
    quantity = raw.get("quantity", 1)

    # Get price from amount_product
    amount_product = raw.get("amount_product", {})
    line_total_cents = amount_product.get("amount_cents") if amount_product else None
    unit_price_cents = line_total_cents // quantity if line_total_cents and quantity else None

    # Generate deterministic external_line_item_id
    external_line_item_id = f"{external_order_id}-1"

    # Try to get title from product
    title = None
    product = raw.get("product")
    if product:
        title = product.get("title") or product.get("name")
    if not title and product_id:
        title = f"(Reverb product {product_id})"

    return {
        "external_line_item_id": external_line_item_id,
        "product_id": str(product_id) if product_id else None,
        "quantity": quantity,
        "unit_price_cents": unit_price_cents,
        "line_total_cents": line_total_cents,
        "title": title,
        "sku": raw.get("sku"),
    }


@router.post("/normalize", response_model=NormalizeOrdersResponse)
def normalize_reverb_orders(
    request: NormalizeOrdersRequest,
    db: Session = Depends(get_db)
):
    """
    Normalize existing Reverb orders by populating buyer, totals, addresses, and lines
    from raw_marketplace_data.

    Parameters:
    - days_back: Number of days back to filter orders (default 30)
    - limit: Maximum orders to process (default 200)
    - dry_run: If true, compute but don't write changes (default true)
    - debug: If true, include debug info in response
    - force_rebuild_lines: If true, rebuild lines even if they exist (default false)
    """
    try:
        # Calculate date cutoff
        cutoff = datetime.utcnow() - timedelta(days=request.days_back)

        print(f"[REVERB_NORMALIZE] action=START days_back={request.days_back} limit={request.limit} dry_run={request.dry_run} force_rebuild_lines={request.force_rebuild_lines}")

        # Query Reverb orders with raw_marketplace_data
        orders = db.query(MarketplaceOrder).filter(
            MarketplaceOrder.marketplace == Marketplace.REVERB,
            MarketplaceOrder.order_date >= cutoff,
            MarketplaceOrder.raw_marketplace_data.isnot(None)
        ).order_by(MarketplaceOrder.order_date.desc()).limit(request.limit).all()

        orders_scanned = len(orders)
        orders_updated = 0
        orders_skipped = 0
        addresses_upserted = 0
        lines_upserted = 0
        preview = []
        debug_info = {} if request.debug else None

        for order in orders:
            raw = order.raw_marketplace_data
            if not isinstance(raw, dict):
                orders_skipped += 1
                continue

            external_order_id = order.external_order_id or str(order.id)
            order_updated = False
            preview_item = {"order_id": order.id, "external_order_id": external_order_id}

            # 1. Extract and apply buyer info
            buyer_info = _extract_reverb_buyer_info(raw)
            if buyer_info.get("buyer_email") and not order.buyer_email:
                if not request.dry_run:
                    order.buyer_email = buyer_info["buyer_email"]
                preview_item["buyer_email"] = buyer_info["buyer_email"]
                order_updated = True
            if buyer_info.get("buyer_name") and not order.buyer_name:
                if not request.dry_run:
                    order.buyer_name = buyer_info["buyer_name"]
                preview_item["buyer_name"] = buyer_info["buyer_name"]
                order_updated = True

            # 2. Extract and apply totals
            totals = _extract_reverb_totals(raw)
            for field, value in totals.items():
                current_value = getattr(order, field, None)
                if value is not None and current_value is None:
                    if not request.dry_run:
                        setattr(order, field, value)
                    preview_item[field] = value
                    order_updated = True

            # 3. Extract and upsert shipping address
            addr_data = _extract_reverb_shipping_address(raw, external_order_id)
            if addr_data:
                preview_item["address"] = {
                    "city": addr_data.get("city"),
                    "state_or_region": addr_data.get("state_or_region"),
                    "country_code": addr_data.get("country_code"),
                }

                if not request.dry_run:
                    # Check if shipping address already exists
                    existing_addr = db.query(MarketplaceOrderAddress).filter(
                        MarketplaceOrderAddress.order_id == order.id,
                        MarketplaceOrderAddress.address_type == "shipping"
                    ).first()

                    if existing_addr:
                        # Update existing
                        for key, val in addr_data.items():
                            if key != "address_type" and val is not None:
                                setattr(existing_addr, key, val)
                    else:
                        # Create new
                        new_addr = MarketplaceOrderAddress(
                            order_id=order.id,
                            address_type=addr_data.get("address_type", "shipping"),
                            name=addr_data.get("name"),
                            line1=addr_data.get("line1"),
                            line2=addr_data.get("line2"),
                            city=addr_data.get("city"),
                            state_or_region=addr_data.get("state_or_region"),
                            postal_code=addr_data.get("postal_code"),
                            country_code=addr_data.get("country_code"),
                            phone=addr_data.get("phone"),
                            raw_payload=addr_data.get("raw_payload")
                        )
                        db.add(new_addr)

                    addresses_upserted += 1
                else:
                    addresses_upserted += 1  # Count for preview

                order_updated = True

            # 4. Extract and upsert line item (only if no lines exist or force_rebuild)
            existing_lines_count = db.query(MarketplaceOrderLine).filter(
                MarketplaceOrderLine.order_id == order.id
            ).count()

            should_create_line = (existing_lines_count == 0) or request.force_rebuild_lines

            if should_create_line:
                line_data = _extract_reverb_line_item(raw, external_order_id)
                preview_item["line"] = {
                    "title": line_data.get("title"),
                    "quantity": line_data.get("quantity"),
                    "line_total_cents": line_data.get("line_total_cents"),
                }

                if not request.dry_run:
                    if request.force_rebuild_lines and existing_lines_count > 0:
                        # Delete existing lines first
                        db.query(MarketplaceOrderLine).filter(
                            MarketplaceOrderLine.order_id == order.id
                        ).delete(synchronize_session=False)

                    new_line = MarketplaceOrderLine(
                        order_id=order.id,
                        external_line_item_id=line_data.get("external_line_item_id"),
                        product_id=line_data.get("product_id"),
                        sku=line_data.get("sku"),
                        title=line_data.get("title"),
                        quantity=line_data.get("quantity", 1),
                        unit_price_cents=line_data.get("unit_price_cents"),
                        line_total_cents=line_data.get("line_total_cents"),
                    )
                    db.add(new_line)
                    lines_upserted += 1
                else:
                    lines_upserted += 1  # Count for preview

                order_updated = True
            else:
                preview_item["line_skipped"] = f"existing_lines={existing_lines_count}"

            if order_updated:
                orders_updated += 1
                if len(preview) < 3:
                    preview.append(preview_item)
            else:
                orders_skipped += 1

        if not request.dry_run:
            db.commit()

        print(f"[REVERB_NORMALIZE] scanned={orders_scanned} updated={orders_updated} skipped={orders_skipped} addresses={addresses_upserted} lines={lines_upserted} dry_run={request.dry_run}")

        if request.debug:
            debug_info = {
                "cutoff_utc": cutoff.isoformat(),
                "days_back": request.days_back,
                "limit": request.limit,
                "force_rebuild_lines": request.force_rebuild_lines,
            }

        return NormalizeOrdersResponse(
            dry_run=request.dry_run,
            orders_scanned=orders_scanned,
            orders_updated=orders_updated,
            addresses_upserted=addresses_upserted,
            lines_upserted=lines_upserted,
            orders_skipped=orders_skipped,
            preview=preview if preview else None,
            debug=debug_info
        )

    except Exception as e:
        print(f"[REVERB_NORMALIZE] unhandled_exception error={repr(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/enrich", response_model=EnrichOrdersResponse)
def enrich_reverb_orders(
    request: EnrichOrdersRequest,
    db: Session = Depends(get_db)
):
    """
    Enrich existing Reverb orders by fetching full details from Reverb API.

    For each order, calls Reverb's order detail endpoint to get:
    - Full shipping address
    - Line items with product details
    - Shipment tracking info

    Parameters:
    - days_back: Number of days back to filter orders (default 30)
    - since_iso: ISO datetime to filter from (overrides days_back)
    - limit: Maximum orders to process (default 50)
    - dry_run: If true, fetch details but don't write to DB (default true)
    - debug: If true, include debug info in response
    - force: If true, overwrite existing non-null fields
    """
    import time

    try:
        # Get credentials
        try:
            credentials = get_reverb_credentials(db)
        except CredentialsNotConfiguredError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except CredentialsDisabledError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Calculate date cutoff
        filter_mode = "days_back"
        if request.since_iso:
            try:
                cutoff = _parse_since_iso(request.since_iso)
                filter_mode = "since_iso"
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            cutoff = datetime.utcnow() - timedelta(days=request.days_back)

        print(f"[REVERB_ENRICH] action=START days_back={request.days_back} limit={request.limit} dry_run={request.dry_run} force={request.force}")

        # Query Reverb orders
        orders = db.query(MarketplaceOrder).filter(
            MarketplaceOrder.marketplace == Marketplace.REVERB,
            MarketplaceOrder.order_date >= cutoff
        ).order_by(MarketplaceOrder.order_date.desc()).limit(request.limit).all()

        orders_scanned = len(orders)
        orders_enriched = 0
        orders_skipped = 0
        lines_upserted = 0
        addresses_upserted = 0
        shipments_upserted = 0
        failed_order_ids = {}
        preview_orders = []

        for order in orders:
            external_order_id = order.external_order_id
            if not external_order_id:
                orders_skipped += 1
                continue

            # Fetch order detail from Reverb API
            detail = get_order_detail(credentials, external_order_id)

            # Small delay between API calls to avoid rate limiting
            time.sleep(0.15)

            # Check for API errors
            if detail.get("error"):
                failed_order_ids[external_order_id] = detail.get("error")
                orders_skipped += 1
                continue

            # Parse enrichment data
            enrichment = parse_order_detail_for_enrichment(detail, external_order_id)

            preview_item = {
                "external_order_id": external_order_id,
                "order_id": order.id,
            }
            order_enriched = False

            # === Update order scalar fields ===
            buyer_info = enrichment.get("buyer", {})
            totals = enrichment.get("totals", {})

            # Buyer email
            if buyer_info.get("buyer_email"):
                if order.buyer_email is None or request.force:
                    if not request.dry_run:
                        order.buyer_email = buyer_info["buyer_email"]
                    preview_item["buyer_email"] = buyer_info["buyer_email"]
                    order_enriched = True

            # Buyer name
            if buyer_info.get("buyer_name"):
                if order.buyer_name is None or request.force:
                    if not request.dry_run:
                        order.buyer_name = buyer_info["buyer_name"]
                    preview_item["buyer_name"] = buyer_info["buyer_name"]
                    order_enriched = True

            # Totals
            for field in ["items_subtotal_cents", "shipping_cents", "tax_cents", "order_total_cents", "currency_code"]:
                new_val = totals.get(field)
                if new_val is not None:
                    current_val = getattr(order, field, None)
                    if current_val is None or request.force:
                        if not request.dry_run:
                            setattr(order, field, new_val)
                        preview_item[field] = new_val
                        order_enriched = True

            # Status
            if enrichment.get("status_raw"):
                if order.status_raw is None or request.force:
                    if not request.dry_run:
                        order.status_raw = enrichment["status_raw"]
                        if enrichment.get("status_normalized"):
                            try:
                                order.status_normalized = NormalizedOrderStatus(enrichment["status_normalized"])
                            except ValueError:
                                pass
                    order_enriched = True

            # === Upsert shipping address ===
            addr_data = enrichment.get("shipping_address")
            if addr_data and any(addr_data.get(k) for k in ["line1", "city", "postal_code"]):
                preview_item["shipping"] = {
                    "name": addr_data.get("name"),
                    "line1": addr_data.get("line1"),
                    "city": addr_data.get("city"),
                    "state_or_region": addr_data.get("state_or_region"),
                    "postal_code": addr_data.get("postal_code"),
                    "country_code": addr_data.get("country_code"),
                }

                if not request.dry_run:
                    existing_addr = db.query(MarketplaceOrderAddress).filter(
                        MarketplaceOrderAddress.order_id == order.id,
                        MarketplaceOrderAddress.address_type == "shipping"
                    ).first()

                    if existing_addr:
                        for key in ["name", "phone", "line1", "line2", "city", "state_or_region", "postal_code", "country_code", "raw_payload"]:
                            new_val = addr_data.get(key)
                            if new_val is not None and (getattr(existing_addr, key, None) is None or request.force):
                                setattr(existing_addr, key, new_val)
                    else:
                        new_addr = MarketplaceOrderAddress(
                            order_id=order.id,
                            address_type="shipping",
                            name=addr_data.get("name"),
                            phone=addr_data.get("phone"),
                            line1=addr_data.get("line1"),
                            line2=addr_data.get("line2"),
                            city=addr_data.get("city"),
                            state_or_region=addr_data.get("state_or_region"),
                            postal_code=addr_data.get("postal_code"),
                            country_code=addr_data.get("country_code"),
                            raw_payload=addr_data.get("raw_payload")
                        )
                        db.add(new_addr)

                    addresses_upserted += 1
                else:
                    addresses_upserted += 1

                order_enriched = True

            # === Upsert line items ===
            lines = enrichment.get("lines", [])
            if lines:
                preview_item["lines"] = []
                for line_data in lines:
                    ext_line_id = line_data.get("external_line_item_id")
                    preview_item["lines"].append({
                        "title": line_data.get("title"),
                        "sku": line_data.get("sku"),
                        "quantity": line_data.get("quantity"),
                        "line_total_cents": line_data.get("line_total_cents"),
                    })

                    if not request.dry_run:
                        existing_line = None
                        if ext_line_id:
                            existing_line = db.query(MarketplaceOrderLine).filter(
                                MarketplaceOrderLine.order_id == order.id,
                                MarketplaceOrderLine.external_line_item_id == ext_line_id
                            ).first()

                        if existing_line:
                            for key in ["product_id", "listing_id", "sku", "title", "quantity", "unit_price_cents", "line_total_cents", "currency_code", "raw_marketplace_data"]:
                                new_val = line_data.get(key)
                                if new_val is not None and (getattr(existing_line, key, None) is None or request.force):
                                    setattr(existing_line, key, new_val)
                        else:
                            new_line = MarketplaceOrderLine(
                                order_id=order.id,
                                external_line_item_id=ext_line_id,
                                product_id=line_data.get("product_id"),
                                listing_id=line_data.get("listing_id"),
                                sku=line_data.get("sku"),
                                title=line_data.get("title"),
                                quantity=line_data.get("quantity", 1),
                                unit_price_cents=line_data.get("unit_price_cents"),
                                line_total_cents=line_data.get("line_total_cents"),
                                currency_code=line_data.get("currency_code"),
                                raw_marketplace_data=line_data.get("raw_marketplace_data")
                            )
                            db.add(new_line)

                        lines_upserted += 1
                    else:
                        lines_upserted += 1

                order_enriched = True

            # === Upsert shipments ===
            shipments = enrichment.get("shipments", [])
            if shipments:
                preview_item["shipments"] = []
                for ship_data in shipments:
                    tracking = ship_data.get("tracking_number")
                    carrier = ship_data.get("carrier")
                    dedupe_key = ship_data.get("dedupe_key", "")

                    preview_item["shipments"].append({
                        "carrier": carrier,
                        "tracking_number": tracking,
                        "shipped_at": ship_data.get("shipped_at"),
                        "dedupe_key": dedupe_key,
                    })

                    if not request.dry_run:
                        existing_ship = None

                        if tracking:
                            existing_ship = db.query(MarketplaceOrderShipment).filter(
                                MarketplaceOrderShipment.order_id == order.id,
                                MarketplaceOrderShipment.tracking_number == tracking
                            ).first()
                        else:
                            shipped_at_str = ship_data.get("shipped_at")
                            if shipped_at_str and carrier:
                                try:
                                    if shipped_at_str.endswith("Z"):
                                        shipped_at_str_parsed = shipped_at_str[:-1] + "+00:00"
                                    else:
                                        shipped_at_str_parsed = shipped_at_str
                                    target_shipped_at = datetime.fromisoformat(shipped_at_str_parsed)

                                    candidates = db.query(MarketplaceOrderShipment).filter(
                                        MarketplaceOrderShipment.order_id == order.id,
                                        MarketplaceOrderShipment.carrier == carrier
                                    ).all()

                                    for cand in candidates:
                                        if cand.shipped_at and abs((cand.shipped_at - target_shipped_at).total_seconds()) < 60:
                                            existing_ship = cand
                                            break
                                except (ValueError, TypeError):
                                    pass

                        if existing_ship:
                            for key in ["carrier", "tracking_number"]:
                                new_val = ship_data.get(key if key != "tracking_number" else "tracking_number")
                                if key == "tracking_number":
                                    new_val = tracking
                                if new_val is not None and (getattr(existing_ship, key, None) is None or request.force):
                                    setattr(existing_ship, key, new_val)
                        else:
                            shipped_at = None
                            shipped_at_str = ship_data.get("shipped_at")
                            if shipped_at_str:
                                try:
                                    if shipped_at_str.endswith("Z"):
                                        shipped_at_str = shipped_at_str[:-1] + "+00:00"
                                    shipped_at = datetime.fromisoformat(shipped_at_str)
                                except (ValueError, TypeError):
                                    pass

                            delivered_at = None
                            delivered_at_str = ship_data.get("delivered_at")
                            if delivered_at_str:
                                try:
                                    if delivered_at_str.endswith("Z"):
                                        delivered_at_str = delivered_at_str[:-1] + "+00:00"
                                    delivered_at = datetime.fromisoformat(delivered_at_str)
                                except (ValueError, TypeError):
                                    pass

                            new_ship = MarketplaceOrderShipment(
                                order_id=order.id,
                                carrier=carrier,
                                tracking_number=tracking,
                                shipped_at=shipped_at,
                                delivered_at=delivered_at,
                                raw_marketplace_data=ship_data.get("raw_payload")
                            )
                            db.add(new_ship)
                            shipments_upserted += 1
                    else:
                        shipments_upserted += 1

                order_enriched = True

            if order_enriched:
                orders_enriched += 1
                if len(preview_orders) < 3:
                    preview_orders.append(preview_item)
            else:
                orders_skipped += 1

        if not request.dry_run:
            db.commit()

        print(f"[REVERB_ENRICH] scanned={orders_scanned} enriched={orders_enriched} skipped={orders_skipped} addresses={addresses_upserted} lines={lines_upserted} shipments={shipments_upserted} dry_run={request.dry_run}")

        debug_info = None
        if request.debug:
            debug_info = {
                "filter_mode": filter_mode,
                "filter_since_utc": cutoff.isoformat(),
                "limit": request.limit,
                "force": request.force,
            }

        return EnrichOrdersResponse(
            dry_run=request.dry_run,
            orders_scanned=orders_scanned,
            orders_enriched=orders_enriched,
            orders_skipped=orders_skipped,
            lines_upserted=lines_upserted,
            addresses_upserted=addresses_upserted,
            shipments_upserted=shipments_upserted,
            failed_order_ids=failed_order_ids if failed_order_ids else None,
            preview_orders=preview_orders if preview_orders else None,
            debug=debug_info
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[REVERB_ENRICH] unhandled_exception error={repr(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")
