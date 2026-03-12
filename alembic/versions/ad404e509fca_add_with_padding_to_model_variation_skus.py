"""add_with_padding_to_model_variation_skus

Revision ID: ad404e509fca
Revises: 57b252b8811c
Create Date: 2026-01-25 01:04:30.116040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad404e509fca'
down_revision: Union[str, Sequence[str], None] = '57b252b8811c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("model_variation_skus", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("with_padding", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        # Remove server default after backfill to keep schema clean
        batch_op.alter_column("with_padding", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("model_variation_skus", schema=None) as batch_op:
        batch_op.drop_column("with_padding")
