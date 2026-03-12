"""add_designer_measurements_and_no_angle

Revision ID: e65bf78a222a
Revises: 72e95fcfbbbc
Create Date: 2025-12-26 19:05:38.690563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e65bf78a222a'
down_revision: Union[str, Sequence[str], None] = '72e95fcfbbbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add two new designer measurement fields to models table
    op.add_column('models', sa.Column('top_depth_in', sa.Float(), nullable=True))
    op.add_column('models', sa.Column('angle_drop_in', sa.Float(), nullable=True))
    
    # Add 'No Angle' to the AngleType enum
    # SQLite doesn't support ALTER TYPE, so we handle this at the application level
    # The new enum value will be available when the ORM is updated


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('models', 'angle_drop_in')
    op.drop_column('models', 'top_depth_in')
