"""Admin-only profiles/diagnostics/disk/global usage; authorized session usage."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import Field, ValidationError
from starlette.concurrency import run_in_threadpool

from flowlens.auth.routes import cookie
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import ProviderProfile
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.ops.health import Operations
from flowlens.ops.providers import ProfileView, ProviderOptions, Providers
from flowlens.ops.usage import UsageReader, UsageSummary
from flowlens.replay.controls import Controls


class CheckBody(MetadataModel):
    key: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
    expected_version: Annotated[int, Field(ge=0, le=32)]


class ProfileBody(CheckBody):
    profile: ProviderProfile
    options: ProviderOptions = ProviderOptions()


async def body[Body: MetadataModel](request: Request, model: type[Body]) -> Body:
    data = bytearray()
    async for block in request.stream():
        if len(data) + len(block) > 16384:
            raise HTTPException(413)
        data.extend(block)
    try:
        strict_json(data.decode())
        return model.model_validate_json(data)
    except (InvalidContent, ValidationError, UnicodeError):
        raise HTTPException(422) from None


def build_router() -> APIRouter:
    router = APIRouter(tags=["Local operability"])

    def providers(request: Request) -> Providers:
        value: Providers | None = request.app.state.providers
        if value is None:
            raise HTTPException(503)
        return value

    def usage(request: Request) -> UsageReader:
        value: UsageReader | None = request.app.state.usage
        if value is None:
            raise HTTPException(503)
        return value

    @router.get("/api/v1/admin/provider-profiles", response_model=list[ProfileView])
    def inventory(request: Request) -> list[ProfileView]:
        return providers(request).inventory(cookie(request))

    @router.post("/api/v1/admin/provider-profiles", response_model=ProfileView)
    async def save(request: Request) -> ProfileView:
        value = await body(request, ProfileBody)
        return await run_in_threadpool(
            providers(request).save,
            cookie(request),
            value.profile,
            options=value.options,
            expected_version=value.expected_version,
            key=value.key,
        )

    @router.get(
        "/api/v1/admin/provider-profiles/{profile_id}/history", response_model=list[ProfileView]
    )
    def history(request: Request, profile_id: UUID) -> list[ProfileView]:
        return providers(request).history(cookie(request), profile_id)

    @router.post("/api/v1/admin/provider-profiles/{profile_id}/checks", response_model=ProfileView)
    async def check(request: Request, profile_id: UUID) -> ProfileView:
        value = await body(request, CheckBody)
        return await run_in_threadpool(
            providers(request).check,
            cookie(request),
            profile_id,
            expected_version=value.expected_version,
            key=value.key,
        )

    @router.get("/api/v1/admin/disk")
    def disk(request: Request) -> dict[str, object]:
        service: Operations = request.app.state.ops
        return service.disk(cookie(request))

    @router.get("/api/v1/admin/usage", response_model=UsageSummary)
    def global_usage(request: Request) -> UsageSummary:
        return usage(request).admin(cookie(request))

    @router.get("/api/v1/sessions/{session_id}/usage", response_model=UsageSummary)
    def session_usage(
        request: Request, session_id: UUID, run_id: UUID | None = None
    ) -> UsageSummary:
        controls: Controls | None = request.app.state.controls
        if controls is None:
            raise HTTPException(503)
        context = controls.context(cookie(request), session_id, run_id=run_id)
        return usage(request).read(context)

    @router.get("/api/v1/admin/ops-audit")
    def audit(
        request: Request,
        after: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> dict[str, object]:
        service = providers(request)
        with service.database.begin() as uow:
            service.admin(uow, cookie(request))
            rows = [
                dict(r)
                for r in uow.connection.execute(
                    "SELECT id,actor_id,action,object_id,version,created_ms "
                    "FROM platform_ops_audit "
                    "WHERE id>? ORDER BY id LIMIT ?",
                    (after, limit + 1),
                )
            ]
        return {
            "items": rows[:limit],
            "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None,
        }

    return router
