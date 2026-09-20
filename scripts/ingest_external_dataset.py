#!/usr/bin/env python3
"""Ingest an external dataset (Kaggle, Hugging Face, a direct URL, or a local
file) into the RAG training corpus (data/processed/rag_training_data.jsonl),
in the same {document_id, chunk_id, text, source, source_type, metadata}
schema produced by chunk_and_prepare_data.py.

This is intentionally generic (works on arbitrary tabular/JSON datasets)
rather than dataset-specific, unlike chunk_and_prepare_data.py's per-source
parsers. Use it to add real-world data on top of (or instead of) the bundled
synthetic samples.

Examples
--------
Local file - NO Kaggle account or token needed. Download a dataset manually
from its Kaggle page (Download button, works with just a free account) or
any other site, unzip it into the project, then ingest it offline:

    mkdir -p data/raw/kaggle_manual/insurance
    unzip ~/Downloads/insurance.zip -d data/raw/kaggle_manual/insurance
    python scripts/ingest_external_dataset.py \\
        --source local --path data/raw/kaggle_manual/insurance/policies.csv \\
        --text-column description --title-column policy_type \\
        --source-name "Kaggle: imtkaggleteam/insurance (manual download)"

Kaggle API (requires `pip install kaggle` and ~/.kaggle/kaggle.json
credentials from https://www.kaggle.com/settings -> API -> Create New Token
- only needed if you want scripted/repeatable downloads instead of the
manual download above):

    python scripts/ingest_external_dataset.py \\
        --source kaggle --dataset imtkaggleteam/insurance \\
        --text-column description --title-column policy_type \\
        --source-name "Kaggle: imtkaggleteam/insurance"

Hugging Face Hub (public datasets, no auth needed; requires
`pip install datasets`):

    python scripts/ingest_external_dataset.py \\
        --source huggingface --dataset pubmed_qa --hf-config pqa_labeled --hf-split train \\
        --text-column long_answer --title-column question \\
        --source-name "HuggingFace: pubmed_qa"

Direct URL to a CSV/JSON file (e.g. an open-data / regulatory endpoint,
no auth needed):

    python scripts/ingest_external_dataset.py \\
        --source url --url https://example.gov/dataset.csv \\
        --text-column summary --source-name "example.gov open data"

After ingesting, restart the API (or just re-run a query) - RAGPipeline
reads data/processed/rag_training_data.jsonl on every query, so no reindex
step is required. All modes append to that same local file, so once
ingested the data lives in your project folder and no further network
access (or token) is ever needed to use it.
"""

import argparse
import csv
import io
import json
import logging
import sys
from pathlib import Path
from typing import Iterator

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_FILE = Path("data/processed/rag_training_data.jsonl")
CHUNK_SIZE_WORDS = 256
CHUNK_OVERLAP_WORDS = 20


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """Split text into overlapping word-count chunks (mirrors chunk_and_prepare_data.py)."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [text.strip()]
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def rows_from_kaggle(dataset: str, file_hint: str | None) -> Iterator[dict]:
    """Download a Kaggle dataset via the `kaggle` CLI/package and yield CSV rows.

    Requires `pip install kaggle` and API credentials at ~/.kaggle/kaggle.json
    (Kaggle account -> Settings -> API -> Create New Token). We never handle
    or ask for the token ourselves - the kaggle package reads it from that
    file / KAGGLE_USERNAME+KAGGLE_KEY env vars on its own.
    """
    try:
        import kaggle  # noqa: F401
    except ImportError:
        logger.error(
            "The `kaggle` package isn't installed. Run: pip install kaggle\n"
            "Then place your API token at ~/.kaggle/kaggle.json "
            "(download it from https://www.kaggle.com/settings -> API)."
        )
        sys.exit(1)

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    download_dir = Path("data/raw/kaggle_downloads") / dataset.replace("/", "__")
    download_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading Kaggle dataset '{dataset}' to {download_dir} ...")
    api.dataset_download_files(dataset, path=str(download_dir), unzip=True)

    candidates = sorted(download_dir.glob("**/*.csv"))
    if file_hint:
        candidates = [p for p in candidates if file_hint in p.name] or candidates
    if not candidates:
        logger.error(f"No CSV files found in {download_dir} after download.")
        sys.exit(1)

    csv_path = candidates[0]
    logger.info(f"Reading {csv_path}")
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        yield from csv.DictReader(f)


def rows_from_huggingface(dataset: str, hf_config: str | None, hf_split: str) -> Iterator[dict]:
    """Stream rows from a public Hugging Face dataset. Requires `pip install datasets`."""
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("The `datasets` package isn't installed. Run: pip install datasets")
        sys.exit(1)

    logger.info(f"Loading Hugging Face dataset '{dataset}' (config={hf_config}, split={hf_split}) ...")
    ds = load_dataset(dataset, hf_config, split=hf_split, streaming=True)
    for row in ds:
        yield row


def rows_from_local(path: str) -> Iterator[dict]:
    """Read rows from a local CSV or JSON file already sitting on disk (e.g. a
    manually-downloaded and unzipped Kaggle dataset - no account/token needed
    beyond the browser download itself, and no network access at ingest time).
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    logger.info(f"Reading local file {file_path}")

    if file_path.suffix.lower() == ".json" or file_path.suffix.lower() == ".jsonl":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            if file_path.suffix.lower() == ".jsonl":
                for line in f:
                    line = line.strip()
                    if line:
                        yield json.loads(line)
            else:
                data = json.load(f)
                records = data if isinstance(data, list) else data.get("results", data.get("data", [data]))
                yield from records
    else:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            yield from csv.DictReader(f)


