"""expand_reverb_fields_and_messages

Revision ID: 7403e6390ecb
Revises: a1b2c3d4e5f7
Create Date: 2026-01-21 19:55:17.109211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7403e6390ecb'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns to marketplace_orders
    with op.batch_alter_table('marketplace_orders') as batch_op:
        batch_op.add_column(sa.Column('payment_method', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('payment_status', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('shipping_provider', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('shipping_code', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('shipping_method', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('reverb_buyer_id', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('reverb_order_status', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('raw_marketplace_detail_data', sa.JSON(), nullable=True))

    # Create marketplace_conversations
    op.create_table(
        'marketplace_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=20), nullable=True),
        sa.Column('external_conversation_id', sa.String(length=128), nullable=True),
        sa.Column('external_buyer_id', sa.String(length=128), nullable=True),
        sa.Column('external_order_id', sa.String(length=128), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('raw_conversation_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('marketplace', 'external_conversation_id', name='uq_conversation_mp_ext_id')
    )

    # Create marketplace_messages
    op.create_table(
        'marketplace_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('external_message_id', sa.String(length=128), nullable=True),
        sa.Column('sender_type', sa.String(length=20), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('raw_message_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['marketplace_conversations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('conversation_id', 'external_message_id', name='uq_message_conv_ext_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('marketplace_messages')
    op.drop_table('marketplace_conversations')
    with op.batch_alter_table('marketplace_orders') as batch_op:
        batch_op.drop_column('raw_marketplace_detail_data')
        batch_op.drop_column('reverb_order_status')
        batch_op.drop_column('reverb_buyer_id')
        batch_op.drop_column('shipping_method')
        batch_op.drop_column('shipping_code')
        batch_op.drop_column('shipping_provider')
        batch_op.drop_column('payment_status')
        batch_op.drop_column('payment_method')
