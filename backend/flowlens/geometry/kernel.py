"""Metric Cartesian geometry. Heading0 is +X,90 is +Y, counterclockwise.

Pure math over observed poses; interpolation/envelopes do not certify actual motion.
"""

import math
from dataclasses import dataclass
from typing import Literal

from flowlens.contracts.models import Track
from flowlens.core.errors import ContractError
from flowlens.sources.metadata import Layout
from pydantic import ValidationError
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

GEOMETRY_VERSION = "footprint-xy-1"
MAX_COORDINATE_M = 10_000_000
MAX_DIMENSION_M = 100_000
EPSILON_M = 1e-9
Resource = Literal["RUNWAY", "PROTECTION"]
Relation = Literal["BEHIND", "TOUCHING", "STRADDLING", "BEYOND", "OUTSIDE_SEGMENT"]


def number(value: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ContractError("INVALID_INPUT")
    if abs(value) > MAX_COORDINATE_M:
        raise ContractError("NOT_EVALUABLE")
    return float(value)


def pose(track: Track) -> Track:
    if type(track) is not Track:
        raise ContractError("INVALID_INPUT")
    try:
        validated = Track.model_validate_json(track.model_dump_json())
    except (ValidationError, ValueError):
        raise ContractError("INVALID_INPUT") from None
    number(validated.x_m)
    number(validated.y_m)
    if max(validated.length_m, validated.width_m) > MAX_DIMENSION_M:
        raise ContractError("NOT_EVALUABLE")
    return validated


def footprint(track: Track) -> Polygon:
    track = pose(track)
    angle = track.heading_deg
    cardinal = {0.0: (1.0, 0.0), 90.0: (0.0, 1.0), 180.0: (-1.0, 0.0), 270.0: (0.0, -1.0)}
    c, s = cardinal.get(angle, (math.cos(math.radians(angle)), math.sin(math.radians(angle))))
    half_length, half_width = track.length_m / 2, track.width_m / 2
    points = [
        (track.x_m + c * x - s * y, track.y_m + s * x + c * y)
        for x, y in (
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width),
        )
    ]
    polygon = Polygon(points)
    if (
        not polygon.is_valid
        or polygon.is_empty
        or not math.isfinite(polygon.area)
        or polygon.area <= 0
    ):
        raise ContractError("NOT_EVALUABLE")
    return polygon


@dataclass(frozen=True)
class Sweep:
    shape: BaseGeometry
    exact: bool
    motion_model: Literal["LINEAR_FIXED_HEADING", "LINEAR_ROTATION_BOUND"]


