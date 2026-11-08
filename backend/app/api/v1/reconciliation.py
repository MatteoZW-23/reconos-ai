from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.reconciliation import (
    ReconciliationSession,
    ReconciliationMatch,
    MatchParticipant,
    SessionStatus,
    MatchStatus,
    MatchType,
    ParticipantSide,
)
from app.models.transaction import NormalizedTransaction, ReconciliationStatus
from app.models.financial_account import FinancialAccount
from app.schemas.reconciliation import (
    SessionCreate,
    SessionResponse,
    MatchResponse,
    ParticipantDetail,
    ManualMatchRequest,
    MatchDecisionRequest,
    SessionApprovalRequest,
    BalanceCheckResponse,
)
from app.services.reconciliation_engine.engine import ReconciliationEngine
from app.services.reconciliation_engine.balance_checker import BalanceChecker
from app.services.audit_service import log_audit_event
from app.api.deps import get_current_user, require_roles
from app.utils.decimal_math import to_decimal

router = APIRouter()

def format_session_response(session: ReconciliationSession) -> SessionResponse:
    matches_dto = []
    for m in session.matches:
        participants_dto = []
        for p in m.participants:
            participants_dto.append(ParticipantDetail(
                id=p.id,
                transaction_id=p.transaction_id,
                side=p.side,
                allocated_amount=p.allocated_amount,
                external_reference=p.transaction.external_reference if p.transaction else None,
                transaction_date=p.transaction.transaction_date if p.transaction else None,
                description=p.transaction.description if p.transaction else None
            ))
        matches_dto.append(MatchResponse(
            id=m.id,
            session_id=m.session_id,
            match_type=m.match_type,
            confidence_score=m.confidence_score,
            status=m.status,
            primary_amount_total=m.primary_amount_total,
            secondary_amount_total=m.secondary_amount_total,
            difference_amount=m.difference_amount,
            notes=m.notes,
            created_at=m.created_at,
            participants=participants_dto
        ))

    total_pool = session.total_primary_count + session.total_secondary_count
    confirmed_participants = sum(len(m.participants) for m in session.matches if m.status == MatchStatus.CONFIRMED)
    recon_rate = (Decimal(confirmed_participants) * 100 / Decimal(total_pool)).quantize(Decimal("0.01")) if total_pool > 0 else Decimal("0.00")

    return SessionResponse(
        id=session.id,
        organization_id=session.organization_id,
        session_name=session.session_name,
        primary_account_id=session.primary_account_id,
        secondary_account_id=session.secondary_account_id,
        date_from=session.date_from,
        date_to=session.date_to,
        status=session.status,
        total_primary_count=session.total_primary_count,
        total_secondary_count=session.total_secondary_count,
        total_primary_amount=session.total_primary_amount,
        total_secondary_amount=session.total_secondary_amount,
        matched_count=session.matched_count,
        matched_amount=session.matched_amount,
        discrepancy_amount=session.discrepancy_amount,
        reconciliation_rate=recon_rate,
        approved_by_id=session.approved_by_id,
        approved_at=session.approved_at,
        created_at=session.created_at,
        matches=matches_dto
    )

@router.post("/sessions", response_model=SessionResponse)
def create_session(
    req: SessionCreate,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    if req.primary_account_id == req.secondary_account_id or req.date_from > req.date_to:
        raise HTTPException(status_code=400, detail="Select distinct accounts and a valid date range")
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.organization_id == current_user.organization_id,
        FinancialAccount.id.in_([req.primary_account_id, req.secondary_account_id]),
    ).all()
    if len(accounts) != 2:
        raise HTTPException(status_code=404, detail="Account not found")
    if accounts[0].currency != accounts[1].currency:
        raise HTTPException(status_code=400, detail="Reconciliation accounts must use the same currency")
    session = ReconciliationSession(
        organization_id=current_user.organization_id,
        session_name=req.session_name,
        primary_account_id=req.primary_account_id,
        secondary_account_id=req.secondary_account_id,
        date_from=req.date_from,
        date_to=req.date_to,
        rule_config=req.rule_config.model_dump(mode="json") if req.rule_config else None,
        initiated_by_id=current_user.id
    )
    db.add(session)
    db.flush()

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="CREATE_RECONCILIATION_SESSION",
        resource_type="RECONCILIATION_SESSION",
        resource_id=session.id,
        user_id=current_user.id,
        details={"name": session.session_name}
    )
    db.commit()
    db.refresh(session)
    return format_session_response(session)

