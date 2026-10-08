"""Scoped append-only platform repositories; no automatic session/run creation."""

import sqlite3
from collections.abc import Callable
from uuid import UUID

from flowlens.contracts.models import Contract, Evidence, RequestContext, SourceEvent, Track
from flowlens.core.errors import ContractError

KINDS: dict[str, tuple[type[Contract], ...]] = {
    "source_events": (SourceEvent, Track),
    "evidence": (Evidence,),
}

QUERIES = {
    "source_events": (
        "INSERT INTO platform_records"
        "(namespace,id,session_id,run_id,revision,kind,payload) VALUES (?,?,?,?,?,?,?)",
        "SELECT * FROM platform_records WHERE namespace=? AND id=?",
    ),
    "evidence": (
        "INSERT INTO platform_evidence"
        "(namespace,id,session_id,run_id,revision,kind,payload,source_id) VALUES (?,?,?,?,?,?,?,?)",
        "SELECT * FROM platform_evidence WHERE namespace=? AND id=?",
    ),
}


def require_scope(context: RequestContext, record: Contract) -> None:
    if (
        getattr(record, "session_id", None),
        getattr(record, "analysis_run_id", None),
        getattr(record, "revision", None),
    ) != (context.session_id, context.analysis_run_id, context.input_revision):
        raise ContractError("ACCESS_DENIED")


class PlatformRepository:
    def __init__(
        self, connection: sqlite3.Connection, namespace: str, guard: Callable[[], None]
    ) -> None:
        if namespace not in KINDS:
            raise ValueError("Unknown platform repository namespace.")
        self.connection = connection
        self.namespace = namespace
        self.guard = guard

    def append(self, context: RequestContext, record: Contract) -> UUID:
        self.guard()
        context.require("analysis", context.session_id, context.analysis_run_id)
        require_scope(context, record)
        identifier = getattr(record, "id", None)
        if type(record) not in KINDS[self.namespace] or not isinstance(identifier, UUID):
            raise ContractError("INVALID_INPUT")
        values: tuple[object, ...] = (
            self.namespace,
            str(identifier),
            str(context.session_id),
            str(context.analysis_run_id) if context.analysis_run_id else None,
            context.input_revision,
            type(record).__name__,
            record.model_dump_json(),
        )
        if isinstance(record, Evidence):
            values += (str(record.source_id),)
        try:
            self.connection.execute(QUERIES[self.namespace][0], values)
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode in (
                sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
                sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            ):
                raise ContractError("VERSION_CONFLICT") from None
            raise
        return identifier

    def get(self, context: RequestContext, record_id: UUID) -> Contract:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        row = self.connection.execute(
            QUERIES[self.namespace][1],
            (self.namespace, str(record_id)),
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (row["session_id"], row["run_id"], row["revision"]) != (
            str(context.session_id),
            str(context.analysis_run_id) if context.analysis_run_id else None,
            context.input_revision,
        ):
            raise ContractError("ACCESS_DENIED")
        kinds = {kind.__name__: kind for kind in KINDS[self.namespace]}
        return kinds[row["kind"]].model_validate_json(row["payload"])
