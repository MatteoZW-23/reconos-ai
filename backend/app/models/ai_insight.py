import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class InsightType(str, enum.Enum):
    ANOMALY_CLUSTER = "ANOMALY_CLUSTER"
    RECURRING_LEAK = "RECURRING_LEAK"
    CASHIER_VARIANCE = "CASHIER_VARIANCE"
    VENDOR_FEE_DRIFT = "VENDOR_FEE_DRIFT"
    SETTLEMENT_LAG = "SETTLEMENT_LAG"

class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_type = Column(Enum(InsightType), nullable=False)
    severity = Column(String(20), default="MEDIUM", nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(String(1000), nullable=False)
    evidence = Column(JSON, nullable=False)  # Grounded transaction IDs, amounts, and dates
    recommendation = Column(String(1000), nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="ai_insights")
