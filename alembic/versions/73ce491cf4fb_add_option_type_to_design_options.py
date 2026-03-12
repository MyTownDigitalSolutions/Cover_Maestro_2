"""Add option_type to design_options

Revision ID: 73ce491cf4fb
Revises: 60137b2619d2
Create Date: 2025-12-25 03:12:33.528705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
"""Add option_type to design_options

Revision ID: 73ce491cf4fb
Revises: 60137b2619d2
Create Date: 2025-12-25 03:12:33.528705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73ce491cf4fb'
down_revision: Union[str, Sequence[str], None] = '60137b2619d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add nullable column first
    op.add_column('design_options', sa.Column('option_type', sa.String(), nullable=True))
    
    # Backfill existing rows
    op.execute("UPDATE design_options SET option_type = 'handle_location'")
    
    # Make non-nullable and add index
    # Using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('design_options', schema=None) as batch_op:
        batch_op.alter_column('option_type', nullable=False)
        batch_op.create_index(batch_op.f('ix_design_options_option_type'), ['option_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('design_options', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_design_options_option_type'))
        batch_op.drop_column('option_type')
