from datetime import datetime
from typing import Any, Optional
import hashlib
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from dateutil import parser as date_parser

from app.models.ingestion import ImportBatch, RawTransaction, IngestionStatus, FileType
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus
from app.models.financial_account import FinancialAccount
from app.models.organization import Organization
from app.schemas.ingestion import ColumnMapping, ImportPreviewResponse
from app.services.adapters.csv_adapter import CsvAdapter
from app.services.adapters.excel_adapter import ExcelAdapter
from app.services.adapters.ecocash_adapter import EcoCashAdapter
from app.services.adapters.bank_adapter import BankStatementAdapter
from app.services.audit_service import log_audit_event
from app.utils.decimal_math import to_decimal

def parse_statement_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value.replace(",", "").replace("$", "").strip())
        if not amount.is_finite() or amount.as_tuple().exponent < -4 or abs(amount) >= Decimal("100000000000000"):
            raise ValueError("Amount is outside supported precision or range")
        return amount
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid monetary amount")

class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.csv_adapter = CsvAdapter()
        self.excel_adapter = ExcelAdapter()
        self.ecocash_adapter = EcoCashAdapter()
        self.bank_adapter = BankStatementAdapter()

    def generate_preview(
        self,
        file_bytes: bytes,
        filename: str,
        organization_id: str,
        account_id: Optional[str] = None
    ) -> ImportPreviewResponse:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Check duplicate file
        existing_batch = self.db.query(ImportBatch).filter(
            ImportBatch.organization_id == organization_id,
            ImportBatch.file_hash == file_hash
        ).first()

        is_duplicate = existing_batch is not None
        duplicate_message = f"Warning: This exact file was already imported in batch #{existing_batch.id[:8]} on {existing_batch.created_at.strftime('%Y-%m-%d %H:%M')}" if is_duplicate else None

        # Determine file type
        file_type = FileType.XLSX if filename.lower().endswith(".xlsx") else FileType.CSV

        if file_type == FileType.XLSX:
            headers, rows, total_rows = self.excel_adapter.parse_file(file_bytes)
        else:
            headers, rows, total_rows = self.csv_adapter.parse_file(file_bytes)

        # Detect adapter type and mapping
        detected_adapter = "Generic"
        if self.ecocash_adapter.detect_format(headers):
            detected_adapter = "Mobile Money (EcoCash/M-Pesa)"
            suggested_mapping = self.ecocash_adapter.get_suggested_mapping(headers)
        elif self.bank_adapter.detect_format(headers):
            detected_adapter = "Bank Statement"
            suggested_mapping = self.bank_adapter.get_suggested_mapping(headers)
        else:
            # Fallback simple mapping
            date_col = next((h for h in headers if "date" in h.lower()), headers[0] if headers else "date")
            amount_col = next((h for h in headers if "amount" in h.lower()), headers[1] if len(headers) > 1 else headers[0])
            ref_col = next((h for h in headers if "ref" in h.lower() or "id" in h.lower()), None)
            type_col = next((h for h in headers if "type" in h.lower()), None)
            desc_col = next((h for h in headers if "desc" in h.lower() or "narrative" in h.lower()), None)
            suggested_mapping = ColumnMapping(
                date_col=date_col,
                amount_col=amount_col,
                reference_col=ref_col,
                type_col=type_col,
                description_col=desc_col,
                default_type="CREDIT"
            )

        return ImportPreviewResponse(
            file_name=filename,
            file_type=file_type,
            file_hash=file_hash,
            is_duplicate=is_duplicate,
            duplicate_message=duplicate_message,
            headers=headers,
            sample_rows=rows[:5],
            total_estimated_rows=total_rows,
            detected_adapter=detected_adapter,
            suggested_mapping=suggested_mapping
        )

    def process_import(
        self,
        file_bytes: bytes,
        filename: str,
        organization_id: str,
        account_id: str,
        column_mapping: ColumnMapping,
        user_id: Optional[str] = None
    ) -> ImportBatch:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_type = FileType.XLSX if filename.lower().endswith(".xlsx") else FileType.CSV

        account = self.db.query(FinancialAccount).filter(
            FinancialAccount.id == account_id,
            FinancialAccount.organization_id == organization_id
        ).first()
        if not account:
            raise ValueError("Financial account not found or access denied")

        # Serialize duplicate-file checks for this tenant on databases with row
        # locking; the lock is held until the import transaction commits.
        self.db.query(Organization).filter(Organization.id == organization_id).with_for_update().one()
        existing = self.db.query(ImportBatch).filter(
            ImportBatch.organization_id == organization_id,
            ImportBatch.file_hash == file_hash,
        ).first()
        if existing:
            raise ValueError("This statement file has already been imported")

        if file_type == FileType.XLSX:
            headers, rows, total_rows = self.excel_adapter.parse_file(file_bytes)
        else:
            headers, rows, total_rows = self.csv_adapter.parse_file(file_bytes)

        batch = ImportBatch(
            organization_id=organization_id,
            financial_account_id=account_id,
            file_name=filename,
            file_hash=file_hash,
            file_type=file_type,
            status=IngestionStatus.PARSING,
            total_rows=total_rows,
            valid_rows=0,
            error_rows=0,
            column_mapping=column_mapping.model_dump(),
            created_by_id=user_id
        )
        self.db.add(batch)
        self.db.flush()

        valid_count = 0
        error_count = 0

        for r in rows:
            row_num = r.get("_row_number", valid_count + error_count + 1)
            raw_tx = RawTransaction(
                organization_id=organization_id,
                batch_id=batch.id,
                row_number=row_num,
                raw_data=r
            )
            self.db.add(raw_tx)

            try:
                # Extract and parse date
                raw_date_str = str(r.get(column_mapping.date_col, "")).strip()
                if not raw_date_str:
                    raise ValueError(f"Missing date in column '{column_mapping.date_col}'")
                
                parsed_date = date_parser.parse(raw_date_str)

                # Extract and parse amount
                raw_amount_str = str(r.get(column_mapping.amount_col, "")).replace(",", "").replace("$", "").strip()
                if not raw_amount_str:
                    raise ValueError(f"Missing amount in column '{column_mapping.amount_col}'")
                
                amount_decimal = parse_statement_amount(raw_amount_str)
                is_negative = amount_decimal < Decimal("0.0000")
                amount_abs = abs(amount_decimal)

                # Determine transaction type (DEBIT or CREDIT)
                tx_type = TransactionType.CREDIT
                if column_mapping.type_col and r.get(column_mapping.type_col):
                    val = str(r[column_mapping.type_col]).upper().strip()
                    if val in {"DEBIT", "DR", "PAYMENT", "OUT", "WITHDRAWAL", "EXPENSE", "CHARGE"}:
                        tx_type = TransactionType.DEBIT
                    elif val in {"CREDIT", "CR", "IN", "DEPOSIT", "RECEIPT"}:
                        tx_type = TransactionType.CREDIT
                    else:
                        raise ValueError("Unrecognized transaction type; use a mapped debit or credit value")
                elif is_negative:
                    tx_type = TransactionType.DEBIT
                elif column_mapping.default_type:
                    tx_type = TransactionType.DEBIT if column_mapping.default_type.upper() == "DEBIT" else TransactionType.CREDIT

                # Reference
                external_ref = None
                if column_mapping.reference_col and r.get(column_mapping.reference_col):
                    external_ref = str(r[column_mapping.reference_col]).strip()

                # Fee
                fee_decimal = Decimal("0.0000")
                if column_mapping.fee_col and r.get(column_mapping.fee_col):
                    fee_raw = str(r[column_mapping.fee_col]).replace(",", "").replace("$", "").strip()
                    fee_decimal = abs(parse_statement_amount(fee_raw))

                # Balance after
                balance_after = None
                if column_mapping.balance_col and r.get(column_mapping.balance_col):
                    bal_raw = str(r[column_mapping.balance_col]).replace(",", "").replace("$", "").strip()
                    balance_after = parse_statement_amount(bal_raw)

                # Description and Counterparty
                desc = None
                if column_mapping.description_col and r.get(column_mapping.description_col):
                    desc = str(r[column_mapping.description_col]).strip()

                counterparty = None
                if column_mapping.counterparty_col and r.get(column_mapping.counterparty_col):
                    counterparty = str(r[column_mapping.counterparty_col]).strip()

                # Duplicate detection within the same organization and account
                is_duplicate_tx = False
                duplicate_parent_id = None
                if external_ref:
                    existing_tx = self.db.query(NormalizedTransaction).filter(
                        NormalizedTransaction.organization_id == organization_id,
                        NormalizedTransaction.financial_account_id == account_id,
                        NormalizedTransaction.external_reference == external_ref,
                        NormalizedTransaction.amount == amount_abs,
                        NormalizedTransaction.transaction_date == parsed_date,
                        NormalizedTransaction.transaction_type == tx_type,
                        NormalizedTransaction.is_duplicate == False
                    ).first()
                    if existing_tx:
                        is_duplicate_tx = True
                        duplicate_parent_id = existing_tx.id

                normalized_tx = NormalizedTransaction(
                    organization_id=organization_id,
                    batch_id=batch.id,
                    financial_account_id=account_id,
                    branch_id=account.branch_id,
                    external_reference=external_ref,
                    internal_reference=f"TXN-{batch.id[:6]}-{row_num:04d}",
                    transaction_date=parsed_date,
                    amount=amount_abs,
                    currency=account.currency,
                    transaction_type=tx_type,
                    fee_amount=fee_decimal,
                    balance_after=balance_after,
                    counterparty_name=counterparty,
                    description=desc,
                    reconciliation_status=ReconciliationStatus.UNRECONCILED,
                    is_duplicate=is_duplicate_tx,
                    duplicate_of_id=duplicate_parent_id
                )
                self.db.add(normalized_tx)
                self.db.flush()
                valid_count += 1

            except Exception as e:
                raw_tx.error_message = str(e)
                error_count += 1

        batch.valid_rows = valid_count
        batch.error_rows = error_count
        batch.status = IngestionStatus.NORMALIZED if valid_count > 0 else IngestionStatus.FAILED

        # Log immutable audit event
        log_audit_event(
            db=self.db,
            organization_id=organization_id,
            action="INGEST_STATEMENT_FILE",
            resource_type="IMPORT_BATCH",
            resource_id=batch.id,
            user_id=user_id,
            details={
                "file_name": filename,
                "file_hash": file_hash,
                "total_rows": total_rows,
                "valid_rows": valid_count,
                "error_rows": error_count,
                "account_id": account_id
            }
        )

        self.db.commit()
        self.db.refresh(batch)
        return batch
