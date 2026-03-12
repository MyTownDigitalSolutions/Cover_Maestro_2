"""realign_core_table_sequences

Revision ID: a7e4c1d9b2f0
Revises: f7a8b9c0d1e2
Create Date: 2026-02-17 07:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7e4c1d9b2f0"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _realign_sequence(table_name: str) -> None:
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
    # Realign primary key sequences that can drift after data restores/imports.
    for table in (
        "manufacturers",
        "series",
        "equipment_types",
        "models",
        "materials",
        "material_colour_surcharges",
        "suppliers",
        "supplier_materials",
        "customers",
        "orders",
        "order_lines",
    ):
        _realign_sequence(table)


def downgrade() -> None:
    # Sequence realignment is a data correction and not safely reversible.
    pass
