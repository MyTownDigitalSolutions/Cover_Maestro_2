"""fix_product_type_field_value_sequence_drift

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-17 10:25:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
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
    # Keep template import tables' ID sequences aligned with existing rows.
    _sync_sequence("product_type_fields")
    _sync_sequence("product_type_field_values")


def downgrade() -> None:
    # Data/sequence correction is not safely reversible.
    pass

