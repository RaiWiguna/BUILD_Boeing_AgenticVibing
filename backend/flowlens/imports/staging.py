"""Private, bounded draft staging. No source/session creation or provider calls."""

import fcntl
import hashlib
import json
import os
import re
import stat
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal
from uuid import UUID, uuid4

from flowlens.auth.accounts import Account
from flowlens.auth.sessions import Sessions, token_hash
from flowlens.core.errors import ContractError
from flowlens.imports.inspection import InvalidContent, inspect_audio, rows
from flowlens.storage.sqlite.database import Database, UnitOfWork
from pydantic import BaseModel, ConfigDict, Field

Role = Literal["audio", "events", "tracks"]


class ImportLimits(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    max_file_bytes: int = Field(default=2 * 1024**3, ge=1, le=8 * 1024**3)
    max_total_bytes: int = Field(default=4 * 1024**3, ge=1, le=16 * 1024**3)
    max_sidecar_bytes: int = Field(default=64 * 1024**2, ge=1, le=128 * 1024**2)
    max_duration_ms: int = Field(default=7200000, ge=1, le=7200000)
    max_rows: int = Field(default=200000, ge=1, le=1000000)
    max_files: int = Field(default=4, ge=1, le=4)
    decoder_timeout: int = Field(default=60, ge=1, le=120)
    ttl_ms: int = Field(default=86400000, ge=1, le=86400000)
    max_drafts: int = Field(default=100, ge=1, le=1000)
    max_owner_drafts: int = Field(default=16, ge=1, le=100)


class Issue(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    code: str
    field: str
    row: int | None = None
    blocking: bool = True
    remediation: str


class FilePreview(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    id: UUID
    role: Role
    filename: str
    media_type: str
    profile: str
    sha256: str
    size_bytes: int
    channels: int | None = None
    sample_rate_hz: int | None = None
    frames: int | None = None
    duration_ms: int | None = None
    row_count: int | None = None


class ImportPreview(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    id: UUID
    profile_version: Literal["imports-1"] = "imports-1"
    status: Literal["UPLOADING", "NEEDS_REMEDIATION", "PREPARED", "FAILED"]
    expires_ms: int
    files: list[FilePreview]
    issues: list[Issue]
    tracks_present: bool = False
    metadata_revision: int = Field(default=0, ge=0, le=64)
    clock_alignment: Literal["UNKNOWN", "KNOWN"] = "UNKNOWN"
    layout_status: Literal["UNKNOWN", "DECLARED"] = "UNKNOWN"
    rights_status: Literal["UNDECLARED", "DECLARED"] = "UNDECLARED"


class ImportFailure(ContractError):
    def __init__(self, code: str, field: str = "files", row: int | None = None) -> None:
        self.issues = [
            Issue(
                code=code,
                field=field,
                row=row,
                remediation="Correct the indicated file or profile and upload again.",
            )
        ]
        super().__init__("INVALID_IMPORT")


@dataclass(frozen=True)
class Upload:
    role: Role
    filename: str
    media_type: str
    chunks: Iterable[bytes]
    expected_sha256: str | None = None


def profile(role: str, filename: str, media_type: str) -> tuple[str, str]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", filename):
        raise ImportFailure("INVALID_FILENAME")
    extension = filename.rsplit(".", 1)[-1].lower()
    allowed = {
        ("audio", "wav"): ("audio/wav", {"audio/wav", "audio/x-wav"}),
        ("audio", "flac"): ("audio/flac", {"audio/flac", "audio/x-flac"}),
        ("events", "json"): ("application/json", {"application/json"}),
        ("events", "jsonl"): ("application/x-ndjson", {"application/x-ndjson", "application/json"}),
        ("tracks", "json"): ("application/json", {"application/json"}),
        ("tracks", "csv"): ("text/csv", {"text/csv"}),
    }
    choice = allowed.get((role, extension))
    if choice is None:
        raise ImportFailure("UNSUPPORTED_FORMAT")
    if media_type not in choice[1] | {"application/octet-stream"}:
        raise ImportFailure("CONTENT_MISMATCH")
    return extension, choice[0]


def digest(fd: int) -> str:
    result = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while block := os.read(fd, 65536):
        result.update(block)
    return result.hexdigest()


class Imports:
    def __init__(
        self,
        database: Database,
        sessions: Sessions,
        root: Path,
        *,
        limits: ImportLimits | None = None,
    ) -> None:
        self.database, self.sessions = database, sessions
        self.limits = limits or ImportLimits()
        self.root = root.absolute()
        if any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise ValueError("Staging symlinks are unsupported.")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.lock_fd = -1
        try:
            self._private(self.root_fd, directory=True)
            self.lock_fd = os.open(
                ".owner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=self.root_fd
            )
            self._private(self.lock_fd)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.slots = BoundedSemaphore(4)
            self.closed = False
            self.recover()
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self.lock_fd >= 0:
            os.close(self.lock_fd)
            self.lock_fd = -1
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1
        self.closed = True

    def _private(self, fd: int, *, directory: bool = False) -> None:
        info = os.fstat(fd)
        valid = (
            stat.S_ISDIR(info.st_mode)
            if directory
            else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        )
        if not valid or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Private staging permissions required.")

    def _admin(self, uow: UnitOfWork, token: str) -> Account:
        account = self.sessions.authenticate(uow, token_hash(token))
        if not account.is_admin:
            raise ContractError("ACCESS_DENIED")
        return account

    def _remove(self, identifier: str) -> None:
        if str(UUID(identifier)) != identifier:
            raise ValueError("Invalid staging identity.")
        try:
            directory = os.open(
                identifier, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.root_fd
            )
        except FileNotFoundError:
            return
        except NotADirectoryError:
            os.unlink(identifier, dir_fd=self.root_fd)
            return
        try:
            for name in os.listdir(directory):
                os.unlink(name, dir_fd=directory)
        finally:
            os.close(directory)
        os.rmdir(identifier, dir_fd=self.root_fd)

    def recover(self) -> None:
        # Called with exclusive staging ownership, before the host accepts requests.
        with self.database.begin() as uow:
            known = {
                row["id"]: row
                for row in uow.connection.execute("SELECT * FROM platform_import_drafts")
            }
            for identifier, row in known.items():
                if row["status"] == "UPLOADING" or row["expires_ms"] <= self.sessions.clock():
                    self._remove(identifier)
                    uow.connection.execute(
                        "DELETE FROM platform_import_drafts WHERE id=?", (identifier,)
                    )
            for name in os.listdir(self.root_fd):
                try:
                    canonical = str(UUID(name))
                except ValueError:
                    continue
                if canonical == name and name not in known:
                    self._remove(name)
            uow.commit()

    def start(self, token: str, key: str) -> "UploadSession":
        if self.closed:
            raise RuntimeError("Staging is closed.")
        if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
            raise ContractError("INVALID_INPUT")
        if not self.slots.acquire(blocking=False):
            raise ImportFailure("IMPORT_BUSY")
        identifier = uuid4()
        try:
            with self.database.begin() as uow:
                owner = self._admin(uow, token)
                rows_count = uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_import_drafts"
                ).fetchone()[0]
                owner_count = uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_import_drafts WHERE owner_id=?", (str(owner.id),)
                ).fetchone()[0]
                prior = uow.connection.execute(
                    "SELECT 1 FROM platform_import_drafts WHERE owner_id=? AND key_hash=?",
                    (str(owner.id), hashlib.sha256(key.encode()).hexdigest()),
                ).fetchone()
                if prior is None and (
                    rows_count >= self.limits.max_drafts
                    or owner_count >= self.limits.max_owner_drafts
                ):
                    raise ImportFailure("DRAFT_LIMIT")
                expires = self.sessions.clock() + self.limits.ttl_ms
                uow.connection.execute(
                    "INSERT INTO platform_import_drafts VALUES (?,?,NULL,NULL,'UPLOADING',?,NULL)",
                    (str(identifier), str(owner.id), expires),
                )
                uow.commit()
            os.mkdir(str(identifier), 0o700, dir_fd=self.root_fd)
            return UploadSession(self, token, key, identifier, owner.id, expires)
        except BaseException:
            self._abort(identifier)
            self.slots.release()
            raise

    def _abort(self, identifier: UUID) -> None:
        self._remove(str(identifier))
        with self.database.begin() as uow:
            uow.connection.execute(
                "DELETE FROM platform_import_drafts WHERE id=?", (str(identifier),)
            )
            uow.commit()

    def stage(self, token: str, key: str, files: Sequence[Upload]) -> ImportPreview:
        session = self.start(token, key)
        try:
            for file in files:
                sink = session.add(file.role, file.filename, file.media_type, file.expected_sha256)
                for block in file.chunks:
                    sink.write(block)
                sink.seal()
            return session.finish()
        finally:
            session.abort()

    def get(self, token: str, identifier: UUID) -> ImportPreview:
        with self.database.begin() as uow:
            owner = self._admin(uow, token)
            row = uow.connection.execute(
                "SELECT * FROM platform_import_drafts WHERE id=?", (str(identifier),)
            ).fetchone()
            if row is None or row["expires_ms"] <= self.sessions.clock():
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if row["owner_id"] != str(owner.id):
                raise ContractError("ACCESS_DENIED")
            if row["status"] == "UPLOADING":
                return ImportPreview(
                    id=identifier,
                    status="UPLOADING",
                    expires_ms=row["expires_ms"],
                    files=[],
                    issues=[],
                )
            preview = ImportPreview.model_validate_json(row["payload"])
        self.verify(preview)
        return preview

    @contextmanager
    def open_file(self, preview: ImportPreview, item: FilePreview) -> Iterator[int]:
        directory = -1
        fd = -1
        try:
            directory = os.open(
                str(preview.id), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.root_fd
            )
            self._private(directory, directory=True)
            fd = os.open(str(item.id) + ".upload", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            self._private(fd)
            if os.fstat(fd).st_size != item.size_bytes or digest(fd) != item.sha256:
                raise ImportFailure("HASH_MISMATCH")
            yield fd
            if os.fstat(fd).st_size != item.size_bytes or digest(fd) != item.sha256:
                raise ImportFailure("HASH_MISMATCH")
        except (OSError, ValueError):
            raise ImportFailure("STAGED_FILE_UNAVAILABLE") from None
        finally:
            if fd >= 0:
                os.close(fd)
            if directory >= 0:
                os.close(directory)

    def verify(self, preview: ImportPreview) -> None:
        try:
            directory = os.open(
                str(preview.id), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.root_fd
            )
            try:
                self._private(directory, directory=True)
                for item in preview.files:
                    fd = os.open(
                        str(item.id) + ".upload", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory
                    )
                    try:
                        self._private(fd)
                        if os.fstat(fd).st_size != item.size_bytes or digest(fd) != item.sha256:
                            raise ImportFailure("HASH_MISMATCH")
                    finally:
                        os.close(fd)
            finally:
                os.close(directory)
        except (OSError, ValueError):
            raise ImportFailure("STAGED_FILE_UNAVAILABLE") from None


class FileSink:
    def __init__(
        self, session: "UploadSession", role: Role, name: str, media_type: str, expected: str | None
    ) -> None:
        self.session, self.role, self.name = session, role, name
        self.extension, self.media_type = profile(role, name, media_type)
        if expected is not None and not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise ImportFailure("INVALID_HASH")
        self.expected = expected
        self.id, self.size, self.hash = uuid4(), 0, hashlib.sha256()
        self.fd = os.open(
            str(self.id) + ".upload",
            os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
            dir_fd=session.directory,
        )
        self.sealed = False

    def write(self, block: bytes) -> None:
        if self.sealed or self.fd < 0:
            raise RuntimeError("Upload file is closed.")
        if type(block) is not bytes:
            raise ImportFailure("INVALID_CHUNK")
        limit = self.session.service.limits
        if self.size + len(block) > min(
            limit.max_file_bytes,
            limit.max_sidecar_bytes if self.role != "audio" else limit.max_file_bytes,
        ):
            raise ImportFailure("FILE_SIZE_LIMIT")
        if self.session.total + len(block) > limit.max_total_bytes:
            raise ImportFailure("TOTAL_SIZE_LIMIT")
        pending = memoryview(block)
        while pending:
            written = os.write(self.fd, pending)
            if written <= 0:
                raise OSError("Staging write failed.")
            pending = pending[written:]
        self.hash.update(block)
        self.size += len(block)
        self.session.total += len(block)

    def seal(self) -> None:
        if not self.size:
            raise ImportFailure("EMPTY_FILE")
        os.fsync(self.fd)
        self.sealed = True
        if self.expected is not None and self.hash.hexdigest() != self.expected:
            raise ImportFailure("HASH_MISMATCH")

    def inspect(self) -> FilePreview:
        if not self.sealed:
            raise ImportFailure("INCOMPLETE_UPLOAD")
        limit = self.session.service.limits
        facts: dict[str, int | None] = {}
        try:
            if self.role == "audio":
                audio = inspect_audio(
                    self.fd, self.extension, limit.max_duration_ms, limit.decoder_timeout
                )
                facts = audio.model_dump()
            else:
                facts["row_count"] = rows(self.fd, self.extension, self.role, limit.max_rows)
        except InvalidContent as error:
            raise ImportFailure(error.code, self.role, error.row) from None
        if digest(self.fd) != self.hash.hexdigest():
            raise ImportFailure("HASH_MISMATCH")
        return FilePreview(
            id=self.id,
            role=self.role,
            filename=self.name,
            media_type=self.media_type,
            profile=f"canonical-{self.role}-{self.extension}-1",
            sha256=self.hash.hexdigest(),
            size_bytes=self.size,
            **facts,
        )

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


class UploadSession:
    def __init__(
        self, service: Imports, token: str, key: str, identifier: UUID, owner: UUID, expires: int
    ) -> None:
        self.service, self.token, self.key = service, token, key
        self.id, self.owner, self.expires = identifier, owner, expires
        self.files: list[FileSink] = []
        self.total, self.done, self.closed = 0, False, False
        self.directory = os.open(
            str(identifier), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=service.root_fd
        )

    def add(
        self, role: Role, filename: str, media_type: str, expected: str | None = None
    ) -> FileSink:
        if self.closed or self.done:
            raise RuntimeError("Upload session closed.")
        if len(self.files) >= self.service.limits.max_files:
            raise ImportFailure("FILE_COUNT_LIMIT")
        if any(file.name == filename for file in self.files):
            raise ImportFailure("DUPLICATE_FILE")
        if sum(file.role == role for file in self.files) >= (2 if role == "audio" else 1):
            raise ImportFailure("FILE_COUNT_LIMIT")
        sink = FileSink(self, role, filename, media_type, expected)
        self.files.append(sink)
        return sink

    def finish(self) -> ImportPreview:
        if self.closed or self.done:
            raise RuntimeError("Upload session closed.")
        if not any(file.role == "audio" for file in self.files):
            raise ImportFailure("AUDIO_REQUIRED")
        files = [file.inspect() for file in self.files]
        if sum(file.channels or 0 for file in files) > 2:
            raise ImportFailure("CHANNEL_LIMIT")
        preview = ImportPreview(
            id=self.id,
            status="NEEDS_REMEDIATION",
            expires_ms=self.expires,
            files=files,
            tracks_present=any(file.role == "tracks" for file in files),
            issues=[
                Issue(
                    code="RIGHTS_REQUIRED",
                    field="permissions",
                    remediation="Declare local/cloud/export rights and retention before commit.",
                ),
                Issue(
                    code="CLOCK_REQUIRED",
                    field="clock",
                    blocking=False,
                    remediation="Supply clock metadata; paired conformance remains unavailable.",
                ),
                Issue(
                    code="LAYOUT_REQUIRED",
                    field="layout",
                    blocking=False,
                    remediation="Supply an airport layout to enable map rendering.",
                ),
            ],
        )
        key_hash = hashlib.sha256(self.key.encode()).hexdigest()
        fingerprint = hashlib.sha256(
            json.dumps(
                [item.model_dump(mode="json", exclude={"id"}) for item in files],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        with self.service.database.begin() as uow:
            current = self.service._admin(uow, self.token)
            if current.id != self.owner or self.expires <= self.service.sessions.clock():
                raise ContractError("ACCESS_DENIED")
            previous = uow.connection.execute(
                "SELECT * FROM platform_import_drafts WHERE owner_id=? AND key_hash=?",
                (str(self.owner), key_hash),
            ).fetchone()
            if previous is not None:
                if previous["expires_ms"] <= self.service.sessions.clock():
                    raise ContractError("EVIDENCE_UNAVAILABLE")
                if previous["request_hash"] != fingerprint:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                original = ImportPreview.model_validate_json(previous["payload"])
                self.service.verify(original)
                return original
            uow.connection.execute(
                "UPDATE platform_import_drafts SET key_hash=?,request_hash=?,status=?,payload=? "
                "WHERE id=?",
                (key_hash, fingerprint, preview.status, preview.model_dump_json(), str(self.id)),
            )
            uow.commit()
        self.done = True
        return preview

    def abort(self) -> None:
        if not self.closed:
            self.closed = True
            try:
                for file in self.files:
                    file.close()
                os.close(self.directory)
                if not self.done:
                    self.service._abort(self.id)
            finally:
                self.service.slots.release()
