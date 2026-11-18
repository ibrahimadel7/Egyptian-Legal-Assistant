from __future__ import annotations

from functools import lru_cache
from typing import Sequence
import logging

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        settings = get_settings()
        self.model_name = settings.embedding_model
        logger.info("Loading embedding model %s on %s", self.model_name, settings.embedding_device)
        self.model = SentenceTransformer(
            self.model_name,
            device=settings.embedding_device,
        )
        # The selected E5-small model has a 256-token maximum input.
        self.model.max_seq_length = min(getattr(self.model, "max_seq_length", 256), 256)
        self.batch_size = settings.embedding_batch_size

    @property
    def tokenizer(self):
        return self.model.tokenizer

    def embed_passages(self, texts: Sequence[str]):
        prefixed = [f"passage: {text}" for text in texts]
        return self.model.encode(
            prefixed,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def embed_query(self, text: str):
        vectors = self.model.encode(
            [f"query: {text}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors[0]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
