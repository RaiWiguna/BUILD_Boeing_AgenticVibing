"""Frozen ArtifactLifecycle over staged/accepted bytes. Rendering and redaction belong to B."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from flowlens.assets.access import Assets
from flowlens.contracts.models import ArtifactSubmission, RequestContext, Scoped
from flowlens.core.errors import ContractError
from flowlens.imports.staging import FilePreview
from flowlens.storage.sqlite.database import UnitOfWork


@dataclass(frozen=True)
class LocatedArtifact:
    artifact: ArtifactSubmission
    package_id: UUID
    file: FilePreview
    expires_ms: int


class ArtifactView(Scoped):
    artifact: ArtifactSubmission
    effective_expires_at: datetime
    media_type: str
    filename: str


class Artifacts:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.sources = assets.sources
        self.database = self.sources.database

    def submit(self, context: RequestContext, artifact: ArtifactSubmission) -> UUID:
        """Register an uploaded pending reference, never promote before accepted result commit."""
        staged, _, _ = self.assets.staged(context, artifact.id)
        if staged != artifact:
            raise ContractError("IDEMPOTENCY_CONFLICT")
        return artifact.id

    def _locate(self, uow: UnitOfWork, ctx: RequestContext, identifier: UUID) -> LocatedArtifact:
        self.sources.permissions.enforce(uow, ctx)
        if "worker" in ctx.capabilities:
            raise ContractError("ACCESS_DENIED")
        row = uow.connection.execute(
            "SELECT a.payload,a.storage_key,s.* FROM platform_artifacts a "
            "JOIN platform_artifact_staging s ON s.id=a.id AND "
            "s.session_id=a.session_id WHERE a.id=? AND a.session_id=? AND "
            "a.revision=? AND a.run_id IS ?",
            (
                str(identifier),
                str(ctx.session_id),
                ctx.input_revision,
                str(ctx.analysis_run_id) if ctx.analysis_run_id else None,
            ),
        ).fetchone()
        if (
            row is None
            or not row["accepted"]
            or row["expires_ms"] <= self.sources.permissions.sessions.clock()
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        spec = ArtifactSubmission.model_validate_json(row["payload"])
        if (
            spec.model_dump_json() != row["spec"]
            or row["storage_key"] != row["package_id"]
            or (spec.session_id, spec.analysis_run_id, spec.revision)
            != (ctx.session_id, ctx.analysis_run_id, ctx.input_revision)
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        ctx.require(spec.required_capability, ctx.session_id, ctx.analysis_run_id)
        ids = [
            UUID(r[0])
            for r in uow.connection.execute(
                "SELECT id FROM platform_sources WHERE session_id=? AND revision=?",
                (str(ctx.session_id), ctx.input_revision),
            )
        ]
        if not ids:
            raise ContractError("SOURCE_PERMISSION_REQUIRED")
        for source in ids:
            self.sources.permissions.require_source_rights(
                uow, ctx, source, export=True, audio_export=spec.kind == "AUDIO_DERIVATIVE"
            )
        file = FilePreview.model_validate_json(row["facts"])
        if file.id != spec.id or file.sha256 != spec.sha256 or file.size_bytes != spec.size_bytes:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        return LocatedArtifact(spec, UUID(row["package_id"]), file, row["expires_ms"])

    def metadata(self, context: RequestContext, identifier: UUID) -> ArtifactView:
        if self.assets.artifacts is None:
            raise ContractError("NOT_EVALUABLE")
        with self.database.begin() as uow:
            item = self._locate(uow, context, identifier)
            self.assets.artifacts.verify(item.package_id, item.artifact.sha256, [item.file])
            return ArtifactView(
                session_id=context.session_id,
                analysis_run_id=context.analysis_run_id,
                revision=context.input_revision,
                artifact=item.artifact,
                effective_expires_at=datetime.fromtimestamp(item.expires_ms / 1000, UTC),
                media_type=item.file.media_type,
                filename=item.file.filename,
            )

    def download(self, context: RequestContext, artifact_id: UUID) -> Iterator[bytes]:
        if self.assets.artifacts is None:
            raise ContractError("NOT_EVALUABLE")
        with self.database.begin() as uow:
            item = self._locate(uow, context, artifact_id)
            self.assets.artifacts.verify(item.package_id, item.artifact.sha256, [item.file])
            uow.audit(context, "ARTIFACT_DOWNLOAD", artifact_id)
            uow.commit()
        with self.assets.artifacts.open(item.package_id, item.file) as fd:
            while True:
                with self.database.begin() as uow:
                    self._locate(uow, context, artifact_id)
                block = os.read(fd, 65536)
                if not block:
                    break
                yield block

    def inventory(self, context: RequestContext) -> list[ArtifactSubmission]:
        with self.database.begin() as uow:
            self.sources.permissions.enforce(uow, context)
            context.require("read", context.session_id, context.analysis_run_id)
            rows = list(
                uow.connection.execute(
                    "SELECT a.id FROM platform_artifacts a JOIN platform_artifact_staging s "
                    "ON s.id=a.id AND s.session_id=a.session_id WHERE a.session_id=? "
                    "AND a.revision=? AND a.run_id IS ? AND s.accepted=1 "
                    "AND s.expires_ms>? ORDER BY a.id",
                    (
                        str(context.session_id),
                        context.input_revision,
                        str(context.analysis_run_id) if context.analysis_run_id else None,
                        self.sources.permissions.sessions.clock(),
                    ),
                )
            )
            return [self._locate(uow, context, UUID(row[0])).artifact for row in rows]

    def purge(self, context: RequestContext, uow: UnitOfWork) -> None:
        if uow.retention_context is not context or uow.domain_active:
            raise ContractError("ACCESS_DENIED")
        context.require("admin", context.session_id)
        rows = list(
            uow.connection.execute(
                "SELECT package_id FROM platform_artifact_staging WHERE session_id=?",
                (str(context.session_id),),
            )
        )
        if rows and self.assets.artifacts is None:
            raise ContractError("NOT_EVALUABLE")
        if self.assets.artifacts is not None:
            for row in rows:
                self.assets.artifacts.remove(UUID(row[0]))
        uow.connection.execute(
            "DELETE FROM platform_artifacts WHERE session_id=?", (str(context.session_id),)
        )
        uow.connection.execute(
            "DELETE FROM platform_artifact_staging WHERE session_id=?", (str(context.session_id),)
        )
