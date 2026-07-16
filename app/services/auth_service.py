"""
Auth business logic: registration, login, and refresh-token lifecycle.

Kept as a plain class taking an `AsyncSession` per call (constructed fresh
per-request via `app/api/deps.py`, not stored on `AppState`) — see the
module docstring in `app/api/deps.py` for why DB-backed services can't be
singletons the way `ChatController`/`DocumentController` are.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    AuthenticationError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import RefreshToken, User

logger = logging.getLogger("rag.auth")


def _is_expired(expires_at: datetime) -> bool:
    """SQLite doesn't reliably round-trip timezone-aware datetimes through
    SQLAlchemy, so a value read back from the DB can come back naive even
    though it was stored aware. Normalize before comparing so this works
    the same on SQLite today and Postgres later."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < datetime.now(timezone.utc)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_user(
        self, email: str, password: str, full_name: str | None = None, role: str | None = None
    ) -> User:
        existing = await self.db.scalar(select(User).where(User.email == email))
        if existing:
            raise EmailAlreadyRegisteredError(email)

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role or "user",
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("Registered new user: %s (role=%s)", email, user.role)
        return user

    async def authenticate_user(self, email: str, password: str) -> User:
        user = await self.db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated")
        return user

    async def issue_token_pair(self, user: User) -> tuple[str, str]:
        """Returns (access_token, raw_refresh_token)."""
        access_token = create_access_token(user.id)
        raw_refresh_token = generate_refresh_token()

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_refresh_token),
                expires_at=expires_at,
            )
        )
        await self.db.commit()

        return access_token, raw_refresh_token

    async def refresh_access_token(self, raw_refresh_token: str) -> tuple[str, str, User]:
        """Validates + revokes the given refresh token and issues a new
        pair (rotation). Returns (access_token, new_refresh_token, user)."""
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

        if not stored or stored.revoked or _is_expired(stored.expires_at):
            raise AuthenticationError("Invalid or expired refresh token")

        user = await self.db.get(User, stored.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid or expired refresh token")

        stored.revoked = True  # rotate: old refresh token is single-use
        await self.db.commit()

        access_token, new_refresh_token = await self.issue_token_pair(user)
        return access_token, new_refresh_token, user

    async def revoke_refresh_token(self, raw_refresh_token: str) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if stored:
            stored.revoked = True
            await self.db.commit()

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self.db.get(User, user_id)