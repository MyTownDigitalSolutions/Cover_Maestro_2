"""add_top_handle_measurements

Revision ID: cfb2ea64ace7
Revises: d1256fecefa1
Create Date: 2025-12-26 20:10:20.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfb2ea64ace7'
down_revision: Union[str, Sequence[str], None] = 'd1256fecefa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable float columns for top handle design note measurements."""
    with op.batch_alter_table('models', schema=None) as batch_op:
        batch_op.add_column(sa.Column('top_handle_length_in', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('top_handle_height_in', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('top_handle_rear_edge_to_center_in', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove top handle measurement columns."""
    with op.batch_alter_table('models', schema=None) as batch_op:
        batch_op.drop_column('top_handle_rear_edge_to_center_in')
        batch_op.drop_column('top_handle_height_in')
        batch_op.drop_column('top_handle_length_in')
