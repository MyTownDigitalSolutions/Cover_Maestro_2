"""Add ebay store category nodes

Revision ID: b1c2d3e4f5a6
Revises: a4b5c6d7e8f9
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ebay_store_category_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("system", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("store_category_number", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("binding_type", sa.String(), nullable=False, server_default=sa.text("'none'")),
        sa.Column("binding_id", sa.Integer(), nullable=True),
        sa.Column("binding_label", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["ebay_store_category_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ebay_store_category_nodes_id"), "ebay_store_category_nodes", ["id"], unique=False)
    op.create_index(op.f("ix_ebay_store_category_nodes_system"), "ebay_store_category_nodes", ["system"], unique=False)
    op.create_index(op.f("ix_ebay_store_category_nodes_level"), "ebay_store_category_nodes", ["level"], unique=False)
    op.create_index(op.f("ix_ebay_store_category_nodes_parent_id"), "ebay_store_category_nodes", ["parent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ebay_store_category_nodes_parent_id"), table_name="ebay_store_category_nodes")
    op.drop_index(op.f("ix_ebay_store_category_nodes_level"), table_name="ebay_store_category_nodes")
    op.drop_index(op.f("ix_ebay_store_category_nodes_system"), table_name="ebay_store_category_nodes")
    op.drop_index(op.f("ix_ebay_store_category_nodes_id"), table_name="ebay_store_category_nodes")
    op.drop_table("ebay_store_category_nodes")
