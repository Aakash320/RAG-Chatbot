"""
Document controller — RAG ingestion orchestration.

Orchestrates: load file -> chunk -> embed -> store in the vector store.

There is no separate metadata database here: the vector store itself is
the source of truth for "what's been ingested" (see
`BaseVectorStore.list_documents`). This class only handles getting a
file's content into the vector store and removing it again.
"""

import logging

from app.core.exceptions import AppError, DocumentNotFoundError, IngestionError, VectorStoreError
from app.models.schemas import DocumentUploadResponse
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

    def ingest_document(
        self,
        file_path: str,
        document_id: str,
        filename: str,
        file_type: str,
    ) -> DocumentUploadResponse:
        """
        Load, chunk, embed, and store a single file.

        Returns a DocumentUploadResponse. Raises `IngestionError` if no
        content could be extracted or if the pipeline fails.
        """
        try:
            chunks = self._ingestion.load_and_chunk(file_path, document_id, filename=filename)
            if not chunks:
                raise IngestionError("No content could be extracted from the file")

            texts = [c.text for c in chunks]
            embeddings = self._embedding.embed_texts(texts)
            self._vector_store.add_documents(chunks, embeddings)
        except AppError:
            # Let any already-typed error (e.g. UnsupportedFileTypeError, 415)
            # pass through with its real status code instead of being
            # re-wrapped as a generic 500.
            raise
        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document_id)
            raise IngestionError("The uploaded file could not be processed") from exc

        logger.info("Ingested document %s with %d chunks", document_id, len(chunks))
        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            file_type=file_type,
            chunk_count=len(chunks),
        )

    def delete_document(self, document_id: str) -> None:
        """Delete every chunk belonging to a document_id from the vector store."""
        try:
            existing = self._vector_store.list_documents()
        except Exception as exc:
            logger.exception("Failed to list documents while deleting %s", document_id)
            raise VectorStoreError(str(exc)) from exc

        if not any(d["document_id"] == document_id for d in existing):
            raise DocumentNotFoundError(document_id)

        try:
            self._vector_store.delete_by_metadata({"document_id": document_id})
        except Exception as exc:
            logger.exception("Failed to delete document %s", document_id)
            raise VectorStoreError(str(exc)) from exc

        logger.info("Deleted all chunks for document %s", document_id)
