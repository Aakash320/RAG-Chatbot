"""
Single switch point for which MCP client implementation gets used.

Right now this only returns `ExternalMCPClient` (a hosted third-party MCP
server). When a self-hosted MCP server is introduced later, this is the
one place that chooses between them — typically off an
`MCP_PROVIDER` setting, exactly like `app/vectorstores/factory.py` does
for vector store backends.
"""

from functools import lru_cache

from app.core.mcp.base import BaseMCPClient
from app.core.mcp.external_client import ExternalMCPClient


@lru_cache
def get_mcp_client() -> BaseMCPClient:
    return ExternalMCPClient()