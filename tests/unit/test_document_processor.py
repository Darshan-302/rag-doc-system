"""Tests for DocumentProcessor parsing/chunking and indexing helpers."""

import io
import json

import pytest

from src.ingestion.document_processor import DocumentParseError, DocumentProcessor
from src.rag.embeddings import HashingEmbedder
from src.rag.indexing import DocumentIndexer, document_type_from_filename, sanitize_filename
from src.search.vector_store import InMemoryVectorStore

P = DocumentProcessor()


def test_txt_csv_json():
    assert P.extract_text(b"hello  world", "txt") == "hello  world"
    assert P.extract_text(b"name,age\nAda,36\nBo,41\n", "csv") == "name: Ada, age: 36\nname: Bo, age: 41"
    out = P.extract_text(json.dumps({"a": {"b": 1}, "rows": [{"x": 1, "y": 2}]}).encode(), "json")
    assert "a.b: 1" in out and "x: 1, y: 2" in out


def test_docx_roundtrip():
    from docx import Document

    d = Document()
    d.add_paragraph("Fictional zebra paragraph")
    buf = io.BytesIO()
    d.save(buf)
    assert "zebra" in P.extract_text(buf.getvalue(), "docx")


def test_pdf_roundtrip():
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(200, 200)
    buf = io.BytesIO()
    w.write(buf)
    assert P.extract_text(buf.getvalue(), "pdf").strip() == ""  # parses; blank page has no text


@pytest.mark.parametrize("kind,data", [("pdf", b"not a pdf"), ("docx", b"nope"), ("json", b"{bad")])
def test_corrupt_files_raise_parse_error(kind, data):
    with pytest.raises(DocumentParseError):
        P.extract_text(data, kind)


def test_unsupported_type():
    with pytest.raises(DocumentParseError):
        P.extract_text(b"x", "exe")


@pytest.mark.asyncio
async def test_chunk_text_overlap_and_bounds():
    text = " ".join(str(i) for i in range(100))
    chunks = await P.chunk_text(text, chunk_size=30, chunk_overlap=10)
    assert all(len(c.split()) <= 30 for c in chunks)
    assert chunks[1].split()[0] == "20"  # step = 20
    assert chunks[-1].split()[-1] == "99"
    assert await P.chunk_text("   ", 30, 10) == []
    assert await P.chunk_text("short text", 30, 10) == ["short text"]
    with pytest.raises(ValueError):
        await P.chunk_text("x", 10, 10)


@pytest.mark.asyncio
async def test_process_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("one two three four five six")
    assert await P.process(str(f), "txt", chunk_size=4, chunk_overlap=1) == ["one two three four", "four five six"]
    with pytest.raises(FileNotFoundError):
        await P.process(str(tmp_path / "missing.txt"), "txt")


@pytest.mark.parametrize("raw,expected", [
    ("../../etc/passwd", "passwd"),
    ("C:\\x\\evil.pdf", "evil.pdf"),
    ("a<b>|c.txt", "a_b__c.txt"),
    ("", "document"),
    ("..", "document"),
    ("a....b.txt", "a.b.txt"),
])
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_document_type_from_filename():
    assert document_type_from_filename("a.PDF") == "pdf"
    assert document_type_from_filename("noext") == ""


@pytest.mark.asyncio
async def test_indexer_indexes_and_deletes():
    store = InMemoryVectorStore()
    changed = []
    ix = DocumentIndexer(store, HashingEmbedder(), on_change=changed.append)
    res = await ix.index_document("t", "f.txt", b"alpha beta gamma", "txt")
    assert res["chunk_count"] == 1 and res["file_size_bytes"] == 16
    assert (await store.list_documents("t"))[0].document_name == "f.txt"
    assert await ix.delete_document("t", res["document_id"]) == 1
    assert changed == ["t", "t"]
    with pytest.raises(DocumentParseError):
        await ix.index_document("t", "e.txt", b"   ", "txt")
