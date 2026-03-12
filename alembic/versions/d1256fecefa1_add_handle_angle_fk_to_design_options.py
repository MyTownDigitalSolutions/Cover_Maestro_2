"""add_handle_angle_fk_to_design_options

Revision ID: d1256fecefa1
Revises: e65bf78a222a
Create Date: 2025-12-26 19:33:08.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1256fecefa1'
down_revision: Union[str, Sequence[str], None] = 'e65bf78a222a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add FK columns for dynamic design option selection."""
    #  Columns already exist from a previous partial migration attempt
    # Just add the FK constraints
    with op.batch_alter_table('models', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_models_handle_location_option',
            'design_options',
            ['handle_location_option_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_models_angle_type_option',
            'design_options',
            ['angle_type_option_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    """Downgrade schema - remove FK columns."""
    with op.batch_alter_table('models', schema=None) as batch_op:
        batch_op.drop_constraint('fk_models_angle_type_option', type_='foreignkey')
        batch_op.drop_constraint('fk_models_handle_location_option', type_='foreignkey')
        batch_op.drop_column('angle_type_option_id')
        batch_op.drop_column('handle_location_option_id')
