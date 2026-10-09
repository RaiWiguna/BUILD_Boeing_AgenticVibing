"""Versioned registration and deterministic migration dependency ordering."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from fastapi import APIRouter
from flowlens import CONTRACT_VERSION
from flowlens.contracts.models import JobResult, RequestContext, Snapshot
from flowlens.contracts.ports import UnitOfWork
from flowlens.core.config import Profile


@dataclass(frozen=True)
class MigrationSpec:
    id: str
    owner: Literal["A", "B"]
    depends_on: tuple[str, ...]
    sql: str


@dataclass(frozen=True)
class ModuleRegistration:
    name: str
    contract_version: str = CONTRACT_VERSION
    mock: bool = False
    routes: tuple[APIRouter, ...] = ()
    services: dict[str, object] = field(default_factory=dict)
    repositories: dict[str, object] = field(default_factory=dict)
    migrations: tuple[MigrationSpec, ...] = ()
    job_handlers: dict[str, Callable[[RequestContext, JobResult, UnitOfWork], None]] = field(
        default_factory=dict
    )
    snapshot_reader: Callable[[RequestContext], Snapshot] | None = None
    purge_handler: Callable[[RequestContext, UnitOfWork], None] | None = None
    readiness: Callable[[], bool] | None = None
    config_keys: tuple[str, ...] = ()
    inventory_namespaces: tuple[str, ...] = ()


def order_migrations(migrations: list[MigrationSpec]) -> list[MigrationSpec]:
    remaining = {m.id: m for m in migrations}
    if len(remaining) != len(migrations):
        raise ValueError("duplicate migration identifier")
    known = set(remaining)
    if any(not set(m.depends_on) <= known for m in migrations):
        raise ValueError("missing migration dependency")
    result: list[MigrationSpec] = []
    done: set[str] = set()
    while remaining:
        ready = sorted(key for key, m in remaining.items() if set(m.depends_on) <= done)
        if not ready:
            raise ValueError("migration dependency cycle")
        for key in ready:
            result.append(remaining.pop(key))
            done.add(key)
    return result


@dataclass
class ModuleRegistry:
    profile: Profile
    modules: list[ModuleRegistration] = field(default_factory=list)

    def register(self, module: ModuleRegistration) -> None:
        if module.contract_version != CONTRACT_VERSION:
            raise ValueError("incompatible contract version")
        if self.profile == "production" and module.mock:
            raise ValueError("MOCK adapter forbidden in production")
        if any(item.name == module.name for item in self.modules):
            raise ValueError("duplicate module name")
        existing = {key for item in self.modules for key in item.job_handlers}
        if existing.intersection(module.job_handlers):
            raise ValueError("duplicate job handler")
        self.modules.append(module)
