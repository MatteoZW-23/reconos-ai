from typing import Optional
from sqlalchemy.orm import Session
from datetime import timedelta
from decimal import Decimal

from app.models.transaction import NormalizedTransaction, ReconciliationStatus
from app.models.exception_case import ExceptionCase
from app.schemas.ai import InvestigationExplanationResponse

class DiscrepancyExplainer:
    @staticmethod
    def explain_unmatched_transaction(
        db: Session,
        transaction_id: str,
        organization_id: str
    ) -> InvestigationExplanationResponse:
        tx = db.query(NormalizedTransaction).filter(
            NormalizedTransaction.id == transaction_id,
            NormalizedTransaction.organization_id == organization_id
        ).first()

        if not tx:
            raise ValueError("Transaction not found")

        amt_str = f"{tx.amount:,.2f} {tx.currency}"
        date_str = tx.transaction_date.strftime("%Y-%m-%d %H:%M")
        evidence = [
            f"Recorded transaction ID: {tx.id}",
            f"Value: {amt_str} on {date_str}",
            f"Type: {tx.transaction_type.value}",
            f"Reference: {tx.external_reference or 'None provided'}",
            f"Description: {tx.description or 'None provided'}"
        ]

        # Look for potential near-matches in the opposite side or different accounts
        potential_near_matches = db.query(NormalizedTransaction).filter(
            NormalizedTransaction.organization_id == organization_id,
            NormalizedTransaction.id != tx.id,
            NormalizedTransaction.financial_account_id != tx.financial_account_id,
            NormalizedTransaction.currency == tx.currency,
            NormalizedTransaction.transaction_type == tx.transaction_type,
            NormalizedTransaction.is_duplicate == False,
            NormalizedTransaction.transaction_date >= tx.transaction_date - timedelta(days=5),
            NormalizedTransaction.transaction_date <= tx.transaction_date + timedelta(days=5),
            NormalizedTransaction.reconciliation_status != ReconciliationStatus.MATCHED
        ).all()

        similar_amount_candidates = [
            c for c in potential_near_matches
            if abs(c.amount - tx.amount) < Decimal("5.00")
        ]

        if similar_amount_candidates:
            cand = similar_amount_candidates[0]
            time_diff = abs((cand.transaction_date - tx.transaction_date).days)
            amt_diff = abs(cand.amount - tx.amount)
            root_cause = "Possible corresponding record; cause unverified"
            explanation = (
                f"Transaction {tx.internal_reference or tx.id[:8]} for {amt_str} remains unmatched. "
                f"A possible candidate of {cand.amount} {cand.currency} was located on {cand.transaction_date.strftime('%Y-%m-%d')} "
                f"(difference of {amt_diff:.2f} {tx.currency}, {time_diff} days offset). "
                f"The relationship and reason for any difference require review."
            )
            evidence.append(f"Near candidate detected: ID {cand.id[:8]} with amount {cand.amount} {cand.currency} on {cand.transaction_date.strftime('%Y-%m-%d')}")
            action = f"Review candidate record {cand.id[:8]} in the Reconciliation Workspace and verify whether the difference ({amt_diff:.2f} {tx.currency}) corresponds to a provider fee or tariff."
            confidence = None  # No calibrated probability is available.
        elif tx.is_duplicate:
            root_cause = "Duplicate Transaction or Double-Entry Submission"
            explanation = (
                f"This transaction shares identical attributes (reference, amount, and timestamp) with another transaction in the system. "
                f"It was flagged as a duplicate entry to prevent double-counting in accounting ledgers."
            )
            evidence.append(f"Original transaction ID: {tx.duplicate_of_id}")
            action = "Confirm with operations staff whether this transaction was submitted twice in error or represents two separate real transfers."
            confidence = None
        else:
            root_cause = "Missing Source Statement Entry or Unsettled Transfer"
            explanation = (
                f"No comparable candidate was found in the imported records within ±5 days. "
                f"The cause and completeness of provider statements have not been established."
            )
            action = "Request an official bank/provider statement covering the target date range and confirm customer proof of payment."
            confidence = None

        return InvestigationExplanationResponse(
            transaction_id=tx.id,
            amount=amt_str,
            reference=tx.external_reference,
            date=date_str,
            plain_language_explanation=explanation,
            root_cause_hypothesis=root_cause,
            evidence_points=evidence,
            suggested_investigator_action=action,
            confidence=confidence
        )
