"""Create Reverb template tables

Revision ID: c81cd4df805f
Revises: a1b2c3d4e5f7
Create Date: 2026-01-22 00:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c81cd4df805f'
down_revision: Union[str, Sequence[str], None] = '7645f47cc463'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # reverb_templates
    op.create_table(
        'reverb_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reverb_templates_id'), 'reverb_templates', ['id'], unique=False)

    # reverb_fields
    op.create_table(
        'reverb_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reverb_template_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('selected_value', sa.String(), nullable=True),
        sa.Column('custom_value', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['reverb_template_id'], ['reverb_templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reverb_fields_id'), 'reverb_fields', ['id'], unique=False)
    
    # reverb_field_values
    op.create_table(
        'reverb_field_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reverb_field_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['reverb_field_id'], ['reverb_fields.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reverb_field_values_id'), 'reverb_field_values', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reverb_field_values_id'), table_name='reverb_field_values')
    op.drop_table('reverb_field_values')
    op.drop_index(op.f('ix_reverb_fields_id'), table_name='reverb_fields')
    op.drop_table('reverb_fields')
    op.drop_index(op.f('ix_reverb_templates_id'), table_name='reverb_templates')
    op.drop_table('reverb_templates')
