"""add equipment type customization templates join table

Revision ID: abc123def456
Revises: fd0f5cddeb04
Create Date: 2025-12-28 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abc123def456'
down_revision = 'fd0f5cddeb04'
branch_labels = None
depends_on = None


def upgrade():
    # Create equipment_type_customization_templates join table
    op.create_table(
        'equipment_type_customization_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_type_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('slot', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['equipment_type_id'], ['equipment_types.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['amazon_customization_templates.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('equipment_type_id', 'slot', name='uq_equipment_type_customization_templates_slot'),
        sa.UniqueConstraint('equipment_type_id', 'template_id', name='uq_equipment_type_customization_templates_template')
    )
    op.create_index(op.f('ix_equipment_type_customization_templates_id'), 'equipment_type_customization_templates', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_equipment_type_customization_templates_id'), table_name='equipment_type_customization_templates')
    op.drop_table('equipment_type_customization_templates')
