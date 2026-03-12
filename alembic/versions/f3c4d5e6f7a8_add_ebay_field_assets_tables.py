"""add ebay field assets tables

Revision ID: f3c4d5e6f7a8
Revises: f2b3c4d5e6f7
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ebay_field_assets (
            id SERIAL PRIMARY KEY,
            ebay_field_id INTEGER NOT NULL,
            asset_type VARCHAR NOT NULL,
            value TEXT NOT NULL,
            is_default_fallback BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ebay_field_assets_id
        ON ebay_field_assets (id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ebay_field_assets_field_type
        ON ebay_field_assets (ebay_field_id, asset_type)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ebay_field_assets_fallback_per_field_type
        ON ebay_field_assets (ebay_field_id, asset_type)
        WHERE is_default_fallback = true
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_ebay_field_assets_asset_type'
            ) THEN
                ALTER TABLE ebay_field_assets
                ADD CONSTRAINT ck_ebay_field_assets_asset_type
                CHECK (asset_type in ('image_parent_pattern','image_variation_pattern'));
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
                WHERE conname = 'ebay_field_assets_ebay_field_id_fkey'
            ) THEN
                ALTER TABLE ebay_field_assets
                ADD CONSTRAINT ebay_field_assets_ebay_field_id_fkey
                FOREIGN KEY (ebay_field_id) REFERENCES ebay_fields(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ebay_field_asset_equipment_types (
            id SERIAL PRIMARY KEY,
            asset_id INTEGER NOT NULL,
            equipment_type_id INTEGER NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ebay_field_asset_equipment_types_id
        ON ebay_field_asset_equipment_types (id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ebay_field_asset_equipment_types_equipment_type_id
        ON ebay_field_asset_equipment_types (equipment_type_id)
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_ebay_field_asset_equipment_type'
            ) THEN
                ALTER TABLE ebay_field_asset_equipment_types
                ADD CONSTRAINT uq_ebay_field_asset_equipment_type
                UNIQUE (asset_id, equipment_type_id);
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
                WHERE conname = 'ebay_field_asset_equipment_types_asset_id_fkey'
            ) THEN
                ALTER TABLE ebay_field_asset_equipment_types
                ADD CONSTRAINT ebay_field_asset_equipment_types_asset_id_fkey
                FOREIGN KEY (asset_id) REFERENCES ebay_field_assets(id) ON DELETE CASCADE;
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
                WHERE conname = 'ebay_field_asset_equipment_types_equipment_type_id_fkey'
            ) THEN
                ALTER TABLE ebay_field_asset_equipment_types
                ADD CONSTRAINT ebay_field_asset_equipment_types_equipment_type_id_fkey
                FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ebay_field_asset_equipment_types_equipment_type_id", table_name="ebay_field_asset_equipment_types")
    op.drop_index("ix_ebay_field_asset_equipment_types_id", table_name="ebay_field_asset_equipment_types")
    op.drop_table("ebay_field_asset_equipment_types")

    op.drop_index("uq_ebay_field_assets_fallback_per_field_type", table_name="ebay_field_assets")
    op.drop_index("ix_ebay_field_assets_field_type", table_name="ebay_field_assets")
    op.drop_index("ix_ebay_field_assets_id", table_name="ebay_field_assets")
    op.drop_table("ebay_field_assets")

