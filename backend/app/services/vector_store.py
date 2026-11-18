from __future__ import annotations

from functools import lru_cache
from typing import Iterable
import chromadb

from app.core.config import get_settings
from app.services.chunker import Chunk


class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = chromadb.PersistentClient(path=settings.chroma_path)
        self.collection_name = settings.chroma_collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[Chunk], embeddings, batch_size: int = 128) -> None:
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            vectors = embeddings[start:start + batch_size]
            self.collection.upsert(
                ids=[c.id for c in batch],
                documents=[c.text for c in batch],
                metadatas=[c.metadata() for c in batch],
                embeddings=vectors.tolist(),
            )

    def query(self, query_embedding, top_k: int):
        if self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        items = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for cid, doc, meta, distance in zip(ids, docs, metas, distances):
            items.append({
                "id": cid,
                "text": doc,
                "metadata": meta or {},
                "distance": float(distance),
                "expanded": False,
            })
        return items

    def get_unit_chunks(self, unit_id: str):
        result = self.collection.get(
            where={"unit_id": unit_id},
            include=["documents", "metadatas"],
        )
        items = []
        for cid, doc, meta in zip(
            result.get("ids", []),
            result.get("documents", []),
            result.get("metadatas", []),
        ):
            items.append({"id": cid, "text": doc, "metadata": meta or {}})
        return items


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()
