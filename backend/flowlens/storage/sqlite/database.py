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
from typing import Self
from uuid import UUID

from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import Repository
from flowlens.core.modules import MigrationSpec
from flowlens.storage.sqlite.migrate import migrate
from flowlens.storage.sqlite.repository import KINDS, PlatformRepository, require_scope
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

RepositoryFactory = Callable[[sqlite3.Connection, Callable[[], None]], Repository]


class UnitOfWork:
    def __init__(
        self, connection: sqlite3.Connection, repositories: Mapping[str, RepositoryFactory]
    ) -> None:
        self.connection = connection
        self.repositories = repositories
        self.callbacks: list[Callable[[], None]] = []
        self.closed = False
        self.committed = False

    def check_open(self) -> None:
        if self.closed:
            raise RuntimeError("Unit-of-work is closed.")

    def repository(self, namespace: str) -> Repository:
        self.check_open()
        if namespace in self.repositories:
            return self.repositories[namespace](self.connection, self.check_open)
        return PlatformRepository(self.connection, namespace, self.check_open)

    def enqueue_event(self, context: RequestContext, payload: Contract) -> int:
        self.check_open()
        context.require("analysis", context.session_id, context.analysis_run_id)
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
        self.check_open()
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
        self.callbacks.append(callback)

    def commit(self) -> None:
        self.check_open()
        self.connection.commit()
        self.committed = True
        self.closed = True

    def rollback(self) -> None:
        if not self.committed:
            self.connection.rollback()
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
        self.repositories = dict(repositories or {})
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
                        uow = UnitOfWork(connection, self.repositories)
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
