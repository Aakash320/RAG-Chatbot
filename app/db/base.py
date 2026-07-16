"""
Async SQLAlchemy engine + session factory.

Uses SQLite for now (settings.DATABASE_URL, e.g.
"sqlite+aiosqlite:///./data/app.db"). Swapping to Postgres later is a
one-line change to DATABASE_URL — nothing else in this file, or any
model/service, needs to change.
"""

import re
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — one session per request, closed automatically."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Creates tables if they don't exist yet.

    Fine for SQLite/dev. If you later introduce Alembic migrations for
    real schema evolution (or move to Postgres), call
    `alembic upgrade head` at deploy time instead of this.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)