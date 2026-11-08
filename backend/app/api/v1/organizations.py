from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Organization, Branch
from app.models.user import User, UserRole
from app.schemas.organization import OrganizationResponse
from app.schemas.auth import UserResponse, UserCreate
from app.utils.security import hash_password
from app.api.deps import get_current_user, require_roles
from app.services.audit_service import log_audit_event

router = APIRouter()

@router.get("/current", response_model=OrganizationResponse)
def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.get("/members", response_model=list[UserResponse])
def list_organization_members(
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER])),
    db: Session = Depends(get_db)
):
    members = db.query(User).filter(User.organization_id == current_user.organization_id).all()
    return members

@router.post("/members", response_model=UserResponse)
def add_organization_member(
    req: UserCreate,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER])),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.OWNER and req.role in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only an owner may create owner or administrator accounts")
    if current_user.role == UserRole.FINANCE_MANAGER and req.role not in (UserRole.ACCOUNTANT, UserRole.OPERATOR):
        raise HTTPException(status_code=403, detail="Finance managers may create accountant or operator accounts only")
    if req.branch_id and not db.query(Branch).filter(Branch.id == req.branch_id,
            Branch.organization_id == current_user.organization_id, Branch.is_active == True).first():
        raise HTTPException(status_code=404, detail="Branch not found")
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        organization_id=current_user.organization_id,
        branch_id=req.branch_id,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role
    )
    db.add(new_user)
    db.flush()

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="ADD_ORGANIZATION_MEMBER",
        resource_type="USER",
        resource_id=new_user.id,
        user_id=current_user.id,
        details={"member_email": new_user.email, "role": new_user.role.value}
    )
    db.commit()
    db.refresh(new_user)
    return new_user
