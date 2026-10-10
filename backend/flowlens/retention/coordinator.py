"""Admin preview -> durable plan/marker -> scoped erasure/retry. No provider-log erasure claim."""

import json
import os
import re
from collections.abc import Callable, Mapping
from typing import Literal
from uuid import UUID, uuid4

from flowlens.assets.access import Assets
from flowlens.auth.permissions import Permissions
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import RequestContext
from flowlens.core.errors import ContractError
from flowlens.imports.metadata import hashed
from flowlens.imports.staging import Imports
from flowlens.retention.journal import Tombstones
from flowlens.storage.sqlite.database import UnitOfWork


class Inventory(MetadataModel):
    session_id: UUID
    counts: dict[str, int]
    raw_packages: list[UUID]
    artifact_packages: list[UUID]
    draft_ids: list[UUID]
    contents_hash: str
    inventory_hash: str


class PurgeReceipt(MetadataModel):
    session_id: UUID
    state: Literal["PREPARED", "DONE"]
    inventory_hash: str


class Retention:
    def __init__(
        self,
        permissions: Permissions,
        assets: Assets,
        journal: Tombstones,
        *,
        imports: Imports | None = None,
        callbacks: Mapping[str, Callable[[RequestContext, UnitOfWork], None]] | None = None,
        inventory_namespaces: tuple[str, ...] = (),
    ) -> None:
        self.permissions, self.assets, self.journal = permissions, assets, journal
        self.database = permissions.database
        self.imports = imports
        self.callbacks = callbacks or {}
        self.namespaces = inventory_namespaces
        if (
            len(set(self.namespaces)) != len(self.namespaces)
            or any(not re.fullmatch(r"analysis(?:\.[a-z0-9_]+)*", n) for n in self.namespaces)
            or any(n not in self.namespaces for n in self.callbacks)
        ):
            raise ValueError("Registered purge namespaces required")
        with self.database.begin() as uow:
            self.pending = {
                UUID(r[0])
                for r in uow.connection.execute(
                    "SELECT session_id FROM platform_purges WHERE state!='DONE'"
                )
            }
        permissions.deny_session = lambda sid: sid in self.pending or journal.contains(sid)
        self.fault: Callable[[str], None] = lambda phase: None

    def recover(self) -> list[UUID]:
        """Reconcile current external markers and expiry before opening restored storage."""
        markers = {m.session_id: m for m in self.journal.entries()}
        with self.database.begin() as uow:
            expired = {
                UUID(r[0])
                for r in uow.connection.execute(
                    "SELECT session_id FROM platform_source_packages GROUP BY session_id "
                    "HAVING MAX(expires_ms)<=?",
                    (self.permissions.sessions.clock(),),
                )
            }
            candidates = self.pending | set(markers) | expired
            for sid in sorted(candidates, key=str):
                if not uow.connection.execute(
                    "SELECT 1 FROM platform_sessions WHERE id=?", (str(sid),)
                ).fetchone():
                    continue
                old = uow.connection.execute(
                    "SELECT * FROM platform_purges WHERE session_id=?", (str(sid),)
                ).fetchone()
                if old is not None and old["state"] == "PREPARED":
                    continue
                # DONE can coexist with resurrected contents after an older asset/DB restore.
                sensitive = uow.connection.execute(
                    "SELECT 1 FROM platform_revisions WHERE session_id=?", (str(sid),)
                ).fetchone()
                if old is not None and not sensitive:
                    continue
                inventory = self._inventory(uow, sid)
                marker = markers.get(sid)
                reason = marker.reason if marker else "RETENTION_EXPIRED"
                digest = marker.inventory_hash if marker else inventory.inventory_hash
                created = marker.deleted_ms if marker else self.permissions.sessions.clock()
                actor = old["actor_id"] if old else str(UUID(int=0))
                uow.connection.execute(
                    "INSERT INTO platform_purges VALUES (?,?,?,'PREPARED',?,?,?,?) "
                    "ON CONFLICT(session_id) DO UPDATE SET state='PREPARED',"
                    "payload=excluded.payload",
                    (
                        str(sid),
                        actor,
                        reason,
                        digest,
                        inventory.model_dump_json(),
                        hashed("restore-reconciliation"),
                        created,
                    ),
                )
                self.pending.add(sid)
            uow.commit()
        completed = []
        for sid in sorted(self.pending, key=str):
            self._resume(sid)
            completed.append(sid)
        self.expire_artifacts()
        return completed

    def expire_artifacts(self) -> int:
        """Erase expired private bytes; retained metadata never grants download authority."""
        with self.database.begin() as uow:
            packages = [
                UUID(r[0])
                for r in uow.connection.execute(
                    "SELECT package_id FROM platform_artifact_staging WHERE expires_ms<=?",
                    (self.permissions.sessions.clock(),),
                )
            ]
        if packages and self.assets.artifacts is None:
            raise ContractError("NOT_EVALUABLE")
        if self.assets.artifacts is not None:
            for package in packages:
                self.assets.artifacts.remove(package)
        return len(packages)

    # Dynamic SQL below uses regex-validated schema identifiers; values stay bound.
    def _outside_scope(self, uow: UnitOfWork, sid: UUID) -> str:
        tables = [
            r[0]
            for r in uow.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        data: dict[str, object] = {}
        for name in tables:
            if not re.fullmatch(r"[a-z][a-z0-9_]+", name):
                raise ContractError("NOT_EVALUABLE")
            scoped = "session_id" in {
                r[1] for r in uow.connection.execute(f"PRAGMA table_info({name})")
            }
            query = f"SELECT * FROM {name}"  # nosec B608
            args: tuple[str, ...] = ()
            if scoped:
                query += " WHERE session_id!=? OR session_id IS NULL"
                args = (str(sid),)
            # Sort serialized rows, including tables without a rowid.
            data[name] = sorted(json.dumps(tuple(r)) for r in uow.connection.execute(query, args))
        data["schema"] = [
            tuple(r)
            for r in uow.connection.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        ]
        return hashed(data)

    def _tables(self, uow: UnitOfWork) -> list[str]:
        tables = []
        for row in uow.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ):
            name = row[0]
            if not re.fullmatch(r"platform_[a-z0-9_]+", name):
                # Frozen inventory namespaces describe repository records, not arbitrary SQL tables.
                # Fail closed until a module supplies an explicit supported inventory adapter.
                raise ContractError("NOT_EVALUABLE")
            if "session_id" in {
                r[1] for r in uow.connection.execute(f"PRAGMA table_info({name})")
            } and name not in ("platform_purges",):
                tables.append(name)
        return sorted(tables)

    def _inventory(self, uow: UnitOfWork, sid: UUID) -> Inventory:
        if (
            uow.connection.execute(
                "SELECT 1 FROM platform_sessions WHERE id=?", (str(sid),)
            ).fetchone()
            is None
        ):
            raise ContractError("ACCESS_DENIED")
        counts = {
            name: uow.connection.execute(
                f"SELECT COUNT(*) FROM {name} WHERE session_id=?",  # nosec B608
                (str(sid),),
            ).fetchone()[0]
            for name in self._tables(uow)
        }
        raw = [
            UUID(r[0])
            for r in uow.connection.execute(
                "SELECT package_id FROM platform_source_packages WHERE "
                "session_id=? ORDER BY package_id",
                (str(sid),),
            )
        ]
        artifacts = [
            UUID(r[0])
            for r in uow.connection.execute(
                "SELECT package_id FROM platform_artifact_staging WHERE "
                "session_id=? ORDER BY package_id",
                (str(sid),),
            )
        ]
        drafts = [
            UUID(r[0])
            for r in uow.connection.execute(
                "SELECT DISTINCT draft_id FROM platform_import_commits WHERE package_id IN "
                "(SELECT package_id FROM platform_source_packages WHERE session_id=?) "
                "ORDER BY draft_id",
                (str(sid),),
            )
        ]
        namespaces = {
            r[0]
            for r in uow.connection.execute(
                "SELECT DISTINCT namespace FROM platform_records WHERE session_id=?", (str(sid),)
            )
        }
        if any(
            n not in ("tracks", "source_events")
            and not any(n == p or n.startswith(p + ".") for p in self.namespaces)
            for n in namespaces
        ):
            raise ContractError("NOT_EVALUABLE")
        data = {
            "session_id": str(sid),
            "counts": counts,
            "raw_packages": list(map(str, raw)),
            "artifact_packages": list(map(str, artifacts)),
            "draft_ids": list(map(str, drafts)),
            "contents_hash": hashed(
                {
                    table: [
                        tuple(row)
                        for row in uow.connection.execute(
                            f"SELECT * FROM {table} WHERE session_id=? ORDER BY rowid",  # nosec B608
                            (str(sid),),
                        )
                    ]
                    for table in self._tables(uow)
                }
            ),
        }
        return Inventory.model_validate_json(json.dumps(data | {"inventory_hash": hashed(data)}))

    def preview(self, token: str, session_id: UUID) -> Inventory:
        with self.database.begin() as uow:
            self.permissions._admin(uow, token)
            return self._inventory(uow, session_id)

    def purge(
        self,
        token: str,
        session_id: UUID,
        *,
        reason: Literal["USER_REQUEST", "RETENTION_EXPIRED"],
        expected_inventory_hash: str,
        key: str,
    ) -> PurgeReceipt:
        if reason not in ("USER_REQUEST", "RETENTION_EXPIRED") or not re.fullmatch(
            r"[A-Za-z0-9_.:-]{1,128}", key
        ):
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            actor = self.permissions._admin(uow, token)
            old = uow.connection.execute(
                "SELECT * FROM platform_purges WHERE session_id=?", (str(session_id),)
            ).fetchone()
            if old:
                if (old["key_hash"], old["reason"], old["inventory_hash"]) != (
                    hashed(key),
                    reason,
                    expected_inventory_hash,
                ):
                    raise ContractError("IDEMPOTENCY_CONFLICT")
            else:
                inventory = self._inventory(uow, session_id)
                if inventory.inventory_hash != expected_inventory_hash:
                    raise ContractError("VERSION_CONFLICT")
                if (
                    reason == "RETENTION_EXPIRED"
                    and uow.connection.execute(
                        "SELECT 1 FROM platform_source_packages WHERE "
                        "session_id=? AND expires_ms>?",
                        (str(session_id), self.permissions.sessions.clock()),
                    ).fetchone()
                ):
                    raise ContractError("INVALID_INPUT")
                uow.connection.execute(
                    "INSERT INTO platform_purges VALUES (?,?,?,'PREPARED',?,?,?,?)",
                    (
                        str(session_id),
                        str(actor.id),
                        reason,
                        inventory.inventory_hash,
                        inventory.model_dump_json(),
                        hashed(key),
                        self.permissions.sessions.clock(),
                    ),
                )
                # Revoke delivery and cancel scheduling before erasure of sensitive payloads.
                uow.connection.execute(
                    "UPDATE platform_worker_scopes SET revoked=1 WHERE session_id=?",
                    (str(session_id),),
                )
                uow.connection.execute(
                    "UPDATE platform_job_state SET state='CANCELLED' WHERE "
                    "session_id=? AND state IN "
                    "('QUEUED','RETRY_WAIT','RUNNING')",
                    (str(session_id),),
                )
                self.pending.add(session_id)
                try:
                    uow.commit()
                except BaseException:
                    self.pending.discard(session_id)
                    raise
        self.pending.add(session_id)
        return self.resume(token, session_id)

    def resume(self, token: str, session_id: UUID) -> PurgeReceipt:
        with self.database.begin() as uow:
            self.permissions._admin(uow, token)
        return self._resume(session_id)

    def _resume(self, session_id: UUID) -> PurgeReceipt:
        with self.database.begin() as uow:
            plan = uow.connection.execute(
                "SELECT * FROM platform_purges WHERE session_id=?", (str(session_id),)
            ).fetchone()
            if plan is None:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if plan["state"] == "DONE":
                return PurgeReceipt(
                    session_id=session_id, state="DONE", inventory_hash=plan["inventory_hash"]
                )
            inventory = Inventory.model_validate_json(plan["payload"])
            revision = uow.connection.execute(
                "SELECT revision,input_hash FROM platform_revisions WHERE "
                "session_id=? ORDER BY revision DESC LIMIT 1",
                (str(session_id),),
            ).fetchone()
            ctx = RequestContext(
                actor_id=UUID(plan["actor_id"]),
                capabilities=["read", "analysis", "review", "admin"],
                session_id=session_id,
                analysis_run_id=None,
                input_revision=revision[0] if revision else 1,
                input_hash=revision[1] if revision else plan["inventory_hash"],
                as_of_ms=0,
                mode="DEBRIEF",
                request_id=uuid4(),
            )
        self.journal.record(session_id, plan["reason"], plan["inventory_hash"], plan["created_ms"])
        self.fault("after_marker")
        with self.database.begin() as uow:
            with uow.retention_writes(ctx):
                outside = self._outside_scope(uow, session_id)
                for callback in self.callbacks.values():
                    with uow.domain_writes():
                        callback(ctx, uow)
                    if self._outside_scope(uow, session_id) != outside:
                        raise ContractError("ACCESS_DENIED")
                self.fault("after_callbacks")
                if inventory.draft_ids and self.imports is None:
                    raise ContractError("NOT_EVALUABLE")
                for package in inventory.raw_packages:
                    self.assets.sources.files.remove(package)
                if inventory.artifact_packages and self.assets.artifacts is None:
                    raise ContractError("NOT_EVALUABLE")
                if self.assets.artifacts is not None:
                    for package in inventory.artifact_packages:
                        self.assets.artifacts.remove(package)
                if self.imports is not None:
                    for draft in inventory.draft_ids:
                        self.imports._remove(str(draft))
                    os.fsync(self.imports.root_fd)
                self.fault("after_files")
                tables = self._tables(uow)
                trigger_rows = list(
                    uow.connection.execute(
                        "SELECT name,sql,tbl_name FROM sqlite_master WHERE type='trigger'"
                    )
                )
                dropped = [
                    r
                    for r in trigger_rows
                    if r["tbl_name"]
                    in {*tables, "platform_import_commits", "platform_import_metadata"}
                ]
                for row in dropped:
                    uow.connection.execute(f'DROP TRIGGER "{row["name"]}"')
                uow.connection.execute("PRAGMA defer_foreign_keys=ON")
                run_ids = [
                    r[0]
                    for r in uow.connection.execute(
                        "SELECT id FROM platform_runs WHERE session_id=?", (str(session_id),)
                    )
                ]
                scopes = [
                    r[0]
                    for r in uow.connection.execute(
                        "SELECT id FROM platform_worker_scopes WHERE session_id=?",
                        (str(session_id),),
                    )
                ]
                for scope in scopes:
                    uow.connection.execute(
                        "DELETE FROM platform_context_receipts WHERE scope_id=?", (scope,)
                    )
                for run in run_ids:
                    uow.connection.execute(
                        "DELETE FROM platform_run_cancels WHERE run_id=?", (run,)
                    )
                for package in inventory.raw_packages:
                    uow.connection.execute(
                        "DELETE FROM platform_import_commits WHERE package_id=?", (str(package),)
                    )
                for draft in inventory.draft_ids:
                    uow.connection.execute(
                        "DELETE FROM platform_import_drafts WHERE id=?", (str(draft),)
                    )
                for table in tables:
                    uow.connection.execute(
                        f"DELETE FROM {table} WHERE session_id=?",  # nosec B608
                        (str(session_id),),
                    )
                for row in dropped:
                    uow.connection.execute(row["sql"])
                uow.connection.execute(
                    "UPDATE platform_purges SET state='DONE' WHERE session_id=?", (str(session_id),)
                )
                uow.audit(ctx, "PURGE_COMPLETED", session_id)
                if uow.connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Purge foreign-key invariant failed")
                self.fault("before_commit")
            uow.commit()
        self.pending.discard(session_id)
        return PurgeReceipt(
            session_id=session_id, state="DONE", inventory_hash=plan["inventory_hash"]
        )
