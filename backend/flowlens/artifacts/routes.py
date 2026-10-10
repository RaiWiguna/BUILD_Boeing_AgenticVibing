"""Private accepted downloads use server contexts and forced attachment delivery."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import Response, StreamingResponse

from flowlens.artifacts.lifecycle import Artifacts, ArtifactView
from flowlens.auth.routes import cookie
from flowlens.contracts.models import ArtifactSubmission
from flowlens.replay.controls import Controls


def build_router() -> APIRouter:
    router = APIRouter(tags=["Private artifacts"])

    def services(request: Request) -> tuple[Artifacts, Controls]:
        if request.app.state.artifacts is None or request.app.state.controls is None:
            raise HTTPException(503)
        return request.app.state.artifacts, request.app.state.controls

    @router.get("/api/v1/sessions/{session_id}/artifacts", response_model=list[ArtifactSubmission])
    def inventory(
        request: Request, session_id: UUID, run_id: UUID | None = None
    ) -> list[ArtifactSubmission]:
        service, controls = services(request)
        context = controls.context(cookie(request), session_id, run_id=run_id)
        return service.inventory(context)

    @router.get(
        "/api/v1/sessions/{session_id}/artifacts/{artifact_id}", response_model=ArtifactView
    )
    def metadata(
        request: Request, session_id: UUID, artifact_id: UUID, run_id: UUID | None = None
    ) -> ArtifactView:
        service, controls = services(request)
        context = controls.context(cookie(request), session_id, run_id=run_id)
        return service.metadata(context, artifact_id)

    @router.get("/api/v1/sessions/{session_id}/artifacts/{artifact_id}/download")
    @router.head(
        "/api/v1/sessions/{session_id}/artifacts/{artifact_id}/download", include_in_schema=False
    )
    def download(
        request: Request, session_id: UUID, artifact_id: UUID, run_id: UUID | None = None
    ) -> Response:
        service, controls = services(request)
        context = controls.context(cookie(request), session_id, run_id=run_id)
        item = service.metadata(context, artifact_id)
        headers = {
            "Content-Disposition": f'attachment; filename="{item.filename}"',
            "Content-Length": str(item.artifact.size_bytes),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        }
        if request.method == "HEAD":
            return Response(headers=headers, media_type=item.media_type)
        return StreamingResponse(
            service.download(context, artifact_id), headers=headers, media_type=item.media_type
        )

    return router
