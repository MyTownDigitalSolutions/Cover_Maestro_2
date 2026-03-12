"""add_ebay_fields_to_pricing_option

Revision ID: 631317e901ee
Revises: daa0c3b32981
Create Date: 2026-01-17 20:31:10.964930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '631317e901ee'
down_revision: Union[str, Sequence[str], None] = 'daa0c3b32981'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add eBay variation SKU fields to pricing_options table
    op.add_column('pricing_options', sa.Column('sku_abbreviation', sa.String(length=3), nullable=True))
    op.add_column('pricing_options', sa.Column('ebay_variation_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove eBay variation fields from pricing_options table
    op.drop_column('pricing_options', 'ebay_variation_enabled')
    op.drop_column('pricing_options', 'sku_abbreviation')
