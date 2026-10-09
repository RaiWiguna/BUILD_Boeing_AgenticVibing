"""Development-only adapters and disposable SQLite contract reference harness.

This is executable specification, not the platform persistence/job implementation.
"""

import hashlib
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter

from flowlens.contracts.models import (
    ArtifactSubmission,
    CommitReceipt,
    Contract,
    Evidence,
    GeometryResult,
    JobLease,
    JobResult,
    RequestContext,
    Snapshot,
    SourceEvent,
    SourceManifest,
    ToolRequest,
    Track,
    TranscriptSegment,
)
from flowlens.contracts.ports import EvidenceService, Repository, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.core.modules import MigrationSpec, ModuleRegistration, ModuleRegistry


class FakePlatform:
    profile = "MOCK"

    def __init__(
        self,
        events: list[SourceEvent],
        segments: list[TranscriptSegment] | None = None,
        manifests: list[SourceManifest] | None = None,
    ) -> None:
        self.events = events
        self.segments = segments or []
        self.manifests = manifests or []
        self.revoked: set[UUID] = set()

    def revoke(self, actor_id: UUID) -> None:
        self.revoked.add(actor_id)

    def authorize(self, context: RequestContext) -> None:
        context.require("read", context.session_id)
        if context.actor_id in self.revoked:
            raise ContractError("ACCESS_DENIED")

    def visible(self, context: RequestContext, row: SourceEvent | TranscriptSegment) -> bool:
        if row.session_id != context.session_id:
            return False
        if row.analysis_run_id is not None and row.analysis_run_id != context.analysis_run_id:
            return False
        if row.event_time_ms > context.as_of_ms:
            return False
        return context.mode == "DEBRIEF" or (
            row.available_time_ms is not None and row.available_time_ms <= context.as_of_ms
        )

    def read_events(self, context: RequestContext) -> list[SourceEvent]:
        self.authorize(context)
        return sorted(
            [row for row in self.events if self.visible(context, row)],
            key=lambda row: (row.event_time_ms, str(row.id)),
        )

    def manifest(self, context: RequestContext, source_id: UUID) -> SourceManifest:
        self.authorize(context)
        for row in self.manifests:
            if row.id == source_id and row.session_id == context.session_id:
                return row
        raise ContractError("ACCESS_DENIED")

    def tracks(self, context: RequestContext, entity_id: UUID) -> list[Track]:
        return [
            row
            for row in self.read_events(context)
            if isinstance(row, Track) and row.entity_id == entity_id
        ]

    def observations(self, context: RequestContext, entity_id: UUID) -> GeometryResult:
        self.authorize(context)
        return GeometryResult(
            session_id=context.session_id,
            analysis_run_id=context.analysis_run_id,
            revision=context.input_revision,
            entity_id=entity_id,
            status="NOT_EVALUABLE",
            reason="MOCK geometry unavailable",
            occupied=None,
            intervals=[],
            uncertainty_ms=None,
            rule_version="synthetic-1",
            layout_version=None,
            evidence=[],
        )

    def resolve(self, context: RequestContext, evidence: Evidence) -> Evidence:
        self.authorize(context)
        context.require("read", evidence.session_id, evidence.analysis_run_id)
        if evidence.revision != context.input_revision:
            raise ContractError("SOURCE_REVISION_CHANGED")
        if evidence.kind == "AUDIO":
            context.require("audio", evidence.session_id)
        for segment in self.segments:
            if segment.id != evidence.segment_id or not self.visible(context, segment):
                continue
            if evidence.source_id != segment.source_id:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if not any(e.source_hash == evidence.source_hash for e in segment.evidence):
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if evidence.start_ms is None or evidence.end_ms is None:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if evidence.start_ms < segment.start_ms or evidence.end_ms > segment.end_ms:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if evidence.span_start is None or evidence.span_end is None:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if evidence.span_end > len(segment.text) or evidence.span_start < 0:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if segment.text[evidence.span_start : evidence.span_end] != evidence.quote:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            return evidence
        raise ContractError("EVIDENCE_UNAVAILABLE")

    def register(self, context: RequestContext, evidence: Evidence, uow: UnitOfWork) -> UUID:
        resolved = self.resolve(context, evidence)
        return uow.repository("evidence").append(context, resolved)

    def lookup(self, context: RequestContext, request: ToolRequest) -> list[Contract]:
        self.authorize(context)
        if request.window is not None and request.window.end_ms > context.as_of_ms:
            raise ContractError("ACCESS_DENIED")
        if request.name == "get_session_events":
            return list(self.read_events(context)[: request.limit])
        if request.name == "get_transcript_window":
            return list[Contract](
                [row for row in self.segments if self.visible(context, row)][: request.limit]
            )
        # Unimplemented mock context is explicitly unavailable; no invented provider output.
        raise ContractError("NOT_EVALUABLE")


