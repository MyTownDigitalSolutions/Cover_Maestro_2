"""add display_name to reverb_templates

Revision ID: b4c5d6e7f8a9
Revises: ab12cd34ef56
Create Date: 2026-03-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reverb_templates", sa.Column("display_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("reverb_templates", "display_name")
