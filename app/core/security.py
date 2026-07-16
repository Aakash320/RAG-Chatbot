"""
Password hashing and token helpers.

Access tokens are JWTs — self-contained, short-lived, verified without a
DB round trip on every request.

Refresh tokens are deliberately NOT JWTs — they're opaque random strings.
Only their SHA-256 hash is stored in the `refresh_tokens` table, which is
what makes revocation and single-use rotation possible. A JWT would add
no value here since the token is looked up by hash in the DB on every
use anyway. They're delivered as an HttpOnly cookie (see
`app/api/endpoints/auth.py`) so client-side JS — and therefore XSS — can
never read them.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

TOKEN_TYPE_ACCESS = "access"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd_context.verify(password, hashed)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": TOKEN_TYPE_ACCESS,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError subclasses on invalid/expired tokens."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise jwt.InvalidTokenError("Expected an access token")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    # sha256 is fine here: the token is already high-entropy/random,
    # unlike a user-chosen password — no need for a slow salted hash.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()