"""add_missing_columns_to_marketplace_order_lines

Revision ID: f087cd0d191c
Revises: 16b73c2009b1
Create Date: 2026-01-20 22:48:14.103569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f087cd0d191c'
down_revision: Union[str, Sequence[str], None] = '16b73c2009b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('marketplace_order_lines')}

    if 'asin' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('asin', sa.String(length=64), nullable=True))
    if 'listing_id' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('listing_id', sa.String(length=128), nullable=True))
    if 'product_id' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('product_id', sa.String(length=128), nullable=True))
    if 'variant' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('variant', sa.String(length=255), nullable=True))
    if 'currency_code' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('currency_code', sa.String(length=3), nullable=True))
    if 'line_subtotal_cents' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('line_subtotal_cents', sa.Integer(), nullable=True))
    if 'tax_cents' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('tax_cents', sa.Integer(), nullable=True))
    if 'discount_cents' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('discount_cents', sa.Integer(), nullable=True))
    if 'line_total_cents' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('line_total_cents', sa.Integer(), nullable=True))
    if 'fulfillment_status_raw' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('fulfillment_status_raw', sa.String(length=64), nullable=True))
    if 'fulfillment_status_normalized' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('fulfillment_status_normalized', sa.String(length=20), nullable=True))
    if 'raw_marketplace_data' not in existing_columns:
        op.add_column('marketplace_order_lines', sa.Column('raw_marketplace_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    pass
