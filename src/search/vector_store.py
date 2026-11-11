"""Tenant-scoped vector stores: Weaviate (native multi-tenancy) and in-memory."""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import numpy as np

from src.config import settings

logger = logging.getLogger(__name__)

TENANT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")


def validate_tenant_id(tenant_id: str) -> str:
    """Tenant ids double as Weaviate tenant names, so keep them strict."""
    if not isinstance(tenant_id, str) or not TENANT_ID_RE.match(tenant_id):
        raise ValueError(
            "tenant_id must be 1-63 chars of letters, digits, '_' or '-', starting with a letter or digit"
        )
    return tenant_id


@dataclass
class ChunkRecord:
    """A chunk to index. ``metadata`` carries document-level info (upload_date, file_size_bytes, ...)."""

    document_id: str
    chunk_id: int
    text: str
    source: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchHit:
    """A retrieved chunk with a relevance score (higher is better)."""

    document_id: str
    chunk_id: int
    text: str
    source: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSummary:
    document_id: str
    document_name: str
    upload_date: str
    chunk_count: int
    file_size_bytes: int


def _summarise(chunks: List[ChunkRecord]) -> List[DocumentSummary]:
    docs: Dict[str, DocumentSummary] = {}
    for c in chunks:
        d = docs.get(c.document_id)
        if d is None:
            docs[c.document_id] = DocumentSummary(
                document_id=c.document_id,
                document_name=c.source,
                upload_date=str(c.metadata.get("upload_date", "")),
                chunk_count=1,
                file_size_bytes=int(c.metadata.get("file_size_bytes", 0) or 0),
            )
        else:
            d.chunk_count += 1
    return sorted(docs.values(), key=lambda d: (d.upload_date, d.document_id))


class VectorStore(ABC):
    """Every operation is scoped to a tenant; a tenant can never see another's chunks."""

    @abstractmethod
    async def add_chunks(self, tenant_id: str, chunks: List[ChunkRecord]) -> int:
        """Index chunks (each must carry an embedding). Returns the number stored."""

    @abstractmethod
    async def search(self, tenant_id: str, embedding: List[float], top_k: int) -> List[SearchHit]:
        """Nearest chunks by cosine similarity, best first."""

    @abstractmethod
    async def get_chunks(self, tenant_id: str) -> List[ChunkRecord]:
        """All chunks of a tenant (used to build the BM25 index)."""

    @abstractmethod
    async def delete_document(self, tenant_id: str, document_id: str) -> int:
        """Remove every chunk of a document. Returns chunks removed."""

    @abstractmethod
    async def list_documents(self, tenant_id: str) -> List[DocumentSummary]:
        """Documents with chunk counts for a tenant."""

    async def close(self) -> None:  # pragma: no cover - default no-op
        return None


class InMemoryVectorStore(VectorStore):
    """Process-local cosine store for tests and development."""

    def __init__(self) -> None:
        self._data: Dict[str, List[ChunkRecord]] = {}

    async def add_chunks(self, tenant_id: str, chunks: List[ChunkRecord]) -> int:
        validate_tenant_id(tenant_id)
        for c in chunks:
            if c.embedding is None:
                raise ValueError("chunk is missing an embedding")
        self._data.setdefault(tenant_id, []).extend(chunks)
        return len(chunks)

    async def search(self, tenant_id: str, embedding: List[float], top_k: int) -> List[SearchHit]:
        validate_tenant_id(tenant_id)
        chunks = self._data.get(tenant_id, [])
        if not chunks:
            return []
        q = np.asarray(embedding, dtype=float)
        qn = np.linalg.norm(q)
        if qn == 0:
            return []
        mat = np.asarray([c.embedding for c in chunks], dtype=float)
        norms = np.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1.0
        sims = (mat @ q) / (norms * qn)
        order = np.argsort(-sims)[:top_k]
        return [
            SearchHit(
                document_id=chunks[i].document_id,
                chunk_id=chunks[i].chunk_id,
                text=chunks[i].text,
                source=chunks[i].source,
                score=float(sims[i]),
                metadata=dict(chunks[i].metadata),
            )
            for i in order
        ]

    async def get_chunks(self, tenant_id: str) -> List[ChunkRecord]:
        validate_tenant_id(tenant_id)
        return list(self._data.get(tenant_id, []))

    async def delete_document(self, tenant_id: str, document_id: str) -> int:
        validate_tenant_id(tenant_id)
        chunks = self._data.get(tenant_id, [])
        kept = [c for c in chunks if c.document_id != document_id]
        self._data[tenant_id] = kept
        return len(chunks) - len(kept)

    async def list_documents(self, tenant_id: str) -> List[DocumentSummary]:
        validate_tenant_id(tenant_id)
        return _summarise(self._data.get(tenant_id, []))


