"""Validated, atomic import and read adapters for normalized ``replay-1`` archives.

The module accepts only the internal normalized profile. It does not infer a
permission grant, connect to an operator feed, or expose synthetic checkpoints.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import ValidationError

from .replay_contracts import ReplayEventRecord, ReplaySourceManifest
from .storage import Archive, ReplayArchiveConflict


class ReplayImportError(ValueError):
    """Base error for an invalid normalized replay bundle."""


class ReplayImportValidationError(ReplayImportError):
    """The bundle is malformed or violates the ``replay-1`` contract."""


class UnsupportedReplayFormat(ReplayImportValidationError):
    """The bundle is not in a supported normalized replay profile."""


class ReplayImportConflict(ReplayImportError):
    """An immutable source or source-event identity was reused inconsistently."""


@dataclass(frozen=True)
class ReplayImportReceipt:
    source_session_id: str
    source_id: str
    import_status: Literal["completed"]
    receipt_id: str
    content_hash: str
    idempotent: bool


_SENSITIVE_KEY_TOKENS = {
    "private",
    "truth",
    "checkpoint",
    "schedule",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
    "api_key",
    "local_path",
    "local_metadata",
}
_PUBLIC_STATE_KEYS = {
    "source_id",
    "as_of_ms",
    "coverage",
    "coverage_status",
    "tracks",
    "previous_tracks",
    "clearances",
    "requests",
    "readbacks",
    "coordination_events",
    "runway",
    "native_source_alerts",
    "control_receipts",
    "track_history",
    "source_event_refs",
    "unresolved_records",
    "track_source_quality",
    "track_freshness",
    "data_quality",
    "quality_reasons",
}
_PUBLIC_FRAME_KEYS = {
    "analysis_id",
    "at_ms",
    "state",
    "detector_result",
    "alerts",
    "lifecycle_events",
    "status",
    "layout_binding",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant {value!r} is unsupported")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON property {key!r}")
        result[key] = value
    return result


def _sensitive_key(key: str) -> bool:
    tokens = key.casefold().replace("-", "_").split("_")
    return any(token in _SENSITIVE_KEY_TOKENS for token in tokens) or key.casefold() in _SENSITIVE_KEY_TOKENS


def _reject_nonpublic_fields(value: Any, path: str = "record") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str) and _sensitive_key(key):
                raise ReplayImportValidationError(f"unsupported private field at {path}.{key}")
            _reject_nonpublic_fields(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_nonpublic_fields(nested, f"{path}[{index}]")


def _public_value(value: Any) -> Any:
    """Recursively retain public values while excluding reserved private keys."""
    if isinstance(value, Mapping):
        return {
            str(key): _public_value(nested)
            for key, nested in value.items()
            if isinstance(key, str) and not _sensitive_key(key)
        }
    if isinstance(value, list):
        return [_public_value(item) for item in value]
    return value


def _parse_json_object(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReplayImportValidationError(f"{label} must be valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReplayImportValidationError(f"{label} must be a JSON object")
    return value


def _validate_manifest(manifest_bytes: bytes) -> ReplaySourceManifest:
    raw_manifest = _parse_json_object(manifest_bytes, label="manifest")
    try:
        manifest = ReplaySourceManifest.model_validate(raw_manifest)
    except ValidationError as exc:
        if raw_manifest.get("schema_version") != "replay-1":
            raise UnsupportedReplayFormat("only normalized schema_version 'replay-1' is supported") from exc
        raise ReplayImportValidationError(f"manifest validation failed: {exc}") from exc
    if manifest.schema_version != "replay-1":
        raise UnsupportedReplayFormat(f"unsupported replay schema {manifest.schema_version!r}")
    return manifest


def _validate_event_time(record: ReplayEventRecord, manifest: ReplaySourceManifest) -> None:
    source_time = record.source_time
    timebase = manifest.timebase
    if source_time.unit != timebase.source_unit or source_time.clock != timebase.source_clock:
        raise ReplayImportValidationError(
            f"event {record.source_event_id!r} source_time unit/clock does not match manifest timebase"
        )

    sim_ms = record.event.sim_ms
    if source_time.value is None:
        if sim_ms is not None:
            raise ReplayImportValidationError(
                f"event {record.source_event_id!r} cannot have session time when source timestamp is missing"
            )
        return

    if timebase.alignment_status == "unknown":
        if sim_ms is not None:
            raise ReplayImportValidationError(
                f"event {record.source_event_id!r} has session time but manifest alignment is unknown"
            )
        return

    try:
        multiplier = Decimal(1000) if source_time.unit == "s" else Decimal(1)
        mapped_ms = Decimal(str(source_time.value)) * multiplier + Decimal(timebase.offset_ms or 0)
    except InvalidOperation as exc:
        raise ReplayImportValidationError(
            f"event {record.source_event_id!r} source timestamp cannot be mapped"
        ) from exc
    if mapped_ms != mapped_ms.to_integral_value():
        raise ReplayImportValidationError(
            f"event {record.source_event_id!r} timestamp does not map to a whole session millisecond"
        )
    expected_ms = int(mapped_ms)
    if expected_ms < 0 or sim_ms != expected_ms:
        raise ReplayImportValidationError(
            f"event {record.source_event_id!r} sim_ms must equal mapped source time ({expected_ms})"
        )
    event = record.event
    if event.received_ms is not None and event.received_ms > sim_ms:
        raise ReplayImportValidationError(
            f"event {record.source_event_id!r} sim_ms precedes received_ms"
        )
    if event.track is not None and event.track.received_ms > sim_ms:
        raise ReplayImportValidationError(
            f"event {record.source_event_id!r} sim_ms precedes track.received_ms"
        )


def _validate_events(event_bytes: bytes, manifest: ReplaySourceManifest) -> list[ReplayEventRecord]:
    try:
        text = event_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ReplayImportValidationError("events JSONL must be UTF-8") from exc
    records_by_identity: dict[tuple[str, str], ReplayEventRecord] = {}
    fingerprints: dict[tuple[str, str], str] = {}
    ordinal_owners: dict[int, tuple[str, str]] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ReplayImportValidationError(f"events JSONL contains a blank record at line {line_number}")
        try:
            raw_record = _parse_json_object(line.encode("utf-8"), label=f"events line {line_number}")
            _reject_nonpublic_fields(raw_record, f"events[{line_number}]")
            record = ReplayEventRecord.model_validate(raw_record)
        except ValidationError as exc:
            raise ReplayImportValidationError(f"events line {line_number} validation failed: {exc}") from exc
        except ReplayImportValidationError:
            raise
        except ValueError as exc:
            raise ReplayImportValidationError(f"events line {line_number} is invalid: {exc}") from exc
        if record.schema_version != manifest.schema_version:
            raise UnsupportedReplayFormat(
                f"events line {line_number} uses unsupported schema {record.schema_version!r}"
            )
        if record.source_id != manifest.source_id:
            raise ReplayImportValidationError(
                f"events line {line_number} source_id does not match manifest source_id"
            )
        _validate_event_time(record, manifest)
        identity = (record.source_id, record.source_event_id)
        fingerprint = _canonical_json(record.model_dump(mode="json"))
        previous = fingerprints.get(identity)
        if previous is not None:
            if previous != fingerprint:
                raise ReplayImportConflict(
                    f"conflicting payloads for source event {record.source_id}:{record.source_event_id}"
                )
            continue
        ordinal_owner = ordinal_owners.get(record.event.ordinal)
        if ordinal_owner is not None and ordinal_owner != identity:
            raise ReplayImportValidationError(
                f"event ordinal {record.event.ordinal} is shared by distinct source event identities"
            )
        ordinal_owners[record.event.ordinal] = identity
        fingerprints[identity] = fingerprint
        records_by_identity[identity] = record
    return sorted(
        records_by_identity.values(),
        key=lambda record: (record.event.ordinal, record.source_event_id),
    )


class ReplayImportService:
    """Parse, validate, and atomically archive one normalized replay bundle."""

    def __init__(self, archive: Archive):
        self._archive = archive

    def import_bundle(self, manifest_bytes: bytes, event_bytes: bytes) -> ReplayImportReceipt:
        manifest = _validate_manifest(manifest_bytes)
        if not isinstance(event_bytes, bytes):
            raise ReplayImportValidationError("events payload must be the original bytes")
        content_hash = hashlib.sha256(event_bytes).hexdigest()
        if content_hash != manifest.content_hash.casefold():
            raise ReplayImportValidationError("manifest content_hash does not match exact events JSONL bytes")
        records = _validate_events(event_bytes, manifest)
        manifest_value = manifest.model_dump(mode="json")
        canonical_manifest = _canonical_json(manifest_value)
        metadata_value = {key: value for key, value in manifest_value.items() if key != "content_hash"}
        try:
            result = self._archive.commit_replay_source(
                source_id=manifest.source_id,
                content_hash=content_hash,
                manifest_json=canonical_manifest,
                manifest_metadata_json=_canonical_json(metadata_value),
                event_bytes=event_bytes,
                records=[record.model_dump(mode="json") for record in records],
            )
        except ReplayArchiveConflict as exc:
            raise ReplayImportConflict(str(exc)) from exc
        return ReplayImportReceipt(**result)

    def persist_analysis(self, analysis: Any) -> None:
        """Append a BE-02 analysis object without changing its source records."""
        metadata = analysis.metadata
        metadata_value = (
            metadata.model_dump(mode="json") if hasattr(metadata, "model_dump") else vars(metadata)
        )
        if hasattr(metadata, "__dataclass_fields__"):
            metadata_value = {
                key: getattr(metadata, key) for key in metadata.__dataclass_fields__
            }
        frames: list[dict[str, Any]] = []
        for frame in analysis.frames:
            projection = frame.public_projection() if hasattr(frame, "public_projection") else dict(frame)
            frames.append(projection)
        self._archive.save_replay_analysis(metadata_value, frames)


class ArchiveReplayEventSource:
    """Read-only event-source adapter for BE-02; it has no archive write methods."""

    def __init__(self, archive: Archive, source_session_id: str):
        self._archive = archive
        self._source_session_id = source_session_id

    def manifest(self) -> ReplaySourceManifest:
        source = self._archive.replay_source(self._source_session_id)
        if source is None:
            raise KeyError(f"unknown replay source session {self._source_session_id!r}")
        return ReplaySourceManifest.model_validate(source["manifest"])

    def read(self, after_ordinal: int, until_ms: int | None = None) -> Sequence[ReplayEventRecord]:
        values = self._archive.replay_source_records(
            self._source_session_id,
            after_ordinal=after_ordinal,
            until_ms=until_ms,
            include_unknown_time=True,
        )
        return tuple(ReplayEventRecord.model_validate(value) for value in values)


class SQLiteReplayArchiveReader:
    """Public, read-only projection used by later transport/consumer work."""

    def __init__(self, archive: Archive):
        self._archive = archive

    @staticmethod
    def _public_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
        public = dict(manifest)
        # source_ref may contain a local path or deployment-specific locator.
        public.pop("source_ref", None)
        return _public_value(public)

    @staticmethod
    def _public_analysis(metadata: Mapping[str, Any]) -> dict[str, Any]:
        fields = (
            "id",
            "source_id",
            "source_session_id",
            "kind",
            "input_hash",
            "versions",
            "window_start_ms",
            "window_end_ms",
            "status",
        )
        return _public_value({key: metadata[key] for key in fields if key in metadata})

    @staticmethod
    def _public_frame(frame: Mapping[str, Any]) -> dict[str, Any]:
        result = {key: frame[key] for key in _PUBLIC_FRAME_KEYS if key in frame}
        state = frame.get("state")
        if isinstance(state, Mapping):
            result["state"] = _public_value({key: state[key] for key in _PUBLIC_STATE_KEYS if key in state})
        return _public_value(result)

    def metadata(self, source_session_id: str) -> Mapping[str, Any] | None:
        source = self._archive.replay_source(source_session_id)
        if source is None:
            return None
        manifest = source["manifest"]
        analyses = self._archive.replay_analyses(source_session_id)
        return {
            "source_session_id": source_session_id,
            "source_id": source["source_id"],
            "content_hash": source["content_hash"],
            "import_status": source["receipt"]["import_status"],
            "manifest": self._public_manifest(manifest),
            "analyses": [self._public_analysis(item) for item in analyses],
        }

    def frame(
        self,
        source_session_id: str,
        at_ms: int | None = None,
        analysis_id: str | None = None,
    ) -> Mapping[str, Any] | None:
        if analysis_id is None:
            # This archive stores derived frames only; do not silently choose an analysis.
            return None
        frame = self._archive.replay_analysis_frame(source_session_id, analysis_id, at_ms)
        if frame is None:
            return None
        return {
            "source_session_id": source_session_id,
            "requested_ms": at_ms,
            "frame_ms": frame["at_ms"],
            "analysis_id": analysis_id,
            "state": self._public_frame(frame),
        }

    def events(
        self,
        source_session_id: str,
        after_ordinal: int = -1,
        until_ms: int | None = None,
        limit: int = 100,
    ) -> Sequence[Mapping[str, Any]]:
        records = self._archive.replay_source_records(
            source_session_id,
            after_ordinal=after_ordinal,
            until_ms=until_ms,
            limit=limit,
        )
        public_records: list[dict[str, Any]] = []
        for record in records:
            event = record["event"]
            public_records.append(
                _public_value(
                    {
                        "source_id": record["source_id"],
                        "source_event_id": record["source_event_id"],
                        "source_time": record["source_time"],
                        "quality": record["quality"],
                        "event": event,
                    }
                )
            )
        return tuple(public_records)


__all__ = [
    "ArchiveReplayEventSource",
    "ReplayImportConflict",
    "ReplayImportError",
    "ReplayImportReceipt",
    "ReplayImportService",
    "ReplayImportValidationError",
    "SQLiteReplayArchiveReader",
    "UnsupportedReplayFormat",
]
