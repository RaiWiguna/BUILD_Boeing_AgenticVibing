"""Observed canonical sidecar metadata; no source-reader or accepted-domain writes."""

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid5

from flowlens.clocks.normalization import ClockSpec, MetadataModel
from flowlens.contracts.models import SourceEvent, Track
from flowlens.imports.inspection import InvalidContent, records
from flowlens.imports.staging import ImportFailure, ImportPreview, Imports
from flowlens.sources.metadata import Declaration, IdentityDeclaration


class NormalizedRecord(MetadataModel):
    file_id: UUID
    record_id: UUID
    source_record_id: UUID
    source_event_id: str
    source_session_id: UUID
    source_id: UUID
    source_hash: str
    raw_event_time_ms: int
    raw_available_time_ms: int | None
    recorded_at: datetime
    raw_entity_id: UUID | None
    event_time_ms: int | None
    available_time_ms: int | None
    entity_id: UUID | None
    position_m: tuple[float, float] | None
    footprint_m: tuple[float, float] | None
    layout_version: str | None


def normalize_record(
    item: SourceEvent | Track,
    clock: ClockSpec,
    draft_id: UUID,
    file_id: UUID,
    identities: list[IdentityDeclaration],
) -> NormalizedRecord:
    event_ms = clock.to_session_ms(item.event_time_ms)
    available = (
        clock.to_session_ms(item.available_time_ms) if item.available_time_ms is not None else None
    )
    entity = next(
        (
            mapping
            for mapping in identities
            if str(item.entity_id) == mapping.source_entity_id
            and event_ms is not None
            and mapping.validity.start_ms <= event_ms < mapping.validity.end_ms
        ),
        None,
    )
    return NormalizedRecord(
        file_id=file_id,
        record_id=uuid5(draft_id, str(file_id) + ":record:" + item.source_event_id),
        source_record_id=item.id,
        source_event_id=item.source_event_id,
        source_session_id=item.session_id,
        source_id=item.source_id,
        source_hash=item.source_hash,
        raw_event_time_ms=item.event_time_ms,
        raw_available_time_ms=item.available_time_ms,
        recorded_at=item.recorded_at,
        raw_entity_id=item.entity_id,
        event_time_ms=event_ms,
        available_time_ms=available,
        entity_id=uuid5(draft_id, "entity:" + entity.source_entity_id) if entity else None,
        position_m=(item.x_m, item.y_m) if isinstance(item, Track) else None,
        footprint_m=(item.length_m, item.width_m) if isinstance(item, Track) else None,
        layout_version=item.layout_version if isinstance(item, Track) else None,
    )


class NormalizationSummary(MetadataModel):
    file_id: UUID
    rows: int
    normalized_hash: str
    min_event_ms: int | None
    max_event_ms: int | None
    min_available_ms: int | None
    available_unknown: int
    identity_unknown: int
    layout_unknown: int