class WeaviateVectorStore(VectorStore):
    """Weaviate v4 store with one native Weaviate tenant per ``tenant_id``.

    The (synchronous) weaviate client is driven through ``asyncio.to_thread``
    and connected lazily, so constructing the store never touches the network.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        grpc_port: Optional[int] = None,
        collection: Optional[str] = None,
    ):
        self.url = url or settings.WEAVIATE_URL
        self.api_key = api_key if api_key is not None else settings.WEAVIATE_API_KEY
        self.grpc_port = grpc_port or settings.WEAVIATE_GRPC_PORT
        self.collection_name = collection or settings.WEAVIATE_COLLECTION
        self._client = None
        self._known_tenants: set = set()

    # -- connection -------------------------------------------------------
    def _connect(self):
        if self._client is not None:
            return self._client
        import weaviate
        from weaviate.classes.init import AdditionalConfig, Auth, Timeout

        parsed = urlparse(self.url)
        secure = parsed.scheme == "https"
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if secure else 80)
        client = weaviate.connect_to_custom(
            http_host=host,
            http_port=port,
            http_secure=secure,
            grpc_host=host,
            grpc_port=self.grpc_port,
            grpc_secure=secure,
            auth_credentials=Auth.api_key(self.api_key) if self.api_key else None,
            additional_config=AdditionalConfig(timeout=Timeout(init=5, query=15, insert=60)),
        )
        self._ensure_collection(client)
        self._client = client
        return client

    def _ensure_collection(self, client) -> None:
        from weaviate.classes.config import Configure, DataType, Property, VectorDistances

        if client.collections.exists(self.collection_name):
            return
        client.collections.create(
            self.collection_name,
            multi_tenancy_config=Configure.multi_tenancy(enabled=True),
            vectorizer_config=Configure.Vectorizer.none(),
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE),
            properties=[
                Property(name="document_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="chunk_id", data_type=DataType.INT),
                Property(name="text", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="source", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="upload_date", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="file_size_bytes", data_type=DataType.INT),
            ],
        )

    def _tenant_collection(self, tenant_id: str, create: bool):
        """Collection handle bound to the tenant. Returns None if it doesn't exist and ``create`` is False."""
        from weaviate.classes.tenants import Tenant

        validate_tenant_id(tenant_id)
        client = self._connect()
        col = client.collections.get(self.collection_name)
        if tenant_id not in self._known_tenants:
            if not col.tenants.exists(tenant_id):
                if not create:
                    return None
                col.tenants.create([Tenant(name=tenant_id)])
            self._known_tenants.add(tenant_id)
        return col.with_tenant(tenant_id)

    # -- operations (sync bodies, run in a thread) ------------------------
    def _add(self, tenant_id: str, chunks: List[ChunkRecord]) -> int:
        from weaviate.classes.data import DataObject
        from weaviate.util import generate_uuid5

        col = self._tenant_collection(tenant_id, create=True)
        objs = []
        for c in chunks:
            if c.embedding is None:
                raise ValueError("chunk is missing an embedding")
            objs.append(
                DataObject(
                    properties={
                        "document_id": c.document_id,
                        "chunk_id": c.chunk_id,
                        "text": c.text,
                        "source": c.source,
                        "upload_date": str(c.metadata.get("upload_date", "")),
                        "file_size_bytes": int(c.metadata.get("file_size_bytes", 0) or 0),
                    },
                    vector=c.embedding,
                    uuid=generate_uuid5(f"{tenant_id}:{c.document_id}:{c.chunk_id}"),
                )
            )
        res = col.data.insert_many(objs)
        if res.has_errors:
            raise RuntimeError(f"Weaviate insert failed: {list(res.errors.values())[:1]}")
        return len(objs)

    def _search(self, tenant_id: str, embedding: List[float], top_k: int) -> List[SearchHit]:
        from weaviate.classes.query import MetadataQuery

        col = self._tenant_collection(tenant_id, create=False)
        if col is None:
            return []
        res = col.query.near_vector(
            near_vector=embedding, limit=top_k, return_metadata=MetadataQuery(distance=True)
        )
        hits = []
        for o in res.objects:
            p = o.properties
            distance = o.metadata.distance if o.metadata and o.metadata.distance is not None else 1.0
            hits.append(
                SearchHit(
                    document_id=p["document_id"],
                    chunk_id=int(p["chunk_id"]),
                    text=p["text"],
                    source=p["source"],
                    score=1.0 - float(distance),  # cosine distance -> similarity
                    metadata={"upload_date": p.get("upload_date", ""), "file_size_bytes": p.get("file_size_bytes", 0)},
                )
            )
        return hits

    def _get_chunks(self, tenant_id: str) -> List[ChunkRecord]:
        col = self._tenant_collection(tenant_id, create=False)
        if col is None:
            return []
        out = []
        for o in col.iterator():
            p = o.properties
            out.append(
                ChunkRecord(
                    document_id=p["document_id"],
                    chunk_id=int(p["chunk_id"]),
                    text=p["text"],
                    source=p["source"],
                    metadata={"upload_date": p.get("upload_date", ""), "file_size_bytes": p.get("file_size_bytes", 0)},
                )
            )
        return out

    def _delete(self, tenant_id: str, document_id: str) -> int:
        from weaviate.classes.query import Filter

        col = self._tenant_collection(tenant_id, create=False)
        if col is None:
            return 0
        res = col.data.delete_many(where=Filter.by_property("document_id").equal(document_id))
        return int(res.successful)

    # -- async interface --------------------------------------------------
    async def add_chunks(self, tenant_id: str, chunks: List[ChunkRecord]) -> int:
        return await asyncio.to_thread(self._add, tenant_id, chunks)

    async def search(self, tenant_id: str, embedding: List[float], top_k: int) -> List[SearchHit]:
        return await asyncio.to_thread(self._search, tenant_id, embedding, top_k)

    async def get_chunks(self, tenant_id: str) -> List[ChunkRecord]:
        return await asyncio.to_thread(self._get_chunks, tenant_id)

    async def delete_document(self, tenant_id: str, document_id: str) -> int:
        return await asyncio.to_thread(self._delete, tenant_id, document_id)

    async def list_documents(self, tenant_id: str) -> List[DocumentSummary]:
        return _summarise(await self.get_chunks(tenant_id))

    async def close(self) -> None:
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None
            self._known_tenants.clear()


def build_vector_store() -> VectorStore:
    """Vector store selected by settings.VECTOR_STORE."""
    if settings.VECTOR_STORE == "memory":
        return InMemoryVectorStore()
    return WeaviateVectorStore()
