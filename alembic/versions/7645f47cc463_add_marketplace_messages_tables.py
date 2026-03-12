"""add_marketplace_messages_tables

Revision ID: 7645f47cc463
Revises: 7403e6390ecb
Create Date: 2026-01-21 20:51:59.613720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7645f47cc463'
down_revision: Union[str, Sequence[str], None] = '7403e6390ecb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create marketplace_conversations
    # NOTE: These tables were already added to models in core.py in previous step
    # This migration formally adds them to the database schema history
    
    # Check if table exists first to support potential partial applied state from previous step
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'marketplace_conversations' not in tables:
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

    if 'marketplace_messages' not in tables:
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
    # We generally don't drop tables in downgrade to be safe, 
    # but strictly speaking this migration created them.
    # Given "Additive Only" constraint, dropping is risky if data exists.
    # However, for pure schema correctness:
    op.drop_table('marketplace_messages')
    op.drop_table('marketplace_conversations')
