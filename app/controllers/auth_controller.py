"""
Auth controller — thin orchestration between the API layer and
AuthService, matching the existing DocumentController / ChatController
pattern used elsewhere in this codebase.
"""

from app.db.models import User
from app.services.auth_service import AuthService


class AuthController:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    async def register(
        self, email: str, password: str, full_name: str | None = None, role: str | None = None
    ) -> User:
        return await self._auth_service.register_user(email, password, full_name, role)

    async def login(self, email: str, password: str) -> dict:
        user = await self._auth_service.authenticate_user(email, password)
        access_token, refresh_token = await self._auth_service.issue_token_pair(user)
        return {"access_token": access_token, "refresh_token": refresh_token, "user": user}

    async def refresh(self, refresh_token: str) -> dict:
        access_token, new_refresh_token, user = await self._auth_service.refresh_access_token(refresh_token)
        return {"access_token": access_token, "refresh_token": new_refresh_token, "user": user}

    async def logout(self, refresh_token: str) -> None:
        await self._auth_service.revoke_refresh_token(refresh_token)