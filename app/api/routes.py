"""
HTTP routes for the RAG API.

NOTE: the endpoint handlers are intentionally NOT implemented here — that
work is owned separately. Everything around them is wired up and ready:

- this `router` is included by `app/main.py` under the `/api/v1` prefix
- the controllers and vector store are available via the dependency
  providers in `app/api/deps.py`
- request/response models live in `app/models/schemas.py`
- supported upload types are in `app/services/ingestion_service.py`
  (`SUPPORTED_EXTENSIONS`)

Sketch of how a handler plugs into the scaffolding:

    from typing import Annotated
    from fastapi import Depends
    from app.api.deps import get_chat_controller
    from app.controllers.chat_controller import ChatController
    from app.models.schemas import ChatRequest, ChatResponse

    @router.post("/chat", response_model=ChatResponse)
    def chat(
        payload: ChatRequest,
        controller: Annotated[ChatController, Depends(get_chat_controller)],
    ) -> ChatResponse:
        result = controller.answer(payload.query, payload.document_id, payload.top_k)
        return ChatResponse(**result)

Use plain (sync) `def` handlers so FastAPI runs the blocking embedding /
LLM work in a threadpool.
"""

from fastapi import APIRouter
from app.api.endpoints import documents, chat, health

router = APIRouter()

router.include_router(documents.router)
router.include_router(chat.router)
router.include_router(health.router)
# Endpoints go here — see module docstring.
