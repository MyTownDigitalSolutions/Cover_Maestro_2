"""add ebay field equipment type contents table

Revision ID: f1a2b3c4d5e6
Revises: e9a1b2c3d4e5
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e9a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ebay_field_equipment_type_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ebay_field_id", sa.Integer(), nullable=False),
        sa.Column("equipment_type_id", sa.Integer(), nullable=True),
        sa.Column("html_value", sa.Text(), nullable=False),
        sa.Column("is_default_fallback", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ebay_field_id"], ["ebay_fields.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ebay_field_id", "equipment_type_id", name="uq_ebay_field_equipment_type_content"),
    )
    op.create_index(
        "ix_ebay_field_equipment_type_contents_id",
        "ebay_field_equipment_type_contents",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ebay_field_equipment_type_contents_id", table_name="ebay_field_equipment_type_contents")
    op.drop_table("ebay_field_equipment_type_contents")

