"""Add custom_value field to product type fields

Revision ID: 15648ed72212
Revises: bc857d9b9269
Create Date: 2025-12-17 22:46:22.819509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15648ed72212'
down_revision: Union[str, Sequence[str], None] = 'bc857d9b9269'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('product_type_fields', sa.Column('custom_value', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('product_type_fields', 'custom_value')
