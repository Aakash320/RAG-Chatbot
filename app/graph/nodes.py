"""
Graph nodes for the RAG pipeline.

Each node is a plain function of `RAGState -> dict` (a partial state
update). The nodes themselves don't hold any logic beyond orchestration —
they delegate to the existing `RetrievalService` / `LLMService`, which are
unchanged. This is the same split that `ChatController.answer()` used to
do inline; it's just re-hosted as graph nodes so the `retrieve -> generate`
step is now a first-class part of the graph.

`make_retrieve_node` / `make_generate_node` are factories (rather than
classes) so the compiled graph can close over the already-constructed
services from `app/state.py` without LangGraph needing to know about
dependency injection at all.
"""

import logging
from typing import Callable

from app.core.exceptions import RetrievalError
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

NO_CONTEXT_ANSWER = "I couldn't find any relevant information to answer that."


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
