"""add template field selection source columns

Revision ID: b7d8e9f0a1b2
Revises: 0a9b8c7d6e5f
Create Date: 2026-03-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d8e9f0a1b2"
down_revision: Union[str, None] = "0a9b8c7d6e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("template_fields", sa.Column("selected_value_source", sa.String(), nullable=True))
    op.add_column("template_fields", sa.Column("parent_selected_value_source", sa.String(), nullable=True))
    op.add_column("template_fields", sa.Column("variation_selected_value_source", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("template_fields", "variation_selected_value_source")
    op.drop_column("template_fields", "parent_selected_value_source")
    op.drop_column("template_fields", "selected_value_source")

