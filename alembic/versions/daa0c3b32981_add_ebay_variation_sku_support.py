"""add_ebay_variation_sku_support

Revision ID: daa0c3b32981
Revises: 6686da0c1ff8
Create Date: 2026-01-17 00:14:25.210310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'daa0c3b32981'
down_revision: Union[str, Sequence[str], None] = '6686da0c1ff8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add abbreviation and toggle fields to design_options
    op.add_column('design_options', sa.Column('sku_abbreviation', sa.String(length=3), nullable=True))
    op.add_column('design_options', sa.Column('ebay_variation_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add abbreviation and toggle fields to materials
    op.add_column('materials', sa.Column('sku_abbreviation', sa.String(length=3), nullable=True))
    op.add_column('materials', sa.Column('ebay_variation_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add color metadata and toggle to material_colour_surcharges
    op.add_column('material_colour_surcharges', sa.Column('color_friendly_name', sa.String(length=64), nullable=True))
    op.add_column('material_colour_surcharges', sa.Column('sku_abbreviation', sa.String(length=3), nullable=True))
    op.add_column('material_colour_surcharges', sa.Column('ebay_variation_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create model_variation_skus table
    op.create_table('model_variation_skus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('variation_sku', sa.String(length=50), nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=True),
        sa.Column('color_id', sa.Integer(), nullable=True),
        sa.Column('design_option_ids', sa.String(), nullable=True),  # JSON array as string
        sa.Column('is_parent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('retail_price_cents', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['color_id'], ['material_colour_surcharges.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id', 'variation_sku', name='uq_model_variation_sku')
    )
    op.create_index(op.f('ix_model_variation_skus_model_id'), 'model_variation_skus', ['model_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop model_variation_skus table
    op.drop_index(op.f('ix_model_variation_skus_model_id'), table_name='model_variation_skus')
    op.drop_table('model_variation_skus')
    
    # Remove columns from material_colour_surcharges
    op.drop_column('material_colour_surcharges', 'ebay_variation_enabled')
    op.drop_column('material_colour_surcharges', 'sku_abbreviation')
    op.drop_column('material_colour_surcharges', 'color_friendly_name')
    
    # Remove columns from materials
    op.drop_column('materials', 'ebay_variation_enabled')
    op.drop_column('materials', 'sku_abbreviation')
    
    # Remove columns from design_options
    op.drop_column('design_options', 'ebay_variation_enabled')
    op.drop_column('design_options', 'sku_abbreviation')
