"""
Chat controller — RAG retrieve-then-generate orchestration.

The orchestration (embed query -> retrieve top-k chunks -> build context
-> call the LLM) lives in a compiled LangGraph graph (`app/graph/build.py`).
This controller drives that graph with `astream_events`, which gives us
two things simultaneously, for free:

1. Node-level lifecycle events (`on_chain_start` / `on_chain_end`) for
   each of detect_intent / rewrite_query / retrieve / generate — turned
   into "status" events for the frontend (and the basis for a future
   "thought chain" UI).
2. Token-level events (`on_chat_model_stream`) emitted specifically while
   the `generate` node's LLM call is running — turned into "token" events
   streamed to the frontend as they're produced.

Every event LangGraph emits is tagged with `metadata["langgraph_node"]`
identifying which node it happened inside, which is what lets us tell
"the generate node's own start/end" apart from "a token streamed by the
chat model *inside* the generate node" without any guesswork.
"""

import logging
import time
from typing import AsyncGenerator

from app.core.exceptions import AppError
from app.core.logging_config import log_section, new_request_id, truncate
from app.graph.build import build_rag_graph
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger("rag.controller")

_NODE_NAMES = {"detect_intent", "rewrite_query", "retrieve", "generate"}

_START_MESSAGES = {
    "detect_intent": "Detecting whether this is a follow-up question...",
    "rewrite_query": "Rewriting follow-up into a standalone question...",
    "retrieve": "Searching the knowledge base...",
    "generate": "Generating the answer...",
}


def _end_status(node_name: str, output: dict) -> dict:
    """Builds the human-readable status payload for a node's completion."""
    if node_name == "detect_intent":
        is_followup = output.get("is_followup", False)
        return {
            "step": node_name,
            "phase": "end",
            "message": f"Classified as {'FOLLOW-UP' if is_followup else 'STANDALONE'}",
            "detail": {"is_followup": is_followup},
        }

    if node_name == "rewrite_query":
        return {
            "step": node_name,
            "phase": "end",
            "message": "Rewrote query into a standalone question",
            "detail": {"rewritten_query": output.get("query", "")},
        }

    if node_name == "retrieve":
        chunks = output.get("chunks", [])
        return {
            "step": node_name,
            "phase": "end",
            "message": f"Retrieved {len(chunks)} chunk(s)",
            "detail": {
                "chunks": [
                    {
                        "source_file": c.metadata.get("source_file", "unknown"),
                        "score": c.score,
                        "text": truncate(c.text, 200),
                    }
                    for c in chunks
                ]
            },
        }

    if node_name == "generate":
        return {"step": node_name, "phase": "end", "message": "Answer generation complete"}

    return {"step": node_name, "phase": "end", "message": node_name}


class ChatController:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self._graph = build_rag_graph(retrieval_service, llm_service)

    async def astream_answer(
        self,
        query: str,
        document_id: str | None = None,
        top_k: int | None = None,
        chat_history: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Async generator yielding dicts shaped like:
            {"event": "status", "data": {"step": ..., "phase": ..., "message": ..., "detail": {...}}}
            {"event": "token",  "data": {"text": "..."}}
            {"event": "done",   "data": {"answer": "...", "sources": [...]}}
            {"event": "error",  "data": {"detail": "..."}}

        The caller (the SSE endpoint) is responsible for wire-formatting
        these as `event: ...\\ndata: ...\\n\\n` lines.
        """
        request_id = new_request_id()
        log_section(logger, "NEW STREAMING CHAT REQUEST")
        logger.info(
            "request_id=%s query=%r document_id=%s top_k=%s",
            request_id, query, document_id, top_k,
        )

        inputs = {
            "query": query,
            "document_id": document_id,
            "top_k": top_k,
            "chat_history": chat_history or [],
        }

        start = time.perf_counter()
        final_answer = ""
        final_sources: list[dict] = []

        try:
            async for event in self._graph.astream_events(inputs, version="v2"):
                node = event.get("metadata", {}).get("langgraph_node")
                kind = event["event"]
                name = event.get("name")

                # Node lifecycle -> status events. `name == node` excludes
                # nested runnables (prompt templates, parsers, etc.) that
                # share the same langgraph_node metadata but aren't the
                # node itself.
                if kind == "on_chain_start" and name in _NODE_NAMES and name == node:
                    yield {
                        "event": "status",
                        "data": {"step": name, "phase": "start", "message": _START_MESSAGES.get(name, name)},
                    }

                elif kind == "on_chain_end" and name in _NODE_NAMES and name == node:
                    output = event["data"].get("output") or {}
                    yield {"event": "status", "data": _end_status(name, output)}
                    if name == "generate":
                        final_answer = output.get("answer", "")
                        final_sources = output.get("sources", [])

                # Token-level streaming, scoped to the generate node only.
                elif kind == "on_chat_model_stream" and node == "generate":
                    chunk = event["data"]["chunk"]
                    text = getattr(chunk, "content", "") or ""
                    if text:
                        yield {"event": "token", "data": {"text": text}}

        except AppError as exc:
            logger.exception("Streaming chat request failed")
            yield {"event": "error", "data": {"detail": exc.message}}
            return
        except Exception as exc:
            logger.exception("Streaming chat request failed")
            yield {"event": "error", "data": {"detail": str(exc)}}
            return

        elapsed = (time.perf_counter() - start) * 1000
        log_section(logger, "STREAMING CHAT REQUEST COMPLETE")
        logger.info(
            "request_id=%s total_time=%.1fms sources_used=%d",
            request_id, elapsed, len(final_sources),
        )

        yield {"event": "done", "data": {"answer": final_answer, "sources": final_sources}}