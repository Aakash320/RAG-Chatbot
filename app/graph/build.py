r"""
Graph construction.

Wires the nodes into a compiled LangGraph. This is the single place that
knows the graph's shape — `ChatController` just invokes the compiled
graph and doesn't know it's a graph at all.

Shape:

    START -> detect_intent --(followup)--> rewrite_query -> retrieve -> generate -> END
                            \--(standalone)-------------------^

`detect_intent` always runs first. If the query is classed as a
follow-up, `rewrite_query` runs before `retrieve`; otherwise `retrieve`
runs directly.
"""

import logging
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes import (
    make_generate_node,
    make_intent_detection_node,
    make_retrieve_node,
    make_rewrite_node,
)
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService


def route_after_intent(state: RAGState) -> str:
    next_node = "rewrite_query" if state.get("is_followup") else "retrieve"
    logging.getLogger("rag.graph").info(
        "ROUTING DECISION -> is_followup=%s -> next node: %s",
        state.get("is_followup"),
        next_node,
    )
    return next_node


def build_rag_graph(
    retrieval_service: RetrievalService, llm_service: LLMService
) -> CompiledStateGraph:
    graph = StateGraph(RAGState)

    graph.add_node("detect_intent", make_intent_detection_node(llm_service))
    graph.add_node("rewrite_query", make_rewrite_node(llm_service))
    graph.add_node("retrieve", make_retrieve_node(retrieval_service))
    graph.add_node("generate", make_generate_node(llm_service))

    graph.add_edge(START, "detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {"rewrite_query": "rewrite_query", "retrieve": "retrieve"},
    )
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()
