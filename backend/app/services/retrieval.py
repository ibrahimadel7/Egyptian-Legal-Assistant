from __future__ import annotations

from app.core.config import get_settings
from app.services.embeddings import get_embedding_service
from app.services.vector_store import get_vector_store


class RetrievalService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.store = get_vector_store()
        self.embedder = None

    def search(self, query: str) -> list[dict]:
        if self.store.collection.count() == 0:
            return []
        if self.embedder is None:
            self.embedder = get_embedding_service()
        vector = self.embedder.embed_query(query)
        return self.store.query(vector, self.settings.top_k)

    def expand_context(self, seeds: list[dict]) -> list[dict]:
        """Expand only within the same parent record and detected legal unit."""
        by_id = {item["id"]: dict(item) for item in seeds}
        for seed in seeds:
            meta = seed["metadata"]
            unit_id = meta.get("unit_id")
            if not unit_id or self.settings.context_neighbors <= 0:
                continue
            siblings = self.store.get_unit_chunks(unit_id)
            target_indices = {
                int(meta.get("unit_chunk_index", 0)) + offset
                for offset in range(-self.settings.context_neighbors, self.settings.context_neighbors + 1)
            }
            for sibling in siblings:
                sibling_meta = sibling["metadata"]
                if int(sibling_meta.get("unit_chunk_index", -999)) not in target_indices:
                    continue
                if sibling["id"] in by_id:
                    continue
                by_id[sibling["id"]] = {
                    **sibling,
                    "distance": seed["distance"] + 0.0001,
                    "expanded": True,
                }
        # Directly retrieved chunks first, ordered by distance; expanded neighbors follow.
        values = list(by_id.values())
        values.sort(key=lambda x: (x.get("expanded", False), x.get("distance", 2.0)))
        return values

    def build_context(self, chunks: list[dict]) -> tuple[str, list[dict]]:
        """Build evidence labels under an approximate GPT-OSS token budget."""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("o200k_base")
            count_tokens = lambda value: len(encoding.encode(value))
        except Exception:
            count_tokens = lambda value: max(1, int(len(value.split()) * 1.5))

        budget = self.settings.max_context_tokens
        used = 0
        blocks = []
        sources = []
        for item in chunks:
            meta = item["metadata"]
            label = f"S{len(sources) + 1}"
            header = (
                f"[{label}] السجل: {meta.get('law_name', 'غير محدد')} | "
                f"التصنيف: {meta.get('category_path', '')} | "
                f"الوحدة: {meta.get('unit_label', '')} | "
                f"نوع الوحدة: {meta.get('unit_type', '')}"
            )
            body = item["text"]
            block = f"{header}\nالنص:\n{body}"
            cost = count_tokens(block)
            if used + cost > budget:
                continue
            used += cost
            blocks.append(block)
            sources.append({
                "source_id": label,
                "chunk_id": item["id"],
                "law_name": meta.get("law_name", "غير محدد"),
                "categories": meta.get("category_path", ""),
                "unit_label": meta.get("unit_label", ""),
                "unit_type": meta.get("unit_type", ""),
                "article_number": meta.get("article_number", ""),
                "excerpt": body,
                "expanded": bool(item.get("expanded", False)),
                "distance": float(item.get("distance", 0.0)),
            })
        return "\n\n".join(blocks), sources
