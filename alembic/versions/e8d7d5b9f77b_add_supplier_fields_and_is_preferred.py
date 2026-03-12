"""add_supplier_fields_and_is_preferred

Revision ID: e8d7d5b9f77b
Revises: 039251c0f3ee
Create Date: 2025-12-22 00:59:21.920152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8d7d5b9f77b'
down_revision: Union[str, Sequence[str], None] = '039251c0f3ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('supplier_materials', sa.Column('is_preferred', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('suppliers', sa.Column('contact_name', sa.String(), nullable=True))
    op.add_column('suppliers', sa.Column('address', sa.String(), nullable=True))
    op.add_column('suppliers', sa.Column('phone', sa.String(), nullable=True))
    op.add_column('suppliers', sa.Column('email', sa.String(), nullable=True))
    op.add_column('suppliers', sa.Column('website', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('suppliers', 'website')
    op.drop_column('suppliers', 'email')
    op.drop_column('suppliers', 'phone')
    op.drop_column('suppliers', 'address')
    op.drop_column('suppliers', 'contact_name')
    op.drop_column('supplier_materials', 'is_preferred')
