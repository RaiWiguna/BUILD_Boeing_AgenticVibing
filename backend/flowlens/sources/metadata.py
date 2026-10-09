"""Detailed rights/provenance and explicit local planar layout declarations."""

from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from flowlens.clocks.normalization import ClockSpec, MetadataModel
from flowlens.contracts.models import TimeRange
from flowlens.core.errors import ContractError
from pydantic import Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")]
Basis = Annotated[str, Field(min_length=1, max_length=2048, pattern=r"\S")]
Right = Literal["ALLOWED", "DENIED", "UNDETERMINED"]
Action = Literal["local", "cloud_audio", "cloud_context", "reviewer", "export", "audio_export"]
Point = tuple[
    Annotated[float, Field(ge=-10000000, le=10000000)],
    Annotated[float, Field(ge=-10000000, le=10000000)],
]


class RightsProfile(MetadataModel):
    local: Right
    cloud_audio: Right
    cloud_context: Right
    reviewer: Right
    export: Right
    audio_export: Right
    basis: Basis

    def permits(self, action: Action) -> bool:
        allowed = self.local == "ALLOWED" and getattr(self, action) == "ALLOWED"
        return allowed and (action != "audio_export" or self.export == "ALLOWED")

    def require(self, action: Action) -> None:
        if not self.permits(action):
            raise ContractError(
                "CLOUD_TRANSFER_BLOCKED"
                if action.startswith("cloud_")
                else "SOURCE_PERMISSION_REQUIRED"
            )


class Retention(MetadataModel):
    policy: Literal["UNDETERMINED", "FIXED_DAYS"]
    days: Annotated[int, Field(ge=1, le=36500)] | None = None
    basis: Basis

    @model_validator(mode="after")
    def declared_days(self) -> Self:
        if (self.policy == "FIXED_DAYS") != (self.days is not None):
            raise ValueError("Fixed retention requires days; unknown retention has none")
        return self


class FileDeclaration(MetadataModel):
    file_id: UUID
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    clock: ClockSpec
    channels: Annotated[list[Text], Field(max_length=2)] = []


class CoverageDeclaration(MetadataModel):
    vehicles: bool | None = None
    speaker_identity: bool | None = None
    basis: Basis | None = None
    gaps: Annotated[list[TimeRange], Field(max_length=256)] = []

    @model_validator(mode="after")
    def explicit_claims(self) -> Self:
        if (
            self.vehicles is not None or self.speaker_identity is not None or self.gaps
        ) and not self.basis:
            raise ValueError("Coverage claims require source basis")
        ordered = sorted(self.gaps, key=lambda x: x.start_ms)
        if any(a.end_ms > b.start_ms for a, b in zip(ordered, ordered[1:], strict=False)):
            raise ValueError("Overlapping gaps")
        return self


class IdentityDeclaration(MetadataModel):
    source_entity_id: Text
    callsign: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9 -]{0,63}$")]
    aliases: Annotated[list[Text], Field(max_length=32)] = []
    validity: TimeRange
    evidence_file_id: UUID
    evidence_record_ids: Annotated[list[Text], Field(min_length=1, max_length=32)]


class HoldLine(MetadataModel):
    id: Text
    points: tuple[Point, Point]

    @model_validator(mode="after")
    def nonzero(self) -> Self:
        if self.points[0] == self.points[1]:
            raise ValueError("Hold line requires two distinct points")
        return self


class Layout(MetadataModel):
    version: Text
    coordinate_system: Literal["LOCAL_CARTESIAN"]
    units: Literal["m", "ft"]
    validity: TimeRange
    uncertainty: Annotated[float, Field(ge=0, le=1000000)]
    runway_polygon: Annotated[list[Point], Field(min_length=3, max_length=128)]
    hold_lines: Annotated[list[HoldLine], Field(min_length=1, max_length=32)]

    @model_validator(mode="after")
    def polygon(self) -> Self:
        points = self.runway_polygon
        if len(set(points)) != len(points):
            raise ValueError("Polygon uses unique vertices without repeated closure")
        area = sum(
            a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1], strict=True)
        )
        if abs(area) < 1e-9:
            raise ValueError("Degenerate polygon")

        def orientation(a: Point, b: Point, c: Point) -> float:
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        def on_segment(a: Point, b: Point, c: Point) -> bool:
            return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(
                a[1], b[1]
            )

        edges = list(zip(points, points[1:] + points[:1], strict=True))
        for index, (a, b) in enumerate(edges):
            for other, (c, d) in enumerate(edges[index + 1 :], index + 1):
                if other == index + 1 or (index == 0 and other == len(edges) - 1):
                    continue
                turns = (
                    orientation(a, b, c),
                    orientation(a, b, d),
                    orientation(c, d, a),
                    orientation(c, d, b),
                )
                crossing = turns[0] * turns[1] < 0 and turns[2] * turns[3] < 0
                touching = any(
                    abs(turn) < 1e-9 and on_segment(x, y, z)
                    for turn, x, y, z in (
                        (turns[0], a, b, c),
                        (turns[1], a, b, d),
                        (turns[2], c, d, a),
                        (turns[3], c, d, b),
                    )
                )
                if crossing or touching:
                    raise ValueError("Self-intersecting polygon")
        if len({line.id for line in self.hold_lines}) != len(self.hold_lines):
            raise ValueError("Duplicate hold line ID")
        return self

    def metric(self) -> "Layout":
        factor = Decimal("0.3048") if self.units == "ft" else Decimal(1)

        def convert(point: Point) -> list[float]:
            return [float(Decimal(str(value)) * factor) for value in point]

        data = self.model_dump(mode="json")
        data["units"] = "m"
        data["uncertainty"] = float(Decimal(str(self.uncertainty)) * factor)
        data["runway_polygon"] = [convert(point) for point in self.runway_polygon]
        data["hold_lines"] = [
            {"id": x.id, "points": [convert(p) for p in x.points]} for x in self.hold_lines
        ]
        import json

        return Layout.model_validate_json(json.dumps(data))


class Declaration(MetadataModel):
    profile_version: Literal["source-metadata-1"] = "source-metadata-1"
    source_kind: Literal["SYNTHETIC", "ROLEPLAY", "PUBLIC_CORPUS", "PARTNER_REPLAY"]
    source_label: Text
    source_owner: Text
    source_identifier: Text
    dataset: Text | None = None
    dataset_version: Text | None = None
    subset: Text | None = None
    rights: RightsProfile
    retention: Retention
    files: Annotated[list[FileDeclaration], Field(min_length=1, max_length=4)]
    coverage: CoverageDeclaration
    identities: Annotated[list[IdentityDeclaration], Field(max_length=1000)]
    layout: Layout | None

    @model_validator(mode="after")
    def unique_files(self) -> Self:
        if len({item.file_id for item in self.files}) != len(self.files):
            raise ValueError("Duplicate file declarations")
        if len({item.source_entity_id for item in self.identities}) != len(self.identities):
            raise ValueError("Duplicate source entity")
        if self.source_kind == "PUBLIC_CORPUS" and (
            self.dataset is None or self.dataset_version is None
        ):
            raise ValueError("Public corpus requires explicit dataset/version")
        return self
