"""add selected_value to product_type_fields

Revision ID: bc857d9b9269
Revises: 7e65815d3539
Create Date: 2025-12-17 22:12:12.393542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc857d9b9269'
down_revision: Union[str, Sequence[str], None] = '7e65815d3539'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('product_type_fields', sa.Column('selected_value', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('product_type_fields', 'selected_value')
