"""
LLM service.

Wraps the Groq-backed chat model via langchain_groq. The prompt template
and chain construction live here so that migrating to LangGraph later
means rebuilding this file's internals as a graph node — the
ChatController doesn't need to know the difference.
"""

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.config import settings

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the \
provided context. If the answer cannot be found in the context, say you don't know — \
do not make up an answer.

Context:
{context}
"""


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

    def generate_answer(self, question: str, context: str) -> str:
        return self._chain.invoke({"question": question, "context": context})

    async def agenerate_answer(self, question: str, context: str) -> str:
        return await self._chain.ainvoke({"question": question, "context": context})


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()