class FakeAnalysis:
    profile = "MOCK"

    def validate(
        self, context: RequestContext, candidate: JobResult, evidence: "EvidenceService"
    ) -> JobResult:
        context.require("analysis", candidate.session_id, candidate.analysis_run_id)
        if (
            candidate.revision != context.input_revision
            or candidate.input_hash != context.input_hash
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        for item in [
            *candidate.evidence,
            *(e for record in candidate.outputs for e in record.evidence),
        ]:
            evidence.resolve(context, item)
        return candidate

    def snapshot(self, context: RequestContext) -> Snapshot:
        context.require("read", context.session_id)
        return Snapshot(
            session_id=context.session_id,
            analysis_run_id=context.analysis_run_id,
            revision=context.input_revision,
            as_of_ms=context.as_of_ms,
            mode=context.mode,
            sequence=0,
            events=[],
            memory=[],
            findings=[],
            quality="MISSING",
        )

    def accept(self, context: RequestContext, candidate: JobResult, uow: UnitOfWork) -> None:
        context.require("analysis", candidate.session_id, candidate.analysis_run_id)
        for record in candidate.outputs:
            uow.repository("analysis").append(context, record)

    def purge(self, context: RequestContext, uow: UnitOfWork) -> None:
        context.require("admin", context.session_id)
        uow.audit(context, "MOCK_PURGE", context.session_id)


@dataclass
class HarnessBundle:
    track: Literal["A", "B"]
    platform: FakePlatform
    analysis: FakeAnalysis
    registry: ModuleRegistry
    assets: "FakeAssets"
    jobs: "FakeJobs"
    evidence: FakePlatform
    transactions: "SQLiteTransactionFactory | None"
    artifacts: "FakeArtifacts"
    geometry: FakePlatform
    context: FakePlatform
    profile: Literal["MOCK"] = "MOCK"


def build_harness(track: Literal["A", "B"], db_path: Path | None = None) -> HarnessBundle:
    platform = FakePlatform([])
    analysis = FakeAnalysis()
    registry = ModuleRegistry(profile="test")
    owner: Literal["A", "B"] = "B" if track == "A" else "A"
    router = APIRouter()

    @router.get("/_harness/module")
    def mock_metadata() -> dict[str, str]:
        return {"profile": "MOCK", "track": track}

    registry.register(
        ModuleRegistration(
            name=f"mock-{owner.lower()}",
            mock=True,
            routes=(router,),
            services={"source": platform, "analysis": analysis},
            repositories={"analysis": analysis},
            migrations=(MigrationSpec(f"mock-{owner.lower()}.1", owner, (), "SELECT 1;"),),
            job_handlers={"MOCK": analysis.accept},
            snapshot_reader=analysis.snapshot,
            purge_handler=analysis.purge,
            readiness=lambda: False,
            config_keys=("contract_version",),
            inventory_namespaces=("analysis",),
        )
    )
    return HarnessBundle(
        track,
        platform,
        analysis,
        registry,
        FakeAssets(UUID(int=1), {}),
        FakeJobs(),
        platform,
        SQLiteTransactionFactory(db_path) if db_path is not None else None,
        FakeArtifacts(),
        platform,
        platform,
    )


class SQLiteHarness:
    """Disposable reference schemas preserving constraints for standalone package tests."""

    def __init__(self, path: Path, target_version: int = 2) -> None:
        if target_version not in (1, 2):
            raise ValueError("unsupported harness schema version")
        self.path = path
        with self.connection() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > target_version:
                raise ValueError("harness downgrade forbidden")
            if version < 1:
                conn.executescript("""
                    BEGIN;
                    CREATE TABLE platform_sessions (id TEXT PRIMARY KEY);
                    CREATE TABLE platform_jobs (
                        session_id TEXT NOT NULL REFERENCES platform_sessions(id),
                        attempt_id TEXT NOT NULL, job_id TEXT NOT NULL, lease_id TEXT NOT NULL,
                        revision INTEGER NOT NULL CHECK(revision > 0), input_hash TEXT NOT NULL,
                        config_hash TEXT NOT NULL, expires_ms INTEGER NOT NULL,
                        cancelled INTEGER NOT NULL, rights INTEGER NOT NULL,
                        run_id TEXT NOT NULL, deadline_ms INTEGER NOT NULL,
                        budget_microunits INTEGER NOT NULL CHECK(budget_microunits >= 0),
                        PRIMARY KEY(session_id, attempt_id));
                    PRAGMA user_version = 1;
                    COMMIT;
                """)
            if version < 2 and target_version == 2:
                conn.executescript("""
                    BEGIN;
                    CREATE TABLE analysis_results (
                        session_id TEXT NOT NULL, attempt_id TEXT NOT NULL, payload TEXT NOT NULL,
                        PRIMARY KEY(session_id, attempt_id),
                        FOREIGN KEY(session_id, attempt_id)
                            REFERENCES platform_jobs(session_id, attempt_id));
                    CREATE TABLE platform_receipts (
                        session_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
                        request_hash TEXT NOT NULL,
                        payload TEXT NOT NULL, PRIMARY KEY(session_id, attempt_id),
                        FOREIGN KEY(session_id, attempt_id)
                            REFERENCES platform_jobs(session_id, attempt_id));
                    CREATE TABLE platform_events (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                        attempt_id TEXT NOT NULL, payload TEXT NOT NULL,
                        FOREIGN KEY(session_id, attempt_id)
                            REFERENCES platform_jobs(session_id, attempt_id));
                    CREATE TABLE platform_evidence (
                        id TEXT PRIMARY KEY, session_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        FOREIGN KEY(session_id, attempt_id)
                            REFERENCES platform_jobs(session_id, attempt_id));
                    CREATE TABLE platform_audit (
                        id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        FOREIGN KEY(session_id, attempt_id)
                            REFERENCES platform_jobs(session_id, attempt_id));
                    PRAGMA user_version = 2;
                    COMMIT;
                """)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def seed_job(
        self,
        result: JobResult,
        *,
        revision: int | None = None,
        expires_ms: int = 1000,
        cancelled: bool = False,
        rights: bool = True,
        config_hash: str | None = None,
        lease_id: str | None = None,
        run_id: str | None = None,
        deadline_ms: int = 2000,
        budget_microunits: int = 1000,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO platform_sessions VALUES (?)", (str(result.session_id),)
            )
            conn.execute(
                "INSERT INTO platform_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(result.session_id),
                    str(result.attempt_id),
                    str(result.job_id),
                    lease_id or str(result.lease_id),
                    revision or result.revision,
                    result.input_hash,
                    config_hash or result.config_hash,
                    expires_ms,
                    int(cancelled),
                    int(rights),
                    run_id or str(result.analysis_run_id),
                    deadline_ms,
                    budget_microunits,
                ),
            )

    def accept(
        self,
        result: JobResult,
        *,
        now_ms: int,
        publish: Callable[[CommitReceipt], None] | None = None,
        fail_before_commit: bool = False,
    ) -> CommitReceipt:
        key = (str(result.session_id), str(result.attempt_id))
        payload = result.model_dump_json()
        request_hash = hashlib.sha256(payload.encode()).hexdigest()
        with self.transaction() as conn:
            job = conn.execute(
                "SELECT * FROM platform_jobs WHERE session_id=? AND attempt_id=?", key
            ).fetchone()
            if job is None or job["job_id"] != str(result.job_id):
                raise ContractError("ACCESS_DENIED")
            if job["run_id"] != str(result.analysis_run_id):
                raise ContractError("ACCESS_DENIED")
            if not job["rights"]:
                raise ContractError("CLOUD_TRANSFER_BLOCKED")
            if job["revision"] != result.revision or job["input_hash"] != result.input_hash:
                raise ContractError("SOURCE_REVISION_CHANGED")
            if job["config_hash"] != result.config_hash:
                raise ContractError("VERSION_CONFLICT")
            previous = conn.execute(
                "SELECT * FROM platform_receipts WHERE session_id=? AND attempt_id=?", key
            ).fetchone()
            if previous is not None:
                if previous["request_hash"] != request_hash:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return CommitReceipt.model_validate_json(previous["payload"])
            if job["cancelled"]:
                raise ContractError("JOB_CANCELLED")
            if job["expires_ms"] <= now_ms or job["lease_id"] != str(result.lease_id):
                raise ContractError("LEASE_EXPIRED")
            if job["deadline_ms"] <= now_ms:
                raise ContractError("LEASE_EXPIRED")
            if job["budget_microunits"] == 0 or (
                result.usage.cost_microunits is not None
                and result.usage.cost_microunits > job["budget_microunits"]
            ):
                raise ContractError("BUDGET_EXCEEDED")
            conn.execute("INSERT INTO analysis_results VALUES (?, ?, ?)", (*key, payload))
            for evidence in result.evidence:
                conn.execute(
                    "INSERT INTO platform_evidence VALUES (?, ?, ?, ?)",
                    (
                        str(evidence.id),
                        *key,
                        evidence.model_dump_json(),
                    ),
                )
            conn.execute(
                "INSERT INTO platform_audit(session_id, attempt_id, action) VALUES(?,?,?)",
                (*key, "MOCK_ACCEPT"),
            )
            cursor = conn.execute(
                "INSERT INTO platform_events(session_id, attempt_id, payload) VALUES(?,?,?)",
                (*key, payload),
            )
            receipt = CommitReceipt(
                id=uuid4(),
                session_id=result.session_id,
                analysis_run_id=result.analysis_run_id,
                revision=result.revision,
                job_id=result.job_id,
                attempt_id=result.attempt_id,
                output_hash=result.output_hash,
                sequence=cursor.lastrowid or 1,
            )
            conn.execute(
                "INSERT INTO platform_receipts VALUES (?, ?, ?, ?)",
                (
                    *key,
                    request_hash,
                    receipt.model_dump_json(),
                ),
            )
            if fail_before_commit:
                raise RuntimeError("injected failure before commit")
        if publish is not None:
            publish(receipt)
        return receipt

    def counts(self) -> dict[str, int]:
        with self.connection() as conn:
            return {
                "receipts": int(
                    conn.execute("SELECT count(*) FROM platform_receipts").fetchone()[0]
                ),
                "events": int(conn.execute("SELECT count(*) FROM platform_events").fetchone()[0]),
                "results": int(conn.execute("SELECT count(*) FROM analysis_results").fetchone()[0]),
            }

    def schema_version(self) -> int:
        with self.connection() as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])

    def foreign_keys_enabled(self) -> bool:
        with self.connection() as conn:
            return bool(conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1)


