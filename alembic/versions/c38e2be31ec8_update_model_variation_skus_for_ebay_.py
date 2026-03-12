"""update_model_variation_skus_for_ebay_variations

Revision ID: c38e2be31ec8
Revises: 631317e901ee
Create Date: 2026-01-17 20:55:02.520739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c38e2be31ec8'
down_revision: Union[str, Sequence[str], None] = '631317e901ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - backup existing table and create fresh model_variation_skus."""
    conn = op.get_bind()
    insp = inspect(conn)
    
    # Check if table exists
    has_old = insp.has_table('model_variation_skus')
    
    if has_old:
        # Backup existing table - rename it
        backup_name = 'model_variation_skus__backup_c38e2be31ec8'
        
        # Check if backup already exists (migration re-run scenario)
        if insp.has_table(backup_name):
            backup_name = 'model_variation_skus__backup_c38e2be31ec8_2'
        
        # Drop any existing indexes before renaming table (SQLite limitation)
        try:
            op.drop_index('ix_model_variation_skus_id', table_name='model_variation_skus')
        except:
            pass
        try:
            op.drop_index('ix_model_variation_skus_model_id', table_name='model_variation_skus')
        except:
            pass
        try:
            op.drop_index('ix_model_variation_skus_sku', table_name='model_variation_skus')
        except:
            pass
        
        op.rename_table('model_variation_skus', backup_name)
    
    # Create fresh table with final schema
    op.create_table(
        'model_variation_skus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('material_colour_surcharge_id', sa.Integer(), nullable=True),
        sa.Column('design_option_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('pricing_option_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_parent', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('retail_price_cents', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_model_variation_skus_id', 'model_variation_skus', ['id'], unique=False)
    op.create_index('ix_model_variation_skus_model_id', 'model_variation_skus', ['model_id'], unique=False)
    op.create_index('ix_model_variation_skus_sku', 'model_variation_skus', ['sku'], unique=True)


def downgrade() -> None:
    """Downgrade schema - restore backup table."""
    conn = op.get_bind()
    insp = inspect(conn)
    
    # Drop the new table
    op.drop_table('model_variation_skus')
    
    # Restore from backup if it exists
    backup_name = 'model_variation_skus__backup_c38e2be31ec8'
    backup_name_2 = 'model_variation_skus__backup_c38e2be31ec8_2'
    
    if insp.has_table(backup_name):
        op.rename_table(backup_name, 'model_variation_skus')
    elif insp.has_table(backup_name_2):
        op.rename_table(backup_name_2, 'model_variation_skus')
