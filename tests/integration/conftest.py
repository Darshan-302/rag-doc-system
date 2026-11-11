"""Fixtures: FastAPI app wired to InMemoryVectorStore + HashingEmbedder + mocked Ollama."""

import httpx
import pytest
from fastapi.testclient import TestClient

from src import main
from src.config import settings
from src.rag.embeddings import HashingEmbedder
from src.rag.indexing import DocumentIndexer
from src.rag.pipeline import RAGPipeline
from src.search.hybrid import Retriever
from src.search.vector_store import InMemoryVectorStore

KEY_A = "key-for-tenant-a"
KEY_B = "key-for-tenant-b"
KEY_ADMIN = "key-for-everyone"


@pytest.fixture
def ollama_prompts():
    return []


@pytest.fixture
def env(monkeypatch, ollama_prompts):
    """Returns (TestClient, pipeline, store)."""
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEYS", f"{KEY_A}=tenant-a;{KEY_B}=tenant-b;{KEY_ADMIN}=*")
    monkeypatch.setattr(settings, "SAMPLE_CORPUS_PATH", "")

    store = InMemoryVectorStore()
    embedder = HashingEmbedder()
    retriever = Retriever(store, embedder, mode="hybrid")
    pipeline = RAGPipeline(retriever=retriever)

    def ollama(request: httpx.Request) -> httpx.Response:
        import json

        ollama_prompts.append(json.loads(request.content)["prompt"])
        return httpx.Response(200, json={"response": "mocked answer"})

    pipeline.client = httpx.AsyncClient(transport=httpx.MockTransport(ollama))

    indexer = DocumentIndexer(store, embedder, on_change=retriever.invalidate)
    main.app.dependency_overrides[main.get_pipeline] = lambda: pipeline
    main.app.dependency_overrides[main.get_indexer] = lambda: indexer
    with TestClient(main.app) as client:
        yield client, pipeline, store
    main.app.dependency_overrides.clear()


def hdr(key):
    return {"X-API-Key": key}
