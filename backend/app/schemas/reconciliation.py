from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.models.reconciliation import SessionStatus, MatchType, MatchStatus, ParticipantSide

class RuleConfig(BaseModel):
    exact_reference_match: bool = True
    date_tolerance_days: int = Field(default=2, ge=0, le=31)
    amount_tolerance_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=1, allow_inf_nan=False)
    allow_one_to_many: bool = True
    allow_many_to_one: bool = True
    max_cluster_size: int = Field(default=5, ge=2, le=5)

class SessionCreate(BaseModel):
    session_name: str
    primary_account_id: str
    secondary_account_id: str
    date_from: datetime
    date_to: datetime
    rule_config: Optional[RuleConfig] = Field(default_factory=RuleConfig)

class ParticipantDetail(BaseModel):
    id: str
    transaction_id: str
    side: ParticipantSide
    allocated_amount: Decimal
    external_reference: Optional[str] = None
    transaction_date: Optional[datetime] = None
    description: Optional[str] = None

class MatchResponse(BaseModel):
    id: str
    session_id: str
    match_type: MatchType
    confidence_score: Decimal
    status: MatchStatus
    primary_amount_total: Decimal
    secondary_amount_total: Decimal
    difference_amount: Decimal
    notes: Optional[str] = None
    created_at: datetime
    participants: list[ParticipantDetail] = []

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: str
    organization_id: str
    session_name: str
    primary_account_id: str
    secondary_account_id: str
    date_from: datetime
    date_to: datetime
    status: SessionStatus
    total_primary_count: int
    total_secondary_count: int
    total_primary_amount: Decimal
    total_secondary_amount: Decimal
    matched_count: int
    matched_amount: Decimal
    discrepancy_amount: Decimal
    reconciliation_rate: Decimal = Decimal("0.00")
    approved_by_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    matches: list[MatchResponse] = []

    class Config:
        from_attributes = True

class ManualMatchRequest(BaseModel):
    primary_transaction_ids: list[str]
    secondary_transaction_ids: list[str]
    notes: Optional[str] = None

class MatchDecisionRequest(BaseModel):
    action: str  # "CONFIRM" or "REJECT"
    notes: Optional[str] = None

class SessionApprovalRequest(BaseModel):
    notes: Optional[str] = None

class BalanceCheckResponse(BaseModel):
    account_id: str
    account_name: str
    currency: str
    opening_balance: Decimal
    total_credits: Decimal
    total_debits: Decimal
    expected_closing: Decimal
    actual_closing: Decimal
    variance: Decimal
    is_balanced: bool
    status_message: str