class Geometry:
    def __init__(self, layout: Layout, *, protection_margin_m: float = 0.0) -> None:
        try:
            self.layout = Layout.model_validate_json(layout.model_dump_json()).metric()
        except (ValidationError, ValueError):
            raise ContractError("INVALID_INPUT") from None
        margin = number(protection_margin_m)
        if margin < 0 or margin > MAX_DIMENSION_M:
            raise ContractError("INVALID_INPUT")
        for x, y in self.layout.runway_polygon:
            number(x)
            number(y)
        for line in self.layout.hold_lines:
            for x, y in line.points:
                number(x)
                number(y)
        self.runway = Polygon(self.layout.runway_polygon)
        if not self.runway.is_valid or self.runway.is_empty:
            raise ContractError("NOT_EVALUABLE")
        # Lab protection geometry uses explicit mitered offsets, including layout uncertainty.
        # No silent repair of invalid geometry or conversion from unregistered geographic CRS.
        self.protection = self.runway.buffer(margin + self.layout.uncertainty, join_style="mitre")
        self.lines = {line.id: LineString(line.points) for line in self.layout.hold_lines}
        if any(line.length <= EPSILON_M for line in self.lines.values()):
            raise ContractError("NOT_EVALUABLE")

    def _track(self, track: Track) -> Track:
        track = pose(track)
        if (
            track.layout_version != self.layout.version
            or not self.layout.validity.start_ms
            <= track.event_time_ms
            < self.layout.validity.end_ms
        ):
            raise ContractError("NOT_EVALUABLE")
        return track

    def region(self, resource: Resource) -> Polygon:
        if resource == "RUNWAY":
            return self.runway
        if resource == "PROTECTION":
            return self.protection
        raise ContractError("INVALID_INPUT")

    def occupied(self, track: Track, *, resource: Resource = "RUNWAY") -> bool:
        return bool(self.region(resource).intersects(footprint(self._track(track))))

    def hold_relation(
        self, track: Track, line_id: str, *, allowed_point: tuple[float, float]
    ) -> Relation:
        shape = footprint(self._track(track))
        line = self.lines.get(line_id)
        if line is None:
            raise ContractError("NOT_EVALUABLE")
        if type(allowed_point) is not tuple or len(allowed_point) != 2:
            raise ContractError("INVALID_INPUT")
        x, y = number(allowed_point[0]), number(allowed_point[1])
        (ax, ay), (bx, by) = line.coords
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        allowed = (dx * (y - ay) - dy * (x - ax)) / length
        if abs(allowed) <= EPSILON_M:
            raise ContractError("NOT_EVALUABLE")
        sign = 1 if allowed > 0 else -1
        # Restrict the footprint to the finite segment's lateral corridor before
        # classifying its side; bounding-box projection can falsely straddle a short line.
        nx, ny = -dy / length, dx / length
        extent = 4 * MAX_COORDINATE_M
        corridor = Polygon(
            [
                (ax + nx * extent, ay + ny * extent),
                (bx + nx * extent, by + ny * extent),
                (bx - nx * extent, by - ny * extent),
                (ax - nx * extent, ay - ny * extent),
            ]
        )
        clipped = shape.intersection(corridor)
        if clipped.is_empty:
            return "OUTSIDE_SEGMENT"
        if isinstance(clipped, Polygon):
            points = clipped.exterior.coords
        elif isinstance(clipped, (Point, LineString)):
            points = clipped.coords
        else:
            raise ContractError("NOT_EVALUABLE")
        distances = [sign * (dx * (py - ay) - dy * (px - ax)) / length for px, py in points]
        lo, hi = min(distances), max(distances)
        if lo < -EPSILON_M and hi > EPSILON_M:
            return "STRADDLING"
        if abs(lo) <= EPSILON_M or abs(hi) <= EPSILON_M:
            return "TOUCHING"
        return "BEHIND" if lo > 0 else "BEYOND"

    def sweep(self, start: Track, end: Track) -> Sweep:
        start, end = self._track(start), self._track(end)
        scope = (
            "session_id",
            "analysis_run_id",
            "revision",
            "source_id",
            "source_hash",
            "entity_id",
            "layout_version",
            "length_m",
            "width_m",
        )
        if (
            start.entity_id is None
            or any(getattr(start, k) != getattr(end, k) for k in scope)
            or end.event_time_ms <= start.event_time_ms
        ):
            raise ContractError("NOT_EVALUABLE")
        if start.heading_deg == end.heading_deg:
            shape = unary_union([footprint(start), footprint(end)]).convex_hull
            return Sweep(shape, True, "LINEAR_FIXED_HEADING")
        radius = math.hypot(start.length_m, start.width_m) / 2
        # Circumscribe the half-diagonal disk. Standard polygonal buffers approximate inward;
        # compensate at64 vertices so all rotating corners remain inside the bound.
        bound = radius / math.cos(math.pi / 64)
        path: BaseGeometry = (
            Point(start.x_m, start.y_m)
            if (start.x_m, start.y_m) == (end.x_m, end.y_m)
            else LineString([(start.x_m, start.y_m), (end.x_m, end.y_m)])
        )
        return Sweep(path.buffer(bound, quad_segs=16), False, "LINEAR_ROTATION_BOUND")

    def swept_occupied(self, start: Track, end: Track, *, resource: Resource = "RUNWAY") -> bool:
        return bool(self.region(resource).intersects(self.sweep(start, end).shape))

    def crosses_hold(
        self, start: Track, end: Track, line_id: str, *, allowed_point: tuple[float, float]
    ) -> bool:
        sweep = self.sweep(start, end)
        a = self.hold_relation(start, line_id, allowed_point=allowed_point)
        b = self.hold_relation(end, line_id, allowed_point=allowed_point)
        return (
            a in ("BEHIND", "TOUCHING")
            and b in ("STRADDLING", "BEYOND")
            and bool(sweep.shape.intersects(self.lines[line_id]))
        )
