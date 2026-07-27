"""
LLM service.

Wraps the Groq-backed chat model via langchain_groq. The prompt templates
and chain construction live here. There are five chains, one per distinct
LLM job the app needs:

- `self._chain`            answer the question using retrieved context
- `self._intent_chain`     top-level routing: QA vs SCHEDULE vs UNSUPPORTED
- `self._followup_chain`   (QA branch only) classify FOLLOWUP vs STANDALONE
- `self._rewrite_chain`    rewrite a follow-up query into a standalone one
- `self._schedule_chain`   (SCHEDULE branch only) classify ADD vs LIST + extract fields

Each is a fixed `prompt | llm | parser` pipeline, so a different prompt
needs a different chain object; the underlying `self._llm` client is
constructed once and reused across all of them.
"""

import json
import logging
import re
from datetime import date
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.config import settings
from app.core.exceptions import LLMGenerationError

logger = logging.getLogger("rag.llm")

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the \
provided context. If the answer cannot be found in the context, say you don't know — \
do not make up an answer.

Context:
{context}
"""

INTENT_SYSTEM_PROMPT = """You are a top-level routing classifier for a chatbot that can \
do two things: (1) answer questions from a document knowledge base, and (2) manage the \
user's schedule/appointments (adding new ones or listing existing ones).

Classify the user's latest message into exactly one of:
- QA: a question seeking information/knowledge (from documents or general knowledge), \
including follow-up questions that depend on prior conversation turns.
- SCHEDULE: a request to add a new appointment/schedule/reminder-with-a-time, OR a \
request to view/list existing schedules/appointments.
- UNSUPPORTED: a request to perform some OTHER action this assistant cannot do (e.g. \
deleting/editing/canceling a schedule, sending an email or message, setting an alarm, \
booking something, making a call, or any action beyond QA and schedule add/list).

Respond with exactly one word — QA, SCHEDULE, or UNSUPPORTED — and nothing else.

User message: {query}"""

FOLLOWUP_SYSTEM_PROMPT = """You are a routing classifier for a RAG chatbot. Given the \
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

SCHEDULE_SYSTEM_PROMPT = """You are a router for a scheduling assistant. Today's date is \
{today}. Given the user's message, decide whether they want to ADD a new schedule/\
appointment record or LIST their existing ones, and extract the relevant fields.

If the action is ADD:
- "description": a short summary of what the appointment/task is (e.g. "dentist \
appointment"). Required.
- "time": the time in 24-hour "HH:MM" format (e.g. "14:00" for 2pm). Required — do your \
best to infer it from however the user phrased it (e.g. "12 pm" -> "12:00", \
"half past 9 in the morning" -> "09:30"). Use null ONLY if genuinely no time was \
mentioned anywhere in the message.
- "date": "YYYY-MM-DD" ONLY if the user mentioned a specific date (resolve relative \
phrases like "tomorrow" using today's date above). Use null if no date was mentioned \
at all — it will default to today.

If the action is LIST:
- "date": "YYYY-MM-DD" ONLY if the user asked about one exact date, resolving "today" \
to {today}. Use null if they asked broadly (e.g. "what are my schedules") — do NOT \
guess a date for fuzzy ranges like "this week", since only exact-date or "today" \
filtering is supported right now.
- "description" and "time" are not used for LIST — always null.

Respond with ONLY a JSON object, no other text, no markdown code fences, in exactly \
this shape:
{{"action": "ADD" or "LIST", "description": string or null, "date": "YYYY-MM-DD" or null, "time": "HH:MM" or null}}

User message: {query}"""


def _format_chat_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return "(none)"
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in chat_history)


def _extract_json_object(raw: str) -> dict:
    """
    Best-effort JSON extraction from an LLM response that's supposed to be
    pure JSON but may come wrapped in markdown code fences or stray text.
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in LLM output: {raw!r}")
    return json.loads(text[start : end + 1])


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

        self._intent_prompt = ChatPromptTemplate.from_messages([("system", INTENT_SYSTEM_PROMPT)])
        self._intent_chain = self._intent_prompt | self._llm | StrOutputParser()

        self._followup_prompt = ChatPromptTemplate.from_messages([("system", FOLLOWUP_SYSTEM_PROMPT)])
        self._followup_chain = self._followup_prompt | self._llm | StrOutputParser()

        self._rewrite_prompt = ChatPromptTemplate.from_messages([("system", REWRITE_SYSTEM_PROMPT)])
        self._rewrite_chain = self._rewrite_prompt | self._llm | StrOutputParser()

        self._schedule_prompt = ChatPromptTemplate.from_messages([("system", SCHEDULE_SYSTEM_PROMPT)])
        self._schedule_chain = self._schedule_prompt | self._llm | StrOutputParser()

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
        logger.info("Calling LLM (async/streamed) to generate final answer (context length=%d chars)", len(context))
        try:
            answer = await self._chain.ainvoke({"question": question, "context": context})
            logger.info("LLM answer received (%d chars)", len(answer))
            return answer
        except Exception as exc:
            logger.exception("LLM generation failed")
            raise LLMGenerationError("The language model failed to generate a response") from exc

    def classify_intent(self, query: str) -> str:
        """Returns one of: "qa", "schedule", "unsupported"."""
        logger.info("Calling LLM top-level intent classifier")
        try:
            result = self._intent_chain.invoke({"query": query})
        except Exception as exc:
            logger.exception("Top-level intent classification failed")
            raise LLMGenerationError("Intent classification failed") from exc

        cleaned = result.strip().upper()
        logger.info("Raw top-level intent classifier output: %r", cleaned)
        if cleaned.startswith("SCHEDULE"):
            return "schedule"
        if cleaned.startswith("UNSUPPORTED"):
            return "unsupported"
        return "qa"

    def detect_followup_intent(self, query: str, chat_history: list[dict]) -> bool:
        logger.info("Calling LLM follow-up classifier (%d history turns)", len(chat_history))
        try:
            result = self._followup_chain.invoke(
                {"query": query, "chat_history": _format_chat_history(chat_history)}
            )
        except Exception as exc:
            logger.exception("Follow-up detection failed")
            raise LLMGenerationError("Follow-up detection failed") from exc
        logger.info("Raw follow-up classifier output: %r", result.strip())
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

    def classify_schedule_action(self, query: str) -> dict:
        """
        Returns a dict shaped like:
            {"action": "add" | "list", "description": str | None,
             "date": str | None, "time": str | None}

        `date`/`time` are the LLM's best-effort extraction, in
        YYYY-MM-DD / HH:MM format — not yet validated against the
        strict format the schedule MCP server requires. The caller
        (schedule_add / schedule_list nodes) is responsible for
        re-validating before calling the tool, since this is model
        output, not guaranteed-correct data.
        """
        today = date.today().isoformat()
        logger.info("Calling LLM schedule classifier (today=%s)", today)
        try:
            raw = self._schedule_chain.invoke({"query": query, "today": today})
        except Exception as exc:
            logger.exception("Schedule action classification failed")
            raise LLMGenerationError("Schedule action classification failed") from exc

        logger.info("Raw schedule classifier output: %r", raw.strip())
        try:
            parsed = _extract_json_object(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.exception("Could not parse schedule classifier output as JSON")
            raise LLMGenerationError("Could not parse schedule details from your message") from exc

        action = str(parsed.get("action", "")).strip().upper()
        return {
            "action": "list" if action == "LIST" else "add",
            "description": parsed.get("description") or None,
            "date": parsed.get("date") or None,
            "time": parsed.get("time") or None,
        }


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()
