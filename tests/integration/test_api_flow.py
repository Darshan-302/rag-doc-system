"""End-to-end: upload -> list -> query -> delete -> query."""

import io
import json

from tests.integration.conftest import KEY_A, hdr

TEA = b"Green tea should steep for exactly three minutes in water heated to eighty degrees. Never use boiling water."
ROCKET = b"Rockets burn liquid fuel and oxidiser to reach orbit around the planet."


def upload(client, tenant, key, name, data, **form):
    return client.post(
        f"/api/v1/{tenant}/documents/upload", headers=hdr(key), files={"file": (name, io.BytesIO(data))}, data=form
    )


def test_health_is_public(env):
    client, *_ = env
    assert client.get("/health").status_code == 200


def test_full_lifecycle(env, ollama_prompts):
    client, _, _ = env
    r = upload(client, "tenant-a", KEY_A, "tea guide.txt", TEA)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "indexed" and body["chunk_count"] == 1 and body["document_name"] == "tea guide.txt"
    tea_id = tea = body["document_id"]
    upload(client, "tenant-a", KEY_A, "rockets.txt", ROCKET)

    docs = client.get("/api/v1/tenant-a/documents", headers=hdr(KEY_A)).json()
    assert docs["total_count"] == 2
    names = {d["document_name"]: d for d in docs["documents"]}
    assert names["tea guide.txt"]["file_size_bytes"] == len(TEA) and names["tea guide.txt"]["chunk_count"] == 1

    q = client.post("/api/v1/tenant-a/query", headers=hdr(KEY_A), json={"query": "how long should green tea steep?", "top_k": 2})
    assert q.status_code == 200, q.text
    out = q.json()
    assert out["answer"] == "mocked answer"
    assert out["sources"][0]["document_id"] == tea_id
    assert out["sources"][0]["document_name"] == "tea guide.txt"
    scores = [s["score"] for s in out["sources"]]
    assert scores == sorted(scores, reverse=True) and scores[0] != 0.9
    assert "three minutes" in ollama_prompts[-1]

    d = client.delete(f"/api/v1/tenant-a/documents/{tea_id}", headers=hdr(KEY_A))
    assert d.status_code == 200 and d.json()["chunks_deleted"] == 1
    again = client.delete(f"/api/v1/tenant-a/documents/{tea_id}", headers=hdr(KEY_A))
    assert again.status_code == 404

    q2 = client.post("/api/v1/tenant-a/query", headers=hdr(KEY_A), json={"query": "how long should green tea steep?"}).json()
    assert tea_id not in [s["document_id"] for s in q2["sources"]]
    assert client.get("/api/v1/tenant-a/documents", headers=hdr(KEY_A)).json()["total_count"] == 1


def test_query_with_nothing_indexed(env):
    client, *_ = env
    out = client.post("/api/v1/tenant-a/query", headers=hdr(KEY_A), json={"query": "anything"}).json()
    assert out["sources"] == [] and out["confidence"] == 0.0


def test_pagination(env):
    client, *_ = env
    for i in range(3):
        upload(client, "tenant-a", KEY_A, f"d{i}.txt", f"document number {i}".encode())
    page = client.get("/api/v1/tenant-a/documents?skip=1&limit=1", headers=hdr(KEY_A)).json()
    assert page["total_count"] == 3 and len(page["documents"]) == 1


def test_upload_formats(env):
    client, *_ = env
    assert upload(client, "tenant-a", KEY_A, "t.csv", b"item,price\nwidget,5\n").status_code == 200
    assert upload(client, "tenant-a", KEY_A, "t.json", json.dumps({"k": "v"}).encode()).status_code == 200
    assert upload(client, "tenant-a", KEY_A, "t.txt", b"x", document_type="txt").status_code == 200


def test_upload_rejections(env, monkeypatch):
    from src.config import settings

    client, *_ = env
    assert upload(client, "tenant-a", KEY_A, "evil.exe", b"MZ").status_code == 415
    assert upload(client, "tenant-a", KEY_A, "noext", b"x").status_code == 415
    assert upload(client, "tenant-a", KEY_A, "a.txt", b"x", document_type="pdf").status_code == 415
    assert upload(client, "tenant-a", KEY_A, "empty.txt", b"").status_code == 422
    assert upload(client, "tenant-a", KEY_A, "blank.txt", b"   \n").status_code == 422
    assert upload(client, "tenant-a", KEY_A, "bad.pdf", b"not really").status_code == 422
    monkeypatch.setattr(settings, "MAX_DOCUMENT_SIZE_MB", 1)
    assert upload(client, "tenant-a", KEY_A, "big.txt", b"a " * (600 * 1024)).status_code == 413


def test_path_traversal_filename_is_sanitised(env):
    client, *_ = env
    r = upload(client, "tenant-a", KEY_A, "../../etc/passwd.txt", b"harmless")
    assert r.status_code == 200 and r.json()["document_name"] == "passwd.txt"


def test_embedding_outage_on_upload_is_503(env):
    from src.rag.embeddings import EmbeddingError

    client, pipeline, _ = env

    async def boom(texts):
        raise EmbeddingError("down")

    pipeline.retriever.embedder.embed_documents = boom
    # indexer shares the same embedder object
    assert upload(client, "tenant-a", KEY_A, "a.txt", b"hello world").status_code == 503


def test_query_falls_back_to_sample_corpus_when_store_down(env, monkeypatch, tmp_path, caplog):
    from src.config import settings

    client, pipeline, store = env
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(json.dumps({"document_id": "demo1", "chunk_id": 0, "source": "Demo",
                                  "text": "Premium is the monthly payment for insurance."}) + "\n")
    monkeypatch.setattr(settings, "SAMPLE_CORPUS_PATH", str(corpus))

    async def down(*a, **k):
        raise ConnectionError("weaviate unreachable")

    store.get_chunks = down
    store.search = down
    with caplog.at_level("WARNING"):
        out = client.post("/api/v1/tenant-a/query", headers=hdr(KEY_A), json={"query": "monthly premium payment"}).json()
    assert out["sources"][0]["document_id"] == "demo1"
    assert 0 < out["sources"][0]["score"] <= 1
    assert any("falling back" in r.message for r in caplog.records)
