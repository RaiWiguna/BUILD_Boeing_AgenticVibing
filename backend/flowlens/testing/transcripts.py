"""Disposable transcript UOW; explicit MOCK platform authority/evidence for standalone tests."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
from flowlens.analysis.transcript_projection import project
from flowlens.analysis.transcript_records import RawTranscript, TranscriptDependency
from flowlens.analysis.transcript_store import RECORDS, TRANSCRIPT_MIGRATIONS, factory
from flowlens.analysis.transcripts import TranscriptLifecycle, register_transcripts
from flowlens.contracts.models import RequestContext, TranscriptSegment
from flowlens.contracts.ports import Repository, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistry
from flowlens.providers.stt.adapter import map_response
from flowlens.testing.analysis import (
    PLATFORM_REFERENCE,
    AnalysisReferenceTransactions,
    AnalysisReferenceUOW,
)
from flowlens.testing.harness import FakePlatform, SQLiteTransactionFactory
from flowlens.testing.stt import mock_binding, mock_config, mock_response


class TranscriptReferenceUOW(AnalysisReferenceUOW):
    def repository(self, namespace: str) -> Repository:
        if namespace in RECORDS:
            self.check_open()
            return factory(namespace)(self.conn, self.check_open)
        return super().repository(namespace)


class TranscriptReferenceTransactions(AnalysisReferenceTransactions):
    def __init__(self, path: Path) -> None:
        SQLiteTransactionFactory.__init__(self, path)
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS mock_migrations(id TEXT PRIMARY KEY, hash TEXT)"
            )
            conn.commit()
        self.migrate((PLATFORM_REFERENCE, *ANALYSIS_MIGRATIONS, *TRANSCRIPT_MIGRATIONS))

    @contextmanager
    def begin(self) -> Iterator[TranscriptReferenceUOW]:
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            uow = TranscriptReferenceUOW(conn)
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


def main() -> None:
    config = mock_config()
    binding, _ = mock_binding(config)
    raw = map_response(config, binding, mock_response())
    context = RequestContext.model_validate(
        binding.context.model_dump()
        | {"capabilities": ["read", "audio", "analysis", "review", "admin"], "as_of_ms": 100000}
    )
    segment = project(raw, recorded_at=datetime.now(UTC), origin="MOCK")[0]
    evidence = FakePlatform([], [segment])

    def authority(ctx: RequestContext, candidate: RawTranscript, uow: UnitOfWork) -> None:
        # Explicit MOCK platform attestation; not a durable live-job authority.
        ctx.require("analysis", candidate.session_id, candidate.analysis_run_id)
        if candidate != raw:
            raise ContractError("LEASE_EXPIRED")

    with TemporaryDirectory(prefix="flowlens-b03-") as temporary:
        transactions = TranscriptReferenceTransactions(Path(temporary) / "b03.db")
        transactions.seed(context)
        registration = register_transcripts(transactions, evidence, authority)
        ModuleRegistry(profile="test").register(registration)
        service = registration.services["transcript_lifecycle"]
        if not isinstance(service, TranscriptLifecycle) or registration.readiness is None:
            raise RuntimeError("Missing lifecycle")
        with transactions.begin() as uow:
            service.store_raw(context, raw, uow)
            service.add_original(context, raw.id, segment, uow)
            dep = TranscriptDependency(
                id=uuid4(),
                session_id=context.session_id,
                analysis_run_id=raw.analysis_run_id,
                revision=context.input_revision,
                input_hash=context.input_hash,
                transcript_ids=(segment.id,),
                kind="INTENT",
            )
            service.depend(context, dep, uow)
            correction_id = uuid4()
            ev = segment.evidence[0].model_copy(
                update={
                    "id": uuid4(),
                    "segment_id": correction_id,
                    "quote": "hold short",
                    "span_end": 10,
                }
            )
            correction = TranscriptSegment.model_validate(
                segment.model_dump()
                | {
                    "id": correction_id,
                    "text": "hold short",
                    "origin": "HUMAN_CORRECTION",
                    "supersedes_id": segment.id,
                    "reason": "Synthetic MOCK review",
                    "confidence": None,
                    "evidence": [ev.model_dump()],
                }
            )
            evidence.segments.append(correction)
            service.correct(context, segment.id, correction, uow)
            if not service.stale(context, dep.id, uow):
                raise RuntimeError("Dependency did not become stale")
            uow.commit()
        reopened = TranscriptReferenceTransactions(transactions.path)
        with reopened.begin() as uow:
            if service.current_segments(context, uow) != (correction,) or registration.readiness():
                raise RuntimeError("Recovery invariant failed")
            if service.resolve_audio(context, correction_id, uow).source_asset_id != UUID(int=6):
                raise RuntimeError("Audio link mismatch")
    print(
        json.dumps(
            {
                "unit": "B03_LIFECYCLE",
                "profile": "MOCK",
                "status": "passed",
                "provider_calls": 0,
                "pipeline_ready": False,
                "database": "disposable-cleaned",
            }
        )
    )


if __name__ == "__main__":
    main()
