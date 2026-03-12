"""fix_model_pricing_history_sequence_drift

Revision ID: b3f4e5a6c7d8
Revises: a0819014454c, a1b2c3d4e5f6
Create Date: 2026-02-16 21:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3f4e5a6c7d8"
down_revision: Union[str, Sequence[str], None] = ("a0819014454c", "a1b2c3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep model_pricing_history ID sequence aligned with existing rows.
    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('model_pricing_history', 'id'),
                COALESCE((SELECT MAX(id) FROM model_pricing_history), 1),
                COALESCE((SELECT MAX(id) FROM model_pricing_history), 0) > 0
            );
            """
        )
    )


def downgrade() -> None:
    # Data/sequence correction is not safely reversible.
    pass

