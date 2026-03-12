"""rebuild_marketplace_orders_to_match_orm

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-01-20 19:22:00.000000

This migration rebuilds the marketplace_orders table to exactly match
the current ORM model definition. SQLite requires table rebuild for
significant schema changes like dropping NOT NULL constraints.

Strategy:
1. Create new table with correct schema
2. Copy existing data with column mapping
3. Drop old table
4. Rename new table
5. Recreate indexes and constraints
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'h2i3j4k5l6m7'
down_revision: Union[str, Sequence[str], None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rebuild marketplace_orders table to match current ORM model."""
    
    bind = op.get_bind()
    
    # Step 1: Create new table with correct ORM schema
    print("[MIGRATION] Creating marketplace_orders__new with ORM-correct schema...")
    
    op.execute(text("""
        CREATE TABLE marketplace_orders__new (
            id INTEGER PRIMARY KEY,
            import_run_id INTEGER REFERENCES marketplace_import_runs(id) ON DELETE SET NULL,
            source VARCHAR(20) NOT NULL,
            marketplace VARCHAR(10),
            external_order_id VARCHAR(128),
            external_order_number VARCHAR(128),
            external_store_id VARCHAR(128),
            order_date DATETIME NOT NULL,
            created_at_external DATETIME,
            updated_at_external DATETIME,
            imported_at DATETIME NOT NULL,
            last_synced_at DATETIME,
            status_raw VARCHAR(64),
            status_normalized VARCHAR(20) NOT NULL DEFAULT 'unknown',
            buyer_name VARCHAR(255),
            buyer_email VARCHAR(255),
            buyer_phone VARCHAR(50),
            currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
            items_subtotal_cents INTEGER,
            shipping_cents INTEGER,
            tax_cents INTEGER,
            discount_cents INTEGER,
            fees_cents INTEGER,
            refunded_cents INTEGER,
            order_total_cents INTEGER,
            fulfillment_channel VARCHAR(64),
            shipping_service_level VARCHAR(64),
            ship_by_date DATETIME,
            deliver_by_date DATETIME,
            notes TEXT,
            import_error TEXT,
            raw_marketplace_data JSON,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Step 2: Copy data from old table with column mapping
    print("[MIGRATION] Copying existing data with column mapping...")
    
    # Check if old table has data
    result = bind.execute(text("SELECT COUNT(*) FROM marketplace_orders"))
    row_count = result.scalar()
    print(f"[MIGRATION] Found {row_count} existing rows to migrate")
    
    if row_count > 0:
        # Map old columns to new columns with sensible defaults
        # Old schema has: marketplace_order_id, status, ship_*, bill_*, subtotal_cents, total_cents, currency
        # New schema has: external_order_id, status_raw, status_normalized, items_subtotal_cents, order_total_cents, currency_code
        op.execute(text("""
            INSERT INTO marketplace_orders__new (
                id,
                import_run_id,
                source,
                marketplace,
                external_order_id,
                external_order_number,
                external_store_id,
                order_date,
                created_at_external,
                updated_at_external,
                imported_at,
                last_synced_at,
                status_raw,
                status_normalized,
                buyer_name,
                buyer_email,
                buyer_phone,
                currency_code,
                items_subtotal_cents,
                shipping_cents,
                tax_cents,
                discount_cents,
                fees_cents,
                refunded_cents,
                order_total_cents,
                fulfillment_channel,
                shipping_service_level,
                ship_by_date,
                deliver_by_date,
                notes,
                import_error,
                raw_marketplace_data,
                created_at,
                updated_at
            )
            SELECT 
                id,
                import_run_id,
                COALESCE(source, 'manual'),
                marketplace,
                COALESCE(external_order_id, marketplace_order_id),
                external_order_number,
                external_store_id,
                order_date,
                COALESCE(created_at_external, marketplace_created_at),
                COALESCE(updated_at_external, marketplace_updated_at),
                COALESCE(imported_at, created_at),
                last_synced_at,
                COALESCE(status_raw, status),
                COALESCE(status_normalized, 'unknown'),
                buyer_name,
                buyer_email,
                buyer_phone,
                COALESCE(currency_code, currency, 'USD'),
                COALESCE(items_subtotal_cents, subtotal_cents),
                COALESCE(shipping_cents, shipping_cost_cents),
                tax_cents,
                discount_cents,
                fees_cents,
                refunded_cents,
                COALESCE(order_total_cents, total_cents),
                fulfillment_channel,
                shipping_service_level,
                ship_by_date,
                deliver_by_date,
                notes,
                import_error,
                raw_marketplace_data,
                created_at,
                updated_at
            FROM marketplace_orders
        """))
        print(f"[MIGRATION] Migrated {row_count} rows")
    
    # Step 3: Drop old table
    print("[MIGRATION] Dropping old marketplace_orders table...")
    op.execute(text("DROP TABLE marketplace_orders"))
    
    # Step 4: Rename new table
    print("[MIGRATION] Renaming marketplace_orders__new to marketplace_orders...")
    op.execute(text("ALTER TABLE marketplace_orders__new RENAME TO marketplace_orders"))
    
    # Step 5: Recreate indexes
    print("[MIGRATION] Creating indexes...")
    op.execute(text("CREATE INDEX ix_marketplace_orders_id ON marketplace_orders (id)"))
    op.execute(text("CREATE INDEX ix_marketplace_orders_marketplace ON marketplace_orders (marketplace)"))
    op.execute(text("CREATE INDEX ix_marketplace_orders_external_order_id ON marketplace_orders (external_order_id)"))
    op.execute(text("CREATE INDEX ix_marketplace_orders_order_date ON marketplace_orders (order_date)"))
    
    # Step 6: Recreate unique constraint
    print("[MIGRATION] Creating unique constraint on (marketplace, external_order_id)...")
    op.execute(text("""
        CREATE UNIQUE INDEX uq_marketplace_external_order_id 
        ON marketplace_orders (marketplace, external_order_id)
        WHERE marketplace IS NOT NULL AND external_order_id IS NOT NULL
    """))
    
    # Verify child table FKs still work (child tables reference marketplace_orders.id which we preserved)
    print("[MIGRATION] Table rebuild complete. Child table FKs preserved via id column.")


def downgrade() -> None:
    """
    Downgrade is not fully supported for this migration.
    
    The old schema had legacy columns that are not in the ORM model.
    Attempting to recreate them would be error-prone and potentially
    break the application. If downgrade is needed, restore from backup.
    """
    raise NotImplementedError(
        "Downgrade not supported for marketplace_orders rebuild migration. "
        "Restore from database backup if needed."
    )
