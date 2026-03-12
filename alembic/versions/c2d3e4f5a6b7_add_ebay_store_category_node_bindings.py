"""Add ebay store category node bindings

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ebay_store_category_node_bindings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("binding_type", sa.String(), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["ebay_store_category_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id", "binding_type", "binding_id", name="uq_ebay_store_category_node_binding"),
    )
    op.create_index(op.f("ix_ebay_store_category_node_bindings_id"), "ebay_store_category_node_bindings", ["id"], unique=False)
    op.create_index(op.f("ix_ebay_store_category_node_bindings_node_id"), "ebay_store_category_node_bindings", ["node_id"], unique=False)
    op.create_index(op.f("ix_ebay_store_category_node_bindings_binding_type"), "ebay_store_category_node_bindings", ["binding_type"], unique=False)
    op.create_index(op.f("ix_ebay_store_category_node_bindings_binding_id"), "ebay_store_category_node_bindings", ["binding_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ebay_store_category_node_bindings_binding_id"), table_name="ebay_store_category_node_bindings")
    op.drop_index(op.f("ix_ebay_store_category_node_bindings_binding_type"), table_name="ebay_store_category_node_bindings")
    op.drop_index(op.f("ix_ebay_store_category_node_bindings_node_id"), table_name="ebay_store_category_node_bindings")
    op.drop_index(op.f("ix_ebay_store_category_node_bindings_id"), table_name="ebay_store_category_node_bindings")
    op.drop_table("ebay_store_category_node_bindings")
