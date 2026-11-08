from pydantic import BaseModel
from typing import Optional, Any, Literal
from datetime import datetime
from app.models.ingestion import IngestionStatus, FileType

class ColumnMapping(BaseModel):
    date_col: str
    amount_col: str
    reference_col: Optional[str] = None
    type_col: Optional[str] = None  # if file has DEBIT/CREDIT column
    description_col: Optional[str] = None
    fee_col: Optional[str] = None
    balance_col: Optional[str] = None
    counterparty_col: Optional[str] = None
    date_format: Optional[str] = None  # e.g., "%Y-%m-%d" or "%d/%m/%Y"
    default_type: Optional[Literal['CREDIT', 'DEBIT']] = None

class ImportPreviewResponse(BaseModel):
    file_name: str
    file_type: FileType
    file_hash: str
    is_duplicate: bool
    duplicate_message: Optional[str] = None
    headers: list[str]
    sample_rows: list[dict[str, Any]]
    total_estimated_rows: int
    detected_adapter: Optional[str] = None
    suggested_mapping: ColumnMapping

class BatchCreateRequest(BaseModel):
    account_id: str
    file_name: str
    file_hash: str
    file_type: FileType
    column_mapping: ColumnMapping
    rows_data: list[dict[str, Any]]

class BatchResponse(BaseModel):
    id: str
    organization_id: str
    financial_account_id: str
    file_name: str
    file_hash: str
    file_type: FileType
    status: IngestionStatus
    total_rows: int
    valid_rows: int
    error_rows: int
    column_mapping: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RawTransactionResponse(BaseModel):
    id: str
    batch_id: str
    row_number: int
    raw_data: dict[str, Any]
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
