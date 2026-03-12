"""Add store and eBay category ids to ebay_store_categories

Revision ID: a4b5c6d7e8f9
Revises: f2a3b4c5d6e7
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ebay_store_categories", sa.Column("store_category_number", sa.Integer(), nullable=True))
    op.add_column("ebay_store_categories", sa.Column("ebay_category_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("ebay_store_categories", "ebay_category_id")
    op.drop_column("ebay_store_categories", "store_category_number")
