"""add source to template field assets

Revision ID: c8d9e0f1a2b3
Revises: b7d8e9f0a1b2
Create Date: 2026-03-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "template_field_assets",
        sa.Column("source", sa.String(), nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("template_field_assets", "source")

