"""
Graph state for the RAG pipeline.

`RAGState` is the dict that flows between nodes. Each node reads whatever
keys it needs and returns a partial dict of updates, which LangGraph
merges back into the state before invoking the next node.

`total=False` means every key is optional at the type level — a node
only has to supply the keys it actually produces. `query`/`document_id`/
`top_k` are seeded by the caller when the graph is invoked; the rest are
filled in as the graph runs.
"""

from typing import TypedDict

from app.vectorstores.base import RetrievedChunk


class RAGState(TypedDict, total=False):
    # Set by the caller at invocation time.
    query: str
    document_id: str | None
    top_k: int | None

    # Set by the `retrieve` node.
    chunks: list[RetrievedChunk]
    context: str

    # Set by the `generate` node.
    answer: str
    sources: list[dict]
