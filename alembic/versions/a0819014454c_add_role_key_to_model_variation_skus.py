"""add_role_key_to_model_variation_skus

Revision ID: a0819014454c
Revises: ad404e509fca
Create Date: 2026-01-26 20:32:39.158030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0819014454c'
down_revision: Union[str, Sequence[str], None] = 'ad404e509fca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('model_variation_skus', sa.Column('role_key', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('model_variation_skus', 'role_key')
