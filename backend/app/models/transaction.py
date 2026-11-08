import uuid
from datetime import datetime
import enum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum, Numeric, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class TransactionType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class ReconciliationStatus(str, enum.Enum):
    UNRECONCILED = "UNRECONCILED"
    MATCHED = "MATCHED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    EXCEPTION = "EXCEPTION"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class NormalizedTransaction(Base):
    __tablename__ = "normalized_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(String(36), ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_account_id = Column(String(36), ForeignKey("financial_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)

    # Identifiers & Lineage
    external_reference = Column(String(100), nullable=True, index=True)
    internal_reference = Column(String(100), nullable=True, index=True)
    transaction_date = Column(DateTime, nullable=False, index=True)
    
    # Financial Values (18 digits, 4 decimal places for absolute financial accuracy)
    amount = Column(Numeric(18, 4), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    fee_amount = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    balance_after = Column(Numeric(18, 4), nullable=True)

    # Counterparty details
    counterparty_name = Column(String(255), nullable=True)
    counterparty_account = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)

    # Reconciliation and Duplicate Flags
    reconciliation_status = Column(Enum(ReconciliationStatus), default=ReconciliationStatus.UNRECONCILED, nullable=False, index=True)
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_of_id = Column(String(36), ForeignKey("normalized_transactions.id", ondelete="SET NULL"), nullable=True)

    # AI & Anomaly Scoring
    anomaly_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    anomaly_flag = Column(Boolean, default=False, index=True)
    anomaly_reasons = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="transactions")
    batch = relationship("ImportBatch", back_populates="normalized_transactions")
    financial_account = relationship("FinancialAccount", back_populates="transactions")
    match_participants = relationship("MatchParticipant", back_populates="transaction")
    exceptions = relationship("ExceptionCase", back_populates="transaction")
