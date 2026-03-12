"""add_display_name_with_padding_to_material_role_configs

Revision ID: d8f1a2b3c4d5
Revises: c1a2b3c4d5e6
Create Date: 2026-02-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "c1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "material_role_configs",
        sa.Column("display_name_with_padding", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("material_role_configs", "display_name_with_padding")
