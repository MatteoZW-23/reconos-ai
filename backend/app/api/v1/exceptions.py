import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.reconciliation import ReconciliationSession
from app.models.transaction import NormalizedTransaction
from app.models.exception_case import (
    ExceptionCase,
    ExceptionCategory,
    ExceptionSeverity,
    ExceptionStatus,
)
from app.schemas.exception_case import (
    ExceptionCreate,
    ExceptionUpdate,
    ExceptionResponse,
)
from app.schemas.ai import InvestigationExplanationResponse
from app.services.ai_investigation.discrepancy_explainer import DiscrepancyExplainer
from app.services.audit_service import log_audit_event
from app.api.deps import get_current_user, require_roles
from app.utils.decimal_math import to_decimal

router = APIRouter()

def validate_case_links(db: Session, organization_id: str, session_id=None, transaction_id=None, assigned_to_id=None):
    for model, record_id in ((ReconciliationSession, session_id), (NormalizedTransaction, transaction_id), (User, assigned_to_id)):
        if record_id and not db.query(model).filter(model.id == record_id, model.organization_id == organization_id).first():
            raise HTTPException(status_code=404, detail="Referenced record not found")

@router.get("", response_model=list[ExceptionResponse])
def list_exceptions(
    status: ExceptionStatus | None = None,
    severity: ExceptionSeverity | None = None,
    category: ExceptionCategory | None = None,
    assigned_to_me: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ExceptionCase).filter(ExceptionCase.organization_id == current_user.organization_id)
    if status:
        query = query.filter(ExceptionCase.status == status)
    if severity:
        query = query.filter(ExceptionCase.severity == severity)
    if category:
        query = query.filter(ExceptionCase.category == category)
    if assigned_to_me:
        query = query.filter(ExceptionCase.assigned_to_id == current_user.id)
    return query.order_by(ExceptionCase.created_at.desc()).all()

@router.post("", response_model=ExceptionResponse)
def create_exception(
    req: ExceptionCreate,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    validate_case_links(db, current_user.organization_id, req.session_id, req.transaction_id, req.assigned_to_id)
    case_no = f"EX-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    exception_case = ExceptionCase(
        organization_id=current_user.organization_id,
        session_id=req.session_id,
        transaction_id=req.transaction_id,
        case_number=case_no,
        title=req.title,
        description=req.description,
        category=req.category,
        severity=req.severity,
        status=ExceptionStatus.OPEN,
        discrepancy_amount=to_decimal(req.discrepancy_amount),
        currency=req.currency.upper(),
        assigned_to_id=req.assigned_to_id,
        created_by_id=current_user.id,
        evidence=req.evidence
    )
    db.add(exception_case)
    db.flush()

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="CREATE_EXCEPTION_CASE",
        resource_type="EXCEPTION_CASE",
        resource_id=exception_case.id,
        user_id=current_user.id,
        details={"case_number": case_no, "title": req.title, "amount": str(req.discrepancy_amount)}
    )

    db.commit()
    db.refresh(exception_case)
    return exception_case

@router.patch("/{case_id}", response_model=ExceptionResponse)
def update_exception(
    case_id: str,
    req: ExceptionUpdate,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    case = db.query(ExceptionCase).filter(
        ExceptionCase.id == case_id,
        ExceptionCase.organization_id == current_user.organization_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Exception case not found")
    validate_case_links(db, current_user.organization_id, assigned_to_id=req.assigned_to_id)

    if req.title is not None:
        case.title = req.title
    if req.description is not None:
        case.description = req.description
    if req.severity is not None:
        case.severity = req.severity
    if req.assigned_to_id is not None:
        case.assigned_to_id = req.assigned_to_id
    if req.resolution_notes is not None:
        case.resolution_notes = req.resolution_notes
    if req.status is not None:
        case.status = req.status
        if req.status in [ExceptionStatus.RESOLVED, ExceptionStatus.CLOSED]:
            case.resolved_at = datetime.utcnow()

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="UPDATE_EXCEPTION_CASE",
        resource_type="EXCEPTION_CASE",
        resource_id=case.id,
        user_id=current_user.id,
        details={"new_status": case.status.value, "notes": req.resolution_notes}
    )

    db.commit()
    db.refresh(case)
    return case

@router.get("/{case_id}/ai-investigate", response_model=InvestigationExplanationResponse)
def get_ai_investigation_briefing(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    case = db.query(ExceptionCase).filter(
        ExceptionCase.id == case_id,
        ExceptionCase.organization_id == current_user.organization_id
    ).first()
    if not case or not case.transaction_id:
        raise HTTPException(status_code=404, detail="Exception case has no linked transaction for investigation")

    briefing = DiscrepancyExplainer.explain_unmatched_transaction(
        db=db,
        transaction_id=case.transaction_id,
        organization_id=current_user.organization_id
    )

    return briefing
