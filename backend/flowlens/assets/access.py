"""AssetAccess raw media port; current permissions are rechecked for each chunk."""

import json
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC
from uuid import UUID, uuid4

from flowlens.artifacts.profiles import REPORT_PROFILES
from flowlens.assets.storage import PrivateFiles
from flowlens.auth.permissions import context_digest
from flowlens.contracts.models import ArtifactSubmission, Asset, RequestContext
from flowlens.core.errors import ContractError
from flowlens.imports.inspection import InvalidContent, inspect_audio, strict_json
from flowlens.imports.metadata import PreparedImport
from flowlens.imports.staging import FilePreview, ImportFailure
from flowlens.sources.policy import policy
from flowlens.sources.store import Sources
from flowlens.storage.sqlite.database import UnitOfWork


@dataclass(frozen=True)
class LocatedAsset:
    asset: Asset
    package_id: UUID
    file: FilePreview


class Assets:
    def __init__(self, sources: Sources, artifacts: PrivateFiles | None = None) -> None:
        self.sources, self.artifacts = sources, artifacts
        self.worker_guard: Callable[[UnitOfWork, RequestContext], None] | None = None

    def locate(self, uow: UnitOfWork, context: RequestContext, asset_id: UUID) -> LocatedAsset:
        if "worker" in context.capabilities and self.worker_guard is not None:
            self.worker_guard(uow, context)
        asset = self.sources.permissions.authorize_asset(uow, context, asset_id)
        row = uow.connection.execute(
            "SELECT p.* FROM platform_source_packages p JOIN platform_assets a "
            "ON a.session_id=p.session_id AND a.source_id=p.source_id "
            "WHERE a.session_id=? AND a.id=?",
            (str(context.session_id), str(asset_id)),
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        self.sources.require_right(
            uow,
            context,
            UUID(row["source_id"]),
            "cloud_audio" if "worker" in context.capabilities else "local",
        )
        prepared = PreparedImport.model_validate_json(row["payload"])
        file = next((f for f in prepared.files if f.id == asset_id and f.role == "audio"), None)
        if file is None or file.sha256 != asset.sha256:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        return LocatedAsset(asset, UUID(row["package_id"]), file)

    def metadata(self, context: RequestContext, asset_id: UUID) -> LocatedAsset:
        with self.sources.database.begin() as uow:
            return self.locate(uow, context, asset_id)

    def stream(
        self, context: RequestContext, asset_id: UUID, start: int, end: int
    ) -> Iterator[bytes]:
        located = self.metadata(context, asset_id)
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= located.file.size_bytes
        ):
            raise ContractError("INVALID_INPUT")
        with self.sources.files.open(located.package_id, located.file) as fd:
            os.lseek(fd, start, os.SEEK_SET)
            remaining = end - start
            while remaining:
                self.metadata(context, asset_id)
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    raise ContractError("EVIDENCE_UNAVAILABLE")
                remaining -= len(chunk)
                yield chunk

    def download(self, context: RequestContext, asset_id: UUID, start: int, end: int) -> bytes:
        if end - start > 16 * 1024**2:
            raise ContractError("INVALID_INPUT")
        return b"".join(self.stream(context, asset_id, start, end))

    def _artifact_authority(
        self, uow: UnitOfWork, context: RequestContext, artifact: ArtifactSubmission
    ) -> UUID:
        if "worker" not in context.capabilities or (
            artifact.session_id,
            artifact.analysis_run_id,
            artifact.revision,
        ) != (context.session_id, context.analysis_run_id, context.input_revision):
            raise ContractError("ACCESS_DENIED")
        if artifact.kind != "AUDIO_DERIVATIVE":
            return self._report_authority(uow, context, artifact)
        if (
            artifact.kind != "AUDIO_DERIVATIVE"
            or artifact.required_capability != "audio"
            or artifact.source_asset_id is None
            or artifact.source_range is None
            or artifact.derivative_range is None
            or artifact.transform_version not in ("resample-1", "chunk-1")
        ):
            raise ContractError("INVALID_INPUT")
        parent = self.locate(uow, context, artifact.source_asset_id)
        if (
            artifact.source_range.end_ms > parent.asset.duration_ms
            or artifact.derivative_range.start_ms != 0
        ):
            raise ContractError("INVALID_INPUT")
        proof = uow.connection.execute(
            "SELECT scope_id FROM platform_context_receipts WHERE digest=?",
            (context_digest(context),),
        ).fetchone()
        return UUID(proof[0])

    def submit(
        self, context: RequestContext, artifact: ArtifactSubmission, chunks: Iterator[bytes]
    ) -> UUID:
        artifact = ArtifactSubmission.model_validate_json(artifact.model_dump_json())
        if artifact.kind != "AUDIO_DERIVATIVE":
            return self._submit_report(context, artifact, chunks)
        if self.artifacts is None:
            raise ContractError("NOT_EVALUABLE")
        if not 0 < artifact.size_bytes <= 64 * 1024**2:
            raise ContractError("INVALID_INPUT")
        with self.sources.database.begin() as uow:
            scope = self._artifact_authority(uow, context, artifact)
            old = uow.connection.execute(
                "SELECT * FROM platform_artifact_staging WHERE id=?", (str(artifact.id),)
            ).fetchone()
            if (
                old is None
                and uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_artifact_staging "
                    "WHERE worker_id=? AND accepted=0",
                    (str(context.actor_id),),
                ).fetchone()[0]
                >= 32
            ):
                raise ContractError("INVALID_INPUT")
        package = uuid4()
        file = FilePreview(
            id=artifact.id,
            role="audio",
            filename=f"{artifact.id}.wav",
            media_type="audio/wav",
            profile="derivative-audio-1",
            sha256=artifact.sha256,
            size_bytes=artifact.size_bytes,
        )
        self.artifacts.create(package)
        try:
            self.artifacts.write(package, file, chunks)
            with self.artifacts.open(package, file) as fd:
                magic = os.read(fd, 4)
                kind = "flac" if magic == b"fLaC" else "wav"
                try:
                    facts = inspect_audio(fd, kind, 7200000, 60)
                except InvalidContent as error:
                    raise ImportFailure(error.code, "artifact") from None
            data = file.model_dump(mode="json")
            data.update(
                filename=f"{artifact.id}.{kind}",
                media_type="audio/flac" if kind == "flac" else "audio/wav",
                **facts.model_dump(),
            )
            file = FilePreview.model_validate_json(json.dumps(data))
            if (
                artifact.derivative_range is None
                or artifact.source_range is None
                or abs(facts.duration_ms - artifact.derivative_range.end_ms) > 1
                or abs(
                    (artifact.source_range.end_ms - artifact.source_range.start_ms)
                    - facts.duration_ms
                )
                > 1
            ):
                raise ContractError("INVALID_INPUT")
            self.artifacts.seal(package, artifact.sha256, [file])
            with self.sources.database.begin() as uow:
                scope = self._artifact_authority(uow, context, artifact)
                if artifact.source_asset_id is None:
                    raise ContractError("INVALID_INPUT")
                parent = self.locate(uow, context, artifact.source_asset_id)
                if facts.channels != parent.asset.channels:
                    raise ContractError("INVALID_INPUT")
                source = uow.connection.execute(
                    "SELECT source_id FROM platform_assets WHERE session_id=? AND id=?",
                    (str(context.session_id), str(artifact.source_asset_id)),
                ).fetchone()
                current = policy(uow.connection, context.session_id, UUID(source[0]))
                if current is None:
                    raise ContractError("SOURCE_PERMISSION_REQUIRED")
                now = self.sources.permissions.sessions.clock()
                expires = min(now + 86400000, current.expires_ms)
                if artifact.expires_at is not None:
                    if artifact.expires_at.utcoffset() != UTC.utcoffset(artifact.expires_at):
                        raise ContractError("INVALID_INPUT")
                    declared = int(artifact.expires_at.timestamp() * 1000)
                    if not now < declared <= current.expires_ms:
                        raise ContractError("INVALID_INPUT")
                    expires = min(expires, declared)
                old = uow.connection.execute(
                    "SELECT * FROM platform_artifact_staging WHERE id=?", (str(artifact.id),)
                ).fetchone()
                if old is not None:
                    if (old["worker_id"], old["scope_id"], old["spec"]) != (
                        str(context.actor_id),
                        str(scope),
                        artifact.model_dump_json(),
                    ):
                        raise ContractError("IDEMPOTENCY_CONFLICT")
                else:
                    uow.connection.execute(
                        "INSERT INTO platform_artifact_staging VALUES (?,?,?,?,?,?,?,?,?,?,0)",
                        (
                            str(artifact.id),
                            str(context.session_id),
                            str(context.analysis_run_id),
                            context.input_revision,
                            str(context.actor_id),
                            str(scope),
                            str(package),
                            expires,
                            artifact.model_dump_json(),
                            file.model_dump_json(),
                        ),
                    )
                    uow.commit()
            return artifact.id
        finally:
            with self.sources.database.begin() as uow:
                durable = uow.connection.execute(
                    "SELECT 1 FROM platform_artifact_staging WHERE package_id=?", (str(package),)
                ).fetchone()
            if not durable:
                self.artifacts.remove(package)

    def staged(
        self, context: RequestContext, identifier: UUID
    ) -> tuple[ArtifactSubmission, FilePreview, UUID]:
        with self.sources.database.begin() as uow:
            return self.staged_in_uow(context, identifier, uow)

    def staged_in_uow(
        self, context: RequestContext, identifier: UUID, uow: UnitOfWork
    ) -> tuple[ArtifactSubmission, FilePreview, UUID]:
        if self.artifacts is None:
            raise ContractError("NOT_EVALUABLE")
        row = uow.connection.execute(
            "SELECT * FROM platform_artifact_staging WHERE id=?", (str(identifier),)
        ).fetchone()
        if row is None or row["expires_ms"] <= self.sources.permissions.sessions.clock():
            raise ContractError("EVIDENCE_UNAVAILABLE")
        artifact = ArtifactSubmission.model_validate_json(row["spec"])
        scope = self._artifact_authority(uow, context, artifact)
        if (str(context.actor_id), str(scope)) != (row["worker_id"], row["scope_id"]):
            raise ContractError("ACCESS_DENIED")
        file = FilePreview.model_validate_json(row["facts"])
        package = UUID(row["package_id"])
        self.artifacts.verify(package, artifact.sha256, [file])
        return artifact, file, package

    def recover_artifacts(self) -> None:
        if self.artifacts is None:
            return
        with self.sources.database.begin() as uow:
            rows = {
                UUID(r["package_id"]): r
                for r in uow.connection.execute("SELECT * FROM platform_artifact_staging")
            }
            for package, row in rows.items():
                if row["expires_ms"] <= self.sources.permissions.sessions.clock():
                    self.artifacts.remove(package)
                    if not row["accepted"]:
                        uow.connection.execute(
                            "DELETE FROM platform_artifact_staging WHERE id=?", (row["id"],)
                        )
                else:
                    self.artifacts.verify(
                        package,
                        ArtifactSubmission.model_validate_json(row["spec"]).sha256,
                        [FilePreview.model_validate_json(row["facts"])],
                    )
            for name in os.listdir(self.artifacts.fd):
                try:
                    identifier = UUID(name)
                except ValueError:
                    continue
                if str(identifier) == name and identifier not in rows:
                    self.artifacts.remove(identifier)
            uow.commit()

    def _report_authority(
        self, uow: UnitOfWork, ctx: RequestContext, spec: ArtifactSubmission
    ) -> UUID:
        self.sources.permissions.enforce(uow, ctx)
        profile = REPORT_PROFILES.get(spec.kind)
        if (
            profile is None
            or spec.required_capability != "export"
            or spec.transform_version != profile.transform_version
            or spec.source_asset_id is not None
            or spec.source_range is not None
            or spec.derivative_range is not None
            or not 0 < spec.size_bytes <= profile.max_bytes
        ):
            raise ContractError("INVALID_INPUT")
        proof = uow.connection.execute(
            "SELECT scope_id FROM platform_context_receipts WHERE digest=?", (context_digest(ctx),)
        ).fetchone()
        if "worker" not in ctx.capabilities or proof is None or proof[0] is None:
            raise ContractError("ACCESS_DENIED")
        row = uow.connection.execute(
            "SELECT r.creator_id,j.stage FROM platform_attempt_state a JOIN "
            "platform_job_state j ON j.id=a.job_id JOIN platform_run_state r "
            "ON r.id=j.run_id WHERE a.scope_id=? AND a.state='ACTIVE'",
            (proof[0],),
        ).fetchone()
        if row is None or row["stage"] != "EXPORT":
            raise ContractError("ACCESS_DENIED")
        capabilities = self.sources.permissions._capabilities(
            uow, UUID(row["creator_id"]), ctx.session_id, "AS_KNOWN"
        )
        if "export" not in capabilities:
            raise ContractError("ACCESS_DENIED")
        ids = [
            UUID(r[0])
            for r in uow.connection.execute(
                "SELECT id FROM platform_sources WHERE session_id=? AND revision=?",
                (str(ctx.session_id), ctx.input_revision),
            )
        ]
        if not ids:
            raise ContractError("SOURCE_PERMISSION_REQUIRED")
        for identifier in ids:
            manifest = self.sources.permissions.require_source_rights(uow, ctx, identifier)
            current = policy(uow.connection, ctx.session_id, identifier)
            if (
                current is None
                or current.expires_ms <= self.sources.permissions.sessions.clock()
                or not manifest.permissions.export
            ):
                raise ContractError("SOURCE_PERMISSION_REQUIRED")
            current.rights.require("export")
        return UUID(proof[0])

    def _submit_report(
        self, ctx: RequestContext, spec: ArtifactSubmission, chunks: Iterator[bytes]
    ) -> UUID:
        if self.artifacts is None:
            raise ContractError("NOT_EVALUABLE")
        with self.sources.database.begin() as uow:
            scope = self._artifact_authority(uow, ctx, spec)
            if (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_artifact_staging WHERE "
                    "worker_id=? AND accepted=0",
                    (str(ctx.actor_id),),
                ).fetchone()[0]
                >= 32
            ):
                old = uow.connection.execute(
                    "SELECT id FROM platform_artifact_staging WHERE id=?", (str(spec.id),)
                ).fetchone()
                if old is None:
                    raise ContractError("INVALID_INPUT")
        profile = REPORT_PROFILES[spec.kind]
        package = uuid4()
        file = FilePreview(
            id=spec.id,
            role="events",
            filename=f"{spec.id}.{profile.extension}",
            media_type=profile.media_type,
            profile=profile.transform_version,
            sha256=spec.sha256,
            size_bytes=spec.size_bytes,
        )
        self.artifacts.create(package)
        try:
            self.artifacts.write(package, file, chunks)
            with self.artifacts.open(package, file) as fd:
                pieces = []
                while block := os.read(fd, 65536):
                    pieces.append(block)
                try:
                    text = b"".join(pieces).decode("utf-8")
                    if "\x00" in text:
                        raise ValueError("NUL in report container")
                    if spec.kind == "JSON_REPORT":
                        if not isinstance(strict_json(text), dict):
                            raise ValueError("Report JSON object required")
                except (UnicodeError, InvalidContent, ValueError):
                    raise ImportFailure("INVALID_ARTIFACT") from None
            self.artifacts.seal(package, spec.sha256, [file])
            with self.sources.database.begin() as uow:
                scope = self._artifact_authority(uow, ctx, spec)
                now = self.sources.permissions.sessions.clock()
                expiries: list[int] = []
                for row in uow.connection.execute(
                    "SELECT id FROM platform_sources WHERE session_id=? AND revision=?",
                    (str(ctx.session_id), ctx.input_revision),
                ):
                    current = policy(uow.connection, ctx.session_id, UUID(row[0]))
                    if current is None:
                        raise ContractError("SOURCE_PERMISSION_REQUIRED")
                    expiries.append(current.expires_ms)
                expires = min(now + 86400000, *expiries)
                if spec.expires_at is not None:
                    if spec.expires_at.utcoffset() != UTC.utcoffset(spec.expires_at):
                        raise ContractError("INVALID_INPUT")
                    declared = int(spec.expires_at.timestamp() * 1000)
                    if not now < declared <= min(expiries):
                        raise ContractError("INVALID_INPUT")
                    expires = min(expires, declared)
                old = uow.connection.execute(
                    "SELECT * FROM platform_artifact_staging WHERE id=?", (str(spec.id),)
                ).fetchone()
                if old is not None:
                    if (old["worker_id"], old["scope_id"], old["spec"]) != (
                        str(ctx.actor_id),
                        str(scope),
                        spec.model_dump_json(),
                    ):
                        raise ContractError("IDEMPOTENCY_CONFLICT")
                else:
                    uow.connection.execute(
                        "INSERT INTO platform_artifact_staging VALUES (?,?,?,?,?,?,?,?,?,?,0)",
                        (
                            str(spec.id),
                            str(ctx.session_id),
                            str(ctx.analysis_run_id),
                            ctx.input_revision,
                            str(ctx.actor_id),
                            str(scope),
                            str(package),
                            expires,
                            spec.model_dump_json(),
                            file.model_dump_json(),
                        ),
                    )
                    uow.commit()
            return spec.id
        finally:
            with self.sources.database.begin() as uow:
                durable = uow.connection.execute(
                    "SELECT 1 FROM platform_artifact_staging WHERE package_id=?", (str(package),)
                ).fetchone()
            if not durable:
                self.artifacts.remove(package)
