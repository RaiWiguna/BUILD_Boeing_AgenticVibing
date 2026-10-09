"""SourceReader port backed by committed observations, never private evaluator input."""

from uuid import UUID

from flowlens.assets.storage import PrivateFiles
from flowlens.auth.permissions import Permissions, context_digest
from flowlens.contracts.models import RequestContext, SourceEvent, SourceManifest, Track
from flowlens.core.errors import ContractError
from flowlens.sources.metadata import Action, RightsProfile
from flowlens.sources.policy import policy
from flowlens.storage.sqlite.database import Database, UnitOfWork


class Sources:
    def __init__(self, database: Database, permissions: Permissions, files: PrivateFiles) -> None:
        self.database, self.permissions, self.files = database, permissions, files

    def require_right(
        self, uow: UnitOfWork, context: RequestContext, source: UUID, action: Action
    ) -> None:
        self.permissions.enforce(uow, context)
        context.require(
            "export" if action in ("export", "audio_export") else "read", context.session_id
        )
        self.permissions.require_source_rights(uow, context, source)
        current = policy(uow.connection, context.session_id, source)
        if current is None or current.expires_ms <= self.permissions.sessions.clock():
            raise ContractError("SOURCE_PERMISSION_REQUIRED")
        current.rights.require(action)

    def manifest(self, context: RequestContext, source_id: UUID) -> SourceManifest:
        with self.database.begin() as uow:
            self.require_right(
                uow,
                context,
                source_id,
                "cloud_context" if "worker" in context.capabilities else "reviewer",
            )
            manifest = self.permissions.require_source_rights(uow, context, source_id)
            if "worker" in context.capabilities:
                proof = uow.connection.execute(
                    "SELECT scope_id FROM platform_context_receipts WHERE digest=?",
                    (context_digest(context),),
                ).fetchone()
                allowed = {
                    row[0]
                    for row in uow.connection.execute(
                        "SELECT asset_id FROM platform_worker_assets WHERE scope_id=?", (proof[0],)
                    )
                }
                manifest = SourceManifest.model_validate_json(
                    manifest.model_copy(
                        update={"assets": [a for a in manifest.assets if str(a.id) in allowed]}
                    ).model_dump_json()
                )
            return manifest

    def read_events(self, context: RequestContext) -> list[SourceEvent]:
        with self.database.begin() as uow:
            self.permissions.enforce(uow, context)
            source_ids = [
                UUID(r[0])
                for r in uow.connection.execute(
                    "SELECT id FROM platform_sources WHERE session_id=? AND revision=?",
                    (str(context.session_id), context.input_revision),
                )
            ]
            for source in source_ids:
                self.require_right(
                    uow,
                    context,
                    source,
                    "cloud_context" if "worker" in context.capabilities else "reviewer",
                )
            rows = uow.connection.execute(
                "SELECT kind,payload FROM platform_records WHERE session_id=? AND revision=? "
                "AND run_id IS NULL AND namespace IN ('source_events','tracks')",
                (str(context.session_id), context.input_revision),
            )
            events = [
                (Track if r["kind"] == "Track" else SourceEvent).model_validate_json(r["payload"])
                for r in rows
            ]
            return sorted(
                [
                    e
                    for e in events
                    if e.event_time_ms <= context.as_of_ms
                    and (
                        context.mode == "DEBRIEF"
                        or (
                            e.available_time_ms is not None
                            and e.available_time_ms <= context.as_of_ms
                        )
                    )
                ],
                key=lambda e: (e.event_time_ms, str(e.id)),
            )

    def tracks(self, context: RequestContext, entity_id: UUID) -> list[Track]:
        return [
            e
            for e in self.read_events(context)
            if isinstance(e, Track) and e.entity_id == entity_id
        ]

    def set_rights(
        self,
        admin_token: str,
        session_id: UUID,
        source_id: UUID,
        rights: RightsProfile,
        *,
        expected_version: int,
    ) -> int:
        rights = RightsProfile.model_validate_json(rights.model_dump_json())
        with self.database.begin() as uow:
            actor = self.permissions._admin(uow, admin_token)
            package = uow.connection.execute(
                "SELECT owner_id FROM platform_source_packages WHERE session_id=? AND source_id=?",
                (str(session_id), str(source_id)),
            ).fetchone()
            if package is None or package[0] != str(actor.id):
                raise ContractError("ACCESS_DENIED")
            version = uow.connection.execute(
                "SELECT MAX(version) FROM platform_source_rights "
                "WHERE session_id=? AND source_id=?",
                (str(session_id), str(source_id)),
            ).fetchone()[0]
            if version != expected_version:
                raise ContractError("VERSION_CONFLICT")
            uow.connection.execute(
                "INSERT INTO platform_source_rights VALUES (?,?,?,?,?,?)",
                (
                    str(session_id),
                    str(source_id),
                    version + 1,
                    str(actor.id),
                    self.permissions.sessions.clock(),
                    rights.model_dump_json(),
                ),
            )
            self.permissions._audit(uow, actor.id, source_id, "SOURCE_RIGHTS_CHANGE")
            uow.commit()
            return int(version) + 1
