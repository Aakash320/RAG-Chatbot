"""
Chat history persistence: sessions and messages, scoped per user.

All operations that touch a specific session enforce ownership — a
session_id that exists but belongs to another user raises the same
SessionNotFoundError as one that doesn't exist at all, so requests can't
be used to probe which session ids are valid.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import SessionNotFoundError
from app.db.models import ChatMessage, ChatSession

logger = logging.getLogger("rag.chat_history")

_TITLE_MAX_LEN = 60


class ChatHistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_session(self, user_id: str, document_id: str | None = None) -> ChatSession:
        session = ChatSession(user_id=user_id, document_id=document_id)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str, user_id: str) -> ChatSession:
        # selectinload is required here: async SQLAlchemy can't do an
        # implicit lazy-load when `.messages` is accessed later — without
        # it you'll hit "MissingGreenlet: greenlet_spawn has not been
        # called" the moment something reads `session.messages`.
        result = await self.db.scalars(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        session = result.first()
        if not session or session.user_id != user_id:
            raise SessionNotFoundError(session_id)
        return session

    async def list_sessions(self, user_id: str) -> list[ChatSession]:
        result = await self.db.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.all())

    async def get_messages(self, session_id: str, user_id: str) -> list[ChatMessage]:
        session = await self.get_session(session_id, user_id)
        return session.messages

    async def get_recent_messages(self, session_id: str, user_id: str, window: int = 6) -> list[ChatMessage]:
        session = await self.get_session(session_id, user_id)
        return session.messages[-window:]

    async def append_user_message(self, session_id: str, content: str) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role="user", content=content)
        self.db.add(message)

        session = await self.db.get(ChatSession, session_id)
        if session and not session.title:
            session.title = content[:_TITLE_MAX_LEN]

        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def append_assistant_message(
        self,
        session_id: str,
        content: str,
        sources: list[dict] | None = None,
        thought_steps: list[dict] | None = None,
        is_followup: bool | None = None,
        rewritten_query: str | None = None,
        latency_ms: int | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=content,
            sources=sources,
            thought_steps=thought_steps,
            is_followup=is_followup,
            rewritten_query=rewritten_query,
            latency_ms=latency_ms,
        )
        self.db.add(message)

        session = await self.db.get(ChatSession, session_id)
        if session:
            # SQLAlchemy won't auto-bump onupdate columns just from a
            # child insert — touch the parent explicitly so session lists
            # sort by most-recently-active.
            session.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def rename_session(self, session_id: str, user_id: str, title: str) -> ChatSession:
        session = await self.get_session(session_id, user_id)
        session.title = title
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete_session(self, session_id: str, user_id: str) -> None:
        session = await self.get_session(session_id, user_id)
        await self.db.delete(session)
        await self.db.commit()