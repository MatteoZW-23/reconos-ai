import uuid
from datetime import datetime
import enum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AccountType(str, enum.Enum):
    BANK = "BANK"
    MOBILE_MONEY = "MOBILE_MONEY"
    POS_TERMINAL = "POS_TERMINAL"
    CASH_DRAWER = "CASH_DRAWER"
    GATEWAY = "GATEWAY"
    ERP_LEDGER = "ERP_LEDGER"

class FinancialAccount(Base):
    __tablename__ = "financial_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    provider_name = Column(String(100), nullable=False)  # e.g., Stanbic, EcoCash, Stripe, Cash Register
    account_number = Column(String(100), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    opening_balance = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    current_balance = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="financial_accounts")
    branch = relationship("Branch", back_populates="financial_accounts")
    import_batches = relationship("ImportBatch", back_populates="financial_account")
    transactions = relationship("NormalizedTransaction", back_populates="financial_account")