def scan(
    imports: Imports, preview: ImportPreview, declaration: Declaration
) -> list[NormalizationSummary]:
    wanted: dict[tuple[UUID, str], list[IdentityDeclaration]] = {}
    identity_lookup = {item.source_entity_id: item for item in declaration.identities}
    for identity in declaration.identities:
        for record in identity.evidence_record_ids:
            wanted.setdefault((identity.evidence_file_id, record), []).append(identity)
    found: set[tuple[UUID, str]] = set()
    summaries = []
    common_scope = None
    clocks = {file.file_id: file.clock for file in declaration.files}
    for file in preview.files:
        if file.role == "audio":
            continue
        role: Literal["events", "tracks"] = file.role
        low = high = available_low = None
        available_unknown = identity_unknown = layout_unknown = count = 0
        digest = hashlib.sha256()
        seen: set[str] = set()
        file_scope = None
        try:
            with imports.open_file(preview, file) as fd:
                for count, item in enumerate(
                    records(
                        fd, file.filename.rsplit(".", 1)[-1].lower(), role, imports.limits.max_rows
                    ),
                    1,
                ):
                    if item.analysis_run_id is not None:
                        raise ImportFailure("SOURCE_SCOPE_CONFLICT", role, count)
                    scope = (item.session_id, item.revision)
                    source_scope = (item.source_id, item.source_hash)
                    if common_scope not in (None, scope) or file_scope not in (None, source_scope):
                        raise ImportFailure("SOURCE_SCOPE_CONFLICT", role, count)
                    common_scope, file_scope = scope, source_scope
                    if item.source_event_id in seen:
                        raise ImportFailure("DUPLICATE_SOURCE_RECORD", role, count)
                    seen.add(item.source_event_id)
                    normalized = normalize_record(
                        item,
                        clocks[file.id],
                        preview.id,
                        file.id,
                        [identity_lookup[str(item.entity_id)]]
                        if str(item.entity_id) in identity_lookup
                        else [],
                    )
                    if normalized.event_time_ms is not None:
                        low = (
                            normalized.event_time_ms
                            if low is None
                            else min(low, normalized.event_time_ms)
                        )
                        high = (
                            normalized.event_time_ms
                            if high is None
                            else max(high, normalized.event_time_ms)
                        )
                    if normalized.available_time_ms is None:
                        available_unknown += 1
                    else:
                        available_low = (
                            normalized.available_time_ms
                            if available_low is None
                            else min(available_low, normalized.available_time_ms)
                        )
                    identity_unknown += normalized.entity_id is None
                    if isinstance(item, Track):
                        layout = declaration.layout
                        if layout is not None and item.layout_version != layout.version:
                            raise ImportFailure("LAYOUT_VERSION_CONFLICT", role, count)
                        layout_unknown += (
                            layout is None
                            or normalized.event_time_ms is None
                            or not (
                                layout.validity.start_ms
                                <= normalized.event_time_ms
                                < layout.validity.end_ms
                            )
                        )
                    pair = (file.id, item.source_event_id)
                    for identity in wanted.get(pair, []):
                        if (
                            identity.evidence_file_id == file.id
                            and item.source_event_id in identity.evidence_record_ids
                        ):
                            if str(item.entity_id) != identity.source_entity_id:
                                raise ImportFailure(
                                    "IDENTITY_EVIDENCE_CONFLICT", "identities", count
                                )
                            if normalized.event_time_ms is not None and not (
                                identity.validity.start_ms
                                <= normalized.event_time_ms
                                < identity.validity.end_ms
                            ):
                                raise ImportFailure("IDENTITY_TIME_CONFLICT", "identities", count)
                            found.add(pair)
                    digest.update(
                        json.dumps(
                            normalized.model_dump(mode="json"),
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    )
                    digest.update(b"\n")
        except InvalidContent as error:
            raise ImportFailure(error.code, role, error.row) from None
        summaries.append(
            NormalizationSummary(
                file_id=file.id,
                rows=count,
                normalized_hash=digest.hexdigest(),
                min_event_ms=low,
                max_event_ms=high,
                min_available_ms=available_low,
                available_unknown=available_unknown,
                identity_unknown=identity_unknown,
                layout_unknown=layout_unknown,
            )
        )
    if set(wanted) != found:
        raise ImportFailure("IDENTITY_EVIDENCE_UNAVAILABLE", "identities")
    for index, identity in enumerate(declaration.identities):
        names = {identity.callsign.upper(), *(alias.upper() for alias in identity.aliases)}
        for other in declaration.identities[index + 1 :]:
            overlap = max(identity.validity.start_ms, other.validity.start_ms) < min(
                identity.validity.end_ms, other.validity.end_ms
            )
            if overlap and names.intersection(
                {other.callsign.upper(), *(alias.upper() for alias in other.aliases)}
            ):
                raise ImportFailure("AMBIGUOUS_IDENTITY", "identities")
    return summaries
