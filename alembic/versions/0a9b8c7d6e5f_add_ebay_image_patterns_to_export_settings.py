"""add_ebay_image_patterns_to_export_settings

Revision ID: 0a9b8c7d6e5f
Revises: f5a6b7c8d9e0
Create Date: 2026-03-01 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0a9b8c7d6e5f"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "export_settings",
        sa.Column("ebay_parent_image_pattern", sa.String(), nullable=True),
    )
    op.add_column(
        "export_settings",
        sa.Column("ebay_variation_image_pattern", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("export_settings", "ebay_variation_image_pattern")
    op.drop_column("export_settings", "ebay_parent_image_pattern")
