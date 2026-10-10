"""B05 executable standalone MOCK acceptance; disposable DB and injected ports only."""

import asyncio
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from uuid import UUID, uuid5

from flowlens.advisory.exports import ExportPolicy, ReportRenderer
from flowlens.advisory.models import NAMESPACE, Document, Entry, Fact, Inputs, Review, Signal
from flowlens.advisory.provider import AdvisoryExecutor
from flowlens.advisory.service import AdvisoryService, journal, register_advisory, repo
from flowlens.advisory.store import MIGRATIONS, SQLiteAdvisoryRepository
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import Repository, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.memory.service import MemoryService
from flowlens.memory.service import repo as memory_repo
from flowlens.providers.gemini.models import GeminiConfig, Reply
from flowlens.testing.harness import FakePlatform, SQLiteTransactionFactory
from flowlens.testing.intent_memory import (
    STAMP,
    MemoryReferenceTransactions,
    MemoryReferenceUOW,
    MockAuthority,
    context,
    fixture,
    mock_provenance,
)


class AdvisoryReferenceUOW(MemoryReferenceUOW):
    def repository(self, namespace: str) -> Repository:
        self.check_open()
        if namespace == NAMESPACE:
            return SQLiteAdvisoryRepository(self.conn, self.check_open)
        return super().repository(namespace)


class AdvisoryReferenceTransactions(MemoryReferenceTransactions):
    def __init__(self, path: Path) -> None:
        SQLiteTransactionFactory.__init__(self, path)
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS mock_migrations(id TEXT PRIMARY KEY, hash TEXT)"
            )
            conn.commit()
        # Incremental upgrade preserves all analysis.0001-.0003 state.
        from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
        from flowlens.analysis.transcript_store import TRANSCRIPT_MIGRATIONS
        from flowlens.memory.store import MEMORY_MIGRATIONS
        from flowlens.testing.analysis import PLATFORM_REFERENCE

        self.migrate(
            (
                PLATFORM_REFERENCE,
                *ANALYSIS_MIGRATIONS,
                *TRANSCRIPT_MIGRATIONS,
                *MEMORY_MIGRATIONS,
                *MIGRATIONS,
            )
        )

    @contextmanager
    def begin(self) -> Iterator[AdvisoryReferenceUOW]:
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            uow = AdvisoryReferenceUOW(conn)
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield uow
            except BaseException:
                uow.rollback()
                raise
            finally:
                if not uow.committed:
                    uow.rollback()
        if uow.committed:
            for callback in uow.callbacks:
                callback()


