"""Private immutable local bundles: SQLite backup API + referenced sealed bytes."""

import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field

from flowlens.assets.storage import PrivateFiles
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import AnalysisRun, RequestContext
from flowlens.contracts.ports import UnitOfWork as TransactionPort
from flowlens.core.host_config import HostSettings
from flowlens.imports.inspection import strict_json
from flowlens.imports.metadata import hashed
from flowlens.ops.health import Operations
from flowlens.ops.usage import invariant
from flowlens.recovery.candidates import release, reserve, sync_tree
from flowlens.recovery.catalog import Item, catalog
from flowlens.recovery.maintenance import Maintenance, Paths
from flowlens.retention.journal import Tombstones
from flowlens.storage.sqlite.migrate import checksum
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

IDENTIFIER = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
FILE_PATTERN = (
    rf"^(?:snapshot.sqlite|(?:raw|artifacts|imports)/{IDENTIFIER}/"
    rf"(?:inventory.json|{IDENTIFIER}\.(?:raw|upload)))$"
)
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class File(MetadataModel):
    path: Annotated[str, Field(pattern=FILE_PATTERN)]
    sha256: Hash
    size_bytes: Annotated[int, Field(ge=0)]
    session_id: UUID | None = None
    expires_ms: int | None = None


class Reference(MetadataModel):
    session_id: UUID
    expires_ms: int | None


class Manifest(MetadataModel):
    version: str = "local-backup-1"
    id: UUID
    created_ms: int
    files: list[File]
    sessions: list[Reference]
    migration_checksums: dict[str, str]
    release: dict[str, object]
    current_journal_digest: Hash
    removal_due_ms: int | None
    storage: str = "LOCAL_PRIVATE_UNENCRYPTED"


class Receipt(MetadataModel):
    id: UUID
    manifest_hash: Hash
    files: int
    sessions: int
    removal_due_ms: int | None
    status: str = "BACKUP_CREATED"


class Restored(MetadataModel):
    id: UUID
    manifest_hash: Hash
    status: str = "RESTORED_ISOLATED"
    purged_sessions: list[UUID]
    paths: Paths
    credentials_invalidated: bool = True
    pending_jobs_cancelled: bool = True


def _safe_path(path: Path) -> Path:
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlink paths unsupported")
    return path


