"""Add external_line_item_id to marketplace_order_lines

Revision ID: 16b73c2009b1
Revises: h2i3j4k5l6m7
Create Date: 2026-01-20 22:23:44.347577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16b73c2009b1'
down_revision: Union[str, Sequence[str], None] = 'h2i3j4k5l6m7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add external_line_item_id column
    op.add_column('marketplace_order_lines', sa.Column('external_line_item_id', sa.String(length=128), nullable=True))
    
    # Create unique index
    op.create_index(
        'uq_marketplace_order_lines_order_external_line_item_id',
        'marketplace_order_lines',
        ['order_id', 'external_line_item_id'],
        unique=True
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('uq_marketplace_order_lines_order_external_line_item_id', table_name='marketplace_order_lines')
    
    # SQLite workaround: we leave the column as dropping it requires table recreation
    # op.drop_column('marketplace_order_lines', 'external_line_item_id')