class MockAdvisoryAccess:
    """MOCK only; cancellation/revision attestation is not real platform authority."""

    profile = "MOCK"

    def __init__(self, ctx: RequestContext, config: GeminiConfig) -> None:
        self.ctx, self.config = ctx, config
        self.cancelled, self.denied, self.show_text = False, False, True
        self.extra_facts: tuple[Fact, ...] = ()
        self.extra_signals: tuple[Signal, ...] = ()

    def authoritative(
        self,
        ctx: RequestContext,
        operation: str,
        candidate: Contract | None,
        uow: UnitOfWork,
    ) -> Inputs:
        if self.cancelled:
            raise ContractError("JOB_CANCELLED")
        if (
            self.denied
            or ctx.session_id != self.ctx.session_id
            or ctx.analysis_run_id != self.ctx.analysis_run_id
        ):
            raise ContractError("ACCESS_DENIED")
        if ctx.input_hash != self.ctx.input_hash or ctx.input_revision != self.ctx.input_revision:
            raise ContractError("SOURCE_REVISION_CHANGED")
        from flowlens.advisory.models import Proposal

        if isinstance(candidate, Proposal) and (
            candidate.document.provenance.profile != "MOCK"
            or candidate.document.provenance.config_hash != self.config.digest()
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        return Inputs(
            events=memory_repo(uow).inventory(ctx),
            facts=self.extra_facts,
            signals=self.extra_signals,
        )

    def authorize(self, ctx: RequestContext, document: Entry, uow: UnitOfWork) -> ExportPolicy:
        self.authoritative(ctx, "EXPORT", document, uow)
        if not isinstance(document.body, Document):
            raise ContractError("INVALID_INPUT")
        ids = {e.id for f in document.body.facts for e in f.evidence}
        ids.update(e.id for f in document.body.findings for e in f.evidence)
        return ExportPolicy(
            evidence_ids=tuple(ids),
            include_text=self.show_text,
            expires_at=STAMP + timedelta(days=1),
            source_labels=("MOCK_SYNTHETIC",),
        )


class MockAdvisoryClient:
    profile = "MOCK"

    def __init__(self) -> None:
        self.calls, self.closed = 0, False

    async def structured(
        self,
        payload: str,
        config: GeminiConfig,
        schema: dict[str, object],
        policy: str,
    ) -> Reply:
        self.calls += 1
        data = json.loads(payload)
        ids = tuple(f["id"] for f in data["facts"])
        body = {
            "status": "COMPLETE" if ids else "INSUFFICIENT_CONTEXT",
            "fact_ids": ids,
            "option_kinds": ("REVIEW_EVIDENCE",) if ids and data["task"] == "OPTIONS" else (),
        }
        return Reply(
            text=json.dumps(body),
            status="COMPLETE",
            input_tokens=100,
            output_tokens=100,
            total_tokens=200,
        )

    async def close(self) -> None:
        self.closed = True


def setup(
    path: Path,
) -> tuple[
    RequestContext,
    GeminiConfig,
    AdvisoryReferenceTransactions,
    FakePlatform,
    MockAdvisoryAccess,
    AdvisoryService,
]:
    ctx = RequestContext.model_validate(
        context().model_dump()
        | {
            "capabilities": [
                "read",
                "analysis",
                "review",
                "export",
                "admin",
            ]
        }
    )
    cfg = GeminiConfig()
    pairs = [
        fixture(ctx, 10, "FLN214 hold short runway 27"),
        fixture(ctx, 11, "FLN214 hold short runway 27", "READBACK", time_ms=3000),
    ]
    segments = [p[0] for p in pairs]
    platform = FakePlatform([], segments)
    tx = AdvisoryReferenceTransactions(path)
    tx.seed(ctx)
    memory = MemoryService(MockAuthority(ctx, segments, cfg.digest()), platform)
    with tx.begin() as uow:
        for _, candidate in pairs:
            memory.accept(
                ctx,
                candidate,
                config_hash=cfg.digest(),
                provenance=mock_provenance(ctx, cfg),
                recorded_at=STAMP,
                uow=uow,
            )
        uow.commit()
    access = MockAdvisoryAccess(ctx, cfg)
    return ctx, cfg, tx, platform, access, AdvisoryService(access, platform)


async def run() -> dict[str, object]:
    with TemporaryDirectory(prefix="flowlens-b05-") as temp:
        path = Path(temp) / "b05.db"
        ctx, cfg, tx, platform, access, service = setup(path)
        client = MockAdvisoryClient()
        executor = AdvisoryExecutor(cfg, client)
        registration = register_advisory(tx, access, platform)
        try:
            with tx.begin() as uow:
                inputs = service.inputs(ctx, uow)
            kinds: tuple[Literal["FINDINGS", "BRIEF", "OPTIONS"], ...] = (
                "FINDINGS",
                "BRIEF",
                "OPTIONS",
            )
            for index, kind in enumerate(kinds, start=100):
                proposal = await service.propose(
                    ctx,
                    kind,
                    inputs,
                    executor,
                    checkpoint=lambda: None,
                    reserve=lambda _: None,
                    local_provenance=mock_provenance(ctx, cfg),
                )
                with tx.begin() as uow:
                    service.accept(
                        ctx,
                        proposal,
                        identifier=UUID(int=index),
                        stream_id=UUID(int=index),
                        expected_version=0,
                        recorded_at=STAMP,
                        event_time_ms=10000,
                        available_time_ms=10000,
                        uow=uow,
                    )
                    uow.commit()
            review = Entry(
                id=UUID(int=104),
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                input_hash=ctx.input_hash,
                stream_id=uuid5(UUID(int=102), str(UUID(int=102))),
                version=1,
                event_time_ms=11000,
                available_time_ms=11000,
                recorded_at=STAMP,
                body=Review(
                    document_id=UUID(int=102),
                    subject_id=UUID(int=102),
                    actor_id=ctx.actor_id,
                    expected_version=1,
                    decision="RELEVANT",
                    reason="Synthetic review only",
                ),
            )
            with tx.begin() as uow:
                service.review(ctx, review, uow)
                service.review(ctx, review, uow)
                uow.commit()
            # Restart reconstructs append-only journal without provider state.
            tx = AdvisoryReferenceTransactions(path)
            with tx.begin() as uow:
                rows = journal(ctx, repo(uow).inventory(ctx))
                if len(rows) != 4 or rows[0].body.kind != "FINDINGS":
                    raise RuntimeError("MOCK journal/restart failed")
                renderer = ReportRenderer(service, access)
                for fmt in ("JSON", "CSV", "HTML"):
                    data, artifact = renderer.render(
                        ctx, UUID(int=102), fmt, artifact_id=UUID(int=200), now=STAMP, uow=uow
                    )
                    if len(data) != artifact.size_bytes or artifact.required_capability != "export":
                        raise RuntimeError("MOCK report boundary failed")
                before = repo(uow).inventory(ctx)
            answer = await service.query(
                ctx,
                "What is still pending?",
                inputs,
                executor,
                checkpoint=lambda: None,
                reserve=lambda _: None,
            )
            with tx.begin() as uow:
                if repo(uow).inventory(ctx) != before or not answer.items:
                    raise RuntimeError("MOCK read-only query failed")
                service.purge(ctx, uow)
                uow.commit()
            with tx.begin() as uow:
                if repo(uow).inventory(ctx):
                    raise RuntimeError("MOCK purge failed")
                if len(memory_repo(uow).inventory(ctx)) != 2:
                    raise RuntimeError("MOCK purge crossed ownership")
        finally:
            await executor.close()
        if not client.closed or registration.routes or registration.job_handlers:
            raise RuntimeError("MOCK lifecycle/import boundary failed")
    if path.exists():
        raise RuntimeError("Disposable cleanup failed")
    return {
        "unit": "B05",
        "profile": "MOCK",
        "status": "passed",
        "mock_provider_calls": client.calls,
        "real_provider_calls": 0,
        "real_stt_calls": 0,
        "real_gemini_calls": 0,
        "database": "disposable-cleaned",
        "integrated_pipeline_ready": False,
        "B03_EXTERNAL_ACCEPTANCE_PENDING": [
            "STT_ACCOUNT_LOGIN_REQUIRED",
            "AUDITED_BENCHMARK_PENDING",
        ],
        "B04_EXTERNAL_ACCEPTANCE_PENDING": [
            "GEMINI_ACCOUNT_ACCESS_UNVERIFIED",
            "REAL_GEMINI_SMOKE_PENDING",
            "AUDITED_SEMANTIC_BENCHMARK_PENDING",
        ],
        "GEMINI_EXTERNAL_ACCEPTANCE_PENDING": True,
        "real_smoke": "NOT_RUN",
        "benchmark_status": "BLOCKED",
        "benchmark_metrics": None,
    }


def main() -> None:
    print(json.dumps(asyncio.run(run())))


if __name__ == "__main__":
    main()
