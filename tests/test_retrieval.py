"""
Tests for RetrievalService using a fake in-memory vector store
(no real embedding model or DB needed).
"""

from app.services.retrieval_service import RetrievalService
from app.vectorstores.base import BaseVectorStore, Chunk, RetrievedChunk


class FakeEmbeddingService:
    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeVectorStore(BaseVectorStore):
    def __init__(self):
        self._chunks = [
            RetrievedChunk(
                id="1", text="hello world", metadata={"source_file": "a.txt"}, score=0.9
            )
        ]

    def add_documents(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        pass

    def similarity_search(self, query_embedding, top_k=4, filter=None) -> list[RetrievedChunk]:
        return self._chunks[:top_k]

    def delete(self, ids: list[str]) -> None:
        pass

    def delete_by_metadata(self, filter: dict) -> None:
        pass

    def count(self) -> int:
        return len(self._chunks)

    def list_documents(self) -> list[dict]:
        return [
            {
                "document_id": "doc-1",
                "filename": "a.txt",
                "file_type": "txt",
                "chunk_count": len(self._chunks),
            }
        ]


def test_retrieve_returns_chunks_from_store():
    service = RetrievalService(
        vector_store=FakeVectorStore(),
        embedding_service=FakeEmbeddingService(),
        top_k=4,
    )

    results = service.retrieve("hello?")

    assert len(results) == 1
    assert results[0].text == "hello world"


def test_format_context_includes_source_file():
    chunks = [
        RetrievedChunk(id="1", text="some text", metadata={"source_file": "a.txt"}, score=0.9)
    ]
    context = RetrievalService.format_context(chunks)

    assert "a.txt" in context
    assert "some text" in context
