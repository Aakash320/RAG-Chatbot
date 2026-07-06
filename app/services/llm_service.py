"""
LLM service.

Wraps the Groq-backed chat model via langchain_groq. The prompt templates
and chain construction live here. There are three chains, one per distinct
LLM job the app needs:

- `self._chain`         answer the question using retrieved context
- `self._intent_chain`  classify the query as FOLLOWUP vs STANDALONE
- `self._rewrite_chain` rewrite a follow-up query into a standalone one

Each is a fixed `prompt | llm | parser` pipeline, so a different prompt
needs a different chain object; the underlying `self._llm` client is
constructed once and reused across all three.
"""

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.config import settings
from app.core.exceptions import LLMGenerationError
import logging

logger = logging.getLogger("rag.llm")

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the \
provided context. If the answer cannot be found in the context, say you don't know — \
do not make up an answer.

Context:
{context}
"""

INTENT_SYSTEM_PROMPT = """You are a routing classifier for a RAG chatbot. Given the \
conversation history and the user's latest message, decide whether the latest message \
is a FOLLOWUP question that depends on prior conversation turns to be understood \
(e.g. it uses pronouns, is elliptical, or references something said earlier), or a \
STANDALONE question that can be fully understood on its own.

Conversation history:
{chat_history}

Latest user message: {query}

Respond with exactly one word — FOLLOWUP or STANDALONE — and nothing else."""

REWRITE_SYSTEM_PROMPT = """Given the conversation history and the user's latest \
follow-up message, rewrite the latest message into a fully self-contained, standalone \
question that can be understood without the conversation history. Preserve the user's \
original intent and phrasing style. Do not answer the question — only rewrite it.

Conversation history:
{chat_history}

Latest user message: {query}

Standalone question:"""


def _format_chat_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return "(none)"
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in chat_history)


class LLMService:
    def __init__(
        self,
        model_name: str = settings.GROQ_MODEL_NAME,
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: int = settings.LLM_MAX_TOKENS,
    ) -> None:
        self._llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "{question}"),
            ]
        )

        self._chain = self._prompt | self._llm | StrOutputParser()

        self._intent_prompt = ChatPromptTemplate.from_messages(
            [("system", INTENT_SYSTEM_PROMPT)]
        )
        self._intent_chain = self._intent_prompt | self._llm | StrOutputParser()

        self._rewrite_prompt = ChatPromptTemplate.from_messages(
            [("system", REWRITE_SYSTEM_PROMPT)]
        )
        self._rewrite_chain = self._rewrite_prompt | self._llm | StrOutputParser()

    def generate_answer(self, question: str, context: str) -> str:
        logger.info("Calling LLM to generate final answer (context length=%d chars)", len(context))
        try:
            answer = self._chain.invoke({"question": question, "context": context})
            logger.info("LLM answer received (%d chars)", len(answer))
            return answer
        except Exception as exc:
            logger.exception("LLM generation failed")
            raise LLMGenerationError("The language model failed to generate a response") from exc

    async def agenerate_answer(self, question: str, context: str) -> str:
        try:
            return await self._chain.ainvoke({"question": question, "context": context})
        except Exception as exc:
            logger.exception("LLM generation failed")
            raise LLMGenerationError("The language model failed to generate a response") from exc

    def detect_followup_intent(self, query: str, chat_history: list[dict]) -> bool:
        logger.info("Calling LLM intent classifier (%d history turns)", len(chat_history))
        try:
            result = self._intent_chain.invoke(
                {"query": query, "chat_history": _format_chat_history(chat_history)}
            )
        except Exception as exc:
            logger.exception("Intent detection failed")
            raise LLMGenerationError("Intent detection failed") from exc
        logger.info("Raw intent classifier output: %r", result.strip())
        return result.strip().upper().startswith("FOLLOWUP")

    def rewrite_query(self, query: str, chat_history: list[dict]) -> str:
        logger.info("Calling LLM to rewrite follow-up query: %r", query)
        try:
            rewritten = self._rewrite_chain.invoke(
                {"query": query, "chat_history": _format_chat_history(chat_history)}
            ).strip()
        except Exception as exc:
            logger.exception("Query rewrite failed")
            raise LLMGenerationError("Query rewrite failed") from exc
        logger.info("LLM rewrite output: %r", rewritten)
        return rewritten


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()
