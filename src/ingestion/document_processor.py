"""Multi-format document processing and chunking."""

import csv
import io
import json
import logging
import os
from typing import Any, List

logger = logging.getLogger(__name__)


class DocumentParseError(ValueError):
    """The file could not be parsed as the declared type."""


def _flatten_json(value: Any, prefix: str = "") -> List[str]:
    """Render JSON as 'path: value' lines (one line per record for lists of objects)."""
    if isinstance(value, dict):
        lines: List[str] = []
        for k, v in value.items():
            lines.extend(_flatten_json(v, f"{prefix}.{k}" if prefix else str(k)))
        return lines
    if isinstance(value, list):
        if value and all(isinstance(v, dict) and all(not isinstance(x, (dict, list)) for x in v.values()) for v in value):
            return [", ".join(f"{k}: {x}" for k, x in v.items()) for v in value]
        lines = []
        for i, v in enumerate(value):
            lines.extend(_flatten_json(v, f"{prefix}[{i}]"))
        return lines
    return [f"{prefix}: {value}" if prefix else str(value)]


class DocumentProcessor:
    """Process documents from various formats into chunks."""

    SUPPORTED_FORMATS = ["pdf", "docx", "txt", "csv", "json"]

    def extract_text(self, data: bytes, document_type: str) -> str:
        """Parse raw file bytes into plain text."""
        document_type = document_type.lower().lstrip(".")
        if document_type not in self.SUPPORTED_FORMATS:
            raise DocumentParseError(f"Unsupported document type: {document_type}")
        try:
            if document_type == "txt":
                return data.decode("utf-8", errors="replace")
            if document_type == "pdf":
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(data))
                if reader.is_encrypted:
                    raise DocumentParseError("Encrypted PDFs are not supported")
                return "\n\n".join((page.extract_text() or "") for page in reader.pages)
            if document_type == "docx":
                from docx import Document

                doc = Document(io.BytesIO(data))
                parts = [p.text for p in doc.paragraphs]
                for table in doc.tables:
                    for row in table.rows:
                        parts.append(" | ".join(cell.text for cell in row.cells))
                return "\n".join(parts)
            if document_type == "csv":
                text = data.decode("utf-8-sig", errors="replace")
                rows = list(csv.reader(io.StringIO(text)))
                if not rows:
                    return ""
                header, body = rows[0], rows[1:]
                if not body:
                    return ", ".join(header)
                return "\n".join(
                    ", ".join(f"{h}: {v}" for h, v in zip(header, row)) for row in body
                )
            # json
            return "\n".join(_flatten_json(json.loads(data.decode("utf-8-sig"))))
        except DocumentParseError:
            raise
        except Exception as e:
            raise DocumentParseError(f"Could not parse {document_type} file: {e}") from e

    async def process(
        self,
        file_path: str,
        document_type: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> List[str]:
        """
        Parse a file on disk and return text chunks.

        Args:
            file_path: Path to document file
            document_type: File format (pdf, docx, txt, csv, json)
            chunk_size: Target chunk size in tokens (approximated by words)
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)
        with open(file_path, "rb") as f:
            data = f.read()
        return await self.process_bytes(data, document_type, chunk_size, chunk_overlap)

    async def process_bytes(
        self,
        data: bytes,
        document_type: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> List[str]:
        """Parse in-memory file bytes and return text chunks."""
        text = self.extract_text(data, document_type)
        return await self.chunk_text(text, chunk_size, chunk_overlap)

    async def chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Tokens are approximated by whitespace-separated words. Each chunk has
        at most ``chunk_size`` words and starts ``chunk_size - chunk_overlap``
        words after the previous one.

        Args:
            text: Input text
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        if not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and < chunk_size")
        words = text.split()
        if not words:
            return []
        step = chunk_size - chunk_overlap
        chunks = []
        for start in range(0, len(words), step):
            chunks.append(" ".join(words[start : start + chunk_size]))
            if start + chunk_size >= len(words):
                break
        return chunks
