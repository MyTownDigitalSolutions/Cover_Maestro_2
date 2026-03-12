"""add canonical template_fields and bridge ebay_fields

Revision ID: f4d5e6f7a8b9
Revises: f3c4d5e6f7a8
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "f3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS template_fields (
            id SERIAL PRIMARY KEY,
            marketplace VARCHAR NOT NULL,
            field_name VARCHAR NOT NULL,
            field_key_norm VARCHAR NOT NULL,
            order_index INTEGER NULL,
            required BOOLEAN NOT NULL DEFAULT false,
            row_scope VARCHAR NULL,
            selected_value VARCHAR NULL,
            custom_value VARCHAR NULL,
            parent_selected_value VARCHAR NULL,
            parent_custom_value VARCHAR NULL,
            variation_selected_value VARCHAR NULL,
            variation_custom_value VARCHAR NULL,
            parsed_default_value VARCHAR NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_template_fields_id
        ON template_fields (id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_template_fields_marketplace_field_key_norm
        ON template_fields (marketplace, field_key_norm)
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_template_fields_marketplace_field_key_norm'
            ) THEN
                ALTER TABLE template_fields
                ADD CONSTRAINT uq_template_fields_marketplace_field_key_norm
                UNIQUE (marketplace, field_key_norm);
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'ebay_fields'
                  AND column_name = 'template_field_id'
            ) THEN
                ALTER TABLE ebay_fields ADD COLUMN template_field_id INTEGER NULL;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        INSERT INTO template_fields (
            marketplace,
            field_name,
            field_key_norm,
            order_index,
            required,
            row_scope,
            selected_value,
            custom_value,
            parent_selected_value,
            parent_custom_value,
            variation_selected_value,
            variation_custom_value,
            parsed_default_value,
            created_at,
            updated_at
        )
        SELECT DISTINCT ON (field_key_norm)
            'ebay' AS marketplace,
            field_name,
            field_key_norm,
            order_index,
            COALESCE(required, false) AS required,
            row_scope,
            selected_value,
            custom_value,
            parent_selected_value,
            parent_custom_value,
            variation_selected_value,
            variation_custom_value,
            parsed_default_value,
            NOW() AS created_at,
            NOW() AS updated_at
        FROM (
            SELECT
                ef.*,
                lower(regexp_replace(coalesce(ef.field_name, ''), '[^a-zA-Z0-9]+', '', 'g')) AS field_key_norm
            FROM ebay_fields ef
        ) s
        WHERE field_key_norm <> ''
        ORDER BY field_key_norm, id DESC
        ON CONFLICT (marketplace, field_key_norm) DO NOTHING
        """
    )

    op.execute(
        """
        UPDATE ebay_fields ef
        SET template_field_id = tf.id
        FROM template_fields tf
        WHERE tf.marketplace = 'ebay'
          AND tf.field_key_norm = lower(regexp_replace(coalesce(ef.field_name, ''), '[^a-zA-Z0-9]+', '', 'g'))
          AND ef.template_field_id IS NULL
        """
    )
    op.execute("UPDATE template_fields SET required = false WHERE required IS NULL")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_ebay_fields_template_field_id_template_fields'
            ) THEN
                ALTER TABLE ebay_fields
                ADD CONSTRAINT fk_ebay_fields_template_field_id_template_fields
                FOREIGN KEY (template_field_id) REFERENCES template_fields(id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ebay_fields_template_field_id
        ON ebay_fields (template_field_id)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ebay_fields_template_field_id", table_name="ebay_fields")
    op.drop_constraint("fk_ebay_fields_template_field_id_template_fields", "ebay_fields", type_="foreignkey")
    op.drop_column("ebay_fields", "template_field_id")

    op.drop_index("ix_template_fields_marketplace_field_key_norm", table_name="template_fields")
    op.drop_index("ix_template_fields_id", table_name="template_fields")
    op.drop_table("template_fields")
