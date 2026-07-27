"""
Single switch point for which MCP client implementation gets used.

Returns one cached `ExternalMCPClient` per logical MCP server this app
talks to: the (hosted, third-party) web-search server and the
(self-hosted) schedule server. Both share the exact same client
implementation and transport (`streamable_http`) — the only difference
is which URL/server_name each is pointed at. When a self-hosted
*web-search* server is introduced later, this is the one place that
would choose between implementations, exactly like
`app/vectorstores/factory.py` does for vector store backends.
"""

from functools import lru_cache

from app.config import settings
from app.core.mcp.base import BaseMCPClient
from app.core.mcp.external_client import ExternalMCPClient


@lru_cache
def get_mcp_client() -> BaseMCPClient:
    """Web search (Tavily) MCP client."""
    return ExternalMCPClient()


@lru_cache
def get_schedule_mcp_client() -> BaseMCPClient:
    """Self-hosted schedule MCP client (see schedule_mcp_server/)."""
    return ExternalMCPClient(
        server_url=settings.SCHEDULE_MCP_SERVER_URL,
        api_key="",  # self-hosted, no auth
        transport=settings.SCHEDULE_MCP_TRANSPORT,
        timeout_seconds=settings.SCHEDULE_MCP_TIMEOUT_SECONDS,
        server_name="schedule",
    )