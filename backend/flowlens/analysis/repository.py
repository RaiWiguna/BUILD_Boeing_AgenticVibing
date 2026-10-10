"""Connection-injected repository; never opens or owns a transaction."""

import sqlite3
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from flowlens.analysis.config import ConfigurationRecord
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import Repository
from flowlens.core.errors import ContractError

NAMESPACE = "analysis.configuration"


def scope(context: RequestContext) -> tuple[str, str, int]:
    if context.analysis_run_id is None:
        raise ContractError("INVALID_INPUT")
    return str(context.session_id), str(context.analysis_run_id), context.input_revision


class ConfigurationRepository(Repository, Protocol):
    def inventory(self, context: RequestContext) -> list[ConfigurationRecord]: ...
    def purge(self, context: RequestContext) -> None: ...


class SQLiteConfigurationRepository:
    def __init__(self, connection: sqlite3.Connection, guard: Callable[[], None]) -> None:
        self.connection = connection
        self.guard = guard

    def append(self, context: RequestContext, record: Contract) -> UUID:
        self.guard()
        context.require("analysis", context.session_id, context.analysis_run_id)
        binding = scope(context)
        if not isinstance(record, ConfigurationRecord):
            raise ContractError("INVALID_INPUT")
        if (str(record.session_id), str(record.analysis_run_id), record.revision) != binding:
            raise ContractError("ACCESS_DENIED")
        parent = self.connection.execute(
            "SELECT input_hash FROM platform_revisions WHERE session_id=? AND revision=?",
            (binding[0], binding[2]),
        ).fetchone()
        if (
            record.input_hash != context.input_hash
            or parent is None
            or parent["input_hash"] != context.input_hash
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        # Revalidate even if an internal caller used Pydantic model_copy without validation.
        record = ConfigurationRecord.model_validate_json(record.model_dump_json())
        try:
            self.connection.execute(
                "INSERT INTO analysis_configurations VALUES (?,?,?,?,?,?,?)",
                (
                    str(record.id),
                    *binding,
                    record.input_hash,
                    record.config_hash,
                    record.model_dump_json(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode in (
                sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
                sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            ):
                raise ContractError("VERSION_CONFLICT") from None
            raise
        return record.id

    def get(self, context: RequestContext, record_id: UUID) -> ConfigurationRecord:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        row = self.connection.execute(
            "SELECT * FROM analysis_configurations WHERE id=?", (str(record_id),)
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (row["session_id"], row["run_id"], row["revision"]) != scope(context):
            raise ContractError("ACCESS_DENIED")
        if row["input_hash"] != context.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        return ConfigurationRecord.model_validate_json(row["payload"])

    def inventory(self, context: RequestContext) -> list[ConfigurationRecord]:
        self.guard()
        context.require("read", context.session_id, context.analysis_run_id)
        rows = self.connection.execute(
            "SELECT id FROM analysis_configurations WHERE session_id=? AND run_id=? AND revision=?"
            " ORDER BY id",
            scope(context),
        ).fetchall()
        return [self.get(context, UUID(row["id"])) for row in rows]

    def purge(self, context: RequestContext) -> None:
        self.guard()
        context.require("admin", context.session_id, context.analysis_run_id)
        self.connection.execute(
            "DELETE FROM analysis_configurations WHERE session_id=? AND run_id=? AND revision=?",
            scope(context),
        )
