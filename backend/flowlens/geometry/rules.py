"""Explicit source-record lab rules. No semantic extraction or clearance issuance."""

from dataclasses import dataclass
from itertools import combinations
from typing import Annotated, Literal
from uuid import UUID, uuid5

from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import Evidence, RequestContext, Scoped, SourceEvent, Track
from flowlens.core.errors import ContractError
from flowlens.geometry.kernel import Geometry
from flowlens.geometry.occupancy import Policy, overlap, predict
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.imports.metadata import hashed
from pydantic import Field, ValidationError, model_validator


@dataclass(frozen=True)
class RuleProfile:
    version: str = "lab-rules-1"
    response_window_ms: int = 5000
    hold_line_id: str = "H1"
    layout_version: str = "fictional-1"
    allowed_point: tuple[float, float] = (-50.0, 0.0)
    occupancy: Policy = Policy(protection_margin_m=5.0)

    def __post_init__(self) -> None:
        if (
            type(self.response_window_ms) is not int
            or not 1 <= self.response_window_ms <= 3600000
            or self.version != "lab-rules-1"
        ):
            raise ValueError("Unsupported lab rule profile")
        from flowlens.geometry.kernel import number

        if (
            not self.hold_line_id
            or type(self.allowed_point) is not tuple
            or len(self.allowed_point) != 2
        ):
            raise ValueError("Explicit allowed hold side required")
        for value in self.allowed_point:
            number(value)


class Instruction(MetadataModel):
    profile_version: Literal["lab-source-1"]
    type: Literal["INSTRUCTION"]
    action: Literal[
        "HOLD_SHORT",
        "CROSS_RUNWAY",
        "LAND",
        "GO_AROUND",
        "CANCEL",
        "REPORT_COMPLETE",
        "GO_AROUND_RESPONSE",
    ]
    line_id: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    related_source_event_id: Annotated[str, Field(min_length=1, max_length=256)] | None = None

    @model_validator(mode="after")
    def linked(self) -> "Instruction":
        if (
            self.action in ("CANCEL", "REPORT_COMPLETE", "GO_AROUND_RESPONSE")
            and self.related_source_event_id is None
        ):
            raise ValueError("Explicit source relationship required")
        if self.action == "HOLD_SHORT" and self.line_id is None:
            raise ValueError("Explicit hold line required")
        return self


class InstructionCoverage(MetadataModel):
    profile_version: Literal["lab-source-1"]
    type: Literal["INSTRUCTION_COVERAGE"]
    action: None = None
    start_ms: Annotated[int, Field(ge=0)]
    end_ms: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def positive(self) -> "InstructionCoverage":
        if self.start_ms >= self.end_ms:
            raise ValueError("Positive coverage range required")
        return self


class SourceAlert(MetadataModel):
    profile_version: Literal["lab-source-1"]
    type: Literal["SOURCE_ALERT"]
    alert_key: Annotated[str, Field(min_length=1, max_length=128)]
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    status: Literal["ACTIVE", "CLEARED"]


class RuleSignal(Scoped):
    id: UUID
    rule_id: str
    status: Literal["ACTIVE", "INACTIVE", "UNKNOWN"]
    reason: str
    statement: str
    priority: Literal["INFO", "NOTICE", "ATTENTION"]
    entity_ids: list[UUID]
    as_of_ms: int
    available_time_ms: int | None
    rule_version: str
    config_hash: str
    applicability: Literal["LAB_ONLY"] = "LAB_ONLY"
    evidence: list[Evidence]
    overlap_ms: int | None = None
    exit_unknown: bool = False


def decode(event: SourceEvent) -> Instruction | InstructionCoverage | SourceAlert | None:
    if event.quality != "SUPPORTED" or len(event.statement) > 8192:
        return None
    try:
        body = strict_json(event.statement)
        if not isinstance(body, dict):
            return None
        if body.get("type") == "INSTRUCTION" and event.kind in ("INSTRUCTION", "REPORT"):
            item = Instruction.model_validate(body)
            if (item.action in ("REPORT_COMPLETE", "GO_AROUND_RESPONSE")) != (
                event.kind == "REPORT"
            ):
                return None
            return item
        if body.get("type") == "INSTRUCTION_COVERAGE" and event.kind == "QUALITY":
            return InstructionCoverage.model_validate(body)
        if body.get("type") == "SOURCE_ALERT" and event.kind == "ALERT":
            return SourceAlert.model_validate(body)
    except (InvalidContent, ValidationError, ValueError):
        return None
    return None


