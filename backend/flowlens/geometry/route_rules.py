"""Scoped local rule/alert REST. Source severity is never writable by a client."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from flowlens.auth.routes import cookie
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import Mode, Scoped
from flowlens.geometry.alerts import Acknowledgement, AlertRevision
from flowlens.geometry.indicators import Indicators
from flowlens.geometry.service import RuleEvaluation, RuleReceipt, Rules
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.replay.controls import Controls, View
from pydantic import Field, ValidationError
from starlette.concurrency import run_in_threadpool


class MutationBody(MetadataModel):
    key: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
    expected_version: Annotated[int, Field(ge=0, lt=2**63 - 1)]


class AlertPage(Scoped):
    items: list[AlertRevision]
    next_cursor: UUID | None
    next_version: int | None = None


async def body(request: Request) -> MutationBody:
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > 4096:
            raise HTTPException(413)
        data.extend(chunk)
    try:
        return MutationBody.model_validate(strict_json(data.decode()))
    except (InvalidContent, ValidationError, UnicodeError):
        raise HTTPException(422) from None


def services(request: Request) -> tuple[Rules, Controls]:
    rules: Rules | None = request.app.state.rules
    controls: Controls | None = request.app.state.controls
    if rules is None or controls is None:
        raise HTTPException(503)
    return rules, controls


def build_router() -> APIRouter:
    router = APIRouter(tags=["Rules and alerts"])
    request_schema = {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": MutationBody.model_json_schema()}},
        }
    }

    @router.get("/api/v1/sessions/{session_id}/rules", response_model=RuleEvaluation)
    def rules(
        request: Request,
        session_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
    ) -> RuleEvaluation:
        service, controls = services(request)
        c = controls.context(cookie(request), session_id, view=view, mode=mode, run_id=run_id)
        return service.evaluate(c)

    @router.get("/api/v1/sessions/{session_id}/indicators", response_model=Indicators)
    def indicators(
        request: Request,
        session_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
    ) -> Indicators:
        return rules(request, session_id, view, mode, run_id).indicators

    @router.post(
        "/api/v1/sessions/{session_id}/rules/evaluations",
        response_model=RuleReceipt,
        openapi_extra=request_schema,
    )
    async def publish(
        request: Request,
        session_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
    ) -> RuleReceipt:
        service, controls = services(request)
        value = await body(request)
        c = await run_in_threadpool(
            controls.context, cookie(request), session_id, view=view, mode=mode, run_id=run_id
        )
        return await run_in_threadpool(
            service.publish, c, key=value.key, expected_version=value.expected_version
        )

    @router.get("/api/v1/sessions/{session_id}/alerts", response_model=AlertPage)
    def alerts(
        request: Request,
        session_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        after: UUID | None = None,
    ) -> AlertPage:
        service, controls = services(request)
        c = controls.context(cookie(request), session_id, view=view, mode=mode, run_id=run_id)
        items = [a for a in service.inventory(c) if after is None or str(a.id) > str(after)]
        page = items[:limit]
        return AlertPage(
            session_id=c.session_id,
            analysis_run_id=c.analysis_run_id,
            revision=c.input_revision,
            items=page,
            next_cursor=page[-1].id if len(items) > limit else None,
        )

    @router.get("/api/v1/sessions/{session_id}/alerts/{alert_id}/history", response_model=AlertPage)
    def history(
        request: Request,
        session_id: UUID,
        alert_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        after_version: Annotated[int, Query(ge=0)] = 0,
    ) -> AlertPage:
        service, controls = services(request)
        c = controls.context(cookie(request), session_id, view=view, mode=mode, run_id=run_id)
        items = [a for a in service.history(c, alert_id) if a.version > after_version]
        page = items[:limit]
        return AlertPage(
            session_id=c.session_id,
            analysis_run_id=c.analysis_run_id,
            revision=c.input_revision,
            items=page,
            next_cursor=None,
            next_version=page[-1].version if len(items) > limit else None,
        )

    @router.post(
        "/api/v1/sessions/{session_id}/alerts/{alert_id}/seen",
        response_model=Acknowledgement,
        openapi_extra=request_schema,
    )
    async def acknowledge(
        request: Request,
        session_id: UUID,
        alert_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
    ) -> Acknowledgement:
        service, controls = services(request)
        value = await body(request)
        c = await run_in_threadpool(
            controls.context, cookie(request), session_id, view=view, mode=mode, run_id=run_id
        )
        return await run_in_threadpool(
            service.acknowledge, c, alert_id, key=value.key, expected_version=value.expected_version
        )

    return router
