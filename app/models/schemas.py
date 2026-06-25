"""
Pydantic schemas describing the HTTP request/response contract.

These describe what the API accepts and returns. They are intentionally
kept separate from the internal `Chunk`/`RetrievedChunk` dataclasses
(`app/vectorstores/base.py`) so the wire format and the internal data
shapes can evolve independently.
"""

from pydantic import BaseModel, Field

# --- Documents ---


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: str


class DocumentMetadata(BaseModel):
    """One ingested document, aggregated from chunk metadata in the vector store.

    Note: there is no separate metadata database, so only fields derivable
    from stored chunks are available (no upload timestamp / status history).
    """

    document_id: str
    filename: str
    file_type: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentMetadata]
    total: int


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool


# --- Chat ---


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's question")
    document_id: str | None = Field(
        default=None, description="Optionally restrict retrieval to a single document"
    )
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceChunk(BaseModel):
    text: str
    source_file: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    vector_store_provider: str
    vector_store_count: int
