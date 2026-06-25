"""
Single switch point for which vector store implementation gets used.

Right now this only returns `ChromaVectorStore`. When another backend is
added (e.g. pgvector), this is the one place that chooses between them —
typically off a `VECTOR_STORE_PROVIDER` setting.
"""

from functools import lru_cache

from app.vectorstores.base import BaseVectorStore
from app.vectorstores.chroma_store import ChromaVectorStore


@lru_cache
def get_vector_store_instance() -> BaseVectorStore:
    return ChromaVectorStore()
