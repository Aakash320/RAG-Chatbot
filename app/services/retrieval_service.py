"""
Retrieval service.

Embeds a query and asks the vector store for the top-k most similar
chunks. Kept separate from the LLM call so it can be tested/reused
independently (and so swapping in LangGraph later only touches how this
gets *invoked*, not what it does).
"""

import logging

from app.config import settings
from app.core.logging_config import truncate
from app.services.embedding_service import EmbeddingService
from app.vectorstores.base import BaseVectorStore, RetrievedChunk

logger = logging.getLogger("rag.retrieval")


class RetrievalService:
    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: EmbeddingService,
        top_k: int = settings.RETRIEVAL_TOP_K,
        similarity_threshold: float = settings.SIMILARITY_THRESHOLD,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> list[RetrievedChunk]:
        effective_top_k = top_k or self._top_k
        logger.info("Embedding query for retrieval: %s", truncate(query, 150))

        query_embedding = self._embedding_service.embed_query(query)
        logger.info("Query embedded (dimension=%d)", len(query_embedding))

        filter_ = {"document_id": document_id} if document_id else None

        chunks = self._vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=effective_top_k,
            filter=filter_,
        )
        logger.info(
            "Vector store returned %d raw chunk(s) (top_k=%d, filter=%s)",
            len(chunks),
            effective_top_k,
            filter_ or "none",
        )
        for i, c in enumerate(chunks, start=1):
            logger.debug(
                "    raw[%d] score=%.3f source=%s",
                i, c.score, c.metadata.get("source_file", "unknown"),
            )

        filtered = [c for c in chunks if c.score >= self._similarity_threshold]
        dropped = len(chunks) - len(filtered)
        if dropped:
            logger.info(
                "Dropped %d chunk(s) below similarity threshold (%.2f)",
                dropped,
                self._similarity_threshold,
            )

        return filtered

    @staticmethod
    def format_context(chunks: list[RetrievedChunk]) -> str:
        """Flatten retrieved chunks into a single context string for the LLM prompt."""
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.metadata.get("source_file", "unknown")
            parts.append(f"[{i}] (source: {source})\n{chunk.text}")
        return "\n\n".join(parts)
