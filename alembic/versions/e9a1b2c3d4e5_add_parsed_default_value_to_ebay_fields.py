"""Add parsed_default_value to ebay_fields

Revision ID: e9a1b2c3d4e5
Revises: e3f4a5b6c7d8
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ebay_fields", sa.Column("parsed_default_value", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("ebay_fields", "parsed_default_value")

