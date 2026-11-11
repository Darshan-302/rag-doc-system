"""Tests for src/rag/embeddings.py."""

import math

import httpx
import pytest

from src.rag.embeddings import EmbeddingError, HashingEmbedder, OllamaEmbedder


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


@pytest.mark.asyncio
async def test_hashing_is_deterministic_and_normalised():
    e = HashingEmbedder(dim=128)
    a = await e.embed_query("The quick brown fox")
    b = await e.embed_query("The quick brown fox")
    assert a == b and len(a) == 128
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, rel_tol=1e-9)


@pytest.mark.asyncio
async def test_hashing_similar_text_scores_higher():
    e = HashingEmbedder()
    q, close, far = await e.embed_documents(
        ["refund policy for gadgets", "gadgets refund policy details", "orchid watering schedule"]
    )
    assert cos(q, close) > cos(q, far)


@pytest.mark.asyncio
async def test_hashing_empty_text_is_zero_vector():
    assert not any(await HashingEmbedder(dim=16).embed_query("!!!"))


def test_hashing_rejects_tiny_dim():
    with pytest.raises(ValueError):
        HashingEmbedder(dim=2)


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_ollama_batches_requests():
    calls = []

    def handler(request):
        import json

        body = json.loads(request.content)
        calls.append(body)
        return httpx.Response(200, json={"embeddings": [[1.0, 0.0] for _ in body["input"]]})

    e = OllamaEmbedder(base_url="http://x", model="m", batch_size=2, client=_client(handler))
    out = await e.embed_documents(["a", "b", "c", "d", "e"])
    assert len(out) == 5
    assert [len(c["input"]) for c in calls] == [2, 2, 1]
    assert calls[0]["model"] == "m"


@pytest.mark.asyncio
async def test_ollama_nomic_prefixes():
    seen = []

    def handler(request):
        import json

        seen.append(json.loads(request.content)["input"])
        return httpx.Response(200, json={"embeddings": [[0.1]]})

    e = OllamaEmbedder(base_url="http://x", model="nomic-embed-text:latest", client=_client(handler))
    await e.embed_query("hi")
    await e.embed_documents(["doc"])
    assert seen == [["search_query: hi"], ["search_document: doc"]]


@pytest.mark.asyncio
async def test_ollama_http_error_raises_embedding_error():
    e = OllamaEmbedder(base_url="http://x", client=_client(lambda r: httpx.Response(500, text="boom")))
    with pytest.raises(EmbeddingError):
        await e.embed_query("q")


@pytest.mark.asyncio
async def test_ollama_unreachable_raises_embedding_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    e = OllamaEmbedder(base_url="http://x", client=_client(handler))
    with pytest.raises(EmbeddingError):
        await e.embed_query("q")


@pytest.mark.asyncio
async def test_ollama_count_mismatch_raises():
    e = OllamaEmbedder(base_url="http://x", client=_client(lambda r: httpx.Response(200, json={"embeddings": []})))
    with pytest.raises(EmbeddingError):
        await e.embed_query("q")
