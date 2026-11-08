import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class UserRole(str, enum.Enum):
    OWNER = "owner"
    FINANCE_MANAGER = "finance_manager"
    ACCOUNTANT = "accountant"
    BRANCH_MANAGER = "branch_manager"
    OPERATOR = "operator"
    AUDITOR = "auditor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.ACCOUNTANT, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    branch = relationship("Branch", back_populates="users")
    created_batches = relationship("ImportBatch", back_populates="created_by")
    assigned_exceptions = relationship("ExceptionCase", foreign_keys="ExceptionCase.assigned_to_id", back_populates="assigned_to")
    approved_sessions = relationship("ReconciliationSession", foreign_keys="ReconciliationSession.approved_by_id", back_populates="approved_by")
