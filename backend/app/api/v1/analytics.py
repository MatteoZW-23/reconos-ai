from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.financial_account import FinancialAccount
from app.models.transaction import NormalizedTransaction, ReconciliationStatus
from app.models.exception_case import ExceptionCase, ExceptionStatus
from app.models.organization import Branch, Organization
from app.models.shift import ShiftSummary
from app.api.deps import get_current_user
from app.utils.decimal_math import to_decimal

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.organization_id
    org = db.query(Organization).filter(Organization.id == org_id).one()
    currency = org.default_currency

    if current_user.role == UserRole.OPERATOR:
        shifts = db.query(ShiftSummary).filter(
            ShiftSummary.organization_id == org_id,
            ShiftSummary.cashier_id == current_user.id,
        ).order_by(ShiftSummary.shift_date.desc(), ShiftSummary.created_at.desc()).limit(10).all()
        return {
            "scope": "employee", "role": current_user.role.value,
            "shifts": [{"id": s.id, "date": s.shift_date.isoformat(), "shift_number": s.shift_number,
                        "status": s.status.value, "cash_discrepancy": str(s.cash_discrepancy),
                        "supervisor_notes": s.supervisor_notes} for s in shifts],
            "notice": "Shift currency is not recorded; discrepancies are shown without a currency."
        }

    branch_scoped = current_user.role == UserRole.BRANCH_MANAGER
    if branch_scoped:
        branch = db.query(Branch).filter(Branch.id == current_user.branch_id,
            Branch.organization_id == org_id, Branch.is_active == True).first()
        if branch is None:
            raise HTTPException(status_code=403, detail="An active branch assignment is required")

    # Financial Accounts & Balances
    accounts_query = db.query(FinancialAccount).filter(
        FinancialAccount.organization_id == org_id,
        FinancialAccount.is_active == True
    )
    if branch_scoped:
        accounts_query = accounts_query.filter(FinancialAccount.branch_id == branch.id)
    accounts = accounts_query.all()

    account_summaries = []
    total_balance = Decimal("0.0000")
    for a in accounts:
        bal = to_decimal(a.current_balance)
        if a.currency == currency:
            total_balance += bal
        account_summaries.append({
            "id": a.id,
            "name": a.name,
            "provider": a.provider_name,
            "type": a.account_type.value,
            "account_number": a.account_number,
            "currency": a.currency,
            "balance": str(bal),
            "last_synced": None,
            "is_live_feed": False  # Explicitly transparent: statement-driven, not live API
        })

    # Transactions & Reconciliation
    txs_query = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.organization_id == org_id,
        NormalizedTransaction.is_duplicate == False,
        NormalizedTransaction.currency == currency
    )
    if branch_scoped:
        txs_query = txs_query.filter(NormalizedTransaction.branch_id == branch.id,
            NormalizedTransaction.financial_account_id.in_([a.id for a in accounts]))
    txs = txs_query.all()

    total_count = len(txs)
    total_volume = sum((to_decimal(t.amount) for t in txs), Decimal("0.0000"))

    matched_txs = [t for t in txs if t.reconciliation_status == ReconciliationStatus.MATCHED]
    matched_count = len(matched_txs)
    matched_volume = sum((to_decimal(t.amount) for t in matched_txs), Decimal("0.0000"))

    unmatched_txs = [t for t in txs if t.reconciliation_status != ReconciliationStatus.MATCHED]
    unmatched_count = len(unmatched_txs)
    unmatched_volume = sum((to_decimal(t.amount) for t in unmatched_txs), Decimal("0.0000"))

    recon_rate = round(float((matched_count / total_count) * 100), 1) if total_count > 0 else 0.0

    # Exceptions
    exceptions_query = db.query(ExceptionCase).filter(
        ExceptionCase.organization_id == org_id,
        ExceptionCase.status.in_([ExceptionStatus.OPEN, ExceptionStatus.UNDER_INVESTIGATION]),
        ExceptionCase.currency == currency
    )
    if branch_scoped:
        exceptions_query = exceptions_query.join(NormalizedTransaction, ExceptionCase.transaction_id == NormalizedTransaction.id).filter(
            NormalizedTransaction.organization_id == org_id, NormalizedTransaction.branch_id == branch.id,
            NormalizedTransaction.financial_account_id.in_([a.id for a in accounts]))
    exceptions = exceptions_query.all()
    open_exception_count = len(exceptions)
    open_exception_volume = sum((to_decimal(e.discrepancy_amount) for e in exceptions), Decimal("0.0000"))

    # Branch breakdown
    branches_query = db.query(Branch).filter(
        Branch.organization_id == org_id,
        Branch.is_active == True
    )
    if branch_scoped:
        branches_query = branches_query.filter(Branch.id == branch.id)
    branches = branches_query.all()

    branch_stats = []
    for b in branches:
        b_txs = [t for t in txs if t.branch_id == b.id]
        b_count = len(b_txs)
        b_matched = sum(1 for t in b_txs if t.reconciliation_status == ReconciliationStatus.MATCHED)
        b_rate = round((b_matched / b_count * 100), 1) if b_count > 0 else 0.0
        branch_stats.append({
            "id": b.id,
            "name": b.name,
            "code": b.code,
            "total_transactions": b_count,
            "reconciliation_rate": b_rate
        })

    # Payment Channels Breakdown
    channel_stats = {}
    for t in txs:
        # Match channel by account provider
        acc = next((a for a in accounts if a.id == t.financial_account_id), None)
        ch_name = acc.provider_name if acc else "Unknown Provider"
        if ch_name not in channel_stats:
            channel_stats[ch_name] = {"count": 0, "volume": Decimal("0.0000"), "matched": 0}
        channel_stats[ch_name]["count"] += 1
        channel_stats[ch_name]["volume"] += to_decimal(t.amount)
        if t.reconciliation_status == ReconciliationStatus.MATCHED:
            channel_stats[ch_name]["matched"] += 1

    channels_list = [
        {
            "channel": k,
            "transaction_count": v["count"],
            "total_volume": str(v["volume"]),
            "match_rate": round((v["matched"] / v["count"] * 100), 1) if v["count"] > 0 else 0.0
        }
        for k, v in channel_stats.items()
    ]

    # Shift Float Discrepancy
    # Shift summaries do not yet store currency, so a monetary aggregate is unsafe.
    total_shift_variance = None

    # Trend: last 7 days volume
    today = datetime.utcnow().date()
    daily_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_txs = [t for t in txs if t.transaction_date.date() == d]
        vol = sum((to_decimal(t.amount) for t in day_txs), Decimal("0.0000"))
        daily_trend.append({
            "date": d.strftime("%b %d"),
            "volume": float(vol),
            "count": len(day_txs)
        })

    return {
        "scope": "branch" if branch_scoped else "organization",
        "role": current_user.role.value,
        "branch_name": branch.name if branch_scoped else None,
        "data_freshness": {
            "last_evaluated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "mode": "BATCH_STATEMENT_IMPORT",
            "is_demonstration_data": False
        },
        "kpis": {
            "currency": currency,
            "total_recorded_balance": str(total_balance),
            "reconciliation_rate_percent": recon_rate,
            "total_transactions": total_count,
            "total_volume": str(total_volume),
            "matched_transactions": matched_count,
            "matched_volume": str(matched_volume),
            "unmatched_transactions": unmatched_count,
            "unmatched_volume": str(unmatched_volume),
            "open_exceptions_count": open_exception_count,
            "open_exceptions_volume": str(open_exception_volume),
            "shift_float_variance_total": total_shift_variance
        },
        "accounts": account_summaries,
        "branches": branch_stats,
        "channels": channels_list,
        "daily_trend": daily_trend
    }
