"""Authenticated replay geometry; context is issued by the host playback authority."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from flowlens.auth.routes import cookie
from flowlens.contracts.models import Mode
from flowlens.geometry.kernel import Resource
from flowlens.geometry.occupancy import Occupancy, OccupancyReport
from flowlens.replay.controls import Controls, View


def build_router() -> APIRouter:
    router = APIRouter(tags=["Geometry"])

    @router.get(
        "/api/v1/sessions/{session_id}/entities/{entity_id}/geometry",
        response_model=OccupancyReport,
    )
    def geometry(
        request: Request,
        session_id: UUID,
        entity_id: UUID,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
        resource: Resource = "RUNWAY",
    ) -> OccupancyReport:
        service: Occupancy | None = request.app.state.geometry
        controls: Controls | None = request.app.state.controls
        if service is None or controls is None:
            raise HTTPException(503)
        context = controls.context(cookie(request), session_id, view=view, mode=mode, run_id=run_id)
        return service.report(context, entity_id, resource=resource)

    return router
