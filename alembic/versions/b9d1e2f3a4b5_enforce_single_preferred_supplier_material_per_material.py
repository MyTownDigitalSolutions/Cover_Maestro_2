"""enforce_single_preferred_supplier_material_per_material

Revision ID: b9d1e2f3a4b5
Revises: a7e4c1d9b2f0
Create Date: 2026-02-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "a7e4c1d9b2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PREFERRED_INDEX_NAME = "uq_supplier_materials_one_preferred_per_material"


def upgrade() -> None:
    # Deterministically resolve existing duplicate preferred rows per material.
    # Keep the preferred row with the highest id and unset the others.
    op.execute(
        sa.text(
            """
            WITH ranked_preferred AS (
                SELECT
                    id,
                    material_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY material_id
                        ORDER BY id DESC
                    ) AS rn
                FROM supplier_materials
                WHERE is_preferred = true
            )
            UPDATE supplier_materials sm
            SET is_preferred = false
            FROM ranked_preferred rp
            WHERE sm.id = rp.id
              AND rp.rn > 1;
            """
        )
    )

    op.create_index(
        PREFERRED_INDEX_NAME,
        "supplier_materials",
        ["material_id"],
        unique=True,
        postgresql_where=sa.text("is_preferred = true"),
    )


def downgrade() -> None:
    op.drop_index(PREFERRED_INDEX_NAME, table_name="supplier_materials")
