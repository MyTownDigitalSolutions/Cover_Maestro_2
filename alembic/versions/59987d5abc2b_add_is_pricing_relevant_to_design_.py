"""Add is_pricing_relevant to design_options

Revision ID: 59987d5abc2b
Revises: 73ce491cf4fb
Create Date: 2025-12-25 04:04:06.144098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59987d5abc2b'
down_revision: Union[str, Sequence[str], None] = '73ce491cf4fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('design_options', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_pricing_relevant', sa.Boolean(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('design_options', schema=None) as batch_op:
        batch_op.drop_column('is_pricing_relevant')
