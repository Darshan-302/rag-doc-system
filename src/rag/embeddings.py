"""Embedders: Ollama (real) and a deterministic offline hashing embedder."""

import hashlib
import math
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from src.config import settings
from src.search.text import tokenize


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be produced (service down, bad response)."""


class Embedder(ABC):
    """Turns text into dense vectors."""

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed passages to be indexed."""

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embed a search query."""

    async def aclose(self) -> None:  # pragma: no cover - default no-op
        return None


class OllamaEmbedder(Embedder):
    """Embeddings via Ollama's ``/api/embed`` endpoint, batched."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: Optional[int] = None,
        timeout: float = 60.0,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.EMBEDDING_MODEL
        self.batch_size = max(1, batch_size or settings.EMBEDDING_BATCH_SIZE)
        self.timeout = timeout
        self._client = client or httpx.AsyncClient()
        # nomic-embed-text was trained with task prefixes.
        nomic = "nomic" in self.model.lower()
        self._doc_prefix = "search_document: " if nomic else ""
        self._query_prefix = "search_query: " if nomic else ""

    async def _embed_batch(self, batch: List[str]) -> List[List[float]]:
        try:
            resp = await self._client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": batch},
                timeout=self.timeout,
            )
        except httpx.HTTPError as e:
            raise EmbeddingError(f"Cannot reach Ollama at {self.base_url}: {e}") from e
        if resp.status_code != 200:
            raise EmbeddingError(f"Ollama /api/embed returned {resp.status_code}: {resp.text[:200]}")
        embeddings = resp.json().get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(batch):
            raise EmbeddingError("Ollama /api/embed returned an unexpected number of embeddings")
        return embeddings

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        out: List[List[float]] = []
        prefixed = [self._doc_prefix + t for t in texts]
        for i in range(0, len(prefixed), self.batch_size):
            out.extend(await self._embed_batch(prefixed[i : i + self.batch_size]))
        return out

    async def embed_query(self, text: str) -> List[float]:
        return (await self._embed_batch([self._query_prefix + text]))[0]

    async def aclose(self) -> None:
        await self._client.aclose()


class HashingEmbedder(Embedder):
    """Deterministic, network-free feature-hashing embedder.

    Hashes unigrams and bigrams into a fixed-size signed bag-of-words vector
    (sublinear tf, L2-normalised). It is lexical, not semantic, but is stable
    across processes and platforms, which makes tests and CI reproducible.
    """

    def __init__(self, dim: int = 512):
        if dim < 8:
            raise ValueError("dim must be >= 8")
        self.dim = dim

    def _embed(self, text: str) -> List[float]:
        tokens = tokenize(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        counts = {}
        for f in features:
            counts[f] = counts.get(f, 0) + 1
        vec = [0.0] * self.dim
        for feat, n in counts.items():
            h = int.from_bytes(hashlib.blake2b(feat.encode(), digest_size=8).digest(), "big")
            sign = 1.0 if (h >> 63) & 1 else -1.0
            weight = 1.0 + math.log(n)
            if "_" in feat:
                weight *= 0.5
            vec[h % self.dim] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    async def embed_query(self, text: str) -> List[float]:
        return self._embed(text)
