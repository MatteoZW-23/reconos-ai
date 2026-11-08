from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.shift import ShiftSummary, ShiftStatus
from app.models.organization import Branch
from app.schemas.shift import ShiftCreate, ShiftVerify, ShiftResponse
from app.api.deps import get_current_user, require_roles
from app.services.audit_service import log_audit_event
from app.utils.decimal_math import to_decimal

router = APIRouter()

@router.get("", response_model=list[ShiftResponse])
def list_shift_summaries(
    branch_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ShiftSummary).filter(ShiftSummary.organization_id == current_user.organization_id)
    if current_user.role == UserRole.OPERATOR:
        query = query.filter(ShiftSummary.cashier_id == current_user.id)
    elif current_user.role == UserRole.BRANCH_MANAGER:
        if not current_user.branch_id:
            raise HTTPException(status_code=403, detail="A branch assignment is required")
        query = query.filter(ShiftSummary.branch_id == current_user.branch_id)
    if branch_id:
        query = query.filter(ShiftSummary.branch_id == branch_id)
    return query.order_by(ShiftSummary.shift_date.desc()).all()

@router.post("", response_model=ShiftResponse)
def submit_shift_summary(
    req: ShiftCreate,
    current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.BRANCH_MANAGER, UserRole.ACCOUNTANT, UserRole.OWNER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    branch = db.query(Branch).filter(
        Branch.id == req.branch_id,
        Branch.organization_id == current_user.organization_id,
        Branch.is_active == True
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    if current_user.role in (UserRole.OPERATOR, UserRole.BRANCH_MANAGER) and current_user.branch_id != branch.id:
        raise HTTPException(status_code=403, detail="Shift belongs to another branch")

    # Serialize submissions by employee on databases supporting row locks.
    db.query(User).filter(User.id == current_user.id, User.organization_id == current_user.organization_id).with_for_update().one()
    existing = db.query(ShiftSummary).filter(
        ShiftSummary.organization_id == current_user.organization_id,
        ShiftSummary.cashier_id == current_user.id,
        ShiftSummary.shift_date == req.shift_date,
        ShiftSummary.shift_number == req.shift_number,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This shift has already been submitted")

    opening = to_decimal(req.opening_cash)
    cash_in = to_decimal(req.cash_sales)
    cash_out = to_decimal(req.cash_payouts)
    counted = to_decimal(req.closing_cash_counted)

    # Decimal equation for cash float
    expected = opening + cash_in - cash_out
    discrepancy = counted - expected
    if abs(expected) >= Decimal("100000000000000") or abs(discrepancy) >= Decimal("100000000000000"):
        raise HTTPException(status_code=422, detail="Calculated shift amounts exceed the supported range")

    status = ShiftStatus.SUBMITTED
    if discrepancy != Decimal("0.0000"):
        status = ShiftStatus.DISCREPANCY_FLAGGED

    shift = ShiftSummary(
        organization_id=current_user.organization_id,
        branch_id=req.branch_id,
        cashier_id=current_user.id,
        cashier_name=current_user.full_name,
        shift_date=req.shift_date,
        shift_number=req.shift_number,
        opening_cash=opening,
        cash_sales=cash_in,
        mobile_money_sales=to_decimal(req.mobile_money_sales),
        card_sales=to_decimal(req.card_sales),
        cash_payouts=cash_out,
        closing_cash_counted=counted,
        system_expected_cash=expected,
        cash_discrepancy=discrepancy,
        status=status
    )
    db.add(shift)
    db.flush()

    # The shift model has no currency field. Keep the discrepancy flagged on
    # the shift; creating a currency-denominated case here would invent a currency.

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="SUBMIT_SHIFT_SUMMARY",
        resource_type="SHIFT_SUMMARY",
        resource_id=shift.id,
        user_id=current_user.id,
        details={"branch": branch.name, "cashier": current_user.full_name, "variance": str(discrepancy)}
    )

    db.commit()
    db.refresh(shift)
    return shift

@router.patch("/{shift_id}/verify", response_model=ShiftResponse)
def verify_shift(
    shift_id: str,
    req: ShiftVerify,
    current_user: User = Depends(require_roles([UserRole.BRANCH_MANAGER, UserRole.FINANCE_MANAGER, UserRole.OWNER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    shift = db.query(ShiftSummary).filter(
        ShiftSummary.id == shift_id,
        ShiftSummary.organization_id == current_user.organization_id
    ).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift summary not found")

    if shift.cashier_id == current_user.id:
        raise HTTPException(status_code=403, detail="A supervisor cannot verify their own shift")
    if current_user.role == UserRole.BRANCH_MANAGER and shift.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Shift belongs to another branch")
    if shift.status == ShiftStatus.VERIFIED or req.status != ShiftStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="Only an unverified shift can be verified")

    shift.status = req.status
    shift.supervisor_notes = req.supervisor_notes
    shift.verified_by_id = current_user.id

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="VERIFY_SHIFT_SUMMARY",
        resource_type="SHIFT_SUMMARY",
        resource_id=shift.id,
        user_id=current_user.id,
        details={"status": shift.status.value, "notes": req.supervisor_notes}
    )

    db.commit()
    db.refresh(shift)
    return shift
