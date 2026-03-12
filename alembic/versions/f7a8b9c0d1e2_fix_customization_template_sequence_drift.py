"""fix_customization_template_sequence_drift

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-02-17 11:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
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
    # Keep customization template tables' ID sequences aligned with existing rows.
    _sync_sequence("amazon_customization_templates")
    _sync_sequence("equipment_type_customization_templates")


def downgrade() -> None:
    # Sequence correction is not safely reversible.
    pass