@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(ReconciliationSession).filter(
        ReconciliationSession.organization_id == current_user.organization_id
    ).order_by(ReconciliationSession.created_at.desc()).all()
    return [format_session_response(s) for s in sessions]

@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ReconciliationSession).filter(
        ReconciliationSession.id == session_id,
        ReconciliationSession.organization_id == current_user.organization_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Reconciliation session not found")
    return format_session_response(session)

@router.post("/sessions/{session_id}/execute", response_model=SessionResponse)
def execute_session(
    session_id: str,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    engine = ReconciliationEngine(db)
    try:
        updated_session = engine.execute_session(
            session_id=session_id,
            organization_id=current_user.organization_id,
            user_id=current_user.id
        )
        return format_session_response(updated_session)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Reconciliation execution failed")

@router.post("/sessions/{session_id}/manual-match", response_model=SessionResponse)
def manual_match_transactions(
    session_id: str,
    req: ManualMatchRequest,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    session = db.query(ReconciliationSession).filter(
        ReconciliationSession.id == session_id,
        ReconciliationSession.organization_id == current_user.organization_id
    ).with_for_update().first()
    if not session:
        raise HTTPException(status_code=404, detail="Reconciliation session not found")

    if session.status != SessionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Manual matches require a completed, unapproved session")
    if (len(set(req.primary_transaction_ids)) != len(req.primary_transaction_ids) or
        len(set(req.secondary_transaction_ids)) != len(req.secondary_transaction_ids)):
        raise HTTPException(status_code=400, detail="Duplicate transaction IDs are not allowed")
    p_txs = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id.in_(req.primary_transaction_ids),
        NormalizedTransaction.organization_id == current_user.organization_id
    ).with_for_update().all()

    s_txs = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id.in_(req.secondary_transaction_ids),
        NormalizedTransaction.organization_id == current_user.organization_id
    ).with_for_update().all()

    if not p_txs or not s_txs or len(p_txs) != len(req.primary_transaction_ids) or len(s_txs) != len(req.secondary_transaction_ids):
        raise HTTPException(status_code=400, detail="Must select at least one primary and one secondary transaction to match")
    for tx, account_id in [(tx, session.primary_account_id) for tx in p_txs] + [(tx, session.secondary_account_id) for tx in s_txs]:
        if (tx.financial_account_id != account_id or tx.is_duplicate or
            not session.date_from <= tx.transaction_date <= session.date_to or
            tx.reconciliation_status not in (ReconciliationStatus.UNRECONCILED, ReconciliationStatus.EXCEPTION)):
            raise HTTPException(status_code=400, detail="Transaction is not available for this session")
    if len({tx.currency for tx in p_txs + s_txs}) != 1 or len({tx.transaction_type for tx in p_txs + s_txs}) != 1:
        raise HTTPException(status_code=400, detail="Transactions must have the same currency and direction")

    p_total = sum((to_decimal(tx.amount) for tx in p_txs), Decimal("0.0000"))
    s_total = sum((to_decimal(tx.amount) for tx in s_txs), Decimal("0.0000"))
    diff = p_total - s_total
    if diff != 0:
        raise HTTPException(status_code=400, detail="Manual matches must have equal totals; partial settlement is not supported")

    match_rec = ReconciliationMatch(
        session_id=session.id,
        organization_id=current_user.organization_id,
        match_type=MatchType.MANUAL_OVERRIDE,
        confidence_score=Decimal("100.00"),
        status=MatchStatus.CONFIRMED,
        primary_amount_total=p_total,
        secondary_amount_total=s_total,
        difference_amount=diff,
        notes=req.notes or "Manual authorized override match",
        matched_by_user_id=current_user.id
    )
    db.add(match_rec)
    db.flush()

    for p in p_txs:
        part = MatchParticipant(
            match_id=match_rec.id,
            transaction_id=p.id,
            side=ParticipantSide.PRIMARY,
            allocated_amount=to_decimal(p.amount)
        )
        db.add(part)
        p.reconciliation_status = ReconciliationStatus.MATCHED

    for s in s_txs:
        part = MatchParticipant(
            match_id=match_rec.id,
            transaction_id=s.id,
            side=ParticipantSide.SECONDARY,
            allocated_amount=to_decimal(s.amount)
        )
        db.add(part)
        s.reconciliation_status = ReconciliationStatus.MATCHED

    session.matched_count += 1
    session.matched_amount += p_total
    session.discrepancy_amount = max(Decimal("0"), session.discrepancy_amount - p_total - s_total)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="MANUAL_RECONCILIATION_MATCH",
        resource_type="RECONCILIATION_MATCH",
        resource_id=match_rec.id,
        user_id=current_user.id,
        details={"primary_ids": req.primary_transaction_ids, "secondary_ids": req.secondary_transaction_ids, "notes": req.notes}
    )

    db.commit()
    db.refresh(session)
    return format_session_response(session)

