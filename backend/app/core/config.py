from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Egyptian Legal Assistant API"
    api_prefix: str = "/api/v1"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    embedding_model: str = "mzahran1/arabic-english-e5-small-retrieval"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32

    dataset_path: str = "data/legal_dataset_decoded.jsonl"
    chroma_path: str = "./chroma_db"
    chroma_collection: str = "egyptian_legal_chunks"
    sqlite_path: str = "./storage/conversations.sqlite3"

    top_k: int = 5
    max_cosine_distance: float = 0.65
    chunk_max_tokens: int = 220
    max_context_tokens: int = 6000
    context_neighbors: int = 1

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    def ensure_directories(self) -> None:
        Path(self.chroma_path).mkdir(parents=True, exist_ok=True)
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
