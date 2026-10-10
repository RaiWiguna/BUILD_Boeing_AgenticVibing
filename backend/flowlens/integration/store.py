"""Frozen DTO projection ledger owned by the API transaction, not workers."""

import sqlite3
from collections.abc import Callable
from uuid import UUID

from flowlens.contracts import models
from flowlens.contracts.models import Contract, RequestContext
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.repository import require_scope

TYPES = {
    name: getattr(models, name)
    for name in (
        "TranscriptSegment",
        "Intent",
        "Association",
        "MemoryEvent",
        "OpenLoop",
        "Finding",
        "Option",
        "Brief",
        "QueryAnswer",
        "Review",
    )
}


class PublicRepository:
    def __init__(self, connection: sqlite3.Connection, guard: Callable[[], None]) -> None:
        self.connection, self.guard = connection, guard

    def append(self, context: RequestContext, record: Contract) -> UUID:
        self.guard()
        context.require("analysis", context.session_id, context.analysis_run_id)
        require_scope(context, record)
        name = type(record).__name__
        if name not in TYPES:
            raise ContractError("INVALID_AI_OUTPUT")
        identifier = getattr(record, "id", None)
        if not isinstance(identifier, UUID):
            raise ContractError("INVALID_AI_OUTPUT")
        self.connection.execute(
            "INSERT INTO analysis_public_records VALUES (?,?,?,?,?,?)",
            (
                str(identifier),
                str(context.session_id),
                str(context.analysis_run_id),
                context.input_revision,
                name,
                record.model_dump_json(),
            ),
        )
        return identifier

    def get(self, context: RequestContext, record_id: UUID) -> Contract:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        row = self.connection.execute(
            "SELECT * FROM analysis_public_records WHERE id=?", (str(record_id),)
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        record: Contract = TYPES[row["kind"]].model_validate_json(row["payload"])
        require_scope(context, record)
        return record

    def inventory(self, context: RequestContext) -> tuple[Contract, ...]:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        rows = self.connection.execute(
            "SELECT id FROM analysis_public_records WHERE session_id=? "
            "AND run_id=? AND revision=? ORDER BY id",
            (str(context.session_id), str(context.analysis_run_id), context.input_revision),
        )
        return tuple(self.get(context, UUID(r[0])) for r in rows.fetchall())

    def purge(self, context: RequestContext) -> None:
        self.guard()
        context.require("admin", context.session_id, context.analysis_run_id)
        self.connection.execute(
            "DELETE FROM analysis_public_records WHERE session_id=? AND run_id=? AND revision=?",
            (str(context.session_id), str(context.analysis_run_id), context.input_revision),
        )
