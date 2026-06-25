"""
Abstract vector store interface.

THIS IS THE KEY ABSTRACTION IN THE PROJECT.

Today `ChromaVectorStore` implements this interface. Later, a different
backend (e.g. `PgVectorStore`) can implement the exact same interface.
Nothing in services/ or controllers/ should ever import a concrete vector
store directly — they only ever talk to `BaseVectorStore`. That is what
makes swapping backends a one-line config change instead of a rewrite.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """A single chunk of text to be embedded and stored."""

    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    """A chunk returned from a similarity search, with its relevance score."""

    id: str
    text: str
    metadata: dict[str, Any]
    score: float  # higher = more similar, normalized 0-1 where possible


class BaseVectorStore(ABC):
    """Abstract interface every vector store backend must implement."""

    @abstractmethod
    def add_documents(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Insert chunks with their precomputed embeddings."""
        raise NotImplementedError

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Return the top_k most similar chunks to the query embedding."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Delete chunks by id."""
        raise NotImplementedError

    @abstractmethod
    def delete_by_metadata(self, filter: dict[str, Any]) -> None:
        """Delete chunks matching a metadata filter (e.g. all chunks for a document_id)."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return the total number of chunks currently stored."""
        raise NotImplementedError

    @abstractmethod
    def list_documents(self) -> list[dict[str, Any]]:
        """
        Aggregate stored chunks by `document_id`.

        Returns one dict per distinct document with keys:
        `document_id`, `filename`, `file_type`, `chunk_count`. This is the
        only "what's been ingested?" view available without a separate
        metadata database — it is derived purely from chunk metadata.
        """
        raise NotImplementedError
