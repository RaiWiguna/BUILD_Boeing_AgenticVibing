"""API-owned aggregate mutation coordination, independent of domain/B implementations."""

import hashlib
import json
import re
import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal
from uuid import UUID, uuid4

from flowlens.contracts.models import Contract, RequestContext, Scoped
from flowlens.contracts.ports import UnitOfWork as TransactionPort
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import Database, UnitOfWork
from flowlens.storage.sqlite.repository import require_scope
from pydantic import ValidationError


@dataclass(frozen=True)
class MutationOperation:
    name: str
    namespace: str
    repository_namespace: str
    capability: Literal["review", "analysis"]
    payload_type: type[Contract]
    apply: Callable[[RequestContext, Contract, TransactionPort], Contract]
    version: str = "1"

    def __post_init__(self) -> None:
        if (
            not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.name)
            or not re.fullmatch(r"[a-z][a-z0-9_.]{0,63}", self.namespace)
            or not re.fullmatch(r"[a-z][a-z0-9_.]{0,63}", self.repository_namespace)
            or self.capability not in ("review", "analysis")
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", self.version)
            or not issubclass(self.payload_type, Contract)
            or not callable(self.apply)
        ):
            raise ValueError("Invalid trusted mutation registration.")


@dataclass(frozen=True)
class MutationReceipt:
    id: UUID
    session_id: UUID
    analysis_run_id: UUID | None
    revision: int
    target_id: UUID
    version: int
    sequence: int
    record_id: UUID


def receipt(row: sqlite3.Row) -> MutationReceipt:
    return MutationReceipt(
        id=UUID(row["id"]),
        session_id=UUID(row["session_id"]),
        analysis_run_id=UUID(row["run_id"]) if row["run_id"] else None,
        revision=row["revision"],
        target_id=UUID(row["target_id"]),
        version=row["version"],
        sequence=row["sequence"],
        record_id=UUID(row["record_id"]),
    )


