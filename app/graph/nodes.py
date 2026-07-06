"""
Graph nodes for the RAG pipeline.

Each node is a plain function of `RAGState -> dict` (a partial state
update). The nodes themselves don't hold any logic beyond orchestration —
they delegate to the existing `RetrievalService` / `LLMService`, which are
unchanged.

`make_*_node` are factories (rather than classes) so the compiled graph
can close over the already-constructed services from `app/state.py`
without LangGraph needing to know about dependency injection at all.
"""

import logging
from typing import Callable

from app.core.exceptions import RetrievalError
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

NO_CONTEXT_ANSWER = "I couldn't find any relevant information to answer that."


def make_intent_detection_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    def detect_intent(state: RAGState) -> dict:
        chat_history = state.get("chat_history") or []
        original_query = state["query"]

        # No history at all -> can't be a follow-up. Skip the LLM call.
        if not chat_history:
            return {"is_followup": False, "original_query": original_query}

        is_followup = llm_service.detect_followup_intent(original_query, chat_history)
        return {"is_followup": is_followup, "original_query": original_query}

    return detect_intent


def make_rewrite_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    def rewrite_query(state: RAGState) -> dict:
        rewritten = llm_service.rewrite_query(
            state["query"], state.get("chat_history") or []
        )
        # Overwrite `query` in place so `retrieve` doesn't need to know
        # a rewrite happened.
        return {"query": rewritten}

    return rewrite_query


def make_retrieve_node(retrieval_service: RetrievalService) -> Callable[[RAGState], dict]:
    def retrieve(state: RAGState) -> dict:
        try:
            chunks = retrieval_service.retrieve(
                state["query"],
                top_k=state.get("top_k"),
                document_id=state.get("document_id"),
            )
        except Exception as exc:
            logger.exception("Retrieval failed for query")
            raise RetrievalError(str(exc)) from exc

        return {
            "chunks": chunks,
            "context": retrieval_service.format_context(chunks),
        }

    return retrieve


def make_generate_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    def generate(state: RAGState) -> dict:
        chunks = state.get("chunks", [])

        if not chunks:
            return {"answer": NO_CONTEXT_ANSWER, "sources": []}

        answer_text = llm_service.generate_answer(
            question=state["query"], context=state["context"]
        )

        sources = [
            {
                "text": c.text,
                "source_file": c.metadata.get("source_file", "unknown"),
                "score": c.score,
            }
            for c in chunks
        ]

        return {"answer": answer_text, "sources": sources}

    return generate
