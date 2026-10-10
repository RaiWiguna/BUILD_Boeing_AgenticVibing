"""API-owned authorization. Context DTOs carry scope, never authorization authority."""

import hashlib
import secrets
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID, uuid4

from flowlens.auth.accounts import Account
from flowlens.auth.sessions import Sessions, token_hash
from flowlens.contracts.models import Asset, Capability, RequestContext, SourceManifest
from flowlens.core.errors import ContractError
from flowlens.sources.policy import policy
from flowlens.storage.sqlite.database import Database, UnitOfWork
from pydantic import SecretStr, ValidationError

Role = Literal["observer", "controller", "evaluator"]
ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    "observer": frozenset({"read", "audio"}),
    "controller": frozenset({"read", "audio", "review"}),
    "evaluator": frozenset({"read", "audio", "review", "analysis", "export", "truth"}),
}


@dataclass(frozen=True)
class WorkerCredential:
    id: UUID
    token: SecretStr
    expires_ms: int


def worker_hash(token: str) -> str:
    if not token.startswith("wrk_"):
        raise ContractError("AUTH_REQUIRED")
    return token_hash(token[4:])


def context_digest(context: RequestContext) -> str:
    return hashlib.sha256(context.model_dump_json().encode()).hexdigest()


class Permissions:
    def __init__(self, database: Database, sessions: Sessions) -> None:
        self.database = database
        self.sessions = sessions
        self.worker_guard: Callable[[UnitOfWork, RequestContext], None] | None = None
        self.deny_session: Callable[[UUID], bool] | None = None

    def _admin(self, uow: UnitOfWork, token: str) -> Account:
        actor = self.sessions.authenticate(uow, token_hash(token))
        if not actor.is_admin:
            raise ContractError("ACCESS_DENIED")
        return actor

    def _audit(self, uow: UnitOfWork, actor: UUID, target: UUID, action: str) -> None:
        uow.connection.execute(
            "INSERT INTO platform_permission_audit(actor_id,target_id,action,recorded_ms) "
            "VALUES (?,?,?,?)",
            (str(actor), str(target), action, self.sessions.clock()),
        )

    def grant(
        self,
        admin_token: str,
        account_id: UUID,
        session_id: UUID,
        capability: Capability,
        *,
        role: Role,
        expires_ms: int,
    ) -> None:
        if capability not in ROLE_CAPABILITIES.get(role, ()) or expires_ms <= self.sessions.clock():
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            admin = self._admin(uow, admin_token)
            target = uow.connection.execute(
                "SELECT active FROM platform_accounts WHERE id=?",
                (str(account_id),),
            ).fetchone()
            exists = uow.connection.execute(
                "SELECT id FROM platform_sessions WHERE id=?",
                (str(session_id),),
            ).fetchone()
            if target is None or not target["active"] or exists is None:
                raise ContractError("ACCESS_DENIED")
            uow.connection.execute(
                "INSERT INTO platform_grants VALUES (?,?,?,?,?,0) "
                "ON CONFLICT(account_id,session_id,capability) DO UPDATE SET "
                "role=excluded.role,expires_ms=excluded.expires_ms,revoked=0",
                (str(account_id), str(session_id), capability, role, expires_ms),
            )
            self._audit(uow, admin.id, account_id, "GRANT")
            uow.commit()

    def revoke(
        self,
        admin_token: str,
        account_id: UUID,
        session_id: UUID,
        capability: Capability,
    ) -> None:
        with self.database.begin() as uow:
            admin = self._admin(uow, admin_token)
            uow.connection.execute(
                "UPDATE platform_grants SET revoked=1 "
                "WHERE account_id=? AND session_id=? AND capability=?",
                (str(account_id), str(session_id), capability),
            )
            self._audit(uow, admin.id, account_id, "REVOKE_GRANT")
            uow.commit()

    def _capabilities(
        self,
        uow: UnitOfWork,
        actor: UUID,
        session: UUID,
        mode: str,
    ) -> list[Capability]:
        rows = uow.connection.execute(
            "SELECT * FROM platform_grants WHERE account_id=? AND session_id=? "
            "AND revoked=0 AND expires_ms>?",
            (str(actor), str(session), self.sessions.clock()),
        ).fetchall()
        # Legacy grants without expiry and invalid role/capability combinations fail closed.
        allowed = {
            row["capability"]
            for row in rows
            if row["capability"] in ROLE_CAPABILITIES.get(row["role"], ())
            and (row["capability"] != "truth" or mode == "DEBRIEF")
        }
        if "read" not in allowed:
            raise ContractError("ACCESS_DENIED")
        return cast(list[Capability], sorted(allowed))

    def _input(self, uow: UnitOfWork, session: UUID, run: UUID | None) -> sqlite3.Row:
        if self.deny_session is not None and self.deny_session(session):
            raise ContractError("ACCESS_DENIED")
        latest = uow.connection.execute(
            "SELECT * FROM platform_revisions WHERE session_id=? ORDER BY revision DESC LIMIT 1",
            (str(session),),
        ).fetchone()
        if latest is None:
            raise ContractError("ACCESS_DENIED")
        if run is not None:
            row = uow.connection.execute(
                "SELECT revision FROM platform_runs WHERE session_id=? AND id=?",
                (str(session), str(run)),
            ).fetchone()
            if row is None:
                raise ContractError("ACCESS_DENIED")
            if row["revision"] != latest["revision"]:
                raise ContractError("SOURCE_REVISION_CHANGED")
        return cast(sqlite3.Row, latest)

    def _state(self, uow: UnitOfWork, session: UUID) -> sqlite3.Row:
        row = uow.connection.execute(
            "SELECT * FROM platform_context_state WHERE session_id=?",
            (str(session),),
        ).fetchone()
        if row is None:
            raise ContractError("NOT_EVALUABLE")
        return cast(sqlite3.Row, row)

    def _receipt(
        self,
        uow: UnitOfWork,
        context: RequestContext,
        kind: str,
        digest: str,
        scope: UUID | None = None,
    ) -> None:
        now = self.sessions.clock()
        uow.connection.execute("DELETE FROM platform_context_receipts WHERE expires_ms<=?", (now,))
        # Short-lived proof binds every field; live credentials/grants are still checked on use.
        uow.connection.execute(
            "INSERT INTO platform_context_receipts VALUES (?,?,?,?,?,?)",
            (
                context_digest(context),
                kind,
                digest,
                str(scope) if scope else None,
                now,
                now + 300000,
            ),
        )

    def human_context(
        self,
        token: str,
        session_id: UUID,
        *,
        run_id: UUID | None = None,
        required: Capability = "read",
    ) -> RequestContext:
        digest = token_hash(token)
        with self.database.begin() as uow:
            actor = self.sessions.authenticate(uow, digest)
            state = self._state(uow, session_id)
            capabilities = self._capabilities(uow, actor.id, session_id, state["mode"])
            if required not in capabilities:
                raise ContractError("ACCESS_DENIED")
            revision = self._input(uow, session_id, run_id)
            ctx = RequestContext(
                actor_id=actor.id,
                capabilities=capabilities,
                session_id=session_id,
                analysis_run_id=run_id,
                input_revision=revision["revision"],
                input_hash=revision["input_hash"],
                as_of_ms=state["as_of_ms"],
                mode=state["mode"],
                request_id=uuid4(),
            )
            self._receipt(uow, ctx, "HUMAN", digest)
            uow.connection.execute(
                "UPDATE platform_auth_sessions SET last_seen_ms=? WHERE token_hash=?",
                (self.sessions.clock(), digest),
            )
            uow.commit()
        return ctx

    def provision_worker(self, admin_token: str, *, expires_ms: int) -> WorkerCredential:
        """Trusted provisioning only; never registered as a public browser endpoint."""
        if expires_ms <= self.sessions.clock():
            raise ContractError("INVALID_INPUT")
        identifier, token = uuid4(), "wrk_" + secrets.token_urlsafe(32)
        with self.database.begin() as uow:
            admin = self._admin(uow, admin_token)
            uow.connection.execute(
                "INSERT INTO platform_workers VALUES (?,?,?,0)",
                (str(identifier), worker_hash(token), expires_ms),
            )
            self._audit(uow, admin.id, identifier, "PROVISION_WORKER")
            uow.commit()
        return WorkerCredential(identifier, SecretStr(token), expires_ms)

    def authenticate_worker(self, token: str) -> UUID:
        """Principal check only; scoped jobs/assets still require worker_context and a lease."""
        with self.database.begin() as uow:
            row = uow.connection.execute(
                "SELECT * FROM platform_workers WHERE token_hash=?", (worker_hash(token),)
            ).fetchone()
            if row is None or row["revoked"] or self.sessions.clock() >= row["expires_ms"]:
                raise ContractError("AUTH_REQUIRED")
            return UUID(row["id"])

    def revoke_worker(self, admin_token: str, worker_id: UUID) -> None:
        with self.database.begin() as uow:
            admin = self._admin(uow, admin_token)
            uow.connection.execute(
                "UPDATE platform_workers SET revoked=1 WHERE id=?", (str(worker_id),)
            )
            self._audit(uow, admin.id, worker_id, "REVOKE_WORKER")
            uow.commit()

    def bind_worker(
        self,
        admin_token: str,
        worker_id: UUID,
        session_id: UUID,
        run_id: UUID,
        *,
        expires_ms: int,
        source_ids: tuple[UUID, ...] = (),
        asset_ids: tuple[UUID, ...] = (),
    ) -> UUID:
        """Bind trusted coordinator context; lease lifecycle is supplied by A06."""
        identifier = uuid4()
        with self.database.begin() as uow:
            admin = self._admin(uow, admin_token)
            caps = self._capabilities(uow, admin.id, session_id, "AS_KNOWN")
            if "analysis" not in caps:
                raise ContractError("ACCESS_DENIED")
            revision = self._input(uow, session_id, run_id)
            state = self._state(uow, session_id)
            worker = uow.connection.execute(
                "SELECT * FROM platform_workers WHERE id=?", (str(worker_id),)
            ).fetchone()
            if (
                worker is None
                or worker["revoked"]
                or not self.sessions.clock() < expires_ms <= worker["expires_ms"]
            ):
                raise ContractError("ACCESS_DENIED")
            uow.connection.execute(
                "INSERT INTO platform_worker_scopes VALUES (?,?,?,?,?,?,?,0)",
                (
                    str(identifier),
                    str(worker_id),
                    str(session_id),
                    str(run_id),
                    revision["revision"],
                    state["as_of_ms"],
                    expires_ms,
                ),
            )
            if len(source_ids) > 100 or len(asset_ids) > 100:
                raise ContractError("INVALID_INPUT")
            sources = set(source_ids)
            for asset_id in set(asset_ids):
                asset = uow.connection.execute(
                    "SELECT source_id,revision FROM platform_assets WHERE session_id=? AND id=?",
                    (str(session_id), str(asset_id)),
                ).fetchone()
                if asset is None or asset["revision"] != revision["revision"]:
                    raise ContractError("ACCESS_DENIED")
                sources.add(UUID(asset["source_id"]))
                uow.connection.execute(
                    "INSERT INTO platform_worker_assets VALUES (?,?,?)",
                    (str(identifier), str(session_id), str(asset_id)),
                )
            for source_id in sources:
                source = uow.connection.execute(
                    "SELECT id FROM platform_sources WHERE session_id=? AND id=? AND revision=?",
                    (str(session_id), str(source_id), revision["revision"]),
                ).fetchone()
                if source is None:
                    raise ContractError("ACCESS_DENIED")
                uow.connection.execute(
                    "INSERT INTO platform_worker_sources VALUES (?,?,?,?)",
                    (str(identifier), str(session_id), str(source_id), revision["revision"]),
                )
            self._audit(uow, admin.id, identifier, "BIND_WORKER")
            uow.commit()
        return identifier

    def revoke_scope(self, admin_token: str, scope_id: UUID) -> None:
        with self.database.begin() as uow:
            admin = self._admin(uow, admin_token)
            uow.connection.execute(
                "UPDATE platform_worker_scopes SET revoked=1 WHERE id=?", (str(scope_id),)
            )
            self._audit(uow, admin.id, scope_id, "REVOKE_WORKER_SCOPE")
            uow.commit()

    def _worker(self, uow: UnitOfWork, digest: str, scope_id: UUID) -> sqlite3.Row:
        row = uow.connection.execute(
            "SELECT s.*,w.token_hash,w.expires_ms AS worker_expires,w.revoked AS worker_revoked "
            "FROM platform_worker_scopes s JOIN platform_workers w ON w.id=s.worker_id "
            "WHERE s.id=? AND w.token_hash=?",
            (str(scope_id), digest),
        ).fetchone()
        now = self.sessions.clock()
        if (
            row is None
            or row["revoked"]
            or row["worker_revoked"]
            or now >= min(row["expires_ms"], row["worker_expires"])
        ):
            raise ContractError("AUTH_REQUIRED")
        return cast(sqlite3.Row, row)

    def worker_context(self, token: str, scope_id: UUID) -> RequestContext:
        digest = worker_hash(token)
        with self.database.begin() as uow:
            scope = self._worker(uow, digest, scope_id)
            sid, run = UUID(scope["session_id"]), UUID(scope["run_id"])
            revision = self._input(uow, sid, run)
            if revision["revision"] != scope["revision"]:
                raise ContractError("SOURCE_REVISION_CHANGED")
            ctx = RequestContext(
                actor_id=UUID(scope["worker_id"]),
                capabilities=["read", "analysis", "worker"],
                session_id=sid,
                analysis_run_id=run,
                input_revision=revision["revision"],
                input_hash=revision["input_hash"],
                as_of_ms=scope["as_of_ms"],
                mode="AS_KNOWN",
                request_id=uuid4(),
            )
            self._receipt(uow, ctx, "WORKER", digest, scope_id)
            uow.commit()
        return ctx

    def enforce(self, uow: UnitOfWork, context: RequestContext) -> None:
        uow.check_open()
        if uow.retention_context is context:
            context.require("admin", context.session_id)
            return
        proof = uow.connection.execute(
            "SELECT * FROM platform_context_receipts WHERE digest=? AND expires_ms>?",
            (context_digest(context), self.sessions.clock()),
        ).fetchone()
        if proof is None or self.sessions.clock() < proof["created_ms"]:
            raise ContractError("ACCESS_DENIED")
        if proof["principal_kind"] == "HUMAN":
            actor = self.sessions.authenticate(uow, proof["credential_hash"])
            caps = self._capabilities(uow, actor.id, context.session_id, context.mode)
            if actor.id != context.actor_id or not set(context.capabilities) <= set(caps):
                raise ContractError("ACCESS_DENIED")
        else:
            scope = self._worker(uow, proof["credential_hash"], UUID(proof["scope_id"]))
            if (
                (
                    scope["worker_id"],
                    scope["session_id"],
                    scope["run_id"],
                    scope["revision"],
                    scope["as_of_ms"],
                )
                != (
                    str(context.actor_id),
                    str(context.session_id),
                    str(context.analysis_run_id),
                    context.input_revision,
                    context.as_of_ms,
                )
                or context.mode != "AS_KNOWN"
                or set(context.capabilities) != {"read", "analysis", "worker"}
            ):
                raise ContractError("ACCESS_DENIED")
        revision = self._input(uow, context.session_id, context.analysis_run_id)
        if (revision["revision"], revision["input_hash"]) != (
            context.input_revision,
            context.input_hash,
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")

        if "worker" in context.capabilities and self.worker_guard is not None:
            self.worker_guard(uow, context)

    def require_source_rights(
        self,
        uow: UnitOfWork,
        context: RequestContext,
        source_id: UUID,
        *,
        cloud: bool = False,
        export: bool = False,
        audio_export: bool = False,
    ) -> SourceManifest:
        """Scoped rights check for future asset/tool/coordinator routes; no inventory API."""
        self.enforce(uow, context)
        context.require("export" if export or audio_export else "read", context.session_id)
        if audio_export:
            context.require("audio", context.session_id)
        if "worker" in context.capabilities:
            proof = uow.connection.execute(
                "SELECT scope_id FROM platform_context_receipts WHERE digest=?",
                (context_digest(context),),
            ).fetchone()
            permitted = uow.connection.execute(
                "SELECT 1 FROM platform_worker_sources WHERE scope_id=? AND source_id=?",
                (proof["scope_id"], str(source_id)),
            ).fetchone()
            if permitted is None:
                raise ContractError("ACCESS_DENIED")
        row = uow.connection.execute(
            "SELECT * FROM platform_sources WHERE session_id=? AND id=? AND revision=?",
            (str(context.session_id), str(source_id), context.input_revision),
        ).fetchone()
        if row is None:
            raise ContractError("SOURCE_PERMISSION_REQUIRED")
        try:
            manifest = SourceManifest.model_validate_json(row["payload"])
        except ValidationError:
            raise ContractError("SOURCE_PERMISSION_REQUIRED") from None
        if (manifest.id, manifest.session_id, manifest.revision, manifest.source_hash) != (
            source_id,
            context.session_id,
            context.input_revision,
            row["source_hash"],
        ) or not manifest.permissions.local:
            raise ContractError("SOURCE_PERMISSION_REQUIRED")
        current = policy(uow.connection, context.session_id, source_id)
        if current is not None:
            if current.expires_ms <= self.sessions.clock():
                raise ContractError("SOURCE_PERMISSION_REQUIRED")
            current.rights.require("local")
            if "worker" not in context.capabilities:
                current.rights.require("reviewer")
            if cloud:
                current.rights.require("cloud_audio")
                current.rights.require("cloud_context")
            if export:
                current.rights.require("export")
            if audio_export:
                current.rights.require("audio_export")
        if cloud and ("analysis" not in context.capabilities or not manifest.permissions.cloud):
            raise ContractError("CLOUD_TRANSFER_BLOCKED")
        if ((export or audio_export) and not manifest.permissions.export) or (
            audio_export and not manifest.permissions.audio_export
        ):
            raise ContractError("SOURCE_PERMISSION_REQUIRED")
        return manifest

    def authorize_asset(
        self,
        uow: UnitOfWork,
        context: RequestContext,
        asset_id: UUID,
    ) -> Asset:
        """Authorize one asset; return metadata without revealing private storage keys."""
        self.enforce(uow, context)
        if "worker" in context.capabilities:
            proof = uow.connection.execute(
                "SELECT scope_id FROM platform_context_receipts WHERE digest=?",
                (context_digest(context),),
            ).fetchone()
            allowed = uow.connection.execute(
                "SELECT 1 FROM platform_worker_assets WHERE scope_id=? AND asset_id=?",
                (proof["scope_id"], str(asset_id)),
            ).fetchone()
            if allowed is None:
                raise ContractError("ACCESS_DENIED")
        else:
            context.require("audio", context.session_id)
        row = uow.connection.execute(
            "SELECT * FROM platform_assets WHERE session_id=? AND id=? AND revision=?",
            (str(context.session_id), str(asset_id), context.input_revision),
        ).fetchone()
        if row is None:
            raise ContractError("ACCESS_DENIED")
        manifest = self.require_source_rights(uow, context, UUID(row["source_id"]))
        for asset in manifest.assets:
            if asset.id == asset_id and asset.sha256 == row["sha256"]:
                return asset.model_copy(update={"fixture_path": None})
        raise ContractError("SOURCE_PERMISSION_REQUIRED")
