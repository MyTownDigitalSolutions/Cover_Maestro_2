"""merge_marketplace_orders_migration

Revision ID: 0b531c4badf9
Revises: 16f3c97d56fe, a1b2c3d4e5f6
Create Date: 2026-01-20 15:40:13.546379

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b531c4badf9'
down_revision: Union[str, Sequence[str], None] = ('16f3c97d56fe', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
