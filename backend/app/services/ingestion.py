from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

import pandas as pd

from app.core.config import get_settings
from app.services.chunker import chunk_record
from app.services.embeddings import get_embedding_service
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def load_records(source: str | Path) -> list[dict]:
    path = Path(source)
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        records = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
                if isinstance(item, dict):
                    records.append(item)
        return records
    if suffix == ".parquet":
        frame = pd.read_parquet(path)
        return frame.to_dict(orient="records")
    raise ValueError(f"Unsupported dataset format: {suffix}. Use .jsonl or .parquet.")


def ingest(source: str | Path, reset: bool = False) -> dict:
    settings = get_settings()
    records = load_records(source)
    embedder = get_embedding_service()
    store = get_vector_store()
    if reset:
        store.reset()

    total_chunks = 0
    batch_size = 96
    batch = []
    for index, row in enumerate(records):
        chunks = chunk_record(
            row=row,
            row_index=index,
            tokenizer=embedder.tokenizer,
            max_tokens=settings.chunk_max_tokens,
        )
        for chunk in chunks:
            batch.append(chunk)
            if len(batch) >= batch_size:
                vectors = embedder.embed_passages([c.text for c in batch])
                store.add_chunks(batch, vectors, batch_size=batch_size)
                total_chunks += len(batch)
                logger.info("Indexed %s chunks", total_chunks)
                batch = []
    if batch:
        vectors = embedder.embed_passages([c.text for c in batch])
        store.add_chunks(batch, vectors, batch_size=batch_size)
        total_chunks += len(batch)

    report = {
        "source": str(source),
        "records": len(records),
        "chunks_indexed_this_run": total_chunks,
        "collection_count": store.collection.count(),
        "embedding_model": settings.embedding_model,
        "chunk_max_tokens": settings.chunk_max_tokens,
        "note": "Dataset provenance/currentness is not verified by ingestion.",
    }
    report_path = Path("data/ingestion_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
