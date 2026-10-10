"""Local single-owner SQLite runtime and API-owned unit-of-work infrastructure."""

import fcntl
import os
import re
import sqlite3
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Protocol, Self, cast
from uuid import UUID

from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import Repository
from flowlens.core.errors import ContractError
from flowlens.core.modules import MigrationSpec
from flowlens.storage.sqlite.migrate import migrate
from flowlens.storage.sqlite.repository import KINDS, PlatformRepository, require_scope
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

RepositoryFactory = Callable[[sqlite3.Connection, Callable[[], None]], Repository]


class ScopedInventory(Protocol):
    def inventory(self, context: RequestContext) -> Sequence[Contract]: ...
    def purge(self, context: RequestContext) -> None: ...


class AuthorizedRepository:
    def __init__(self, delegate: Repository, guard: Callable[[RequestContext], None]) -> None:
        self.delegate = delegate
        self.guard = guard

    def append(self, context: RequestContext, record: Contract) -> UUID:
        self.guard(context)
        return self.delegate.append(context, record)

    def get(self, context: RequestContext, record_id: UUID) -> Contract:
        self.guard(context)
        return self.delegate.get(context, record_id)

    def inventory(self, context: RequestContext) -> Sequence[Contract]:
        self.guard(context)
        return cast(ScopedInventory, self.delegate).inventory(context)

    def purge(self, context: RequestContext) -> None:
        self.guard(context)
        cast(ScopedInventory, self.delegate).purge(context)


class UnitOfWork:
    def __init__(
        self,
        connection: sqlite3.Connection,
        repositories: Mapping[str, RepositoryFactory],
        context_guard: Callable[["UnitOfWork", RequestContext], None] | None = None,
    ) -> None:
        self.connection = connection
        self.repositories = repositories
        self.context_guard = context_guard
        self.callbacks: list[Callable[[], None]] = []
        self.closed = False
        self.committed = False
        self.domain_active = False
        self.poisoned = False
        self.owner_transaction = False
        self.retention_context: RequestContext | None = None
        connection.set_authorizer(self.runtime_authorize)

    def runtime_authorize(
        self,
        action: int,
        arg1: str | None,
        arg2: str | None,
        database: str | None,
        trigger: str | None,
    ) -> int:
        if self.retention_context is not None and not self.domain_active:
            if (
                action == sqlite3.SQLITE_DROP_TRIGGER
                or (action == sqlite3.SQLITE_PRAGMA and arg1 == "defer_foreign_keys")
                or (
                    action == sqlite3.SQLITE_DELETE
                    and arg1 in ("platform_audit", "platform_mutation_receipts")
                )
            ):
                return sqlite3.SQLITE_OK
        immutable = {
            "platform_audit",
            "platform_account_audit",
            "platform_permission_audit",
            "platform_mutation_receipts",
            "platform_schema_migrations",
        }
        denied = (
            (
                action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT)
                and not self.owner_transaction
            )
            or (action in (sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE) and arg1 in immutable)
            or (
                action in (sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE)
                and bool(immutable.intersection((arg1, arg2)))
            )
            or (
                action == sqlite3.SQLITE_DROP_TRIGGER
                and (arg1 or "").startswith("platform_append_only_")
            )
            or action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH)
            or (
                action == sqlite3.SQLITE_PRAGMA
                and arg2 is not None
                and arg1
                not in {
                    "table_info",
                    "table_xinfo",
                    "foreign_key_list",
                    "index_list",
                    "index_info",
                    "index_xinfo",
                    "foreign_key_check",
                    "integrity_check",
                    "quick_check",
                }
            )
        )
        if denied:
            if self.domain_active or action in (
                sqlite3.SQLITE_TRANSACTION,
                sqlite3.SQLITE_SAVEPOINT,
            ):
                self.poisoned = True
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    @contextmanager
    def retention_writes(self, context: RequestContext) -> Iterator[None]:
        """Coordinator-only erasure context; callbacks cannot enter or acquire commit authority."""
        self.check_open()
        if self.domain_active or self.retention_context is not None:
            self.poisoned = True
            raise RuntimeError("Nested retention authority denied")
        context.require("admin", context.session_id)
        self.retention_context = context
        try:
            yield
        finally:
            self.retention_context = None

    @contextmanager
    def domain_writes(self) -> Iterator[None]:
        """Domain callbacks use frozen UOW ports but never own commit/rollback."""
        self.check_open()
        if self.domain_active:
            raise RuntimeError("Nested mutation callback unsupported.")
        self.domain_active = True
        try:
            yield
        finally:
            self.domain_active = False

    def check_open(self) -> None:
        if self.closed:
            raise RuntimeError("Unit-of-work is closed.")

    def authorize(self, context: RequestContext) -> None:
        self.check_open()
        if self.context_guard is not None:
            self.context_guard(self, context)

    def repository(self, namespace: str) -> Repository:
        self.check_open()
        delegate = (
            self.repositories[namespace](self.connection, self.check_open)
            if namespace in self.repositories
            else PlatformRepository(self.connection, namespace, self.check_open)
        )
        return AuthorizedRepository(delegate, self.authorize)

    def enqueue_event(self, context: RequestContext, payload: Contract) -> int:
        self.authorize(context)
        if not {"analysis", "review"}.intersection(context.capabilities):
            raise ContractError("ACCESS_DENIED")
        context.require("read", context.session_id, context.analysis_run_id)
        require_scope(context, payload)
        sequence = int(
            self.connection.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM platform_events WHERE session_id=?",
                (str(context.session_id),),
            ).fetchone()[0]
        )
        self.connection.execute(
            "INSERT INTO platform_events VALUES (?,?,?,?,?)",
            (
                str(context.session_id),
                sequence,
                str(context.analysis_run_id) if context.analysis_run_id else None,
                context.input_revision,
                payload.model_dump_json(),
            ),
        )
        return sequence

    def audit(self, context: RequestContext, action: str, target_id: UUID) -> None:
        self.authorize(context)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", action):
            raise ValueError("Audit action must be a bounded identifier.")
        self.connection.execute(
            "INSERT INTO platform_audit"
            "(session_id,actor_id,request_id,action,target_id,recorded_at) VALUES (?,?,?,?,?,?)",
            (
                str(context.session_id),
                str(context.actor_id),
                str(context.request_id),
                action,
                str(target_id),
                datetime.now(UTC).isoformat(),
            ),
        )

    def after_commit(self, callback: Callable[[], None]) -> None:
        self.check_open()
        if self.retention_context is not None and self.domain_active:
            self.poisoned = True
            raise RuntimeError("Purge callbacks cannot defer unscoped writes")
        self.callbacks.append(callback)

    def commit(self) -> None:
        self.check_open()
        if self.domain_active:
            self.poisoned = True
            raise RuntimeError("Only the coordinator may commit a mutation.")
        if self.poisoned:
            raise RuntimeError("Transaction is rollback-only.")
        self.owner_transaction = True
        try:
            self.connection.commit()
        finally:
            self.owner_transaction = False
        self.committed = True
        self.closed = True

    def rollback(self) -> None:
        if self.domain_active:
            self.poisoned = True
            raise RuntimeError("Only the coordinator may rollback a mutation.")
        if not self.committed:
            self.owner_transaction = True
            try:
                self.connection.rollback()
            finally:
                self.owner_transaction = False
            self.callbacks.clear()
        self.closed = True


