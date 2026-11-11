"""Tests for src/search/vector_store.py (in-memory store + Weaviate wiring)."""

import pytest

from src.search.vector_store import (
    ChunkRecord,
    InMemoryVectorStore,
    WeaviateVectorStore,
    build_vector_store,
    validate_tenant_id,
)


def rec(doc, i, emb, text="t"):
    return ChunkRecord(document_id=doc, chunk_id=i, text=text, source=f"{doc}.txt", embedding=emb,
                       metadata={"upload_date": "2026-01-01T00:00:00", "file_size_bytes": 10})


@pytest.mark.asyncio
async def test_search_orders_by_cosine():
    s = InMemoryVectorStore()
    await s.add_chunks("a", [rec("d1", 0, [1, 0]), rec("d2", 0, [0, 1]), rec("d3", 0, [0.9, 0.1])])
    hits = await s.search("a", [1, 0], top_k=2)
    assert [h.document_id for h in hits] == ["d1", "d3"]
    assert hits[0].score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_tenants_are_isolated():
    s = InMemoryVectorStore()
    await s.add_chunks("a", [rec("d1", 0, [1, 0])])
    await s.add_chunks("b", [rec("d2", 0, [1, 0])])
    assert [h.document_id for h in await s.search("b", [1, 0], 5)] == ["d2"]
    assert [c.document_id for c in await s.get_chunks("a")] == ["d1"]
    assert await s.delete_document("b", "d1") == 0
    assert len(await s.list_documents("a")) == 1


@pytest.mark.asyncio
async def test_delete_and_list_documents():
    s = InMemoryVectorStore()
    await s.add_chunks("a", [rec("d1", 0, [1, 0]), rec("d1", 1, [0, 1]), rec("d2", 0, [1, 1])])
    docs = {d.document_id: d for d in await s.list_documents("a")}
    assert docs["d1"].chunk_count == 2 and docs["d1"].file_size_bytes == 10
    assert await s.delete_document("a", "d1") == 2
    assert [d.document_id for d in await s.list_documents("a")] == ["d2"]


@pytest.mark.asyncio
async def test_missing_embedding_and_empty_tenant():
    s = InMemoryVectorStore()
    with pytest.raises(ValueError):
        await s.add_chunks("a", [ChunkRecord("d", 0, "t", "s")])
    assert await s.search("nobody", [1, 0], 3) == []


@pytest.mark.parametrize("bad", ["", "../x", "a b", "-lead", "x" * 64, "a/b"])
def test_invalid_tenant_ids_rejected(bad):
    with pytest.raises(ValueError):
        validate_tenant_id(bad)


@pytest.mark.asyncio
async def test_store_rejects_invalid_tenant():
    with pytest.raises(ValueError):
        await InMemoryVectorStore().search("../etc", [1], 1)


def test_weaviate_store_is_lazy_and_parses_config():
    s = WeaviateVectorStore(url="http://example:8080", api_key="k", grpc_port=1234, collection="C")
    assert s._client is None and s.grpc_port == 1234 and s.collection_name == "C"


def test_build_vector_store_follows_setting(monkeypatch):
    from src.config import settings

    monkeypatch.setattr(settings, "VECTOR_STORE", "memory")
    assert isinstance(build_vector_store(), InMemoryVectorStore)
    monkeypatch.setattr(settings, "VECTOR_STORE", "weaviate")
    assert isinstance(build_vector_store(), WeaviateVectorStore)
