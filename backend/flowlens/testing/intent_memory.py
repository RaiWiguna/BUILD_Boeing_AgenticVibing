"""Executable B04 acceptance: explicit MOCK provider and disposable injected ports."""

import asyncio
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid5

from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
from flowlens.analysis.transcript_store import TRANSCRIPT_MIGRATIONS
from flowlens.contracts.models import Evidence, RequestContext, TranscriptSegment
from flowlens.contracts.ports import Repository, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.intent.models import Candidate, Provenance, QuoteSlot, Response
from flowlens.memory.models import NAMESPACE
from flowlens.memory.reducer import reconstruct
from flowlens.memory.service import AcceptedInputs, MemoryService, repo
from flowlens.memory.store import MEMORY_MIGRATIONS, SQLiteMemoryRepository
from flowlens.providers.gemini.adapter import GeminiExecutor
from flowlens.providers.gemini.models import GeminiConfig, Reply
from flowlens.providers.gemini.tools import BoundedTools
from flowlens.testing.analysis import PLATFORM_REFERENCE
from flowlens.testing.harness import FakePlatform, SQLiteTransactionFactory
from flowlens.testing.transcripts import TranscriptReferenceTransactions, TranscriptReferenceUOW

STAMP = datetime(2026, 10, 9, tzinfo=UTC)
ENTITY = UUID(int=214)


def context() -> RequestContext:
    return RequestContext(
        actor_id=UUID(int=3),
        capabilities=["read", "analysis", "review", "admin"],
        session_id=UUID(int=1),
        analysis_run_id=UUID(int=2),
        input_revision=1,
        input_hash="a" * 64,
        as_of_ms=100000,
        mode="AS_KNOWN",
        request_id=UUID(int=4),
    )


def mock_provenance(ctx: RequestContext, cfg: GeminiConfig) -> Provenance:
    return Provenance(
        profile="MOCK",
        model=cfg.model,
        api_version=cfg.api_version,
        sdk_version=cfg.sdk_version,
        prompt_version=cfg.prompt_version,
        schema_hash="d" * 64,
        config_hash=cfg.digest(),
        input_hash=ctx.input_hash,
        request_hashes=(),
        response_hashes=(),
        calls=0,
        total_tokens=None,
    )


def fixture(
    ctx: RequestContext,
    identifier: int,
    text: str,
    act: str = "INSTRUCTION",
    callsign: str = "FLN214",
    runway: str = "27",
    time_ms: int = 1000,
) -> tuple[TranscriptSegment, Candidate]:
    """Synthetic MOCK input/output, never claimed as provider or evaluator gold."""
    sid = UUID(int=identifier)
    evs: list[Evidence] = []

    def quote(value: str) -> Evidence:
        start = text.index(value)
        ev = Evidence(
            id=uuid5(sid, value),
            session_id=ctx.session_id,
            analysis_run_id=ctx.analysis_run_id,
            revision=ctx.input_revision,
            kind="TRANSCRIPT",
            source_id=UUID(int=5),
            segment_id=sid,
            start_ms=time_ms,
            end_ms=time_ms + 500,
            quote=value,
            span_start=start,
            span_end=start + len(value),
            source_hash="b" * 64,
        )
        if ev not in evs:
            evs.append(ev)
        return ev

    def slot(value: str | None) -> QuoteSlot:
        return QuoteSlot(
            value=value,
            quality="MISSING" if value is None else "SUPPORTED",
            evidence_ids=() if value is None else (quote(value).id,),
            alternatives=(),
            unknowns=("NO_EXPLICIT_CUE",) if value is None else (),
        )

    cs, rw = slot(callsign), slot(runway)
    condition = next(
        (text[text.index(cue) :] for cue in ("after", "until", "if") if cue in text), None
    )
    negation = next((cue for cue in ("not", "negative", "cancel") if cue in text.split()), None)
    cond, neg = slot(condition), slot(negation)
    action = quote("hold short" if "hold short" in text else text)
    candidate = Candidate.model_validate(
        {
            "id": uuid5(sid, "candidate"),
            "segment_id": sid,
            "speech_act": act,
            "role": "PILOT" if act in ("READBACK", "REPORT") else "CONTROLLER",
            "entity_candidates": (ENTITY,),
            "callsign": cs,
            "runway": rw,
            "actions": ("HOLD_SHORT",) if "hold short" in text else ("REPORT",),
            "action_evidence_ids": (action.id,),
            "condition": cond,
            "negation": neg,
            "evidence": tuple(evs),
            "unknowns": (),
        }
    )
    segment = TranscriptSegment(
        id=sid,
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        event_time_ms=time_ms,
        available_time_ms=time_ms + 500,
        recorded_at=STAMP,
        evidence=evs,
        source_id=UUID(int=5),
        start_ms=time_ms,
        end_ms=time_ms + 500,
        channel=0,
        text=text,
        speaker_id=None,
        confidence=None,
        quality="SUPPORTED",
        origin="MOCK",
        provider_profile_version="MOCK-b04-1",
        supersedes_id=None,
        reason=None,
    )
    return segment, candidate