def evaluate(
    ctx: RequestContext,
    g: Geometry,
    tracks: list[Track],
    events: list[SourceEvent],
    anchors: dict[UUID, Evidence],
    *,
    profile: RuleProfile,
) -> list[RuleSignal]:
    """Pure scoped rules; the service owns source retrieval/permissions/evidence verification."""
    records = [*tracks, *events]
    for record in records:
        if (record.session_id, record.revision) != (
            ctx.session_id,
            ctx.input_revision,
        ) or record.analysis_run_id is not None:
            raise ContractError("ACCESS_DENIED")
        anchor = anchors.get(record.id)
        if anchor is None or (
            anchor.session_id,
            anchor.analysis_run_id,
            anchor.revision,
            anchor.source_id,
            anchor.source_hash,
            anchor.segment_id,
        ) != (
            ctx.session_id,
            ctx.analysis_run_id,
            ctx.input_revision,
            record.source_id,
            record.source_hash,
            record.id,
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
    eligible = [
        r
        for r in records
        if r.event_time_ms <= ctx.as_of_ms
        and (
            ctx.mode == "DEBRIEF"
            or r.available_time_ms is not None
            and r.available_time_ms <= ctx.as_of_ms
        )
    ]
    eligible.sort(key=lambda r: (r.event_time_ms, str(r.id)))
    poses: dict[UUID, list[Track]] = {}
    decoded = [(e, decode(e)) for e in eligible if not isinstance(e, Track)]
    for record in eligible:
        if isinstance(record, Track) and record.entity_id is not None:
            poses.setdefault(record.entity_id, []).append(record)
    config_hash = hashed(
        {
            "profile": profile.version,
            "response_window_ms": profile.response_window_ms,
            "hold_line_id": profile.hold_line_id,
            "layout_version": profile.layout_version,
            "allowed_point": profile.allowed_point,
            "occupancy": profile.occupancy.__dict__,
            "layout": g.layout.model_dump(mode="json"),
        }
    )
    result: list[RuleSignal] = []

    def emit(
        code: str,
        entities: list[UUID],
        status: Literal["ACTIVE", "INACTIVE", "UNKNOWN"],
        reason: str,
        statement: str,
        proof: list[SourceEvent],
        *,
        priority: Literal["INFO", "NOTICE", "ATTENTION"] = "NOTICE",
        overlap_ms: int | None = None,
        exit_unknown: bool = False,
    ) -> None:
        if g.layout.version != profile.layout_version:
            status, reason, priority = "UNKNOWN", "RULE_PROFILE_NOT_APPLICABLE", "NOTICE"
            overlap_ms, exit_unknown = None, True
        entities = sorted(entities, key=str)
        unique = {p.id: p for p in proof}
        evidence = [anchors[k] for k in sorted(unique, key=str)]
        availability = [p.available_time_ms for p in unique.values()]
        result.append(
            RuleSignal(
                id=uuid5(
                    ctx.session_id,
                    f"{ctx.analysis_run_id}:{ctx.input_revision}:{profile.version}:{code}:"
                    f"{','.join(map(str, entities))}",
                ),
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                rule_id=code,
                status=status,
                reason=reason,
                statement=statement,
                priority=priority
                if status == "ACTIVE"
                else "NOTICE"
                if status == "UNKNOWN"
                else "INFO",
                entity_ids=entities,
                as_of_ms=ctx.as_of_ms,
                available_time_ms=max(v for v in availability if v is not None)
                if availability and all(v is not None for v in availability)
                else None,
                rule_version=profile.version,
                config_hash=config_hash,
                evidence=evidence,
                overlap_ms=overlap_ms,
                exit_unknown=exit_unknown,
            )
        )

    def health(history: list[Track]) -> str | None:
        latest = history[-1]
        if latest.quality != "SUPPORTED":
            return "TRACK_" + latest.quality
        if latest.age_ms + ctx.as_of_ms - latest.event_time_ms > profile.occupancy.stale_ms:
            return "STALE_TRACK"
        if any(
            b.event_time_ms - a.event_time_ms > profile.occupancy.gap_ms
            for a, b in zip(history, history[1:], strict=False)
        ):
            return "TRACK_GAP"
        if any(
            a.event_time_ms == b.event_time_ms
            and any(
                getattr(a, k) != getattr(b, k)
                for k in (
                    "x_m",
                    "y_m",
                    "heading_deg",
                    "speed_mps",
                    "length_m",
                    "width_m",
                    "source_id",
                    "source_hash",
                    "layout_version",
                )
            )
            for a, b in zip(history, history[1:], strict=False)
        ):
            return "TRACK_CONFLICTING"
        try:
            g._track(latest)
        except ContractError:
            return "LAYOUT_MISMATCH"
        return None

    for entity, history in poses.items():
        latest = history[-1]
        problem = health(history)
        inside = g.occupied(latest, resource="PROTECTION") if problem is None else False
        stopped = latest.speed_mps < profile.occupancy.speed_floor_mps
        emit(
            "STOPPED_IN_PROTECTION",
            [entity],
            "UNKNOWN" if problem else "ACTIVE" if inside and stopped else "INACTIVE",
            problem or ("STOPPED_EXIT_UNKNOWN" if inside and stopped else "NO_STOPPED_OCCUPANCY"),
            "A stopped observed footprint in protection requires review of "
            "unknown future motion and exit.",
            [latest],
            priority="ATTENTION",
            exit_unknown=inside and stopped or problem is not None,
        )
        instructions = [
            (e, p) for e, p in decoded if e.entity_id == entity and isinstance(p, Instruction)
        ]
        cancelled = {
            (e.source_id, p.related_source_event_id)
            for e, p in instructions
            if p.action in ("CANCEL", "HOLD_SHORT", "CROSS_RUNWAY", "LAND", "GO_AROUND")
            and p.related_source_event_id is not None
            and any(
                prior.source_id == e.source_id
                and prior.source_event_id == p.related_source_event_id
                and prior.event_time_ms < e.event_time_ms
                for prior, _ in instructions
            )
        }
        active = [
            (e, p)
            for e, p in instructions
            if p.action in ("HOLD_SHORT", "CROSS_RUNWAY", "LAND", "GO_AROUND")
            and (e.source_id, e.source_event_id) not in cancelled
        ]
        hold = next(((e, p) for e, p in reversed(active) if p.action == "HOLD_SHORT"), None)
        pair = history[-2:] if len(history) > 1 else []
        crossing = False
        movement_problem = problem
        if (
            len(pair) == 2
            and pair[1].event_time_ms > pair[0].event_time_ms
            and movement_problem is None
        ):
            try:
                crossing = g.crosses_hold(
                    pair[0], pair[1], profile.hold_line_id, allowed_point=profile.allowed_point
                )
            except ContractError:
                movement_problem = "MOTION_NOT_EVALUABLE"
        elif len(pair) != 2:
            movement_problem = movement_problem or "MOVEMENT_UNAVAILABLE"
        hold_problem = movement_problem or ("INSTRUCTION_UNAVAILABLE" if hold is None else None)
        if hold is not None and (
            hold[1].line_id != profile.hold_line_id
            or pair
            and hold[0].event_time_ms > pair[0].event_time_ms
        ):
            hold_problem = "INSTRUCTION_NOT_APPLICABLE"
        emit(
            "HOLD_SHORT_MOVEMENT",
            [entity],
            "UNKNOWN" if hold_problem else "ACTIVE" if crossing else "INACTIVE",
            hold_problem or ("OBSERVED_HOLD_CROSSING" if crossing else "NO_OBSERVED_CROSSING"),
            "Check full-footprint movement against an applicable source HOLD_SHORT record.",
            [*pair, *([hold[0]] if hold else [])] or [latest],
            priority="ATTENTION",
        )
        coverage = [
            e
            for e, p in decoded
            if isinstance(p, InstructionCoverage)
            and pair
            and p.start_ms <= pair[0].event_time_ms
            and p.end_ms > ctx.as_of_ms
            and e.source_id == latest.source_id
        ]
        permitted = [
            e
            for e, p in active
            if p.action == "CROSS_RUNWAY"
            and pair
            and e.event_time_ms <= pair[0].event_time_ms
            and e.source_id == latest.source_id
        ]
        ambiguous = [
            e for e, p in decoded if e.entity_id == entity and e.kind == "INSTRUCTION" and p is None
        ]
        no_clearance_problem = movement_problem or (
            "INSTRUCTION_AMBIGUOUS"
            if ambiguous
            else None
            if coverage
            else "INSTRUCTION_COVERAGE_UNKNOWN"
        )
        emit(
            "MOVEMENT_WITHOUT_OBSERVED_CLEARANCE",
            [entity],
            "UNKNOWN"
            if no_clearance_problem
            else "ACTIVE"
            if crossing and not permitted
            else "INACTIVE",
            no_clearance_problem
            or (
                "NO_APPLICABLE_OBSERVED_CROSS_RECORD"
                if crossing and not permitted
                else "NO_UNSUPPORTED_CROSSING"
            ),
            "Check observed movement for an applicable source crossing instruction; "
            "this does not prove no clearance was issued.",
            [*pair, *coverage, *permitted, *ambiguous] or [latest],
            priority="NOTICE",
        )
        for issued, p in active:
            if p.action != "GO_AROUND":
                continue
            responses = [
                e
                for e, q in instructions
                if q.action == "GO_AROUND_RESPONSE"
                and q.related_source_event_id == issued.source_event_id
                and e.source_id == issued.source_id
                and e.event_time_ms >= issued.event_time_ms
            ]
            delayed = (
                ctx.as_of_ms - issued.event_time_ms > profile.response_window_ms and not responses
            )
            emit(
                "GO_AROUND_RESPONSE_DELAY",
                [entity],
                "ACTIVE" if delayed else "INACTIVE",
                "RESPONSE_NOT_OBSERVED_IN_LAB_WINDOW"
                if delayed
                else "RESPONSE_OBSERVED_OR_WINDOW_OPEN",
                "Check source GO_AROUND response against the configured LAB_RULE window; "
                "physical occupancy is independent.",
                [issued, *responses],
                priority="NOTICE",
            )
    for (a, ha), (b, hb) in combinations(sorted(poses.items(), key=lambda p: str(p[0])), 2):
        x, y = ha[-1], hb[-1]
        problem = health(ha) or health(hb)
        if x.source_id != y.source_id or x.source_hash != y.source_hash:
            problem = "SOURCE_RESOURCE_ALIGNMENT_UNKNOWN"
        duration: int | None = None
        reason = problem
        status: Literal["ACTIVE", "INACTIVE", "UNKNOWN"] = "UNKNOWN"
        if problem is None:
            try:
                fa, fb = [
                    predict(
                        g,
                        t,
                        ctx.as_of_ms,
                        profile.occupancy,
                        ctx.as_of_ms - t.event_time_ms + t.age_ms,
                    )
                    for t in (x, y)
                ]
                duration = overlap(fa.intervals, fb.intervals)
                occupied = g.occupied(x) and g.occupied(y)
                if occupied:
                    status, reason = "ACTIVE", "OBSERVED_FOOTPRINT_OVERLAP"
                elif fa.unknown or fb.unknown:
                    reason = "PREDICTION_UNKNOWN"
                elif duration:
                    status, reason = "ACTIVE", "PREDICTED_MODEL_OVERLAP"
                else:
                    status, reason = "INACTIVE", "NO_MODELED_OVERLAP"
            except ContractError:
                reason = "MOTION_NOT_EVALUABLE"
        emit(
            "RUNWAY_SHARED_RESOURCE",
            [a, b],
            status,
            reason or "UNKNOWN",
            "Compare observed/predicted footprint intervals on the same runway resource.",
            [x, y],
            priority="ATTENTION",
            overlap_ms=duration,
            exit_unknown=problem is not None,
        )
    return sorted(result, key=lambda r: (r.rule_id, str(r.id)))
