"""The retrieval eval must stay above a sane floor (offline, HashingEmbedder)."""

import importlib.util
from pathlib import Path

import pytest

from src.rag.embeddings import HashingEmbedder

SPEC = importlib.util.spec_from_file_location(
    "eval_retrieval", Path(__file__).resolve().parents[2] / "scripts" / "eval_retrieval.py"
)
ev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ev)


@pytest.mark.asyncio
async def test_eval_set_is_big_enough():
    import json

    qs = json.loads((ev.EVAL_DIR / "questions.json").read_text())
    docs = {p.stem for p in (ev.EVAL_DIR / "corpus").glob("*.txt")}
    assert len(qs) >= 15
    assert all(q["expected"] in docs for q in qs)


@pytest.mark.asyncio
async def test_retrieval_quality_floor():
    res = await ev.run_eval(HashingEmbedder(), k=5)
    for mode in ("keyword", "vector", "hybrid"):
        assert res[mode]["hit@5"] >= 0.8, (mode, res[mode])
        assert res[mode]["mrr"] >= 0.6, (mode, res[mode])
    # hybrid must not be worse than the weaker single retriever
    assert res["hybrid"]["mrr"] >= min(res["keyword"]["mrr"], res["vector"]["mrr"])
