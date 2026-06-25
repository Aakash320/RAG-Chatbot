"""
Tests for IngestionService chunking logic.

Run with: pytest tests/test_ingestion.py
"""

from langchain_core.documents import Document

from app.services.ingestion_service import IngestionService


def test_chunk_documents_produces_chunks_with_metadata():
    service = IngestionService(chunk_size=50, chunk_overlap=10)
    docs = [
        Document(
            page_content="A" * 200,
            metadata={"source_file": "test.txt", "file_type": "txt"},
        )
    ]

    chunks = service.chunk_documents(docs, document_id="doc-123")

    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk.metadata["document_id"] == "doc-123"
        assert chunk.metadata["chunk_index"] == i
        assert chunk.metadata["source_file"] == "test.txt"


def test_chunk_documents_empty_input_returns_empty_list():
    service = IngestionService()
    assert service.chunk_documents([], document_id="doc-123") == []
