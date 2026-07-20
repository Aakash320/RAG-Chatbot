"""
Abstract MCP client interface.

THIS IS THE KEY ABSTRACTION FOR MCP TOOL ACCESS.

Today `ExternalMCPClient` connects to a third-party hosted MCP server
(Tavily). Later, a self-hosted MCP server can implement the exact same
interface (e.g. `SelfHostedMCPClient`). Nothing above this layer —
`WebSearchService`, the graph node — should ever import a concrete MCP
client directly; they only ever talk to `BaseMCPClient`. That is what
makes swapping servers a one-line config change instead of a rewrite,
mirroring how `app/vectorstores/base.py` decouples `RetrievalService`
from the concrete vector store backend.
"""

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.tools import BaseTool


class BaseMCPClient(ABC):
    """Abstract interface every MCP client/transport must implement."""

    @abstractmethod
    async def get_tools(self) -> list[BaseTool]:
        """Discover and return the tools exposed by the connected MCP server(s)."""
        raise NotImplementedError

    @abstractmethod
    async def acall_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a named tool on the connected MCP server and return its raw result."""
        raise NotImplementedError