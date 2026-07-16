"""
Chat session controller — wraps the RAG streaming pipeline
(`ChatController`) with per-user session management and persistence.

`ChatController` itself stays completely unaware of users/sessions/the
database — it only knows how to stream one query through the LangGraph
pipeline. This controller is the seam between that and chat history
storage:

    endpoint -> ChatSessionController.stream_chat() -> ChatController.astream_answer()
                        |                                        |
                        v                                        v
                 create/load session                     status/token/done events
                 load prior messages                      (forwarded to the client
                 persist user + assistant                  unchanged)
                 messages when done
"""

import logging
import time
from typing import AsyncGenerator

from app.controllers.chat_controller import ChatController
from app.services.chat_history_service import ChatHistoryService

logger = logging.getLogger("rag.chat_session")


class ChatSessionController:
    def __init__(self, chat_controller: ChatController, chat_history_service: ChatHistoryService) -> None:
        self._chat_controller = chat_controller
        self._history = chat_history_service

    async def stream_chat(
        self,
        user_id: str,
        query: str,
        session_id: str | None = None,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Async generator yielding the same event dicts as
        `ChatController.astream_answer` (status/token/done/error), plus one
        extra `session` event emitted first so the client learns the
        session id immediately — important when a new session is created
        mid-request.
        """
        if session_id:
            session = await self._history.get_session(session_id, user_id)
        else:
            session = await self._history.create_session(user_id, document_id)

        yield {"event": "session", "data": {"session_id": session.id, "title": session.title}}

        prior_messages = await self._history.get_recent_messages(session.id, user_id)
        chat_history = [{"role": m.role, "content": m.content} for m in prior_messages]

        await self._history.append_user_message(session.id, query)

        collected_status: list[dict] = []
        start = time.perf_counter()

        async for item in self._chat_controller.astream_answer(
            query, document_id=document_id, top_k=top_k, chat_history=chat_history
        ):
            if item["event"] == "status":
                collected_status.append(item["data"])
            yield item

            if item["event"] == "done":
                latency_ms = int((time.perf_counter() - start) * 1000)
                is_followup = next(
                    (
                        s["detail"]["is_followup"]
                        for s in collected_status
                        if s["step"] == "detect_intent" and "detail" in s
                    ),
                    None,
                )
                rewritten_query = next(
                    (
                        s["detail"]["rewritten_query"]
                        for s in collected_status
                        if s["step"] == "rewrite_query" and "detail" in s
                    ),
                    None,
                )
                await self._history.append_assistant_message(
                    session.id,
                    content=item["data"]["answer"],
                    sources=item["data"]["sources"],
                    thought_steps=collected_status,
                    is_followup=is_followup,
                    rewritten_query=rewritten_query,
                    latency_ms=latency_ms,
                )
            elif item["event"] == "error":
                # Still persist an assistant "message" so the failure shows
                # up in history instead of silently vanishing.
                await self._history.append_assistant_message(
                    session.id,
                    content=item["data"]["detail"],
                    sources=[],
                    thought_steps=collected_status,
                )