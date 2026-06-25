"""
Embedding service.

Wraps the embedding model so the rest of the app never touches
sentence-transformers directly. Swapping to a different embedding model
(or an API-based one like OpenAI embeddings) later means editing only
this file.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME) -> None:
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts (used during ingestion)."""
        if not texts:
            return []
        embeddings = self._model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string (used during retrieval)."""
        return self._model.encode(text, convert_to_numpy=True).tolist()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
