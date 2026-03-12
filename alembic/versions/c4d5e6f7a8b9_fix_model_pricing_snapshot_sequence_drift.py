"""fix_model_pricing_snapshot_sequence_drift

Revision ID: c4d5e6f7a8b9
Revises: b3f4e5a6c7d8
Create Date: 2026-02-16 22:35:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3f4e5a6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sync_sequence(table_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table_name}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                COALESCE((SELECT MAX(id) FROM {table_name}), 0) > 0
            );
            """
        )
    )


def upgrade() -> None:
    # Keep pricing snapshot/history ID sequences aligned with existing rows.
    _sync_sequence("model_pricing_snapshots")
    _sync_sequence("model_pricing_history")


def downgrade() -> None:
    # Data/sequence correction is not safely reversible.
    pass

