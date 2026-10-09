"""Deterministic semantic eligibility from accepted memory, separate source facts."""

import hashlib
from typing import Literal
from uuid import UUID, uuid5

from flowlens.advisory.models import Fact, Finding, Inputs
from flowlens.contracts.models import Evidence, RequestContext
from flowlens.contracts.ports import EvidenceService
from flowlens.core.errors import ContractError
from flowlens.intent.validation import visible
from flowlens.memory.models import AcceptedEvent
from flowlens.memory.reducer import reconstruct


def digest(inputs: Inputs) -> str:
    canonical = Inputs(
        events=tuple(sorted(inputs.events, key=lambda e: str(e.id))),
        facts=tuple(sorted(inputs.facts, key=lambda e: str(e.id))),
        signals=tuple(sorted(inputs.signals, key=lambda e: str(e.id))),
    )
    return hashlib.sha256(canonical.model_dump_json().encode()).hexdigest()


def validate_inputs(ctx: RequestContext, inputs: Inputs, evidence: EvidenceService) -> None:
    ctx.require("read", ctx.session_id, ctx.analysis_run_id)
    if "truth" in ctx.capabilities:
        raise ContractError("ACCESS_DENIED")
    ids: set[UUID] = set()
    for row in (*inputs.events, *inputs.facts, *inputs.signals):
        visible(ctx, row)
        if row.id in ids:
            raise ContractError("INVALID_INPUT")
        ids.add(row.id)
        if isinstance(row, AcceptedEvent) and row.input_hash != ctx.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        evs = (
            row.candidate.evidence
            if isinstance(row, AcceptedEvent)
            else getattr(row, "evidence", ())
        )
        for ev in evs:
            if (ev.session_id, ev.analysis_run_id, ev.revision) != (
                ctx.session_id,
                ctx.analysis_run_id,
                ctx.input_revision,
            ):
                raise ContractError("ACCESS_DENIED")
            if ev.end_ms is not None and ev.end_ms > ctx.as_of_ms:
                raise ContractError("ACCESS_DENIED")
            if evidence.resolve(ctx, ev) != ev:
                raise ContractError("EVIDENCE_UNAVAILABLE")
    facts = {f.id: f for f in inputs.facts}
    for fact in inputs.facts:
        required_kinds = {
            "OBSERVED": {"TRACK", "EVENT"},
            "SOURCE_ALERT": {"EVENT"},
            "SOURCE_RECORD": {"EVENT", "POLICY"},
        }.get(fact.label)
        if required_kinds and not any(e.kind in required_kinds for e in fact.evidence):
            raise ContractError("NOT_EVALUABLE")
    for signal in inputs.signals:
        if not set(signal.fact_ids) <= facts.keys():
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if signal.status == "SUPPORTED":
            labels = {facts[i].label for i in signal.fact_ids}
            required = (
                {"SAID", "OBSERVED"}
                if signal.category == "MOVEMENT_DIVERGENCE"
                else {"SAID", "SOURCE_RECORD"}
            )
            if signal.category != "QUALITY_GAP" and (
                signal.entity_id is None or not required <= labels
            ):
                raise ContractError("NOT_EVALUABLE")
            if not signal.evidence:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if not {e.id for i in signal.fact_ids for e in facts[i].evidence} <= {
                e.id for e in signal.evidence
            }:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if any(facts[i].entity_id != signal.entity_id for i in signal.fact_ids):
                raise ContractError("NOT_EVALUABLE")
            if signal.category != "QUALITY_GAP":
                eligible = signal.eligibility
                if eligible is None or not all(
                    (
                        eligible.identity_known,
                        eligible.association_known,
                        eligible.clock_aligned,
                        eligible.coverage_known,
                        eligible.instruction_applicable,
                    )
                ):
                    raise ContractError("NOT_EVALUABLE")
                if signal.category == "MOVEMENT_DIVERGENCE":
                    geometry = signal.geometry
                    if (
                        geometry is None
                        or not eligible.track_fresh
                        or (
                            geometry.session_id,
                            geometry.analysis_run_id,
                            geometry.revision,
                            geometry.entity_id,
                            geometry.rule_version,
                        )
                        != (
                            ctx.session_id,
                            ctx.analysis_run_id,
                            ctx.input_revision,
                            signal.entity_id,
                            signal.rule_version,
                        )
                        or geometry.status != "EVALUATED"
                        or geometry.occupied is None
                        or (geometry.uncertainty_ms is None)
                        or not geometry.intervals
                    ):
                        raise ContractError("NOT_EVALUABLE")
                    if any(i.end_ms > ctx.as_of_ms for i in geometry.intervals):
                        raise ContractError("ACCESS_DENIED")
                    if not {e.id for e in geometry.evidence} <= {e.id for e in signal.evidence}:
                        raise ContractError("EVIDENCE_UNAVAILABLE")


def catalog(ctx: RequestContext, inputs: Inputs) -> tuple[Fact, ...]:
    """Only exact excerpts become speech facts; no provider invented paraphrases."""
    facts = sorted(inputs.facts, key=lambda f: str(f.id))
    projections = reconstruct(ctx, inputs.events)
    stale = {p.originating_id for p in projections if p.stale}
    invalid = {t for e in inputs.events if not isinstance(e, AcceptedEvent) for t in e.targets}
    for event in sorted(inputs.events, key=lambda e: (e.event_time_ms, str(e.id))):
        if not isinstance(event, AcceptedEvent) or event.id in stale | invalid:
            continue
        c = event.candidate
        if not c.evidence:
            continue
        label: Literal["HEARD", "REPORTED", "SAID"] = (
            "HEARD"
            if c.speech_act == "READBACK"
            else ("REPORTED" if c.speech_act == "REPORT" else "SAID")
        )
        facts.append(
            Fact(
                id=event.id,
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                event_time_ms=event.event_time_ms,
                available_time_ms=event.available_time_ms,
                recorded_at=event.recorded_at,
                label=label,
                statement=" | ".join(e.quote for e in c.evidence if e.quote),
                evidence=c.evidence,
                entity_id=c.entity_candidates[0] if len(c.entity_candidates) == 1 else None,
            )
        )
    return tuple(facts)


