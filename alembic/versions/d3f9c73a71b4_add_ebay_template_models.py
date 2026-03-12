"""Add eBay template models

Revision ID: d3f9c73a71b4
Revises: 0edb99622d44
Create Date: 2026-01-01 23:07:08.456461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f9c73a71b4'
down_revision: Union[str, Sequence[str], None] = '0edb99622d44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ebay_templates
    op.create_table(
        'ebay_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ebay_templates_id'), 'ebay_templates', ['id'], unique=False)

    # ebay_fields
    op.create_table(
        'ebay_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ebay_template_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('selected_value', sa.String(), nullable=True),
        sa.Column('custom_value', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['ebay_template_id'], ['ebay_templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ebay_fields_id'), 'ebay_fields', ['id'], unique=False)
    
    # ebay_field_values
    op.create_table(
        'ebay_field_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ebay_field_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['ebay_field_id'], ['ebay_fields.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ebay_field_values_id'), 'ebay_field_values', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ebay_field_values_id'), table_name='ebay_field_values')
    op.drop_table('ebay_field_values')
    op.drop_index(op.f('ix_ebay_fields_id'), table_name='ebay_fields')
    op.drop_table('ebay_fields')
    op.drop_index(op.f('ix_ebay_templates_id'), table_name='ebay_templates')
    op.drop_table('ebay_templates')
