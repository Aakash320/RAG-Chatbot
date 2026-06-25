from fastapi import APIRouter, Depends
from typing import Annotated
from app.api.deps import get_vector_store
from app.vectorstores.base import BaseVectorStore
from app.models.schemas import HealthResponse

router = APIRouter(prefix = "/health", tags=["health"])

@router.get("", response_model = HealthResponse)
def health(
    vector_store: Annotated[BaseVectorStore, Depends(get_vector_store)],
) -> HealthResponse:
    return HealthResponse(
        status= "ok",
        vector_store_provider= vector_store.__class__.__name__,
        vector_store_count= vector_store.count(),
    )