"""Document ingestion: parse -> chunk -> embed -> index."""

import re
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from src.config import settings
from src.ingestion.document_processor import DocumentParseError, DocumentProcessor
from src.rag.embeddings import Embedder
from src.search.vector_store import ChunkRecord, VectorStore

_UNSAFE = re.compile(r"[^A-Za-z0-9._ -]")


def sanitize_filename(name: Optional[str]) -> str:
    """Strip any path, control or unusual characters from an uploaded filename."""
    base = (name or "").replace("\\", "/").split("/")[-1]
    base = _UNSAFE.sub("_", base).strip(" .")
    base = re.sub(r"\.{2,}", ".", base)[:120]
    return base or "document"


def document_type_from_filename(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


class DocumentIndexer:
    """Indexes uploaded files into a tenant's slice of the vector store."""

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        processor: Optional[DocumentProcessor] = None,
        on_change: Optional[Callable[[str], None]] = None,
    ):
        self.store = store
        self.embedder = embedder
        self.processor = processor or DocumentProcessor()
        self.on_change = on_change

    async def index_document(self, tenant_id: str, filename: str, data: bytes, document_type: str) -> dict:
        chunks = await self.processor.process_bytes(
            data, document_type, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP
        )
        if not chunks:
            raise DocumentParseError("No extractable text found in document")
        embeddings = await self.embedder.embed_documents(chunks)
        document_id = uuid.uuid4().hex
        meta = {
            "upload_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "file_size_bytes": len(data),
        }
        records = [
            ChunkRecord(
                document_id=document_id,
                chunk_id=i,
                text=text,
                source=filename,
                embedding=emb,
                metadata=dict(meta),
            )
            for i, (text, emb) in enumerate(zip(chunks, embeddings))
        ]
        await self.store.add_chunks(tenant_id, records)
        if self.on_change:
            self.on_change(tenant_id)
        return {
            "document_id": document_id,
            "document_name": filename,
            "chunk_count": len(records),
            "file_size_bytes": len(data),
        }

    async def delete_document(self, tenant_id: str, document_id: str) -> int:
        removed = await self.store.delete_document(tenant_id, document_id)
        if self.on_change:
            self.on_change(tenant_id)
        return removed
