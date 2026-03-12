"""create reverb_equipment_type_field_overrides table

Revision ID: 0c5758488c82
Revises: aaa0c3b32982
Create Date: 2026-01-22 01:25:18.112056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c5758488c82'
down_revision: Union[str, Sequence[str], None] = 'aaa0c3b32982'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reverb_equipment_type_field_overrides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_type_id', sa.Integer(), nullable=False),
        sa.Column('reverb_field_id', sa.Integer(), nullable=False),
        sa.Column('default_value', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['equipment_type_id'], ['equipment_types.id'], ),
        sa.ForeignKeyConstraint(['reverb_field_id'], ['reverb_fields.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('equipment_type_id', 'reverb_field_id', name='uq_reverb_et_field_override')
    )
    op.create_index(op.f('ix_reverb_equipment_type_field_overrides_id'), 'reverb_equipment_type_field_overrides', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reverb_equipment_type_field_overrides_id'), table_name='reverb_equipment_type_field_overrides')
    op.drop_table('reverb_equipment_type_field_overrides')
