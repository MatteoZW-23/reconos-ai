from pydantic import BaseModel, Field
from typing import Optional, Any
from decimal import Decimal
from datetime import datetime
from app.models.transaction import TransactionType, ReconciliationStatus

class TransactionCreate(BaseModel):
    financial_account_id: str
    branch_id: Optional[str] = None
    transaction_date: datetime
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    currency: str = "USD"
    transaction_type: TransactionType
    fee_amount: Decimal = Field(default=Decimal("0.0000"), ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    external_reference: Optional[str] = None
    internal_reference: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    description: Optional[str] = None

class TransactionResponse(BaseModel):
    id: str
    organization_id: str
    batch_id: str
    financial_account_id: str
    branch_id: Optional[str] = None
    external_reference: Optional[str] = None
    internal_reference: Optional[str] = None
    transaction_date: datetime
    amount: Decimal
    currency: str
    transaction_type: TransactionType
    fee_amount: Decimal
    balance_after: Optional[Decimal] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    description: Optional[str] = None
    reconciliation_status: ReconciliationStatus
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    anomaly_score: float
    anomaly_flag: bool
    anomaly_reasons: Optional[list[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionFilter(BaseModel):
    account_id: Optional[str] = None
    branch_id: Optional[str] = None
    status: Optional[ReconciliationStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    is_duplicate: Optional[bool] = None
    anomaly_flag: Optional[bool] = None
    search: Optional[str] = None
