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

from app.core.exceptions import RetrievalError, WebSearchError
from app.core.logging_config import log_kv, truncate
from app.utils.logging_utils import log_node
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.web_search_service import WebSearchService

logger = logging.getLogger("rag.graph")

NO_CONTEXT_ANSWER = "I couldn't find any relevant information to answer that."
WEB_SEARCH_ALSO_FAILED_ANSWER = (
    "I couldn't find anything in the knowledge base, and the web search "
    "didn't return any results either."
)


def make_intent_detection_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    @log_node("detect_intent")
    def detect_intent(state: RAGState) -> dict:
        chat_history = state.get("chat_history") or []
        original_query = state["query"]

        log_kv(logger, query=original_query, chat_history_turns=len(chat_history))

        if not chat_history:
            logger.info("No chat history -> classified as STANDALONE (LLM call skipped)")
            return {"is_followup": False, "original_query": original_query}

        is_followup = llm_service.detect_followup_intent(original_query, chat_history)
        logger.info("Intent detected: %s", "FOLLOWUP" if is_followup else "STANDALONE")
        return {"is_followup": is_followup, "original_query": original_query}

    return detect_intent


def make_rewrite_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    @log_node("rewrite_query")
    def rewrite_query(state: RAGState) -> dict:
        original = state["query"]
        rewritten = llm_service.rewrite_query(original, state.get("chat_history") or [])

        # log_kv(logger, original_query=original, rewritten_query=rewritten)

        return {"query": rewritten}

    return rewrite_query


def make_retrieve_node(retrieval_service: RetrievalService) -> Callable[[RAGState], dict]:
    @log_node("retrieve")
    def retrieve(state: RAGState) -> dict:
        query = state["query"]
        top_k = state.get("top_k")
        document_id = state.get("document_id")

        log_kv(
            logger,
            query=query,
            top_k=top_k or "(default)",
            document_id=document_id or "(all documents)",
        )

        try:
            chunks = retrieval_service.retrieve(query, top_k=top_k, document_id=document_id)
        except Exception as exc:
            logger.exception("Retrieval failed for query")
            raise RetrievalError(str(exc)) from exc

        if not chunks:
            logger.warning("No chunks passed the similarity threshold — context will be empty")
        else:
            logger.info("Retrieved %d chunk(s):", len(chunks))
            for i, chunk in enumerate(chunks, start=1):
                source = chunk.metadata.get("source_file", "unknown")
                logger.info(
                    "    [%d] score=%.3f source=%s\n        content: %s",
                    i,
                    chunk.score,
                    source,
                    truncate(chunk.text),
                )

        context = retrieval_service.format_context(chunks)
        return {"chunks": chunks, "context": context}

    return retrieve


def make_websearch_node(web_search_service: WebSearchService) -> Callable[[RAGState], dict]:
    """
    Fallback node — only reached when `retrieve` found zero chunks (see
    `route_after_retrieve` in app/graph/build.py). A failure here is
    deliberately swallowed rather than propagated: this is already the
    fallback path, so an MCP/web-search error should degrade to
    "no results" and let `generate` produce the "even web search failed"
    answer, not 500 the whole request the way a `retrieve` failure does.
    """

    @log_node("web_search")
    async def web_search(state: RAGState) -> dict:
        query = state["query"]
        log_kv(logger, query=query)

        try:
            response = await web_search_service.asearch(query)
        except WebSearchError as exc:
            logger.warning("Web search fallback failed: %s", exc.message)
            return {"web_search_used": True, "web_search_results": [], "web_search_context": ""}

        if not response.found_results:
            logger.warning("Web search returned no results")
        else:
            logger.info("Web search returned %d result(s):", len(response.results))
            for i, result in enumerate(response.results, start=1):
                logger.info(
                    "    [%d] source=%s url=%s\n        snippet: %s",
                    i, result.source_name, result.url, truncate(result.snippet),
                )

        return {
            "web_search_used": True,
            "web_search_results": response.results,
            "web_search_context": response.context,
        }

    return web_search


def make_generate_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    @log_node("generate")
    async def generate(state: RAGState) -> dict:
        chunks = state.get("chunks", [])

        if chunks:
            logger.info("Generating answer using %d chunk(s) as context", len(chunks))
            answer_text = await llm_service.agenerate_answer(
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
            log_kv(logger, answer=truncate(answer_text), sources_used=len(sources))
            return {"answer": answer_text, "sources": sources}

        web_results = state.get("web_search_results") or []

        if state.get("web_search_used") and web_results:
            logger.info("No chunks -> generating answer from %d web search result(s)", len(web_results))
            answer_text = await llm_service.agenerate_answer(
                question=state["query"], context=state["web_search_context"]
            )
            sources = [
                {
                    "text": r.snippet,
                    "source_file": r.source_name,
                    "score": 0.0,
                }
                for r in web_results
            ]
            log_kv(logger, answer=truncate(answer_text), sources_used=len(sources))
            return {"answer": answer_text, "sources": sources}

        if state.get("web_search_used"):
            logger.info("No chunks and web search found nothing -> returning canned answer")
            return {"answer": WEB_SEARCH_ALSO_FAILED_ANSWER, "sources": []}

        logger.info("No chunks in state -> returning canned no-context answer")
        return {"answer": NO_CONTEXT_ANSWER, "sources": []}

    return generate
