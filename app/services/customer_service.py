"""
Customer service for deterministic customer upsert during marketplace order import.

Matching priority:
1. If source_customer_id exists: match on (source_marketplace, source_customer_id)
2. Else if marketplace_buyer_email exists: match on (source_marketplace, marketplace_buyer_email)
3. Else create new customer

Write rules:
- Always store marketplace relay email into marketplace_buyer_email
- NEVER overwrite buyer_email from marketplace import
- If customer field has value and incoming is blank: do NOT overwrite
- If customer field is NULL and incoming has value: fill it
"""
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.core import Customer, MarketplaceOrderAddress
from app.utils.normalization import normalize_marketplace, normalize_identifier


def upsert_customer_from_marketplace_order(
    db: Session,
    marketplace: str,
    source_customer_id: Optional[str],
    marketplace_buyer_email: Optional[str],
    buyer_name: Optional[str],
    buyer_phone: Optional[str],
    shipping_address: Optional[Dict[str, Any]] = None,
    billing_address: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Customer], Dict[str, bool]]:
    """
    Find or create a Customer from marketplace order data.
    
    Args:
        db: Database session
        marketplace: Marketplace name (e.g., "reverb", "ebay")
        source_customer_id: Marketplace-provided buyer/user ID (if available)
        marketplace_buyer_email: Relay/proxy email from marketplace
        buyer_name: Buyer's name from order
        buyer_phone: Buyer's phone from order
        shipping_address: Dict with address fields from order
        billing_address: Dict with address fields from order
    
    Returns:
        Tuple of (Customer object or None, stats dict)
    """
    stats = {
        "created": False,
        "updated_name": False,
        "updated_shipping_name": False,
        "updated_address1": False,
        "updated_phone": False
    }

    # Normalize inputs
    norm_marketplace = normalize_marketplace(marketplace)
    norm_customer_id = normalize_identifier(source_customer_id)
    norm_email = normalize_identifier(marketplace_buyer_email)  # Strip whitespace
    
    if not norm_marketplace:
        # No marketplace = cannot link to customer
        return None, stats
    
    customer: Optional[Customer] = None
    
    # 1. Try (source_marketplace, source_customer_id) match
    if norm_customer_id:
        customer = db.query(Customer).filter(
            Customer.source_marketplace == norm_marketplace,
            Customer.source_customer_id == norm_customer_id
        ).first()
        if customer:
            print(f"[CUSTOMER_SERVICE] Matched customer id={customer.id} by source_marketplace={norm_marketplace}, source_customer_id={norm_customer_id}")
    
    # 2. Else try (source_marketplace, marketplace_buyer_email) match
    if not customer and norm_email:
        customer = db.query(Customer).filter(
            Customer.source_marketplace == norm_marketplace,
            Customer.marketplace_buyer_email == norm_email
        ).first()
        if customer:
            print(f"[CUSTOMER_SERVICE] Matched customer id={customer.id} by source_marketplace={norm_marketplace}, marketplace_buyer_email={norm_email}")
            # If we matched by email and now have a source_customer_id, update it
            if norm_customer_id and not customer.source_customer_id:
                customer.source_customer_id = norm_customer_id
    
    # 3. Create new customer if no match
    if not customer:
        # Require at least a name or some identifier to create
        if not buyer_name and not norm_email:
            print("[CUSTOMER_SERVICE] Insufficient data to create customer (no name or email)")
            return None, stats
        
        customer = Customer(
            name=buyer_name or "Unknown",
            source_marketplace=norm_marketplace,
            source_customer_id=norm_customer_id,
            marketplace_buyer_email=norm_email,
            # buyer_email intentionally NOT set during import
        )
        db.add(customer)
        stats["created"] = True
        print(f"[CUSTOMER_SERVICE] Created new customer source_marketplace={norm_marketplace}, source_customer_id={norm_customer_id}, marketplace_buyer_email={norm_email}")
    
    # Update fields with "fill if NULL, don't overwrite if has value" logic
    _update_if_null(customer, 'marketplace_buyer_email', norm_email)
    if _update_if_null(customer, 'phone', buyer_phone):
        stats["updated_phone"] = True
        
    # Also verify mobile_phone not overwritten but filled if explicit phone is better logic? 
    # Current logic relies on _update_if_null for specific fields below.
    
    # Parse buyer_name into first_name/last_name if we have name but not parsed names
    if buyer_name and not customer.first_name and not customer.last_name:
        parts = buyer_name.strip().split(' ', 1)
        if len(parts) >= 1:
            _update_if_null(customer, 'first_name', parts[0])
        if len(parts) >= 2:
            _update_if_null(customer, 'last_name', parts[1])
    
    # Update name if we have one
    if buyer_name and customer.name == "Unknown":
        customer.name = buyer_name
        stats["updated_name"] = True
    
    # Update shipping address fields if provided
    if shipping_address:
         # Only counts if it actually changed from None/Empty to Value
        if _update_if_null(customer, 'shipping_name', shipping_address.get('name')):
            stats["updated_shipping_name"] = True
            
        if _update_if_null(customer, 'shipping_address1', shipping_address.get('line1')):
            stats["updated_address1"] = True
            
        _update_if_null(customer, 'shipping_address2', shipping_address.get('line2'))
        _update_if_null(customer, 'shipping_city', shipping_address.get('city'))
        _update_if_null(customer, 'shipping_state', shipping_address.get('state_or_region'))
        _update_if_null(customer, 'shipping_postal_code', shipping_address.get('postal_code'))
        _update_if_null(customer, 'shipping_country', shipping_address.get('country_code'))
        
        # Also update phone if provided in address and we don't have one
        if _update_if_null(customer, 'mobile_phone', shipping_address.get('phone')):
             stats["updated_phone"] = True
    
    # Update billing address fields if provided
    if billing_address:
        _update_if_null(customer, 'billing_address1', billing_address.get('line1'))
        _update_if_null(customer, 'billing_address2', billing_address.get('line2'))
        _update_if_null(customer, 'billing_city', billing_address.get('city'))
        _update_if_null(customer, 'billing_state', billing_address.get('state_or_region'))
        _update_if_null(customer, 'billing_postal_code', billing_address.get('postal_code'))
        _update_if_null(customer, 'billing_country', billing_address.get('country_code'))
    
    return customer, stats


