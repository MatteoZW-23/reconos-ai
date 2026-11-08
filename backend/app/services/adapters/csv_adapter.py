import csv
import io
from typing import Any
from app.services.adapters.base import StatementAdapter

class CsvAdapter(StatementAdapter):
    def detect_format(self, headers: list[str]) -> bool:
        return True  # Fallback general adapter

    def parse_file(self, content_bytes: bytes) -> tuple[list[str], list[dict[str, Any]], int]:
        # Handle UTF-8 with BOM or plain utf-8 / latin-1
        try:
            text = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content_bytes.decode("latin-1")

        stream = io.StringIO(text)
        
        # Sniff delimiter
        sample_chunk = text[:4096]
        delimiter = ","
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_chunk)
            delimiter = dialect.delimiter
        except Exception:
            if ";" in sample_chunk and "," not in sample_chunk:
                delimiter = ";"
            elif "\t" in sample_chunk:
                delimiter = "\t"

        reader = csv.DictReader(stream, delimiter=delimiter)
        raw_headers = reader.fieldnames or []
        headers = [h.strip() for h in raw_headers if h and h.strip()]
        if not headers or len(headers) != len(raw_headers) or len(set(headers)) != len(headers):
            raise ValueError("Statement headers must be non-empty and unique")

        rows = []
        for idx, row in enumerate(reader):
            if None in row:
                raise ValueError(f"Row {idx + 2} has more fields than the header")
            # Clean keys and strip whitespace
            cleaned_row = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
            if any(cleaned_row.values()):
                cleaned_row["_row_number"] = idx + 2
                rows.append(cleaned_row)

        return headers, rows, len(rows)
