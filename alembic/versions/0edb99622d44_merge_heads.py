"""Merge heads

Revision ID: 0edb99622d44
Revises: abc123def456, add_model_notes
Create Date: 2026-01-01 23:06:41.300438

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0edb99622d44'
down_revision: Union[str, Sequence[str], None] = ('abc123def456', 'add_model_notes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
