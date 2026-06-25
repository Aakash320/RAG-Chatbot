"""
Retrieval service.

Embeds a query and asks the vector store for the top-k most similar
chunks. Kept separate from the LLM call so it can be tested/reused
independently (and so swapping in LangGraph later only touches how this
gets *invoked*, not what it does).
"""

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.vectorstores.base import BaseVectorStore, RetrievedChunk


class RetrievalService:
    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: EmbeddingService,
        top_k: int = settings.RETRIEVAL_TOP_K,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._top_k = top_k

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> list[RetrievedChunk]:
        query_embedding = self._embedding_service.embed_query(query)

        filter_ = {"document_id": document_id} if document_id else None

        return self._vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k or self._top_k,
            filter=filter_,
        )

    @staticmethod
    def format_context(chunks: list[RetrievedChunk]) -> str:
        """Flatten retrieved chunks into a single context string for the LLM prompt."""
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.metadata.get("source_file", "unknown")
            parts.append(f"[{i}] (source: {source})\n{chunk.text}")
        return "\n\n".join(parts)
