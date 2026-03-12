"""Add row_scope to ebay_fields

Revision ID: e1b2c3d4f5a6
Revises: d8f1a2b3c4d5
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1b2c3d4f5a6'
down_revision: Union[str, Sequence[str], None] = 'd8f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ebay_fields', sa.Column('row_scope', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('ebay_fields', 'row_scope')
