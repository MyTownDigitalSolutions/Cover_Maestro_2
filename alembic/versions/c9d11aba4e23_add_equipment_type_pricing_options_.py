"""add equipment type pricing options junction table

Revision ID: c9d11aba4e23
Revises: 47774ccbacb8
Create Date: 2025-12-19 03:20:09.419587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d11aba4e23'
down_revision: Union[str, Sequence[str], None] = '47774ccbacb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('equipment_type_pricing_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_type_id', sa.Integer(), nullable=False),
        sa.Column('pricing_option_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['equipment_type_id'], ['equipment_types.id'], ),
        sa.ForeignKeyConstraint(['pricing_option_id'], ['pricing_options.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('equipment_type_id', 'pricing_option_id', name='uq_equip_type_pricing_option')
    )
    op.create_index(op.f('ix_equipment_type_pricing_options_id'), 'equipment_type_pricing_options', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_equipment_type_pricing_options_id'), table_name='equipment_type_pricing_options')
    op.drop_table('equipment_type_pricing_options')
