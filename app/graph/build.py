r"""
Graph construction.

Wires the nodes into a compiled LangGraph. This is the single place that
knows the graph's shape — `ChatController` just invokes the compiled
graph and doesn't know it's a graph at all.

Shape:

    START -> detect_intent --(followup)--> rewrite_query -> retrieve --(chunks found)--> generate -> END
                            \--(standalone)-------------------^      \--(no chunks)--> web_search -^

`detect_intent` always runs first. If the query is classed as a
follow-up, `rewrite_query` runs before `retrieve`; otherwise `retrieve`
runs directly. After `retrieve`, `web_search` is only reached as a
fallback when zero chunks passed the similarity threshold — otherwise
`retrieve` goes straight to `generate`. Either way, `generate` is the
single place a final answer gets produced.
"""

import logging
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.config import settings
from app.graph.nodes import (
    make_generate_node,
    make_intent_detection_node,
    make_retrieve_node,
    make_rewrite_node,
    make_websearch_node,
)
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.web_search_service import WebSearchService


def route_after_intent(state: RAGState) -> str:
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


def build_rag_graph(
    retrieval_service: RetrievalService,
    llm_service: LLMService,
    web_search_service: WebSearchService,
) -> CompiledStateGraph:
    graph = StateGraph(RAGState)

    graph.add_node("detect_intent", make_intent_detection_node(llm_service))
    graph.add_node("rewrite_query", make_rewrite_node(llm_service))
    graph.add_node("retrieve", make_retrieve_node(retrieval_service))
    graph.add_node("web_search", make_websearch_node(web_search_service))
    graph.add_node("generate", make_generate_node(llm_service))

    graph.add_edge(START, "detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        route_after_intent,
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

    return graph.compile()
