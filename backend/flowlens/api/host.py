"""Paket A composition root. Persistence and business routes arrive in later units."""

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from os import environ
from time import perf_counter_ns
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import _IncludedRouter
from flowlens import CONTRACT_VERSION
from flowlens.artifacts.lifecycle import Artifacts
from flowlens.artifacts.routes import build_router as build_artifact_router
from flowlens.assets.access import Assets
from flowlens.assets.routes import build_router as build_asset_router
from flowlens.assets.storage import PrivateFiles
from flowlens.auth.accounts import Accounts
from flowlens.auth.permissions import Permissions
from flowlens.auth.routes import build_router
from flowlens.auth.sessions import Sessions
from flowlens.auth.transport import WebSocketPolicy, check_http_transport
from flowlens.contracts.ports import AnalysisModule, ContextReader
from flowlens.core.errors import HTTP_STATUS, ContractError, ErrorResponse
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import ModuleRegistration, ModuleRegistry
from flowlens.evidence.registry import EvidenceRegistry
from flowlens.geometry.occupancy import Occupancy
from flowlens.geometry.route_rules import build_router as build_rule_router
from flowlens.geometry.routes import build_router as build_geometry_router
from flowlens.geometry.service import Rules
from flowlens.imports.commit import ImportCommit
from flowlens.imports.routes import build_router as build_import_router
from flowlens.imports.staging import ImportFailure, Imports
from flowlens.jobs.coordinator import Jobs, StagePolicy
from flowlens.jobs.routes import build_router as build_job_router
from flowlens.ops.health import Operations
from flowlens.ops.logs import emit
from flowlens.ops.providers import AdapterBinding, Providers
from flowlens.ops.routes import build_router as build_ops_router
from flowlens.ops.usage import UsageReader
from flowlens.replay.compatibility import LegacyHistory
from flowlens.replay.controls import Controls
from flowlens.replay.routes import build_router as build_replay_router
from flowlens.replay.snapshots import Replay
from flowlens.retention.coordinator import Retention
from flowlens.retention.journal import Tombstones
from flowlens.retention.routes import build_router as build_retention_router
from flowlens.sources.store import Sources
from flowlens.storage.sqlite.database import Database, RepositoryFactory
from flowlens.storage.sqlite.mutations import MutationOperation, Mutations
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.routing import Route, WebSocketRoute


