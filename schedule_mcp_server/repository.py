"""
Data-access layer for schedules. Kept separate from `server.py` so the
MCP tool functions stay thin (validate -> call repository -> serialize)
and the DB logic is independently testable without spinning up an MCP
session.
"""

import re
from datetime import date as date_cls

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schedule_mcp_server.models import Schedule

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ScheduleValidationError(ValueError):
    """Raised on malformed date/time/description input from a tool call."""


def validate_date(value: str) -> str:
    if not _DATE_RE.match(value):
        raise ScheduleValidationError(f"date must be in YYYY-MM-DD format, got: {value!r}")
    try:
        date_cls.fromisoformat(value)
    except ValueError as exc:
        raise ScheduleValidationError(f"date is not a real calendar date: {value!r}") from exc
    return value


def validate_time(value: str) -> str:
    if not _TIME_RE.match(value):
        raise ScheduleValidationError(f"time must be in 24-hour HH:MM format, got: {value!r}")
    return value


def today_str() -> str:
    return date_cls.today().isoformat()


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: str, description: str, date: str, time: str) -> Schedule:
        date = validate_date(date)
        time = validate_time(time)
        description = description.strip()
        if not description:
            raise ScheduleValidationError("description must not be empty")

        record = Schedule(user_id=user_id, description=description, date=date, time=time)
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def list_for_user(self, user_id: str, date: str | None = None) -> list[Schedule]:
        stmt = select(Schedule).where(Schedule.user_id == user_id)
        if date is not None:
            date = validate_date(date)
            stmt = stmt.where(Schedule.date == date)
        stmt = stmt.order_by(Schedule.date, Schedule.time)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
