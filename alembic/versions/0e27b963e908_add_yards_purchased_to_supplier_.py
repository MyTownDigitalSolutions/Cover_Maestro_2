"""add yards_purchased to supplier_materials

Revision ID: 0e27b963e908
Revises: ae22d244c5c2
Create Date: 2025-12-22 02:14:49.902757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e27b963e908'
down_revision: Union[str, Sequence[str], None] = 'ae22d244c5c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('supplier_materials', sa.Column('yards_purchased', sa.Float(), nullable=True, server_default='1.0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('supplier_materials', 'yards_purchased')
