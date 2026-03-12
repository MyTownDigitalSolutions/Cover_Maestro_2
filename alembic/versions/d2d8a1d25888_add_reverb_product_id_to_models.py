"""add_reverb_product_id_to_models

Revision ID: d2d8a1d25888
Revises: f087cd0d191c
Create Date: 2026-01-21 15:40:42.784560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2d8a1d25888'
down_revision: Union[str, Sequence[str], None] = 'f087cd0d191c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add reverb_product_id column to models table."""
    # Add column
    op.add_column('models', sa.Column('reverb_product_id', sa.String(32), nullable=True))
    
    # Add index for efficient lookups
    op.create_index('ix_models_reverb_product_id', 'models', ['reverb_product_id'])


def downgrade() -> None:
    """Remove reverb_product_id column from models table."""
    op.drop_index('ix_models_reverb_product_id', table_name='models')
    op.drop_column('models', 'reverb_product_id')

