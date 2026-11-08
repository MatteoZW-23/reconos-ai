import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.reconciliation import (
    ReconciliationSession,
    ReconciliationMatch,
    MatchParticipant,
    SessionStatus,
    MatchStatus,
    ParticipantSide,
    MatchType,
)
from app.models.transaction import NormalizedTransaction, ReconciliationStatus
from app.models.exception_case import (
    ExceptionCase,
    ExceptionCategory,
    ExceptionSeverity,
    ExceptionStatus,
)
from app.schemas.reconciliation import RuleConfig
from app.services.reconciliation_engine.rules import ReconciliationRules, MatchCandidate
from app.services.audit_service import log_audit_event
from app.utils.decimal_math import to_decimal

class ReconciliationEngine:
    def __init__(self, db: Session):
        self.db = db

    def execute_session(
        self,
        session_id: str,
        organization_id: str,
        user_id: str | None = None
    ) -> ReconciliationSession:
        session = self.db.query(ReconciliationSession).filter(
            ReconciliationSession.id == session_id,
            ReconciliationSession.organization_id == organization_id
        ).with_for_update().first()

        if not session:
            raise ValueError("Reconciliation session not found")
        if session.status != SessionStatus.DRAFT:
            raise ValueError("Only draft reconciliation sessions can be executed")

        rule_config_dict = session.rule_config or {}
        rule_config = RuleConfig(**rule_config_dict)

        # Retrieve unreconciled transactions for primary account
        primary_txs = self.db.query(NormalizedTransaction).filter(
            NormalizedTransaction.organization_id == organization_id,
            NormalizedTransaction.financial_account_id == session.primary_account_id,
            NormalizedTransaction.currency == session.primary_account.currency,
            NormalizedTransaction.transaction_date >= session.date_from,
            NormalizedTransaction.transaction_date <= session.date_to,
            NormalizedTransaction.is_duplicate == False,
            NormalizedTransaction.reconciliation_status.in_([ReconciliationStatus.UNRECONCILED, ReconciliationStatus.EXCEPTION])
        ).with_for_update().all()

        # Retrieve unreconciled transactions for secondary account
        secondary_txs = self.db.query(NormalizedTransaction).filter(
            NormalizedTransaction.organization_id == organization_id,
            NormalizedTransaction.financial_account_id == session.secondary_account_id,
            NormalizedTransaction.currency == session.secondary_account.currency,
            NormalizedTransaction.transaction_date >= session.date_from,
            NormalizedTransaction.transaction_date <= session.date_to,
            NormalizedTransaction.is_duplicate == False,
            NormalizedTransaction.reconciliation_status.in_([ReconciliationStatus.UNRECONCILED, ReconciliationStatus.EXCEPTION])
        ).with_for_update().all()

        session.total_primary_count = len(primary_txs)
        session.total_secondary_count = len(secondary_txs)
        session.total_primary_amount = sum((to_decimal(tx.amount) for tx in primary_txs), Decimal("0.0000"))
        session.total_secondary_amount = sum((to_decimal(tx.amount) for tx in secondary_txs), Decimal("0.0000"))
        session.status = SessionStatus.IN_PROGRESS

        # Track active pools
        p_pool = list(primary_txs)
        s_pool = list(secondary_txs)
        all_matches: list[MatchCandidate] = []

        # Stage 1: Exact reference matching
        if rule_config.exact_reference_match:
            exact_matches = ReconciliationRules.match_exact_references(p_pool, s_pool)
            all_matches.extend(exact_matches)
            # Remove matched items from pools
            matched_p = {tx.id for m in exact_matches for tx in m.primary_txs}
            matched_s = {tx.id for m in exact_matches for tx in m.secondary_txs}
            p_pool = [tx for tx in p_pool if tx.id not in matched_p]
            s_pool = [tx for tx in s_pool if tx.id not in matched_s]

        # Stage 2: Amount and Date tolerance matching
        tol_matches = ReconciliationRules.match_amount_and_date_tolerance(
            p_pool,
            s_pool,
            tolerance_days=rule_config.date_tolerance_days,
            amount_tolerance_percent=rule_config.amount_tolerance_percent
        )
        all_matches.extend(tol_matches)
        matched_p = {tx.id for m in tol_matches for tx in m.primary_txs}
        matched_s = {tx.id for m in tol_matches for tx in m.secondary_txs}
        p_pool = [tx for tx in p_pool if tx.id not in matched_p]
        s_pool = [tx for tx in s_pool if tx.id not in matched_s]

        # Aggregate matches are suggestions and always require human review.
        if rule_config.allow_many_to_one and s_pool and p_pool:
            o2m_matches = ReconciliationRules.match_one_to_many(
                p_pool,
                s_pool,
                tolerance_days=rule_config.date_tolerance_days + 1,
                max_group_size=rule_config.max_cluster_size
            )
            all_matches.extend(o2m_matches)
            matched_p = {tx.id for m in o2m_matches for tx in m.primary_txs}
            matched_s = {tx.id for m in o2m_matches for tx in m.secondary_txs}
            p_pool = [tx for tx in p_pool if tx.id not in matched_p]
            s_pool = [tx for tx in s_pool if tx.id not in matched_s]

        if rule_config.allow_one_to_many and s_pool and p_pool:
            reverse = ReconciliationRules.match_one_to_many(
                s_pool, p_pool, tolerance_days=rule_config.date_tolerance_days + 1,
                max_group_size=rule_config.max_cluster_size
            )
            reverse_matches = [MatchCandidate(
                match_type=MatchType.ONE_TO_MANY,
                primary_txs=m.secondary_txs,
                secondary_txs=m.primary_txs,
                confidence_score=m.confidence_score,
                notes=f"One-to-many aggregate suggestion (one primary record sums to {len(m.primary_txs)} secondary records)"
            ) for m in reverse]
            all_matches.extend(reverse_matches)
            matched_p = {tx.id for m in reverse_matches for tx in m.primary_txs}
            matched_s = {tx.id for m in reverse_matches for tx in m.secondary_txs}
            p_pool = [tx for tx in p_pool if tx.id not in matched_p]
            s_pool = [tx for tx in s_pool if tx.id not in matched_s]

        # Persist matches into database
        matched_volume = Decimal("0.0000")
        for candidate in all_matches:
            # Uncertain / ambiguous matches require human review
            match_status = MatchStatus.CONFIRMED if candidate.confidence_score >= Decimal("95.00") else MatchStatus.SUGGESTED
            tx_status = ReconciliationStatus.MATCHED if match_status == MatchStatus.CONFIRMED else ReconciliationStatus.MANUAL_REVIEW

            match_rec = ReconciliationMatch(
                session_id=session.id,
                organization_id=organization_id,
                match_type=candidate.match_type,
                confidence_score=candidate.confidence_score,
                status=match_status,
                primary_amount_total=candidate.primary_total,
                secondary_amount_total=candidate.secondary_total,
                difference_amount=candidate.difference,
                notes=candidate.notes,
                matched_by_user_id=user_id
            )
            self.db.add(match_rec)
            self.db.flush()

            if match_status == MatchStatus.CONFIRMED:
                matched_volume += candidate.primary_total

            # Add participants
            for p_tx in candidate.primary_txs:
                part = MatchParticipant(
                    match_id=match_rec.id,
                    transaction_id=p_tx.id,
                    side=ParticipantSide.PRIMARY,
                    allocated_amount=to_decimal(p_tx.amount)
                )
                self.db.add(part)
                p_tx.reconciliation_status = tx_status

            for s_tx in candidate.secondary_txs:
                part = MatchParticipant(
                    match_id=match_rec.id,
                    transaction_id=s_tx.id,
                    side=ParticipantSide.SECONDARY,
                    allocated_amount=to_decimal(s_tx.amount)
                )
                self.db.add(part)
                s_tx.reconciliation_status = tx_status

        # Remaining unmatched transactions:
        # Flag outstanding items as exceptions if significant or unhandled
        unmatched_count = len(p_pool) + len(s_pool)
        unmatched_volume = sum((to_decimal(t.amount) for t in p_pool), Decimal("0.0000")) + sum((to_decimal(t.amount) for t in s_pool), Decimal("0.0000"))
        
        session.matched_count = sum(1 for c in all_matches if c.confidence_score >= Decimal("95.00"))
        session.matched_amount = matched_volume
        session.discrepancy_amount = unmatched_volume + sum(
            (c.primary_total + c.secondary_total for c in all_matches if c.confidence_score < Decimal("95.00")), Decimal("0")
        )
        session.status = SessionStatus.COMPLETED

        # Create exception records for remaining unmatched transactions
        for tx in p_pool:
            tx.reconciliation_status = ReconciliationStatus.EXCEPTION
            amt = to_decimal(tx.amount)
            severity = ExceptionSeverity.HIGH if amt >= Decimal("500.00") else ExceptionSeverity.MEDIUM
            case_no = f"EX-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            ex_case = ExceptionCase(
                organization_id=organization_id,
                session_id=session.id,
                transaction_id=tx.id,
                case_number=case_no,
                title=f"Unmatched Ledger Transaction: {tx.description or tx.external_reference or 'Missing counter-entry'}",
                description=f"Transaction of {tx.amount} {tx.currency} recorded on {tx.transaction_date.strftime('%Y-%m-%d')} has no matching entry in secondary statement.",
                category=ExceptionCategory.MISSING_TRANSACTION,
                severity=severity,
                status=ExceptionStatus.OPEN,
                discrepancy_amount=amt,
                currency=tx.currency,
                created_by_id=user_id,
                evidence={
                    "transaction_id": tx.id,
                    "date": tx.transaction_date.isoformat(),
                    "amount": str(tx.amount),
                    "reference": tx.external_reference,
                    "side": "PRIMARY"
                }
            )
            self.db.add(ex_case)

        for tx in s_pool:
            tx.reconciliation_status = ReconciliationStatus.EXCEPTION
            amt = to_decimal(tx.amount)
            severity = ExceptionSeverity.HIGH if amt >= Decimal("500.00") else ExceptionSeverity.MEDIUM
            case_no = f"EX-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            ex_case = ExceptionCase(
                organization_id=organization_id,
                session_id=session.id,
                transaction_id=tx.id,
                case_number=case_no,
                title=f"Unmatched Provider Transaction: {tx.description or tx.external_reference or 'Unrecorded bank/mobile credit'}",
                description=f"Provider record of {tx.amount} {tx.currency} on {tx.transaction_date.strftime('%Y-%m-%d')} has no corresponding entry in primary accounts.",
                category=ExceptionCategory.MISSING_TRANSACTION,
                severity=severity,
                status=ExceptionStatus.OPEN,
                discrepancy_amount=amt,
                currency=tx.currency,
                created_by_id=user_id,
                evidence={
                    "transaction_id": tx.id,
                    "date": tx.transaction_date.isoformat(),
                    "amount": str(tx.amount),
                    "reference": tx.external_reference,
                    "side": "SECONDARY"
                }
            )
            self.db.add(ex_case)

        # Log audit event
        log_audit_event(
            db=self.db,
            organization_id=organization_id,
            action="RUN_RECONCILIATION_ENGINE",
            resource_type="RECONCILIATION_SESSION",
            resource_id=session.id,
            user_id=user_id,
            details={
                "session_name": session.session_name,
                "matches_found": len(all_matches),
                "matched_amount": str(matched_volume),
                "unmatched_primary": len(p_pool),
                "unmatched_secondary": len(s_pool)
            }
        )

        self.db.commit()
        self.db.refresh(session)
        return session
