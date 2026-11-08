import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.user import User, UserRole
from app.models.transaction import NormalizedTransaction, ReconciliationStatus, TransactionType
from app.models.financial_account import FinancialAccount
from app.models.ingestion import ImportBatch, FileType, IngestionStatus
from app.schemas.transaction import TransactionResponse, TransactionCreate
from app.api.deps import get_current_user, require_roles
from app.services.audit_service import log_audit_event
from app.utils.decimal_math import to_decimal

router = APIRouter()

@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    account_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    status: Optional[ReconciliationStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_duplicate: Optional[bool] = None,
    anomaly_flag: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(default=200, le=1000),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.organization_id == current_user.organization_id
    )

    if account_id:
        query = query.filter(NormalizedTransaction.financial_account_id == account_id)
    if branch_id:
        query = query.filter(NormalizedTransaction.branch_id == branch_id)
    if status:
        query = query.filter(NormalizedTransaction.reconciliation_status == status)
    if date_from:
        query = query.filter(NormalizedTransaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(NormalizedTransaction.transaction_date <= date_to)
    if is_duplicate is not None:
        query = query.filter(NormalizedTransaction.is_duplicate == is_duplicate)
    if anomaly_flag is not None:
        query = query.filter(NormalizedTransaction.anomaly_flag == anomaly_flag)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                NormalizedTransaction.external_reference.ilike(search_filter),
                NormalizedTransaction.internal_reference.ilike(search_filter),
                NormalizedTransaction.description.ilike(search_filter),
                NormalizedTransaction.counterparty_name.ilike(search_filter)
            )
        )

    return query.order_by(NormalizedTransaction.transaction_date.desc()).offset(offset).limit(limit).all()

@router.post("", response_model=TransactionResponse)
def create_manual_transaction(
    req: TransactionCreate,
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT])),
    db: Session = Depends(get_db)
):
    account = db.query(FinancialAccount).filter(
        FinancialAccount.id == req.financial_account_id,
        FinancialAccount.organization_id == current_user.organization_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Financial account not found")
    if req.currency.upper() != account.currency:
        raise HTTPException(status_code=400, detail="Transaction currency must match the account currency")
    if req.branch_id and req.branch_id != account.branch_id:
        raise HTTPException(status_code=400, detail="Transaction branch must match the account branch")

    # Ensure a manual import batch exists or create one
    manual_batch = db.query(ImportBatch).filter(
        ImportBatch.organization_id == current_user.organization_id,
        ImportBatch.financial_account_id == req.financial_account_id,
        ImportBatch.file_type == FileType.MANUAL
    ).first()

    if not manual_batch:
        manual_batch = ImportBatch(
            organization_id=current_user.organization_id,
            financial_account_id=req.financial_account_id,
            file_name="manual_entries",
            file_hash="MANUAL_HASH_" + uuid.uuid4().hex[:12],
            file_type=FileType.MANUAL,
            status=IngestionStatus.NORMALIZED,
            total_rows=0,
            valid_rows=0,
            error_rows=0,
            created_by_id=current_user.id
        )
        db.add(manual_batch)
        db.flush()

    internal_ref = req.internal_reference or f"MAN-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    tx = NormalizedTransaction(
        organization_id=current_user.organization_id,
        batch_id=manual_batch.id,
        financial_account_id=req.financial_account_id,
        branch_id=req.branch_id or account.branch_id,
        external_reference=req.external_reference,
        internal_reference=internal_ref,
        transaction_date=req.transaction_date,
        amount=to_decimal(req.amount),
        currency=req.currency.upper(),
        transaction_type=req.transaction_type,
        fee_amount=to_decimal(req.fee_amount),
        counterparty_name=req.counterparty_name,
        counterparty_account=req.counterparty_account,
        description=req.description,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    db.add(tx)
    db.flush()
    manual_batch.valid_rows += 1
    manual_batch.total_rows += 1

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        action="MANUAL_TRANSACTION_CREATE",
        resource_type="TRANSACTION",
        resource_id=tx.id,
        user_id=current_user.id,
        details={"reference": internal_ref, "amount": str(tx.amount), "account": account.name}
    )

    db.commit()
    db.refresh(tx)
    return tx
