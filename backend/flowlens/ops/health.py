"""Actual local dependency probes. Cloud state and integration gates are separate."""

import os
from collections.abc import Callable, Sequence
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from uuid import uuid4

from flowlens.assets.storage import PrivateFiles
from flowlens.auth.sessions import token_hash
from flowlens.core.errors import ContractError
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import MigrationSpec
from flowlens.geometry.kernel import GEOMETRY_VERSION
from flowlens.geometry.rules import RuleProfile
from flowlens.ops.usage import invariant
from flowlens.replay.snapshots import REDUCER_VERSION
from flowlens.storage.sqlite.migrate import checksum


class Operations:
    def __init__(
        self,
        state: Any,
        settings: HostSettings,
        migrations: Sequence[MigrationSpec],
        *,
        profile: str,
    ) -> None:
        self.state, self.settings, self.profile = state, settings, profile
        self.manifest = {m.id: checksum(m) for m in migrations}
        self.free_bytes: Callable[[int], int] = lambda fd: (
            os.fstatvfs(fd).f_bavail * os.fstatvfs(fd).f_frsize
        )

    def _root(self, fd: int) -> dict[str, int | str]:
        PrivateFiles.private(fd, directory=True)
        stats = os.fstatvfs(fd)
        free = self.free_bytes(fd)
        status = "DISK_LOW" if free < self.settings.minimum_free_bytes else "READY"
        name = f".ops-{uuid4()}.probe"
        created = False
        try:
            probe = os.open(
                name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=fd
            )
            created = True
            try:
                if os.write(probe, b"FlowLens probe\n") != 15:
                    raise OSError("Storage probe failed")
                os.fsync(probe)
            finally:
                os.close(probe)
        finally:
            if created:
                os.unlink(name, dir_fd=fd)
                os.fsync(fd)
        return {
            "status": status,
            "free_bytes": free,
            "total_bytes": stats.f_blocks * stats.f_frsize,
        }

    def _roots(self) -> dict[str, dict[str, int | str]]:
        roots: dict[str, dict[str, int | str]] = {}
        for label, service, attr in (
            ("imports", self.state.imports, "root_fd"),
            ("raw", self.state.raw_files, "fd"),
            ("artifacts", self.state.artifact_files, "fd"),
            ("tombstones", self.state.tombstones.files if self.state.tombstones else None, "fd"),
        ):
            try:
                roots[label] = (
                    self._root(getattr(service, attr)) if service else {"status": "NOT_CONFIGURED"}
                )
            except Exception:
                roots[label] = {"status": "UNAVAILABLE"}
        if self.state.transactions is None:
            roots["database"] = {"status": "NOT_CONFIGURED"}
        else:
            fd = -1
            try:
                fd = os.open(
                    self.state.transactions.path.parent,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                )
                roots["database"] = self._root(fd)
            except Exception:
                roots["database"] = {"status": "UNAVAILABLE"}
            finally:
                if fd >= 0:
                    os.close(fd)
        return roots

    def ready(self) -> dict[str, object]:
        dependencies = {name: info["status"] for name, info in self._roots().items()}
        database = self.state.transactions
        if database is not None:
            try:
                if database.path.is_symlink():
                    raise ValueError("Invalid database identity")
                with database.begin() as uow:
                    applied = dict(
                        uow.connection.execute("SELECT id,checksum FROM platform_schema_migrations")
                    )
                    if (
                        applied != self.manifest
                        or uow.connection.execute("PRAGMA quick_check").fetchone()[0] != "ok"
                    ):
                        raise ValueError("Schema invariant failed")
                    uow.connection.execute("UPDATE platform_ops_probe SET value=value+1 WHERE id=1")
                    # A real write rolled back by UOW exit, leaving no health history/data mutation.
            except Exception:
                dependencies["database"] = "UNAVAILABLE"
        for label, service in (
            ("replay", self.state.controls),
            ("coordinator", self.state.jobs),
            ("retention", self.state.retention),
        ):
            dependencies[label] = (
                "READY" if service is not None and database is not None else "NOT_CONFIGURED"
            )
        if self.state.jobs is not None and database is not None:
            try:
                if self.state.jobs.database is not database:
                    raise ValueError("Coordinator identity mismatch")
                with database.begin() as uow:
                    invariant(uow)
            except Exception:
                dependencies["coordinator"] = "UNAVAILABLE"
        if self.state.tombstones is not None:
            try:
                self.state.tombstones.entries()
            except Exception:
                dependencies["tombstones"] = "UNAVAILABLE"
        return {
            "ready": all(v == "READY" for v in dependencies.values()),
            "scope": "LOCAL_PLATFORM",
            "implementation": "HOST_ONLY",
            "profile": self.profile,
            "dependencies": dependencies,
            "integration_gate": "NOT_STARTED",
            "provider_verified": False,
        }

    def disk(self, token: str) -> dict[str, object]:
        if self.state.transactions is None or self.state.imports is None:
            raise ContractError("NOT_EVALUABLE")
        with self.state.transactions.begin() as uow:
            actor = self.state.imports.sessions.authenticate(uow, token_hash(token))
            if not actor.is_admin:
                raise ContractError("ACCESS_DENIED")
        return {"roots": self._roots(), "minimum_free_bytes": self.settings.minimum_free_bytes}

    def release(self) -> dict[str, object]:
        dependencies = {}
        for name in ("atc-flowlens", "fastapi", "pydantic", "uvicorn", "shapely"):
            try:
                dependencies[name] = version(name)
            except PackageNotFoundError:
                dependencies[name] = "UNRECORDED"
        return {
            "contract_version": "1.0.0",
            "implementation": "HOST_ONLY",
            "profile": self.profile,
            "source_sha": self.settings.release_sha,
            "lock_sha256": self.settings.lock_sha256,
            "schema_versions": sorted(self.manifest),
            "dependencies": dependencies,
            "reducer_version": REDUCER_VERSION,
            "geometry_version": GEOMETRY_VERSION,
            "rule_template_version": RuleProfile().version,
            "lab_layout_version": RuleProfile().layout_version,
            "source_sha_origin": "OPERATOR_DECLARED" if self.settings.release_sha else "UNRECORDED",
            "lock_sha256_origin": "OPERATOR_DECLARED"
            if self.settings.lock_sha256
            else "UNRECORDED",
            "domain_validation": "NOT_DOMAIN_VALIDATED",
            "integration_gate": "NOT_STARTED",
            "provider_verified": False,
            "operational_validation": "NOT_VALIDATED",
        }
