"""
Chroma implementation of BaseVectorStore.

This is the only file allowed to import chromadb directly. If you ever
find yourself importing chromadb anywhere else in the codebase, that's a
sign the abstraction is leaking — route it through this class instead.
"""

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.vectorstores.base import BaseVectorStore, Chunk, RetrievedChunk


class ChromaVectorStore(BaseVectorStore):
    def __init__(
        self,
        persist_dir: str = settings.CHROMA_PERSIST_DIR,
        collection_name: str = settings.CHROMA_COLLECTION_NAME,
    ) -> None:
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # cosine distance keeps scores easy to normalize into a 0-1 similarity
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        space = (self._collection.metadata or {}).get("hnsw:space", "l2")
        if space != "cosine":
            raise RuntimeError(
                f"Chroma collection '{collection_name}' already exists with "
                f"space='{space}', but similarity_search() assumes cosine distance. "
                "Delete the collection/persist dir or fix the scoring formula."
            )

    def add_documents(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter,
        )

        retrieved: list[RetrievedChunk] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for id_, doc, meta, dist in zip(ids, documents, metadatas, distances):
            # cosine distance is in [0, 2]; convert to a 0-1 similarity score
            similarity = 1 - (dist / 2)
            retrieved.append(
                RetrievedChunk(id=id_, text=doc, metadata=meta or {}, score=similarity)
            )
        return retrieved

    def delete(self, ids: list[str]) -> None:
        if ids:
            self._collection.delete(ids=ids)

    def delete_by_metadata(self, filter: dict[str, Any]) -> None:
        self._collection.delete(where=filter)

    def count(self) -> int:
        return self._collection.count()

    def list_documents(self) -> list[dict[str, Any]]:
        # Pull only metadata (not the embeddings/text) and aggregate by document_id.
        result = self._collection.get(include=["metadatas"])
        metadatas = result.get("metadatas") or []

        documents: dict[str, dict[str, Any]] = {}
        for meta in metadatas:
            if not meta:
                continue
            doc_id = meta.get("document_id")
            if doc_id is None:
                continue
            entry = documents.setdefault(
                doc_id,
                {
                    "document_id": doc_id,
                    "filename": meta.get("source_file", "unknown"),
                    "file_type": meta.get("file_type", "unknown"),
                    "chunk_count": 0,
                },
            )
            entry["chunk_count"] += 1

        return list(documents.values())