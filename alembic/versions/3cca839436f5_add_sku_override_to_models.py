"""add_sku_override_to_models

Revision ID: 3cca839436f5
Revises: 12345abcde67
Create Date: 2025-12-27 18:00:30.818532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cca839436f5'
down_revision: Union[str, Sequence[str], None] = '12345abcde67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sku_override column to models table."""
    op.add_column('models', sa.Column('sku_override', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove sku_override column from models table."""
    op.drop_column('models', 'sku_override')
