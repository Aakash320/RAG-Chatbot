"""
ORM model for the schedule MCP server.

`user_id` is stored as a plain indexed string, not a SQLAlchemy
`ForeignKey("users.id")` — this module doesn't import the main app's
`User` model (different `Base`, different deployable), so referential
integrity to `users.id` is enforced at the application level (the graph
node always passes the authenticated user's id) rather than at the DB
level. If you'd rather have a real FK constraint, the alternative is
having this server import `app.db.models.User` directly instead of
staying decoupled — see the integration notes for the tradeoff.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from schedule_mcp_server.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    # Stored as "YYYY-MM-DD" / "HH:MM" strings rather than Date/Time
    # columns — keeps comparisons trivial (exact-date filtering is a
    # plain string equality check) and avoids timezone ambiguity, since
    # these represent the user's stated wall-clock date/time, not a
    # UTC instant.
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(5), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
