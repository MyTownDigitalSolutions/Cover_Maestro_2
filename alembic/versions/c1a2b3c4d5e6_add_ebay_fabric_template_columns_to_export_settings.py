"""add_ebay_fabric_template_columns_to_export_settings

Revision ID: c1a2b3c4d5e6
Revises: b9d1e2f3a4b5
Create Date: 2026-02-23 18:06:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "b9d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "export_settings",
        sa.Column("ebay_fabric_template_no_padding", sa.String(), nullable=True),
    )
    op.add_column(
        "export_settings",
        sa.Column("ebay_fabric_template_with_padding", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("export_settings", "ebay_fabric_template_with_padding")
    op.drop_column("export_settings", "ebay_fabric_template_no_padding")
