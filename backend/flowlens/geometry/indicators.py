"""Experimental counts and source-reported activity; never mental state or radio occupancy."""

from typing import Annotated, Literal

from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import (
    Evidence,
    OpenLoop,
    RequestContext,
    Scoped,
    SourceEvent,
    TimeRange,
)
from flowlens.core.errors import ContractError
from flowlens.geometry.occupancy import merge
from flowlens.imports.inspection import InvalidContent, strict_json
from pydantic import Field, ValidationError, model_validator


class Activity(MetadataModel):
    profile_version: Literal["lab-source-1"]
    type: Literal["AUDIO_ACTIVITY"]
    action: None = None
    start_ms: Annotated[int, Field(ge=0)]
    end_ms: Annotated[int, Field(gt=0)]
    channel: Literal[0, 1]
    measurement_version: Literal["synthetic-active-audio-1"]

    @model_validator(mode="after")
    def positive(self) -> "Activity":
        if self.start_ms >= self.end_ms:
            raise ValueError("Positive activity range required")
        return self


class Indicators(Scoped):
    as_of_ms: int
    window_start_ms: int
    definition_version: Literal["lab-indicators-1"] = "lab-indicators-1"
    label: Literal["EXPERIMENTAL_NOT_WORKLOAD"] = "EXPERIMENTAL_NOT_WORKLOAD"
    reported_active_audio_ms: int | None
    activity_status: Literal["UNAVAILABLE", "SOURCE_REPORTED_NOT_VAD_VERIFIED"]
    occupied_audio_ms: None = None
    occupied_audio_reason: Literal["VAD_CHANNEL_OVERLAP_NOT_VALIDATED"] = (
        "VAD_CHANNEL_OVERLAP_NOT_VALIDATED"
    )
    open_loop_count: int | None
    open_loop_status: Literal["UNAVAILABLE", "EVALUATED", "PARTIAL"]
    active_entity_count: int
    unknown_entity_count: int
    queued_job_count: int
    running_job_count: int
    job_state_basis: Literal["CURRENT_COORDINATOR_STATE"] = "CURRENT_COORDINATOR_STATE"
    evidence: list[Evidence]


def activity_records(
    ctx: RequestContext, events: list[SourceEvent]
) -> list[tuple[SourceEvent, Activity]]:
    result = []
    for event in events:
        if event.kind != "QUALITY" or event.quality != "SUPPORTED" or len(event.statement) > 8192:
            continue
        try:
            activity = Activity.model_validate(strict_json(event.statement))
        except (InvalidContent, ValidationError, ValueError):
            continue
        if activity.end_ms <= event.event_time_ms and event.event_time_ms <= ctx.as_of_ms:
            result.append((event, activity))
    return result


def active_duration(
    ctx: RequestContext, records: list[tuple[SourceEvent, Activity]], *, window_ms: int = 60000
) -> int | None:
    low = max(0, ctx.as_of_ms - window_ms)
    if not records:
        return None
    intervals = [
        TimeRange(start_ms=max(low, a.start_ms), end_ms=min(ctx.as_of_ms, a.end_ms))
        for _, a in records
        if a.end_ms > low and a.start_ms < ctx.as_of_ms
    ]
    return sum(t.end_ms - t.start_ms for t in merge(intervals))


def validate_loop(ctx: RequestContext, loop: OpenLoop) -> OpenLoop:
    loop = OpenLoop.model_validate_json(loop.model_dump_json())
    if (loop.session_id, loop.analysis_run_id, loop.revision) != (
        ctx.session_id,
        ctx.analysis_run_id,
        ctx.input_revision,
    ):
        raise ContractError("ACCESS_DENIED")
    if (
        loop.event_time_ms > ctx.as_of_ms
        or ctx.mode == "AS_KNOWN"
        and (loop.available_time_ms is None or loop.available_time_ms > ctx.as_of_ms)
    ):
        raise ContractError("EVIDENCE_UNAVAILABLE")
    return loop
