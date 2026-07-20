"""
Web search service.

Fallback path for when retrieval finds nothing in the knowledge base.
Calls the configured MCP server's search tool and shapes the raw result
into `WebSearchResult`s + a formatted context string, the same role
`RetrievalService` plays for vector store chunks. Kept separate from the
MCP client itself so the *shape* of a web search result doesn't leak the
*mechanics* of talking to MCP into the graph node.
"""

import logging
from typing import Any

from app.config import settings
from app.core.exceptions import WebSearchError
from app.core.logging_config import truncate
from app.core.mcp.base import BaseMCPClient
from app.models.schemas import WebSearchResponse, WebSearchResult

logger = logging.getLogger("rag.websearch")


class WebSearchService:
    def __init__(
        self,
        mcp_client: BaseMCPClient,
        tool_name: str = settings.MCP_SEARCH_TOOL_NAME,
        max_results: int = settings.WEB_SEARCH_MAX_RESULTS,
    ) -> None:
        self._mcp_client = mcp_client
        self._tool_name = tool_name
        self._max_results = max_results

    async def asearch(self, query: str) -> WebSearchResponse:
        logger.info("Calling MCP web search tool for query: %s", truncate(query, 150))

        try:
            raw_result = await self._mcp_client.acall_tool(
                self._tool_name,
                {"query": query, "max_results": self._max_results},
            )
        except WebSearchError:
            raise
        except Exception as exc:
            logger.exception("Web search tool call failed")
            raise WebSearchError(str(exc)) from exc

        results = self._parse_results(raw_result)
        logger.info("Web search returned %d result(s)", len(results))

        return WebSearchResponse(results=results, context=self._format_context(results))

    @staticmethod
    def _parse_results(raw_result: Any) -> list[WebSearchResult]:
        """
        Normalize the MCP tool's raw output into `WebSearchResult`s.

        Tavily's MCP search tool returns a list of dicts (or a dict with a
        `results` key) shaped like {"title": ..., "url": ..., "content": ...}.
        This is deliberately defensive about the exact shape, since it's the
        one place in the app that's coupled to a specific provider's
        response format — everything downstream only ever sees `WebSearchResult`.
        """
        items: list[dict] = []
        if isinstance(raw_result, dict):
            items = raw_result.get("results", [])
        elif isinstance(raw_result, list):
            items = raw_result

        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                WebSearchResult(
                    source_name=item.get("title") or item.get("source") or "Unknown source",
                    url=item.get("url", ""),
                    snippet=item.get("content") or item.get("snippet") or "",
                )
            )
        return results

    @staticmethod
    def _format_context(results: list[WebSearchResult]) -> str:
        """Flatten web search results into a context string for the LLM prompt."""
        parts = []
        for i, result in enumerate(results, start=1):
            parts.append(f"[{i}] (source: {result.source_name}, url: {result.url})\n{result.snippet}")
        return "\n\n".join(parts)