def _parent(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        PrivateFiles.private(fd, directory=True)
    finally:
        os.close(fd)
    if target.exists():
        raise ValueError("A new isolated destination is required")


def _fsync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _read(root: Path, relative: str) -> Iterator[int]:
    if re.fullmatch(FILE_PATTERN, relative) is None:
        raise ValueError("Code-owned snapshot path required")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = -1
    try:
        PrivateFiles.private(directory, directory=True)
        parts = relative.split("/")
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
            PrivateFiles.private(directory, directory=True)
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        PrivateFiles.private(fd)
        yield fd
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(directory)


def _digest(fd: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    os.lseek(fd, 0, os.SEEK_SET)
    while block := os.read(fd, 65536):
        size += len(block)
        digest.update(block)
    os.lseek(fd, 0, os.SEEK_SET)
    return digest.hexdigest(), size


def _copy(fd: int, path: Path, *, expected: File | None = None) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    out = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    digest = hashlib.sha256()
    size = 0
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        while block := os.read(fd, 65536):
            data = memoryview(block)
            while data:
                written = os.write(out, data)
                if written <= 0:
                    raise OSError("Snapshot write unavailable")
                data = data[written:]
            digest.update(block)
            size += len(block)
        if expected and (digest.hexdigest(), size) != (expected.sha256, expected.size_bytes):
            raise ValueError("Snapshot file hash/size mismatch")
        os.fchmod(out, 0o400)
        os.fsync(out)
    finally:
        os.close(out)
    _fsync(path.parent)
    return digest.hexdigest(), size


def _write(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        os.fchmod(fd, 0o400)
    finally:
        os.close(fd)
    _fsync(path.parent)


def _connection(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


class Snapshots:
    def __init__(self, maintenance: Maintenance) -> None:
        if not maintenance.open:
            raise RuntimeError("Exclusive offline owner required")
        self.m = maintenance
        self.fault: Callable[[str], None] = lambda phase: None

    def create(self, target: Path) -> Receipt:
        target = _safe_path(target)
        roots = [
            self.m.paths.raw,
            self.m.paths.artifacts,
            self.m.paths.imports,
            self.m.paths.journal,
        ]
        if (
            any(target == r or target in r.parents or r in target.parents for r in roots)
            or target == self.m.paths.database
        ):
            raise ValueError("Snapshot must be outside source roots")
        _parent(target)
        stage = target.parent / f".snapshot-{uuid4()}.tmp"
        lease_descriptor = reserve(stage)
        published = False
        try:
            stage.mkdir(mode=0o700)
            for group in ("raw", "artifacts", "imports"):
                (stage / group).mkdir(mode=0o700)
            with self.m.database.mutex:
                self.m.check()
                marker_digest = hashed(
                    [e.model_dump(mode="json") for e in self.m.journal.entries()]
                )
                with self.m.database._connect() as source:
                    dest = stage / "snapshot.sqlite"
                    descriptor = os.open(
                        dest, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600
                    )
                    os.close(descriptor)
                    snapshot_connection = sqlite3.connect(dest)
                    try:
                        source.backup(snapshot_connection, pages=256)
                        snapshot_connection.execute("PRAGMA journal_mode=DELETE")
                    finally:
                        snapshot_connection.close()
                    _fsync(dest)
                    os.chmod(dest, 0o400)
                self.fault("after_database")
                database = _connection(dest)
                try:
                    now = self.m.clock()
                    items = catalog(database, now)
                    for row in database.execute("SELECT * FROM platform_source_packages"):
                        from flowlens.imports.metadata import PreparedImport

                        p = PreparedImport.model_validate_json(row["payload"])
                        self.m.raw.verify(UUID(row["package_id"]), p.manifest_hash, p.files)
                    files = []
                    with _read(stage, "snapshot.sqlite") as fd:
                        sha, size = _digest(fd)
                        files.append(File(path="snapshot.sqlite", sha256=sha, size_bytes=size))
                    schema = dict(
                        database.execute("SELECT id,checksum FROM platform_schema_migrations")
                    )
                    sessions = [
                        Reference(session_id=UUID(r[0]), expires_ms=r[1])
                        for r in database.execute(
                            "SELECT r.session_id,MIN(p.expires_ms) FROM "
                            "platform_revisions r LEFT JOIN "
                            "platform_source_packages p ON "
                            "p.session_id=r.session_id GROUP BY r.session_id ORDER BY r.session_id"
                        )
                    ]
                finally:
                    database.close()
                # Copy roots through the same descriptor checks, but with code-owned group prefix.
                for item in items:
                    root = getattr(self.m.paths, item.group)
                    with _item_fd(root, item) as fd:
                        expected = (
                            File(
                                path=item.path,
                                sha256=item.file.sha256,
                                size_bytes=item.file.size_bytes,
                            )
                            if item.file
                            else None
                        )
                        sha, size = _copy(fd, stage / item.path, expected=expected)
                    files.append(
                        File(
                            path=item.path,
                            sha256=sha,
                            size_bytes=size,
                            session_id=item.session_id,
                            expires_ms=item.expires_ms,
                        )
                    )
                self.fault("after_assets")
                due = min((f.expires_ms for f in files if f.expires_ms is not None), default=None)
                if (due is not None and due <= self.m.clock()) or marker_digest != hashed(
                    [e.model_dump(mode="json") for e in self.m.journal.entries()]
                ):
                    raise ValueError("Retention changed before snapshot publication")
                manifest = Manifest(
                    id=uuid4(),
                    created_ms=now,
                    files=files,
                    sessions=sessions,
                    migration_checksums=schema,
                    release=Operations(
                        None,
                        HostSettings(profile="test"),
                        self.m.database.specs,
                        profile="OFFLINE_MAINTENANCE",
                    ).release(),
                    current_journal_digest=marker_digest,
                    removal_due_ms=due,
                )
                manifest_hash = hashed(manifest.model_dump(mode="json"))
                envelope = {
                    "manifest": manifest.model_dump(mode="json"),
                    "manifest_hash": manifest_hash,
                }
                encoded = json.dumps(envelope, sort_keys=True).encode()
                if len(encoded) > 8 * 1024**2:
                    raise ValueError("Snapshot manifest exceeds limit")
                _write(stage / "manifest.json", encoded)
                sync_tree(stage)
                self.fault("before_publish")
                _publish(stage, target)
                published = True
            status = "BACKUP_CREATED"
            try:
                self.m.audit("BACKUP_CREATED", manifest.id, manifest_hash)
            except Exception:
                # The bundle is already durable; do not claim rollback or delete a valid backup.
                status = "BACKUP_DURABLE_AUDIT_PENDING"
            return Receipt(
                id=manifest.id,
                manifest_hash=manifest_hash,
                files=len(files),
                sessions=len(sessions),
                removal_due_ms=due,
                status=status,
            )
        finally:
            try:
                if not published and stage.exists():
                    shutil.rmtree(stage)
            finally:
                release(stage, lease_descriptor)

    @staticmethod
    def _manifest(root: Path, expected_manifest_hash: str) -> Manifest:
        root = _safe_path(root)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            PrivateFiles.private(directory, directory=True)
            fd = os.open("manifest.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        finally:
            os.close(directory)
        try:
            PrivateFiles.private(fd)
            if os.fstat(fd).st_size > 8 * 1024**2:
                raise ValueError("Snapshot manifest exceeds limit")
            body = os.read(fd, 8 * 1024**2 + 1)
        finally:
            os.close(fd)
        data = strict_json(body.decode())
        if not isinstance(data, dict) or set(data) != {"manifest", "manifest_hash"}:
            raise ValueError("Invalid snapshot envelope")
        manifest = Manifest.model_validate_json(json.dumps(data["manifest"]))
        if (
            manifest.version != "local-backup-1"
            or manifest.storage != "LOCAL_PRIVATE_UNENCRYPTED"
            or hashed(manifest.model_dump(mode="json")) != data["manifest_hash"]
            or data["manifest_hash"] != expected_manifest_hash
        ):
            raise ValueError("Selected snapshot hash mismatch")
        if (
            len({f.path for f in manifest.files}) != len(manifest.files)
            or sum(f.path == "snapshot.sqlite" for f in manifest.files) != 1
        ):
            raise ValueError("Snapshot inventory mismatch")
        from flowlens.core.modules import order_migrations
        from flowlens.integration.catalog import JOINT_MIGRATIONS

        definitions = (
            order_migrations(list(JOINT_MIGRATIONS))
            if any(k.startswith("analysis.") for k in manifest.migration_checksums)
            else list(PLATFORM_MIGRATIONS)
        )
        supported = {s.id: checksum(s) for s in definitions}
        prefix = {s.id for s in definitions[: len(manifest.migration_checksums)]}
        if (
            set(manifest.migration_checksums) != prefix
            or len(prefix) < 16
            or any(supported.get(k) != v for k, v in manifest.migration_checksums.items())
        ):
            raise ValueError("Unsupported snapshot schema")
        return manifest

    @staticmethod
    def verify(root: Path, expected_manifest_hash: str) -> Manifest:
        root = _safe_path(root)
        manifest = Snapshots._manifest(root, expected_manifest_hash)
        expected_names = {f.path for f in manifest.files} | {"manifest.json"}
        if _tree(root) != expected_names:
            raise ValueError("Unexpected snapshot entries")
        for f in manifest.files:
            with _read(root, f.path) as fd:
                if _digest(fd) != (f.sha256, f.size_bytes):
                    raise ValueError("Snapshot bytes mismatch")
        db = _connection(root / "snapshot.sqlite")
        try:
            if (
                dict(db.execute("SELECT id,checksum FROM platform_schema_migrations"))
                != manifest.migration_checksums
                or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or db.execute("PRAGMA foreign_key_check").fetchall()
            ):
                raise ValueError("Snapshot database integrity mismatch")
            items = catalog(db, manifest.created_ms)
            expected = {i.path for i in items} | {"snapshot.sqlite"}
            declared = {f.path: f for f in manifest.files}
            if expected != set(declared):
                raise ValueError("Snapshot references mismatch")
            for item in items:
                value = declared[item.path]
                if (value.session_id, value.expires_ms) != (item.session_id, item.expires_ms):
                    raise ValueError("Snapshot retention/reference mismatch")
                if item.file and (value.sha256, value.size_bytes) != (
                    item.file.sha256,
                    item.file.size_bytes,
                ):
                    raise ValueError("Snapshot asset facts mismatch")
            references = [
                Reference(session_id=UUID(r[0]), expires_ms=r[1])
                for r in db.execute(
                    "SELECT r.session_id,MIN(p.expires_ms) FROM platform_revisions r LEFT JOIN "
                    "platform_source_packages p ON p.session_id=r.session_id "
                    "GROUP BY r.session_id ORDER BY r.session_id"
                )
            ]
            due = min(
                (f.expires_ms for f in manifest.files if f.expires_ms is not None), default=None
            )
            if references != manifest.sessions or due != manifest.removal_due_ms:
                raise ValueError("Snapshot removal schedule mismatch")
        finally:
            db.close()
        return manifest

    @staticmethod
    def prune(
        root: Path,
        *,
        journal_path: Path,
        expected_manifest_hash: str,
        clock: Callable[[], int] | None = None,
    ) -> str:
        root = _safe_path(root)
        if re.fullmatch(r"[a-f0-9]{64}", expected_manifest_hash) is None:
            raise ValueError("Known snapshot hash required")
        retired = root.parent / f".retired-{expected_manifest_hash}.tmp"
        marker = root.parent / f".retirement-{expected_manifest_hash}"
        if not root.exists() and not retired.exists():
            if marker.exists():
                metadata = _marker_read(marker)
                if (
                    metadata.get("state") == "REMOVED"
                    and metadata.get("manifest_hash") == expected_manifest_hash
                ):
                    return "ALREADY_REMOVED"
            raise ValueError("Selected snapshot unavailable")
        if root.exists():
            manifest = Snapshots._manifest(root, expected_manifest_hash)
            selected = root
        else:
            envelope = _marker_read(marker)
            manifest = Manifest.model_validate_json(json.dumps(envelope["manifest"]))
            if hashed(manifest.model_dump(mode="json")) != expected_manifest_hash:
                raise ValueError("Retirement selection mismatch")
            selected = retired
        if not _tree(selected).issubset({f.path for f in manifest.files} | {"manifest.json"}):
            raise ValueError("Unexpected retirement contents")
        current = clock if clock is not None else lambda: time.time_ns() // 1000000
        if not all((journal_path / n).is_file() for n in ("ledger.jsonl", "head.json")):
            raise ValueError("Current deletion journal required")
        with closing(Tombstones(journal_path)) as journal:
            deleted = {m.session_id for m in journal.entries()}
            due = (
                manifest.removal_due_ms is not None and manifest.removal_due_ms <= current()
            ) or any(r.session_id in deleted for r in manifest.sessions)
            if not due:
                return "RETAINED"
            if root.exists():
                if not marker.exists():
                    _write(
                        marker,
                        json.dumps(
                            {
                                "manifest": manifest.model_dump(mode="json"),
                                "manifest_hash": expected_manifest_hash,
                                "state": "PREPARED",
                            }
                        ).encode(),
                    )
                else:
                    saved = _marker_read(marker)
                    if saved.get("manifest_hash") != expected_manifest_hash:
                        raise ValueError("Retirement marker conflict")
                _publish(root, retired)
            shutil.rmtree(retired)
            _fsync(root.parent)
            replacement = marker.parent / f".retirement-{uuid4()}.tmp"
            _write(
                replacement,
                json.dumps(
                    {
                        "id": str(manifest.id),
                        "manifest_hash": expected_manifest_hash,
                        "state": "REMOVED",
                        "removed_ms": current(),
                        "operator_uid": os.getuid(),
                    }
                ).encode(),
            )
            os.replace(replacement, marker)
            _fsync(marker.parent)
        return "REMOVED"

    @staticmethod
    def restore(
        root: Path,
        target: Path,
        *,
        journal_path: Path,
        expected_manifest_hash: str,
        clock: Callable[[], int] | None = None,
        fault: Callable[[str], None] | None = None,
        callbacks: Mapping[str, Callable[[RequestContext, TransactionPort], None]] | None = None,
    ) -> Restored:
        root, target, journal_path = _safe_path(root), _safe_path(target), _safe_path(journal_path)
        if (
            target == root
            or target in root.parents
            or root in target.parents
            or target == journal_path
            or target in journal_path.parents
            or journal_path in target.parents
        ):
            raise ValueError("Separate restore and current journal roots required")
        manifest = Snapshots.verify(root, expected_manifest_hash)
        boundary = fault if fault is not None else lambda phase: None
        boundary("after_verify")
        if not all((journal_path / n).is_file() for n in ("ledger.jsonl", "head.json")):
            raise ValueError("Current deletion journal required")
        _parent(target)
        stage = target.parent / f".restore-{uuid4()}.tmp"
        lease_descriptor = reserve(stage)
        published = False
        try:
            stage.mkdir(mode=0o700)
            for label in ("db", "raw", "artifacts", "imports"):
                (stage / label).mkdir(mode=0o700)
            for f in manifest.files:
                path = (
                    stage / "db" / "data.sqlite" if f.path == "snapshot.sqlite" else stage / f.path
                )
                with _read(root, f.path) as fd:
                    _copy(fd, path, expected=f)
                if f.path == "snapshot.sqlite":
                    os.chmod(path, 0o600)
            boundary("after_files")
            p = Paths(
                database=stage / "db" / "data.sqlite",
                raw=stage / "raw",
                artifacts=stage / "artifacts",
                imports=stage / "imports",
                journal=journal_path,
            )
            with Maintenance(p, clock=clock, callbacks=callbacks) as m:
                _invalidate(m)
                m.check()
                m.audit("RESTORE_COMPLETED", manifest.id, expected_manifest_hash)
                purged = m.purged
            boundary("after_reconciliation")
            sync_tree(stage)
            boundary("before_publish")
            _publish(stage, target)
            published = True
            paths = Paths(
                database=target / "db" / "data.sqlite",
                raw=target / "raw",
                artifacts=target / "artifacts",
                imports=target / "imports",
                journal=journal_path,
            )
            return Restored(
                id=manifest.id,
                manifest_hash=expected_manifest_hash,
                purged_sessions=purged,
                paths=paths,
            )
        finally:
            try:
                if not published and stage.exists():
                    shutil.rmtree(stage)
            finally:
                release(stage, lease_descriptor)


@contextmanager
def _item_fd(root: Path, item: Item) -> Iterator[int]:
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = package = -1
    try:
        PrivateFiles.private(directory, directory=True)
        package = os.open(
            str(item.package), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
        )
        PrivateFiles.private(package, directory=True)
        fd = os.open(item.filename, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=package)
        PrivateFiles.private(fd)
        yield fd
    finally:
        if fd >= 0:
            os.close(fd)
        if package >= 0:
            os.close(package)
        os.close(directory)


def _invalidate(m: Maintenance) -> None:
    with m.database.begin() as uow:
        uow.connection.execute("UPDATE platform_auth_sessions SET revoked=1")
        uow.connection.execute("UPDATE platform_workers SET revoked=1")
        uow.connection.execute("UPDATE platform_worker_scopes SET revoked=1")
        uow.connection.execute("DELETE FROM platform_context_receipts")
        for run in uow.connection.execute("SELECT * FROM platform_run_state").fetchall():
            active = uow.connection.execute(
                "SELECT a.id,a.reservation FROM platform_attempt_state a JOIN "
                "platform_job_state j ON j.id=a.job_id WHERE j.run_id=? AND a.state='ACTIVE'",
                (run["id"],),
            ).fetchall()
            for attempt in active:
                uow.connection.execute(
                    "UPDATE platform_attempt_state SET "
                    "state='CANCELLED',charged=reservation,failure_code='JOB_CANCELLED' WHERE id=?",
                    (attempt[0],),
                )
            charge = sum(a[1] for a in active)
            uow.connection.execute(
                "UPDATE platform_run_state SET "
                "used=used+?,reserved=reserved-?,version=version+1 WHERE id=?",
                (charge, charge, run["id"]),
            )
            changed = uow.connection.execute(
                "UPDATE platform_job_state SET "
                "state='CANCELLED',failure_code='JOB_CANCELLED' WHERE run_id=? "
                "AND state IN ('QUEUED','RETRY_WAIT','RUNNING')",
                (run["id"],),
            ).rowcount
            if changed:
                payload = AnalysisRun.model_validate_json(run["payload"]).model_copy(
                    update={"status": "CANCELLED", "usage": None}
                )
                uow.connection.execute(
                    "UPDATE platform_run_state SET payload=? WHERE id=?",
                    (payload.model_dump_json(), run["id"]),
                )
        invariant(uow)
        uow.commit()


def _publish(stage: Path, target: Path) -> None:
    descriptor = os.open(
        target.parent / ".publish.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        PrivateFiles.private(descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if target.exists() or target.is_symlink():
            raise ValueError("Destination already exists")
        os.rename(stage, target)
        try:
            _fsync(target.parent)
        except BaseException:
            os.rename(target, stage)
            raise
    finally:
        os.close(descriptor)


def _tree(root: Path) -> set[str]:
    result = set()
    for folder, dirs, files in root.walk(follow_symlinks=False):
        for directory in dirs:
            path = folder / directory
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                PrivateFiles.private(fd, directory=True)
            finally:
                os.close(fd)
            relative = path.relative_to(root).as_posix()
            if re.fullmatch(rf"(?:raw|artifacts|imports)(?:/{IDENTIFIER})?", relative) is None:
                raise ValueError("Unexpected snapshot directory")
        for filename in files:
            result.add((folder / filename).relative_to(root).as_posix())
    return result


def _marker_read(path: Path) -> dict[str, object]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        PrivateFiles.private(fd)
        if os.fstat(fd).st_size > 8 * 1024**2:
            raise ValueError("Retirement marker exceeds limit")
        body = strict_json(os.read(fd, 8 * 1024**2 + 1).decode())
        if not isinstance(body, dict):
            raise ValueError("Invalid retirement marker")
        return body
    finally:
        os.close(fd)
