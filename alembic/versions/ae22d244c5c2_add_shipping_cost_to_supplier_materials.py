"""add_shipping_cost_to_supplier_materials

Revision ID: ae22d244c5c2
Revises: e8d7d5b9f77b
Create Date: 2025-12-22 01:59:44.589488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae22d244c5c2'
down_revision: Union[str, Sequence[str], None] = 'e8d7d5b9f77b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('supplier_materials', sa.Column('shipping_cost', sa.Float(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('supplier_materials', 'shipping_cost')
