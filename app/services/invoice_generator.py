"""
Invoice Generation Service for Marketplace Orders.

Generates HTML invoices using resolved model identity for each line item,
with safe fallbacks for unmatched lines.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.core import MarketplaceOrder, MarketplaceOrderLine, Model


def format_cents(cents: Optional[int], currency: str = "USD") -> str:
    """Format cents as currency string."""
    if cents is None:
        return "—"
    dollars = cents / 100
    if currency == "USD":
        return f"${dollars:,.2f}"
    return f"{dollars:,.2f} {currency}"


def resolve_line_description(line: MarketplaceOrderLine, db: Session) -> str:
    """
    Get the best description for a line item.
    
    Priority:
    1. If line.model_id exists, use resolved model identity
    2. Else use line.title if present
    3. Else fallback to "Unmatched Item (product_id)"
    """
    if line.model_id:
        model = db.query(Model).filter(Model.id == line.model_id).first()
        if model and model.series and model.series.manufacturer:
            return f"{model.series.manufacturer.name} / {model.series.name} / {model.name}"
        elif model:
            return model.name
    
    if line.title:
        return line.title
    
    if line.product_id:
        return f"Unmatched Item ({line.product_id})"
    
    return "Unknown Item"


def generate_invoice_html(orders: List[MarketplaceOrder], db: Session) -> str:
    """
    Generate HTML invoice for one or more marketplace orders.
    
    Args:
        orders: List of MarketplaceOrder objects to include
        db: Database session for model lookups
        
    Returns:
        HTML string containing the invoice
    """
    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    # Build order sections
    order_sections = []
    grand_total_cents = 0
    
    for order in orders:
        # Invoice number
        invoice_number = f"INV-{order.id}"
        
        # Customer info
        customer_name = order.buyer_name or "—"
        customer_email = order.buyer_email or "—"
        
        # Get shipping address
        ship_to_lines = []
        for addr in order.addresses:
            if addr.address_type.lower() in ("shipping", "ship_to", "ship-to"):
                if addr.name:
                    ship_to_lines.append(addr.name)
                if addr.line1:
                    ship_to_lines.append(addr.line1)
                if addr.line2:
                    ship_to_lines.append(addr.line2)
                city_state_zip = " ".join(filter(None, [addr.city, addr.state_or_region, addr.postal_code]))
                if city_state_zip:
                    ship_to_lines.append(city_state_zip)
                if addr.country_code:
                    ship_to_lines.append(addr.country_code)
                break
        
        ship_to_html = "<br>".join(ship_to_lines) if ship_to_lines else "—"
        
        # Line items
        line_rows = []
        subtotal_cents = 0
        currency = order.currency_code or "USD"
        
        for line in order.lines:
            description = resolve_line_description(line, db)
            qty = line.quantity
            unit_price = format_cents(line.unit_price_cents, currency)
            line_total = format_cents(line.line_total_cents, currency)
            
            if line.line_total_cents is not None:
                subtotal_cents += line.line_total_cents
            
            line_rows.append(f"""
                <tr>
                    <td>{description}</td>
                    <td class="center">{qty}</td>
                    <td class="right">{unit_price}</td>
                    <td class="right">{line_total}</td>
                </tr>
            """)
        
        # Totals
        # Prefer order-level totals if available, else compute
        if order.items_subtotal_cents is not None:
            display_subtotal = format_cents(order.items_subtotal_cents, currency)
        else:
            display_subtotal = format_cents(subtotal_cents, currency) if subtotal_cents else "—"
        
        shipping = format_cents(order.shipping_cents, currency)
        tax = format_cents(order.tax_cents, currency)
        
        if order.order_total_cents is not None:
            display_total = format_cents(order.order_total_cents, currency)
            grand_total_cents += order.order_total_cents
        else:
            # Compute if we have all parts
            computed_total = None
            if subtotal_cents:
                computed_total = subtotal_cents
                if order.shipping_cents:
                    computed_total += order.shipping_cents
                if order.tax_cents:
                    computed_total += order.tax_cents
                if order.discount_cents:
                    computed_total -= order.discount_cents
            display_total = format_cents(computed_total, currency) if computed_total else "—"
            if computed_total:
                grand_total_cents += computed_total
        
        order_section = f"""
        <div class="order-section">
            <div class="order-header">
                <div class="invoice-info">
                    <h2>Invoice {invoice_number}</h2>
                    <p><strong>Marketplace:</strong> {order.marketplace.value if order.marketplace else "—"}</p>
                    <p><strong>Order Date:</strong> {order.order_date.strftime("%B %d, %Y") if order.order_date else "—"}</p>
                    <p><strong>External Order #:</strong> {order.external_order_number or order.external_order_id or "—"}</p>
                </div>
                <div class="customer-info">
                    <h3>Bill To</h3>
                    <p>{customer_name}</p>
                    <p>{customer_email}</p>
                </div>
                <div class="ship-to-info">
                    <h3>Ship To</h3>
                    <p>{ship_to_html}</p>
                </div>
            </div>
            
            <table class="line-items">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th class="center">Qty</th>
                        <th class="right">Unit Price</th>
                        <th class="right">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(line_rows)}
                </tbody>
            </table>
            
            <div class="totals">
                <table>
                    <tr><td>Subtotal:</td><td class="right">{display_subtotal}</td></tr>
                    <tr><td>Shipping:</td><td class="right">{shipping}</td></tr>
                    <tr><td>Tax:</td><td class="right">{tax}</td></tr>
                    <tr class="total-row"><td><strong>Total:</strong></td><td class="right"><strong>{display_total}</strong></td></tr>
                </table>
            </div>
        </div>
        """
        order_sections.append(order_section)
    
    # Build full HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.5;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .invoice-container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .company-header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #333;
        }}
        .company-header h1 {{
            font-size: 28px;
            margin-bottom: 5px;
        }}
        .generated-at {{
            color: #666;
            font-size: 12px;
        }}
        .order-section {{
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 1px solid #ddd;
        }}
        .order-section:last-child {{
            border-bottom: none;
        }}
        .order-header {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .order-header h2 {{
            font-size: 20px;
            color: #2196F3;
            margin-bottom: 10px;
        }}
        .order-header h3 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .order-header p {{
            font-size: 13px;
            margin-bottom: 4px;
        }}
        .line-items {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        .line-items th, .line-items td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .line-items th {{
            background: #f9f9f9;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .line-items td {{
            font-size: 14px;
        }}
        .center {{
            text-align: center;
        }}
        .right {{
            text-align: right;
        }}
        .totals {{
            display: flex;
            justify-content: flex-end;
        }}
        .totals table {{
            width: 250px;
        }}
        .totals td {{
            padding: 8px 12px;
            font-size: 14px;
        }}
        .totals .total-row {{
            border-top: 2px solid #333;
            font-size: 16px;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .invoice-container {{
                box-shadow: none;
                padding: 20px;
            }}
            .order-section {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="invoice-container">
        <div class="company-header">
            <h1>INVOICE</h1>
            <p class="generated-at">Generated on {generated_at}</p>
        </div>
        
        {"".join(order_sections)}
        
    </div>
</body>
</html>"""
    
    return html