class FakeAssets:
    profile = "MOCK"

    def __init__(self, session_id: UUID, assets: dict[UUID, bytes]) -> None:
        self.session_id = session_id
        self.assets = assets

    def download(self, context: RequestContext, asset_id: UUID, start: int, end: int) -> bytes:
        context.require("audio", self.session_id)
        content = self.assets.get(asset_id)
        if content is None or not 0 <= start < end <= len(content):
            raise ContractError("ACCESS_DENIED")
        return content[start:end]

    def submit(
        self, context: RequestContext, artifact: ArtifactSubmission, chunks: Iterator[bytes]
    ) -> UUID:
        context.require("audio", artifact.session_id, artifact.analysis_run_id)
        if artifact.session_id != self.session_id:
            raise ContractError("ACCESS_DENIED")
        content = bytearray()
        for chunk in chunks:
            content.extend(chunk)
            if len(content) > min(artifact.size_bytes, 1024 * 1024):
                raise ContractError("INVALID_INPUT")
        if (
            len(content) != artifact.size_bytes
            or hashlib.sha256(content).hexdigest() != artifact.sha256
        ):
            raise ContractError("INVALID_INPUT")
        self.assets[artifact.id] = bytes(content)
        return artifact.id


class FakeJobs:
    """Empty MOCK queue; actual lease transport belongs to A/B Phase 6."""

    profile = "MOCK"

    def lease(self, worker_id: UUID, stage: str) -> None:
        return None

    def heartbeat(self, lease: "JobLease") -> "JobLease":
        raise ContractError("LEASE_EXPIRED")

    def result(self, result: JobResult) -> CommitReceipt:
        raise ContractError("LEASE_EXPIRED")

    def cancelled(self, lease: "JobLease") -> bool:
        return True


