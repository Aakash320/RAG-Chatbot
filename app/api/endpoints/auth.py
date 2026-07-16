"""
Auth endpoints.

`/auth/login` deliberately uses OAuth2's standard form-based request
(`username` + `password` fields, not JSON) — this is what lets FastAPI's
`/docs` "Authorize" button work out of the box: enter your email as the
username, and Swagger UI will attach the resulting bearer token to every
other request you try from the docs page.

The refresh token itself is never returned in a JSON body — it's set as
an HttpOnly cookie, scoped to the /auth path, so client-side JS (and
therefore XSS) can never read it. The browser sends it back automatically
on /auth/refresh and /auth/logout; a frontend fetch()/axios call to those
two endpoints must include credentials (`credentials: "include"` /
`withCredentials: true`) for that to work.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_controller, get_current_user
from app.config import settings
from app.controllers.auth_controller import AuthController
from app.core.exceptions import AuthenticationError
from app.db.models import User
from app.models.schemas import AccessTokenResponse, UserCreate, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])

# Scoping the cookie's path to /auth means the browser only sends it on
# refresh/logout calls, not on every request.
_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=_COOKIE_PATH,
    )


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(
    payload: UserCreate,
    controller: Annotated[AuthController, Depends(get_auth_controller)],
) -> User:
    return await controller.register(payload.email, payload.password, payload.full_name, payload.role)


@router.post("/login", response_model=AccessTokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    controller: Annotated[AuthController, Depends(get_auth_controller)],
) -> dict:
    result = await controller.login(form_data.username, form_data.password)
    _set_refresh_cookie(response, result["refresh_token"])
    return {"access_token": result["access_token"], "token_type": "bearer", "user": result["user"]}


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    controller: Annotated[AuthController, Depends(get_auth_controller)],
) -> dict:
    raw_refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise AuthenticationError("Missing refresh token")

    result = await controller.refresh(raw_refresh_token)
    _set_refresh_cookie(response, result["refresh_token"])
    return {"access_token": result["access_token"], "token_type": "bearer", "user": result["user"]}


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    controller: Annotated[AuthController, Depends(get_auth_controller)],
) -> None:
    raw_refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if raw_refresh_token:
        await controller.logout(raw_refresh_token)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=_COOKIE_PATH)


@router.get("/me", response_model=UserPublic)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user