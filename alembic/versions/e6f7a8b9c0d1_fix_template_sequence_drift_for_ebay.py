"""fix_template_sequence_drift_for_ebay

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-02-17 10:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
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
    # Keep template tables' ID sequences aligned with existing rows.
    _sync_sequence("ebay_templates")
    _sync_sequence("ebay_fields")
    _sync_sequence("ebay_field_values")


def downgrade() -> None:
    # Sequence correction is not safely reversible.
    pass

