"""Opaque, owner-only immutable file packages with explicit durability boundaries."""

import fcntl
import hashlib
import json
import os
import stat
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from flowlens.imports.staging import FilePreview, ImportFailure


class PrivateFiles:
    def __init__(self, root: Path) -> None:
        self.root = root.absolute()
        self.fd = self.lock = -1
        if any(p.is_symlink() for p in (self.root, *self.root.parents)):
            raise ValueError("Private root cannot use symlinks")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self.private(self.fd, directory=True)
            self.lock = os.open(
                ".owner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=self.fd
            )
            self.private(self.lock)
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        for descriptor in (self.lock, self.fd):
            if descriptor >= 0:
                os.close(descriptor)
        self.lock = self.fd = -1

    @staticmethod
    def private(fd: int, *, directory: bool = False) -> None:
        info = os.fstat(fd)
        valid = (
            stat.S_ISDIR(info.st_mode)
            if directory
            else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        )
        if not valid or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ImportFailure("PRIVATE_STORAGE_UNAVAILABLE")

    @contextmanager
    def directory(self, package: UUID) -> Iterator[int]:
        fd = os.open(str(package), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            self.private(fd, directory=True)
            yield fd
        finally:
            os.close(fd)

    def create(self, package: UUID) -> None:
        os.mkdir(str(package), 0o700, dir_fd=self.fd)
        os.fsync(self.fd)

    def write(self, package: UUID, item: FilePreview, chunks: Iterable[bytes]) -> None:
        with self.directory(package) as directory:
            fd = os.open(
                str(item.id) + ".raw",
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            try:
                digest, size = hashlib.sha256(), 0
                for block in chunks:
                    if type(block) is not bytes or size + len(block) > item.size_bytes:
                        raise ImportFailure("FILE_SIZE_LIMIT")
                    pending = memoryview(block)
                    while pending:
                        written = os.write(fd, pending)
                        if written <= 0:
                            raise OSError("Private write failed")
                        pending = pending[written:]
                    size += len(block)
                    digest.update(block)
                if size != item.size_bytes or digest.hexdigest() != item.sha256:
                    raise ImportFailure("HASH_MISMATCH")
                os.fchmod(fd, 0o400)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(directory)

    def seal(self, package: UUID, manifest_hash: str, items: list[FilePreview]) -> None:
        with self.directory(package) as directory:
            fd = os.open(
                "inventory.json",
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            try:
                body = json.dumps(
                    {
                        "manifest_hash": manifest_hash,
                        "files": [f.model_dump(mode="json") for f in items],
                    },
                    sort_keys=True,
                ).encode()
                with os.fdopen(fd, "wb", closefd=False) as stream:
                    stream.write(body)
                    stream.flush()
                    os.fchmod(fd, 0o400)
                    os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(directory)
        os.fsync(self.fd)

    @contextmanager
    def open(self, package: UUID, item: FilePreview) -> Iterator[int]:
        try:
            with self.directory(package) as directory:
                fd = os.open(str(item.id) + ".raw", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
                try:
                    self.private(fd)
                    if os.fstat(fd).st_size != item.size_bytes:
                        raise ImportFailure("HASH_MISMATCH")
                    digest = hashlib.sha256()
                    while block := os.read(fd, 65536):
                        digest.update(block)
                    if digest.hexdigest() != item.sha256:
                        raise ImportFailure("HASH_MISMATCH")
                    os.lseek(fd, 0, os.SEEK_SET)
                    yield fd
                finally:
                    os.close(fd)
        except OSError:
            raise ImportFailure("PRIVATE_STORAGE_UNAVAILABLE") from None

    def verify(self, package: UUID, manifest_hash: str, items: list[FilePreview]) -> None:
        try:
            with self.directory(package) as directory:
                fd = os.open("inventory.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
                try:
                    self.private(fd)
                    body = os.read(fd, 65537)
                    expected = {
                        "manifest_hash": manifest_hash,
                        "files": [f.model_dump(mode="json") for f in items],
                    }
                    if len(body) > 65536 or json.loads(body) != expected:
                        raise ImportFailure("PACKAGE_INTEGRITY_FAILURE")
                finally:
                    os.close(fd)
            for item in items:
                with self.open(package, item):
                    pass
        except (OSError, ValueError):
            raise ImportFailure("PACKAGE_INTEGRITY_FAILURE") from None

    def remove(self, package: UUID) -> None:
        try:
            with self.directory(package) as directory:
                for name in os.listdir(directory):
                    os.unlink(name, dir_fd=directory)
            os.rmdir(str(package), dir_fd=self.fd)
            os.fsync(self.fd)
        except FileNotFoundError:
            pass
        except NotADirectoryError:
            os.unlink(str(package), dir_fd=self.fd)
