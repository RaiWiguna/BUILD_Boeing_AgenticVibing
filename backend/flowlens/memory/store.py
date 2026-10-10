"""Connection-injected append-only B ledger, never a worker-owned database."""

import sqlite3
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from flowlens.analysis.repository import scope
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import Repository
from flowlens.core.errors import ContractError
from flowlens.core.modules import MigrationSpec
from flowlens.memory.models import AcceptedEvent, Invalidation

MEMORY_MIGRATIONS = (
    MigrationSpec(
        "analysis.0003",
        "B",
        ("analysis.0002",),
        """CREATE TABLE analysis_memory_ledger(
        id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>0), input_hash TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('ACCEPTED','INVALIDATION')),
        payload TEXT NOT NULL CHECK(json_valid(payload)),
        CHECK(length(input_hash)=64),
        FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
        FOREIGN KEY(session_id,run_id,revision)
          REFERENCES platform_runs(session_id,id,revision));""",
    ),
)


class MemoryRepository(Repository, Protocol):
    def get(self, context: RequestContext, record_id: UUID) -> AcceptedEvent | Invalidation: ...
    def inventory(self, context: RequestContext) -> tuple[AcceptedEvent | Invalidation, ...]: ...
    def purge(self, context: RequestContext) -> None: ...


class SQLiteMemoryRepository:
    def __init__(self, connection: sqlite3.Connection, guard: Callable[[], None]) -> None:
        self.connection, self.guard = connection, guard

    def append(self, context: RequestContext, record: Contract) -> UUID:
        self.guard()
        context.require("analysis", context.session_id, context.analysis_run_id)
        if not isinstance(record, (AcceptedEvent, Invalidation)):
            raise ContractError("INVALID_INPUT")
        row = type(record).model_validate_json(record.model_dump_json())
        if (str(row.session_id), str(row.analysis_run_id), row.revision) != scope(context):
            raise ContractError("ACCESS_DENIED")
        parent = self.connection.execute(
            "SELECT input_hash FROM platform_revisions WHERE session_id=? AND revision=?",
            (str(context.session_id), context.input_revision),
        ).fetchone()
        if (
            parent is None
            or parent["input_hash"] != context.input_hash
            or (row.input_hash != context.input_hash)
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        try:
            self.connection.execute(
                "INSERT INTO analysis_memory_ledger VALUES (?,?,?,?,?,?,?)",
                (
                    str(row.id),
                    *scope(context),
                    row.input_hash,
                    "ACCEPTED" if isinstance(row, AcceptedEvent) else "INVALIDATION",
                    row.model_dump_json(),
                ),
            )
        except sqlite3.IntegrityError:
            raise ContractError("VERSION_CONFLICT") from None
        return row.id

    def get(self, context: RequestContext, record_id: UUID) -> AcceptedEvent | Invalidation:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        row = self.connection.execute(
            "SELECT * FROM analysis_memory_ledger WHERE id=?", (str(record_id),)
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (row["session_id"], row["run_id"], row["revision"]) != scope(context):
            raise ContractError("ACCESS_DENIED")
        if row["input_hash"] != context.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        model = AcceptedEvent if row["kind"] == "ACCEPTED" else Invalidation
        return model.model_validate_json(row["payload"])

    def inventory(self, context: RequestContext) -> tuple[AcceptedEvent | Invalidation, ...]:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        rows = self.connection.execute(
            "SELECT id FROM analysis_memory_ledger WHERE session_id=? AND run_id=? "
            "AND revision=? ORDER BY id",
            scope(context),
        ).fetchall()
        return tuple(self.get(context, UUID(row["id"])) for row in rows)

    def purge(self, context: RequestContext) -> None:
        self.guard()
        context.require("admin", context.session_id, context.analysis_run_id)
        self.connection.execute(
            "DELETE FROM analysis_memory_ledger WHERE session_id=? AND run_id=? AND revision=?",
            scope(context),
        )
