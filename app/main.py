"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

Build steps (services, controllers, vector store) happen once during the
lifespan startup, not at import time, so importing this module stays cheap.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.state import build_app_state

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the embedding model, vector store, LLM client and controllers once.
    app.state.rag = build_app_state()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
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
