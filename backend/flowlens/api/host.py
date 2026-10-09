"""Paket A composition root. Persistence and business routes arrive in later units."""

from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from os import environ
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from flowlens import CONTRACT_VERSION
from flowlens.auth.accounts import Accounts
from flowlens.auth.routes import build_router
from flowlens.auth.sessions import Sessions
from flowlens.core.errors import HTTP_STATUS, ContractError, ErrorResponse
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import ModuleRegistration, ModuleRegistry
from flowlens.storage.sqlite.database import Database
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS
from starlette.exceptions import HTTPException
from starlette.routing import Route, WebSocketRoute


def create_host(
    settings: HostSettings | None = None, *, modules: Sequence[ModuleRegistration] = ()
) -> FastAPI:
    config = settings if settings is not None else HostSettings.from_environment(environ)
    registry = ModuleRegistry(profile=config.profile)
    for module in modules:
        if module.mock and config.profile != "test":
            raise ValueError("MOCK modules are allowed only in the test profile.")
        registry.register(module)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if config.database_path is None:
            yield
            return
        specs = (
            *PLATFORM_MIGRATIONS,
            *(spec for module in registry.modules if not module.mock for spec in module.migrations),
        )
        try:
            database = Database(config.database_path, migrations=specs)
        except Exception:
            raise RuntimeError("Platform storage startup failed.") from None
        with database:
            app.state.transactions = database
            try:
                app.state.accounts = Accounts(database)
                app.state.sessions = Sessions(database, app.state.accounts)
                yield
            finally:
                app.state.sessions = None
                app.state.accounts = None
                app.state.transactions = None

    app = FastAPI(
        title="FlowLens Paket A host",
        version=CONTRACT_VERSION,
        description="Platform persistence/accounts foundation; HTTP auth/business APIs not ready.",
        debug=False,
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.registry = registry
    app.state.transactions = None
    app.state.accounts = None
    app.state.sessions = None
    profile = "MOCK" if any(module.mock for module in registry.modules) else config.profile

    @app.middleware("http")
    async def safe_boundary(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Never trust a caller-supplied ID or log untrusted exception text.
        request.state.request_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            response = transport_error(request, 500, "INTERNAL_ERROR")
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        error = ErrorResponse(
            code="INVALID_INPUT",
            message="Request does not match the contract.",
            request_id=request.state.request_id,
            field_issues=[".".join(map(str, row["loc"])) for row in exc.errors()],
        )
        return JSONResponse(status_code=422, content=error.model_dump())

    @app.exception_handler(ContractError)
    async def contract_error(request: Request, exc: ContractError) -> JSONResponse:
        error = ErrorResponse(
            code=exc.code,
            message="Request cannot be accepted.",
            request_id=request.state.request_id,
        )
        return JSONResponse(status_code=HTTP_STATUS[exc.code], content=error.model_dump())

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {401: "AUTH_REQUIRED", 403: "ACCESS_DENIED", 404: "NOT_FOUND", 429: "RATE_LIMITED"}
        response = transport_error(
            request, exc.status_code, codes.get(exc.status_code, "HTTP_ERROR")
        )
        retry = (exc.headers or {}).get("Retry-After", "")
        if exc.status_code == 429 and retry.isascii() and retry.isdecimal() and len(retry) <= 10:
            response.headers["Retry-After"] = retry
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "alive", "profile": profile}

    @app.get("/ready")
    def ready() -> JSONResponse:
        # Module readiness alone cannot prove DB/assets/coordinator or G-BE readiness.
        return JSONResponse(
            status_code=503,
            content={"ready": False, "implementation": "HOST_ONLY", "profile": profile},
        )

    @app.get("/release.json")
    def release() -> dict[str, str]:
        return {"contract_version": CONTRACT_VERSION, "implementation": "HOST_ONLY"}

    app.include_router(build_router())
    occupied: set[tuple[str, str]] = set()
    for route in app.routes:
        occupied.update(route_keys(route))
    for module in registry.modules:
        for router in module.routes:
            for route in router.routes:
                keys = route_keys(route)
                if keys & occupied:
                    raise ValueError("Duplicate or reserved host route.")
                occupied.update(keys)
            app.include_router(router)
    return app


def route_keys(route: object) -> set[tuple[str, str]]:
    if isinstance(route, WebSocketRoute):
        return {(route.path, "WEBSOCKET")}
    if isinstance(route, Route):
        return {(route.path, method) for method in route.methods or ()}
    return set()


def transport_error(request: Request, status: int, code: str) -> JSONResponse:
    """Host-only transport codes supplement, without editing, frozen domain errors."""
    return JSONResponse(
        status_code=status,
        content={
            "code": code,
            "message": "Request cannot be accepted.",
            "request_id": request.state.request_id,
            "field_issues": [],
            "recovery_hint": "Check the request or contact the operator.",
        },
    )
