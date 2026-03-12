"""add_pricing_metadata_columns

Revision ID: 60137b2619d2
Revises: ade414416fed
Create Date: 2025-12-24 01:28:43.640417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60137b2619d2'
down_revision: Union[str, Sequence[str], None] = 'ade414416fed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # model_pricing_snapshots
    op.add_column('model_pricing_snapshots', sa.Column('surface_area_sq_in', sa.Float(), nullable=True))
    op.add_column('model_pricing_snapshots', sa.Column('material_cost_per_sq_in_cents', sa.Integer(), nullable=True))
    op.add_column('model_pricing_snapshots', sa.Column('labor_minutes', sa.Integer(), nullable=True))
    op.add_column('model_pricing_snapshots', sa.Column('labor_rate_cents_per_hour', sa.Integer(), nullable=True))
    op.add_column('model_pricing_snapshots', sa.Column('marketplace_fee_rate', sa.Float(), nullable=True))

    # model_pricing_history
    op.add_column('model_pricing_history', sa.Column('surface_area_sq_in', sa.Float(), nullable=True))
    op.add_column('model_pricing_history', sa.Column('material_cost_per_sq_in_cents', sa.Integer(), nullable=True))
    op.add_column('model_pricing_history', sa.Column('labor_minutes', sa.Integer(), nullable=True))
    op.add_column('model_pricing_history', sa.Column('labor_rate_cents_per_hour', sa.Integer(), nullable=True))
    op.add_column('model_pricing_history', sa.Column('marketplace_fee_rate', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # model_pricing_history
    op.drop_column('model_pricing_history', 'marketplace_fee_rate')
    op.drop_column('model_pricing_history', 'labor_rate_cents_per_hour')
    op.drop_column('model_pricing_history', 'labor_minutes')
    op.drop_column('model_pricing_history', 'material_cost_per_sq_in_cents')
    op.drop_column('model_pricing_history', 'surface_area_sq_in')

    # model_pricing_snapshots
    op.drop_column('model_pricing_snapshots', 'marketplace_fee_rate')
    op.drop_column('model_pricing_snapshots', 'labor_rate_cents_per_hour')
    op.drop_column('model_pricing_snapshots', 'labor_minutes')
    op.drop_column('model_pricing_snapshots', 'material_cost_per_sq_in_cents')
    op.drop_column('model_pricing_snapshots', 'surface_area_sq_in')
