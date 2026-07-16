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
    APP_NAME: str = "RAG Chatbot"
    API_V1_PREFIX: str = "/api/v1"
    
    # JSON list in .env, e.g. CORS_ORIGINS=["http://localhost:5173"]
    # NOTE: cannot be ["*"] once allow_credentials=True (browsers reject
    # wildcard-origin + credentials per the CORS spec) — must be explicit
    # origins. Defaulting to the Vite dev server; override in .env.
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

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
    # Chunks with a similarity score below this are treated as irrelevant
    # and discarded before being used as chat context. Score range is 0-1
    # (see ChromaVectorStore.similarity_search).
    SIMILARITY_THRESHOLD: float = 0.35

    # --- Chroma vector store ---
    CHROMA_PERSIST_DIR: str = "data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "documents"

    # --- LLM (Groq) ---
    GROQ_API_KEY: str = ""
    GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # --- Auth / JWT ---
    JWT_SECRET_KEY: str = "CHANGE_ME_dev_only_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False  # set True in .env once you're serving over https


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance. Import `settings` below from anywhere in the app."""
    return Settings()


settings = get_settings()
