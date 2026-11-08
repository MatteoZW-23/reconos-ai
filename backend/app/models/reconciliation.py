import uuid
from datetime import datetime
import enum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Integer, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class SessionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    APPROVED = "APPROVED"

class MatchType(str, enum.Enum):
    EXACT_REFERENCE = "EXACT_REFERENCE"
    AMOUNT_DATE_TOLERANCE = "AMOUNT_DATE_TOLERANCE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

class MatchStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"

class ParticipantSide(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"

class ReconciliationSession(Base):
    __tablename__ = "reconciliation_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    session_name = Column(String(255), nullable=False)
    primary_account_id = Column(String(36), ForeignKey("financial_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    secondary_account_id = Column(String(36), ForeignKey("financial_accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    date_from = Column(DateTime, nullable=False)
    date_to = Column(DateTime, nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.DRAFT, nullable=False)

    total_primary_count = Column(Integer, default=0, nullable=False)
    total_secondary_count = Column(Integer, default=0, nullable=False)
    total_primary_amount = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    total_secondary_amount = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    matched_count = Column(Integer, default=0, nullable=False)
    matched_amount = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    discrepancy_amount = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    rule_config = Column(JSON, nullable=True)

    initiated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="reconciliation_sessions")
    primary_account = relationship("FinancialAccount", foreign_keys=[primary_account_id])
    secondary_account = relationship("FinancialAccount", foreign_keys=[secondary_account_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id], back_populates="approved_sessions")
    matches = relationship("ReconciliationMatch", back_populates="session", cascade="all, delete-orphan")
    exceptions = relationship("ExceptionCase", back_populates="session", cascade="all, delete-orphan")


class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("reconciliation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    match_type = Column(Enum(MatchType), nullable=False)
    confidence_score = Column(Numeric(5, 2), default=Decimal("100.00"), nullable=False)
    status = Column(Enum(MatchStatus), default=MatchStatus.CONFIRMED, nullable=False)

    primary_amount_total = Column(Numeric(18, 4), nullable=False)
    secondary_amount_total = Column(Numeric(18, 4), nullable=False)
    difference_amount = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    notes = Column(String(500), nullable=True)
    matched_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ReconciliationSession", back_populates="matches")
    participants = relationship("MatchParticipant", back_populates="match", cascade="all, delete-orphan")


class MatchParticipant(Base):
    __tablename__ = "match_participants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    match_id = Column(String(36), ForeignKey("reconciliation_matches.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("normalized_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    side = Column(Enum(ParticipantSide), nullable=False)
    allocated_amount = Column(Numeric(18, 4), nullable=False)

    match = relationship("ReconciliationMatch", back_populates="participants")
    transaction = relationship("NormalizedTransaction", back_populates="match_participants")
