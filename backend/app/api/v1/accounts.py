from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.financial_account import FinancialAccount
from app.models.user import User, UserRole
from app.models.organization import Branch
from app.schemas.financial_account import AccountCreate, AccountResponse
from app.schemas.reconciliation import BalanceCheckResponse
from app.services.reconciliation_engine.balance_checker import BalanceChecker
from app.api.deps import get_current_user, require_roles
from app.services.audit_service import log_audit_event

router = APIRouter()

def require_active_manager_branch(db: Session, user: User):
    branch = db.query(Branch).filter(Branch.id == user.branch_id,
        Branch.organization_id == user.organization_id, Branch.is_active == True).first()
    if branch is None:
        raise HTTPException(status_code=403, detail="An active branch assignment is required")
    return branch.id

@router.get("", response_model=list[AccountResponse])
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(FinancialAccount).filter(
        FinancialAccount.organization_id == current_user.organization_id,
        FinancialAccount.is_active == True
    )
    if current_user.role == UserRole.BRANCH_MANAGER:
        query = query.filter(FinancialAccount.branch_id == require_active_manager_branch(db, current_user))
    return query.all()

@router.post("", response_model=AccountResponse)
def create_account(
    req: AccountCreate,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    if req.branch_id and not db.query(Branch).filter(
        Branch.id == req.branch_id, Branch.organization_id == current_user.organization_id,
        Branch.is_active == True
    ).first():
        raise HTTPException(status_code=404, detail="Branch not found")
    account = FinancialAccount(
        organization_id=current_user.organization_id,
        branch_id=req.branch_id,
        name=req.name,
        account_type=req.account_type,
        provider_name=req.provider_name,
        account_number=req.account_number,
        currency=req.currency.upper(),
        opening_balance=req.opening_balance,
        current_balance=req.opening_balance
    )
    db.add(account)
    db.flush()

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="CREATE_FINANCIAL_ACCOUNT",
        resource_type="FINANCIAL_ACCOUNT",
        resource_id=account.id,
        user_id=current_user.id,
        details={"name": account.name, "provider": account.provider_name, "type": account.account_type.value}
    )
    db.commit()
    db.refresh(account)
    return account

@router.get("/{account_id}/balance-check", response_model=BalanceCheckResponse)
def check_account_balance(
    account_id: str,
    date_from: datetime = Query(default_factory=lambda: datetime.utcnow() - timedelta(days=30)),
    date_to: datetime = Query(default_factory=lambda: datetime.utcnow()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == UserRole.BRANCH_MANAGER:
        branch_id = require_active_manager_branch(db, current_user)
        account = db.query(FinancialAccount).filter(
            FinancialAccount.id == account_id,
            FinancialAccount.organization_id == current_user.organization_id,
            FinancialAccount.branch_id == branch_id,
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Financial account not found")
    return BalanceChecker.check_account_balance(
        db=db,
        account_id=account_id,
        organization_id=current_user.organization_id,
        date_from=date_from,
        date_to=date_to
    )
