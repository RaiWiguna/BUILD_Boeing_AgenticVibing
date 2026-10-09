"""API-side injected repositories for private transcript provenance and revision chains."""

import sqlite3
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from flowlens.analysis.repository import scope
from flowlens.analysis.transcript_records import (
    RawTranscript,
    TranscriptChange,
    TranscriptDependency,
    TranscriptRevision,
)
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import Repository
from flowlens.core.errors import ContractError
from flowlens.core.modules import MigrationSpec

Record = RawTranscript | TranscriptRevision | TranscriptDependency | TranscriptChange
RECORDS: dict[str, tuple[str, type[Record]]] = {
    "analysis.transcript.raw": ("analysis_transcript_raw", RawTranscript),
    "analysis.transcript.revision": ("analysis_transcript_revisions", TranscriptRevision),
    "analysis.transcript.dependency": ("analysis_transcript_dependencies", TranscriptDependency),
    "analysis.transcript.change": ("analysis_transcript_changes", TranscriptChange),
}

TRANSCRIPT_MIGRATIONS = (
    MigrationSpec(
        "analysis.0002",
        "B",
        ("analysis.0001",),
        "\n".join(
            f"""CREATE TABLE {table}(
        id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL,
        run_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
        input_hash TEXT NOT NULL CHECK(length(input_hash)=64),
        payload TEXT NOT NULL CHECK(json_valid(payload)),
        FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
        FOREIGN KEY(session_id,run_id,revision)
            REFERENCES platform_runs(session_id,id,revision));"""
            for table, _ in RECORDS.values()
        )
        + """
    CREATE UNIQUE INDEX analysis_raw_chunk ON analysis_transcript_raw(
        session_id,run_id,revision,json_extract(payload,'$.chunk_id'));
    CREATE UNIQUE INDEX analysis_correction_version ON analysis_transcript_revisions(
        session_id,run_id,revision,json_extract(payload,'$.original_id'),
        json_extract(payload,'$.correction_revision'));
    """,
    ),
)


class TranscriptRepository(Repository, Protocol):
    def get(self, context: RequestContext, record_id: UUID) -> Record: ...
    def inventory(self, context: RequestContext) -> tuple[Record, ...]: ...
    def purge(self, context: RequestContext) -> None: ...


class SQLiteTranscriptRepository:
    """SQL identifiers come exclusively from static RECORDS; all values are bound."""

    def __init__(
        self, connection: sqlite3.Connection, guard: Callable[[], None], namespace: str
    ) -> None:
        self.connection, self.guard = connection, guard
        self.table, self.model = RECORDS[namespace]

    def append(self, context: RequestContext, record: Contract) -> UUID:
        self.guard()
        context.require("analysis", context.session_id, context.analysis_run_id)
        if not isinstance(record, self.model):
            raise ContractError("INVALID_INPUT")
        row = self.model.model_validate_json(record.model_dump_json())
        if (str(row.session_id), str(row.analysis_run_id), row.revision) != scope(context):
            raise ContractError("ACCESS_DENIED")
        parent = self.connection.execute(
            "SELECT input_hash FROM platform_revisions WHERE session_id=? AND revision=?",
            (str(context.session_id), context.input_revision),
        ).fetchone()
        if (
            parent is None
            or parent["input_hash"] != context.input_hash
            or row.input_hash != context.input_hash
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        try:
            self.connection.execute(
                f"INSERT INTO {self.table} VALUES (?,?,?,?,?,?)",  # nosec B608
                (str(row.id), *scope(context), row.input_hash, row.model_dump_json()),
            )
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode in (
                sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
                sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            ):
                raise ContractError("VERSION_CONFLICT") from None
            raise
        return row.id

    def get(self, context: RequestContext, record_id: UUID) -> Record:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        row = self.connection.execute(
            f"SELECT * FROM {self.table} WHERE id=?",  # nosec B608
            (str(record_id),),
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (row["session_id"], row["run_id"], row["revision"]) != scope(context):
            raise ContractError("ACCESS_DENIED")
        if row["input_hash"] != context.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        return self.model.model_validate_json(row["payload"])

    def inventory(self, context: RequestContext) -> tuple[Record, ...]:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        rows = self.connection.execute(
            f"SELECT id FROM {self.table} WHERE session_id=? "  # nosec B608
            "AND run_id=? AND revision=? ORDER BY id",
            scope(context),
        ).fetchall()
        return tuple(self.get(context, UUID(row["id"])) for row in rows)

    def purge(self, context: RequestContext) -> None:
        self.guard()
        context.require("admin", context.session_id, context.analysis_run_id)
        self.connection.execute(
            f"DELETE FROM {self.table} "  # nosec B608
            "WHERE session_id=? AND run_id=? AND revision=?",
            scope(context),
        )


def factory(namespace: str) -> Callable[[sqlite3.Connection, Callable[[], None]], Repository]:
    def build(connection: sqlite3.Connection, guard: Callable[[], None]) -> Repository:
        return SQLiteTranscriptRepository(connection, guard, namespace)

    return build
