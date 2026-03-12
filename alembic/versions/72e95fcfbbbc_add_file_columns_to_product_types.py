"""add_file_columns_to_product_types

Revision ID: 72e95fcfbbbc
Revises: 7ba518abc741
Create Date: 2025-12-26 13:29:28.695434

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72e95fcfbbbc'
down_revision: Union[str, Sequence[str], None] = '7ba518abc741'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('amazon_product_types', sa.Column('original_filename', sa.String(), nullable=True))
    op.add_column('amazon_product_types', sa.Column('file_path', sa.String(), nullable=True))
    op.add_column('amazon_product_types', sa.Column('upload_date', sa.DateTime(), nullable=True))
    op.add_column('amazon_product_types', sa.Column('file_size', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('amazon_product_types', 'file_size')
    op.drop_column('amazon_product_types', 'upload_date')
    op.drop_column('amazon_product_types', 'file_path')
    op.drop_column('amazon_product_types', 'original_filename')
