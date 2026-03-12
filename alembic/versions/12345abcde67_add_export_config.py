"""add export config

Revision ID: 12345abcde67
Revises: 69db6a90d75b
Create Date: 2025-12-27 01:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '12345abcde67'
down_revision = '69db6a90d75b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('amazon_product_types', schema=None) as batch_op:
        batch_op.add_column(sa.Column('export_sheet_name_override', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('export_start_row_override', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('export_force_exact_start_row', sa.Boolean(), server_default='0', nullable=False))


def downgrade():
    with op.batch_alter_table('amazon_product_types', schema=None) as batch_op:
        batch_op.drop_column('export_force_exact_start_row')
        batch_op.drop_column('export_start_row_override')
        batch_op.drop_column('export_sheet_name_override')
