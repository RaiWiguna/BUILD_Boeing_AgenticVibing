"""Deterministic conservative association; no forced nearest-message pairing."""

from collections.abc import Mapping, Sequence
from typing import Literal
from uuid import UUID

from pydantic import Field

from flowlens.contracts.models import Contract, TranscriptSegment
from flowlens.intent.models import Candidate
from flowlens.intent.validation import words


class Link(Contract):
    source_id: UUID
    target_id: UUID | None
    alternatives: tuple[UUID, ...]
    relationship: Literal[
        "READBACK_OF",
        "REPORT_FOR",
        "CORRECTION_OF",
        "CANCELS",
        "POSSIBLE_LINK",
        "RESPONSE_TO",
        "COORDINATION_FOR",
    ]
    status: Literal["SUPPORTED", "AMBIGUOUS", "MISSING"]
    match: Literal["MATCHED", "MISMATCH", "PARTIAL", "UNKNOWN"]
    unknowns: tuple[str, ...] = Field(max_length=16)


def associate(
    source: Candidate,
    prior: Sequence[Candidate],
    segments: Mapping[UUID, TranscriptSegment],
    *,
    max_delay_ms: int = 120000,
) -> Link:
    relationship: Literal[
        "READBACK_OF",
        "REPORT_FOR",
        "CORRECTION_OF",
        "CANCELS",
        "POSSIBLE_LINK",
        "RESPONSE_TO",
        "COORDINATION_FOR",
    ]
    relationship = {
        "READBACK": "READBACK_OF",
        "REPORT": "REPORT_FOR",
        "CORRECTION": "CORRECTION_OF",
        "CANCELLATION": "CANCELS",
        "INFORMATION": "RESPONSE_TO",
        "COORDINATION": "COORDINATION_FOR",
    }.get(source.speech_act, "POSSIBLE_LINK")  # type: ignore[assignment]
    current = segments[source.segment_id]
    possible = []
    for item in prior:
        old = segments[item.segment_id]
        expected_acts = (
            ("REQUEST",)
            if source.speech_act == "INFORMATION"
            else ("COORDINATION",)
            if source.speech_act == "COORDINATION"
            else ("INSTRUCTION", "CORRECTION")
        )
        if item.id == source.id or item.speech_act not in expected_acts:
            continue
        delay = current.start_ms - old.end_ms
        if delay < 0 or delay > max_delay_ms:
            continue
        if not set(source.entity_candidates).intersection(item.entity_candidates):
            continue
        if source.speech_act in ("READBACK", "REPORT") and (
            source.role not in ("PILOT", "VEHICLE") or item.role != "CONTROLLER"
        ):
            continue
        if source.speech_act in ("CORRECTION", "CANCELLATION") and source.role != "CONTROLLER":
            continue
        if source.speech_act in ("CORRECTION", "CANCELLATION") and (
            not set(source.actions).intersection(item.actions) or "UNKNOWN" in source.actions
        ):
            continue
        if source.speech_act == "CANCELLATION" and source.runway.value != item.runway.value:
            continue
        possible.append(item)
    possible.sort(key=lambda c: str(c.id))
    certain = (
        len(possible) == 1
        and len(source.entity_candidates) == 1
        and len(possible[0].entity_candidates) == 1
        and source.callsign.quality == possible[0].callsign.quality == "SUPPORTED"
        and source.role != "UNKNOWN"
        and possible[0].role != "UNKNOWN"
        and current.quality == segments[possible[0].segment_id].quality == "SUPPORTED"
        and relationship != "POSSIBLE_LINK"
    )
    target = possible[0] if certain else None
    match: Literal["MATCHED", "MISMATCH", "PARTIAL", "UNKNOWN"] = "UNKNOWN"
    if target and source.speech_act in ("READBACK", "REPORT", "INFORMATION", "COORDINATION"):
        critical_unknown = any(
            (slot.value is None and slot.unknowns != ("NO_EXPLICIT_CUE",))
            or (slot.value is not None and slot.quality != "SUPPORTED")
            for slot in (source.negation, target.negation, source.condition, target.condition)
        )
        if critical_unknown or not source.actions or "UNKNOWN" in source.actions:
            match = "PARTIAL"
        elif any(s.quality != "SUPPORTED" for s in (source.runway, target.runway)):
            match = "PARTIAL"
        elif words(source.runway.value or "") != words(target.runway.value or "") or (
            source.actions != target.actions
        ):
            match = "MISMATCH"
        elif source.negation.value != target.negation.value:
            match = "MISMATCH"
        elif source.condition.value != target.condition.value:
            match = "PARTIAL"
        else:
            match = "MATCHED"
    return Link(
        source_id=source.id,
        target_id=None if target is None else target.id,
        alternatives=tuple(c.id for c in possible),
        relationship=relationship,
        status="SUPPORTED" if target else ("AMBIGUOUS" if possible else "MISSING"),
        match=match,
        unknowns=() if target else ("IDENTITY_TIMING_OR_COMPETING_TARGETS",),
    )
