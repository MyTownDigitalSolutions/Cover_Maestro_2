"""Add model_notes column to models table

Revision ID: add_model_notes
Revises: previous_migration
Create Date: 2025-01-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_model_notes'
down_revision = None  # Update this to reference your last migration
branch_labels = None
depends_on = None


def upgrade():
    # Add model_notes column - TEXT, nullable
    op.add_column('models', sa.Column('model_notes', sa.Text(), nullable=True))


def downgrade():
    # Remove model_notes column
    op.drop_column('models', 'model_notes')
