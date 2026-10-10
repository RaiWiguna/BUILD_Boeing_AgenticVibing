"""Authorized single byte ranges. Every stream chunk rechecks live authority."""

import asyncio
import re
from collections.abc import Iterator
from queue import Empty, Full, Queue
from threading import Event
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from flowlens.assets.access import Assets
from flowlens.auth.transport import http_context, worker_context
from flowlens.contracts.models import ArtifactSubmission
from flowlens.core.errors import ContractError
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.imports.staging import ImportFailure
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response, StreamingResponse


def byte_range(header: str | None, size: int) -> tuple[int, int, bool]:
    if header is None:
        return 0, size, False
    match = re.fullmatch(r"bytes=([0-9]{0,20})-([0-9]{0,20})", header)
    if not match or not any(match.groups()):
        raise ValueError("Invalid range")
    a, b = match.groups()
    if not a:
        suffix = int(b)
        if suffix <= 0:
            raise ValueError("Invalid suffix")
        start, end = max(0, size - suffix), size
    else:
        start = int(a)
        end = min(size, int(b) + 1) if b else size
    if not 0 <= start < end <= size:
        raise ValueError("Unsatisfiable range")
    return start, end, True


def build_router() -> APIRouter:
    router = APIRouter(tags=["Private media"])

    def respond(request: Request, asset_id: UUID, scope_id: UUID | None = None) -> Response:
        assets: Assets | None = request.app.state.assets
        if assets is None:
            raise HTTPException(503)
        if request.url.path.startswith("/internal"):
            if scope_id is None:
                raise ContractError("ACCESS_DENIED")
            context = worker_context(request, scope_id)
        else:
            with assets.sources.database.begin() as uow:
                row = uow.connection.execute(
                    "SELECT session_id FROM platform_assets WHERE id=?", (str(asset_id),)
                ).fetchone()
                if row is None:
                    raise ContractError("EVIDENCE_UNAVAILABLE")
                sid = UUID(row[0])
            context = http_context(request, sid, required="audio")
        item = assets.metadata(context, asset_id)
        etag = '"' + item.asset.sha256 + '"'
        range_header = request.headers.get("range")
        if request.headers.get("if-range") not in (None, etag):
            range_header = None
        try:
            start, end, partial = byte_range(range_header, item.file.size_bytes)
        except ValueError:
            return Response(
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{item.file.size_bytes}",
                    "Cache-Control": "no-store",
                },
            )
        headers = {
            "Content-Length": str(end - start),
            "Accept-Ranges": "bytes",
            "ETag": etag,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{asset_id}.audio"',
        }
        if partial:
            headers["Content-Range"] = f"bytes {start}-{end - 1}/{item.file.size_bytes}"
        if request.method == "HEAD":
            return Response(
                status_code=206 if partial else 200,
                headers=headers,
                media_type=item.asset.media_type,
            )
        return StreamingResponse(
            assets.stream(context, asset_id, start, end),
            status_code=206 if partial else 200,
            headers=headers,
            media_type=item.asset.media_type,
        )

    @router.get("/api/v1/assets/{asset_id}/audio")
    @router.head("/api/v1/assets/{asset_id}/audio", include_in_schema=False)
    def audio(request: Request, asset_id: UUID) -> Response:
        return respond(request, asset_id)

    @router.get("/internal/assets/{asset_id}/audio")
    @router.head("/internal/assets/{asset_id}/audio", include_in_schema=False)
    def worker_audio(request: Request, asset_id: UUID, scope_id: UUID) -> Response:
        return respond(request, asset_id, scope_id)

    @router.put("/internal/artifacts/{artifact_id}")
    async def submit_artifact(
        request: Request, artifact_id: UUID, scope_id: UUID
    ) -> dict[str, str]:
        assets: Assets | None = request.app.state.assets
        if assets is None or assets.artifacts is None:
            raise HTTPException(503)
        raw = request.headers.get("x-artifact-metadata", "")
        if len(raw.encode()) > 16384:
            raise ImportFailure("INVALID_ARTIFACT")
        try:
            strict_json(raw)
            artifact = ArtifactSubmission.model_validate_json(raw)
        except (InvalidContent, ValidationError):
            raise ImportFailure("INVALID_ARTIFACT") from None
        if artifact.id != artifact_id:
            raise ContractError("INVALID_INPUT")
        context = await run_in_threadpool(worker_context, request, scope_id)
        queue: Queue[bytes | None] = Queue(maxsize=2)
        stopped = Event()

        def chunks() -> Iterator[bytes]:
            while True:
                if stopped.is_set():
                    raise ImportFailure("INCOMPLETE_UPLOAD")
                try:
                    block = queue.get(timeout=0.1)
                except Empty:
                    continue
                if block is None:
                    return
                yield block

        pending = asyncio.create_task(run_in_threadpool(assets.submit, context, artifact, chunks()))

        async def put(block: bytes | None) -> None:
            while True:
                if pending.done():
                    await pending
                    raise ImportFailure("INCOMPLETE_UPLOAD")
                try:
                    await run_in_threadpool(queue.put, block, True, 0.1)
                    return
                except Full:
                    continue

        count = 0
        try:
            async with asyncio.timeout(600):
                async for block in request.stream():
                    count += len(block)
                    if count > artifact.size_bytes:
                        raise ImportFailure("FILE_SIZE_LIMIT")
                    for offset in range(0, len(block), 65536):
                        await put(block[offset : offset + 65536])
                if count != artifact.size_bytes:
                    raise ImportFailure("INCOMPLETE_UPLOAD")
                await put(None)
                identifier = await pending
                return {"id": str(identifier)}
        finally:
            stopped.set()
            if not pending.done():
                try:
                    await pending
                except (ContractError, ValueError, OSError):
                    pass

    return router


# Artifact streaming uses a bounded producer queue into the fd-backed AssetAccess port.
