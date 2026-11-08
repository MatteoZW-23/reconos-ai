from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class ReportFilter(BaseModel):
    branch_id: Optional[str] = None
    account_id: Optional[str] = None
    date_from: datetime
    date_to: datetime

class DailyReconciliationSummary(BaseModel):
    report_date: str
    organization_name: str
    currency: str
    total_volume: Decimal
    total_transactions: int
    matched_count: int
    matched_volume: Decimal
    unmatched_count: int
    unmatched_volume: Decimal
    reconciliation_rate: Decimal
    open_exceptions_count: int
    open_exceptions_volume: Decimal
    branches_covered: list[str]

class BranchPerformanceItem(BaseModel):
    branch_id: str
    branch_name: str
    branch_code: str
    total_transactions: int
    total_volume: Decimal
    reconciliation_rate: Decimal
    unmatched_count: int
    shift_discrepancy_total: Decimal

class BranchPerformanceReport(BaseModel):
    period_start: str
    period_end: str
    organization_name: str
    branches: list[BranchPerformanceItem]

class AuditEventResponse(BaseModel):
    id: str
    organization_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
