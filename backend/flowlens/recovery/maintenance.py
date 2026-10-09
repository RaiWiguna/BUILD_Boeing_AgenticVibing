"""Exclusive local owner lifecycle; no provider or B implementation is loaded."""

import os
import time
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from pathlib import Path
from typing import Self
from uuid import UUID, uuid4

from flowlens.assets.access import Assets
from flowlens.assets.storage import PrivateFiles
from flowlens.auth.accounts import Accounts
from flowlens.auth.permissions import Permissions
from flowlens.auth.sessions import Sessions
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import RequestContext
from flowlens.contracts.ports import UnitOfWork as TransactionPort
from flowlens.imports.commit import ImportCommit
from flowlens.imports.staging import Imports
from flowlens.replay.controls import Controls
from flowlens.replay.snapshots import Replay
from flowlens.retention.coordinator import Retention
from flowlens.retention.journal import Tombstones
from flowlens.sources.store import Sources
from flowlens.storage.sqlite.database import Database


class Paths(MetadataModel):
    database: Path
    raw: Path
    artifacts: Path
    imports: Path
    journal: Path

    def check_paths(self) -> None:
        values = [self.database, self.raw, self.artifacts, self.imports, self.journal]
        if any(p.is_symlink() or any(a.is_symlink() for a in p.parents) for p in values):
            raise ValueError("Private paths cannot use symlinks")
        roots = [p.absolute() for p in values[1:]]
        if any(
            a == b or a in b.parents or b in a.parents
            for i, a in enumerate(roots)
            for b in roots[i + 1 :]
        ):
            raise ValueError("Independent private roots required")
        if any(
            self.database.absolute() == r or r in self.database.absolute().parents for r in roots
        ):
            raise ValueError("Database must be outside asset/journal roots")
        if not self.database.is_file() or any(not r.is_dir() for r in roots):
            raise ValueError("Existing initialized private storage required")
        if not all((self.journal / name).is_file() for name in ("ledger.jsonl", "head.json")):
            raise ValueError("Current initialized deletion authority required")


class Maintenance:
    def __init__(
        self,
        paths: Paths,
        *,
        clock: Callable[[], int] | None = None,
        callbacks: Mapping[str, Callable[[RequestContext, TransactionPort], None]] | None = None,
    ) -> None:
        self.paths = paths
        self.callbacks = callbacks
        self.clock = clock if clock is not None else lambda: time.time_ns() // 1000000
        self.stack = ExitStack()
        self.open = False

    def __enter__(self) -> Self:
        self.paths.check_paths()
        try:
            self.database = self.stack.enter_context(Database(self.paths.database))
            self.raw = PrivateFiles(self.paths.raw)
            self.stack.callback(self.raw.close)
            self.artifacts = PrivateFiles(self.paths.artifacts)
            self.stack.callback(self.artifacts.close)
            self.journal = Tombstones(self.paths.journal)
            self.stack.callback(self.journal.close)
            self.sessions = Sessions(self.database, Accounts(self.database), clock=self.clock)
            self.permissions = Permissions(self.database, self.sessions)
            self.database.context_guard = self.permissions.enforce
            self.imports = Imports(self.database, self.sessions, self.paths.imports)
            self.stack.callback(self.imports.close)
            self.sources = Sources(self.database, self.permissions, self.raw)
            self.assets = Assets(self.sources, self.artifacts)
            self.retention = Retention(
                self.permissions,
                self.assets,
                self.journal,
                imports=self.imports,
                inventory_namespaces=("analysis",),
                callbacks=self.callbacks,
            )
            self.purged = self.retention.recover()
            ImportCommit(self.imports, self.raw)
            self.assets.recover_artifacts()
            self.controls = Controls(Replay(self.sources))
            self.controls.recover()
            self.open = True
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, kind: object, value: object, traceback: object) -> None:
        self.open = False
        self.stack.close()

    def check(self) -> dict[str, int]:
        if not self.open:
            raise RuntimeError("Offline owner is closed")
        self.journal.entries()
        with self.database.begin() as uow:
            if (
                uow.connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or uow.connection.execute("PRAGMA foreign_key_check").fetchall()
            ):
                raise ValueError("Database integrity failed")
            for row in uow.connection.execute("SELECT id FROM platform_sessions"):
                self.retention._inventory(uow, UUID(row[0]))
            return {
                name: uow.connection.execute(query).fetchone()[0]
                for name, query in {
                    "source_packages": "SELECT COUNT(*) FROM platform_source_packages",
                    "artifacts": "SELECT COUNT(*) FROM platform_artifacts",
                    "revisions": "SELECT COUNT(*) FROM platform_revisions",
                    "jobs": "SELECT COUNT(*) FROM platform_jobs",
                    "grants": "SELECT COUNT(*) FROM platform_grants",
                    "checkpoints": "SELECT COUNT(*) FROM platform_replay_snapshots",
                    "legacy_checkpoints": "SELECT COUNT(*) FROM platform_replay",
                }.items()
            }

    def audit(self, operation: str, backup_id: UUID, manifest_hash: str) -> None:
        if operation not in ("BACKUP_CREATED", "RESTORE_COMPLETED", "BACKUP_REMOVED"):
            raise ValueError("Bounded maintenance operation required")
        with self.database.begin() as uow:
            uow.connection.execute(
                "INSERT INTO platform_recovery_audit VALUES (?,?,?,?,?,?)",
                (str(uuid4()), operation, str(backup_id), manifest_hash, os.getuid(), self.clock()),
            )
            uow.commit()