@router.post("/sessions/{session_id}/matches/{match_id}/decision", response_model=SessionResponse)
def decide_match(
    session_id: str,
    match_id: str,
    req: MatchDecisionRequest,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    session = db.query(ReconciliationSession).filter(
        ReconciliationSession.id == session_id,
        ReconciliationSession.organization_id == current_user.organization_id,
    ).with_for_update().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    match = db.query(ReconciliationMatch).filter(
        ReconciliationMatch.id == match_id,
        ReconciliationMatch.session_id == session_id,
        ReconciliationMatch.organization_id == current_user.organization_id
    ).with_for_update().first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if session.status != SessionStatus.COMPLETED or match.status != MatchStatus.SUGGESTED:
        raise HTTPException(status_code=400, detail="Only suggested matches in an unapproved session can be reviewed")

    if req.action == "CONFIRM":
        if match.difference_amount != 0:
            raise HTTPException(status_code=400, detail="Unequal matches require partial allocation, which is not yet supported")
        match.status = MatchStatus.CONFIRMED
        session.matched_count += 1
        session.matched_amount += match.primary_amount_total
        session.discrepancy_amount = max(Decimal("0"), session.discrepancy_amount - match.primary_amount_total - match.secondary_amount_total + abs(match.difference_amount))
        for part in match.participants:
            if part.transaction:
                part.transaction.reconciliation_status = ReconciliationStatus.MATCHED
    elif req.action == "REJECT":
        match.status = MatchStatus.REJECTED
        for part in match.participants:
            if part.transaction:
                part.transaction.reconciliation_status = ReconciliationStatus.UNRECONCILED
    else:
        raise HTTPException(status_code=400, detail="Action must be CONFIRM or REJECT")

    if req.notes:
        match.notes = (match.notes or "") + f" | Decision Note: {req.notes}"

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action=f"MATCH_DECISION_{req.action}",
        resource_type="RECONCILIATION_MATCH",
        resource_id=match.id,
        user_id=current_user.id,
        details={"action": req.action, "notes": req.notes}
    )

    db.commit()
    db.refresh(session)
    return format_session_response(session)

@router.post("/sessions/{session_id}/approve", response_model=SessionResponse)
def approve_session(
    session_id: str,
    req: SessionApprovalRequest,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.FINANCE_MANAGER])),
    db: Session = Depends(get_db)
):
    session = db.query(ReconciliationSession).filter(
        ReconciliationSession.id == session_id,
        ReconciliationSession.organization_id == current_user.organization_id
    ).with_for_update().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.COMPLETED or any(m.status == MatchStatus.SUGGESTED for m in session.matches):
        raise HTTPException(status_code=400, detail="Complete the session and review all suggested matches before approval")

    session.status = SessionStatus.APPROVED
    session.approved_by_id = current_user.id
    session.approved_at = datetime.utcnow()

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="APPROVE_RECONCILIATION_SESSION",
        resource_type="RECONCILIATION_SESSION",
        resource_id=session.id,
        user_id=current_user.id,
        details={"approved_at": session.approved_at.isoformat(), "notes": req.notes}
    )

    db.commit()
    db.refresh(session)
    return format_session_response(session)
