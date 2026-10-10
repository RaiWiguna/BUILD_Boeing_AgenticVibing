"""Durable raw promotion before atomic metadata publication; recover orphan packages."""

import json
import os
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from flowlens.assets.storage import PrivateFiles
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import SourceEvent, SourceQualityChanged, Track
from flowlens.core.errors import ContractError
from flowlens.imports.inspection import records
from flowlens.imports.metadata import ImportMetadata, PreparedImport, hashed
from flowlens.imports.normalization import normalize_record
from flowlens.imports.staging import ImportFailure, Imports


class ImportReceipt(MetadataModel):
    session_id: UUID
    source_id: UUID
    revision: int
    source_hash: str
    deduplicated: bool


def semantic(prepared: PreparedImport) -> tuple[str, str]:
    declaration = prepared.declaration.model_dump(mode="json")
    identity = hashed(
        {
            k: declaration[k]
            for k in (
                "source_kind",
                "source_owner",
                "source_identifier",
                "dataset",
                "dataset_version",
                "subset",
            )
        }
    )
    aliases = {str(f.id): f.role + ":" + f.filename for f in prepared.files}
    for file in declaration["files"]:
        file["file_id"] = aliases[file["file_id"]]
    declaration["files"].sort(key=lambda x: x["file_id"])
    for item in declaration["identities"]:
        item["evidence_file_id"] = aliases[item["evidence_file_id"]]
    return identity, hashed([prepared.content_hash, declaration])


