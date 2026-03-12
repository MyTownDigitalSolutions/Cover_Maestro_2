"""add_model_export_exclusion_flags

Revision ID: 6686da0c1ff8
Revises: d3f9c73a71b4
Create Date: 2026-01-03 18:57:59.161045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6686da0c1ff8'
down_revision: Union[str, Sequence[str], None] = 'd3f9c73a71b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add exclude_from_amazon_export column with server default
    op.add_column('models', sa.Column('exclude_from_amazon_export', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    
    # Add exclude_from_ebay_export column with server default
    op.add_column('models', sa.Column('exclude_from_ebay_export', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    
    # Add exclude_from_reverb_export column with server default
    op.add_column('models', sa.Column('exclude_from_reverb_export', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    
    # Add exclude_from_etsy_export column with server default
    op.add_column('models', sa.Column('exclude_from_etsy_export', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    
    # Remove server defaults to match ORM (optional but recommended)
    op.alter_column('models', 'exclude_from_amazon_export', server_default=None)
    op.alter_column('models', 'exclude_from_ebay_export', server_default=None)
    op.alter_column('models', 'exclude_from_reverb_export', server_default=None)
    op.alter_column('models', 'exclude_from_etsy_export', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop columns in reverse order
    op.drop_column('models', 'exclude_from_etsy_export')
    op.drop_column('models', 'exclude_from_reverb_export')
    op.drop_column('models', 'exclude_from_ebay_export')
    op.drop_column('models', 'exclude_from_amazon_export')
