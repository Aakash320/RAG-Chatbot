import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_session_controller, get_current_user
from app.controllers.chat_session_controller import ChatSessionController
from app.db.models import User
from app.models.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("")
async def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[ChatSessionController, Depends(get_chat_session_controller)],
) -> StreamingResponse:
    async def event_generator():
        async for item in controller.stream_chat(
            user_id=current_user.id,
            query=request.query,
            session_id=request.session_id,
            document_id=request.document_id,
            top_k=request.top_k,
        ):
            yield _format_sse(item["event"], item["data"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )