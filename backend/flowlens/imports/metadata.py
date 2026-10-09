"""Immutable, scoped draft metadata revisions. Never commit a source/session here."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID, uuid5

from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import Asset, ClockMapping, Coverage, Permissions, SourceManifest
from flowlens.core.errors import ContractError
from flowlens.imports.normalization import NormalizationSummary, scan
from flowlens.imports.staging import FilePreview, ImportFailure, ImportPreview, Imports, Issue
from flowlens.sources.metadata import Action, Declaration, Layout
from flowlens.storage.sqlite.database import UnitOfWork
from pydantic import Field, model_validator


def hashed(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def content_hash(files: list[FilePreview]) -> str:
    return hashed(
        sorted(
            [file.model_dump(mode="json", exclude={"id"}) for file in files],
            key=lambda x: (x["role"], x["filename"]),
        )
    )


class MetadataRequest(MetadataModel):
    expected_revision: Annotated[int, Field(ge=0, le=63)]
    declaration: Declaration


class IdentityMapping(MetadataModel):
    source_entity_id: str
    entity_id: UUID
    callsign: str
    aliases: list[str]


class PreparedImport(MetadataModel):
    profile_version: Literal["prepared-import-1"] = "prepared-import-1"
    id: UUID
    revision: Annotated[int, Field(ge=1, le=64)]
    declared_at: datetime
    declaration: Declaration
    files: list[FilePreview]
    content_hash: str
    declaration_hash: str
    manifest_hash: str
    manifest: SourceManifest | None
    layout: Layout | None
    identities: list[IdentityMapping]
    normalizations: list[NormalizationSummary]
    paired_status: Literal["METADATA_COMPLETE", "NOT_EVALUABLE"]
    alignment_status: Literal["KNOWN", "UNKNOWN"]
    locally_eligible: bool
    cloud_audio_eligible: bool
    cloud_context_eligible: bool
    status: Literal["PREPARED", "NEEDS_REMEDIATION"]
    issues: list[Issue]

    @model_validator(mode="after")
    def hashes_match(self) -> Self:
        if (offset := self.declared_at.utcoffset()) is None or offset.total_seconds() != 0:
            raise ValueError("Server declaration time must be UTC")
        if (
            self.content_hash != content_hash(self.files)
            or self.declaration_hash != hashed(self.declaration.model_dump(mode="json"))
            or self.manifest_hash != hashed(self.model_dump(mode="json", exclude={"manifest_hash"}))
        ):
            raise ValueError("Metadata hash mismatch")
        return self

    def require_right(self, action: Action) -> None:
        self.declaration.rights.require(action)
        if self.declaration.retention.days is None:
            raise ContractError("SOURCE_PERMISSION_REQUIRED")


def validate_bindings(preview: ImportPreview, declaration: Declaration) -> None:
    given = {item.file_id: item for item in declaration.files}
    if set(given) != {item.id for item in preview.files}:
        raise ImportFailure("FILE_BINDING_MISMATCH", "files")
    for file in preview.files:
        item = given[file.id]
        if item.sha256 != file.sha256:
            raise ImportFailure("HASH_MISMATCH", "files")
        if len(item.channels) != (file.channels or 0) or len(set(item.channels)) != len(
            item.channels
        ):
            raise ImportFailure("CHANNEL_LABEL_MISMATCH", "channels")
        if file.duration_ms is not None:
            item.clock.to_session_ms(0)
            item.clock.to_session_ms(file.duration_ms)


def build(
    preview: ImportPreview,
    request: MetadataRequest,
    now_ms: int,
    summaries: list[NormalizationSummary],
) -> PreparedImport:
    declaration = request.declaration
    validate_bindings(preview, declaration)
    rights, retention = declaration.rights, declaration.retention
    eligible = rights.local == "ALLOWED" and retention.days is not None
    tracks = any(file.role == "tracks" for file in preview.files)
    if declaration.coverage.vehicles is True and not tracks:
        raise ImportFailure("COVERAGE_CONFLICT", "coverage.vehicles")
    if declaration.coverage.speaker_identity is True:
        raise ImportFailure("SPEAKER_MAPPING_REQUIRED", "coverage.speaker_identity")
    layout = declaration.layout.metric() if declaration.layout else None
    known = all(item.clock.offset_ms is not None for item in declaration.files)
    issues: list[Issue] = []

    def issue(code: str, field: str, blocking: bool, remediation: str) -> None:
        issues.append(Issue(code=code, field=field, blocking=blocking, remediation=remediation))

    if rights.local != "ALLOWED":
        issue(
            "LOCAL_RIGHT_REQUIRED",
            "rights.local",
            True,
            "Declare allowed local use with its source basis.",
        )
    if retention.days is None:
        issue(
            "RETENTION_REQUIRED", "retention", True, "Declare an explicit source retention period."
        )
    if not known:
        issue(
            "ALIGNMENT_UNKNOWN",
            "clock",
            False,
            "Declare clock offset and uncertainty before cross-source analysis.",
        )
    if layout is None:
        issue(
            "LAYOUT_UNKNOWN",
            "layout",
            False,
            "Supply a versioned local layout before map/geometry use.",
        )
    for action in ("cloud_audio", "cloud_context", "export", "audio_export", "reviewer"):
        if not rights.permits(action):
            issue(
                "RIGHT_UNAVAILABLE",
                "rights." + action,
                False,
                "This action remains unavailable until separately allowed.",
            )
    identities = [
        IdentityMapping(
            source_entity_id=item.source_entity_id,
            entity_id=uuid5(preview.id, "entity:" + item.source_entity_id),
            callsign=item.callsign.upper(),
            aliases=sorted({alias.upper() for alias in item.aliases}),
        )
        for item in declaration.identities
    ]
    given = {item.file_id: item for item in declaration.files}
    first_audio = next(file for file in preview.files if file.role == "audio")
    clock = given[first_audio.id].clock
    source_hash = content_hash(preview.files)
    manifest = None
    if eligible and retention.days is not None:
        manifest = SourceManifest(
            id=uuid5(preview.id, "source"),
            session_id=uuid5(preview.id, "session"),
            source_kind=declaration.source_kind,
            source_label=declaration.source_label,
            source_hash=source_hash,
            revision=request.expected_revision + 1,
            permissions=Permissions(
                local=rights.permits("reviewer"),
                cloud=rights.permits("cloud_audio") and rights.permits("cloud_context"),
                export=rights.permits("export"),
                audio_export=rights.permits("audio_export"),
                basis=rights.basis,
                retention_days=retention.days,
            ),
            clock=ClockMapping(
                offset_ms=clock.offset_ms if clock.method != "DECLARED_LINEAR" else None,
                uncertainty_ms=clock.uncertainty_ms if clock.method != "DECLARED_LINEAR" else None,
                timezone=clock.timezone,
                mapping_version=clock.version,
            ),
            coverage=Coverage(
                audio=True,
                tracks=tracks,
                vehicles=declaration.coverage.vehicles,
                speaker_identity=declaration.coverage.speaker_identity,
                quality="SUPPORTED"
                if known
                and all(f.clock.method != "DECLARED_LINEAR" for f in declaration.files)
                and declaration.coverage.vehicles is not None
                and declaration.coverage.speaker_identity is not None
                and not declaration.coverage.gaps
                else "MISSING",
                gaps=declaration.coverage.gaps,
            ),
            units="m",
            coordinate_system="LOCAL_CARTESIAN" if layout else "UNKNOWN",
            layout_version=layout.version if layout else None,
            assets=[
                Asset.model_validate_json(
                    json.dumps(
                        dict(
                            id=str(f.id),
                            sha256=f.sha256,
                            duration_ms=f.duration_ms,
                            channels=f.channels,
                            sample_rate_hz=f.sample_rate_hz,
                            media_type=f.media_type,
                            fixture_path=None,
                        )
                    )
                )
                for f in preview.files
                if f.role == "audio"
            ],
            domain_validation="NOT_DOMAIN_VALIDATED",
        )
    result = PreparedImport.model_construct(
        id=preview.id,
        revision=request.expected_revision + 1,
        declared_at=datetime.fromtimestamp(now_ms / 1000, UTC),
        declaration=declaration,
        files=preview.files,
        content_hash=source_hash,
        declaration_hash=hashed(declaration.model_dump(mode="json")),
        manifest_hash="",
        manifest=manifest,
        layout=layout,
        identities=identities,
        normalizations=summaries,
        paired_status="METADATA_COMPLETE"
        if tracks
        and known
        and layout is not None
        and summaries
        and all(x.identity_unknown == 0 and x.layout_unknown == 0 for x in summaries)
        else "NOT_EVALUABLE",
        alignment_status="KNOWN" if known else "UNKNOWN",
        locally_eligible=eligible,
        cloud_audio_eligible=eligible and rights.permits("cloud_audio"),
        cloud_context_eligible=eligible and rights.permits("cloud_context"),
        status="PREPARED" if eligible else "NEEDS_REMEDIATION",
        issues=issues,
    )
    data = result.model_dump()
    data["manifest_hash"] = hashed(result.model_dump(mode="json", exclude={"manifest_hash"}))
    return PreparedImport.model_validate(data)


class ImportMetadata:
    def __init__(self, imports: Imports) -> None:
        self.imports = imports

    def authorize(self, uow: UnitOfWork, token: str, identifier: UUID) -> None:
        owner = self.imports._admin(uow, token)
        row = uow.connection.execute(
            "SELECT * FROM platform_import_drafts WHERE id=?", (str(identifier),)
        ).fetchone()
        if row is None or row["expires_ms"] <= self.imports.sessions.clock():
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if row["owner_id"] != str(owner.id):
            raise ContractError("ACCESS_DENIED")
        if row["status"] == "UPLOADING":
            raise ImportFailure("INCOMPLETE_UPLOAD")

    def prepare(
        self, token: str, identifier: UUID, key: str, request: MetadataRequest
    ) -> PreparedImport:
        if type(request) is not MetadataRequest:
            raise ContractError("INVALID_INPUT")
        request = MetadataRequest.model_validate_json(request.model_dump_json())
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
            raise ContractError("INVALID_INPUT")
        preview = self.imports.get(token, identifier)
        key_hash, request_hash = hashed(key), hashed(request.model_dump(mode="json"))
        validate_bindings(preview, request.declaration)
        summaries = scan(self.imports, preview, request.declaration)
        prepared = build(preview, request, self.imports.sessions.clock(), summaries)
        self.imports.verify(preview)
        with self.imports.database.begin() as uow:
            self.authorize(uow, token, identifier)
            prior = uow.connection.execute(
                "SELECT * FROM platform_import_metadata WHERE draft_id=? AND key_hash=?",
                (str(identifier), key_hash),
            ).fetchone()
            if prior is not None:
                if prior["request_hash"] != request_hash:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return PreparedImport.model_validate_json(prior["payload"])
            current = uow.connection.execute(
                "SELECT COALESCE(MAX(revision),0) FROM platform_import_metadata WHERE draft_id=?",
                (str(identifier),),
            ).fetchone()[0]
            if current != request.expected_revision:
                raise ContractError("VERSION_CONFLICT")
            owner = self.imports._admin(uow, token)
            uow.connection.execute(
                "INSERT INTO platform_import_metadata VALUES (?,?,?,?,?,?,?,?)",
                (
                    str(identifier),
                    prepared.revision,
                    str(owner.id),
                    key_hash,
                    request_hash,
                    prepared.content_hash,
                    self.imports.sessions.clock(),
                    prepared.model_dump_json(),
                ),
            )
            uow.commit()
        return prepared

    def require_right(self, token: str, identifier: UUID, action: Action) -> PreparedImport:
        prepared = self.get(token, identifier)
        prepared.require_right(action)
        return prepared

    def current_preview(self, token: str, identifier: UUID) -> ImportPreview:
        preview = self.imports.get(token, identifier)
        if preview.status == "UPLOADING":
            return preview
        prepared = self._read_metadata(token, identifier)
        if prepared is None:
            return preview
        data = preview.model_dump(mode="json")
        data.update(
            metadata_revision=prepared.revision,
            status=prepared.status,
            clock_alignment=prepared.alignment_status,
            layout_status="DECLARED" if prepared.layout is not None else "UNKNOWN",
            rights_status="DECLARED",
            issues=[issue.model_dump() for issue in prepared.issues],
        )
        return ImportPreview.model_validate_json(json.dumps(data))

    def get(self, token: str, identifier: UUID, *, revision: int | None = None) -> PreparedImport:
        self.imports.get(token, identifier)
        prepared = self._read_metadata(token, identifier, revision=revision)
        if prepared is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        return prepared

    def _read_metadata(
        self, token: str, identifier: UUID, *, revision: int | None = None
    ) -> PreparedImport | None:
        with self.imports.database.begin() as uow:
            self.authorize(uow, token, identifier)
            row = uow.connection.execute(
                "SELECT payload FROM platform_import_metadata WHERE draft_id=? "
                "AND (? IS NULL OR revision=?) ORDER BY revision DESC LIMIT 1",
                (str(identifier), revision, revision),
            ).fetchone()
            return None if row is None else PreparedImport.model_validate_json(row["payload"])
