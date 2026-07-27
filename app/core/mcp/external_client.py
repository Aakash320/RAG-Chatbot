"""
External MCP client.

Connects to a third-party *hosted* MCP server over HTTP using
``langchain-mcp-adapters``, which handles the MCP session/transport and
exposes each server-side tool as a LangChain `BaseTool`. That's a
deliberate choice: this project is already LangChain/LangGraph-based, so
a discovered MCP tool can be called with the same `.ainvoke(...)`
interface as any other LangChain tool, and is trivial to hand to an
agent later if this ever becomes a tool-calling node instead of a fixed
"call this one search tool" node.

Configured for Tavily's remote MCP server by default (see
`app.config.settings.MCP_SERVER_URL`), but nothing here is Tavily-specific
beyond the URL/API-key — pointing `MCP_SERVER_URL` at a different remote
MCP server (including your own, later) is enough to switch providers.

`api_key` is optional (defaults to ""): Tavily's hosted server needs one,
appended as a query param, but a self-hosted server (e.g. the schedule
MCP server) doesn't require auth at all, so an empty api_key simply
skips that step instead of raising.
"""

import json
import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import settings
from app.core.exceptions import WebSearchError
from app.core.mcp.base import BaseMCPClient

logger = logging.getLogger("rag.mcp")


class ExternalMCPClient(BaseMCPClient):
    """MCP client for a single remote, HTTP-based external MCP server."""

    def __init__(
        self,
        server_url: str = settings.MCP_SERVER_URL,
        api_key: str = settings.TAVILY_API_KEY,
        transport: str = settings.MCP_TRANSPORT,
        timeout_seconds: int = settings.MCP_TIMEOUT_SECONDS,
        server_name: str = "web_search",
        api_key_query_param: str = "tavilyApiKey",
    ) -> None:
        # Deliberately no validation / connection here. This is used on
        # fallback/secondary paths — a missing config shouldn't crash app
        # startup, only fail once the path is actually reached. See
        # get_tools() below for where that happens instead.
        self._server_url = server_url
        self._api_key = api_key
        self._transport = transport
        self._timeout_seconds = timeout_seconds
        self._server_name = server_name
        self._api_key_query_param = api_key_query_param
        self._client: MultiServerMCPClient | None = None
        self._tools_cache: list[BaseTool] | None = None

    def _build_client(self) -> MultiServerMCPClient:
        if not self._server_url:
            raise WebSearchError(f"Server URL is not configured for '{self._server_name}'")

        full_url = self._server_url
        if self._api_key:
            # Tavily's hosted MCP server authenticates via a query param on
            # the endpoint URL itself rather than a header. Self-hosted
            # servers that don't need auth just leave api_key empty and
            # skip this entirely.
            separator = "&" if "?" in self._server_url else "?"
            full_url = f"{self._server_url}{separator}{self._api_key_query_param}={self._api_key}"

        return MultiServerMCPClient(
            {
                self._server_name: {
                    "url": full_url,
                    "transport": self._transport,
                    "timeout": self._timeout_seconds,
                }
            }
        )

    async def get_tools(self) -> list[BaseTool]:
        if self._client is None:
            self._client = self._build_client()

        if self._tools_cache is None:
            logger.info("Discovering tools from MCP server '%s'", self._server_name)
            try:
                self._tools_cache = await self._client.get_tools(server_name=self._server_name)
            except Exception as exc:
                logger.exception("Failed to discover tools from MCP server '%s'", self._server_name)
                raise WebSearchError(f"Could not connect to MCP server: {exc}") from exc
            logger.info(
                "Discovered %d tool(s): %s",
                len(self._tools_cache),
                [t.name for t in self._tools_cache],
            )
        return self._tools_cache

    async def acall_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        tools = await self.get_tools()
        tool = next((t for t in tools if t.name == tool_name), None)
        if tool is None:
            available = [t.name for t in tools]
            raise WebSearchError(
                f"Tool '{tool_name}' not found on MCP server (available: {available})"
            )

        logger.info("Calling MCP tool '%s' with arguments=%s", tool_name, arguments)
        try:
            result = await tool.ainvoke(arguments)
        except Exception as exc:
            logger.exception("MCP tool call '%s' failed", tool_name)
            raise WebSearchError(f"MCP tool call failed: {exc}") from exc

        return self._normalize(result)

    @staticmethod
    def _normalize(result: Any) -> Any:
        if isinstance(result, ToolMessage):
            if result.artifact:
                return result.artifact
            result = result.content

        if isinstance(result, str):
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                logger.warning("MCP tool result is not valid JSON, returning as-is")
                return result

        if isinstance(result, list) and result and all(isinstance(r, str) for r in result):
            for text in result:
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    continue
            return result

        return result