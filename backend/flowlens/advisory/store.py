"""Private append-only advisory ledger with scoped optimistic versions and caller UOW."""

import sqlite3
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from flowlens.advisory.models import Entry
from flowlens.analysis.repository import scope
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import Repository
from flowlens.core.errors import ContractError
from flowlens.core.modules import MigrationSpec

MIGRATIONS = (
    MigrationSpec(
        "analysis.0004",
        "B",
        ("analysis.0003",),
        """
CREATE TABLE analysis_advisory_ledger(
 id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision>0), input_hash TEXT NOT NULL CHECK(length(input_hash)=64),
 stream_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
 payload TEXT NOT NULL CHECK(json_valid(payload)),
 UNIQUE(session_id,run_id,revision,stream_id,version),
 FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
 FOREIGN KEY(session_id,run_id,revision) REFERENCES platform_runs(session_id,id,revision));
""",
    ),
)


class AdvisoryRepository(Repository, Protocol):
    def get(self, context: RequestContext, record_id: UUID) -> Entry: ...
    def inventory(self, context: RequestContext) -> tuple[Entry, ...]: ...
    def purge(self, context: RequestContext) -> None: ...


class SQLiteAdvisoryRepository:
    def __init__(self, connection: sqlite3.Connection, guard: Callable[[], None]) -> None:
        self.connection, self.guard = connection, guard

    def append(self, context: RequestContext, record: Contract) -> UUID:
        self.guard()
        context.require("analysis", context.session_id, context.analysis_run_id)
        if not isinstance(record, Entry):
            raise ContractError("INVALID_INPUT")
        record = Entry.model_validate_json(record.model_dump_json())
        if (str(record.session_id), str(record.analysis_run_id), record.revision) != scope(context):
            raise ContractError("ACCESS_DENIED")
        parent = self.connection.execute(
            "SELECT input_hash FROM platform_revisions WHERE session_id=? AND revision=?",
            (str(context.session_id), context.input_revision),
        ).fetchone()
        if (
            parent is None
            or parent["input_hash"] != context.input_hash
            or record.input_hash != context.input_hash
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        previous = self.connection.execute(
            "SELECT COALESCE(MAX(version),0) FROM analysis_advisory_ledger WHERE "
            "session_id=? AND run_id=? AND revision=? AND stream_id=?",
            (*scope(context), str(record.stream_id)),
        ).fetchone()[0]
        if record.version != previous + 1:
            raise ContractError("VERSION_CONFLICT")
        try:
            self.connection.execute(
                "INSERT INTO analysis_advisory_ledger VALUES(?,?,?,?,?,?,?,?)",
                (
                    str(record.id),
                    *scope(context),
                    record.input_hash,
                    str(record.stream_id),
                    record.version,
                    record.model_dump_json(),
                ),
            )
        except sqlite3.IntegrityError:
            raise ContractError("VERSION_CONFLICT") from None
        return record.id

    def get(self, context: RequestContext, record_id: UUID) -> Entry:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        row = self.connection.execute(
            "SELECT * FROM analysis_advisory_ledger WHERE id=?", (str(record_id),)
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (row["session_id"], row["run_id"], row["revision"]) != scope(context):
            raise ContractError("ACCESS_DENIED")
        if row["input_hash"] != context.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        return Entry.model_validate_json(row["payload"])

    def inventory(self, context: RequestContext) -> tuple[Entry, ...]:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        rows = self.connection.execute(
            "SELECT id FROM analysis_advisory_ledger WHERE session_id=? AND run_id=? "
            "AND revision=? ORDER BY stream_id,version",
            scope(context),
        ).fetchall()
        return tuple(self.get(context, UUID(row["id"])) for row in rows)

    def purge(self, context: RequestContext) -> None:
        self.guard()
        context.require("admin", context.session_id, context.analysis_run_id)
        self.connection.execute(
            "DELETE FROM analysis_advisory_ledger WHERE session_id=? AND run_id=? AND revision=?",
            scope(context),
        )
