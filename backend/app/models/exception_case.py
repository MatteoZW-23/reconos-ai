import uuid
from datetime import datetime
import enum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ExceptionCategory(str, enum.Enum):
    MISSING_TRANSACTION = "MISSING_TRANSACTION"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    UNRECOGNIZED_FEE = "UNRECOGNIZED_FEE"
    TIMING_DELAY = "TIMING_DELAY"
    CASH_SHORTAGE = "CASH_SHORTAGE"

class ExceptionSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ExceptionStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"

class ExceptionCase(Base):
    __tablename__ = "exception_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("reconciliation_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_id = Column(String(36), ForeignKey("normalized_transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    case_number = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    category = Column(Enum(ExceptionCategory), nullable=False)
    severity = Column(Enum(ExceptionSeverity), default=ExceptionSeverity.MEDIUM, nullable=False)
    status = Column(Enum(ExceptionStatus), default=ExceptionStatus.OPEN, nullable=False)

    discrepancy_amount = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    assigned_to_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    ai_analysis = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    resolution_notes = Column(String(1000), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="exceptions")
    session = relationship("ReconciliationSession", back_populates="exceptions")
    transaction = relationship("NormalizedTransaction", back_populates="exceptions")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_exceptions")
