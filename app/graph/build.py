"""
Graph construction.

Wires the retrieve/generate nodes into a compiled LangGraph. This is the
single place that knows the graph's shape — `ChatController` just invokes
the compiled graph and doesn't know it's a graph at all.

Currently a straight line: retrieve -> generate. The similarity-threshold
/ query-rewrite conditional loop (retrieve -> check -> rewrite -> retrieve)
will be added here later as a conditional edge out of "retrieve" — nothing
elsewhere needs to change when that happens.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes import make_generate_node, make_retrieve_node
from app.graph.state import RAGState
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService


def build_rag_graph(
    retrieval_service: RetrievalService, llm_service: LLMService
) -> CompiledStateGraph:
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", make_retrieve_node(retrieval_service))
    graph.add_node("generate", make_generate_node(llm_service))

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()