class MemoryReferenceUOW(TranscriptReferenceUOW):
    def repository(self, namespace: str) -> Repository:
        self.check_open()
        if namespace == NAMESPACE:
            return SQLiteMemoryRepository(self.conn, self.check_open)
        return super().repository(namespace)


class MemoryReferenceTransactions(TranscriptReferenceTransactions):
    def __init__(self, path: Path) -> None:
        SQLiteTransactionFactory.__init__(self, path)
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS mock_migrations(id TEXT PRIMARY KEY, hash TEXT)"
            )
            conn.commit()
        self.migrate(
            (PLATFORM_REFERENCE, *ANALYSIS_MIGRATIONS, *TRANSCRIPT_MIGRATIONS, *MEMORY_MIGRATIONS)
        )

    @contextmanager
    def begin(self) -> Iterator[MemoryReferenceUOW]:
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            uow = MemoryReferenceUOW(conn)
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


class MockAuthority:
    """Test-only authority with explicit cancellation/config/scope checks."""

    def __init__(self, ctx: RequestContext, segments: list[TranscriptSegment], config: str) -> None:
        self.ctx, self.config = ctx, config
        self.inputs = AcceptedInputs(
            {s.id: s for s in segments},
            {ENTITY: ("FLN214",)},
            {s.id: "CONTROLLER" if i == 0 else "PILOT" for i, s in enumerate(segments)},
            True,
        )
        self.cancelled = False

    def authoritative(
        self,
        context: RequestContext,
        candidate: Candidate,
        config_hash: str,
        uow: UnitOfWork,
        *,
        provenance: Provenance,
    ) -> AcceptedInputs:
        if self.cancelled:
            raise ContractError("JOB_CANCELLED")
        if config_hash != self.config or context != self.ctx or provenance.profile != "MOCK":
            raise ContractError("SOURCE_REVISION_CHANGED")
        return self.inputs


class MockClient:
    profile = "MOCK"

    def __init__(self, response: Response) -> None:
        self.response, self.calls, self.closed = response, 0, False

    async def create(self, payload: str, config: GeminiConfig) -> Reply:
        self.calls += 1
        response = (
            self.response
            if json.loads(payload)["stage"] == "EXTRACT"
            else Response(
                status="COMPLETE",
                tools=(),
                candidates=(),
            )
        )
        return Reply(
            text=response.model_dump_json(),
            status="COMPLETE",
            input_tokens=100,
            output_tokens=100,
            total_tokens=200,
        )

    async def close(self) -> None:
        self.closed = True


async def run() -> dict[str, object]:
    ctx, config = context(), GeminiConfig()
    pairs = [
        fixture(ctx, 10, "FLN214 hold short runway 27"),
        fixture(ctx, 11, "FLN214 hold short runway 27", "READBACK", time_ms=3000),
    ]
    segments = [p[0] for p in pairs]
    platform = FakePlatform([], segments)
    response = Response(status="COMPLETE", tools=(), candidates=tuple(p[1] for p in pairs))
    client = MockClient(response)
    executor = GeminiExecutor(config, client)
    reservations: list[int] = []
    try:
        result = await executor.extract(
            ctx,
            segments,
            {ENTITY: ("FLN214",)},
            BoundedTools(config, ctx, platform, platform),
            checkpoint=lambda: None,
            reserve=reservations.append,
        )
    finally:
        await executor.close()
    with TemporaryDirectory(prefix="flowlens-b04-") as temporary:
        path = Path(temporary) / "b04.db"
        tx = MemoryReferenceTransactions(path)
        tx.seed(ctx)
        service = MemoryService(MockAuthority(ctx, segments, config.digest()), platform)
        with tx.begin() as uow:
            for item in result.response.candidates:
                service.accept(
                    ctx,
                    item,
                    config_hash=config.digest(),
                    provenance=result.provenance,
                    recorded_at=STAMP,
                    uow=uow,
                )
            uow.commit()
        # Restart reads persisted records, without hidden provider state.
        tx = MemoryReferenceTransactions(path)
        with tx.begin() as uow:
            events = repo(uow).inventory(ctx)
            projection = reconstruct(ctx, events)
        if len(projection) != 1 or projection[0].loop != "CLOSED_WITH_EVIDENCE":
            raise RuntimeError("MOCK reconstruction acceptance failed")
        if projection[0].movement != "NOT_EVALUABLE" or not client.closed:
            raise RuntimeError("MOCK boundary failed")
        with tx.begin() as uow:
            service.purge(ctx, uow)
            uow.commit()
        with tx.begin() as uow:
            if repo(uow).inventory(ctx):
                raise RuntimeError("MOCK purge failed")
    return {
        "unit": "B04",
        "profile": "MOCK",
        "status": "passed",
        "mock_provider_calls": client.calls,
        "real_provider_calls": 0,
        "pipeline_ready": False,
        "database": "disposable-cleaned",
        "B03_EXTERNAL_ACCEPTANCE_PENDING": True,
    }


def main() -> None:
    print(json.dumps(asyncio.run(run())))


if __name__ == "__main__":
    main()
