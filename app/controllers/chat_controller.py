"""
Chat controller — RAG retrieve-then-generate orchestration.

The orchestration itself (embed query -> retrieve top-k chunks -> build
context -> call the LLM) now lives in a compiled LangGraph graph
(`app/graph/build.py`); this controller just builds that graph once and
invokes it per request.

Returns a plain dict; the API layer reshapes it into the `ChatResponse`
schema. Errors raised inside graph nodes (e.g. `RetrievalError`,
`LLMGenerationError`) propagate through `.invoke()` unchanged, so the
existing `AppError` exception handlers in `app/core/exceptions.py` still
catch them exactly as before.
"""

from app.graph.build import build_rag_graph
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService


class ChatController:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self._graph = build_rag_graph(retrieval_service, llm_service)

    def answer(
        self,
        query: str,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> dict:
        """
        Returns a dict shaped like:
        {
            "answer": str,
            "sources": [{"text": str, "source_file": str, "score": float}, ...]
        }
        """
        result = self._graph.invoke(
            {"query": query, "document_id": document_id, "top_k": top_k}
        )
        return {"answer": result["answer"], "sources": result["sources"]}
