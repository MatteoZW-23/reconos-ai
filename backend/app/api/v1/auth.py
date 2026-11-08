import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.organization import Organization, Branch
from app.schemas.auth import Token, LoginRequest, OnboardingRequest, UserResponse
from app.utils.security import verify_password, hash_password, create_access_token
from app.services.audit_service import log_audit_event
from app.api.deps import get_current_user

router = APIRouter()

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text)

@router.post("/login", response_model=Token)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email, User.is_active == True).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not org or not org.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    org_name = org.name if org else "ReconOS Organization"

    token_data = {
        "sub": user.id,
        "org_id": user.organization_id,
        "role": user.role.value,
        "branch_id": user.branch_id
    }
    access_token = create_access_token(data=token_data)

    log_audit_event(
        db=db,
        organization_id=user.organization_id,
        action="USER_LOGIN",
        resource_type="USER",
        resource_id=user.id,
        user_id=user.id,
        details={"email": user.email}
    )
    db.commit()

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        organization_id=user.organization_id,
        organization_name=org_name,
        role=user.role,
        full_name=user.full_name,
        email=user.email
    )

@router.post("/onboarding", response_model=Token)
def onboard_organization(req: OnboardingRequest, db: Session = Depends(get_db)):
    # Check if user email already exists
    existing_user = db.query(User).filter(User.email == req.admin_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="A user with this email address already exists")

    base_slug = slugify(req.organization_name)
    slug = base_slug
    counter = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(
        name=req.organization_name,
        slug=slug,
        default_currency=req.default_currency.upper()
    )
    db.add(org)
    db.flush()

    branch = Branch(
        organization_id=org.id,
        name=req.branch_name or "Headquarters",
        code=req.branch_code or "HQ-01",
        country="Zimbabwe"
    )
    db.add(branch)
    db.flush()

    admin_user = User(
        organization_id=org.id,
        branch_id=branch.id,
        email=req.admin_email,
        hashed_password=hash_password(req.admin_password),
        full_name=req.admin_full_name,
        role=UserRole.OWNER
    )
    db.add(admin_user)
    db.flush()

    log_audit_event(
        db=db,
        organization_id=org.id,
        action="ONBOARD_ORGANIZATION",
        resource_type="ORGANIZATION",
        resource_id=org.id,
        user_id=admin_user.id,
        details={"organization_name": org.name, "admin_email": admin_user.email}
    )

    db.commit()

    token_data = {
        "sub": admin_user.id,
        "org_id": org.id,
        "role": admin_user.role.value,
        "branch_id": branch.id
    }
    access_token = create_access_token(data=token_data)

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=admin_user.id,
        organization_id=org.id,
        organization_name=org.name,
        role=admin_user.role,
        full_name=admin_user.full_name,
        email=admin_user.email
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