class Database:
    def __init__(
        self,
        path: Path,
        *,
        migrations: Sequence[MigrationSpec] = PLATFORM_MIGRATIONS,
        repositories: Mapping[str, RepositoryFactory] | None = None,
    ) -> None:
        if path.is_symlink():
            raise ValueError("Database symlinks are not supported.")
        self.path = path.absolute()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.path.parent.resolve() / self.path.name
        self.mutex = RLock()
        self.closed = False
        self.active = False
        self.context_guard: Callable[[UnitOfWork, RequestContext], None] | None = None
        self.repositories = dict(repositories or {})
        self.specs = tuple(migrations)
        if any(
            namespace in KINDS or not (namespace == "analysis" or namespace.startswith("analysis."))
            for namespace in self.repositories
        ):
            raise ValueError("Repository extensions must use the analysis namespace.")
        self.owner = os.open(
            self.path.with_name(self.path.name + ".owner.lock"),
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
        try:
            try:
                fcntl.flock(self.owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("Database already has an API owner.") from None
            descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            os.close(descriptor)
            if self.path.stat().st_mode & 0o077:
                raise ValueError("Database requires private filesystem permissions.")
            with self._connect() as connection:
                migrate(connection, migrations)
                connection.execute("PRAGMA journal_mode=WAL")
        except BaseException:
            os.close(self.owner)
            self.closed = True
            raise

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=5)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("PRAGMA recursive_triggers=ON")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def begin(self) -> Iterator[UnitOfWork]:
        uow: UnitOfWork | None = None
        try:
            with self.mutex:
                if self.closed or self.active:
                    raise RuntimeError("Database closed or nested unit-of-work unsupported.")
                self.active = True
                try:
                    with self._connect() as connection:
                        connection.execute("BEGIN IMMEDIATE")
                        uow = UnitOfWork(connection, self.repositories, self.context_guard)
                        try:
                            yield uow
                        finally:
                            if not uow.committed:
                                uow.rollback()
                finally:
                    self.active = False
        finally:
            if uow is not None and uow.committed:
                failed = False
                for callback in uow.callbacks:
                    try:
                        callback()
                    except Exception:
                        failed = True
                if failed:
                    raise RuntimeError(
                        "Commit is durable; publication failed. Resync required."
                    ) from None

    def close(self) -> None:
        with self.mutex:
            if self.active:
                raise RuntimeError("Cannot close active database transaction.")
            if not self.closed:
                os.close(self.owner)
                self.closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
