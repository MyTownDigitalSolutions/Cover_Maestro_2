"""add_active_to_shipping_rate_tiers

Revision ID: 4ffe8a80d14e
Revises: caaa9a9e8666
Create Date: 2025-12-23 17:19:21.015156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ffe8a80d14e'
down_revision: Union[str, Sequence[str], None] = 'caaa9a9e8666'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('shipping_rate_tiers', sa.Column('active', sa.Boolean(), server_default='1', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('shipping_rate_tiers', 'active')
