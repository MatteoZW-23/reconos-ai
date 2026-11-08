import uuid
from datetime import datetime
import enum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Date
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ShiftStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"
    DISCREPANCY_FLAGGED = "DISCREPANCY_FLAGGED"

class ShiftSummary(Base):
    __tablename__ = "shift_summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    cashier_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cashier_name = Column(String(255), nullable=False)

    shift_date = Column(Date, nullable=False)
    shift_number = Column(String(50), nullable=False)

    opening_cash = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    cash_sales = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    mobile_money_sales = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    card_sales = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    cash_payouts = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    closing_cash_counted = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    system_expected_cash = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    cash_discrepancy = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)

    status = Column(Enum(ShiftStatus), default=ShiftStatus.SUBMITTED, nullable=False)
    supervisor_notes = Column(String(500), nullable=True)
    verified_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    branch = relationship("Branch", back_populates="shift_summaries")
