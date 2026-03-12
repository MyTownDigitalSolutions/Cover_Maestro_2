"""add colors and material_colors tables

Revision ID: ab12cd34ef56
Revises: a9b8c7d6e5f4
Create Date: 2026-03-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab12cd34ef56"
down_revision: Union[str, None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "colors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("internal_name", sa.String(length=128), nullable=False),
        sa.Column("friendly_name", sa.String(length=128), nullable=False),
        sa.Column("sku_abbrev", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_name"),
    )
    op.create_index("ix_colors_id", "colors", ["id"], unique=False)

    op.create_table(
        "material_colors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("color_id", sa.Integer(), nullable=False),
        sa.Column("surcharge", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ebay_variation_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["color_id"], ["colors.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("material_id", "color_id", name="uq_material_colors_material_color"),
    )
    op.create_index("ix_material_colors_id", "material_colors", ["id"], unique=False)
    op.create_index("ix_material_colors_material_id", "material_colors", ["material_id"], unique=False)
    op.create_index("ix_material_colors_color_id", "material_colors", ["color_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_material_colors_color_id", table_name="material_colors")
    op.drop_index("ix_material_colors_material_id", table_name="material_colors")
    op.drop_index("ix_material_colors_id", table_name="material_colors")
    op.drop_table("material_colors")

    op.drop_index("ix_colors_id", table_name="colors")
    op.drop_table("colors")
