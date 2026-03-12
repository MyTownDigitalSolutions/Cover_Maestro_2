"""add reverb_template to equipment type

Revision ID: aaa0c3b32982
Revises: 7403e6390ecb
Create Date: 2026-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aaa0c3b32982'
down_revision = 'c81cd4df805f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('equipment_types', sa.Column('reverb_template_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_equipment_types_reverb_templates', 'equipment_types', 'reverb_templates', ['reverb_template_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_equipment_types_reverb_templates', 'equipment_types', type_='foreignkey')
    op.drop_column('equipment_types', 'reverb_template_id')
