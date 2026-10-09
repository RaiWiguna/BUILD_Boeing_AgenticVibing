"""Conservative lexical support is necessary, never proof of domain correctness."""

import re
from collections.abc import Mapping
from uuid import UUID

from flowlens.contracts.models import RequestContext, Timed, TranscriptSegment
from flowlens.contracts.ports import EvidenceService
from flowlens.core.errors import ContractError
from flowlens.intent.models import Candidate, QuoteSlot

ACTION_PHRASES = {
    "HOLD_SHORT": ("hold short",),
    "CROSS_RUNWAY": ("cross", "crossing"),
    "LINE_UP_WAIT": ("line up and wait",),
    "TAKEOFF": ("takeoff", "take off"),
    "LAND": ("land", "landing"),
    "TAXI": ("taxi",),
    "VACATE": ("vacate", "vacated"),
    "CONTACT": ("contact",),
    "REPORT": ("report", "clear"),
}


def visible(context: RequestContext, row: Timed) -> None:
    if (row.session_id, row.analysis_run_id, row.revision) != (
        context.session_id,
        context.analysis_run_id,
        context.input_revision,
    ):
        raise ContractError("ACCESS_DENIED")
    if row.event_time_ms > context.as_of_ms or (
        context.mode == "AS_KNOWN"
        and (row.available_time_ms is None or row.available_time_ms > context.as_of_ms)
    ):
        raise ContractError("ACCESS_DENIED")


def words(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", text.casefold()))


def validate(
    context: RequestContext,
    candidate: Candidate,
    segments: Mapping[UUID, TranscriptSegment],
    identities: Mapping[UUID, tuple[str, ...]],
    evidence: EvidenceService,
) -> Candidate:
    context.require("read", context.session_id, context.analysis_run_id)
    candidate = Candidate.model_validate_json(candidate.model_dump_json())
    roles = {
        "INSTRUCTION": ("CONTROLLER", "UNKNOWN"),
        "READBACK": ("PILOT", "VEHICLE", "UNKNOWN"),
        "CORRECTION": ("CONTROLLER", "UNKNOWN"),
        "CANCELLATION": ("CONTROLLER", "UNKNOWN"),
    }
    if candidate.speech_act in roles and candidate.role not in roles[candidate.speech_act]:
        raise ContractError("INVALID_AI_OUTPUT")
    segment = segments.get(candidate.segment_id)
    if segment is None:
        raise ContractError("EVIDENCE_UNAVAILABLE")
    visible(context, segment)
    if segment.end_ms > context.as_of_ms:
        raise ContractError("ACCESS_DENIED")
    refs = {e.id: e for e in candidate.evidence}
    if len(refs) != len(candidate.evidence):
        raise ContractError("INVALID_AI_OUTPUT")
    for ev in refs.values():
        if (
            (ev.session_id, ev.analysis_run_id, ev.revision)
            != (context.session_id, context.analysis_run_id, context.input_revision)
            or ev.segment_id != segment.id
            or ev.kind != "TRANSCRIPT"
            or ev.source_id != segment.source_id
            or ev.span_start is None
            or ev.span_end is None
            or ev.quote is None
            or ev.span_end > len(segment.text)
            or segment.text[ev.span_start : ev.span_end] != ev.quote
            or ev.start_ms is None
            or ev.end_ms is None
            or ev.start_ms < segment.start_ms
            or ev.end_ms > segment.end_ms
            or not any(item.source_hash == ev.source_hash for item in segment.evidence)
            or evidence.resolve(context, ev) != ev
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")

    def slot(value: QuoteSlot) -> None:
        if not set(value.evidence_ids) <= refs.keys():
            raise ContractError("INVALID_AI_OUTPUT")
        if value.value is None:
            if not value.unknowns or value.quality == "SUPPORTED":
                raise ContractError("INVALID_AI_OUTPUT")
        elif not value.evidence_ids or not any(
            words(value.value) == words(refs[i].quote or "") for i in value.evidence_ids
        ):
            # Normalization/phonetic expansion is not silently inferred.
            raise ContractError("INVALID_AI_OUTPUT")
        if value.quality == "SUPPORTED" and value.alternatives:
            raise ContractError("INVALID_AI_OUTPUT")

    for value in (candidate.callsign, candidate.runway, candidate.condition, candidate.negation):
        slot(value)
    for entity in candidate.entity_candidates:
        if (
            entity not in identities
            or candidate.callsign.value is None
            or not any(
                words(alias) == words(candidate.callsign.value) for alias in identities[entity]
            )
        ):
            raise ContractError("INVALID_AI_OUTPUT")
    text = words(segment.text)
    # Explicit cues cannot disappear into null critical fields.
    for cues, value in (
        (("not", "negative", "never", "cancel", "cancelled"), candidate.negation),
        (("after", "until", "if", "behind", "when"), candidate.condition),
    ):
        if any(cue in text.split() for cue in cues) and value.value is None:
            raise ContractError("INVALID_AI_OUTPUT")
        if value.unknowns == ("NO_EXPLICIT_CUE",) and value.value is not None:
            raise ContractError("INVALID_AI_OUTPUT")
    if not set(candidate.action_evidence_ids) <= refs.keys():
        raise ContractError("INVALID_AI_OUTPUT")
    action_text = " ".join(words(refs[i].quote or "") for i in candidate.action_evidence_ids)
    for action in candidate.actions:
        if action != "UNKNOWN" and not any(
            f" {phrase} " in f" {action_text} " for phrase in ACTION_PHRASES[action]
        ):
            raise ContractError("INVALID_AI_OUTPUT")
    if candidate.speech_act == "CANCELLATION" and not any(
        cue in text.split() for cue in ("cancel", "cancelled")
    ):
        raise ContractError("INVALID_AI_OUTPUT")
    if candidate.speech_act == "CORRECTION" and "correction" not in text.split():
        raise ContractError("INVALID_AI_OUTPUT")
    return candidate
