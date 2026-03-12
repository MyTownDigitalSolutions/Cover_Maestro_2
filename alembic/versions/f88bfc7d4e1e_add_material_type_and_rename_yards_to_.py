"""add material type and rename yards to quantity

Revision ID: f88bfc7d4e1e
Revises: 0e27b963e908
Create Date: 2025-12-22 02:43:13.786736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f88bfc7d4e1e'
down_revision: Union[str, Sequence[str], None] = '0e27b963e908'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add material_type with server default for SQLite compatibility
    op.add_column('materials', sa.Column('material_type', sa.String(20), server_default='fabric', nullable=False))
    op.add_column('materials', sa.Column('unit_of_measure', sa.String(20), server_default='yard', nullable=True))
    op.add_column('materials', sa.Column('package_quantity', sa.Float(), nullable=True))
    
    # Make linear_yard_width and weight_per_linear_yard nullable for non-fabric materials
    # SQLite doesn't support ALTER COLUMN well, so we skip these for now (they're effectively already nullable in SQLite)
    
    # Add quantity_purchased with default, copy from yards_purchased, then drop yards_purchased
    op.add_column('supplier_materials', sa.Column('quantity_purchased', sa.Float(), server_default='1.0', nullable=False))
    
    # Copy data from yards_purchased to quantity_purchased
    op.execute('UPDATE supplier_materials SET quantity_purchased = yards_purchased')
    
    # Drop old column
    op.drop_column('supplier_materials', 'yards_purchased')


def downgrade() -> None:
    """Downgrade schema."""
    # Add yards_purchased back
    op.add_column('supplier_materials', sa.Column('yards_purchased', sa.Float(), server_default=sa.text("'1.0'"), nullable=False))
    
    # Copy data back
    op.execute('UPDATE supplier_materials SET yards_purchased = quantity_purchased')
    
    # Drop quantity_purchased
    op.drop_column('supplier_materials', 'quantity_purchased')
    
    # Drop new material columns
    op.drop_column('materials', 'package_quantity')
    op.drop_column('materials', 'unit_of_measure')
    op.drop_column('materials', 'material_type')
