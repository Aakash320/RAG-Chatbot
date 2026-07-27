"""
Settings for the schedule MCP server.

Deliberately separate from `app/config.py` — this is a standalone
deployable process and shouldn't import the FastAPI app's settings
module. `DATABASE_URL` defaults to the exact same relative path as
`app.config.Settings.DATABASE_URL` so that, when this process and the
main app are both run from the `rag_structured/` repo root, they point
at the same physical SQLite file. Point `DATABASE_URL` at an absolute
path (or a Postgres URL) via `.env` if you ever run this from a
different working directory.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ScheduleServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Database ---
    # Same file as the main app's DATABASE_URL, different table
    # ("schedules") — see models.py. Async SQLite via aiosqlite, same
    # driver the main app uses.
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # --- MCP server transport ---
    # streamable-http, matching MCP_TRANSPORT="streamable_http" already
    # used by app/core/mcp/external_client.py for the Tavily server.
    HOST: str = "127.0.0.1"
    PORT: int = 8100
    SERVER_NAME: str = "schedule-server"


@lru_cache
def get_settings() -> ScheduleServerSettings:
    return ScheduleServerSettings()


settings = get_settings()
