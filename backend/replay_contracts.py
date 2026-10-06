"""Versioned, source-side contracts for offline replay imports.

These DTOs describe imported evidence. They do not authorize a source, infer
freshness, or start any runtime services.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, StrictFloat, StrictInt, StrictStr, field_validator, model_validator

from .models import Contract, Track

SchemaVersion = Literal["replay-1"]
TimeUnit = Literal["ms", "s"]
QualityStatus = Literal["nominal", "missing", "stale", "invalid", "alignment_unknown"]


class ReplaySourceProvenance(Contract):
    owner: StrictStr | None
    version: StrictStr | None
    derivation: StrictStr | None
    retention_reason: StrictStr | None = None


class ReplayPermissionProfile(Contract):
    reference: StrictStr = Field(min_length=1)
    purpose: StrictStr = Field(min_length=1)
    processing_scope: StrictStr = Field(min_length=1)


class ReplayTimebase(Contract):
    source_clock: StrictStr = Field(min_length=1)
    source_unit: TimeUnit
    mapping_id: StrictStr | None
    offset_ms: StrictInt | None
    uncertainty_ms: StrictInt | None
    alignment_status: Literal["aligned", "unknown"]

    @field_validator("uncertainty_ms")
    @classmethod
    def nonnegative_uncertainty(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("uncertainty_ms must be nonnegative")
        return value

    @model_validator(mode="after")
    def aligned_mapping_is_explicit(self) -> ReplayTimebase:
        if self.alignment_status == "aligned" and (
            self.mapping_id is None or self.offset_ms is None or self.uncertainty_ms is None
        ):
            raise ValueError("aligned timebase requires mapping_id, offset_ms, and uncertainty_ms")
        return self


class ReplayCoverageInterval(Contract):
    start_ms: StrictInt = Field(ge=0)
    end_ms: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def ordered_interval(self) -> ReplayCoverageInterval:
        if self.end_ms < self.start_ms:
            raise ValueError("coverage interval end_ms must be >= start_ms")
        return self


class ReplaySourceCoverage(Contract):
    status: Literal["known", "partial", "unknown"]
    object_ids: list[StrictStr] | None
    channel_ids: list[StrictStr] | None
    intervals: list[ReplayCoverageInterval] | None
    missing_intervals: list[ReplayCoverageInterval] | None

    @model_validator(mode="after")
    def preserve_unknown_coverage(self) -> ReplaySourceCoverage:
        fields = (self.object_ids, self.channel_ids, self.intervals, self.missing_intervals)
        if self.status == "unknown" and any(value is not None for value in fields):
            raise ValueError("unknown coverage must use null fields rather than imply empty coverage")
        if self.status != "unknown" and any(value is None for value in fields):
            raise ValueError("known or partial coverage requires explicit lists")
        if self.status == "known" and self.missing_intervals:
            raise ValueError("known coverage cannot contain missing intervals")
        if self.status == "partial" and not self.missing_intervals:
            raise ValueError("partial coverage requires at least one missing interval")
        return self


def _validate_points(value: Any) -> Any:
    """Reject nonnumeric, boolean, and nonfinite geometry coordinates."""
    if not isinstance(value, list):
        raise TypeError("layout geometry must be a list")

    def point(item: Any) -> bool:
        return (
            isinstance(item, (list, tuple))
            and len(item) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in item)
        )

    def line(item: Any) -> bool:
        return isinstance(item, (list, tuple)) and len(item) >= 2 and all(point(p) for p in item)

    # A polygon is a list of points; a collection of lines is a list of polygons/lines.
    if value and point(value[0]):
        if not all(point(item) for item in value):
            raise ValueError("layout geometry contains an invalid point")
    elif not all(line(item) for item in value):
        raise ValueError("layout geometry contains an invalid line")
    return value


class ReplayLayout(Contract):
    id: StrictStr = Field(min_length=1)
    version: StrictStr = Field(min_length=1)
    name: StrictStr = Field(min_length=1)
    coordinate_system: Literal["LOCAL_METRES"]
    physical_runway_id: StrictStr = Field(min_length=1)
    runway: list[tuple[float, float]]
    protected_area: list[tuple[float, float]]
    taxiways: list[list[tuple[float, float]]]
    hold_lines: list[list[tuple[float, float]]]
    directions: dict[Literal["09", "27"], StrictStr]
    note: StrictStr

    @field_validator("runway", "protected_area", "taxiways", "hold_lines", mode="before")
    @classmethod
    def finite_geometry(cls, value: Any) -> Any:
        return _validate_points(value)

    @model_validator(mode="after")
    def both_directions_are_present(self) -> ReplayLayout:
        if set(self.directions) != {"09", "27"}:
            raise ValueError("layout directions must identify both 09 and 27")
        return self


class ReplaySourceManifest(Contract):
    """Manifest for the normalized internal ``replay-1`` source profile."""

    schema_version: SchemaVersion
    source_id: StrictStr = Field(min_length=1)
    source_kind: Literal["synthetic", "authorized_simulator_replay"]
    source_ref: StrictStr = Field(min_length=1)
    content_hash: StrictStr = Field(pattern=r"^[0-9a-fA-F]{64}$")
    provenance: ReplaySourceProvenance
    permission_profile: ReplayPermissionProfile
    retention_until: datetime | None
    timebase: ReplayTimebase
    coverage: ReplaySourceCoverage
    layout: ReplayLayout

    @field_validator("retention_until")
    @classmethod
    def retention_is_utc_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("retention_until must include a timezone")
        return value

    @model_validator(mode="after")
    def null_retention_has_reason(self) -> ReplaySourceManifest:
        if self.retention_until is None and not self.provenance.retention_reason:
            raise ValueError("null retention_until requires an explicit provenance retention_reason")
        return self


class ReplaySourceTime(Contract):
    """Original source clock value; null means missing, never receipt time."""

    value: StrictInt | StrictFloat | None
    unit: TimeUnit
    clock: StrictStr = Field(min_length=1)

    @field_validator("value")
    @classmethod
    def finite_source_time(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("source timestamp must be finite")
        return value


class ReplayEventQuality(Contract):
    status: QualityStatus
    reasons: list[StrictStr]

    @model_validator(mode="after")
    def explain_non_nominal_quality(self) -> ReplayEventQuality:
        if self.status != "nominal" and not self.reasons:
            raise ValueError("non-nominal source quality requires at least one reason")
        return self


class ReplayEventPayload(Contract):
    """Event/session time fields with type-specific source data kept together."""

    id: StrictStr = Field(min_length=1)
    ordinal: StrictInt = Field(ge=0)
    # sim_ms is session availability/receive time, not observed or audit time.
    sim_ms: StrictInt | None = Field(ge=0)
    audit_utc: StrictInt | StrictFloat | None
    type: StrictStr = Field(min_length=1)
    message: StrictStr
    target: StrictStr | None = None
    observed_ms: StrictInt | None = Field(default=None, ge=0)
    received_ms: StrictInt | None = Field(default=None, ge=0)
    track: Track | None = None
    # Remaining type-specific fields are namespaced to keep this envelope strict.
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("track", mode="before")
    @classmethod
    def strict_track_numbers(cls, value: Any) -> Any:
        if value is None or isinstance(value, Track):
            return value
        if not isinstance(value, dict):
            raise TypeError("track must be an object")
        for key in ("x_m", "y_m", "speed_mps", "heading_deg", "length_m", "width_m"):
            coordinate = value.get(key)
            if not isinstance(coordinate, (int, float)) or isinstance(coordinate, bool):
                raise TypeError(f"track.{key} must be numeric")
            if not math.isfinite(coordinate):
                raise ValueError(f"track.{key} must be finite")
        for key in ("observed_ms", "received_ms"):
            timestamp = value.get(key)
            if not isinstance(timestamp, int) or isinstance(timestamp, bool) or timestamp < 0:
                raise ValueError(f"track.{key} must be a nonnegative integer")
        route = value.get("route")
        if not isinstance(route, list):
            raise TypeError("track.route must be a list")
        for point in route:
            if (not isinstance(point, (list, tuple)) or len(point) != 2
                    or any(not isinstance(item, (int, float)) or isinstance(item, bool)
                           or not math.isfinite(item) for item in point)):
                raise ValueError("track.route contains an invalid coordinate")
        return value

    @field_validator("audit_utc")
    @classmethod
    def finite_audit_time(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("audit_utc (epoch seconds) must be finite")
        return value

    @field_validator("data")
    @classmethod
    def finite_json_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        def check(item: Any) -> None:
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("event data contains a nonfinite number")
            if isinstance(item, dict):
                for nested in item.values():
                    check(nested)
            elif isinstance(item, (list, tuple)):
                for nested in item:
                    check(nested)

        check(value)
        return value

    @model_validator(mode="after")
    def finite_track_coordinates(self) -> ReplayEventPayload:
        if self.track is not None:
            numeric = (
                self.track.x_m,
                self.track.y_m,
                self.track.speed_mps,
                self.track.heading_deg,
                self.track.length_m,
                self.track.width_m,
            )
            if not all(math.isfinite(value) for value in numeric):
                raise ValueError("track contains a nonfinite numeric value")
            if not all(math.isfinite(coord) for point in self.track.route for coord in point):
                raise ValueError("track route contains a nonfinite coordinate")
            if self.observed_ms is not None and self.track.observed_ms != self.observed_ms:
                raise ValueError("event observed_ms must match the normalized track observation time")
            if self.received_ms is not None and self.track.received_ms != self.received_ms:
                raise ValueError("event received_ms must match the normalized track receipt time")
        return self


class ReplayEventRecord(Contract):
    """Immutable event identity and source time sidecar for a replay record."""

    schema_version: SchemaVersion
    source_id: StrictStr = Field(min_length=1)
    source_event_id: StrictStr = Field(min_length=1)
    source_time: ReplaySourceTime
    event: ReplayEventPayload
    quality: ReplayEventQuality

    @model_validator(mode="after")
    def event_identity_is_preserved(self) -> ReplayEventRecord:
        if self.event.id != self.source_event_id:
            raise ValueError("event.id must preserve source_event_id")
        if self.event.sim_ms is None and self.quality.status != "alignment_unknown":
            raise ValueError("an event without session time must retain alignment_unknown quality")
        return self


__all__ = [
    "QualityStatus",
    "ReplayCoverageInterval",
    "ReplayEventPayload",
    "ReplayEventQuality",
    "ReplayEventRecord",
    "ReplayLayout",
    "ReplayPermissionProfile",
    "ReplaySourceCoverage",
    "ReplaySourceManifest",
    "ReplaySourceProvenance",
    "ReplaySourceTime",
    "ReplayTimebase",
    "SchemaVersion",
]
