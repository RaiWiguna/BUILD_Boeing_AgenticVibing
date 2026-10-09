"""Real scoped replay REST and WebSocket routes; no client-supplied RequestContext."""

import asyncio
import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket
from fastapi import Path as PathParam
from flowlens.auth.routes import cookie
from flowlens.auth.transport import browser_principal
from flowlens.contracts.models import Mode, Snapshot, SourceManifest
from flowlens.core.errors import ContractError
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.replay.compatibility import LegacyHistory, LegacySummary
from flowlens.replay.controls import ControlResult, Controls, View
from flowlens.replay.snapshots import digest
from flowlens.replay.streams import Stream
from flowlens.replay.views import (
    CataloguePage,
    ControlBody,
    ControlReply,
    HistoryPage,
    SourcesPage,
    Views,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect


class ResyncMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    type: Literal["RESYNC"]
    after_sequence: Annotated[int, Field(ge=0, lt=2**63)]


def services(connection: Request | WebSocket) -> Views:
    controls: Controls | None = connection.app.state.controls
    if controls is None:
        raise HTTPException(503)
    return Views(controls)


def control_result(value: ControlResult) -> ControlReply:
    return ControlReply(state=value.state, version=value.version, archived=value.archived)


def build_router() -> APIRouter:
    router = APIRouter(tags=["Replay"])
    connections: dict[UUID, int] = {}

    @router.get("/api/v1/sessions", response_model=CataloguePage)
    def catalogue(
        request: Request,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: UUID | None = None,
    ) -> JSONResponse:
        data = services(request).catalogue(cookie(request), limit, cursor)
        page = CataloguePage.model_validate_json(json.dumps(data))
        return JSONResponse(page.model_dump(mode="json"))

    @router.get("/api/v1/sessions/{session_id}/sources", response_model=SourcesPage)
    def sources(
        request: Request,
        session_id: UUID,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: Annotated[str | None, Query(max_length=1024)] = None,
    ) -> JSONResponse:
        v = services(request)
        c = v.context(cookie(request), session_id, "FOLLOW", "DEBRIEF")
        page = SourcesPage.model_validate_json(json.dumps(v.sources(c, limit, cursor)))
        return JSONResponse(page.model_dump(mode="json"))

    @router.get("/api/v1/sessions/{session_id}/sources/{source_id}", response_model=SourceManifest)
    def source(request: Request, session_id: UUID, source_id: UUID) -> JSONResponse:
        v = services(request)
        c = v.context(cookie(request), session_id, "FOLLOW", "DEBRIEF")
        return JSONResponse(v.source(c, source_id))

    @router.get("/api/v1/sessions/{session_id}/snapshot", response_model=Snapshot)
    def snapshot(
        request: Request,
        session_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
    ) -> JSONResponse:
        return JSONResponse(
            services(request).snapshot(cookie(request), session_id, view, mode, run_id)
        )

    @router.get("/api/v1/sessions/{session_id}/history", response_model=HistoryPage)
    def history(
        request: Request,
        session_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: Annotated[str | None, Query(max_length=1024)] = None,
    ) -> JSONResponse:
        v = services(request)
        c = v.context(cookie(request), session_id, view, mode, run_id)
        page = HistoryPage.model_validate_json(json.dumps(v.history(c, view, limit, cursor)))
        return JSONResponse(page.model_dump(mode="json"))

    @router.get("/api/v1/sessions/{session_id}/playback")
    def playback(request: Request, session_id: UUID, view: View = "FOLLOW") -> ControlReply:
        return control_result(
            services(request).controls.get(cookie(request), session_id, view=view)
        )

    @router.post(
        "/api/v1/sessions/{session_id}/playback",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": ControlBody.model_json_schema()}},
            }
        },
    )
    async def control(request: Request, session_id: UUID) -> ControlReply:
        v = services(request)
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise ContractError("INVALID_INPUT")
        payload = bytearray()
        async for block in request.stream():
            payload.extend(block)
            if len(payload) > 4096:
                raise ContractError("INVALID_INPUT")
        try:
            strict_json(bytes(payload).decode("utf-8"))
            body = ControlBody.model_validate_json(bytes(payload))
        except (ValidationError, InvalidContent, ValueError):
            raise ContractError("INVALID_INPUT") from None
        result = await run_in_threadpool(
            v.controls.command,
            cookie(request),
            session_id,
            body.action,
            expected_version=body.expected_version,
            key=body.key,
            view=body.view,
            value=body.value,
            mode=body.mode,
        )
        return control_result(result)

    def legacy_service(request: Request) -> LegacyHistory:
        reader: LegacyHistory | None = request.app.state.legacy_history
        if reader is None:
            raise HTTPException(503)
        return reader

    @router.get("/api/v1/sessions/{session_id}/legacy-history", response_model=LegacySummary)
    def legacy_canonical(
        request: Request,
        session_id: UUID,
        mode: Literal["DEBRIEF"] = "DEBRIEF",
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> LegacySummary:
        return legacy_service(request).read(cookie(request), session_id, limit=limit)

    @router.get("/api/v1/legacy/sessions/{legacy_id}/history", response_model=LegacySummary)
    def legacy_alias(
        request: Request,
        legacy_id: Annotated[str, PathParam(min_length=1, max_length=128)],
        mode: Literal["DEBRIEF"] = "DEBRIEF",
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> LegacySummary:
        return legacy_service(request).read(cookie(request), legacy_id, limit=limit)

    @router.websocket("/api/v1/sessions/{session_id}/stream")
    async def stream(
        websocket: WebSocket,
        session_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
        after_sequence: Annotated[int, Query(ge=0, lt=2**63)] = 0,
    ) -> None:
        principal = await run_in_threadpool(browser_principal, websocket)
        actor = principal.account.id
        if sum(connections.values()) >= 32 or connections.get(actor, 0) >= 4:
            raise ContractError("ACCESS_DENIED")
        v = services(websocket)
        transport = Stream(v, view=view)
        connections[actor] = connections.get(actor, 0) + 1
        last, previous, force, initial = after_sequence, "", True, True
        conflicts = 0
        try:
            while True:
                try:
                    await run_in_threadpool(browser_principal, websocket)
                    c = await run_in_threadpool(
                        v.context, cookie(websocket), session_id, view, mode, run_id
                    )
                    snapshot = await run_in_threadpool(v.replay.snapshot, c)
                    fingerprint = digest(snapshot.model_dump(mode="json"))
                    if force or previous != fingerprint:
                        frames = await run_in_threadpool(
                            transport.frame, c, snapshot, last, incremental=not force
                        )
                        if initial:
                            await websocket.accept()
                            initial = False
                        # Recheck browser credential + object rights immediately before publication.
                        await run_in_threadpool(browser_principal, websocket)
                        for frame in frames:
                            await run_in_threadpool(v.replay.sources.read_events, c)
                            await websocket.send_json(frame)
                        previous, last, force = fingerprint, snapshot.sequence, False
                except ContractError as error:
                    if error.code != "VERSION_CONFLICT":
                        raise
                    conflicts += 1
                    if conflicts >= 3:
                        await websocket.close(code=1013)
                        return
                    force = True
                    await asyncio.sleep(0)
                    continue
                conflicts = 0
                try:
                    raw = await asyncio.wait_for(websocket.receive(), timeout=0.25)
                except TimeoutError:
                    continue
                if raw["type"] == "websocket.disconnect":
                    return
                text = raw.get("text")
                if not isinstance(text, str) or len(text.encode()) > 1024:
                    raise ContractError("INVALID_INPUT")
                try:
                    strict_json(text)
                    resync = ResyncMessage.model_validate_json(text)
                except (ValidationError, InvalidContent, ValueError):
                    raise ContractError("INVALID_INPUT") from None
                last, force = resync.after_sequence, True
        except WebSocketDisconnect:
            return
        finally:
            connections[actor] -= 1
            if connections[actor] == 0:
                del connections[actor]

    return router
