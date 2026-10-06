"""Read normalized replay records and reduce their public observed state.

This module is deliberately independent from ``Session`` and ``Simulator``.
It reads only a ``ReplayEventSource`` and calls injected detector/lifecycle
ports; it never opens storage or imports scenario data.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

from pydantic import ValidationError

from .models import Clearance, SimulationConfig, Track
from .ports import AlertLifecyclePort, DetectorPort, ReplayEventSource
from .replay_contracts import ReplayEventRecord, ReplayLayout, ReplaySourceCoverage, ReplaySourceManifest


class ReplaySourceError(ValueError):
    """A source violates the normalized replay contract."""


class ReplayImportConflict(ReplaySourceError):
    """A source event identity was repeated with a different payload."""


@dataclass(frozen=True)
class SourceEventRef:
    source_id: str
    source_event_id: str
    ordinal: int
    event_type: str
    sim_ms: int | None
    observed_ms: int | None = None
    received_ms: int | None = None


@dataclass(frozen=True)
class UnresolvedSourceEvent:
    ref: SourceEventRef
    reason: str
    quality_status: str


@dataclass(frozen=True)
class NativeSourceAlert:
    """A source-owned alert projection, kept apart from detector output."""

    ref: SourceEventRef
    available_ms: int
    message: str
    target: str | None
    data: Mapping[str, Any]
    quality_status: str


@dataclass(frozen=True)
class ObservedState:
    """Public, time-bounded observations; no simulator truth or checkpoint."""

    source_id: str
    source_ref: str
    as_of_ms: int | None
    coverage: ReplaySourceCoverage
    coverage_status: Literal["known", "partial", "unknown"]
    tracks: Mapping[str, Track] = field(default_factory=dict)
    previous_tracks: Mapping[str, Track] = field(default_factory=dict)
    clearances: tuple[Clearance, ...] = ()
    requests: tuple[Mapping[str, Any], ...] = ()
    readbacks: tuple[Mapping[str, Any], ...] = ()
    coordination_events: tuple[Mapping[str, Any], ...] = ()
    runway_open: bool | None = None
    runway_configuration_events: tuple[Mapping[str, Any], ...] = ()
    native_source_alerts: tuple[NativeSourceAlert, ...] = ()
    control_receipts: tuple[SourceEventRef, ...] = ()
    track_history: tuple[SourceEventRef, ...] = ()
    source_event_refs: tuple[SourceEventRef, ...] = ()
    unresolved_records: tuple[UnresolvedSourceEvent, ...] = ()
    track_source_quality: Mapping[str, str] = field(default_factory=dict)
    track_freshness: Mapping[str, Literal["fresh", "stale", "unknown"]] = field(default_factory=dict)
    quality_reasons: tuple[str, ...] = ()

    @property
    def data_quality(self) -> Literal["nominal", "degraded"]:
        return "degraded" if self.coverage_status != "known" or self.quality_reasons else "nominal"

    def public_projection(self) -> dict[str, Any]:
        """Return a JSON-ready projection with no source payload/private state."""
        return {
            "source_id": self.source_id,
            "source_ref": self.source_ref,
            "as_of_ms": self.as_of_ms,
            "coverage": self.coverage.model_dump(mode="json"),
            "coverage_status": self.coverage_status,
            "tracks": {object_id: track.model_dump(mode="json") for object_id, track in self.tracks.items()},
            "previous_tracks": {
                object_id: track.model_dump(mode="json") for object_id, track in self.previous_tracks.items()
            },
            "clearances": [clearance.model_dump(mode="json") for clearance in self.clearances],
            "requests": copy.deepcopy(list(self.requests)),
            "readbacks": copy.deepcopy(list(self.readbacks)),
            "coordination_events": copy.deepcopy(list(self.coordination_events)),
            "runway": {
                "open": self.runway_open,
                "configuration_events": copy.deepcopy(list(self.runway_configuration_events)),
            },
            "native_source_alerts": [
                {
                    "source_id": item.ref.source_id,
                    "source_event_id": item.ref.source_event_id,
                    "ordinal": item.ref.ordinal,
                    "sim_ms": item.ref.sim_ms,
                    "available_ms": item.available_ms,
                    "type": item.ref.event_type,
                    "target": item.target,
                    "message": item.message,
                    "data": copy.deepcopy(dict(item.data)),
                    "quality_status": item.quality_status,
                }
                for item in self.native_source_alerts
            ],
            "control_receipts": [_ref_dict(ref) for ref in self.control_receipts],
            "track_history": [_ref_dict(ref) for ref in self.track_history],
            "source_event_refs": [_ref_dict(ref) for ref in self.source_event_refs],
            "unresolved_records": [
                {**_ref_dict(item.ref), "reason": item.reason, "quality_status": item.quality_status}
                for item in self.unresolved_records
            ],
            "track_source_quality": dict(self.track_source_quality),
            "track_freshness": dict(self.track_freshness),
            "data_quality": self.data_quality,
            "quality_reasons": list(self.quality_reasons),
        }


@dataclass(frozen=True)
class ReplayAnalysisMetadata:
    id: str
    source_id: str
    source_session_id: str
    kind: Literal["detector"]
    input_hash: str
    versions: Mapping[str, Any]
    window_start_ms: int
    window_end_ms: int
    status: Literal["completed", "completed_degraded", "partial"]


@dataclass(frozen=True)
class ReplayAnalysisFrame:
    analysis_id: str
    at_ms: int
    state: ObservedState
    detector_result: Mapping[str, Any] | None
    alerts: Mapping[str, Mapping[str, Any]]
    lifecycle_events: tuple[Mapping[str, Any], ...]
    status: Literal[
        "evaluated",
        "skipped_unknown_coverage",
        "skipped_outside_coverage",
        "skipped_unknown_runway_configuration",
    ]
    layout_binding: Literal["source_layout_parameter", "not_exposed_by_detector_port"]

    def public_projection(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "at_ms": self.at_ms,
            "state": self.state.public_projection(),
            "detector_result": copy.deepcopy(dict(self.detector_result)) if self.detector_result is not None else None,
            "alerts": copy.deepcopy(dict(self.alerts)),
            "lifecycle_events": copy.deepcopy(list(self.lifecycle_events)),
            "status": self.status,
            "layout_binding": self.layout_binding,
        }


@dataclass(frozen=True)
class ReplayAnalysis:
    metadata: ReplayAnalysisMetadata
    frames: tuple[ReplayAnalysisFrame, ...]


class ReplayLayoutAwareDetectorPort(Protocol):
    """Optional structural extension until the shared detector port carries layout."""

    def evaluate_with_layout(
        self,
        *,
        tracks: dict[str, Track],
        clearances: list[Clearance],
        now_ms: int,
        config: SimulationConfig,
        runway_open: bool,
        expected_ids: list[str],
        previous_tracks: dict[str, Track],
        layout: ReplayLayout,
    ) -> Mapping[str, Any]: ...


def _record_fingerprint(record: ReplayEventRecord) -> str:
    payload = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _availability_ms(record: ReplayEventRecord, manifest: ReplaySourceManifest) -> int | None:
    if manifest.timebase.alignment_status != "aligned" or record.quality.status == "alignment_unknown":
        return None
    event = record.event
    if event.sim_ms is None:
        return None
    times = [event.sim_ms]
    if event.received_ms is not None:
        times.append(event.received_ms)
    if event.track is not None:
        times.append(event.track.received_ms)
    return max(times)


def _source_ref(record: ReplayEventRecord) -> SourceEventRef:
    event = record.event
    observed_ms = event.observed_ms
    received_ms = event.received_ms
    if event.track is not None:
        observed_ms = event.track.observed_ms if observed_ms is None else observed_ms
        received_ms = event.track.received_ms if received_ms is None else received_ms
    return SourceEventRef(
        source_id=record.source_id,
        source_event_id=record.source_event_id,
        ordinal=event.ordinal,
        event_type=event.type,
        sim_ms=event.sim_ms,
        observed_ms=observed_ms,
        received_ms=received_ms,
    )


def _ref_dict(ref: SourceEventRef) -> dict[str, Any]:
    return {
        "source_id": ref.source_id,
        "source_event_id": ref.source_event_id,
        "ordinal": ref.ordinal,
        "event_type": ref.event_type,
        "sim_ms": ref.sim_ms,
        "observed_ms": ref.observed_ms,
        "received_ms": ref.received_ms,
    }


class ReplaySourceReader:
    """Read, validate, deduplicate, and deterministically order one source."""

    def __init__(self, source: ReplayEventSource) -> None:
        self._source = source
        self._manifest: ReplaySourceManifest | None = None
        self._seen: dict[tuple[str, str], str] = {}

    def manifest(self) -> ReplaySourceManifest:
        if self._manifest is None:
            self._manifest = self._source.manifest()
        return self._manifest

    def read(self, after_ordinal: int = -1, until_ms: int | None = None) -> tuple[ReplayEventRecord, ...]:
        if after_ordinal < -1:
            raise ValueError("after_ordinal must be -1 or greater")
        if until_ms is not None and until_ms < 0:
            raise ValueError("until_ms must be nonnegative")
        manifest = self.manifest()
        raw_records = self._source.read(after_ordinal, until_ms)
        unique: list[ReplayEventRecord] = []
        page_fingerprints: dict[tuple[str, str], str] = {}
        for record in raw_records:
            if record.source_id != manifest.source_id:
                raise ReplaySourceError(
                    f"record source_id {record.source_id!r} does not match manifest {manifest.source_id!r}"
                )
            if record.event.ordinal <= after_ordinal:
                continue
            if until_ms is not None and record.event.sim_ms is not None and record.event.sim_ms > until_ms:
                continue
            availability = _availability_ms(record, manifest)
            if until_ms is not None and availability is not None and availability > until_ms:
                continue
            identity = (record.source_id, record.source_event_id)
            fingerprint = _record_fingerprint(record)
            previous = self._seen.get(identity)
            if previous is not None and previous != fingerprint:
                raise ReplayImportConflict(
                    f"conflicting payloads for source event {record.source_id}:{record.source_event_id}"
                )
            in_page = page_fingerprints.get(identity)
            if in_page is not None:
                if in_page != fingerprint:
                    raise ReplayImportConflict(
                        f"conflicting payloads for source event {record.source_id}:{record.source_event_id}"
                    )
                continue
            page_fingerprints[identity] = fingerprint
            self._seen.setdefault(identity, fingerprint)
            unique.append(record.model_copy(deep=True))
        unique.sort(
            key=lambda record: (
                _availability_ms(record, manifest) is None,
                _availability_ms(record, manifest) if _availability_ms(record, manifest) is not None else 0,
                record.event.ordinal,
                record.source_event_id,
            )
        )
        return tuple(unique)

    def normalize(
        self, records: Sequence[ReplayEventRecord], manifest: ReplaySourceManifest | None = None
    ) -> tuple[ReplayEventRecord, ...]:
        """Normalize an already-read page or an in-memory fixture consistently."""
        active_manifest = manifest or self.manifest()
        deduped: dict[tuple[str, str], ReplayEventRecord] = {}
        fingerprints: dict[tuple[str, str], str] = {}
        for record in records:
            if record.source_id != active_manifest.source_id:
                raise ReplaySourceError(
                    f"record source_id {record.source_id!r} does not match manifest {active_manifest.source_id!r}"
                )
            identity = (record.source_id, record.source_event_id)
            fingerprint = _record_fingerprint(record)
            if identity in fingerprints:
                if fingerprints[identity] != fingerprint:
                    raise ReplayImportConflict(
                        f"conflicting payloads for source event {record.source_id}:{record.source_event_id}"
                    )
                continue
            fingerprints[identity] = fingerprint
            deduped[identity] = record
        normalized = list(deduped.values())
        normalized.sort(
            key=lambda record: (
                _availability_ms(record, active_manifest) is None,
                _availability_ms(record, active_manifest)
                if _availability_ms(record, active_manifest) is not None
                else 0,
                record.event.ordinal,
                record.source_event_id,
            )
        )
        return tuple(normalized)


@dataclass
class _StateDraft:
    tracks: dict[str, Track] = field(default_factory=dict)
    previous_tracks: dict[str, Track] = field(default_factory=dict)
    track_order: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    clearances: dict[str, Clearance] = field(default_factory=dict)
    requests: list[dict[str, Any]] = field(default_factory=list)
    readbacks: list[dict[str, Any]] = field(default_factory=list)
    coordination_events: list[dict[str, Any]] = field(default_factory=list)
    runway_open: bool | None = None
    runway_configuration_events: list[dict[str, Any]] = field(default_factory=list)
    native_source_alerts: list[NativeSourceAlert] = field(default_factory=list)
    control_receipts: list[SourceEventRef] = field(default_factory=list)
    track_history: list[SourceEventRef] = field(default_factory=list)
    source_event_refs: list[SourceEventRef] = field(default_factory=list)
    unresolved_records: list[UnresolvedSourceEvent] = field(default_factory=list)
    track_source_quality: dict[str, str] = field(default_factory=dict)
    quality_reasons: list[str] = field(default_factory=list)


class ObservedStateReducer:
    """Pure reducer over immutable replay records and manifest coverage."""

    def __init__(self, reader: ReplaySourceReader, stale_after_ms: int = 3000) -> None:
        if stale_after_ms < 0:
            raise ValueError("stale_after_ms must be nonnegative")
        self.reader = reader
        self.manifest = reader.manifest()
        self.stale_after_ms = stale_after_ms

    def build_state(
        self,
        at_ms: int | None,
        *,
        records: Sequence[ReplayEventRecord] | None = None,
    ) -> ObservedState:
        """Rebuild a source-only state as of replay time; later records are excluded."""
        if at_ms is not None and at_ms < 0:
            raise ValueError("at_ms must be nonnegative or None")
        source_records = tuple(records) if records is not None else self.reader.read(-1, at_ms)
        normalized = self.reader.normalize(source_records, self.manifest)
        draft = _StateDraft()
        applicable_times: list[int] = []
        for record in normalized:
            ref = _source_ref(record)
            available_ms = _availability_ms(record, self.manifest)
            if available_ms is None:
                draft.unresolved_records.append(
                    UnresolvedSourceEvent(
                        ref=ref,
                        reason="unsupported_alignment" if self.manifest.timebase.alignment_status != "aligned"
                        or record.quality.status == "alignment_unknown" else "unmapped_time",
                        quality_status=record.quality.status,
                    )
                )
                draft.quality_reasons.append("source_time_unresolved")
                continue
            if at_ms is not None and available_ms > at_ms:
                continue
            applicable_times.append(available_ms)
            draft.source_event_refs.append(ref)
            _apply_source_event(draft, record, ref, available_ms, self.manifest.layout.physical_runway_id)

        resolved_at_ms = at_ms if at_ms is not None else (max(applicable_times) if applicable_times else None)
        coverage_status = _coverage_status(self.manifest.coverage, resolved_at_ms)
        if coverage_status != "known":
            draft.quality_reasons.append(f"coverage_{coverage_status}")
        freshness: dict[str, Literal["fresh", "stale", "unknown"]] = {}
        if resolved_at_ms is not None:
            for object_id, track in draft.tracks.items():
                age = max(0, resolved_at_ms - track.received_ms)
                source_stale = draft.track_source_quality.get(object_id) == "stale"
                freshness[object_id] = "stale" if source_stale or age > self.stale_after_ms else "fresh"
        return ObservedState(
            source_id=self.manifest.source_id,
            source_ref=self.manifest.source_ref,
            as_of_ms=resolved_at_ms,
            coverage=self.manifest.coverage,
            coverage_status=coverage_status,
            tracks=dict(draft.tracks),
            previous_tracks=dict(draft.previous_tracks),
            clearances=tuple(draft.clearances.values()),
            requests=tuple(copy.deepcopy(draft.requests)),
            readbacks=tuple(copy.deepcopy(draft.readbacks)),
            coordination_events=tuple(copy.deepcopy(draft.coordination_events)),
            runway_open=draft.runway_open,
            runway_configuration_events=tuple(copy.deepcopy(draft.runway_configuration_events)),
            native_source_alerts=tuple(draft.native_source_alerts),
            control_receipts=tuple(draft.control_receipts),
            track_history=tuple(draft.track_history),
            source_event_refs=tuple(draft.source_event_refs),
            unresolved_records=tuple(draft.unresolved_records),
            track_source_quality=dict(draft.track_source_quality),
            track_freshness=freshness,
            quality_reasons=tuple(dict.fromkeys(draft.quality_reasons)),
        )

    def normalize(
        self, records: Sequence[ReplayEventRecord], manifest: ReplaySourceManifest | None = None
    ) -> tuple[ReplayEventRecord, ...]:
        """Validate identity, collapse identical duplicates, and order receive-time ties."""
        active_manifest = manifest or self.manifest()
        deduped: dict[tuple[str, str], ReplayEventRecord] = {}
        fingerprints: dict[tuple[str, str], str] = {}
        for record in records:
            if record.source_id != active_manifest.source_id:
                raise ReplaySourceError(
                    f"record source_id {record.source_id!r} does not match manifest {active_manifest.source_id!r}"
                )
            identity = (record.source_id, record.source_event_id)
            fingerprint = _record_fingerprint(record)
            if identity in fingerprints:
                if fingerprints[identity] != fingerprint:
                    raise ReplayImportConflict(
                        f"conflicting payloads for source event {record.source_id}:{record.source_event_id}"
                    )
                continue
            fingerprints[identity] = fingerprint
            deduped[identity] = record
        normalized = list(deduped.values())
        normalized.sort(
            key=lambda record: (
                _availability_ms(record, active_manifest) is None,
                _availability_ms(record, active_manifest) if _availability_ms(record, active_manifest) is not None else 0,
                record.event.ordinal,
                record.source_event_id,
            )
        )
        return tuple(normalized)


def _coverage_status(coverage: ReplaySourceCoverage, at_ms: int | None) -> Literal["known", "partial", "unknown"]:
    if coverage.status == "unknown" or at_ms is None:
        return "unknown"
    in_coverage = any(interval.start_ms <= at_ms <= interval.end_ms for interval in coverage.intervals or [])
    if not in_coverage:
        return "unknown"
    in_missing_interval = any(
        interval.start_ms <= at_ms <= interval.end_ms for interval in coverage.missing_intervals or []
    )
    if coverage.status == "partial" or in_missing_interval:
        return "partial"
    return "known"


def _unresolved(draft: _StateDraft, ref: SourceEventRef, record: ReplayEventRecord, reason: str) -> None:
    draft.unresolved_records.append(UnresolvedSourceEvent(ref, reason, record.quality.status))
    draft.quality_reasons.append(reason)


def _namespaced_event_id(source_id: str, event_id: str) -> str:
    return f"{source_id}:{event_id}"


def _apply_source_event(
    draft: _StateDraft,
    record: ReplayEventRecord,
    ref: SourceEventRef,
    available_ms: int,
    physical_runway_id: str,
) -> None:
    event = record.event
    event_type = event.type
    if record.quality.status == "invalid":
        _unresolved(draft, ref, record, "invalid_source_quality")
        return
    if record.quality.status in {"missing", "stale"}:
        draft.quality_reasons.append(f"source_quality_{record.quality.status}")

    if event_type == "TRACK":
        track = event.track
        if track is None:
            _unresolved(draft, ref, record, "track_payload_missing")
            return
        if event.target is not None and event.target != track.id:
            _unresolved(draft, ref, record, "track_target_id_mismatch")
            return
        draft.track_history.append(ref)
        ordering = (track.observed_ms, available_ms, event.ordinal)
        previous_order = draft.track_order.get(track.id)
        if previous_order is not None and ordering <= previous_order:
            draft.quality_reasons.append("out_of_order_track_ignored")
            return
        old = draft.tracks.get(track.id)
        if old is not None:
            draft.previous_tracks[track.id] = old
        namespaced = track.model_copy(update={"event_id": _namespaced_event_id(record.source_id, record.source_event_id)})
        draft.tracks[track.id] = namespaced
        draft.track_order[track.id] = ordering
        draft.track_source_quality[track.id] = record.quality.status
        return

    if event_type == "CLEARANCE":
        data = event.data
        target = event.target
        instruction = data.get("instruction")
        runway = data.get("runway")
        issuer = data.get("issuer")
        if not target or not isinstance(instruction, str) or not isinstance(runway, str) or not isinstance(issuer, str):
            _unresolved(draft, ref, record, "clearance_fields_missing")
            return
        try:
            clearance = Clearance.model_validate(
                {
                    "id": _namespaced_event_id(record.source_id, record.source_event_id),
                    "target": target,
                    "instruction": instruction,
                    "runway": runway,
                    "issued_ms": available_ms,
                    "issuer": issuer,
                    "status": data.get("status", "ISSUED"),
                    "readback": data.get("readback", "PENDING"),
                    "event_id": _namespaced_event_id(record.source_id, record.source_event_id),
                }
            )
        except (ValidationError, TypeError, ValueError):
            _unresolved(draft, ref, record, "clearance_fields_unsupported")
            return
        for clearance_id, old in tuple(draft.clearances.items()):
            if old.target == target and old.status == "ISSUED":
                draft.clearances[clearance_id] = old.model_copy(update={"status": "SUPERSEDED"})
        draft.clearances[clearance.id] = clearance
        return

    if event_type == "CANCEL":
        target = event.target
        active = next((item for item in reversed(tuple(draft.clearances.values()))
                       if item.target == target and item.status == "ISSUED"), None)
        if not target or active is None:
            _unresolved(draft, ref, record, "cancel_without_active_clearance")
            return
        draft.clearances[active.id] = active.model_copy(update={"status": "CANCELLED"})
        return

    if event_type == "READBACK":
        data = event.data
        target = event.target
        readback = data.get("readback")
        item: dict[str, Any] = {
            "source_id": record.source_id,
            "source_event_id": record.source_event_id,
            "target": target,
            "received_ms": available_ms,
            "readback": readback if isinstance(readback, str) else None,
        }
        draft.readbacks.append(item)
        if isinstance(readback, str):
            active = next((value for value in reversed(tuple(draft.clearances.values()))
                           if value.target == target and value.status == "ISSUED"), None)
            if active is None or readback not in {"PENDING", "ACKNOWLEDGED", "MISMATCH_RECORDED"}:
                _unresolved(draft, ref, record, "readback_unmatched_or_unsupported")
                return
            draft.clearances[active.id] = active.model_copy(update={"readback": readback})
        return

    if event_type in {"COORDINATION", "REQUEST_CROSSING"}:
        data = event.data
        coordination = {
            "source_id": record.source_id,
            "source_event_id": record.source_event_id,
            "target": event.target,
            "received_ms": available_ms,
            "kind": data.get("kind") or data.get("request_type"),
            "channel": data.get("channel"),
            "issuer": data.get("issuer"),
        }
        draft.coordination_events.append(coordination)
        request_kind = coordination["kind"]
        if request_kind is not None and not isinstance(request_kind, str):
            _unresolved(draft, ref, record, "coordination_kind_unsupported")
            return
        if event_type == "REQUEST_CROSSING" or request_kind in {"RUNWAY_CROSSING_REQUEST", "CROSSING_REQUEST"}:
            if not event.target:
                _unresolved(draft, ref, record, "crossing_request_target_missing")
                return
            completed = data.get("completed", False)
            if not isinstance(completed, bool):
                _unresolved(draft, ref, record, "crossing_request_status_unsupported")
                return
            draft.requests.append(
                {
                    "id": _namespaced_event_id(record.source_id, record.source_event_id),
                    "target": event.target,
                    "requested_ms": available_ms,
                    "completed": completed,
                }
            )
        return

    if event_type in {"RUNWAY_OPEN", "RUNWAY_CLOSED", "RUNWAY_CONFIG", "RUNWAY_CONFIGURATION", "RUNWAY_STATUS"}:
        data = event.data
        if event_type == "RUNWAY_OPEN":
            is_open: bool | None = True
        elif event_type == "RUNWAY_CLOSED":
            is_open = False
        else:
            raw_open = data.get("runway_open", data.get("open"))
            raw_status = data.get("status")
            if isinstance(raw_open, bool):
                is_open = raw_open
            elif raw_status == "OPEN":
                is_open = True
            elif raw_status == "CLOSED":
                is_open = False
            else:
                is_open = None
        runway_id = data.get("physical_runway_id")
        if is_open is None or (runway_id is not None and runway_id != physical_runway_id):
            _unresolved(draft, ref, record, "runway_configuration_unmapped")
            return
        draft.runway_open = is_open
        draft.runway_configuration_events.append(
            {
                "source_id": record.source_id,
                "source_event_id": record.source_event_id,
                "available_ms": available_ms,
                "runway_open": is_open,
                "physical_runway_id": runway_id,
            }
        )
        return

    if event_type == "COMMAND":
        # A command is retained as a receipt. Its resulting structured event is
        # the only input that may change observed state.
        draft.control_receipts.append(ref)
        return

    if event_type.startswith("ALERT_"):
        draft.native_source_alerts.append(
            NativeSourceAlert(
                ref=ref,
                available_ms=available_ms,
                message=event.message,
                target=event.target,
                data=copy.deepcopy(event.data),
                quality_status=record.quality.status,
            )
        )
        return

    _unresolved(draft, ref, record, "unsupported_event_type")


def _detector_layout_evaluate(
    detector: DetectorPort,
    *,
    tracks: dict[str, Track],
    clearances: list[Clearance],
    now_ms: int,
    config: SimulationConfig,
    runway_open: bool,
    expected_ids: list[str],
    previous_tracks: dict[str, Track],
    layout: ReplayLayout,
) -> tuple[Mapping[str, Any], Literal["source_layout_parameter", "not_exposed_by_detector_port"]]:
    """Use an optional layout-aware structural adapter, then BE-01's base port."""
    layout_evaluator = getattr(detector, "evaluate_with_layout", None)
    if callable(layout_evaluator):
        result = cast(ReplayLayoutAwareDetectorPort, detector).evaluate_with_layout(
            tracks=tracks,
            clearances=clearances,
            now_ms=now_ms,
            config=config,
            runway_open=runway_open,
            expected_ids=expected_ids,
            previous_tracks=previous_tracks,
            layout=layout,
        )
        return result, "source_layout_parameter"
    result = detector.evaluate(
        tracks=tracks,
        clearances=clearances,
        now_ms=now_ms,
        config=config,
        runway_open=runway_open,
        expected_ids=expected_ids,
        previous_tracks=previous_tracks,
    )
    return result, "not_exposed_by_detector_port"


