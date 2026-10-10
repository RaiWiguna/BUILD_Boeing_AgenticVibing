"""API-side binding for the actual isolated B audio executor."""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from flowlens.assets.access import Assets
from flowlens.audio.models import AudioLimits, FrameRange
from flowlens.auth.transport import worker_token
from flowlens.contracts.models import JobLease, JobResult, RequestContext
from flowlens.core.errors import ContractError
from flowlens.imports.metadata import PreparedImport
from flowlens.jobs.coordinator import RunConfig
from flowlens.jobs.routes import bounded
from flowlens.storage.sqlite.database import UnitOfWork
from flowlens.workers.audio.models import AudioInput

AUDIO_CONFIG = RunConfig(
    model_version="LOCAL_AUDIO",
    api_version="integration-1",
    sdk_version="ffmpeg-9",
    prompt_version="NONE",
    reducer_version="memory-1",
    rule_version="findings-1",
)


def resolve(request: Request, lease: JobLease) -> AudioInput:
    jobs = request.app.state.jobs
    token = worker_token(request)
    ctx = jobs.context(token, lease)
    with jobs.database.begin() as uow:
        _, _, _, policy = jobs._attempt(uow, token, lease)
        if policy.stage != "AUDIO" or len(lease.asset_ids) != 1:
            raise ContractError("ACCESS_DENIED")
        parent = request.app.state.assets.locate(uow, ctx, lease.asset_ids[0])
        row = uow.connection.execute(
            "SELECT payload FROM platform_source_packages WHERE session_id=? AND package_id=?",
            (str(ctx.session_id), str(parent.package_id)),
        ).fetchone()
        p = PreparedImport.model_validate_json(row[0])
        if p.manifest is None:
            raise ContractError("NOT_EVALUABLE")
        p.require_right("local")
        if p.manifest.coverage.gaps and p.manifest.clock.offset_ms is None:
            raise ContractError("ALIGNMENT_REQUIRED")
        gaps = []
        for gap in p.manifest.coverage.gaps:
            offset = p.manifest.clock.offset_ms or 0
            start = max(0, (gap.start_ms - offset) * parent.asset.sample_rate_hz // 1000)
            end = min(
                parent.asset.duration_ms * parent.asset.sample_rate_hz // 1000,
                ((gap.end_ms - offset) * parent.asset.sample_rate_hz + 999) // 1000,
            )
            if end > start:
                gaps.append(FrameRange(start=start, end=end))
        return AudioInput(
            context=ctx,
            job_id=lease.job_id,
            attempt_id=lease.attempt_id,
            lease_id=lease.lease_id,
            config_hash=lease.config_hash,
            audio_config_hash=AudioLimits().digest(),
            source_id=p.manifest.id,
            asset=parent.asset,
            size_bytes=parent.file.size_bytes,
            clock=p.manifest.clock,
            source_gaps=tuple(gaps),
            local_allowed=True,
        )


def router() -> APIRouter:
    result = APIRouter(tags=["Private audio binding"])

    @result.post("/internal/analysis/audio-input")
    async def input(request: Request) -> dict[str, object]:
        lease = await bounded(request, JobLease, 8192)
        bound = await run_in_threadpool(resolve, request, lease)
        return bound.model_dump(mode="json")

    return result


def validate_artifacts(
    ctx: RequestContext, result: JobResult, uow: UnitOfWork, assets: Assets
) -> None:
    """Validate private provenance against accepted, inspected artifacts in this transaction."""
    import json
    import os
    from uuid import UUID

    from pydantic import ValidationError

    from flowlens.audio.models import PreparationMetadata

    derivatives = [a for a in result.artifacts if a.kind == "AUDIO_DERIVATIVE"]
    reports = [a for a in result.artifacts if a.transform_version == "audio-worker-provenance-1"]
    if not derivatives or len(reports) != 1 or len(result.artifacts) != len(derivatives) + 1:
        raise ContractError("INVALID_AI_OUTPUT")
    spec, file, package = assets.staged_in_uow(ctx, reports[0].id, uow)
    if assets.artifacts is None:
        raise ContractError("NOT_EVALUABLE")
    with assets.artifacts.open(package, file) as fd:
        raw = os.read(fd, 2 * 1024**2 + 1)
    try:
        data = json.loads(raw)
        if set(data) != {
            "version",
            "job_id",
            "attempt_id",
            "input_hash",
            "config_hash",
            "artifact_ids",
            "preparation",
        }:
            raise ValueError("unexpected provenance fields")
        metadata = PreparationMetadata.model_validate_json(json.dumps(data["preparation"]))
        if (
            data["version"],
            UUID(data["job_id"]),
            UUID(data["attempt_id"]),
            data["input_hash"],
            data["config_hash"],
            data["artifact_ids"],
        ) != (
            "audio-worker-1",
            result.job_id,
            result.attempt_id,
            ctx.input_hash,
            result.config_hash,
            [str(a.id) for a in derivatives],
        ):
            raise ValueError("binding mismatch")
        if spec.source_asset_id is None:
            raise ValueError("missing source")
        parent = assets.locate(uow, ctx, spec.source_asset_id)
        source = uow.connection.execute(
            "SELECT source_id FROM platform_assets WHERE session_id=? AND id=?",
            (str(ctx.session_id), str(parent.asset.id)),
        ).fetchone()
        if (
            metadata.asset_id,
            str(metadata.source_id),
            metadata.source_sha256,
            metadata.source_after_sha256,
            metadata.config_sha256,
        ) != (
            parent.asset.id,
            source[0],
            parent.asset.sha256,
            parent.asset.sha256,
            AudioLimits().digest(),
        ) or metadata.config != AudioLimits():
            raise ValueError("source/config mismatch")
        package_row = uow.connection.execute(
            "SELECT payload FROM platform_source_packages WHERE session_id=? AND package_id=?",
            (str(ctx.session_id), str(parent.package_id)),
        ).fetchone()
        prepared = PreparedImport.model_validate_json(package_row[0])
        if prepared.manifest is None or metadata.clock != prepared.manifest.clock:
            raise ValueError("clock mismatch")
        if (metadata.probe.sample_rate, metadata.probe.channels) != (
            parent.asset.sample_rate_hz,
            parent.asset.channels,
        ):
            raise ValueError("probe mismatch")
        if len(metadata.chunks) != len(derivatives):
            raise ValueError("missing chunks")
        for chunk, artifact in zip(metadata.chunks, derivatives, strict=True):
            _, facts, _ = assets.staged_in_uow(ctx, artifact.id, uow)
            if (
                artifact.source_range is None
                or artifact.source_range.start_ms
                != chunk.plan.source_frames.start * 1000 // metadata.probe.sample_rate
                or artifact.source_range.end_ms
                != min(
                    parent.asset.duration_ms,
                    (chunk.plan.source_frames.end * 1000 + metadata.probe.sample_rate - 1)
                    // metadata.probe.sample_rate,
                )
                or not 0 <= chunk.plan.channel < parent.asset.channels
            ):
                raise ValueError("frame/channel mismatch")
            if (
                chunk.sha256,
                chunk.byte_count,
                artifact.source_asset_id,
                artifact.transform_version,
                facts.sample_rate_hz,
                facts.channels,
            ) != (
                artifact.sha256,
                artifact.size_bytes,
                metadata.asset_id,
                metadata.transform_version,
                metadata.output_rate,
                1,
            ):
                raise ValueError("chunk mismatch")
    except (KeyError, TypeError, ValueError, ValidationError):
        raise ContractError("INVALID_AI_OUTPUT") from None