def assemble(ctx: RequestContext, inputs: Inputs) -> tuple[Finding, ...]:
    events = {
        e.id: e
        for e in sorted(inputs.events, key=lambda e: str(e.id))
        if isinstance(e, AcceptedEvent)
    }
    findings: list[Finding] = []

    def add(
        identifier: UUID,
        category: str,
        statement: str,
        evs: tuple[Evidence, ...],
        entities: tuple[UUID, ...],
        supported: bool,
        unknowns: tuple[str, ...],
        said: tuple[UUID, ...] = (),
        heard: tuple[UUID, ...] = (),
        observed: tuple[UUID, ...] = (),
        rule: str = "findings-1",
    ) -> None:
        findings.append(
            Finding.model_validate(
                {
                    "id": uuid5(identifier, category),
                    "category": category,
                    "statement": statement,
                    "status": "SUPPORTED" if supported else "NOT_EVALUABLE",
                    "priority": "ATTENTION"
                    if supported
                    and category
                    in ("READBACK_DISCREPANCY", "MOVEMENT_DIVERGENCE", "SPEECH_RECORD_DISCREPANCY")
                    else "NOTICE",
                    "evidence": evs,
                    "entity_ids": entities,
                    "said": said,
                    "heard": heard,
                    "observed": observed,
                    "rule_version": rule,
                    "unknowns": unknowns,
                    "quality": "SUPPORTED" if supported else "MISSING",
                }
            )
        )

    projections = reconstruct(ctx, inputs.events)
    invalid = {p.originating_id for p in projections if p.stale}
    invalid.update(t for e in inputs.events if not isinstance(e, AcceptedEvent) for t in e.targets)
    for event in events.values():
        c = event.candidate
        if event.id in invalid:
            continue
        if len(c.entity_candidates) != 1 or any(
            slot.quality != "SUPPORTED" for slot in (c.callsign, c.runway)
        ):
            add(
                event.id,
                "CRITICAL_SLOT_UNCERTAIN",
                "Critical slot or identity requires review.",
                c.evidence,
                c.entity_candidates,
                bool(c.evidence),
                ("CRITICAL_SLOT_OR_IDENTITY_UNKNOWN",),
                (event.id,) if c.speech_act == "INSTRUCTION" else (),
                (event.id,) if c.speech_act == "READBACK" else (),
            )
    for p in projections:
        if p.stale or p.instruction in ("SUPERSEDED", "CANCELLED"):
            continue
        event = events[p.originating_id]
        c, evs, entities = event.candidate, event.candidate.evidence, (p.entity_id,)
        readbacks = [
            e
            for e in events.values()
            if e.link
            and e.link.status == "SUPPORTED"
            and e.link.relationship == "READBACK_OF"
            and e.link.target_id == event.id
        ]
        if p.readback in ("MISMATCH", "PARTIAL", "AMBIGUOUS"):
            read_evs = tuple({e.id: e for r in readbacks for e in r.candidate.evidence}.values())
            good = (
                p.readback == "MISMATCH"
                and bool(evs)
                and bool(read_evs)
                and all(
                    slot.quality == "SUPPORTED"
                    for candidate in (c, *(r.candidate for r in readbacks))
                    for slot in (candidate.callsign, candidate.runway)
                )
            )
            add(
                event.id,
                "READBACK_DISCREPANCY",
                "Readback comparison requires review.",
                evs + read_evs,
                entities,
                good,
                () if good else ("PAIR_OR_SLOTS_UNCERTAIN",),
                (event.id,),
                tuple(r.id for r in readbacks),
            )
        if p.loop in ("OPEN", "UNKNOWN"):
            add(
                event.id,
                "OPEN_LOOP",
                "Communication obligation remains open or unknown.",
                evs,
                entities,
                p.coverage_known and bool(evs) and p.instruction == "ACTIVE",
                ()
                if p.coverage_known and p.instruction == "ACTIVE"
                else ("COVERAGE_OR_INSTRUCTION_UNKNOWN",),
                (event.id,),
            )
        # Readback/report never establish physical movement. External eligibility
        # must come through authoritative source/geometry adapter, independently.
        if not any(
            s.category == "MOVEMENT_DIVERGENCE" and s.entity_id == p.entity_id
            for s in inputs.signals
        ):
            add(
                event.id,
                "MOVEMENT_DIVERGENCE",
                "Movement comparison unavailable.",
                evs,
                entities,
                False,
                ("ALIGNED_FRESH_APPLICABLE_GEOMETRY_REQUIRED",),
                (event.id,),
            )
    for s in sorted(inputs.signals, key=lambda s: str(s.id)):
        labels = {f.id: f.label for f in inputs.facts}
        add(
            s.id,
            s.category,
            {
                "MOVEMENT_DIVERGENCE": "Eligible source movement comparison requires review.",
                "SPEECH_RECORD_DISCREPANCY": "Speech and source record comparison requires review.",
                "QUALITY_GAP": "Source alignment or quality requires review.",
            }[s.category],
            s.evidence,
            () if s.entity_id is None else (s.entity_id,),
            s.status == "SUPPORTED",
            s.unknowns,
            tuple(i for i in s.fact_ids if labels[i] == "SAID"),
            observed=tuple(i for i in s.fact_ids if labels[i] == "OBSERVED"),
            rule=s.rule_version,
        )
    return tuple(findings)
