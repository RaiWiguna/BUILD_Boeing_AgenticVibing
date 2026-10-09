"""Same-origin cookie authentication routes; no role or session identity from the client."""

import hmac
import re
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from flowlens.auth.sessions import AuthSession, RateLimited, Sessions, csrf_token
from flowlens.core.errors import ContractError
from pydantic import BaseModel, ConfigDict, Field, SecretStr

COOKIE = "flowlens_session"


class LoginInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    login: str = Field(min_length=3, max_length=64)
    password: SecretStr = Field(min_length=12, max_length=4096)


class PasswordInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    current_password: SecretStr = Field(min_length=12, max_length=4096)
    new_password: SecretStr = Field(min_length=12, max_length=4096)


class AccountView(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: UUID
    login: str
    active: bool
    is_admin: bool
    must_change_password: bool
    credential_version: int


class SessionView(BaseModel):
    account: AccountView
    csrf_token: str
    expires_ms: int


def auth_service(request: Request) -> Sessions:
    service: Sessions | None = request.app.state.sessions
    if service is None:
        raise HTTPException(503)
    return service


def require_origin(request: Request) -> None:
    if (
        request.headers.get("origin") != request.app.state.settings.origin
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise ContractError("ACCESS_DENIED")


def cookie(request: Request) -> str:
    value = request.cookies.get(COOKIE)
    if value is None:
        raise ContractError("AUTH_REQUIRED")
    return value


def require_csrf(request: Request, token: str) -> None:
    provided = request.headers.get("x-csrf-token", "")
    if (
        len(token) > 128
        or not re.fullmatch(r"[0-9a-f]{64}", provided)
        or not hmac.compare_digest(provided, csrf_token(token))
    ):
        raise ContractError("ACCESS_DENIED")


def view(session: AuthSession) -> SessionView:
    return SessionView(
        account=AccountView(**asdict(session.account)),
        csrf_token=session.csrf_token,
        expires_ms=session.expires_ms,
    )


def clear_cookie(request: Request, response: Response) -> None:
    response.delete_cookie(
        COOKIE,
        path="/",
        secure=request.app.state.settings.origin.startswith("https://"),
        httponly=True,
        samesite="lax",
    )


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

    @router.post("/login", response_model=SessionView)
    def login(payload: LoginInput, request: Request, response: Response) -> SessionView:
        require_origin(request)
        try:
            session = auth_service(request).login(
                payload.login,
                payload.password,
                request.client.host if request.client else "unknown",
                previous_token=request.cookies.get(COOKIE),
            )
        except RateLimited as error:
            raise HTTPException(429, headers={"Retry-After": str(error.retry_after)}) from None
        response.set_cookie(
            COOKIE,
            session.token.get_secret_value(),
            max_age=8 * 60 * 60,
            path="/",
            httponly=True,
            secure=request.app.state.settings.origin.startswith("https://"),
            samesite="lax",
        )
        response.headers["Cache-Control"] = "no-store"
        return view(session)

    @router.get("/session", response_model=SessionView)
    def session(request: Request, response: Response) -> SessionView:
        response.headers["Cache-Control"] = "no-store"
        return view(auth_service(request).resolve(cookie(request), allow_password_change=True))

    @router.post("/logout", status_code=204)
    def logout(request: Request) -> Response:
        require_origin(request)
        token = request.cookies.get(COOKIE)
        if token:
            require_csrf(request, token)
            auth_service(request).logout(token)
        response = Response(status_code=204, headers={"Cache-Control": "no-store"})
        clear_cookie(request, response)
        return response

    @router.post("/password", status_code=204)
    def change_password(payload: PasswordInput, request: Request) -> Response:
        require_origin(request)
        token = cookie(request)
        require_csrf(request, token)
        service = auth_service(request)
        session = service.resolve(token, allow_password_change=True)
        try:
            service.change_password(session, payload.current_password, payload.new_password)
        except RateLimited as error:
            raise HTTPException(429, headers={"Retry-After": str(error.retry_after)}) from None
        response = Response(status_code=204, headers={"Cache-Control": "no-store"})
        clear_cookie(request, response)
        return response

    return router