class FakeArtifacts:
    profile = "MOCK"

    def submit(self, context: RequestContext, artifact: ArtifactSubmission) -> UUID:
        context.require("export", artifact.session_id, artifact.analysis_run_id)
        raise ContractError("NOT_EVALUABLE")

    def download(self, context: RequestContext, artifact_id: UUID) -> Iterator[bytes]:
        context.require("export", context.session_id)
        raise ContractError("EVIDENCE_UNAVAILABLE")

    def inventory(self, context: RequestContext) -> list[ArtifactSubmission]:
        context.require("export", context.session_id)
        return []

    def purge(self, context: RequestContext, uow: UnitOfWork) -> None:
        context.require("admin", context.session_id)
        uow.audit(context, "MOCK_ARTIFACT_PURGE", context.session_id)


class SQLiteRepository:
    def __init__(self, conn: sqlite3.Connection, namespace: str) -> None:
        self.conn = conn
        self.namespace = namespace

    def append(self, context: RequestContext, record: Contract) -> UUID:
        context.require("analysis", context.session_id, context.analysis_run_id)
        session = getattr(record, "session_id", None)
        run = getattr(record, "analysis_run_id", None)
        revision = getattr(record, "revision", None)
        identifier = getattr(record, "id", None)
        if (session, run, revision) != (
            context.session_id,
            context.analysis_run_id,
            context.input_revision,
        ):
            raise ContractError("ACCESS_DENIED")
        if not isinstance(identifier, UUID):
            raise ContractError("INVALID_INPUT")
        self.conn.execute(
            "INSERT OR IGNORE INTO reference_sessions VALUES (?)", (str(context.session_id),)
        )
        self.conn.execute(
            "INSERT INTO reference_records VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                self.namespace,
                str(identifier),
                str(context.session_id),
                str(context.analysis_run_id),
                context.input_revision,
                type(record).__name__,
                record.model_dump_json(),
            ),
        )
        return identifier

    def get(self, context: RequestContext, record_id: UUID) -> Contract:
        from flowlens.contracts.models import INTERNAL_MODELS, PUBLIC_MODELS

        context.require("read", context.session_id)
        row = self.conn.execute(
            "SELECT * FROM reference_records WHERE namespace=? AND id=?",
            (self.namespace, str(record_id)),
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        if (row["session_id"], row["run_id"], row["revision"]) != (
            str(context.session_id),
            str(context.analysis_run_id),
            context.input_revision,
        ):
            raise ContractError("ACCESS_DENIED")
        classes = {cls.__name__: cls for cls in (*PUBLIC_MODELS, *INTERNAL_MODELS)}
        return classes[row["kind"]].model_validate_json(row["payload"])


class SQLiteUnitOfWork:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.callbacks: list[Callable[[], None]] = []
        self.committed = False
        self.closed = False

    def check_open(self) -> None:
        if self.closed:
            raise RuntimeError("unit-of-work already closed")

    def repository(self, namespace: str) -> Repository:
        self.check_open()
        if namespace not in ("analysis", "evidence"):
            raise ValueError("unknown repository namespace")
        return SQLiteRepository(self.conn, namespace)

    def enqueue_event(self, context: RequestContext, payload: Contract) -> int:
        self.check_open()
        context.require(
            "analysis",
            getattr(payload, "session_id", UUID(int=0)),
            getattr(payload, "analysis_run_id", None),
        )
        cursor = self.conn.execute(
            "INSERT INTO reference_events(session_id,payload) VALUES (?,?)",
            (str(context.session_id), payload.model_dump_json()),
        )
        return cursor.lastrowid or 1

    def audit(self, context: RequestContext, action: str, target_id: UUID) -> None:
        self.check_open()
        self.conn.execute(
            "INSERT INTO reference_audit(session_id,actor_id,action,target_id) VALUES(?,?,?,?)",
            (str(context.session_id), str(context.actor_id), action, str(target_id)),
        )

    def after_commit(self, callback: Callable[[], None]) -> None:
        self.check_open()
        self.callbacks.append(callback)

    def commit(self) -> None:
        self.check_open()
        self.conn.commit()
        self.committed = True
        self.closed = True

    def rollback(self) -> None:
        if not self.committed:
            self.conn.rollback()
        self.callbacks.clear()
        self.closed = True


class SQLiteTransactionFactory:
    """Standalone repository adapter, never mounted/used by worker."""

    profile = "MOCK"

    def __init__(self, path: Path) -> None:
        self.path = path
        with closing(sqlite3.connect(path)) as conn:
            conn.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS reference_sessions(id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS reference_records(
                    namespace TEXT NOT NULL, id TEXT NOT NULL, session_id TEXT NOT NULL,
                    run_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision > 0),
                    kind TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(namespace, id),
                    FOREIGN KEY(session_id) REFERENCES reference_sessions(id));
                CREATE TABLE IF NOT EXISTS reference_events(sequence INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES reference_sessions(id),
                    payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reference_audit(id INTEGER PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES reference_sessions(id),
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL, target_id TEXT NOT NULL);
            """)

    @contextmanager
    def begin(self) -> Iterator[SQLiteUnitOfWork]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        uow = SQLiteUnitOfWork(conn)
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield uow
        except BaseException:
            uow.rollback()
            raise
        finally:
            if not uow.committed:
                uow.rollback()
            conn.close()
        # Callback failure does not undo committed state: callers resync durable event cursor.
        if uow.committed:
            for callback in uow.callbacks:
                callback()
