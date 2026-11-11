"""Hybrid retrieval: BM25 + vector search fused with Reciprocal Rank Fusion."""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from rank_bm25 import BM25Plus

from src.config import settings
from src.rag.embeddings import Embedder, EmbeddingError
from src.search.text import tokenize
from src.search.vector_store import ChunkRecord, SearchHit, VectorStore

logger = logging.getLogger(__name__)

BM25_CACHE_TTL_SECONDS = 30.0


def reciprocal_rank_fusion(
    rankings: List[List[Tuple[str, int]]], k: int = 60
) -> Dict[Tuple[str, int], float]:
    """Fuse ranked lists of (document_id, chunk_id) keys.

    score(d) = sum over lists of 1 / (k + rank), rank starting at 1.
    """
    fused: Dict[Tuple[str, int], float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank)
    return fused


class _BM25Index:
    def __init__(self, chunks: List[ChunkRecord]):
        self.chunks = chunks
        self.tokens = [set(tokenize(c.text)) for c in chunks]
        # BM25Plus rather than Okapi: Okapi's idf goes negative on tiny/
        # per-tenant corpora where a term is in over half the chunks.
        self.bm25 = BM25Plus([tokenize(c.text) for c in chunks]) if chunks else None
        self.built_at = time.monotonic()

    def search(self, query: str, top_k: int) -> List[SearchHit]:
        q = tokenize(query)
        if not q or self.bm25 is None:
            return []
        qset = set(q)
        scores = self.bm25.get_scores(q)
        # BM25Plus adds a delta even for absent terms; only chunks that
        # actually contain a query term are candidates.
        ranked = sorted(
            (i for i, toks in enumerate(self.tokens) if toks & qset),
            key=lambda i: -scores[i],
        )[:top_k]
        return [
            SearchHit(
                document_id=self.chunks[i].document_id,
                chunk_id=self.chunks[i].chunk_id,
                text=self.chunks[i].text,
                source=self.chunks[i].source,
                score=float(scores[i]),
                metadata=dict(self.chunks[i].metadata),
            )
            for i in ranked
        ]


class Retriever:
    """Tenant-scoped retrieval in keyword, vector or hybrid mode.

    Returned scores are normalised to [0, 1]:
      * keyword: BM25 score / best BM25 score in the result list
      * vector:  cosine similarity (clamped at 0)
      * hybrid:  RRF score / maximum attainable RRF score (rank 1 in both lists)
    """

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        mode: Optional[str] = None,
        rrf_k: Optional[int] = None,
    ):
        self.store = store
        self.embedder = embedder
        self.mode = mode or settings.RETRIEVAL_MODE
        self.rrf_k = rrf_k or settings.RRF_K
        self._bm25: Dict[str, _BM25Index] = {}

    def invalidate(self, tenant_id: str) -> None:
        """Drop the cached BM25 index after a tenant's documents change."""
        self._bm25.pop(tenant_id, None)

    async def _bm25_index(self, tenant_id: str) -> _BM25Index:
        idx = self._bm25.get(tenant_id)
        if idx is None or time.monotonic() - idx.built_at > BM25_CACHE_TTL_SECONDS:
            idx = _BM25Index(await self.store.get_chunks(tenant_id))
            self._bm25[tenant_id] = idx
        return idx

    async def _keyword(self, tenant_id: str, query: str, n: int) -> List[SearchHit]:
        return (await self._bm25_index(tenant_id)).search(query, n)

    async def _vector(self, tenant_id: str, query: str, n: int) -> List[SearchHit]:
        embedding = await self.embedder.embed_query(query)
        return await self.store.search(tenant_id, embedding, n)

    async def retrieve(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        mode: Optional[str] = None,
    ) -> List[SearchHit]:
        """Top-k chunks for the tenant. Raises if the store is unreachable."""
        mode = mode or self.mode
        pool = max(top_k * 4, 20)

        if mode == "keyword":
            hits = await self._keyword(tenant_id, query, top_k)
            best = max((h.score for h in hits), default=0.0)
            for h in hits:
                h.score = h.score / best if best > 0 else 0.0
            return hits

        if mode == "vector":
            hits = await self._vector(tenant_id, query, top_k)
            for h in hits:
                h.score = max(0.0, h.score)
            return hits

        # hybrid
        keyword_hits = await self._keyword(tenant_id, query, pool)
        try:
            vector_hits = await self._vector(tenant_id, query, pool)
        except EmbeddingError as e:
            logger.warning("Embedding unavailable (%s); hybrid retrieval degrading to BM25 only", e)
            vector_hits = []
        by_key: Dict[Tuple[str, int], SearchHit] = {}
        for h in keyword_hits + vector_hits:
            by_key.setdefault((h.document_id, h.chunk_id), h)
        lists = [l for l in ([(h.document_id, h.chunk_id) for h in keyword_hits],
                             [(h.document_id, h.chunk_id) for h in vector_hits]) if l]
        fused = reciprocal_rank_fusion(lists, self.rrf_k)
        max_score = len(lists) / (self.rrf_k + 1) if lists else 1.0
        ordered = sorted(fused.items(), key=lambda kv: -kv[1])[:top_k]
        out = []
        for key, score in ordered:
            hit = by_key[key]
            hit.score = score / max_score
            out.append(hit)
        return out


def build_retriever(store: Optional[VectorStore] = None, embedder: Optional[Embedder] = None) -> Retriever:
    """Retriever wired from settings (VECTOR_STORE, EMBEDDER, RETRIEVAL_MODE)."""
    from src.rag.embeddings import HashingEmbedder, OllamaEmbedder
    from src.search.vector_store import build_vector_store

    if embedder is None:
        embedder = HashingEmbedder() if settings.EMBEDDER == "hashing" else OllamaEmbedder()
    return Retriever(store or build_vector_store(), embedder)
