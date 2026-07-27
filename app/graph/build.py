r"""
Graph construction.

Wires the nodes into a compiled LangGraph. This is the single place that
knows the graph's shape — `ChatController` just invokes the compiled
graph and doesn't know it's a graph at all.

Shape:

    START -> detect_intent --(qa)---------> classify_followup --(followup)--> rewrite_query -> retrieve --(chunks)--> generate -> END
                            |                                 \--(standalone)---------------------^      \--(no chunks)--> web_search -^
                            --(schedule)---> classify_schedule --(add)----> schedule_add  -> END
                            |                                 \--(list)---> schedule_list -> END
                            --(unsupported)-------------------------------> unsupported_action -> END

`detect_intent` always runs first and decides the top-level branch (QA /
SCHEDULE / UNSUPPORTED). The QA branch is unchanged from before (a
`classify_followup` step, then optionally `rewrite_query`, then
`retrieve` -> `web_search`? -> `generate`). The SCHEDULE branch runs a
second classification (`classify_schedule`) to decide add vs list, then
calls the matching terminal node directly. `schedule_add`, `schedule_list`,
and `unsupported_action` all write `answer`/`sources` themselves (a fixed
template, not an LLM call) and go straight to END — `generate` is only
ever reached from the QA branch.
"""

import logging
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.config import settings
from app.graph.nodes import (
    make_followup_detection_node,
    make_generate_node,
    make_intent_detection_node,
    make_retrieve_node,
    make_rewrite_node,
    make_schedule_add_node,
    make_schedule_classification_node,
    make_schedule_list_node,
    make_unsupported_action_node,
    make_websearch_node,
)
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.schedule_service import ScheduleService
from app.services.web_search_service import WebSearchService


def route_after_intent(state: RAGState) -> str:
    intent = state.get("intent", "qa")
    next_node = {
        "qa": "classify_followup",
        "schedule": "classify_schedule",
        "unsupported": "unsupported_action",
    }.get(intent, "classify_followup")
    logging.getLogger("rag.graph").info(
        "ROUTING DECISION -> intent=%s -> next node: %s", intent, next_node
    )
    return next_node


def route_after_followup(state: RAGState) -> str:
    next_node = "rewrite_query" if state.get("is_followup") else "retrieve"
    logging.getLogger("rag.graph").info(
        "ROUTING DECISION -> is_followup=%s -> next node: %s",
        state.get("is_followup"),
        next_node,
    )
    return next_node


def route_after_retrieve(state: RAGState) -> str:
    chunks = state.get("chunks") or []
    next_node = "generate" if (chunks or not settings.WEB_SEARCH_ENABLED) else "web_search"
    logging.getLogger("rag.graph").info(
        "ROUTING DECISION -> chunks_found=%d -> next node: %s",
        len(chunks),
        next_node,
    )
    return next_node


def route_after_schedule_classification(state: RAGState) -> str:
    action = state.get("schedule_action", "add")
    next_node = "schedule_list" if action == "list" else "schedule_add"
    logging.getLogger("rag.graph").info(
        "ROUTING DECISION -> schedule_action=%s -> next node: %s", action, next_node
    )
    return next_node


def build_rag_graph(
    retrieval_service: RetrievalService,
    llm_service: LLMService,
    web_search_service: WebSearchService,
    schedule_service: ScheduleService,
) -> CompiledStateGraph:
    graph = StateGraph(RAGState)

    graph.add_node("detect_intent", make_intent_detection_node(llm_service))
    graph.add_node("classify_followup", make_followup_detection_node(llm_service))
    graph.add_node("rewrite_query", make_rewrite_node(llm_service))
    graph.add_node("retrieve", make_retrieve_node(retrieval_service))
    graph.add_node("web_search", make_websearch_node(web_search_service))
    graph.add_node("generate", make_generate_node(llm_service))
    graph.add_node("classify_schedule", make_schedule_classification_node(llm_service))
    graph.add_node("schedule_add", make_schedule_add_node(schedule_service))
    graph.add_node("schedule_list", make_schedule_list_node(schedule_service))
    graph.add_node("unsupported_action", make_unsupported_action_node())

    graph.add_edge(START, "detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {
            "classify_followup": "classify_followup",
            "classify_schedule": "classify_schedule",
            "unsupported_action": "unsupported_action",
        },
    )

    graph.add_conditional_edges(
        "classify_followup",
        route_after_followup,
        {"rewrite_query": "rewrite_query", "retrieve": "retrieve"},
    )
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"generate": "generate", "web_search": "web_search"},
    )
    graph.add_edge("web_search", "generate")
    graph.add_edge("generate", END)

    graph.add_conditional_edges(
        "classify_schedule",
        route_after_schedule_classification,
        {"schedule_add": "schedule_add", "schedule_list": "schedule_list"},
    )
    graph.add_edge("schedule_add", END)
    graph.add_edge("schedule_list", END)

    graph.add_edge("unsupported_action", END)

    return graph.compile()
