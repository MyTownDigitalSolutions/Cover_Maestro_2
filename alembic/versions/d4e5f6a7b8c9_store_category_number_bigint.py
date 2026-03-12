"""Make ebay store category numbers bigint

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ebay_store_category_nodes",
        "store_category_number",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        postgresql_using="store_category_number::bigint",
    )
    op.alter_column(
        "ebay_store_categories",
        "store_category_number",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        postgresql_using="store_category_number::bigint",
    )


def downgrade() -> None:
    op.alter_column(
        "ebay_store_categories",
        "store_category_number",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        postgresql_using="store_category_number::integer",
    )
    op.alter_column(
        "ebay_store_category_nodes",
        "store_category_number",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        postgresql_using="store_category_number::integer",
    )