def build_replay_analysis(
    reader: ReplaySourceReader,
    detector: DetectorPort,
    lifecycle: AlertLifecyclePort,
    *,
    config: SimulationConfig,
    window_start_ms: int,
    window_end_ms: int,
    source_session_id: str,
    analysis_id: str | None = None,
    config_version: str | None = None,
) -> ReplayAnalysis:
    """Build in-memory, time-causal detector frames for one replay window."""
    if window_start_ms < 0 or window_end_ms < window_start_ms:
        raise ValueError("analysis window must be nonnegative and ordered")
    if not source_session_id:
        raise ValueError("source_session_id must be provided for analysis provenance")
    manifest = reader.manifest()
    records = reader.read(-1, window_end_ms)
    reducer = ObservedStateReducer(reader, stale_after_ms=config.stale_ms)
    run_id = analysis_id or f"analysis-{uuid.uuid4().hex}"
    active_alerts: dict[str, dict[str, Any]] = {}
    lifecycle_ordinal = 0
    frames: list[ReplayAnalysisFrame] = []
    known_versions: dict[str, Any] = {
        "schema_version": manifest.schema_version,
        "layout_version": manifest.layout.version,
    }
    source_version = manifest.provenance.version
    if source_version is not None:
        known_versions["source_version"] = source_version
    if config_version is not None:
        known_versions["config_version"] = config_version
    detector_version = getattr(detector, "version", None)
    if isinstance(detector_version, str):
        known_versions["detector_version"] = detector_version
    engine_version = getattr(detector, "engine_version", None)
    if isinstance(engine_version, str):
        known_versions["engine_version"] = engine_version

    def append_frame(at_ms: int) -> None:
        nonlocal lifecycle_ordinal
        state = reducer.build_state(at_ms, records=records)
        result: Mapping[str, Any] | None = None
        frame_events: list[dict[str, Any]] = []
        layout_binding: Literal["source_layout_parameter", "not_exposed_by_detector_port"] = (
            "not_exposed_by_detector_port"
        )
        if state.coverage_status == "unknown":
            frame_status: Literal[
                "evaluated", "skipped_unknown_coverage", "skipped_outside_coverage", "skipped_unknown_runway_configuration"
            ] = "skipped_unknown_coverage" if manifest.coverage.status == "unknown" else "skipped_outside_coverage"
        elif state.runway_open is None:
            frame_status = "skipped_unknown_runway_configuration"
        else:
            coverage_ids = manifest.coverage.object_ids
            if coverage_ids is None:
                frame_status = "skipped_unknown_coverage"
            else:
                result, layout_binding = _detector_layout_evaluate(
                    detector,
                    tracks=dict(state.tracks),
                    clearances=list(state.clearances),
                    now_ms=at_ms,
                    config=config,
                    runway_open=state.runway_open,
                    expected_ids=list(dict.fromkeys(coverage_ids)),
                    previous_tracks=dict(state.previous_tracks),
                    layout=manifest.layout,
                )
                for prediction in result.get("predictions", ()):
                    version = prediction.get("model_version") if isinstance(prediction, Mapping) else None
                    if isinstance(version, str):
                        known_versions.setdefault("model_versions", set()).add(version)
                for candidate in result.get("candidates", ()):
                    version = candidate.get("rule_version") if isinstance(candidate, Mapping) else None
                    if isinstance(version, str):
                        known_versions.setdefault("rule_versions", set()).add(version)
                if state.coverage_status == "known":
                    def emit_event(event_type: str, message: str, **fields: Any) -> dict[str, Any]:
                        nonlocal lifecycle_ordinal
                        lifecycle_ordinal += 1
                        event = {
                            "id": f"{run_id}:lifecycle:{lifecycle_ordinal}",
                            "ordinal": lifecycle_ordinal,
                            "sim_ms": at_ms,
                            "type": event_type,
                            "message": message,
                            **copy.deepcopy(fields),
                        }
                        frame_events.append(event)
                        return event

                    lifecycle.update(active_alerts, result, at_ms, emit_event)
                frame_status = "evaluated"
        frames.append(
            ReplayAnalysisFrame(
                analysis_id=run_id,
                at_ms=at_ms,
                state=state,
                detector_result=copy.deepcopy(dict(result)) if result is not None else None,
                alerts=copy.deepcopy(active_alerts),
                lifecycle_events=tuple(frame_events),
                status=frame_status,
                layout_binding=layout_binding,
            )
        )

    append_frame(window_start_ms)
    evaluation_times = sorted(
        {
            available
            for record in records
            if (available := _availability_ms(record, manifest)) is not None
            and window_start_ms < available <= window_end_ms
        }
    )
    for timestamp in evaluation_times:
        append_frame(timestamp)

    normalized_versions: dict[str, Any] = {}
    for key, value in known_versions.items():
        if isinstance(value, set):
            normalized_versions[key] = sorted(value)
        else:
            normalized_versions[key] = value
    input_material = {
        "source_id": manifest.source_id,
        "source_content_hash": manifest.content_hash,
        "config": config.model_dump(mode="json"),
        "config_version": config_version,
        "versions": normalized_versions,
        "window_start_ms": window_start_ms,
        "window_end_ms": window_end_ms,
    }
    input_hash = hashlib.sha256(
        json.dumps(input_material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    any_evaluated = any(frame.detector_result is not None for frame in frames)
    any_degraded = any(
        frame.state.data_quality == "degraded"
        or frame.layout_binding == "not_exposed_by_detector_port"
        or frame.status != "evaluated"
        for frame in frames
    )
    status: Literal["completed", "completed_degraded", "partial"] = (
        "partial" if not any_evaluated else "completed_degraded" if any_degraded else "completed"
    )
    metadata = ReplayAnalysisMetadata(
        id=run_id,
        source_id=manifest.source_id,
        source_session_id=source_session_id,
        kind="detector",
        input_hash=input_hash,
        versions=normalized_versions,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        status=status,
    )
    return ReplayAnalysis(metadata=metadata, frames=tuple(frames))


__all__ = [
    "NativeSourceAlert",
    "ObservedState",
    "ObservedStateReducer",
    "ReplayAnalysis",
    "ReplayAnalysisFrame",
    "ReplayAnalysisMetadata",
    "ReplayImportConflict",
    "ReplayLayoutAwareDetectorPort",
    "ReplaySourceError",
    "ReplaySourceReader",
    "SourceEventRef",
    "UnresolvedSourceEvent",
    "build_replay_analysis",
]
