"""
Chat controller — RAG retrieve-then-generate orchestration.

The orchestration itself (embed query -> retrieve top-k chunks -> build
context -> call the LLM) now lives in a compiled LangGraph graph
(`app/graph/build.py`); this controller just builds that graph once and
invokes it per request.

Returns a plain dict; the API layer reshapes it into the `ChatResponse`
schema. Errors raised inside graph nodes (e.g. `RetrievalError`,
`LLMGenerationError`) propagate through `.invoke()` unchanged, so the
existing `AppError` exception handlers in `app/core/exceptions.py` still
catch them exactly as before.
"""

import logging
import time

from app.core.logging_config import log_section, new_request_id
from app.graph.build import build_rag_graph
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger("rag.controller")


class ChatController:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self._graph = build_rag_graph(retrieval_service, llm_service)

    def answer(
        self,
        query: str,
        document_id: str | None = None,
        top_k: int | None = None,
        chat_history: list[dict] | None = None,
    ) -> dict:
        """
        Returns a dict shaped like:
        {
            "answer": str,
            "sources": [{"text": str, "source_file": str, "score": float}, ...]
        }
        """
        request_id = new_request_id()
        log_section(logger, "NEW CHAT REQUEST")
        logger.info(
            "request_id=%s query=%r document_id=%s top_k=%s",
            request_id, query, document_id, top_k,
        )

        start = time.perf_counter()
        result = self._graph.invoke(
            {
                "query": query,
                "document_id": document_id,
                "top_k": top_k,
                "chat_history": chat_history or [],
            }
        )
        elapsed = (time.perf_counter() - start) * 1000

        log_section(logger, "CHAT REQUEST COMPLETE")
        logger.info(
            "request_id=%s total_time=%.1fms sources_used=%d",
            request_id, elapsed, len(result["sources"]),
        )

        return {"answer": result["answer"], "sources": result["sources"]}
