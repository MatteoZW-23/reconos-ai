import io
from typing import Any
import openpyxl
import zipfile
from app.services.adapters.base import StatementAdapter

class ExcelAdapter(StatementAdapter):
    def detect_format(self, headers: list[str]) -> bool:
        return True

    def parse_file(self, content_bytes: bytes) -> tuple[list[str], list[dict[str, Any]], int]:
        stream = io.BytesIO(content_bytes)
        try:
            with zipfile.ZipFile(stream) as archive:
                if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                    raise ValueError("Workbook expands beyond the 50 MB limit")
            stream.seek(0)
            workbook = openpyxl.load_workbook(stream, data_only=False, read_only=True)
        except (zipfile.BadZipFile, OSError) as exc:
            raise ValueError("Invalid XLSX workbook") from exc
        sheet = workbook.active
        if sheet is None:
            return [], [], 0

        rows_iter = sheet.iter_rows(values_only=True)
        try:
            first_row = next(rows_iter)
        except StopIteration:
            return [], [], 0

        headers = [str(cell).strip() if cell is not None else "" for cell in first_row]
        if not headers or any(not h for h in headers) or len(set(headers)) != len(headers):
            raise ValueError("Spreadsheet headers must be non-empty and unique")

        rows = []
        for idx, row in enumerate(rows_iter):
            row_dict = {}
            has_data = False
            for h_idx, header in enumerate(headers):
                val = row[h_idx] if h_idx < len(row) else None
                if isinstance(val, str) and val.startswith("="):
                    raise ValueError("Spreadsheet formulas are not supported in statement data")
                if val is not None and str(val).strip() != "":
                    has_data = True
                row_dict[header] = str(val).strip() if val is not None else ""
            if has_data:
                row_dict["_row_number"] = idx + 2
                rows.append(row_dict)

        return headers, rows, len(rows)
