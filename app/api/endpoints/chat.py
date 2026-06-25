from fastapi import APIRouter, Depends
from typing import Annotated
from app.models.schemas import ChatRequest, ChatResponse
from app.controllers.chat_controller import ChatController
from app.api.deps import get_chat_controller

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    controller: Annotated[ChatController, Depends(get_chat_controller)],
) -> ChatResponse:
    return ChatResponse(**controller.answer(request.query, request.document_id, request.top_k))