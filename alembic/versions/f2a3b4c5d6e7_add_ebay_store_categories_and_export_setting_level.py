"""Add ebay store categories and export setting default level

Revision ID: f2a3b4c5d6e7
Revises: e1b2c3d4f5a6
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1b2c3d4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ebay_store_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("system", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("equipment_type_id", sa.Integer(), nullable=False),
        sa.Column("manufacturer_id", sa.Integer(), nullable=True),
        sa.Column("series_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.String(), nullable=False),
        sa.Column("category_name", sa.String(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_types.id"]),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"]),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["ebay_store_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ebay_store_categories_id"), "ebay_store_categories", ["id"], unique=False)
    op.create_index(op.f("ix_ebay_store_categories_system"), "ebay_store_categories", ["system"], unique=False)
    op.create_index(op.f("ix_ebay_store_categories_level"), "ebay_store_categories", ["level"], unique=False)
    op.create_index(op.f("ix_ebay_store_categories_equipment_type_id"), "ebay_store_categories", ["equipment_type_id"], unique=False)
    op.create_index(op.f("ix_ebay_store_categories_manufacturer_id"), "ebay_store_categories", ["manufacturer_id"], unique=False)
    op.create_index(op.f("ix_ebay_store_categories_series_id"), "ebay_store_categories", ["series_id"], unique=False)
    op.create_index(op.f("ix_ebay_store_categories_parent_id"), "ebay_store_categories", ["parent_id"], unique=False)
    op.create_index(
        "uq_ebay_store_cat_equipment_type",
        "ebay_store_categories",
        ["system", "level", "equipment_type_id"],
        unique=True,
        sqlite_where=sa.text("level = 'equipment_type'"),
        postgresql_where=sa.text("level = 'equipment_type'"),
    )
    op.create_index(
        "uq_ebay_store_cat_manufacturer",
        "ebay_store_categories",
        ["system", "level", "equipment_type_id", "manufacturer_id"],
        unique=True,
        sqlite_where=sa.text("level = 'manufacturer'"),
        postgresql_where=sa.text("level = 'manufacturer'"),
    )
    op.create_index(
        "uq_ebay_store_cat_series",
        "ebay_store_categories",
        ["system", "level", "equipment_type_id", "series_id"],
        unique=True,
        sqlite_where=sa.text("level = 'series'"),
        postgresql_where=sa.text("level = 'series'"),
    )

    op.add_column(
        "export_settings",
        sa.Column("ebay_store_category_default_level", sa.String(), nullable=False, server_default="series"),
    )


def downgrade() -> None:
    op.drop_column("export_settings", "ebay_store_category_default_level")

    op.drop_index("uq_ebay_store_cat_series", table_name="ebay_store_categories")
    op.drop_index("uq_ebay_store_cat_manufacturer", table_name="ebay_store_categories")
    op.drop_index("uq_ebay_store_cat_equipment_type", table_name="ebay_store_categories")
    op.drop_index(op.f("ix_ebay_store_categories_parent_id"), table_name="ebay_store_categories")
    op.drop_index(op.f("ix_ebay_store_categories_series_id"), table_name="ebay_store_categories")
    op.drop_index(op.f("ix_ebay_store_categories_manufacturer_id"), table_name="ebay_store_categories")
    op.drop_index(op.f("ix_ebay_store_categories_equipment_type_id"), table_name="ebay_store_categories")
    op.drop_index(op.f("ix_ebay_store_categories_level"), table_name="ebay_store_categories")
    op.drop_index(op.f("ix_ebay_store_categories_system"), table_name="ebay_store_categories")
    op.drop_index(op.f("ix_ebay_store_categories_id"), table_name="ebay_store_categories")
    op.drop_table("ebay_store_categories")
