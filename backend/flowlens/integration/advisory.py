"""Scoped B advisory review/render adapters; authority and transaction stay API-owned."""

from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID, uuid5

from fastapi import APIRouter, Request, Response
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from flowlens.advisory.exports import ExportPolicy, ReportRenderer
from flowlens.advisory.models import Document, Entry, Inputs, Review
from flowlens.advisory.service import AdvisoryService, journal, repo
from flowlens.auth.transport import http_context
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import UnitOfWork as TransactionPort
from flowlens.core.errors import ContractError
from flowlens.integration.engine import Engine, TransactionalEvidence
from flowlens.jobs.routes import bounded
from flowlens.sources.policy import policy
from flowlens.storage.sqlite.database import UnitOfWork


class Access:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def authoritative(
        self, ctx: RequestContext, operation: str, candidate: Contract | None, uow: TransactionPort
    ) -> Inputs:
        actual = cast(UnitOfWork, uow)
        actual.authorize(ctx)
        ctx.require(
            "review" if operation in ("REVIEW", "INVALIDATE") else "read",
            ctx.session_id,
            ctx.analysis_run_id,
        )
        if "worker" in ctx.capabilities and operation != "READ":
            raise ContractError("ACCESS_DENIED")
        return self.engine.inputs(ctx, uow)

    def authorize(self, ctx: RequestContext, document: Entry, uow: TransactionPort) -> ExportPolicy:
        actual = cast(UnitOfWork, uow)
        actual.authorize(ctx)
        ctx.require("export", ctx.session_id, ctx.analysis_run_id)
        if not isinstance(document.body, Document):
            raise ContractError("INVALID_INPUT")
        refs = {e.id: e for f in document.body.facts for e in f.evidence}
        refs.update({e.id: e for f in document.body.findings for e in f.evidence})
        expiries = []
        labels = []
        for source_id in {e.source_id for e in refs.values()}:
            manifest = self.engine.app.state.permissions.require_source_rights(
                actual, ctx, source_id, export=True
            )
            current = policy(actual.connection, ctx.session_id, source_id)
            if current is None:
                raise ContractError("SOURCE_PERMISSION_REQUIRED")
            expiries.append(current.expires_ms)
            labels.append(manifest.source_label)
        now = self.engine.app.state.sessions.clock()
        expires = min([now + 3600000, *expiries])
        return ExportPolicy(
            evidence_ids=tuple(refs),
            include_text=True,
            expires_at=datetime.fromtimestamp(expires / 1000, UTC),
            source_labels=tuple(labels),
        )


class ReviewRequest(Contract):
    subject_id: UUID
    expected_version: int = Field(ge=1)
    decision: Literal["UNDER_REVIEW", "CONFIRMED", "DISMISSED", "UNRESOLVED"]
    reason: str = Field(min_length=1, max_length=2048)


def router(engine: Engine) -> APIRouter:
    result = APIRouter(tags=["Integrated advisory"])

    def service(uow: UnitOfWork) -> AdvisoryService:
        return AdvisoryService(
            Access(engine), TransactionalEvidence(engine.app.state.evidence, uow)
        )

    @result.get("/api/v1/sessions/{session_id}/analysis-runs/{run_id}/advisory")
    def inventory(request: Request, session_id: UUID, run_id: UUID) -> dict[str, object]:
        ctx = http_context(request, session_id, run_id=run_id)
        with engine.database.begin() as uow:
            service(uow).inputs(ctx, uow)
            rows = journal(ctx, repo(uow).inventory(ctx))
            return {"entries": [r.model_dump(mode="json") for r in rows], "status": engine.status()}

    @result.post(
        "/api/v1/sessions/{session_id}/analysis-runs/{run_id}/advisory/{document_id}/reviews"
    )
    async def review(
        request: Request, session_id: UUID, run_id: UUID, document_id: UUID
    ) -> dict[str, str]:
        body = await bounded(request, ReviewRequest, 8192)
        ctx = await run_in_threadpool(
            http_context, request, session_id, run_id=run_id, required="review"
        )
        key = request.headers.get("Idempotency-Key", "")
        if not 1 <= len(key) <= 128:
            raise ContractError("INVALID_INPUT")

        def commit() -> UUID:
            with engine.database.begin() as uow:
                # The actor and scope are server-derived; body cannot escalate them.
                checked = Review(
                    document_id=document_id,
                    subject_id=body.subject_id,
                    actor_id=ctx.actor_id,
                    expected_version=body.expected_version,
                    decision=body.decision,
                    reason=body.reason,
                )
                identifier = uuid5(document_id, str(ctx.actor_id) + ":" + key)
                try:
                    old = repo(uow).get(ctx, identifier)
                except ContractError as exc:
                    if exc.code != "EVIDENCE_UNAVAILABLE":
                        raise
                else:
                    Access(engine).authoritative(ctx, "REVIEW", old, uow)
                    if old.body != checked:
                        raise ContractError("IDEMPOTENCY_CONFLICT")
                    return old.id
                entry = Entry(
                    id=identifier,
                    session_id=ctx.session_id,
                    analysis_run_id=ctx.analysis_run_id,
                    revision=ctx.input_revision,
                    input_hash=ctx.input_hash,
                    stream_id=uuid5(document_id, str(body.subject_id)),
                    version=body.expected_version,
                    body=checked,
                    event_time_ms=ctx.as_of_ms,
                    available_time_ms=None,
                    recorded_at=datetime.now(UTC),
                )
                service(uow).review(ctx, entry, uow)
                uow.commit()
                return identifier

        return {"id": str(await run_in_threadpool(commit))}

    @result.get(
        "/api/v1/sessions/{session_id}/analysis-runs/{run_id}/advisory/{document_id}/report"
    )
    def report(
        request: Request,
        session_id: UUID,
        run_id: UUID,
        document_id: UUID,
        format: Literal["JSON", "CSV", "HTML"] = "JSON",
    ) -> Response:
        ctx = http_context(request, session_id, run_id=run_id, required="export")
        with engine.database.begin() as uow:
            payload, _ = ReportRenderer(service(uow), Access(engine)).render(
                ctx,
                document_id,
                format,
                artifact_id=uuid5(document_id, "report:" + format),
                now=datetime.fromtimestamp(engine.app.state.sessions.clock() / 1000, UTC),
                uow=uow,
            )
        return Response(
            payload,
            media_type={"JSON": "application/json", "CSV": "text/csv", "HTML": "text/html"}[format],
            headers={
                "Content-Disposition": 'attachment; filename="report.' + format.lower() + '"',
                "Content-Security-Policy": "sandbox; default-src 'none'",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )

    return result
