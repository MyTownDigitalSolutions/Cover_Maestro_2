"""enforce_one_template_per_equipment_type

Revision ID: 69db6a90d75b
Revises: cfb2ea64ace7
Create Date: 2025-12-26 21:52:52.438429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69db6a90d75b'
down_revision: Union[str, Sequence[str], None] = 'cfb2ea64ace7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




from sqlalchemy import text, Integer
from collections import defaultdict

def upgrade() -> None:
    conn = op.get_bind()
    
    # 1. Make column nullable to allow unassigning
    with op.batch_alter_table("equipment_type_product_types", schema=None) as batch_op:
        batch_op.alter_column('equipment_type_id', nullable=True, existing_type=Integer())

    # 2. Find duplicates and cleanup
    query = text("""
        SELECT 
            etpt.id, 
            etpt.equipment_type_id, 
            etpt.product_type_id,
            et.amazon_customization_template_id,
            apt.file_path,
            apt.id as apt_id
        FROM equipment_type_product_types etpt
        LEFT JOIN equipment_types et ON etpt.equipment_type_id = et.id
        LEFT JOIN amazon_product_types apt ON etpt.product_type_id = apt.id
        WHERE etpt.equipment_type_id IS NOT NULL
        ORDER BY etpt.equipment_type_id
    """)
    rows = conn.execute(query).fetchall()
    
    groups = defaultdict(list)
    for r in rows:
        # Access safely assuming RowProxy allows attribute or key access
        # Using getattr or _mapping if needed, but attribute access usually works in new SQLAlchemy
        eq_id = r.equipment_type_id
        groups[eq_id].append(r)
        
    losers = []
    cleaned_count = 0
    
    for eq_id, records in groups.items():
        if len(records) > 1:
            winner = None
            
            # Rule 1: Explicit Assignment (Check if implicit match)
            # We compare IDs cautiously.
            explicit_matches = [r for r in records if r.amazon_customization_template_id == r.product_type_id]
            
            if explicit_matches:
                 winner = explicit_matches[0]
            else:
                 # Rule 2: Non-null file_path, then max ID
                 candidates_with_file = [r for r in records if r.file_path]
                 if candidates_with_file:
                     # Sort by ProductType ID desc (proxy for recency)
                     candidates_with_file.sort(key=lambda x: x.apt_id or 0, reverse=True)
                     winner = candidates_with_file[0]
                 else:
                     # Rule 3: Max Link ID (most recently created assignment)
                     records.sort(key=lambda x: x.id, reverse=True)
                     winner = records[0]
            
            # Identify losers
            msg_losers = []
            for r in records:
                if r.id != winner.id:
                    losers.append(r.id)
                    msg_losers.append(str(r.product_type_id))
            
            print(f"Cleanup: EquipmentType {eq_id} had {len(records)} templates; kept {winner.product_type_id}; unassigned {','.join(msg_losers)}")
            cleaned_count += 1

    if losers:
        print(f"Cleanup: Unassigning {len(losers)} total duplicate links.")
        for loser_id in losers:
             conn.execute(text("UPDATE equipment_type_product_types SET equipment_type_id = NULL WHERE id = :id"), {"id": loser_id})

    # 3. Add Constraint
    with op.batch_alter_table("equipment_type_product_types", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_equipment_type_product_types_equipment_type_id", 
            ["equipment_type_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("equipment_type_product_types", schema=None) as batch_op:
        batch_op.drop_constraint("uq_equipment_type_product_types_equipment_type_id", type_="unique")
        # Attempt to revert nullable (may fail if nulls exist)
        # batch_op.alter_column('equipment_type_id', nullable=False, existing_type=sa.Integer())

