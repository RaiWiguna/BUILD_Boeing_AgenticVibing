"""Admin-only preview, purge/retry and bounded metadata audit queries."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import Field, ValidationError
from starlette.concurrency import run_in_threadpool

from flowlens.auth.routes import cookie
from flowlens.clocks.normalization import MetadataModel
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.retention.coordinator import Inventory, PurgeReceipt, Retention


class PurgeBody(MetadataModel):
    key: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
    reason: Literal["USER_REQUEST", "RETENTION_EXPIRED"]
    expected_inventory_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


async def body(request: Request) -> PurgeBody:
    data = bytearray()
    async for block in request.stream():
        if len(data) + len(block) > 4096:
            raise HTTPException(413)
        data.extend(block)
    try:
        return PurgeBody.model_validate(strict_json(data.decode()))
    except (InvalidContent, ValidationError, UnicodeError):
        raise HTTPException(422) from None


def build_router() -> APIRouter:
    router = APIRouter(tags=["Admin retention"])

    def service(request: Request) -> Retention:
        value: Retention | None = request.app.state.retention
        if value is None:
            raise HTTPException(503)
        return value

    @router.get("/api/v1/admin/sessions/{session_id}/purge-preview", response_model=Inventory)
    def preview(request: Request, session_id: UUID) -> Inventory:
        return service(request).preview(cookie(request), session_id)

    @router.post("/api/v1/admin/sessions/{session_id}/purge", response_model=PurgeReceipt)
    async def purge(request: Request, session_id: UUID) -> PurgeReceipt:
        value = await body(request)
        return await run_in_threadpool(
            service(request).purge,
            cookie(request),
            session_id,
            reason=value.reason,
            expected_inventory_hash=value.expected_inventory_hash,
            key=value.key,
        )

    @router.post("/api/v1/admin/sessions/{session_id}/purge-resume", response_model=PurgeReceipt)
    def resume(request: Request, session_id: UUID) -> PurgeReceipt:
        return service(request).resume(cookie(request), session_id)

    @router.get("/api/v1/admin/sessions/{session_id}/audit")
    def audit(
        request: Request,
        session_id: UUID,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        after: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, object]:
        retention = service(request)
        with retention.database.begin() as uow:
            retention.permissions._admin(uow, cookie(request))
            rows = [
                dict(r)
                for r in uow.connection.execute(
                    "SELECT id,actor_id,action,target_id,recorded_at FROM platform_audit "
                    "WHERE session_id=? AND id>? ORDER BY id LIMIT ?",
                    (str(session_id), after, limit + 1),
                )
            ]
        return {
            "session_id": str(session_id),
            "items": rows[:limit],
            "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None,
        }

    return router
