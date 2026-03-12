"""add_marketplace_listings_table

Revision ID: fd0f5cddeb04
Revises: 3cca839436f5
Create Date: 2025-12-27 19:39:36.364221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd0f5cddeb04'
down_revision: Union[str, Sequence[str], None] = '3cca839436f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create marketplace_listings table."""
    op.create_table(
        'marketplace_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=20), nullable=False),
        sa.Column('external_id', sa.String(length=64), nullable=False),
        sa.Column('listing_url', sa.String(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('parent_external_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id', 'marketplace', 'external_id', name='uq_model_marketplace_external_id')
    )
    
    # Create indexes
    op.create_index('ix_marketplace_listings_model_id', 'marketplace_listings', ['model_id'])
    op.create_index('ix_marketplace_listings_marketplace_external_id', 'marketplace_listings', ['marketplace', 'external_id'])


def downgrade() -> None:
    """Drop marketplace_listings table."""
    op.drop_index('ix_marketplace_listings_marketplace_external_id', table_name='marketplace_listings')
    op.drop_index('ix_marketplace_listings_model_id', table_name='marketplace_listings')
    op.drop_table('marketplace_listings')
