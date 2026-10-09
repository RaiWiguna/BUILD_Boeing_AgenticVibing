"""Speech-only loop closure policy. Coverage and matching evidence are mandatory."""

from collections.abc import Sequence
from typing import Literal
from uuid import UUID, uuid5

from flowlens.contracts.models import Contract, RequestContext
from flowlens.core.errors import ContractError
from flowlens.intent.validation import visible
from flowlens.memory.models import AcceptedEvent, Invalidation


class LoopState(Contract):
    id: UUID
    originating_id: UUID
    kind: Literal[
        "REQUEST_RESPONSE",
        "REPORT_EXPECTED",
        "COORDINATION_PENDING",
        "READBACK_EXPECTED",
    ]
    status: Literal["OPEN", "UNKNOWN", "CLOSED_WITH_EVIDENCE", "CANCELLED", "SUPERSEDED"]
    coverage_known: bool
    started_ms: int
    expected_window_ms: int | None = None
    timer_profile_version: Literal["synthetic-no-deadline-1"] = "synthetic-no-deadline-1"
    closing_evidence_ids: tuple[UUID, ...] = ()


def reconstruct_loops(
    context: RequestContext,
    events: Sequence[AcceptedEvent | Invalidation],
) -> tuple[LoopState, ...]:
    context.require("read", context.session_id, context.analysis_run_id)
    included = []
    seen: set[UUID] = set()
    for event in events:
        if event.id in seen or event.reducer_version != "memory-1":
            raise ContractError("VERSION_CONFLICT")
        seen.add(event.id)
        if (event.session_id, event.analysis_run_id, event.revision, event.input_hash) != (
            context.session_id,
            context.analysis_run_id,
            context.input_revision,
            context.input_hash,
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        try:
            visible(context, event)
        except ContractError:
            continue
        included.append(event)
    stale = {target for e in included if isinstance(e, Invalidation) for target in e.targets}
    accepted = sorted(
        (e for e in included if isinstance(e, AcceptedEvent)),
        key=lambda e: (e.event_time_ms, str(e.id)),
    )
    loops: dict[UUID, LoopState] = {}
    for event in accepted:
        candidate = event.candidate
        kind: (
            Literal[
                "REQUEST_RESPONSE",
                "REPORT_EXPECTED",
                "COORDINATION_PENDING",
                "READBACK_EXPECTED",
            ]
            | None
        ) = None
        replacement = (
            candidate.speech_act == "CORRECTION"
            and event.link is not None
            and event.link.status == "SUPPORTED"
            and event.link.target_id in loops
        )
        if candidate.speech_act == "INSTRUCTION" or replacement:
            kind = "REPORT_EXPECTED" if "REPORT" in candidate.actions else "READBACK_EXPECTED"
        elif candidate.speech_act == "REQUEST":
            kind = "REQUEST_RESPONSE"
        elif candidate.speech_act == "COORDINATION" and not (
            event.link
            and event.link.status == "SUPPORTED"
            and event.link.relationship == "COORDINATION_FOR"
        ):
            kind = "COORDINATION_PENDING"
        if kind and len(candidate.entity_candidates) == 1:
            loops[event.id] = LoopState(
                id=uuid5(event.id, kind),
                originating_id=event.id,
                kind=kind,
                status="OPEN"
                if (
                    event.coverage_known
                    and candidate.callsign.quality == "SUPPORTED"
                    and candidate.role != "UNKNOWN"
                )
                else "UNKNOWN",
                coverage_known=event.coverage_known,
                started_ms=event.event_time_ms,
            )
        link = event.link
        if not link or link.status != "SUPPORTED" or link.target_id not in loops:
            continue
        old = loops[link.target_id]
        if old.originating_id in stale:
            continue
        updates: dict[str, object] = {}
        if link.relationship in ("CANCELS", "CORRECTION_OF"):
            updates["status"] = "CANCELLED" if link.relationship == "CANCELS" else "SUPERSEDED"
        else:
            if old.status not in ("OPEN", "UNKNOWN"):
                continue
            expected = {
                "READBACK_EXPECTED": "READBACK_OF",
                "REPORT_EXPECTED": "REPORT_FOR",
                "REQUEST_RESPONSE": "RESPONSE_TO",
                "COORDINATION_PENDING": "COORDINATION_FOR",
            }[old.kind]
            if (
                link.relationship == expected
                and link.match == "MATCHED"
                and event.coverage_known
                and old.coverage_known
                and event.id not in stale
            ):
                updates.update(
                    status="CLOSED_WITH_EVIDENCE",
                    closing_evidence_ids=tuple(e.id for e in candidate.evidence),
                )
        loops[link.target_id] = LoopState.model_validate(old.model_dump() | updates)
    for identifier in stale:
        if identifier in loops:
            loops[identifier] = loops[identifier].model_copy(
                update={"status": "SUPERSEDED", "closing_evidence_ids": ()}
            )
    return tuple(loops[k] for k in sorted(loops, key=str))


def closes_readback(event: AcceptedEvent) -> bool:
    return (
        event.coverage_known
        and event.link is not None
        and event.link.relationship == "READBACK_OF"
        and event.link.status == "SUPPORTED"
        and event.link.match == "MATCHED"
        and bool(event.candidate.evidence)
    )
