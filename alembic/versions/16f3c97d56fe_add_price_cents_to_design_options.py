"""add_price_cents_to_design_options

Revision ID: 16f3c97d56fe
Revises: d12f5bda01c3
Create Date: 2026-01-18 01:00:11.022340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16f3c97d56fe'
down_revision: Union[str, Sequence[str], None] = 'd12f5bda01c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('design_options', schema=None) as batch_op:
        batch_op.add_column(sa.Column('price_cents', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('design_options', schema=None) as batch_op:
        batch_op.drop_column('price_cents')
