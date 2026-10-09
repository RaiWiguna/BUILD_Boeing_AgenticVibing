"""Host transport policy; object selectors never supply authorization authority."""

from uuid import UUID

from fastapi import HTTPException, Request, WebSocket
from flowlens.auth.permissions import Permissions
from flowlens.auth.routes import COOKIE, auth_service, cookie, require_csrf
from flowlens.auth.sessions import AuthSession
from flowlens.contracts.models import Capability, RequestContext
from flowlens.core.errors import ContractError
from starlette.concurrency import run_in_threadpool
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocketDisconnect

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
AUTH_PATHS = frozenset(
    f"/api/v1/auth/{name}" for name in ("login", "logout", "password", "session")
)
FORBIDDEN_QUERY = frozenset(
    {
        "token",
        "access_token",
        "session_token",
        "worker_token",
        "authorization",
        "csrf_token",
        "context",
        "request_context",
        "actor_id",
        "capabilities",
        "role",
    }
)


def permissions(connection: HTTPConnection) -> Permissions:
    service: Permissions | None = connection.app.state.permissions
    if service is None:
        raise HTTPException(503)
    return service


def single_headers(connection: HTTPConnection) -> None:
    for name in ("origin", "authorization", "cookie", "sec-fetch-site", "x-csrf-token"):
        if len(connection.headers.getlist(name)) > 1:
            raise ContractError("ACCESS_DENIED")
    if any(key.casefold() in FORBIDDEN_QUERY for key in connection.query_params):
        raise ContractError("ACCESS_DENIED")
    if any(name in connection.headers for name in ("x-request-context", "x-worker-token")):
        raise ContractError("ACCESS_DENIED")


def browser_headers(connection: HTTPConnection, *, require_origin: bool = False) -> None:
    single_headers(connection)
    origin = connection.headers.get("origin")
    if (
        (require_origin or origin is not None) and origin != connection.app.state.settings.origin
    ) or connection.headers.get("sec-fetch-site") == "cross-site":
        raise ContractError("ACCESS_DENIED")
    if "authorization" in connection.headers:
        raise ContractError("ACCESS_DENIED")
    # Cookie parsing normally selects the last occurrence; reject ambiguous credentials instead.
    matches = [
        part
        for part in connection.headers.get("cookie", "").split(";")
        if part.strip().split("=", 1)[0] == COOKIE
    ]
    if len(matches) > 1:
        raise ContractError("ACCESS_DENIED")


def browser_principal(connection: HTTPConnection) -> AuthSession:
    websocket = connection.scope["type"] == "websocket"
    mutation = not websocket and connection.scope["method"] not in SAFE_METHODS
    browser_headers(connection, require_origin=websocket or mutation)
    # These helpers consume only shared HTTPConnection attributes.
    token = cookie(connection)
    if mutation:
        require_csrf(connection, token)
    return auth_service(connection).resolve(token)


def worker_token(connection: HTTPConnection) -> str:
    single_headers(connection)
    if (
        connection.scope["type"] != "http"
        or "cookie" in connection.headers
        or any(name in connection.headers for name in ("origin", "referer", "x-csrf-token"))
        or any(name.startswith("sec-fetch-") for name in connection.headers)
    ):
        raise ContractError("ACCESS_DENIED")
    value = connection.headers.get("authorization", "")
    if not value.startswith("Bearer wrk_") or len(value) > 128:
        raise ContractError("AUTH_REQUIRED")
    return value.removeprefix("Bearer ")


def internal_path(path: str) -> bool:
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in ("/internal", "/api/v1/internal")
    )


def check_http_transport(request: Request) -> None:
    path = request.url.path
    if internal_path(path):
        token = worker_token(request)
        request.state.principal_id = permissions(request).authenticate_worker(token)
    elif path == "/api/v1" or path.startswith("/api/v1/"):
        if path in AUTH_PATHS:
            # Forced-password-change and unauthenticated login/logout remain auth route policy.
            browser_headers(request, require_origin=request.method not in SAFE_METHODS)
        else:
            request.state.principal_id = browser_principal(request).account.id


def http_context(
    request: Request,
    session_id: UUID,
    *,
    run_id: UUID | None = None,
    required: Capability = "read",
) -> RequestContext:
    if internal_path(request.url.path):
        raise ContractError("ACCESS_DENIED")
    browser_principal(request)
    return permissions(request).human_context(
        cookie(request), session_id, run_id=run_id, required=required
    )


def worker_context(request: Request, scope_id: UUID) -> RequestContext:
    if not internal_path(request.url.path):
        raise ContractError("ACCESS_DENIED")
    return permissions(request).worker_context(worker_token(request), scope_id)


async def websocket_context(
    websocket: WebSocket,
    session_id: UUID,
    *,
    run_id: UUID | None = None,
    required: Capability = "read",
) -> RequestContext:
    """Call before accept and again at publication; real stream scheduling belongs to A07."""
    if internal_path(websocket.url.path):
        raise ContractError("ACCESS_DENIED")
    await run_in_threadpool(browser_principal, websocket)
    return await run_in_threadpool(
        permissions(websocket).human_context,
        cookie(websocket),
        session_id,
        run_id=run_id,
        required=required,
    )


class WebSocketPolicy:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return
        websocket = WebSocket(scope, receive=receive, send=send)
        try:
            if internal_path(websocket.url.path):
                raise ContractError("ACCESS_DENIED")
            await run_in_threadpool(browser_principal, websocket)
            await self.app(scope, receive, send)
        except (ContractError, HTTPException):
            # No credential/context/exception text in the close reason, before or after accept.
            await send({"type": "websocket.close", "code": 1008, "reason": ""})
        except WebSocketDisconnect:
            return
        except Exception:
            await send({"type": "websocket.close", "code": 1011, "reason": ""})
