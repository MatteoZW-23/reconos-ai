from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.transaction import NormalizedTransaction, ReconciliationStatus
from app.models.ai_insight import AIInsight, InsightType
from app.schemas.ai import (
    AnomalyScanResponse,
    AIInsightResponse,
    InvestigationExplanationResponse,
)
from app.services.ai_investigation.anomaly_detector import AnomalyDetector
from app.services.ai_investigation.discrepancy_explainer import DiscrepancyExplainer
from app.services.ai_investigation.candidate_ranker import CandidateRanker
from app.services.audit_service import log_audit_event
from app.api.deps import get_current_user, require_roles

router = APIRouter()

@router.post("/scan-anomalies", response_model=AnomalyScanResponse)
def scan_anomalies(
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    detector = AnomalyDetector()
    results = detector.scan_transactions(db, current_user.organization_id)
    anom_count = sum(1 for r in results if r.is_anomaly)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="RUN_AI_ANOMALY_SCAN",
        resource_type="AI_ANOMALY_MODEL",
        user_id=current_user.id,
        details={"scanned_count": len(results), "anomalies_flagged": anom_count}
    )
    db.commit()

    return AnomalyScanResponse(
        scanned_count=len(results),
        anomalies_detected=anom_count,
        anomalies=results
    )

@router.get("/insights", response_model=list[AIInsightResponse])
def get_ai_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Return persisted insights without inventing findings for new tenants.
    insights = db.query(AIInsight).filter(
        AIInsight.organization_id == current_user.organization_id
    ).all()

    # Older versions persisted this exact synthetic placeholder. Preserve the
    # record but do not present it as a finding about the customer's business.
    return [item for item in insights if not (
        item.title == "Mobile Money Weekend Settlement Window Latency"
        and item.evidence == {"affected_channel": "EcoCash Merchant Wallet",
                              "sample_window": "Friday 16:00 to Monday 09:00",
                              "average_lag_hours": 52}
    )]

@router.get("/explain/{transaction_id}", response_model=InvestigationExplanationResponse)
def get_transaction_explanation(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return DiscrepancyExplainer.explain_unmatched_transaction(
        db=db,
        transaction_id=transaction_id,
        organization_id=current_user.organization_id
    )

@router.get("/rank-candidates/{transaction_id}")
def rank_candidates_for_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == transaction_id,
        NormalizedTransaction.organization_id == current_user.organization_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target transaction not found")

    candidates = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.organization_id == current_user.organization_id,
        NormalizedTransaction.id != target.id,
        NormalizedTransaction.financial_account_id != target.financial_account_id,
        NormalizedTransaction.currency == target.currency,
        NormalizedTransaction.transaction_type == target.transaction_type,
        NormalizedTransaction.is_duplicate == False,
        NormalizedTransaction.reconciliation_status != ReconciliationStatus.MATCHED
    ).limit(30).all()

    ranked = CandidateRanker.rank_candidates(target, candidates)
    return {"target_id": target.id, "candidates": ranked}
