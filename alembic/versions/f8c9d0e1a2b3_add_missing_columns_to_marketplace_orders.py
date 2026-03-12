"""add_missing_columns_to_marketplace_orders

Revision ID: f8c9d0e1a2b3
Revises: 0b531c4badf9
Create Date: 2026-01-20 16:45:00.000000

This migration adds columns to the existing marketplace_orders table
that are expected by the ORM model but were not present in the original
table schema created by Base.metadata.create_all().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'f8c9d0e1a2b3'
down_revision: Union[str, Sequence[str], None] = '0b531c4badf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_existing_columns(table_name: str) -> set:
    """Get set of column names that exist in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = inspector.get_columns(table_name)
    return {col['name'] for col in columns}


def upgrade() -> None:
    """Add missing columns to marketplace_orders table."""
    
    # Get existing columns
    existing_cols = get_existing_columns('marketplace_orders')
    
    # Define columns to add (column_name, column_definition)
    columns_to_add = [
        ('import_run_id', sa.Column('import_run_id', sa.Integer(), nullable=True)),
        ('external_order_id', sa.Column('external_order_id', sa.String(128), nullable=True)),
        ('external_order_number', sa.Column('external_order_number', sa.String(128), nullable=True)),
        ('external_store_id', sa.Column('external_store_id', sa.String(128), nullable=True)),
        ('created_at_external', sa.Column('created_at_external', sa.DateTime(), nullable=True)),
        ('updated_at_external', sa.Column('updated_at_external', sa.DateTime(), nullable=True)),
        ('status_raw', sa.Column('status_raw', sa.String(64), nullable=True)),
        ('status_normalized', sa.Column('status_normalized', sa.String(20), nullable=False, server_default='unknown')),
        ('currency_code', sa.Column('currency_code', sa.String(3), nullable=False, server_default='USD')),
        ('items_subtotal_cents', sa.Column('items_subtotal_cents', sa.Integer(), nullable=True)),
        ('shipping_cents', sa.Column('shipping_cents', sa.Integer(), nullable=True)),
        ('discount_cents', sa.Column('discount_cents', sa.Integer(), nullable=True)),
        ('fees_cents', sa.Column('fees_cents', sa.Integer(), nullable=True)),
        ('refunded_cents', sa.Column('refunded_cents', sa.Integer(), nullable=True)),
        ('order_total_cents', sa.Column('order_total_cents', sa.Integer(), nullable=True)),
        ('fulfillment_channel', sa.Column('fulfillment_channel', sa.String(64), nullable=True)),
        ('shipping_service_level', sa.Column('shipping_service_level', sa.String(64), nullable=True)),
        ('ship_by_date', sa.Column('ship_by_date', sa.DateTime(), nullable=True)),
        ('deliver_by_date', sa.Column('deliver_by_date', sa.DateTime(), nullable=True)),
        ('import_error', sa.Column('import_error', sa.Text(), nullable=True)),
    ]
    
    # Add each missing column
    for col_name, col_def in columns_to_add:
        if col_name not in existing_cols:
            print(f"[MIGRATION] Adding column: marketplace_orders.{col_name}")
            op.add_column('marketplace_orders', col_def)
        else:
            print(f"[MIGRATION] Column already exists: marketplace_orders.{col_name}")
    
    # Also check marketplace_import_runs table exists and has required columns
    try:
        import_runs_cols = get_existing_columns('marketplace_import_runs')
        # Table exists, check for any missing columns
        print(f"[MIGRATION] marketplace_import_runs has {len(import_runs_cols)} columns")
    except Exception:
        # Table doesn't exist, create it
        print("[MIGRATION] Creating marketplace_import_runs table")
        op.create_table(
            'marketplace_import_runs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('marketplace', sa.String(length=20), nullable=False),
            sa.Column('external_store_id', sa.String(length=128), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('orders_fetched', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('orders_upserted', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('errors_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_summary', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Check/create child tables
    for table_name, table_def in [
        ('marketplace_order_addresses', [
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('address_type', sa.String(length=20), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=True),
            sa.Column('phone', sa.String(length=50), nullable=True),
            sa.Column('company', sa.String(length=255), nullable=True),
            sa.Column('line1', sa.String(length=255), nullable=True),
            sa.Column('line2', sa.String(length=255), nullable=True),
            sa.Column('city', sa.String(length=100), nullable=True),
            sa.Column('state_or_region', sa.String(length=100), nullable=True),
            sa.Column('postal_code', sa.String(length=20), nullable=True),
            sa.Column('country_code', sa.String(length=10), nullable=True),
            sa.Column('raw_payload', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['order_id'], ['marketplace_orders.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        ]),
        ('marketplace_order_lines', [
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('external_line_item_id', sa.String(length=128), nullable=True),
            sa.Column('marketplace_item_id', sa.String(length=128), nullable=True),
            sa.Column('sku', sa.String(length=64), nullable=True),
            sa.Column('asin', sa.String(length=20), nullable=True),
            sa.Column('listing_id', sa.String(length=64), nullable=True),
            sa.Column('product_id', sa.String(length=64), nullable=True),
            sa.Column('title', sa.String(length=500), nullable=True),
            sa.Column('variant', sa.String(length=255), nullable=True),
            sa.Column('quantity', sa.Integer(), nullable=False),
            sa.Column('currency_code', sa.String(length=3), nullable=True),
            sa.Column('unit_price_cents', sa.Integer(), nullable=True),
            sa.Column('line_subtotal_cents', sa.Integer(), nullable=True),
            sa.Column('tax_cents', sa.Integer(), nullable=True),
            sa.Column('discount_cents', sa.Integer(), nullable=True),
            sa.Column('line_total_cents', sa.Integer(), nullable=True),
            sa.Column('fulfillment_status_raw', sa.String(length=64), nullable=True),
            sa.Column('fulfillment_status_normalized', sa.String(length=20), nullable=True),
            sa.Column('model_id', sa.Integer(), nullable=True),
            sa.Column('customization_data', sa.JSON(), nullable=True),
            sa.Column('raw_marketplace_data', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['order_id'], ['marketplace_orders.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        ]),
        ('marketplace_order_shipments', [
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False),
            sa.Column('external_shipment_id', sa.String(length=128), nullable=True),
            sa.Column('carrier', sa.String(length=64), nullable=True),
            sa.Column('service', sa.String(length=64), nullable=True),
            sa.Column('tracking_number', sa.String(length=128), nullable=True),
            sa.Column('shipped_at', sa.DateTime(), nullable=True),
            sa.Column('delivered_at', sa.DateTime(), nullable=True),
            sa.Column('raw_marketplace_data', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['order_id'], ['marketplace_orders.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        ]),
    ]:
        try:
            existing = get_existing_columns(table_name)
            print(f"[MIGRATION] {table_name} already exists with {len(existing)} columns")
        except Exception:
            print(f"[MIGRATION] Creating table: {table_name}")
            op.create_table(table_name, *table_def)


def downgrade() -> None:
    """Remove the columns added in upgrade."""
    
    columns_to_remove = [
        'import_run_id', 'external_order_id', 'external_order_number', 'external_store_id',
        'created_at_external', 'updated_at_external', 'status_raw', 'status_normalized',
        'currency_code', 'items_subtotal_cents', 'shipping_cents', 'discount_cents',
        'fees_cents', 'refunded_cents', 'order_total_cents', 'fulfillment_channel',
        'shipping_service_level', 'ship_by_date', 'deliver_by_date', 'import_error',
    ]
    
    for col_name in columns_to_remove:
        try:
            op.drop_column('marketplace_orders', col_name)
            print(f"[MIGRATION] Dropped column: marketplace_orders.{col_name}")
        except Exception as e:
            print(f"[MIGRATION] Could not drop column {col_name}: {e}")
    
    # Drop child tables
    for table_name in ['marketplace_order_shipments', 'marketplace_order_lines', 'marketplace_order_addresses']:
        try:
            op.drop_table(table_name)
            print(f"[MIGRATION] Dropped table: {table_name}")
        except Exception as e:
            print(f"[MIGRATION] Could not drop table {table_name}: {e}")
    
    # Drop import_runs table
    try:
        op.drop_table('marketplace_import_runs')
        print("[MIGRATION] Dropped table: marketplace_import_runs")
    except Exception as e:
        print(f"[MIGRATION] Could not drop table marketplace_import_runs: {e}")
