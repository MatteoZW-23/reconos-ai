import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class IngestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    NORMALIZED = "NORMALIZED"
    FAILED = "FAILED"

class FileType(str, enum.Enum):
    CSV = "CSV"
    XLSX = "XLSX"
    MANUAL = "MANUAL"

class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_account_id = Column(String(36), ForeignKey("financial_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for duplicate file detection
    file_type = Column(Enum(FileType), default=FileType.CSV, nullable=False)
    status = Column(Enum(IngestionStatus), default=IngestionStatus.PENDING, nullable=False)
    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    error_rows = Column(Integer, default=0, nullable=False)
    column_mapping = Column(JSON, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="import_batches")
    financial_account = relationship("FinancialAccount", back_populates="import_batches")
    created_by = relationship("User", back_populates="created_batches")
    raw_transactions = relationship("RawTransaction", back_populates="batch", cascade="all, delete-orphan")
    normalized_transactions = relationship("NormalizedTransaction", back_populates="batch", cascade="all, delete-orphan")


class RawTransaction(Base):
    __tablename__ = "raw_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(String(36), ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("ImportBatch", back_populates="raw_transactions")
