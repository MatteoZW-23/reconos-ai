from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Branch
from app.models.user import User, UserRole
from app.schemas.organization import BranchCreate, BranchResponse
from app.api.deps import get_current_user, require_roles
from app.services.audit_service import log_audit_event

router = APIRouter()

@router.get("", response_model=list[BranchResponse])
def list_branches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Branch).filter(
        Branch.organization_id == current_user.organization_id,
        Branch.is_active == True
    )
    if current_user.role in (UserRole.OPERATOR, UserRole.BRANCH_MANAGER):
        query = query.filter(Branch.id == current_user.branch_id)
    return query.all()

@router.post("", response_model=BranchResponse)
def create_branch(
    req: BranchCreate,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER])),
    db: Session = Depends(get_db)
):
    branch = Branch(
        organization_id=current_user.organization_id,
        name=req.name,
        code=req.code,
        address=req.address,
        city=req.city,
        country=req.country or "Zimbabwe"
    )
    db.add(branch)
    db.flush()

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="CREATE_BRANCH",
        resource_type="BRANCH",
        resource_id=branch.id,
        user_id=current_user.id,
        details={"name": branch.name, "code": branch.code}
    )
    db.commit()
    db.refresh(branch)
    return branch
