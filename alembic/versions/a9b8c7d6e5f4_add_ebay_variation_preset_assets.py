"""add ebay variation preset assets

Revision ID: a9b8c7d6e5f4
Revises: f0a1b2c3d4e5
Create Date: 2026-03-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ebay_variation_preset_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("marketplace", sa.String(), nullable=False, server_default="EBAY"),
        sa.Column("equipment_type_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ebay_variation_preset_assets_id",
        "ebay_variation_preset_assets",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_ebay_variation_preset_assets_marketplace",
        "ebay_variation_preset_assets",
        ["marketplace"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ebay_variation_preset_assets_marketplace", table_name="ebay_variation_preset_assets")
    op.drop_index("ix_ebay_variation_preset_assets_id", table_name="ebay_variation_preset_assets")
    op.drop_table("ebay_variation_preset_assets")
