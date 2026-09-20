"""Test the external dataset ingestion script (scripts/ingest_external_dataset.py)."""

import json

from scripts.ingest_external_dataset import (
    _stringify_field,
    build_chunks,
    chunk_text,
    rows_from_local,
)


def test_chunk_text_short_text_returns_single_chunk():
    chunks = chunk_text("A short sentence.")
    assert chunks == ["A short sentence."]


def test_chunk_text_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_long_text_splits_with_overlap():
    long_text = " ".join(f"word{i}" for i in range(600))
    chunks = chunk_text(long_text, chunk_size=256, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.strip() == chunk
        assert len(chunk.split()) <= 256


def test_stringify_field_handles_plain_and_list_values():
    assert _stringify_field("hello") == "hello"
    assert _stringify_field(["a", "b", "c"]) == "a b c"
    assert _stringify_field(None) == ""


def test_build_chunks_produces_expected_schema():
    rows = iter([
        {"title": "Doc A", "body": "Some sample content about the topic."},
        {"title": "Doc B", "body": ""},  # empty text is skipped
    ])
    chunks = build_chunks(
        rows,
        text_column="body",
        title_column="title",
        source_name="unit-test-source",
        source_type="Test",
        id_prefix="t",
        limit=None,
    )
    assert len(chunks) == 1
    chunk = chunks[0]
    assert set(chunk.keys()) == {"document_id", "chunk_id", "text", "source", "source_type", "metadata"}
    assert chunk["document_id"] == "t_0"
    assert chunk["source"] == "unit-test-source"
    assert chunk["source_type"] == "Test"
    assert "Doc A" in chunk["text"]
    assert chunk["metadata"] == {"title": "Doc A"}


def test_build_chunks_respects_limit():
    rows = iter([{"body": f"content {i}"} for i in range(10)])
    chunks = build_chunks(
        rows, text_column="body", title_column=None,
        source_name="s", source_type="Test", id_prefix="t", limit=3,
    )
    doc_ids = {c["document_id"] for c in chunks}
    assert doc_ids == {"t_0", "t_1", "t_2"}


def test_rows_from_local_reads_csv(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("title,body\nDoc A,Content A\nDoc B,Content B\n")
    rows = list(rows_from_local(str(csv_path)))
    assert rows == [
        {"title": "Doc A", "body": "Content A"},
        {"title": "Doc B", "body": "Content B"},
    ]


def test_rows_from_local_reads_json_list(tmp_path):
    json_path = tmp_path / "sample.json"
    json_path.write_text(json.dumps([{"title": "Doc A", "body": "Content A"}]))
    rows = list(rows_from_local(str(json_path)))
    assert rows == [{"title": "Doc A", "body": "Content A"}]


def test_rows_from_local_reads_json_with_results_key(tmp_path):
    json_path = tmp_path / "sample.json"
    json_path.write_text(json.dumps({"results": [{"title": "Doc A", "body": "Content A"}]}))
    rows = list(rows_from_local(str(json_path)))
    assert rows == [{"title": "Doc A", "body": "Content A"}]


def test_rows_from_local_reads_jsonl(tmp_path):
    jsonl_path = tmp_path / "sample.jsonl"
    jsonl_path.write_text(
        json.dumps({"title": "Doc A", "body": "Content A"}) + "\n"
        + json.dumps({"title": "Doc B", "body": "Content B"}) + "\n"
    )
    rows = list(rows_from_local(str(jsonl_path)))
    assert len(rows) == 2
    assert rows[0]["title"] == "Doc A"


def test_ingest_local_to_jsonl_end_to_end(tmp_path, monkeypatch):
    """End-to-end: local CSV -> chunks -> appended jsonl, matching the schema
    RAGPipeline reads from data/processed/rag_training_data.jsonl."""
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("title,body\nDoc A,Some real content here.\n")

    rows = rows_from_local(str(csv_path))
    chunks = build_chunks(
        rows, text_column="body", title_column="title",
        source_name="test-corpus", source_type="Test", id_prefix="t", limit=None,
    )

    out_file = tmp_path / "rag_training_data.jsonl"
    with open(out_file, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    with open(out_file) as f:
        lines = [json.loads(line) for line in f]

    assert len(lines) == 1
    assert lines[0]["source"] == "test-corpus"
    assert "text" in lines[0] and "document_id" in lines[0]
