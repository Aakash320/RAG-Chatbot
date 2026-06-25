"""
Application settings.

Loaded from environment variables / a `.env` file via pydantic-settings.
Every other module imports `settings` from here rather than reading
`os.environ` directly, so configuration has a single source of truth.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App / API ---
    APP_NAME: str = "RAG API"
    API_V1_PREFIX: str = "/api/v1"
    # JSON list in .env, e.g. CORS_ORIGINS=["http://localhost:5173"]
    CORS_ORIGINS: list[str] = ["*"]

    # --- File uploads ---
    UPLOAD_DIR: str = "data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".docx", ".txt", ".md"]

    # --- Embeddings ---
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # --- Chunking ---
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # --- Retrieval ---
    RETRIEVAL_TOP_K: int = 4

    # --- Chroma vector store ---
    CHROMA_PERSIST_DIR: str = "data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "documents"

    # --- LLM (Groq) ---
    GROQ_API_KEY: str = ""
    GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance. Import `settings` below from anywhere in the app."""
    return Settings()


settings = get_settings()
