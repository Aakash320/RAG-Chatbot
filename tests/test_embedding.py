"""
Integration test for EmbeddingService.

This loads the real sentence-transformers model, so it needs the model to
be available locally (or internet access to download it on first run). If
the model can't be loaded (e.g. offline CI), the tests skip rather than
fail.

Run with: pytest tests/test_embedding.py
"""

import pytest

pytest.importorskip("sentence_transformers")

from app.config import settings  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402


@pytest.fixture(scope="module")
def service() -> EmbeddingService:
    try:
        return EmbeddingService()
    except Exception as exc:  # offline / model unavailable
        pytest.skip(f"Embedding model unavailable: {exc}")


def test_embed_texts_returns_one_vector_per_text(service: EmbeddingService):
    embeddings = service.embed_texts(["hello", "world", "rag"])
    assert len(embeddings) == 3
    assert all(len(e) == settings.EMBEDDING_DIMENSION for e in embeddings)


def test_embed_query_dimension(service: EmbeddingService):
    embedding = service.embed_query("what is retrieval augmented generation?")
    assert len(embedding) == settings.EMBEDDING_DIMENSION


def test_embed_texts_empty_returns_empty(service: EmbeddingService):
    assert service.embed_texts([]) == []
