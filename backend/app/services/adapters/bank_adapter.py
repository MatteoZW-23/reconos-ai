from typing import Any
from app.services.adapters.base import StatementAdapter
from app.schemas.ingestion import ColumnMapping

class BankStatementAdapter(StatementAdapter):
    """
    Adapter for standard banking statements (e.g. Stanbic, Standard Chartered, Nedbank, CBZ).
    Auto-detects typical headers like Date, Value Date, Reference, Description, Debit, Credit, Balance.
    """
    def detect_format(self, headers: list[str]) -> bool:
        lower_headers = [h.lower() for h in headers]
        has_debit_credit = any("debit" in h for h in lower_headers) or any("credit" in h for h in lower_headers)
        has_amount = any("amount" in h for h in lower_headers)
        has_date = any("date" in h for h in lower_headers)
        return (has_debit_credit or has_amount) and has_date

    def get_suggested_mapping(self, headers: list[str]) -> ColumnMapping:
        lower_map = {h.lower(): h for h in headers}

        date_col = next((h for l, h in lower_map.items() if "date" in l and "value" not in l), headers[0])
        ref_col = next((h for l, h in lower_map.items() if "ref" in l or "chq" in l or "cheque" in l), None)
        desc_col = next((h for l, h in lower_map.items() if "desc" in l or "narrative" in l or "details" in l or "particulars" in l), None)
        balance_col = next((h for l, h in lower_map.items() if "bal" in l), None)
        
        # Check for explicit Amount or Debit/Credit columns
        amount_col = next((h for l, h in lower_map.items() if "amount" in l), None)
        type_col = next((h for l, h in lower_map.items() if "type" in l or "dr/cr" in l or "d/c" in l), None)
        
        if not amount_col:
            # Fall back to credit or debit column if split
            amount_col = next((h for l, h in lower_map.items() if "credit" in l or "debit" in l), headers[1] if len(headers) > 1 else headers[0])

        return ColumnMapping(
            date_col=date_col,
            amount_col=amount_col,
            reference_col=ref_col,
            type_col=type_col,
            description_col=desc_col,
            balance_col=balance_col,
            default_type="CREDIT"
        )

    def parse_file(self, content_bytes: bytes) -> tuple[list[str], list[dict[str, Any]], int]:
        return [], [], 0
