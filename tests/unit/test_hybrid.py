"""Tests for src/search/hybrid.py."""

import pytest

from src.rag.embeddings import EmbeddingError, HashingEmbedder
from src.search.hybrid import Retriever, reciprocal_rank_fusion
from src.search.vector_store import ChunkRecord, InMemoryVectorStore


def test_rrf_rewards_agreement():
    fused = reciprocal_rank_fusion([[("a", 0), ("b", 0)], [("b", 0), ("c", 0)]], k=60)
    assert fused[("b", 0)] > fused[("a", 0)] > fused[("c", 0)]
    assert fused[("a", 0)] == pytest.approx(1 / 61)


async def make(texts, mode="hybrid", tenant="t"):
    emb = HashingEmbedder()
    store = InMemoryVectorStore()
    vecs = await emb.embed_documents(list(texts.values()))
    await store.add_chunks(tenant, [ChunkRecord(d, 0, t, d + ".txt", v) for (d, t), v in zip(texts.items(), vecs)])
    return Retriever(store, emb, mode=mode), store


DOCS = {
    "cats": "cats purr and sleep on warm windowsills all afternoon",
    "rockets": "rockets burn liquid fuel to reach orbit around the planet",
    "tea": "green tea should steep for three minutes in hot water",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["keyword", "vector", "hybrid"])
async def test_each_mode_finds_relevant_doc(mode):
    r, _ = await make(DOCS, mode)
    hits = await r.retrieve("t", "how long to steep green tea", top_k=2)
    assert hits[0].document_id == "tea"
    assert 0.0 <= hits[0].score <= 1.0


@pytest.mark.asyncio
async def test_keyword_mode_returns_nothing_without_term_overlap():
    r, _ = await make(DOCS, "keyword")
    assert await r.retrieve("t", "zzzz qqqq", top_k=3) == []


@pytest.mark.asyncio
async def test_hybrid_scores_are_normalised_and_descending():
    r, _ = await make(DOCS)
    hits = await r.retrieve("t", "rockets reach orbit", top_k=3)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0)  # rank 1 in both lists


@pytest.mark.asyncio
async def test_retrieval_is_tenant_scoped():
    r, store = await make(DOCS, tenant="a")
    assert await r.retrieve("b", "green tea", top_k=3) == []


@pytest.mark.asyncio
async def test_hybrid_degrades_to_bm25_when_embedder_fails():
    r, _ = await make(DOCS)

    async def boom(_):
        raise EmbeddingError("down")

    r.embedder.embed_query = boom
    hits = await r.retrieve("t", "green tea", top_k=2)
    assert hits and hits[0].document_id == "tea"


@pytest.mark.asyncio
async def test_vector_mode_propagates_embedder_failure():
    r, _ = await make(DOCS, "vector")

    async def boom(_):
        raise EmbeddingError("down")

    r.embedder.embed_query = boom
    with pytest.raises(EmbeddingError):
        await r.retrieve("t", "tea", top_k=2)


@pytest.mark.asyncio
async def test_invalidate_picks_up_new_chunks():
    r, store = await make(DOCS, "keyword")
    assert await r.retrieve("t", "volcano", 3) == []
    await store.add_chunks("t", [ChunkRecord("volc", 0, "a volcano erupted", "v.txt", [1.0] + [0.0] * 511)])
    assert await r.retrieve("t", "volcano", 3) == []  # cached index
    r.invalidate("t")
    assert (await r.retrieve("t", "volcano", 3))[0].document_id == "volc"
