from pydantic import BaseModel
from typing import Optional, Any
from decimal import Decimal
from datetime import datetime
from app.models.exception_case import ExceptionCategory, ExceptionSeverity, ExceptionStatus

class ExceptionCreate(BaseModel):
    title: str
    description: str
    category: ExceptionCategory
    severity: ExceptionSeverity = ExceptionSeverity.MEDIUM
    discrepancy_amount: Decimal = Decimal("0.0000")
    currency: str = "USD"
    session_id: Optional[str] = None
    transaction_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None

class ExceptionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[ExceptionSeverity] = None
    status: Optional[ExceptionStatus] = None
    assigned_to_id: Optional[str] = None
    resolution_notes: Optional[str] = None

class ExceptionResponse(BaseModel):
    id: str
    organization_id: str
    session_id: Optional[str] = None
    transaction_id: Optional[str] = None
    case_number: str
    title: str
    description: str
    category: ExceptionCategory
    severity: ExceptionSeverity
    status: ExceptionStatus
    discrepancy_amount: Decimal
    currency: str
    assigned_to_id: Optional[str] = None
    created_by_id: Optional[str] = None
    ai_analysis: Optional[dict[str, Any]] = None
    evidence: Optional[dict[str, Any]] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