def _update_if_null(obj: Any, field: str, value: Optional[str]) -> bool:
    """
    Update field only if current value is NULL and incoming value is not empty.
    Returns True if update occurred.
    """
    if value and not getattr(obj, field, None):
        setattr(obj, field, value.strip() if isinstance(value, str) else value)
        return True
    return False


def extract_address_dict(order_addresses: list, address_type: str) -> Optional[Dict[str, Any]]:
    """
    Extract address data from order addresses list by type.
    
    Args:
        order_addresses: List of MarketplaceOrderAddress objects or dicts
        address_type: "shipping" or "billing"
    
    Returns:
        Dict with address fields or None
    """
    for addr in order_addresses:
        # Handle both ORM objects and dicts
        if hasattr(addr, 'address_type'):
            if addr.address_type == address_type:
                return {
                    'name': addr.name,
                    'phone': addr.phone,
                    'line1': addr.line1,
                    'line2': addr.line2,
                    'city': addr.city,
                    'state_or_region': addr.state_or_region,
                    'postal_code': addr.postal_code,
                    'country_code': addr.country_code,
                }
        elif isinstance(addr, dict):
            if addr.get('address_type') == address_type:
                return {
                    'name': addr.get('name'),
                    'phone': addr.get('phone'),
                    'line1': addr.get('line1'),
                    'line2': addr.get('line2'),
                    'city': addr.get('city'),
                    'state_or_region': addr.get('state_or_region'),
                    'postal_code': addr.get('postal_code'),
                    'country_code': addr.get('country_code'),
                }
    return None
