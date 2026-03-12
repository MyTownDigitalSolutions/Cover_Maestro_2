"""add placeholder_token to design_options

Revision ID: 57b252b8811c
Revises: 0c5758488c82
Create Date: 2026-01-22 22:30:26.168422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57b252b8811c'
down_revision: Union[str, Sequence[str], None] = '0c5758488c82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('design_options') as batch_op:
        batch_op.add_column(sa.Column('placeholder_token', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_design_options_placeholder_token', ['placeholder_token'])


def downgrade() -> None:
    with op.batch_alter_table('design_options') as batch_op:
        batch_op.drop_constraint('uq_design_options_placeholder_token', type_='unique')
        batch_op.drop_column('placeholder_token')
