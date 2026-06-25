"""
Document controller — RAG ingestion orchestration.

Orchestrates: load file -> chunk -> embed -> store in the vector store.

There is no separate metadata database here: the vector store itself is
the source of truth for "what's been ingested" (see
`BaseVectorStore.list_documents`). This class only handles getting a
file's content into the vector store and removing it again.
"""

import logging

from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)


class DocumentController:
    def __init__(
        self,
        ingestion_service: IngestionService,
        embedding_service: EmbeddingService,
        vector_store: BaseVectorStore,
    ) -> None:
        self._ingestion = ingestion_service
        self._embedding = embedding_service
        self._vector_store = vector_store

    def ingest_document(self, file_path: str, document_id: str) -> int:
        """
        Load, chunk, embed, and store a single file.

        Returns the number of chunks stored. Raises `ValueError` if no
        content could be extracted (empty/unsupported file) — the API
        layer translates this into an HTTP 400.
        """
        chunks = self._ingestion.load_and_chunk(file_path, document_id)
        if not chunks:
            raise ValueError("No content could be extracted from the file")

        texts = [c.text for c in chunks]
        embeddings = self._embedding.embed_texts(texts)
        self._vector_store.add_documents(chunks, embeddings)

        logger.info("Ingested document %s with %d chunks", document_id, len(chunks))
        return len(chunks)

    def delete_document(self, document_id: str) -> None:
        """Delete every chunk belonging to a document_id from the vector store."""
        self._vector_store.delete_by_metadata({"document_id": document_id})
        logger.info("Deleted all chunks for document %s", document_id)
