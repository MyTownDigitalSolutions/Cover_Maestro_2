"""Add parent/variation value columns to ebay_fields

Revision ID: e3f4a5b6c7d8
Revises: d4e5f6a7b8c9
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ebay_fields", sa.Column("parent_selected_value", sa.String(), nullable=True))
    op.add_column("ebay_fields", sa.Column("parent_custom_value", sa.String(), nullable=True))
    op.add_column("ebay_fields", sa.Column("variation_selected_value", sa.String(), nullable=True))
    op.add_column("ebay_fields", sa.Column("variation_custom_value", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("ebay_fields", "variation_custom_value")
    op.drop_column("ebay_fields", "variation_selected_value")
    op.drop_column("ebay_fields", "parent_custom_value")
    op.drop_column("ebay_fields", "parent_selected_value")