def rows_from_url(url: str) -> Iterator[dict]:
    """Download a CSV or JSON file from a direct URL (no auth) and yield rows."""
    logger.info(f"Downloading {url} ...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    if url.endswith(".json") or resp.headers.get("content-type", "").startswith("application/json"):
        data = resp.json()
        records = data if isinstance(data, list) else data.get("results", data.get("data", [data]))
        yield from records
    else:
        yield from csv.DictReader(io.StringIO(resp.text))


def _stringify_field(value) -> str:
    """Flatten a field that may be a plain value or a list (common in JSON APIs
    like openFDA, which return e.g. indications_and_usage as a list of strings)."""
    if isinstance(value, (list, tuple)):
        return " ".join(_stringify_field(v) for v in value)
    return str(value) if value is not None else ""


def build_chunks(
    rows: Iterator[dict],
    text_column: str,
    title_column: str | None,
    source_name: str,
    source_type: str,
    id_prefix: str,
    limit: int | None,
) -> list[dict]:
    chunks_out = []
    for doc_idx, row in enumerate(rows):
        if limit and doc_idx >= limit:
            break

        text = _stringify_field(row.get(text_column, "")).strip()
        if not text or text.lower() == "nan":
            continue

        title = _stringify_field(row.get(title_column, "")).strip() if title_column else None
        full_text = f"{title}\n\n{text}" if title else text

        for chunk_idx, chunk in enumerate(chunk_text(full_text)):
            chunks_out.append({
                "document_id": f"{id_prefix}_{doc_idx}",
                "chunk_id": chunk_idx,
                "text": chunk,
                "source": source_name,
                "source_type": source_type,
                "metadata": {"title": title} if title else {},
            })

    return chunks_out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, choices=["local", "kaggle", "huggingface", "url"])
    parser.add_argument("--dataset", help="Kaggle 'owner/dataset-slug' or Hugging Face dataset name")
    parser.add_argument("--file-hint", help="Substring to pick a specific CSV from a multi-file Kaggle dataset")
    parser.add_argument("--hf-config", help="Hugging Face dataset config name (if the dataset has subsets)")
    parser.add_argument("--hf-split", default="train", help="Hugging Face split name (default: train)")
    parser.add_argument("--url", help="Direct URL to a CSV or JSON file (used with --source url)")
    parser.add_argument("--path", help="Local CSV/JSON/JSONL file path (used with --source local, e.g. a manually-downloaded Kaggle file)")
    parser.add_argument("--text-column", required=True, help="Column/field holding the main text to index")
    parser.add_argument("--title-column", help="Optional column/field holding a title, prepended to the text")
    parser.add_argument("--source-name", required=True, help='Human-readable source label, e.g. "Kaggle: owner/dataset"')
    parser.add_argument("--source-type", default="External Dataset", help="Category label stored in each chunk")
    parser.add_argument("--id-prefix", default="ext", help="Prefix for generated document_id values")
    parser.add_argument("--limit", type=int, help="Only ingest the first N rows (useful for a quick test)")
    parser.add_argument("--dry-run", action="store_true", help="Print a summary without writing to the output file")
    args = parser.parse_args()

    if args.source == "local":
        if not args.path:
            parser.error("--path is required for --source local")
        rows = rows_from_local(args.path)
    elif args.source == "kaggle":
        if not args.dataset:
            parser.error("--dataset is required for --source kaggle")
        rows = rows_from_kaggle(args.dataset, args.file_hint)
    elif args.source == "huggingface":
        if not args.dataset:
            parser.error("--dataset is required for --source huggingface")
        rows = rows_from_huggingface(args.dataset, args.hf_config, args.hf_split)
    else:
        if not args.url:
            parser.error("--url is required for --source url")
        rows = rows_from_url(args.url)

    new_chunks = build_chunks(
        rows,
        text_column=args.text_column,
        title_column=args.title_column,
        source_name=args.source_name,
        source_type=args.source_type,
        id_prefix=args.id_prefix,
        limit=args.limit,
    )

    if not new_chunks:
        logger.warning("No chunks were produced - check --text-column matches a real field name in the dataset.")
        sys.exit(1)

    logger.info(f"Prepared {len(new_chunks)} chunks from {args.source_name}")

    if args.dry_run:
        logger.info("Dry run - not writing output. Sample chunk:")
        print(json.dumps(new_chunks[0], indent=2))
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for chunk in new_chunks:
            f.write(json.dumps(chunk) + "\n")

    logger.info(f"Appended {len(new_chunks)} chunks to {OUTPUT_FILE}")
    logger.info("No reindex step needed - RAGPipeline reads this file on every query.")


if __name__ == "__main__":
    main()
