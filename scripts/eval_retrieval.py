#!/usr/bin/env python3
"""Retrieval-quality eval: hit@k and MRR for keyword vs vector vs hybrid.

Indexes the synthetic corpus in tests/eval/corpus (one document per .txt file,
document id = file stem) into an in-memory store, then runs every question in
tests/eval/questions.json in each retrieval mode.

Offline by default (deterministic HashingEmbedder, no network). Pass
``--ollama`` to use real embeddings from OLLAMA_BASE_URL / EMBEDDING_MODEL.

    PYTHONPATH=. python scripts/eval_retrieval.py
    PYTHONPATH=. python scripts/eval_retrieval.py --ollama --k 5
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingestion.document_processor import DocumentProcessor  # noqa: E402
from src.rag.embeddings import Embedder, HashingEmbedder, OllamaEmbedder  # noqa: E402
from src.search.hybrid import Retriever  # noqa: E402
from src.search.vector_store import ChunkRecord, InMemoryVectorStore  # noqa: E402

EVAL_DIR = ROOT / "tests" / "eval"
MODES = ("keyword", "vector", "hybrid")
TENANT = "eval"


async def build_retriever(embedder: Embedder, chunk_size: int = 60, overlap: int = 10) -> Retriever:
    store = InMemoryVectorStore()
    processor = DocumentProcessor()
    for path in sorted((EVAL_DIR / "corpus").glob("*.txt")):
        chunks = await processor.chunk_text(path.read_text(), chunk_size, overlap)
        embeddings = await embedder.embed_documents(chunks)
        await store.add_chunks(
            TENANT,
            [
                ChunkRecord(document_id=path.stem, chunk_id=i, text=t, source=path.name, embedding=e)
                for i, (t, e) in enumerate(zip(chunks, embeddings))
            ],
        )
    return Retriever(store, embedder)


async def run_eval(embedder: Embedder, k: int = 5, questions: Optional[List[dict]] = None) -> Dict[str, Dict[str, float]]:
    """Return {mode: {"hit@1": .., "hit@3": .., "hit@k": .., "mrr": ..}}."""
    questions = questions or json.loads((EVAL_DIR / "questions.json").read_text())
    retriever = await build_retriever(embedder)
    results: Dict[str, Dict[str, float]] = {}
    for mode in MODES:
        ranks = []
        for q in questions:
            # Retrieve generously, then collapse chunks to a ranked list of documents.
            hits = await retriever.retrieve(TENANT, q["question"], top_k=20, mode=mode)
            docs: List[str] = []
            for h in hits:
                if h.document_id not in docs:
                    docs.append(h.document_id)
            ranks.append(docs.index(q["expected"]) + 1 if q["expected"] in docs else None)
        n = len(ranks)
        results[mode] = {
            "hit@1": sum(1 for r in ranks if r and r <= 1) / n,
            "hit@3": sum(1 for r in ranks if r and r <= 3) / n,
            f"hit@{k}": sum(1 for r in ranks if r and r <= k) / n,
            "mrr": sum(1 / r for r in ranks if r) / n,
        }
    return results


def format_table(results: Dict[str, Dict[str, float]], n_questions: int, embedder_name: str) -> str:
    cols = list(next(iter(results.values())).keys())
    lines = [f"Embedder: {embedder_name}   questions: {n_questions}", "mode".ljust(10) + "".join(c.rjust(9) for c in cols)]
    for mode, m in results.items():
        lines.append(mode.ljust(10) + "".join(f"{m[c]:9.3f}" for c in cols))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ollama", action="store_true", help="use real Ollama embeddings instead of the offline hashing embedder")
    ap.add_argument("--k", type=int, default=5, help="k for the extra hit@k column (default 5)")
    ap.add_argument("--json", action="store_true", help="print results as JSON")
    args = ap.parse_args()

    embedder: Embedder = OllamaEmbedder() if args.ollama else HashingEmbedder()
    questions = json.loads((EVAL_DIR / "questions.json").read_text())
    results = asyncio.run(run_eval(embedder, args.k, questions))
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_table(results, len(questions), "ollama" if args.ollama else "hashing (offline)"))


if __name__ == "__main__":
    main()
