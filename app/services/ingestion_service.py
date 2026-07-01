"""
Ingestion service.

Handles loading a single uploaded file and splitting it into chunks.
Ingestion is triggered per-upload via the API (one file at a time) rather
than scanning a fixed folder at startup.

A folder-scan helper is also included for manual/bulk ingestion via a
script (see scripts/ingest_folder.py).
"""

import uuid
from functools import lru_cache
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document

from app.config import settings
from app.core.exceptions import UnsupportedFileTypeError
from app.vectorstores.base import Chunk

_LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
}

# Single source of truth for which file types can be ingested.
# Imported by the API layer and the bulk-ingest script for validation.
SUPPORTED_EXTENSIONS = frozenset(_LOADER_MAP)

def _sanitize_metadata(metadata: dict) -> dict:
    """Chroma metadata values must be str/int/float/bool/None — coerce anything else."""
    clean = {}
    for k, v in metadata.items():
        clean[k] = v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
    return clean

class IngestionService:
    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def load_file(self, file_path: str, filename: str | None = None) -> list[Document]:
        """Load a single file into LangChain Documents using the right loader."""
        path = Path(file_path)
        extension = path.suffix.lower()

        loader_cls = _LOADER_MAP.get(extension)
        if loader_cls is None:
            raise UnsupportedFileTypeError(extension)

        loader = loader_cls(str(path))
        documents = loader.load()

        source_name = filename or path.name
        for doc in documents:
            doc.metadata["source_file"] = source_name
            doc.metadata["file_type"] = extension.lstrip(".")

        return documents

    def chunk_documents(
        self,
        documents: list[Document],
        document_id: str,
    ) -> list[Chunk]:
        """Split loaded documents into Chunk objects ready for embedding + storage."""
        split_docs = self._splitter.split_documents(documents)

        chunks: list[Chunk] = []
        for i, doc in enumerate(split_docs):
            chunk_id = f"{document_id}_chunk_{i}_{uuid.uuid4().hex[:8]}"
            metadata = _sanitize_metadata(
                {**doc.metadata, "document_id": document_id, "chunk_index": i}
            )
            chunks.append(Chunk(id=chunk_id, text=doc.page_content, metadata=metadata))

        return chunks

    def load_and_chunk(self, file_path: str, document_id: str, filename: str | None = None) -> list[Chunk]:
        """Convenience method: load a file and chunk it in one call."""
        documents = self.load_file(file_path, filename=filename)
        return self.chunk_documents(documents, document_id)

    def load_folder(self, folder_path: str) -> list[Document]:
        """Bulk-load every supported file in a folder. Used by manual ingestion scripts."""
        all_documents: list[Document] = []
        folder = Path(folder_path)

        for file_path in folder.iterdir():
            if file_path.suffix.lower() in _LOADER_MAP:
                all_documents.extend(self.load_file(str(file_path)))

        return all_documents


@lru_cache
def get_ingestion_service() -> IngestionService:
    return IngestionService()
