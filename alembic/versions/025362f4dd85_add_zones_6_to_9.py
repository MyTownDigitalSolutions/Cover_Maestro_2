"""add_zones_6_to_9

Revision ID: 025362f4dd85
Revises: 1b01423ff433
Create Date: 2025-12-23 17:00:12.165080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '025362f4dd85'
down_revision: Union[str, Sequence[str], None] = '1b01423ff433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure 1-5 exist (restoring missing data)
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('1', 'Zone 1', 1, TRUE)")
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('2', 'Zone 2', 2, TRUE)")
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('3', 'Zone 3', 3, TRUE)")
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('4', 'Zone 4', 4, TRUE)")
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('5', 'Zone 5', 5, TRUE)")
    # New zones 6-9
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('6', 'Zone 6', 6, TRUE)")
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('7', 'Zone 7', 7, TRUE)")
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('8', 'Zone 8', 8, TRUE)")
    op.execute("INSERT INTO shipping_zones (code, name, sort_order, active) VALUES ('9', 'Zone 9', 9, TRUE)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM shipping_zones WHERE code IN ('1', '2', '3', '4', '5', '6', '7', '8', '9')")
