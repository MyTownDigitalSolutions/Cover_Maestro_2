"""add ebay field equipment type image patterns table

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ebay_field_equipment_type_image_patterns (
            id SERIAL PRIMARY KEY,
            ebay_field_id INTEGER NOT NULL,
            equipment_type_id INTEGER NULL,
            parent_pattern TEXT NOT NULL,
            variation_pattern TEXT NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ebay_field_equipment_type_image_patterns_id
        ON ebay_field_equipment_type_image_patterns (id)
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_ebay_field_equipment_type_image_pattern'
            ) THEN
                ALTER TABLE ebay_field_equipment_type_image_patterns
                ADD CONSTRAINT uq_ebay_field_equipment_type_image_pattern
                UNIQUE (ebay_field_id, equipment_type_id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ebay_field_equipment_type_image_patterns_ebay_field_id_fkey'
            ) THEN
                ALTER TABLE ebay_field_equipment_type_image_patterns
                ADD CONSTRAINT ebay_field_equipment_type_image_patterns_ebay_field_id_fkey
                FOREIGN KEY (ebay_field_id) REFERENCES ebay_fields(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ebay_field_equipment_type_image_patterns_equipment_type_id_fkey'
            ) THEN
                ALTER TABLE ebay_field_equipment_type_image_patterns
                ADD CONSTRAINT ebay_field_equipment_type_image_patterns_equipment_type_id_fkey
                FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ebay_field_equipment_type_image_patterns_id", table_name="ebay_field_equipment_type_image_patterns")
    op.drop_table("ebay_field_equipment_type_image_patterns")

