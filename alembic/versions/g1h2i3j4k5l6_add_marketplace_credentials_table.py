"""add_marketplace_credentials_table

Revision ID: g1h2i3j4k5l6
Revises: f8c9d0e1a2b3
Create Date: 2026-01-20 17:15:00.000000

This migration creates the marketplace_credentials table for storing
API credentials for various marketplaces (Reverb, Amazon, eBay, Etsy).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, Sequence[str], None] = 'f8c9d0e1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create marketplace_credentials table."""
    op.create_table(
        'marketplace_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('secrets_blob', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('marketplace', name='uq_marketplace_credentials_marketplace')
    )
    op.create_index('ix_marketplace_credentials_marketplace', 'marketplace_credentials', ['marketplace'])
    print("[MIGRATION] Created table: marketplace_credentials")


def downgrade() -> None:
    """Drop marketplace_credentials table."""
    op.drop_index('ix_marketplace_credentials_marketplace', 'marketplace_credentials')
    op.drop_table('marketplace_credentials')
    print("[MIGRATION] Dropped table: marketplace_credentials")
