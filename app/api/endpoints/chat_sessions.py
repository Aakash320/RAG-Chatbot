"""
Chat session endpoints — list/rename/delete a user's own conversations,
and fetch the full message history (including thought steps) for one.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_chat_history_service, get_current_user
from app.db.models import User
from app.models.schemas import ChatMessageOut, ChatSessionSummary, RenameSessionRequest
from app.services.chat_history_service import ChatHistoryService

router = APIRouter(prefix="/sessions", tags=["chat-sessions"])


@router.get("", response_model=list[ChatSessionSummary])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    history: Annotated[ChatHistoryService, Depends(get_chat_history_service)],
):
    return await history.list_sessions(current_user.id)


@router.get("/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_session_messages(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    history: Annotated[ChatHistoryService, Depends(get_chat_history_service)],
):
    return await history.get_messages(session_id, current_user.id)


@router.patch("/{session_id}", response_model=ChatSessionSummary)
async def rename_session(
    session_id: str,
    payload: RenameSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    history: Annotated[ChatHistoryService, Depends(get_chat_history_service)],
):
    return await history.rename_session(session_id, current_user.id, payload.title)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    history: Annotated[ChatHistoryService, Depends(get_chat_history_service)],
) -> None:
    await history.delete_session(session_id, current_user.id)