"""add_active_to_rate_cards

Revision ID: caaa9a9e8666
Revises: 025362f4dd85
Create Date: 2025-12-23 17:05:43.476278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caaa9a9e8666'
down_revision: Union[str, Sequence[str], None] = '025362f4dd85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('shipping_rate_cards', sa.Column('active', sa.Boolean(), nullable=True, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('shipping_rate_cards', 'active')
