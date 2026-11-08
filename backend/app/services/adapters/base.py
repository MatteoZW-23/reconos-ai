from abc import ABC, abstractmethod
from typing import Any
import hashlib

class StatementAdapter(ABC):
    @abstractmethod
    def parse_file(self, content_bytes: bytes) -> tuple[list[str], list[dict[str, Any]], int]:
        """
        Parses file bytes.
        Returns: (headers, sample_or_all_rows, total_row_count)
        """
        pass

    @abstractmethod
    def detect_format(self, headers: list[str]) -> bool:
        """
        Returns True if this adapter recognizes the header structure.
        """
        pass

    @staticmethod
    def compute_sha256(content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()
