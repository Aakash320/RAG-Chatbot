"""
Schedule service.

Wraps the schedule MCP client (see schedule_mcp_server/) the same way
`WebSearchService` wraps the web-search MCP client — the graph nodes only
ever talk to this service, never to the MCP client or tool names
directly. Tool names are hardcoded here (not settings) since, unlike
Tavily, this is a first-party server we fully control.
"""

import logging
from typing import Any

from app.core.exceptions import ScheduleError, WebSearchError
from app.core.mcp.base import BaseMCPClient

logger = logging.getLogger("rag.schedule")

_ADD_TOOL_NAME = "add_schedule"
_LIST_TOOL_NAME = "list_schedules"


class ScheduleService:
    def __init__(self, mcp_client: BaseMCPClient) -> None:
        self._mcp_client = mcp_client

    async def add_schedule(
        self,
        user_id: str,
        description: str,
        time: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Returns the created record: {id, user_id, date, time, description}."""
        logger.info("Adding schedule user_id=%s date=%s time=%s", user_id, date or "(today)", time)
        arguments = {"user_id": user_id, "description": description, "time": time}
        if date:
            arguments["date"] = date

        try:
            result = await self._mcp_client.acall_tool(_ADD_TOOL_NAME, arguments)
        except WebSearchError as exc:
            # ExternalMCPClient raises WebSearchError generically — re-wrap
            # with the correct, schedule-specific error/status here so it
            # isn't misreported as a web-search failure upstream.
            raise ScheduleError(exc.message) from exc
        except Exception as exc:
            logger.exception("add_schedule tool call failed")
            raise ScheduleError(str(exc)) from exc

        if not isinstance(result, dict):
            raise ScheduleError(f"Unexpected add_schedule result shape: {result!r}")
        return result

    async def list_schedules(self, user_id: str, date: str | None = None) -> list[dict[str, Any]]:
        """Returns a list of records: [{id, user_id, date, time, description}, ...]."""
        logger.info("Listing schedules user_id=%s date=%s", user_id, date or "(all)")
        arguments = {"user_id": user_id}
        if date:
            arguments["date"] = date

        try:
            result = await self._mcp_client.acall_tool(_LIST_TOOL_NAME, arguments)
        except WebSearchError as exc:
            raise ScheduleError(exc.message) from exc
        except Exception as exc:
            logger.exception("list_schedules tool call failed")
            raise ScheduleError(str(exc)) from exc

        if not isinstance(result, list):
            raise ScheduleError(f"Unexpected list_schedules result shape: {result!r}")
        return result