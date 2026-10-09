"""Explicit source clocks; unknown alignment is never replaced with zero."""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flowlens.imports.staging import ImportFailure
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_MS = 2**63 - 1


class MetadataModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, allow_inf_nan=False)


class ClockSpec(MetadataModel):
    version: Literal["clock-normalization-1"] = "clock-normalization-1"
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    method: Literal["UNKNOWN", "DECLARED_OFFSET", "DECLARED_LINEAR"] = "UNKNOWN"
    offset_ms: Annotated[int, Field(ge=-MAX_MS, le=MAX_MS)] | None = None
    uncertainty_ms: Annotated[int, Field(ge=0, le=MAX_MS)] | None = None
    drift_ppm: Annotated[float, Field(ge=-1000, le=1000)] | None = None
    basis: Annotated[str, Field(min_length=1, max_length=2048, pattern=r"\S")] | None = None
    reviewer: Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")] | None = None

    @model_validator(mode="after")
    def explicit_mapping(self) -> Self:
        if self.timezone != "UNKNOWN":
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Unsupported timezone") from None
        if self.method == "UNKNOWN":
            if any(
                x is not None
                for x in (
                    self.offset_ms,
                    self.uncertainty_ms,
                    self.drift_ppm,
                    self.basis,
                    self.reviewer,
                )
            ):
                raise ValueError("Unknown mapping cannot declare alignment")
        else:
            if any(
                x is None for x in (self.offset_ms, self.uncertainty_ms, self.basis, self.reviewer)
            ):
                raise ValueError("Declared mapping requires offset/uncertainty/basis/reviewer")
            if (self.method == "DECLARED_LINEAR") != (self.drift_ppm is not None):
                raise ValueError("Only linear mapping declares drift")
        return self

    def to_session_ms(self, source_ms: int) -> int | None:
        if type(source_ms) is not int or not 0 <= source_ms <= MAX_MS:
            raise ImportFailure("IMPOSSIBLE_TIME", "clock")
        if self.offset_ms is None:
            return None
        value = Decimal(source_ms) + self.offset_ms
        if self.drift_ppm is not None:
            value += Decimal(source_ms) * Decimal(str(self.drift_ppm)) / 1000000
        result = int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))
        if not 0 <= result <= MAX_MS:
            raise ImportFailure("IMPOSSIBLE_TIME", "clock")
        return result


def source_timestamp_ms(
    raw: str, timezone: str, origin: datetime, *, fold: Literal[0, 1] | None = None
) -> int:
    """Wall timestamp adapter: caller retains raw text and declares UTC session origin."""
    try:
        offset = origin.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("UTC origin required")
        if "T" not in raw:
            raise ValueError("Timestamp requires time")
        zone = ZoneInfo(timezone)
        value = datetime.fromisoformat(raw)
        if value.tzinfo is None:
            candidates = [value.replace(tzinfo=zone, fold=i) for i in (0, 1)]
            valid = [
                x
                for x in candidates
                if x.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == value
            ]
            if not valid:
                raise ImportFailure("NONEXISTENT_TIME", "clock")
            if len({x.astimezone(UTC) for x in valid}) > 1 and fold is None:
                raise ImportFailure("AMBIGUOUS_TIME", "clock")
            value = candidates[fold or 0]
        elif value.utcoffset() != value.astimezone(zone).utcoffset():
            raise ImportFailure("TIMEZONE_MISMATCH", "clock")
        delta = value.astimezone(UTC) - origin
        if delta.microseconds % 1000:
            raise ImportFailure("TIMESTAMP_PRECISION", "clock")
        milliseconds = delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000
        if not 0 <= milliseconds <= MAX_MS:
            raise ImportFailure("IMPOSSIBLE_TIME", "clock")
        return milliseconds
    except (ValueError, ZoneInfoNotFoundError, OverflowError):
        raise ImportFailure("INVALID_TIMESTAMP", "clock") from None
