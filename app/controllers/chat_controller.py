"""
Chat controller — RAG retrieve-then-generate orchestration.

Orchestrates: embed query -> retrieve top-k chunks -> build context ->
call the LLM -> return answer + sources.

Returns a plain dict; the API layer reshapes it into the `ChatResponse`
schema. LLM-call failures propagate as-is for the API layer to translate.
"""

import logging

from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.core.exceptions import RetrievalError

logger = logging.getLogger(__name__)


class ChatController:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self._retrieval = retrieval_service
        self._llm = llm_service

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
        try:
            chunks = self._retrieval.retrieve(query, top_k=top_k, document_id=document_id)
        except Exception as exc:
            logger.exception("Retrieval failed for query")
            raise RetrievalError(str(exc)) from exc

        if not chunks:
            return {
                "answer": "I couldn't find any relevant information to answer that.",
                "sources": [],
            }

        context = self._retrieval.format_context(chunks)
        answer_text = self._llm.generate_answer(question=query, context=context)

        sources = [
            {
                "text": c.text,
                "source_file": c.metadata.get("source_file", "unknown"),
                "score": c.score,
            }
            for c in chunks
        ]

        return {"answer": answer_text, "sources": sources}
