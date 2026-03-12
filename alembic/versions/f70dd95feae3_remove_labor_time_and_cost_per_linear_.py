"""remove labor_time and cost_per_linear_yard from materials

Revision ID: f70dd95feae3
Revises: f88bfc7d4e1e
Create Date: 2025-12-22 03:02:51.894423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f70dd95feae3'
down_revision: Union[str, Sequence[str], None] = 'f88bfc7d4e1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove labor_time_minutes and cost_per_linear_yard from materials."""
    with op.batch_alter_table('materials', schema=None) as batch_op:
        batch_op.drop_column('labor_time_minutes')
        batch_op.drop_column('cost_per_linear_yard')


def downgrade() -> None:
    """Downgrade schema - add back removed columns."""
    with op.batch_alter_table('materials', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cost_per_linear_yard', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('labor_time_minutes', sa.Float(), nullable=False, server_default='0'))
