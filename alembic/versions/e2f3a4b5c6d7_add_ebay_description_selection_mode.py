"""add ebay_description_selection_mode to export_settings

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-03-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "export_settings",
        sa.Column(
            "ebay_description_selection_mode",
            sa.String(),
            nullable=False,
            server_default="GLOBAL_PRIMARY",
        ),
    )


def downgrade() -> None:
    op.drop_column("export_settings", "ebay_description_selection_mode")
