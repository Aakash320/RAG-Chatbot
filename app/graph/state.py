"""
Graph state for the RAG pipeline.

`RAGState` is the dict that flows between nodes. Each node reads whatever
keys it needs and returns a partial dict of updates, which LangGraph
merges back into the state before invoking the next node.

`total=False` means every key is optional at the type level — a node
only has to supply the keys it actually produces. `query`/`document_id`/
`top_k`/`user_id` are seeded by the caller when the graph is invoked;
the rest are filled in as the graph runs.
"""

from typing import Literal, TypedDict

from app.models.schemas import WebSearchResult
from app.vectorstores.base import RetrievedChunk


class RAGState(TypedDict, total=False):
    # Set by the caller at invocation time.
    query: str
    document_id: str | None
    top_k: int | None
    chat_history: list[dict]  # [{"role": "user" | "assistant", "content": str}, ...]
    user_id: str  # required for the schedule branch; unused elsewhere

    # Set by the `detect_intent` node (top-level routing).
    original_query: str
    intent: Literal["qa", "schedule", "unsupported"]

    # Set by the `classify_followup` node (QA branch only).
    is_followup: bool

    # `rewrite_query` overwrites `query` in place (no new key), so
    # `retrieve` doesn't need to know whether a rewrite happened.

    # Set by the `retrieve` node.
    chunks: list[RetrievedChunk]
    context: str

    # Set by the `web_search` node (only runs when `retrieve` found no
    # chunks). `web_search_used` distinguishes "ran and found nothing"
    # from "didn't run" for the `generate` node's three-way branch.
    web_search_used: bool
    web_search_results: list[WebSearchResult]
    web_search_context: str

    # Set by the `classify_schedule` node (SCHEDULE branch only). `date`/
    # `time` are the LLM's raw extraction — re-validated by schedule_add /
    # schedule_list before being sent to the MCP tool.
    schedule_action: Literal["add", "list"]
    schedule_description: str | None
    schedule_date: str | None
    schedule_time: str | None

    # Set by `generate` / `schedule_add` / `schedule_list` /
    # `unsupported_action` — every terminal node writes this same shape,
    # which is what lets ChatController treat them identically.
    answer: str
    sources: list[dict]