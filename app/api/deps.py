"""
FastAPI dependency providers.

Two different lifetimes are in play here:

- ML/vector-store-backed controllers (`ChatController`, `DocumentController`)
  are true singletons, built once at startup and pulled off
  `request.app.state.rag` — see `app/state.py`.
- DB-backed services/controllers (`AuthService`, `ChatHistoryService`,
  `ChatSessionController`) are constructed fresh on every request, each
  wrapping its own `AsyncSession` from `get_db()`. This is what lets
  FastAPI safely run concurrent requests without DB sessions leaking or
  colliding across requests.
"""

from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.controllers.auth_controller import AuthController
from app.controllers.chat_controller import ChatController
from app.controllers.chat_session_controller import ChatSessionController
from app.controllers.document_controller import DocumentController
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.db.base import get_db
from app.db.models import User
from app.services.auth_service import AuthService
from app.services.chat_history_service import ChatHistoryService
from app.state import AppState
from app.vectorstores.base import BaseVectorStore

# --- Singletons (built at startup, see app/state.py) ---


def get_state(request: Request) -> AppState:
    return request.app.state.rag


def get_document_controller(request: Request) -> DocumentController:
    return get_state(request).document_controller


def get_chat_controller(request: Request) -> ChatController:
    return get_state(request).chat_controller


def get_vector_store(request: Request) -> BaseVectorStore:
    return get_state(request).vector_store


# --- Per-request, DB-backed ---


def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(db)


def get_auth_controller(auth_service: Annotated[AuthService, Depends(get_auth_service)]) -> AuthController:
    return AuthController(auth_service)


def get_chat_history_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ChatHistoryService:
    return ChatHistoryService(db)


def get_chat_session_controller(
    chat_controller: Annotated[ChatController, Depends(get_chat_controller)],
    chat_history_service: Annotated[ChatHistoryService, Depends(get_chat_history_service)],
) -> ChatSessionController:
    return ChatSessionController(chat_controller, chat_history_service)


# --- Current user ---

# tokenUrl points at the login endpoint so FastAPI's /docs "Authorize"
# button can obtain a token directly from Swagger UI.
_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login".lstrip("/"), auto_error=False
)


async def get_current_user(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if not token:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid or expired access token")

    user = await auth_service.get_user_by_id(payload["sub"])
    if not user or not user.is_active:
        raise AuthenticationError("Invalid or expired access token")
    return user


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "admin":
        raise AuthorizationError("Admin privileges required")
    return current_user