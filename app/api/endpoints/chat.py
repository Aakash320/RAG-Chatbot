import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_controller
from app.controllers.chat_controller import ChatController
from app.models.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("")
async def chat(
    request: ChatRequest,
    controller: Annotated[ChatController, Depends(get_chat_controller)],
) -> StreamingResponse:
    async def event_generator():
        async for item in controller.astream_answer(
            request.query,
            request.document_id,
            request.top_k,
            chat_history=[m.model_dump() for m in request.chat_history],
        ):
            yield _format_sse(item["event"], item["data"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx etc.) if present
        },
    )