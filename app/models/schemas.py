"""
Pydantic schemas describing the HTTP request/response contract.

These describe what the API accepts and returns. They are intentionally
kept separate from the internal `Chunk`/`RetrievedChunk` dataclasses
(`app/vectorstores/base.py`) so the wire format and the internal data
shapes can evolve independently.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from datetime import datetime

# --- Documents ---


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    chunk_count: int


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
    session_id: str | None = Field(
        default=None,
        description="Existing chat session to continue. Omit to start a new session.",
    )
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


# --- Auth ---


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    role: Literal["user", "admin"] | None = Field(
        default=None,
        description="Defaults to 'user' if omitted. Chosen at registration (e.g. a checkbox on the signup form).",
    )


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccessTokenResponse(BaseModel):
    """
    Returned by /auth/login and /auth/refresh. The refresh token itself is
    never in this body — it's set as an HttpOnly cookie (see
    app/api/endpoints/auth.py), so client-side JS can't read it.
    """

    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# --- Chat sessions / history ---


class ChatSessionSummary(BaseModel):
    id: str
    title: str | None
    document_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceChunk] | None = None
    thought_steps: list[dict] | None = None
    is_followup: bool | None = None
    rewritten_query: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    vector_store_provider: str
    vector_store_count: int
