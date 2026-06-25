"""
FastAPI dependency providers.

These pull the already-constructed controllers / vector store off
`app.state.rag` (built once at startup in `app/state.py`). Using
`Request.app.state` keeps the heavy objects as true singletons without
module-level globals, and makes them trivial to override in tests via
FastAPI's `dependency_overrides`.
"""

from fastapi import Request

from app.controllers.chat_controller import ChatController
from app.controllers.document_controller import DocumentController
from app.state import AppState
from app.vectorstores.base import BaseVectorStore


def get_state(request: Request) -> AppState:
    return request.app.state.rag


def get_document_controller(request: Request) -> DocumentController:
    return get_state(request).document_controller


def get_chat_controller(request: Request) -> ChatController:
    return get_state(request).chat_controller


def get_vector_store(request: Request) -> BaseVectorStore:
    return get_state(request).vector_store
