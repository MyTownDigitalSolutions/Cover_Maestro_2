"""add_linked_design_option_to_pricing_options

Revision ID: d12f5bda01c3
Revises: c38e2be31ec8
Create Date: 2026-01-17 21:24:22.904337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd12f5bda01c3'
down_revision: Union[str, Sequence[str], None] = 'c38e2be31ec8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add linked_design_option_id to pricing_options."""
    op.add_column('pricing_options', sa.Column('linked_design_option_id', sa.Integer(), nullable=True))
    # Create index for better query performance
    op.create_index('ix_pricing_options_linked_design_option_id', 'pricing_options', ['linked_design_option_id'])


def downgrade() -> None:
    """Downgrade schema - remove linked_design_option_id from pricing_options."""
    op.drop_index('ix_pricing_options_linked_design_option_id', table_name='pricing_options')
    op.drop_column('pricing_options', 'linked_design_option_id')
