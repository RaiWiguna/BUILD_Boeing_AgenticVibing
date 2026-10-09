"""Evidence-bound occupancy. Linear models describe possibilities, never operational clearance."""

import math
from dataclasses import asdict, dataclass
from uuid import UUID

from flowlens.contracts.models import GeometryResult, RequestContext, TimeRange, Track
from flowlens.core.errors import ContractError
from flowlens.evidence.registry import EvidenceRegistry
from flowlens.geometry.kernel import GEOMETRY_VERSION, Geometry, Resource, footprint
from flowlens.imports.metadata import PreparedImport, hashed
from flowlens.sources.store import Sources
from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


@dataclass(frozen=True)
class Policy:
    horizon_ms: int = 30000
    stale_ms: int = 5000
    gap_ms: int = 5000
    temporal_margin_ms: int = 0
    protection_margin_m: float = 0.0
    speed_floor_mps: float = 0.05
    max_speed_mps: float = 400.0
    max_clock_uncertainty_ms: int = 1000
    version: str = "occupancy-1"

    def __post_init__(self) -> None:
        for key in (
            "horizon_ms",
            "stale_ms",
            "gap_ms",
            "temporal_margin_ms",
            "max_clock_uncertainty_ms",
        ):
            value = getattr(self, key)
            if (
                type(value) is not int
                or value < (0 if key in ("temporal_margin_ms", "max_clock_uncertainty_ms") else 1)
                or value > 3600000
            ):
                raise ValueError("Invalid bounded time policy")
        for key in ("protection_margin_m", "speed_floor_mps", "max_speed_mps"):
            value = getattr(self, key)
            if (
                type(value) not in (float, int)
                or not math.isfinite(value)
                or value < (0 if key == "protection_margin_m" else 1e-9)
            ):
                raise ValueError("Invalid metric policy")
        if (
            self.protection_margin_m > 100000
            or self.max_speed_mps > 400
            or self.speed_floor_mps > self.max_speed_mps
            or self.version != "occupancy-1"
        ):
            raise ValueError("Unsupported policy")


@dataclass(frozen=True)
class Forecast:
    intervals: list[TimeRange]
    eta_ms: int | None
    exit_ms: int | None
    unknown: bool
    exit_unknown: bool


def merge(ranges: list[TimeRange]) -> list[TimeRange]:
    result: list[TimeRange] = []
    for r in sorted(ranges, key=lambda x: (x.start_ms, x.end_ms)):
        if result and r.start_ms <= result[-1].end_ms:
            result[-1] = TimeRange(
                start_ms=result[-1].start_ms, end_ms=max(r.end_ms, result[-1].end_ms)
            )
        else:
            result.append(r)
    return result


def overlap(a: list[TimeRange], b: list[TimeRange]) -> int:
    return sum(
        max(0, min(x.end_ms, y.end_ms) - max(x.start_ms, y.start_ms))
        for x in merge(a)
        for y in merge(b)
    )


def _fractions(
    g: Geometry, start: Track, end: Track, resource: Resource
) -> list[tuple[float, float]]:
    sweep = g.sweep(start, end)
    region = g.region(resource)
    if not sweep.exact:
        raise ContractError("NOT_EVALUABLE")
    # Decompose concave polygons first; Minkowski addition distributes over the union.
    offsets = [(start.x_m - x, start.y_m - y) for x, y in footprint(start).exterior.coords[:-1]]
    pieces = constrained_delaunay_triangles(region)
    expanded = unary_union(
        [
            MultiPoint(
                [(x + dx, y + dy) for x, y in p.exterior.coords[:-1] for dx, dy in offsets]
            ).convex_hull
            for p in pieces.geoms
            if isinstance(p, Polygon)
        ]
    )
    if (start.x_m, start.y_m) == (end.x_m, end.y_m):
        return [(0.0, 1.0)] if expanded.intersects(Point(start.x_m, start.y_m)) else []
    path = LineString([(start.x_m, start.y_m), (end.x_m, end.y_m)])
    intersection = expanded.intersection(path)

    def pieces_of(shape: BaseGeometry) -> list[tuple[float, float]]:
        if shape.is_empty:
            return []
        if isinstance(shape, (Point, LineString)):
            values = [path.project(Point(x, y), normalized=True) for x, y in shape.coords]
            return [(min(values), max(values))]
        return [pair for part in getattr(shape, "geoms", []) for pair in pieces_of(part)]

    return sorted(pieces_of(intersection))