class Mutations:
    def __init__(self, database: Database, *, operations: Sequence[MutationOperation] = ()) -> None:
        self.database = database
        entries = {spec.name: spec for spec in operations}
        if len(entries) != len(operations):
            raise ValueError("Duplicate mutation registration.")
        self.operations = MappingProxyType(entries)

    def _operation(self, name: str) -> MutationOperation:
        if type(name) is not str or name not in self.operations:
            raise ContractError("INVALID_INPUT")
        return self.operations[name]

    def _authorize(self, uow: UnitOfWork, context: RequestContext) -> None:
        if uow.context_guard is None:
            raise ContractError("ACCESS_DENIED")
        uow.authorize(context)
        if "worker" in context.capabilities:
            raise ContractError("ACCESS_DENIED")

    def version(self, context: RequestContext, operation: str, target_id: UUID) -> int:
        spec = self._operation(operation)
        if type(target_id) is not UUID:
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            self._authorize(uow, context)
            context.require("read", context.session_id, context.analysis_run_id)
            return self._version(uow, context, spec, target_id)

    def _version(
        self,
        uow: UnitOfWork,
        context: RequestContext,
        spec: MutationOperation,
        target: UUID,
    ) -> int:
        row = uow.connection.execute(
            "SELECT version FROM platform_mutation_versions "
            "WHERE session_id=? AND run_scope=? AND namespace=? AND target_id=?",
            (
                str(context.session_id),
                str(context.analysis_run_id or ""),
                spec.namespace,
                str(target),
            ),
        ).fetchone()
        return row["version"] if row else 0

    def execute(
        self,
        context: RequestContext,
        operation: str,
        *,
        target_id: UUID,
        key: str,
        expected_version: int,
        payload: Contract,
        publish: Callable[[MutationReceipt], None] | None = None,
    ) -> MutationReceipt:
        spec = self._operation(operation)
        if (
            type(target_id) is not UUID
            or type(key) is not str
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key)
            or type(expected_version) is not int
            or not 0 <= expected_version < 2**63 - 1
            or type(payload) is not spec.payload_type
        ):
            raise ContractError("INVALID_INPUT")
        try:
            validated = spec.payload_type.model_validate_json(payload.model_dump_json())
            normalized = json.dumps(
                [
                    operation,
                    spec.namespace,
                    spec.version,
                    spec.capability,
                    f"{spec.payload_type.__module__}.{spec.payload_type.__qualname__}",
                    str(target_id),
                    spec.repository_namespace,
                    context.input_revision,
                    context.input_hash,
                    expected_version,
                    json.loads(validated.model_dump_json()),
                ],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (ValidationError, ValueError, TypeError):
            raise ContractError("INVALID_INPUT") from None
        request_hash = hashlib.sha256(normalized.encode()).hexdigest()
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        run_scope = str(context.analysis_run_id or "")
        identity = (
            str(context.session_id),
            run_scope,
            str(context.actor_id),
            operation,
            str(target_id),
            key_hash,
        )
        with self.database.begin() as uow:
            self._authorize(uow, context)
            context.require(spec.capability, context.session_id, context.analysis_run_id)
            if isinstance(validated, Scoped):
                require_scope(context, validated)
            previous = uow.connection.execute(
                "SELECT * FROM platform_mutation_receipts WHERE session_id=? AND run_scope=? "
                "AND actor_id=? AND operation=? AND target_id=? AND key_hash=?",
                identity,
            ).fetchone()
            if previous is not None:
                if previous["request_hash"] != request_hash:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return receipt(previous)
            if self._version(uow, context, spec, target_id) != expected_version:
                raise ContractError("VERSION_CONFLICT")
            with uow.domain_writes():
                accepted = spec.apply(context, validated, uow)
            if not isinstance(accepted, Scoped) or not isinstance(
                getattr(accepted, "id", None), UUID
            ):
                raise ContractError("INVALID_INPUT")
            require_scope(context, accepted)
            try:
                accepted = type(accepted).model_validate_json(accepted.model_dump_json())
            except (ValidationError, ValueError, TypeError):
                raise ContractError("INVALID_INPUT") from None
            record_id = getattr(accepted, "id", None)
            if not isinstance(record_id, UUID):
                raise ContractError("INVALID_INPUT")
            persisted = uow.repository(spec.repository_namespace).get(context, record_id)
            if type(persisted) is not type(accepted) or persisted != accepted:
                raise ContractError("INVALID_INPUT")
            next_version = expected_version + 1
            if expected_version == 0:
                uow.connection.execute(
                    "INSERT INTO platform_mutation_versions VALUES (?,?,?,?,?,1)",
                    (
                        str(context.session_id),
                        run_scope,
                        str(context.analysis_run_id) if context.analysis_run_id else None,
                        spec.namespace,
                        str(target_id),
                    ),
                )
            else:
                changed = uow.connection.execute(
                    "UPDATE platform_mutation_versions SET version=? "
                    "WHERE session_id=? AND run_scope=? AND namespace=? AND target_id=? "
                    "AND version=?",
                    (
                        next_version,
                        str(context.session_id),
                        run_scope,
                        spec.namespace,
                        str(target_id),
                        expected_version,
                    ),
                )
                if changed.rowcount != 1:
                    raise ContractError("VERSION_CONFLICT")
            sequence = uow.enqueue_event(context, accepted)
            uow.audit(context, spec.name, target_id)
            audit_id = uow.connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            result = MutationReceipt(
                uuid4(),
                context.session_id,
                context.analysis_run_id,
                context.input_revision,
                target_id,
                next_version,
                sequence,
                record_id,
            )
            uow.connection.execute(
                "INSERT INTO platform_mutation_receipts "
                "(id,session_id,run_scope,run_id,revision,actor_id,operation,namespace,target_id,"
                "key_hash,request_hash,version,sequence,record_id,audit_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(result.id),
                    str(context.session_id),
                    run_scope,
                    str(context.analysis_run_id) if context.analysis_run_id else None,
                    context.input_revision,
                    str(context.actor_id),
                    operation,
                    spec.namespace,
                    str(target_id),
                    key_hash,
                    request_hash,
                    next_version,
                    sequence,
                    str(result.record_id),
                    audit_id,
                ),
            )
            if publish is not None:
                uow.after_commit(lambda: publish(result))
            uow.commit()
        return result
