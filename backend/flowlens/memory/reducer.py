"""Pure reconstruction. No provider memory, IO, current-clock lookup or safety inference."""

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from flowlens.contracts.models import Contract, RequestContext
from flowlens.core.errors import ContractError
from flowlens.intent.validation import visible
from flowlens.loops import closes_readback
from flowlens.memory.models import REDUCER, AcceptedEvent, Invalidation


class Projection(Contract):
    originating_id: UUID
    entity_id: UUID
    interpretation: Literal["SUPPORTED", "AMBIGUOUS"]
    instruction: Literal["ACTIVE", "SUPERSEDED", "CANCELLED", "COMPLETED_REPORTED", "UNKNOWN"]
    readback: Literal["NOT_OBSERVED", "MATCHED", "PARTIAL", "MISMATCH", "AMBIGUOUS"]
    movement: Literal["NOT_EVALUABLE"] = "NOT_EVALUABLE"
    reviewer: Literal["UNREVIEWED"] = "UNREVIEWED"
    report: Literal["NOT_OBSERVED", "REPORTED"] = "NOT_OBSERVED"
    loop: Literal["OPEN", "UNKNOWN", "CLOSED_WITH_EVIDENCE", "CANCELLED", "SUPERSEDED"]
    coverage_known: bool
    closing_evidence_ids: tuple[UUID, ...] = ()
    stale: bool = False
    condition: str | None
    negation: str | None
    applicability: Literal["CONDITIONAL", "UNKNOWN", "UNCONDITIONAL"]


def reconstruct(
    context: RequestContext,
    events: Sequence[AcceptedEvent | Invalidation],
    *,
    reducer_version: str = REDUCER,
) -> tuple[Projection, ...]:
    if reducer_version != REDUCER:
        raise ContractError("VERSION_CONFLICT")
    context.require("read", context.session_id, context.analysis_run_id)
    included = []
    ids: set[UUID] = set()
    for event in events:
        if event.id in ids:
            raise ContractError("VERSION_CONFLICT")
        ids.add(event.id)
        if (event.session_id, event.analysis_run_id, event.revision, event.input_hash) != (
            context.session_id,
            context.analysis_run_id,
            context.input_revision,
            context.input_hash,
        ) or event.reducer_version != reducer_version:
            raise ContractError("SOURCE_REVISION_CHANGED")
        try:
            visible(context, event)
        except ContractError:
            continue
        included.append(event)
    # Dependencies, rather than arrival order, determine projection. Invalidations
    # are applied after the fact and remain invisible before their availability.
    accepted = sorted(
        (e for e in included if isinstance(e, AcceptedEvent)),
        key=lambda e: (e.event_time_ms, str(e.id)),
    )
    invalid = {target for e in included if isinstance(e, Invalidation) for target in e.targets}
    invalid.update(target for e in accepted for target in e.invalidates)
    changed = True
    while changed:
        changed = False
        for event in accepted:
            if event.link and event.link.target_id in invalid and event.id not in invalid:
                invalid.add(event.id)
                changed = True
    state: dict[UUID, Projection] = {}
    for event in accepted:
        candidate, link = event.candidate, event.link
        replacement = (
            candidate.speech_act == "CORRECTION"
            and link is not None
            and link.status == "SUPPORTED"
            and link.target_id in state
            and state[link.target_id].instruction == "ACTIVE"
            and not state[link.target_id].stale
        )
        if (candidate.speech_act == "INSTRUCTION" or replacement) and (
            len(candidate.entity_candidates) == 1
        ):
            if candidate.callsign.quality != "SUPPORTED":
                continue
            supported = (
                candidate.role == "CONTROLLER"
                and candidate.runway.quality == "SUPPORTED"
                and bool(candidate.actions)
                and "UNKNOWN" not in candidate.actions
            )
            state[event.id] = Projection(
                originating_id=event.id,
                entity_id=candidate.entity_candidates[0],
                interpretation="SUPPORTED" if supported else "AMBIGUOUS",
                instruction="ACTIVE" if supported else "UNKNOWN",
                readback="NOT_OBSERVED",
                loop="OPEN" if event.coverage_known else "UNKNOWN",
                coverage_known=event.coverage_known,
                stale=event.id in invalid,
                condition=candidate.condition.value,
                negation=candidate.negation.value,
                applicability="CONDITIONAL"
                if candidate.condition.value
                else (
                    "UNCONDITIONAL"
                    if candidate.condition.unknowns == ("NO_EXPLICIT_CUE",)
                    else "UNKNOWN"
                ),
            )
        if not link or link.status != "SUPPORTED" or link.target_id not in state:
            continue
        old = state[link.target_id]
        if old.instruction != "ACTIVE" or old.stale or event.id in invalid:
            continue
        updates: dict[str, object] = {}
        if link.relationship == "READBACK_OF":
            updates["readback"] = link.match if link.match != "UNKNOWN" else "AMBIGUOUS"
            if closes_readback(event) and old.coverage_known:
                updates.update(
                    loop="CLOSED_WITH_EVIDENCE",
                    closing_evidence_ids=tuple(e.id for e in candidate.evidence),
                )
        elif link.relationship == "CANCELS":
            updates.update(instruction="CANCELLED", loop="CANCELLED")
        elif link.relationship == "CORRECTION_OF":
            updates.update(instruction="SUPERSEDED", loop="SUPERSEDED", stale=True)
        elif link.relationship == "REPORT_FOR":
            updates["report"] = "REPORTED"
            origin = next(e.candidate for e in accepted if e.id == old.originating_id)
            if link.match == "MATCHED" and set(origin.actions).intersection(("REPORT", "VACATE")):
                updates["instruction"] = "COMPLETED_REPORTED"
            # A report is never a track observation or automatic readback closure.
        state[link.target_id] = Projection.model_validate(old.model_dump() | updates)
    return tuple(state[k] for k in sorted(state, key=str))
