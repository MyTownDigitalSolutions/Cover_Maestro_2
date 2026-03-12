"""add assumed shipping fields

Revision ID: ade414416fed
Revises: 4ffe8a80d14e
Create Date: 2025-12-23 17:58:06.628539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ade414416fed'
down_revision: Union[str, Sequence[str], None] = '4ffe8a80d14e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('shipping_default_settings') as batch_op:
        batch_op.add_column(sa.Column('assumed_rate_card_id', sa.Integer(), sa.ForeignKey('shipping_rate_cards.id', name='fk_shipping_defaults_assumed_card'), nullable=True))
        batch_op.add_column(sa.Column('assumed_tier_id', sa.Integer(), sa.ForeignKey('shipping_rate_tiers.id', name='fk_shipping_defaults_assumed_tier'), nullable=True))
        batch_op.add_column(sa.Column('assumed_zone_code', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('shipping_default_settings') as batch_op:
        batch_op.drop_column('assumed_zone_code')
        batch_op.drop_column('assumed_tier_id')
        batch_op.drop_column('assumed_rate_card_id')
