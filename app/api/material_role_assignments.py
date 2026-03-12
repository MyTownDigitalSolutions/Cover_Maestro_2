from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.core import MaterialRoleAssignment, Material
from app.schemas.core import (
    MaterialRoleAssignmentCreate,
    MaterialRoleAssignmentResponse
)

router = APIRouter(prefix="/material-role-assignments", tags=["material-role-assignments"])


@router.get("", response_model=List[MaterialRoleAssignmentResponse])
def list_material_role_assignments(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all material role assignments.
    
    Args:
        active_only: If True, only return assignments where end_date IS NULL
    
    Returns:
        List of assignments ordered by role ASC, effective_date DESC
    """
    query = db.query(MaterialRoleAssignment)
    
    if active_only:
        query = query.filter(MaterialRoleAssignment.end_date.is_(None))
    
    assignments = query.order_by(
        MaterialRoleAssignment.role.asc(),
        MaterialRoleAssignment.effective_date.desc()
    ).all()
    
    return assignments


@router.get("/active/{role}", response_model=Optional[MaterialRoleAssignmentResponse])
def get_active_assignment_for_role(role: str, db: Session = Depends(get_db)):
    """
    Get the currently active assignment for a specific role.
    
    Returns the most recent assignment where end_date IS NULL.
    """
    assignment = db.query(MaterialRoleAssignment).filter(
        MaterialRoleAssignment.role == role,
        MaterialRoleAssignment.end_date.is_(None)
    ).order_by(
        MaterialRoleAssignment.effective_date.desc(),
        MaterialRoleAssignment.created_at.desc()
    ).first()
    
    return assignment


@router.post("", response_model=MaterialRoleAssignmentResponse)
def create_material_role_assignment(
    data: MaterialRoleAssignmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new material role assignment.
    
    If auto_end_previous=True, automatically ends any active assignment
    for the same role by setting end_date to now.
    """
    # Validate material exists
    material = db.query(Material).filter(Material.id == data.material_id).first()
    if not material:
        raise HTTPException(
            status_code=404,
            detail=f"Material with ID {data.material_id} not found"
        )
    
    # Normalize role to uppercase
    role = data.role.strip().upper()
    if not role:
        raise HTTPException(status_code=400, detail="Role cannot be blank")
    
    # Auto-end previous active assignment if requested
    if data.auto_end_previous:
        active_assignments = db.query(MaterialRoleAssignment).filter(
            MaterialRoleAssignment.role == role,
            MaterialRoleAssignment.end_date.is_(None)
        ).all()
        
        for assignment in active_assignments:
            assignment.end_date = datetime.utcnow()
    
    # Create new assignment
    effective_date = data.effective_date or datetime.utcnow()
    
    assignment = MaterialRoleAssignment(
        role=role,
        material_id=data.material_id,
        effective_date=effective_date,
        end_date=None
    )
    
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    
    return assignment


@router.post("/{id}/end", response_model=MaterialRoleAssignmentResponse)
def end_material_role_assignment(id: int, db: Session = Depends(get_db)):
    """
    End a material role assignment by setting end_date to now.
    """
    assignment = db.query(MaterialRoleAssignment).filter(
        MaterialRoleAssignment.id == id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=404,
            detail=f"Material role assignment with ID {id} not found"
        )
    
    if assignment.end_date is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Assignment is already ended (end_date: {assignment.end_date})"
        )
    
    assignment.end_date = datetime.utcnow()
    
    db.commit()
    db.refresh(assignment)
    
    return assignment
