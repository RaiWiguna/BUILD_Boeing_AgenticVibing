"""Actual A/B composition. Provider execution deliberately remains unconfigured."""

from collections.abc import Mapping
from typing import cast

from fastapi import APIRouter, FastAPI, Request
from starlette.concurrency import run_in_threadpool

from flowlens.api.host import create_host
from flowlens.auth.transport import browser_principal, http_context, worker_token
from flowlens.contracts.models import JobLease, JobResult, RequestContext, Snapshot
from flowlens.contracts.ports import EvidenceService, UnitOfWork
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import ModuleRegistration
from flowlens.integration.catalog import B_MIGRATIONS, TABLES, repositories
from flowlens.integration.engine import Engine, IntentSubmission
from flowlens.jobs.routes import bounded
from flowlens.storage.sqlite.database import RepositoryFactory


def create_integrated_host(settings: HostSettings | None = None) -> FastAPI:
    from os import environ

    config = settings or HostSettings.from_environment(environ)
    holder: list[Engine] = []

    def engine() -> Engine:
        return holder[0]

    def purge(ctx: RequestContext, uow: UnitOfWork) -> None:
        return engine().purge(ctx, uow)

    class Module:
        def validate(
            self, context: RequestContext, candidate: JobResult, evidence: EvidenceService
        ) -> JobResult:
            return engine().validate(context, candidate, evidence)

        def accept(self, context: RequestContext, candidate: JobResult, uow: UnitOfWork) -> None:
            engine().accept(context, candidate, uow)

        def snapshot(self, context: RequestContext) -> Snapshot:
            return engine().snapshot(context)

        def purge(self, context: RequestContext, uow: UnitOfWork) -> None:
            engine().purge(context, uow)

    # Assemble without credentials or network access. Deferred engine methods are
    # called only after host-owned database/permissions/sources have started.
    provisional = FastAPI()
    provisional.state.settings = config
    pending = Engine(provisional)
    from dataclasses import replace

    policies = tuple(
        replace(
            p,
            handler=lambda ctx, r, uow: engine().accept(ctx, r, uow),
        )
        for p in pending.policies()
    )
    registration = ModuleRegistration(
        name="analysis_integrated",
        repositories=dict(repositories()),
        migrations=B_MIGRATIONS,
        purge_handler=purge,
        inventory_namespaces=tuple(repositories()),
        inventory_tables=TABLES,
        readiness=lambda: False,
    )
    app = create_host(
        config,
        modules=(registration,),
        analysis_module=Module() if config.database_path is not None else None,
        job_policies=policies if config.database_path is not None else (),
        repository_factories=cast(Mapping[str, RepositoryFactory], repositories()),
    )
    current = Engine(app)
    app.state.integration = current
    holder.append(current)
    # A EvidenceRegistry resolves transcript anchors through this canonical store.
    # Factory alias preserves the existing frozen interface namespace.
    router = APIRouter(tags=["Integrated analysis"])

    @router.get("/api/v1/integration-status")
    def status(request: Request) -> dict[str, object]:
        browser_principal(request)
        return current.status()

    @router.post("/internal/analysis/intents")
    async def intents(request: Request) -> dict[str, object]:
        packet = await bounded(request, IntentSubmission, 1024**2)
        receipt = await run_in_threadpool(current.submit, worker_token(request), packet)
        return receipt.model_dump(mode="json")

    @router.post("/internal/analysis/prepare")
    async def prepare(request: Request) -> dict[str, object]:
        lease = await bounded(request, JobLease, 8192)
        return await run_in_threadpool(current.prepare, worker_token(request), lease)

    @router.get("/api/v1/sessions/{session_id}/analysis-runs/{run_id}/records")
    def records(request: Request, session_id: str, run_id: str) -> dict[str, object]:
        from uuid import UUID

        ctx = http_context(request, UUID(session_id), run_id=UUID(run_id))
        with current.database.begin() as uow:
            return {
                "records": [r.model_dump(mode="json") for r in current.records(ctx, uow)],
                "status": current.status(),
            }

    from flowlens.integration.advisory import router as advisory_router
    from flowlens.integration.audio import router as audio_router

    app.include_router(advisory_router(current))
    app.include_router(audio_router())
    app.include_router(router)
    return app