def interpolate(
    g: Geometry, start: Track, end: Track, uncertainty_ms: int, *, resource: Resource = "RUNWAY"
) -> list[TimeRange]:
    if type(uncertainty_ms) is not int or uncertainty_ms < 0:
        raise ContractError("INVALID_INPUT")
    duration = end.event_time_ms - start.event_time_ms
    return merge(
        [
            TimeRange(
                start_ms=max(
                    g.layout.validity.start_ms,
                    math.floor(start.event_time_ms + a * duration) - uncertainty_ms,
                ),
                end_ms=min(
                    g.layout.validity.end_ms,
                    math.ceil(start.event_time_ms + b * duration) + 1 + uncertainty_ms,
                ),
            )
            for a, b in _fractions(g, start, end, resource)
        ]
    )


def predict(
    g: Geometry,
    track: Track,
    as_of_ms: int,
    policy: Policy,
    timing_uncertainty_ms: int,
    *,
    resource: Resource = "RUNWAY",
) -> Forecast:
    g._track(track)
    if (
        type(as_of_ms) is not int
        or as_of_ms < track.event_time_ms
        or not as_of_ms < g.layout.validity.end_ms
        or type(timing_uncertainty_ms) is not int
        or timing_uncertainty_ms < 0
        or track.speed_mps > policy.max_speed_mps
    ):
        raise ContractError("NOT_EVALUABLE")
    high = min(as_of_ms + policy.horizon_ms + 1, g.layout.validity.end_ms)
    if track.speed_mps < policy.speed_floor_mps:
        occupied = g.occupied(track, resource=resource)
        return Forecast(
            [TimeRange(start_ms=as_of_ms, end_ms=high)] if occupied else [],
            None,
            None,
            True,
            occupied,
        )
    end_time = high - 1
    if end_time <= track.event_time_ms:
        occupied = g.occupied(track, resource=resource)
        return Forecast(
            [TimeRange(start_ms=as_of_ms, end_ms=high)] if occupied else [],
            None,
            None,
            True,
            occupied,
        )
    seconds = (end_time - track.event_time_ms) / 1000
    angle = math.radians(track.heading_deg)
    end = track.model_copy(
        update={
            "event_time_ms": end_time,
            "x_m": track.x_m + math.cos(angle) * track.speed_mps * seconds,
            "y_m": track.y_m + math.sin(angle) * track.speed_mps * seconds,
        }
    )
    fractions = _fractions(g, track, end, resource)
    duration = end_time - track.event_time_ms
    central = [
        (track.event_time_ms + a * duration, track.event_time_ms + b * duration, b == 1.0)
        for a, b in fractions
    ]
    relevant = [(a, b, open_exit) for a, b, open_exit in central if b >= as_of_ms]
    margin = (
        timing_uncertainty_ms
        + policy.temporal_margin_ms
        + math.ceil(g.layout.uncertainty / track.speed_mps * 1000)
    )
    ranges = [
        TimeRange(
            start_ms=max(as_of_ms, math.floor(a) - margin),
            end_ms=min(high, math.ceil(b) + 1 + margin),
        )
        for a, b, _ in relevant
    ]
    return Forecast(
        merge(ranges),
        math.floor(relevant[0][0]) if relevant else None,
        math.ceil(relevant[-1][1]) if relevant and not relevant[-1][2] else None,
        False,
        bool(relevant and relevant[-1][2]),
    )


@dataclass(frozen=True)
class OccupancyReport:
    result: GeometryResult
    observed: list[TimeRange]
    predicted: list[TimeRange]
    observed_at_ms: int | None
    last_observed_occupied: bool | None
    eta_ms: int | None
    exit_ms: int | None
    prediction_unknown: bool
    exit_unknown: bool
    resource: Resource
    config_hash: str


