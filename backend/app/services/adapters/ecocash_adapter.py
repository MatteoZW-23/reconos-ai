from typing import Any
from app.services.adapters.base import StatementAdapter
from app.schemas.ingestion import ColumnMapping

class EcoCashAdapter(StatementAdapter):
    """
    Adapter for mobile money statements (EcoCash, M-Pesa, Airtel Money).
    Auto-detects typical headers like Transaction ID, Date/Time, Amount, Fee, Balance.
    """
    def detect_format(self, headers: list[str]) -> bool:
        lower_headers = [h.lower() for h in headers]
        has_id = any("trans" in h and "id" in h for h in lower_headers) or any("txnid" in h or "ref" in h for h in lower_headers)
        has_amount = any("amount" in h or "gross" in h for h in lower_headers)
        has_date = any("date" in h or "time" in h for h in lower_headers)
        return has_id and has_amount and has_date

    def get_suggested_mapping(self, headers: list[str]) -> ColumnMapping:
        lower_map = {h.lower(): h for h in headers}
        
        date_col = next((h for l, h in lower_map.items() if "date" in l or "time" in l), headers[0])
        amount_col = next((h for l, h in lower_map.items() if "amount" in l or "gross" in l), headers[1] if len(headers) > 1 else headers[0])
        ref_col = next((h for l, h in lower_map.items() if "ref" in l or "id" in l or "txn" in l), None)
        type_col = next((h for l, h in lower_map.items() if "type" in l), None)
        fee_col = next((h for l, h in lower_map.items() if "fee" in l or "charge" in l), None)
        balance_col = next((h for l, h in lower_map.items() if "balance" in l), None)
        desc_col = next((h for l, h in lower_map.items() if "subscriber" in l or "counterparty" in l or "detail" in l or "desc" in l), None)

        return ColumnMapping(
            date_col=date_col,
            amount_col=amount_col,
            reference_col=ref_col,
            type_col=type_col,
            fee_col=fee_col,
            balance_col=balance_col,
            description_col=desc_col,
            default_type=None
        )

    def parse_file(self, content_bytes: bytes) -> tuple[list[str], list[dict[str, Any]], int]:
        # Handled via base CSV / Excel parsing; this provides header pattern detection and mapping
        return [], [], 0
