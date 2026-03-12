"""add parent_sku to models

Revision ID: 47774ccbacb8
Revises: 15648ed72212
Create Date: 2025-12-17 23:50:43.790894

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47774ccbacb8'
down_revision: Union[str, Sequence[str], None] = '15648ed72212'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('models', sa.Column('parent_sku', sa.String(length=40), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('models', 'parent_sku')
