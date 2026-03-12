"""Expand customers table and link marketplace_orders to customers

Revision ID: a1b2c3d4e5f7
Revises: 16b73c2009b1
Create Date: 2026-01-21 16:51:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'd2d8a1d25888'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # Expand customers table with new columns
    # ============================================================
    
    # Names
    op.add_column('customers', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('customers', sa.Column('last_name', sa.String(100), nullable=True))
    
    # Emails (TWO DISTINCT EMAILS)
    op.add_column('customers', sa.Column('buyer_email', sa.String(255), nullable=True))
    op.add_column('customers', sa.Column('marketplace_buyer_email', sa.String(255), nullable=True))
    
    # Phones
    op.add_column('customers', sa.Column('mobile_phone', sa.String(40), nullable=True))
    op.add_column('customers', sa.Column('work_phone', sa.String(40), nullable=True))
    op.add_column('customers', sa.Column('other_phone', sa.String(40), nullable=True))
    
    # Billing Address
    op.add_column('customers', sa.Column('billing_address1', sa.String(255), nullable=True))
    op.add_column('customers', sa.Column('billing_address2', sa.String(255), nullable=True))
    op.add_column('customers', sa.Column('billing_city', sa.String(120), nullable=True))
    op.add_column('customers', sa.Column('billing_state', sa.String(120), nullable=True))
    op.add_column('customers', sa.Column('billing_postal_code', sa.String(40), nullable=True))
    op.add_column('customers', sa.Column('billing_country', sa.String(80), nullable=True))
    
    # Shipping Name + Address
    op.add_column('customers', sa.Column('shipping_name', sa.String(255), nullable=True))
    op.add_column('customers', sa.Column('shipping_address1', sa.String(255), nullable=True))
    op.add_column('customers', sa.Column('shipping_address2', sa.String(255), nullable=True))
    op.add_column('customers', sa.Column('shipping_city', sa.String(120), nullable=True))
    op.add_column('customers', sa.Column('shipping_state', sa.String(120), nullable=True))
    op.add_column('customers', sa.Column('shipping_postal_code', sa.String(40), nullable=True))
    op.add_column('customers', sa.Column('shipping_country', sa.String(80), nullable=True))
    
    # Marketplace identity (for deterministic matching)
    op.add_column('customers', sa.Column('source_marketplace', sa.String(40), nullable=True))
    op.add_column('customers', sa.Column('source_customer_id', sa.String(80), nullable=True))
    
    # Add indexes on customers
    op.create_index('ix_customers_buyer_email', 'customers', ['buyer_email'])
    op.create_index('ix_customers_marketplace_buyer_email', 'customers', ['marketplace_buyer_email'])
    op.create_index('ix_customers_marketplace_identity', 'customers', ['source_marketplace', 'source_customer_id'])
    
    # ============================================================
    # Add customer_id FK to marketplace_orders
    # ============================================================
    op.add_column('marketplace_orders', sa.Column('customer_id', sa.Integer(), nullable=True))
    
    # Create FK constraint (SQLite compatible)
    with op.batch_alter_table('marketplace_orders') as batch_op:
        batch_op.create_foreign_key(
            'fk_marketplace_orders_customer_id',
            'customers',
            ['customer_id'],
            ['id'],
            ondelete='SET NULL'
        )
    
    op.create_index('ix_marketplace_orders_customer_id', 'marketplace_orders', ['customer_id'])


def downgrade() -> None:
    # Remove FK and index from marketplace_orders
    op.drop_index('ix_marketplace_orders_customer_id', 'marketplace_orders')
    with op.batch_alter_table('marketplace_orders') as batch_op:
        batch_op.drop_constraint('fk_marketplace_orders_customer_id', type_='foreignkey')
    op.drop_column('marketplace_orders', 'customer_id')
    
    # Remove indexes from customers
    op.drop_index('ix_customers_marketplace_identity', 'customers')
    op.drop_index('ix_customers_marketplace_buyer_email', 'customers')
    op.drop_index('ix_customers_buyer_email', 'customers')
    
    # Remove columns from customers
    op.drop_column('customers', 'source_customer_id')
    op.drop_column('customers', 'source_marketplace')
    op.drop_column('customers', 'shipping_country')
    op.drop_column('customers', 'shipping_postal_code')
    op.drop_column('customers', 'shipping_state')
    op.drop_column('customers', 'shipping_city')
    op.drop_column('customers', 'shipping_address2')
    op.drop_column('customers', 'shipping_address1')
    op.drop_column('customers', 'shipping_name')
    op.drop_column('customers', 'billing_country')
    op.drop_column('customers', 'billing_postal_code')
    op.drop_column('customers', 'billing_state')
    op.drop_column('customers', 'billing_city')
    op.drop_column('customers', 'billing_address2')
    op.drop_column('customers', 'billing_address1')
    op.drop_column('customers', 'other_phone')
    op.drop_column('customers', 'work_phone')
    op.drop_column('customers', 'mobile_phone')
    op.drop_column('customers', 'marketplace_buyer_email')
    op.drop_column('customers', 'buyer_email')
    op.drop_column('customers', 'last_name')
    op.drop_column('customers', 'first_name')
