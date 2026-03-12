"""add_model_pricing_history

Revision ID: 999c3d75543c
Revises: 3e3f85a21bca
Create Date: 2025-12-23 00:30:01.954692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '999c3d75543c'
down_revision: Union[str, Sequence[str], None] = '3e3f85a21bca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'model_pricing_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(), nullable=False),
        sa.Column('variant_key', sa.String(), nullable=False),
        
        sa.Column('raw_cost_cents', sa.Integer(), nullable=False),
        sa.Column('base_cost_cents', sa.Integer(), nullable=False),
        sa.Column('retail_price_cents', sa.Integer(), nullable=False),
        sa.Column('marketplace_fee_cents', sa.Integer(), nullable=False),
        sa.Column('profit_cents', sa.Integer(), nullable=False),
        sa.Column('material_cost_cents', sa.Integer(), nullable=False),
        sa.Column('shipping_cost_cents', sa.Integer(), nullable=False),
        sa.Column('labor_cost_cents', sa.Integer(), nullable=False),
        sa.Column('weight_oz', sa.Float(), nullable=False),
        
        sa.Column('calculated_at', sa.DateTime(), nullable=True),
        sa.Column('pricing_context_hash', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], )
    )
    op.create_index('ix_model_pricing_history_lookup', 'model_pricing_history', ['model_id', 'marketplace', 'variant_key', 'calculated_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_model_pricing_history_lookup', table_name='model_pricing_history')
    op.drop_table('model_pricing_history')
