"""
Async SQLAlchemy engine + session factory for the schedule MCP server.

Mirrors `app/db/base.py` in the main app almost exactly, on purpose —
same driver, same "ensure parent dir exists" behavior for SQLite — so
the two processes behave identically against the same database file.
This module owns its own `Base` (SQLAlchemy declarative base) rather
than importing the main app's `Base`, since this is a standalone
deployable and shouldn't import from `app/`. Because SQLAlchemy scopes
metadata per-`Base`, two different `Base` subclasses can safely share
one physical SQLite file as long as table names don't collide — this
server only ever creates the `schedules` table (see models.py), which
doesn't exist in the main app's models.
"""

import re
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from schedule_mcp_server.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir_exists(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return
    db_path = re.sub(r"^sqlite\+aiosqlite:///", "", database_url)
    if db_path and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir_exists(settings.DATABASE_URL)

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_async_engine(settings.DATABASE_URL, connect_args=_connect_args)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """One session per tool call, closed automatically."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Creates the `schedules` table if it doesn't exist yet.

    Only ever touches tables registered against *this module's* `Base`
    (i.e. just `schedules`) — running this against the shared DB file
    never affects the main app's `users` / `chat_sessions` / etc tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