def create_host(
    settings: HostSettings | None = None,
    *,
    modules: Sequence[ModuleRegistration] = (),
    mutation_operations: Sequence[MutationOperation] = (),
    analysis_module: AnalysisModule | None = None,
    context_reader: ContextReader | None = None,
    job_policies: Sequence[StagePolicy] = (),
    provider_adapters: Mapping[str, AdapterBinding] | None = None,
    repository_factories: Mapping[str, RepositoryFactory] | None = None,
) -> FastAPI:
    config = settings if settings is not None else HostSettings.from_environment(environ)
    if bool(analysis_module) != bool(job_policies):
        raise ValueError("Analysis module and registered stage policies required together")
    if job_policies and (config.database_path is None or config.raw_assets_path is None):
        raise ValueError("Jobs require durable database and committed source storage")
    if provider_adapters and any(
        k not in ("GOOGLE_STT", "GEMINI")
        or not isinstance(v, AdapterBinding)
        or type(v.mock) is not bool
        or (v.mock and config.profile != "test")
        for k, v in provider_adapters.items()
    ):
        raise ValueError("Provider MOCK registration requires test profile")
    registry = ModuleRegistry(profile=config.profile)
    for module in modules:
        if module.mock and config.profile != "test":
            raise ValueError("MOCK modules are allowed only in the test profile.")
        registry.register(module)

    snapshot_readers = [
        m.snapshot_reader for m in registry.modules if m.snapshot_reader is not None
    ]
    if analysis_module is not None:
        snapshot_readers.append(analysis_module.snapshot)
    if len(snapshot_readers) > 1:
        raise ValueError("One analysis snapshot reader required")

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
            database = Database(
                config.database_path, migrations=specs, repositories=repository_factories
            )
        except Exception:
            raise RuntimeError("Platform storage startup failed.") from None
        with database:
            app.state.transactions = database
            try:
                app.state.accounts = Accounts(database)
                app.state.sessions = Sessions(database, app.state.accounts)
                app.state.permissions = Permissions(database, app.state.sessions)
                app.state.providers = Providers(
                    database,
                    app.state.sessions,
                    adapters=provider_adapters,
                    allow_mock=config.profile == "test",
                )
                app.state.usage = UsageReader(app.state.permissions)
                database.context_guard = app.state.permissions.enforce
                app.state.legacy_history = LegacyHistory(app.state.permissions)
                app.state.mutations = Mutations(database, operations=mutation_operations)
                if config.import_staging_path is not None:
                    try:
                        app.state.imports = Imports(
                            database, app.state.sessions, config.import_staging_path
                        )
                    except Exception:
                        raise RuntimeError("Private import staging startup failed.") from None
                if config.raw_assets_path is not None:
                    try:
                        app.state.raw_files = PrivateFiles(config.raw_assets_path)
                        app.state.sources = Sources(
                            database, app.state.permissions, app.state.raw_files
                        )
                        app.state.replay = Replay(
                            app.state.sources,
                            snapshot_reader=snapshot_readers[0] if snapshot_readers else None,
                        )
                        app.state.controls = Controls(app.state.replay)
                        app.state.controls.recover()
                        if config.artifact_staging_path is not None:
                            app.state.artifact_files = PrivateFiles(config.artifact_staging_path)
                        app.state.assets = Assets(app.state.sources, app.state.artifact_files)
                        app.state.artifacts = Artifacts(app.state.assets)
                        if config.retention_journal_path is not None:
                            app.state.tombstones = Tombstones(config.retention_journal_path)
                            callbacks = {}
                            namespaces: list[str] = []
                            for module in registry.modules:
                                namespaces.extend(module.inventory_namespaces)
                                if module.purge_handler is not None:
                                    if not module.inventory_namespaces:
                                        raise ValueError(
                                            "Purge handler requires registered inventory"
                                        )
                                    callbacks[module.inventory_namespaces[0]] = module.purge_handler
                            app.state.retention = Retention(
                                app.state.permissions,
                                app.state.assets,
                                app.state.tombstones,
                                imports=app.state.imports,
                                callbacks=callbacks,
                                inventory_namespaces=tuple(namespaces),
                            )
                            app.state.retention.recover()
                        app.state.import_commits = ImportCommit(
                            app.state.imports, app.state.raw_files
                        )
                        app.state.assets.recover_artifacts()
                        app.state.evidence = EvidenceRegistry(app.state.sources, app.state.assets)
                        app.state.geometry = Occupancy(app.state.sources, app.state.evidence)
                        app.state.rules = Rules(
                            app.state.geometry, app.state.evidence, context_reader=context_reader
                        )
                    except Exception:
                        raise RuntimeError("Committed source storage startup failed.") from None
                if analysis_module is not None:
                    app.state.jobs = Jobs(
                        database,
                        app.state.permissions,
                        app.state.assets,
                        app.state.evidence,
                        analysis_module,
                        job_policies,
                        allow_mock=config.profile == "test",
                    )
                yield
            finally:
                app.state.jobs = None
                if app.state.tombstones is not None:
                    app.state.tombstones.close()
                app.state.tombstones = None
                app.state.retention = None
                app.state.artifacts = None
                if app.state.artifact_files is not None:
                    app.state.artifact_files.close()
                app.state.artifact_files = None
                if app.state.raw_files is not None:
                    app.state.raw_files.close()
                app.state.assets = None
                app.state.evidence = None
                app.state.geometry = None
                app.state.rules = None
                app.state.raw_files = None
                app.state.import_commits = None
                app.state.controls = None
                app.state.legacy_history = None
                app.state.replay = None
                app.state.sources = None
                if app.state.imports is not None:
                    app.state.imports.close()
                app.state.imports = None
                app.state.mutations = None
                app.state.permissions = None
                app.state.sessions = None
                app.state.accounts = None
                app.state.providers = None
                app.state.usage = None
                app.state.transactions = None

    app = FastAPI(
        title="FlowLens Paket A host",
        version=CONTRACT_VERSION,
        description="Platform/auth/transport foundation; domain business APIs not ready.",
        debug=False,
        lifespan=lifespan,
    )
    app.add_middleware(WebSocketPolicy)
    app.state.settings = config
    app.state.registry = registry
    app.state.transactions = None
    app.state.accounts = None
    app.state.sessions = None
    app.state.permissions = None
    app.state.mutations = None
    app.state.imports = None
    app.state.artifact_files = None
    app.state.assets = None
    app.state.evidence = None
    app.state.geometry = None
    app.state.rules = None
    app.state.raw_files = None
    app.state.import_commits = None
    app.state.controls = None
    app.state.legacy_history = None
    app.state.replay = None
    app.state.sources = None
    app.state.jobs = None
    app.state.providers = None
    app.state.usage = None
    app.state.tombstones = None
    app.state.retention = None
    app.state.artifacts = None
    profile = (
        "MOCK"
        if any(module.mock for module in registry.modules)
        or any(v.mock for v in (provider_adapters or {}).values())
        or (analysis_module is not None and config.profile == "test")
        else config.profile
    )

    @app.middleware("http")
    async def safe_boundary(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Never trust a caller-supplied ID or log untrusted exception text.
        started = perf_counter_ns()
        request.state.request_id = str(uuid4())
        try:
            await run_in_threadpool(check_http_transport, request)
            response = await call_next(request)
        except ContractError as error:
            response = transport_error(request, HTTP_STATUS[error.code], error.code)
        except HTTPException as error:
            response = transport_error(request, error.status_code, "HTTP_ERROR")
        except Exception:
            response = transport_error(request, 500, "INTERNAL_ERROR")
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith(("/api/v1", "/internal")):
            response.headers["Cache-Control"] = "no-store"
        emit(
            event="HTTP_REQUEST",
            request_id=UUID(request.state.request_id),
            status=response.status_code,
            latency_ms=max(0, (perf_counter_ns() - started) // 1000000),
            measurement="UNTIL_HEADERS",
        )
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

    @app.exception_handler(WebSocketRequestValidationError)
    async def invalid_websocket(websocket: WebSocket, exc: WebSocketRequestValidationError) -> None:
        await websocket.close(code=1008)

    @app.exception_handler(ImportFailure)
    async def import_error(request: Request, exc: ImportFailure) -> JSONResponse:
        response = ErrorResponse(
            code="INVALID_IMPORT",
            message="Uploaded input cannot be accepted.",
            request_id=request.state.request_id,
            field_issues=[
                f"{issue.field}:{issue.code}"
                + (f":row={issue.row}" if issue.row is not None else "")
                for issue in exc.issues
            ],
        )
        return JSONResponse(status_code=422, content=response.model_dump())

    @app.exception_handler(ContractError)
    async def contract_error(
        request: Request | WebSocket, exc: ContractError
    ) -> JSONResponse | None:
        if isinstance(request, WebSocket):
            await request.close(code=1008)
            return None
        error = ErrorResponse(
            code=exc.code,
            message="Request cannot be accepted.",
            request_id=request.state.request_id,
        )
        return JSONResponse(status_code=HTTP_STATUS[exc.code], content=error.model_dump())

    @app.exception_handler(HTTPException)
    async def http_error(request: Request | WebSocket, exc: HTTPException) -> JSONResponse | None:
        if isinstance(request, WebSocket):
            await request.close(code=1008)
            return None
        codes = {401: "AUTH_REQUIRED", 403: "ACCESS_DENIED", 404: "NOT_FOUND", 429: "RATE_LIMITED"}
        response = transport_error(
            request, exc.status_code, codes.get(exc.status_code, "HTTP_ERROR")
        )
        retry = (exc.headers or {}).get("Retry-After", "")
        if exc.status_code == 429 and retry.isascii() and retry.isdecimal() and len(retry) <= 10:
            response.headers["Retry-After"] = retry
        return response

    app.state.ops = Operations(
        app.state,
        config,
        (
            *PLATFORM_MIGRATIONS,
            *(spec for module in registry.modules if not module.mock for spec in module.migrations),
        ),
        profile=profile,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "alive", "profile": profile}

    @app.get("/ready")
    def ready() -> JSONResponse:
        report = app.state.ops.ready()
        return JSONResponse(status_code=200 if report["ready"] else 503, content=report)

    @app.get("/release.json")
    def release() -> dict[str, object]:
        service: Operations = app.state.ops
        return service.release()

    app.include_router(build_router())
    app.include_router(build_import_router())
    app.include_router(build_asset_router())
    app.include_router(build_job_router())
    app.include_router(build_replay_router())
    app.include_router(build_geometry_router())
    app.include_router(build_rule_router())
    app.include_router(build_artifact_router())
    app.include_router(build_retention_router())
    app.include_router(build_ops_router())
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
    # The locked FastAPI runtime retains includes as lazy branches. Use the same
    # effective paths as its matcher, including nested prefixes and WebSockets.
    if isinstance(route, _IncludedRouter):
        keys: set[tuple[str, str]] = set()
        for candidate in route.effective_candidates():
            if isinstance(candidate, _IncludedRouter):
                keys.update(route_keys(candidate))
            elif candidate.starlette_route is not None:
                keys.update(route_keys(candidate.starlette_route))
            else:
                keys.update((candidate.path, method) for method in candidate.methods)
        return keys
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
