"""
Schedule MCP server.

Exposes two tools over streamable-http:
  - add_schedule(user_id, description, time, date=None)
  - list_schedules(user_id, date=None)

Run directly with:
    python -m schedule_mcp_server.server

This starts a standalone process, separate from the FastAPI app, that
the app connects to as an MCP *client* (see app/core/mcp/). It shares
the app's SQLite file (see database.py) but owns its own table.
"""

import asyncio
import logging
import json

from mcp.server.fastmcp import FastMCP

from schedule_mcp_server.config import settings
from schedule_mcp_server.database import AsyncSessionLocal, init_db
from schedule_mcp_server.repository import (
    ScheduleRepository,
    ScheduleValidationError,
    today_str,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schedule_mcp_server")

mcp = FastMCP(
    settings.SERVER_NAME,
    host=settings.HOST,
    port=settings.PORT,
    # Default streamable_http_path is "/mcp" — full URL will be
    # http://{HOST}:{PORT}/mcp
)


@mcp.tool()
async def add_schedule(
    user_id: str,
    description: str,
    time: str,
    date: str | None = None,
) -> dict:
    """Add a new schedule/appointment record for a user.

    Args:
        user_id: The authenticated user's id. Always required.
        description: What the appointment/schedule is about, e.g.
            "dentist appointment".
        time: Time of the appointment in 24-hour "HH:MM" format, e.g.
            "14:00" for 2pm. Always required — extract it from the
            user's message before calling this tool.
        date: Date of the appointment in "YYYY-MM-DD" format. Optional
            — if omitted, defaults to today's date, matching "no date
            mentioned means today".

    Returns:
        A dict with the created record: id, user_id, date, time,
        description.
    """
    resolved_date = date or today_str()
    logger.info(
        "add_schedule user_id=%s date=%s time=%s description=%s",
        user_id, resolved_date, time, description,
    )

    async with AsyncSessionLocal() as session:
        repo = ScheduleRepository(session)
        try:
            record = await repo.add(
                user_id=user_id, description=description, date=resolved_date, time=time
            )
        except ScheduleValidationError as exc:
            # Raised back to the caller as a tool error — the graph
            # node/service layer decides how to surface this.
            raise ValueError(str(exc)) from exc

    return {
        "id": record.id,
        "user_id": record.user_id,
        "date": record.date,
        "time": record.time,
        "description": record.description,
    }


@mcp.tool()
async def list_schedules(user_id: str, date: str | None = None) -> str:
    """List a user's schedule/appointment records.

    Args:
        user_id: The authenticated user's id. Always required.
        date: Optional exact date filter in "YYYY-MM-DD" format, e.g.
            for "what are my schedules for 2026-08-01" or "for today"
            (resolve "today" to today's actual date before calling).
            Omit entirely to list ALL of the user's schedules,
            e.g. for "what are my schedules".

    Returns:
        A JSON-encoded string of a list of records (possibly an empty
        list), each: id, user_id, date, time, description. Sorted by
        date, then time.

        Returned as a JSON string rather than a raw list: FastMCP's
        content conversion explodes a returned Python list into one
        content block per item, which collapses a single-item list
        down to a bare object on the wire. Returning a pre-serialized
        string sidesteps that entirely — see schedule_mcp_server's
        integration notes for the full explanation.
    """
    logger.info("list_schedules user_id=%s date=%s", user_id, date or "(all)")

    async with AsyncSessionLocal() as session:
        repo = ScheduleRepository(session)
        try:
            records = await repo.list_for_user(user_id=user_id, date=date)
        except ScheduleValidationError as exc:
            raise ValueError(str(exc)) from exc

    return json.dumps(
        [
            {
                "id": r.id,
                "user_id": r.user_id,
                "date": r.date,
                "time": r.time,
                "description": r.description,
            }
            for r in records
        ]
    )


def main() -> None:
    asyncio.run(init_db())
    logger.info(
        "Starting schedule MCP server on http://%s:%s/mcp",
        settings.HOST, settings.PORT,
    )
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
