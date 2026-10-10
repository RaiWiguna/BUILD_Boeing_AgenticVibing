"""Bounded human run controls and worker-only JobClient transport."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from flowlens.auth.transport import http_context, worker_token
from flowlens.contracts.models import Contract, JobLease, JobResult
from flowlens.core.errors import ContractError
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.jobs.coordinator import Jobs, RunConfig, StageInput
from pydantic import Field, ValidationError
from starlette.concurrency import run_in_threadpool


class CreateRun(Contract):
    config: RunConfig
    jobs: list[StageInput] = Field(min_length=1, max_length=64)
    budget_microunits: int = Field(ge=0, le=10**12)
    deadline_ms: int = Field(ge=0)
    expected_revision: int = Field(ge=1)


class Cancel(Contract):
    expected_version: int = Field(ge=1)


class Claim(Contract):
    stage: str = Field(min_length=1, max_length=16)


async def bounded[C: Contract](request: Request, model: type[C], limit: int) -> C:
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise ContractError("INVALID_INPUT")
    body = bytearray()
    try:
        async with asyncio.timeout(60):
            async for part in request.stream():
                if len(body) + len(part) > limit:
                    raise ContractError("INVALID_INPUT")
                body.extend(part)
        strict_json(bytes(body).decode("utf-8"))
        return model.model_validate_json(bytes(body))
    except (TimeoutError, UnicodeDecodeError, InvalidContent, ValidationError):
        raise ContractError("INVALID_INPUT") from None


def build_router() -> APIRouter:
    router = APIRouter(tags=["Durable jobs"])

    def service(request: Request) -> Jobs:
        jobs: Jobs | None = request.app.state.jobs
        if jobs is None:
            raise HTTPException(503)
        return jobs

    @router.post("/api/v1/sessions/{session_id}/analysis-runs", status_code=202)
    async def create(request: Request, session_id: UUID) -> dict[str, object]:
        jobs = service(request)
        body = await bounded(request, CreateRun, 65536)
        ctx = await run_in_threadpool(http_context, request, session_id, required="analysis")
        run = await run_in_threadpool(
            jobs.create,
            ctx,
            body.config,
            body.jobs,
            budget=body.budget_microunits,
            deadline_ms=body.deadline_ms,
            expected_revision=body.expected_revision,
            key=request.headers.get("idempotency-key", ""),
        )
        return run.model_dump(mode="json")

    @router.get("/api/v1/sessions/{session_id}/analysis-runs/{run_id}")
    def inspect(request: Request, session_id: UUID, run_id: UUID) -> dict[str, object]:
        ctx = http_context(request, session_id, required="analysis")
        return service(request).inspect(ctx, run_id)

    @router.post("/api/v1/sessions/{session_id}/analysis-runs/{run_id}/cancel")
    async def cancel(request: Request, session_id: UUID, run_id: UUID) -> dict[str, str]:
        body = await bounded(request, Cancel, 4096)
        ctx = await run_in_threadpool(http_context, request, session_id, required="analysis")
        await run_in_threadpool(
            service(request).cancel,
            ctx,
            run_id,
            key=request.headers.get("idempotency-key", ""),
            expected_version=body.expected_version,
        )
        return {"status": "CANCEL_REQUESTED"}

    @router.post("/internal/jobs/lease")
    async def lease(request: Request) -> dict[str, object]:
        jobs = service(request)
        body = await bounded(request, Claim, 4096)
        token = worker_token(request)
        worker = await run_in_threadpool(jobs.permissions.authenticate_worker, token)
        leased = await run_in_threadpool(jobs.lease, token, worker, body.stage)
        if leased is None:
            return {"lease": None}
        scope = await run_in_threadpool(jobs.scope, token, leased)
        return {"lease": leased.model_dump(mode="json"), "scope_id": str(scope)}

    @router.post("/internal/jobs/{job_id}/input")
    async def input(request: Request, job_id: UUID) -> dict[str, object]:
        body = await bounded(request, JobLease, 16384)
        if body.job_id != job_id:
            raise ContractError("ACCESS_DENIED")
        return await run_in_threadpool(service(request).input, worker_token(request), body)

    @router.post("/internal/jobs/{job_id}/heartbeat")
    async def heartbeat(request: Request, job_id: UUID) -> dict[str, object]:
        body = await bounded(request, JobLease, 16384)
        if body.job_id != job_id:
            raise ContractError("ACCESS_DENIED")
        updated = await run_in_threadpool(service(request).heartbeat, worker_token(request), body)
        return updated.model_dump(mode="json")

    @router.post("/internal/jobs/{job_id}/cancelled")
    async def cancelled(request: Request, job_id: UUID) -> dict[str, bool]:
        body = await bounded(request, JobLease, 16384)
        if body.job_id != job_id:
            raise ContractError("ACCESS_DENIED")
        value = await run_in_threadpool(service(request).cancelled, worker_token(request), body)
        return {"cancelled": value}

    @router.post("/internal/jobs/{job_id}/results")
    async def result(request: Request, job_id: UUID) -> dict[str, object]:
        body = await bounded(request, JobResult, 1024**2)
        if body.job_id != job_id:
            raise ContractError("ACCESS_DENIED")
        receipt = await run_in_threadpool(service(request).result, worker_token(request), body)
        return receipt.model_dump(mode="json")

    return router
