"""create_marketplace_order_import_tables

Revision ID: a1b2c3d4e5f6
Revises: c38e2be31ec8
Create Date: 2026-01-20 15:17:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c38e2be31ec8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create marketplace order import tables."""
    
    # 1) marketplace_import_runs (create first - parent table)
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
    op.create_index('ix_marketplace_import_runs_marketplace', 'marketplace_import_runs', ['marketplace'])
    op.create_index('ix_marketplace_import_runs_started_at', 'marketplace_import_runs', ['started_at'])
    
    # 2) marketplace_orders
    op.create_table(
        'marketplace_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('import_run_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('marketplace', sa.String(length=20), nullable=True),
        sa.Column('external_order_id', sa.String(length=128), nullable=True),
        sa.Column('external_order_number', sa.String(length=128), nullable=True),
        sa.Column('external_store_id', sa.String(length=128), nullable=True),
        # Dates
        sa.Column('order_date', sa.DateTime(), nullable=False),
        sa.Column('created_at_external', sa.DateTime(), nullable=True),
        sa.Column('updated_at_external', sa.DateTime(), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        # Status
        sa.Column('status_raw', sa.String(length=64), nullable=True),
        sa.Column('status_normalized', sa.String(length=20), nullable=False, server_default='unknown'),
        # Buyer
        sa.Column('buyer_name', sa.String(length=255), nullable=True),
        sa.Column('buyer_email', sa.String(length=255), nullable=True),
        sa.Column('buyer_phone', sa.String(length=50), nullable=True),
        # Money (cents)
        sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('items_subtotal_cents', sa.Integer(), nullable=True),
        sa.Column('shipping_cents', sa.Integer(), nullable=True),
        sa.Column('tax_cents', sa.Integer(), nullable=True),
        sa.Column('discount_cents', sa.Integer(), nullable=True),
        sa.Column('fees_cents', sa.Integer(), nullable=True),
        sa.Column('refunded_cents', sa.Integer(), nullable=True),
        sa.Column('order_total_cents', sa.Integer(), nullable=True),
        # Fulfillment
        sa.Column('fulfillment_channel', sa.String(length=64), nullable=True),
        sa.Column('shipping_service_level', sa.String(length=64), nullable=True),
        sa.Column('ship_by_date', sa.DateTime(), nullable=True),
        sa.Column('deliver_by_date', sa.DateTime(), nullable=True),
        # Ops
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('import_error', sa.Text(), nullable=True),
        sa.Column('raw_marketplace_data', sa.JSON(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        # Constraints
        sa.ForeignKeyConstraint(['import_run_id'], ['marketplace_import_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('marketplace', 'external_order_id', name='uq_marketplace_external_order_id')
    )
    op.create_index('ix_marketplace_orders_order_date', 'marketplace_orders', ['order_date'])
    op.create_index('ix_marketplace_orders_status_normalized', 'marketplace_orders', ['status_normalized'])
    op.create_index('ix_marketplace_orders_buyer_email', 'marketplace_orders', ['buyer_email'])
    op.create_index('ix_marketplace_orders_marketplace_external_order_id', 'marketplace_orders', ['marketplace', 'external_order_id'])
    
    # 3) marketplace_order_addresses
    op.create_table(
        'marketplace_order_addresses',
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
        sa.UniqueConstraint('order_id', 'address_type', name='uq_order_address_type')
    )
    op.create_index('ix_marketplace_order_addresses_order_id', 'marketplace_order_addresses', ['order_id'])
    
    # 4) marketplace_order_lines
    op.create_table(
        'marketplace_order_lines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('external_line_item_id', sa.String(length=128), nullable=True),
        # Item refs
        sa.Column('marketplace_item_id', sa.String(length=128), nullable=True),
        sa.Column('sku', sa.String(length=64), nullable=True),
        sa.Column('asin', sa.String(length=20), nullable=True),
        sa.Column('listing_id', sa.String(length=64), nullable=True),
        sa.Column('product_id', sa.String(length=64), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('variant', sa.String(length=255), nullable=True),
        # Qty & pricing
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=True),
        sa.Column('unit_price_cents', sa.Integer(), nullable=True),
        sa.Column('line_subtotal_cents', sa.Integer(), nullable=True),
        sa.Column('tax_cents', sa.Integer(), nullable=True),
        sa.Column('discount_cents', sa.Integer(), nullable=True),
        sa.Column('line_total_cents', sa.Integer(), nullable=True),
        # Fulfillment
        sa.Column('fulfillment_status_raw', sa.String(length=64), nullable=True),
        sa.Column('fulfillment_status_normalized', sa.String(length=20), nullable=True),
        # Internal link
        sa.Column('model_id', sa.Integer(), nullable=True),
        # Customization
        sa.Column('customization_data', sa.JSON(), nullable=True),
        # Raw
        sa.Column('raw_marketplace_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['marketplace_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', 'external_line_item_id', name='uq_order_line_item_id')
    )
    op.create_index('ix_marketplace_order_lines_order_id', 'marketplace_order_lines', ['order_id'])
    op.create_index('ix_marketplace_order_lines_sku', 'marketplace_order_lines', ['sku'])
    op.create_index('ix_marketplace_order_lines_model_id', 'marketplace_order_lines', ['model_id'])
    
    # 5) marketplace_order_shipments
    op.create_table(
        'marketplace_order_shipments',
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
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_marketplace_order_shipments_order_id', 'marketplace_order_shipments', ['order_id'])
    op.create_index('ix_marketplace_order_shipments_tracking_number', 'marketplace_order_shipments', ['tracking_number'])


def downgrade() -> None:
    """Drop marketplace order import tables in reverse order."""
    # Drop indexes and tables in reverse FK order
    
    # 5) marketplace_order_shipments
    op.drop_index('ix_marketplace_order_shipments_tracking_number', table_name='marketplace_order_shipments')
    op.drop_index('ix_marketplace_order_shipments_order_id', table_name='marketplace_order_shipments')
    op.drop_table('marketplace_order_shipments')
    
    # 4) marketplace_order_lines
    op.drop_index('ix_marketplace_order_lines_model_id', table_name='marketplace_order_lines')
    op.drop_index('ix_marketplace_order_lines_sku', table_name='marketplace_order_lines')
    op.drop_index('ix_marketplace_order_lines_order_id', table_name='marketplace_order_lines')
    op.drop_table('marketplace_order_lines')
    
    # 3) marketplace_order_addresses
    op.drop_index('ix_marketplace_order_addresses_order_id', table_name='marketplace_order_addresses')
    op.drop_table('marketplace_order_addresses')
    
    # 2) marketplace_orders
    op.drop_index('ix_marketplace_orders_marketplace_external_order_id', table_name='marketplace_orders')
    op.drop_index('ix_marketplace_orders_buyer_email', table_name='marketplace_orders')
    op.drop_index('ix_marketplace_orders_status_normalized', table_name='marketplace_orders')
    op.drop_index('ix_marketplace_orders_order_date', table_name='marketplace_orders')
    op.drop_table('marketplace_orders')
    
    # 1) marketplace_import_runs
    op.drop_index('ix_marketplace_import_runs_started_at', table_name='marketplace_import_runs')
    op.drop_index('ix_marketplace_import_runs_marketplace', table_name='marketplace_import_runs')
    op.drop_table('marketplace_import_runs')