class Occupancy:
    def __init__(
        self, sources: Sources, evidence: EvidenceRegistry, policy: Policy | None = None
    ) -> None:
        self.sources, self.evidence, self.policy = sources, evidence, policy or Policy()

    def observations(self, context: RequestContext, entity_id: UUID) -> GeometryResult:
        return self.report(context, entity_id).result

    def report(
        self, ctx: RequestContext, entity_id: UUID, *, resource: Resource = "RUNWAY"
    ) -> OccupancyReport:
        if resource not in ("RUNWAY", "PROTECTION") or type(entity_id) is not UUID:
            raise ContractError("INVALID_INPUT")
        tracks = self.sources.tracks(ctx, entity_id)
        with self.sources.database.begin() as uow:
            self.sources.permissions.enforce(uow, ctx)
            rows = list(
                uow.connection.execute(
                    "SELECT source_id,payload FROM platform_source_packages WHERE session_id=?",
                    (str(ctx.session_id),),
                )
            )
            packages = []
            for row in rows:
                self.sources.require_right(
                    uow,
                    ctx,
                    UUID(row["source_id"]),
                    "cloud_context" if "worker" in ctx.capabilities else "reviewer",
                )
                packages.append(PreparedImport.model_validate_json(row["payload"]))
        prepared = next(
            (p for p in packages if any(i.entity_id == entity_id for i in p.identities)),
            packages[0] if packages else None,
        )
        latest = tracks[-1] if tracks else None
        reason: str | None = None
        g: Geometry | None = None
        last_occupied: bool | None = None
        observed: list[TimeRange] = []
        uncertainty: int | None = None
        forecast = Forecast([], None, None, True, True)
        if prepared is None:
            reason = "SOURCE_MISSING"
        else:
            clocks = [
                f.clock
                for f in prepared.declaration.files
                if any(x.id == f.file_id and x.role == "tracks" for x in prepared.files)
            ]
            mapping = next((i for i in prepared.identities if i.entity_id == entity_id), None)
            identity = next(
                (
                    i
                    for i in prepared.declaration.identities
                    if mapping and i.source_entity_id == mapping.source_entity_id
                ),
                None,
            )
            if not clocks or any(c.uncertainty_ms is None for c in clocks):
                reason = "CLOCK_UNKNOWN"
            elif prepared.layout is None:
                reason = "LAYOUT_MISSING"
            elif identity is None:
                reason = "IDENTITY_UNKNOWN"
            elif not identity.validity.start_ms <= ctx.as_of_ms < identity.validity.end_ms:
                reason = "IDENTITY_EXPIRED"
            elif (
                not prepared.layout.validity.start_ms
                <= ctx.as_of_ms
                < prepared.layout.validity.end_ms
            ):
                reason = "LAYOUT_EXPIRED"
            elif latest is None:
                reason = "TRACK_MISSING"
            else:
                g = Geometry(prepared.layout, protection_margin_m=self.policy.protection_margin_m)
                try:
                    last_occupied = g.occupied(latest, resource=resource)
                except ContractError:
                    reason = "LAYOUT_MISMATCH"
                clock_uncertainty = max(c.uncertainty_ms or 0 for c in clocks)
                uncertainty = (
                    clock_uncertainty + latest.age_ms + ctx.as_of_ms - latest.event_time_ms
                )
                if reason is None:
                    if clock_uncertainty > self.policy.max_clock_uncertainty_ms:
                        reason = "CLOCK_UNCERTAIN"
                    elif latest.quality != "SUPPORTED":
                        reason = "TRACK_" + latest.quality
                    elif latest.age_ms + ctx.as_of_ms - latest.event_time_ms > self.policy.stale_ms:
                        reason = "STALE_TRACK"
                    elif prepared.declaration.coverage.vehicles is not True:
                        reason = "COVERAGE_UNKNOWN"
                    elif any(
                        gap.start_ms <= ctx.as_of_ms and gap.end_ms > latest.event_time_ms
                        for gap in prepared.declaration.coverage.gaps
                    ):
                        reason = "COVERAGE_GAP"
                    elif any(
                        b.event_time_ms - a.event_time_ms > self.policy.gap_ms
                        for a, b in zip(tracks, tracks[1:], strict=False)
                    ):
                        reason = "TRACK_GAP"
                    elif any(
                        a.event_time_ms == b.event_time_ms
                        and any(
                            getattr(a, field) != getattr(b, field)
                            for field in (
                                "x_m",
                                "y_m",
                                "heading_deg",
                                "speed_mps",
                                "length_m",
                                "width_m",
                                "age_ms",
                                "layout_version",
                                "source_id",
                                "source_hash",
                            )
                        )
                        for a, b in zip(tracks, tracks[1:], strict=False)
                    ):
                        reason = "TRACK_CONFLICTING"
                    elif any(t.quality != "SUPPORTED" for t in tracks):
                        reason = "TRACK_AMBIGUOUS"
                if reason is None:
                    try:
                        observed = [
                            TimeRange(start_ms=t.event_time_ms, end_ms=t.event_time_ms + 1)
                            for t in tracks
                            if g.occupied(t, resource=resource)
                        ]
                        for a, b in zip(tracks, tracks[1:], strict=False):
                            if b.event_time_ms > a.event_time_ms:
                                observed.extend(
                                    interpolate(g, a, b, clock_uncertainty, resource=resource)
                                )
                        observed = merge(
                            [
                                TimeRange(
                                    start_ms=r.start_ms, end_ms=min(r.end_ms, ctx.as_of_ms + 1)
                                )
                                for r in observed
                                if r.start_ms <= ctx.as_of_ms
                            ]
                        )
                        forecast = predict(
                            g, latest, ctx.as_of_ms, self.policy, uncertainty, resource=resource
                        )
                        limit = min(identity.validity.end_ms, g.layout.validity.end_ms)
                        clipped = [
                            TimeRange(start_ms=r.start_ms, end_ms=min(r.end_ms, limit))
                            for r in forecast.intervals
                            if r.start_ms < limit
                        ]
                        truncated = any(r.end_ms > limit for r in forecast.intervals)
                        gap_unknown = any(
                            gap.start_ms < min(ctx.as_of_ms + self.policy.horizon_ms + 1, limit)
                            and gap.end_ms > ctx.as_of_ms
                            for gap in prepared.declaration.coverage.gaps
                        )
                        forecast = Forecast(
                            clipped,
                            forecast.eta_ms if clipped else None,
                            None if truncated or gap_unknown else forecast.exit_ms,
                            forecast.unknown or gap_unknown,
                            forecast.exit_unknown or truncated or gap_unknown,
                        )
                    except ContractError:
                        reason = "MOTION_NOT_EVALUABLE"
        fingerprint = hashed(
            {
                "policy": asdict(self.policy),
                "kernel": GEOMETRY_VERSION,
                "source": prepared.declaration_hash if prepared else None,
                "resource": resource,
            }
        )
        # Authority and each canonical anchor are revalidated together after pure geometry.
        with self.sources.database.begin() as uow:
            self.sources.permissions.enforce(uow, ctx)
            for row in rows:
                self.sources.require_right(
                    uow,
                    ctx,
                    UUID(row["source_id"]),
                    "cloud_context" if "worker" in ctx.capabilities else "reviewer",
                )
            anchors = [self.evidence.index_track(ctx, t, uow) for t in tracks]
            result = GeometryResult(
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                entity_id=entity_id,
                status="NOT_EVALUABLE" if reason else "EVALUATED",
                reason=reason
                or ("PREDICTION_UNKNOWN" if forecast.unknown else "LINEAR_FIXED_HEADING_MODEL"),
                occupied=last_occupied if reason is None else None,
                intervals=merge(observed + forecast.intervals) if reason is None else [],
                uncertainty_ms=uncertainty,
                rule_version=self.policy.version,
                layout_version=prepared.layout.version if prepared and prepared.layout else None,
                evidence=anchors,
            )
            uow.commit()
        return OccupancyReport(
            result,
            observed if reason is None else [],
            forecast.intervals if reason is None else [],
            latest.event_time_ms if latest else None,
            last_occupied,
            forecast.eta_ms if reason is None else None,
            forecast.exit_ms if reason is None else None,
            reason is not None or forecast.unknown,
            reason is not None or forecast.exit_unknown,
            resource,
            fingerprint,
        )


def shared_resource(a: OccupancyReport, b: OccupancyReport) -> str:
    """Same runway collision possibility, without converting missing observations to clearance."""
    x, y = a.result, b.result
    if (
        x.session_id,
        x.analysis_run_id,
        x.revision,
        x.layout_version,
        a.resource,
        a.config_hash,
    ) != (y.session_id, y.analysis_run_id, y.revision, y.layout_version, b.resource, b.config_hash):
        raise ContractError("ACCESS_DENIED")
    if x.entity_id == y.entity_id:
        raise ContractError("INVALID_INPUT")
    if overlap(a.observed, b.observed):
        return "OBSERVED_MODEL_OVERLAP"
    if (
        x.status == "NOT_EVALUABLE"
        or y.status == "NOT_EVALUABLE"
        or a.prediction_unknown
        or b.prediction_unknown
    ):
        return "UNKNOWN"
    if overlap(a.predicted, b.predicted):
        return "PREDICTED_MODEL_OVERLAP"
    return "NO_MODELED_OVERLAP"