class ImportCommit:
    def __init__(self, imports: Imports, files: PrivateFiles) -> None:
        self.imports, self.files = imports, files
        self.fault: Callable[[str], None] = lambda _: None
        self.recover()

    def recover(self) -> None:
        with self.imports.database.begin() as uow:
            packages = {
                UUID(row["package_id"]): PreparedImport.model_validate_json(row["payload"])
                for row in uow.connection.execute("SELECT * FROM platform_source_packages")
            }
        for identifier, prepared in packages.items():
            self.files.verify(identifier, prepared.manifest_hash, prepared.files)
        for name in os.listdir(self.files.fd):
            try:
                identifier = UUID(name)
            except ValueError:
                continue
            if str(identifier) == name and identifier not in packages:
                self.files.remove(identifier)

    def commit(self, token: str, draft: UUID, expected_revision: int, key: str) -> ImportReceipt:
        if (
            type(expected_revision) is not int
            or not 1 <= expected_revision <= 64
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key)
        ):
            raise ContractError("INVALID_INPUT")
        request_hash, key_hash = hashed([str(draft), expected_revision]), hashed(key)
        with self.imports.database.begin() as uow:
            owner = self.imports._admin(uow, token)
            old = uow.connection.execute(
                "SELECT * FROM platform_import_commits "
                "WHERE owner_id=? AND draft_id=? AND key_hash=?",
                (str(owner.id), str(draft), key_hash),
            ).fetchone()
            if old:
                if old["request_hash"] != request_hash:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return ImportReceipt.model_validate_json(old["payload"])
        metadata = ImportMetadata(self.imports)
        prepared = metadata.get(token, draft)
        if prepared.revision != expected_revision:
            raise ContractError("VERSION_CONFLICT")
        prepared.require_right("local")
        if prepared.manifest is None:
            raise ContractError("SOURCE_PERMISSION_REQUIRED")
        identity_hash, semantic_hash = semantic(prepared)
        package = uuid4()
        self.files.create(package)
        try:
            preview = self.imports.get(token, draft)
            for file in prepared.files:
                with self.imports.open_file(preview, file) as fd:

                    def chunks() -> Iterator[bytes]:
                        os.lseek(fd, 0, os.SEEK_SET)
                        while block := os.read(fd, 65536):
                            yield block

                    self.files.write(package, file, chunks())
            self.fault("after_copy")
            self.files.seal(package, prepared.manifest_hash, prepared.files)
            self.fault("after_promotion")
            with self.imports.database.begin() as uow:
                metadata.authorize(uow, token, draft)
                latest = uow.connection.execute(
                    "SELECT MAX(revision) FROM platform_import_metadata WHERE draft_id=?",
                    (str(draft),),
                ).fetchone()[0]
                if latest != expected_revision:
                    raise ContractError("VERSION_CONFLICT")
                prior = uow.connection.execute(
                    "SELECT * FROM platform_import_commits "
                    "WHERE owner_id=? AND draft_id=? AND key_hash=?",
                    (str(owner.id), str(draft), key_hash),
                ).fetchone()
                if prior:
                    if prior["request_hash"] != request_hash:
                        raise ContractError("IDEMPOTENCY_CONFLICT")
                    result = ImportReceipt.model_validate_json(prior["payload"])
                else:
                    existing = uow.connection.execute(
                        "SELECT * FROM platform_source_packages "
                        "WHERE owner_id=? AND identity_hash=?",
                        (str(owner.id), identity_hash),
                    ).fetchone()
                    if existing:
                        if existing["semantic_hash"] != semantic_hash:
                            raise ImportFailure("DUPLICATE_SOURCE_CONFLICT")
                        result = ImportReceipt(
                            session_id=UUID(existing["session_id"]),
                            source_id=UUID(existing["source_id"]),
                            revision=existing["revision"],
                            source_hash=prepared.content_hash,
                            deduplicated=True,
                        )
                        used_package = existing["package_id"]
                    else:
                        manifest = prepared.manifest
                        sid, source = str(manifest.session_id), str(manifest.id)
                        now = self.imports.sessions.clock()
                        uow.connection.execute("INSERT INTO platform_sessions VALUES (?)", (sid,))
                        uow.connection.execute(
                            "INSERT INTO platform_revisions VALUES (?,?,?)",
                            (sid, manifest.revision, prepared.manifest_hash),
                        )
                        uow.connection.execute(
                            "INSERT INTO platform_sources VALUES (?,?,?,?,?)",
                            (
                                sid,
                                source,
                                manifest.revision,
                                manifest.source_hash,
                                manifest.model_dump_json(),
                            ),
                        )
                        days = prepared.declaration.retention.days
                        if days is None:
                            raise ContractError("SOURCE_PERMISSION_REQUIRED")
                        uow.connection.execute(
                            "INSERT INTO platform_source_packages VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (
                                str(package),
                                sid,
                                source,
                                manifest.revision,
                                str(owner.id),
                                identity_hash,
                                semantic_hash,
                                now,
                                now + days * 86400000,
                                prepared.model_dump_json(),
                            ),
                        )
                        uow.connection.execute(
                            "INSERT INTO platform_source_rights VALUES (?,?,1,?,?,?)",
                            (
                                sid,
                                source,
                                str(owner.id),
                                now,
                                prepared.declaration.rights.model_dump_json(),
                            ),
                        )
                        for asset in manifest.assets:
                            uow.connection.execute(
                                "INSERT INTO platform_assets VALUES (?,?,?,?,?,?)",
                                (
                                    sid,
                                    str(asset.id),
                                    source,
                                    manifest.revision,
                                    f"{package}/{asset.id}.raw",
                                    asset.sha256,
                                ),
                            )
                        clocks = {x.file_id: x.clock for x in prepared.declaration.files}
                        for file in prepared.files:
                            if file.role == "audio":
                                continue
                            with self.files.open(package, file) as fd:
                                for item in records(
                                    fd,
                                    file.filename.rsplit(".", 1)[-1].lower(),
                                    file.role,
                                    self.imports.limits.max_rows,
                                ):
                                    normalized = normalize_record(
                                        item,
                                        clocks[file.id],
                                        draft,
                                        file.id,
                                        prepared.declaration.identities,
                                    )
                                    if normalized.event_time_ms is None:
                                        continue
                                    data = item.model_dump(mode="json")
                                    data.update(
                                        id=str(normalized.record_id),
                                        session_id=sid,
                                        source_id=source,
                                        revision=manifest.revision,
                                        source_hash=manifest.source_hash,
                                        entity_id=str(normalized.entity_id)
                                        if normalized.entity_id
                                        else None,
                                        event_time_ms=normalized.event_time_ms,
                                        available_time_ms=normalized.available_time_ms,
                                    )
                                    cls = Track if isinstance(item, Track) else SourceEvent
                                    if isinstance(item, Track):
                                        drift = clocks[file.id].drift_ppm
                                        if drift is not None:
                                            data["age_ms"] = int(
                                                (
                                                    Decimal(item.age_ms)
                                                    * (1 + Decimal(str(drift)) / 1000000)
                                                ).quantize(Decimal(1), rounding=ROUND_HALF_UP)
                                            )
                                    record = cls.model_validate_json(json.dumps(data))
                                    uow.connection.execute(
                                        "INSERT INTO platform_records VALUES (?,?,?,NULL,?,?,?)",
                                        (
                                            "tracks"
                                            if isinstance(record, Track)
                                            else "source_events",
                                            str(record.id),
                                            sid,
                                            manifest.revision,
                                            type(record).__name__,
                                            record.model_dump_json(),
                                        ),
                                    )
                        duration = max(
                            (
                                (clocks[f.id].to_session_ms(f.duration_ms or 0) or 0)
                                if clocks[f.id].offset_ms is not None
                                else f.duration_ms or 0
                                for f in prepared.files
                                if f.role == "audio"
                            ),
                            default=0,
                        )
                        endpoint = max(
                            [duration, *[x.max_event_ms or 0 for x in prepared.normalizations]]
                        )
                        uow.connection.execute(
                            "INSERT INTO platform_context_state VALUES (?,?,'DEBRIEF')",
                            (sid, endpoint),
                        )
                        event = SourceQualityChanged(
                            session_id=manifest.session_id,
                            analysis_run_id=None,
                            revision=manifest.revision,
                            source_id=manifest.id,
                            coverage=manifest.coverage,
                        )
                        uow.connection.execute(
                            "INSERT INTO platform_events VALUES (?,1,NULL,?,?)",
                            (sid, manifest.revision, event.model_dump_json()),
                        )
                        uow.connection.execute(
                            "INSERT INTO platform_audit "
                            "(session_id,actor_id,request_id,action,target_id,recorded_at) "
                            "VALUES (?,?,?,'IMPORT_COMMIT',?,?)",
                            (
                                sid,
                                str(owner.id),
                                str(uuid4()),
                                source,
                                datetime.fromtimestamp(now / 1000, UTC).isoformat(),
                            ),
                        )
                        used_package = str(package)
                        result = ImportReceipt(
                            session_id=manifest.session_id,
                            source_id=manifest.id,
                            revision=manifest.revision,
                            source_hash=manifest.source_hash,
                            deduplicated=False,
                        )
                    uow.connection.execute(
                        "INSERT INTO platform_import_commits VALUES (?,?,?,?,?,?)",
                        (
                            str(owner.id),
                            str(draft),
                            key_hash,
                            request_hash,
                            used_package,
                            result.model_dump_json(),
                        ),
                    )
                self.fault("before_db_commit")
                uow.commit()
            self.fault("after_db_commit")
            return result
        finally:
            with self.imports.database.begin() as uow:
                durable = uow.connection.execute(
                    "SELECT 1 FROM platform_source_packages WHERE package_id=?", (str(package),)
                ).fetchone()
            if not durable:
                self.files.remove(package)
