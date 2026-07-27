"""
Graph nodes for the RAG pipeline.

Each node is a plain function of `RAGState -> dict` (a partial state
update). The nodes themselves don't hold any logic beyond orchestration —
they delegate to the existing `RetrievalService` / `LLMService` /
`WebSearchService` / `ScheduleService`, which are unchanged.

`make_*_node` are factories (rather than classes) so the compiled graph
can close over the already-constructed services from `app/state.py`
without LangGraph needing to know about dependency injection at all.
"""

import logging
import re
from typing import Callable

from app.core.exceptions import RetrievalError, ScheduleError, WebSearchError
from app.core.logging_config import log_kv, truncate
from app.utils.logging_utils import log_node
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.schedule_service import ScheduleService
from app.services.web_search_service import WebSearchService

logger = logging.getLogger("rag.graph")

NO_CONTEXT_ANSWER = "I couldn't find any relevant information to answer that."
WEB_SEARCH_ALSO_FAILED_ANSWER = (
    "I couldn't find anything in the knowledge base, and the web search "
    "didn't return any results either."
)
UNSUPPORTED_ACTION_ANSWER = (
    "I can currently help with answering questions from your documents and "
    "managing schedules (adding or listing appointments) — that's not "
    "something I support yet."
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _is_valid_date(value: str | None) -> bool:
    return bool(value) and bool(_DATE_RE.match(value))


def _is_valid_time(value: str | None) -> bool:
    return bool(value) and bool(_TIME_RE.match(value))


def make_intent_detection_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    """Top-level routing: QA vs SCHEDULE vs UNSUPPORTED."""

    @log_node("detect_intent")
    def detect_intent(state: RAGState) -> dict:
        original_query = state["query"]
        log_kv(logger, query=original_query)

        intent = llm_service.classify_intent(original_query)
        logger.info("Top-level intent detected: %s", intent.upper())
        return {"intent": intent, "original_query": original_query}

    return detect_intent


def make_followup_detection_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    """QA branch only — the old `detect_intent` body, gated behind routing now."""

    @log_node("classify_followup")
    def classify_followup(state: RAGState) -> dict:
        chat_history = state.get("chat_history") or []
        query = state["query"]

        log_kv(logger, query=query, chat_history_turns=len(chat_history))

        if not chat_history:
            logger.info("No chat history -> classified as STANDALONE (LLM call skipped)")
            return {"is_followup": False}

        is_followup = llm_service.detect_followup_intent(query, chat_history)
        logger.info("Follow-up classification: %s", "FOLLOWUP" if is_followup else "STANDALONE")
        return {"is_followup": is_followup}

    return classify_followup


def make_rewrite_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    @log_node("rewrite_query")
    def rewrite_query(state: RAGState) -> dict:
        original = state["query"]
        rewritten = llm_service.rewrite_query(original, state.get("chat_history") or [])
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


def make_schedule_classification_node(llm_service: LLMService) -> Callable[[RAGState], dict]:
    """SCHEDULE branch only — decide add vs list, extract fields."""

    @log_node("classify_schedule")
    def classify_schedule(state: RAGState) -> dict:
        query = state["query"]
        log_kv(logger, query=query)

        parsed = llm_service.classify_schedule_action(query)
        logger.info(
            "Schedule classification: action=%s description=%r date=%r time=%r",
            parsed["action"], parsed["description"], parsed["date"], parsed["time"],
        )
        return {
            "schedule_action": parsed["action"],
            "schedule_description": parsed["description"],
            "schedule_date": parsed["date"],
            "schedule_time": parsed["time"],
        }

    return classify_schedule


def make_schedule_add_node(schedule_service: ScheduleService) -> Callable[[RAGState], dict]:
    @log_node("schedule_add")
    async def schedule_add(state: RAGState) -> dict:
        user_id = state.get("user_id")
        description = (state.get("schedule_description") or "").strip()
        time = state.get("schedule_time")
        raw_date = state.get("schedule_date")

        log_kv(logger, user_id=user_id, description=description, date=raw_date, time=time)

        if not description or not _is_valid_time(time):
            logger.warning("Missing/invalid description or time for schedule_add — asking user to clarify")
            return {
                "answer": (
                    "I couldn't tell what to schedule or what time — could you rephrase "
                    "with a clear time, e.g. \"dentist appointment at 3pm\"?"
                ),
                "sources": [],
            }

        date = raw_date if _is_valid_date(raw_date) else None  # None -> MCP tool defaults to today

        try:
            record = await schedule_service.add_schedule(
                user_id=user_id, description=description, time=time, date=date
            )
        except ScheduleError as exc:
            logger.warning("schedule_add failed: %s", exc.message)
            raise

        answer = f'Got it — added "{record["description"]}" on {record["date"]} at {record["time"]}.'
        log_kv(logger, answer=answer)
        return {"answer": answer, "sources": []}

    return schedule_add


def make_schedule_list_node(schedule_service: ScheduleService) -> Callable[[RAGState], dict]:
    @log_node("schedule_list")
    async def schedule_list(state: RAGState) -> dict:
        user_id = state.get("user_id")
        raw_date = state.get("schedule_date")
        date = raw_date if _is_valid_date(raw_date) else None

        log_kv(logger, user_id=user_id, date=date or "(all)")

        try:
            records = await schedule_service.list_schedules(user_id=user_id, date=date)
        except ScheduleError as exc:
            logger.warning("schedule_list failed: %s", exc.message)
            raise

        if not records:
            answer = f"You don't have any schedules{f' for {date}' if date else ''}."
        else:
            lines = [f"- {r['date']} at {r['time']}: {r['description']}" for r in records]
            answer = "Here's what you have scheduled:\n" + "\n".join(lines)

        log_kv(logger, answer=truncate(answer), record_count=len(records))
        return {"answer": answer, "sources": []}

    return schedule_list


def make_unsupported_action_node() -> Callable[[RAGState], dict]:
    @log_node("unsupported_action")
    def unsupported_action(state: RAGState) -> dict:
        logger.info("Query classified as an unsupported action")
        return {"answer": UNSUPPORTED_ACTION_ANSWER, "sources": []}

    return unsupported_action