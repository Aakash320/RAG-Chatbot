"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

Build steps (services, controllers, vector store) happen once during the
lifespan startup, not at import time, so importing this module stays cheap.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.state import build_app_state
from app.core.logging_config import setup_logging
from app.db.base import engine, init_db

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables if they don't exist yet (fine for SQLite/dev — swap
    # for `alembic upgrade head` once real migrations are introduced).
    await init_db()
    app.state.rag = build_app_state()
    yield
    # Cleanly close all pooled DB connections before the process exits.
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,  # required so the browser sends the refresh-token cookie
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(router, prefix=settings.API_V1_PREFIX)
    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {"message": f"{settings.APP_NAME} is running. See /docs for API documentation."}

    return app


app = create_app()
