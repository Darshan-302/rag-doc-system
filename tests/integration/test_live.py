"""Tests against live Weaviate and Ollama. Run: RUN_LIVE_TESTS=1 pytest -m live"""

import uuid

import pytest

from src.rag.embeddings import OllamaEmbedder
from src.search.hybrid import Retriever
from src.search.vector_store import ChunkRecord, WeaviateVectorStore

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_weaviate_multitenant_roundtrip():
    from src.rag.embeddings import HashingEmbedder

    emb = HashingEmbedder()
    store = WeaviateVectorStore(collection="LiveTestChunk" + uuid.uuid4().hex[:6])
    ta, tb = "live-a", "live-b"
    try:
        texts = ["green tea steeps three minutes", "rockets reach orbit"]
        vecs = await emb.embed_documents(texts)
        await store.add_chunks(ta, [ChunkRecord("d1", i, t, "f.txt", v, {"upload_date": "x", "file_size_bytes": 5})
                                    for i, (t, v) in enumerate(zip(texts, vecs))])
        hits = await store.search(ta, await emb.embed_query("tea"), 1)
        assert hits[0].document_id == "d1" and hits[0].score > 0
        assert await store.search(tb, await emb.embed_query("tea"), 3) == []
        assert (await store.list_documents(ta))[0].chunk_count == 2
        assert await store.delete_document(ta, "d1") == 2
        assert await store.list_documents(ta) == []
    finally:
        if store._client is not None:
            store._client.collections.delete(store.collection_name)
        await store.close()


@pytest.mark.asyncio
async def test_ollama_embeddings_hybrid():
    emb = OllamaEmbedder()
    vecs = await emb.embed_documents(["hello world"])
    assert len(vecs[0]) > 100
