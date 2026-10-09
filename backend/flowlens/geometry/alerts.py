"""Pure immutable alert revisions; source severity and reviewer seen state remain separate."""

from typing import Literal
from uuid import UUID, uuid5

from flowlens.contracts.models import Evidence, RequestContext, Scoped, SourceEvent
from flowlens.core.errors import ContractError
from flowlens.geometry.rules import RuleSignal, SourceAlert, decode
from flowlens.imports.metadata import hashed


class AlertRevision(Scoped):
    id: UUID
    revision_id: UUID
    previous_revision_id: UUID | None
    version: int
    origin: Literal["SOURCE", "DETERMINISTIC"]
    status: Literal["ACTIVE", "CLEARED", "UNKNOWN"]
    priority: Literal["INFO", "NOTICE", "ATTENTION"] | None
    source_severity: Literal["INFO", "WARNING", "CRITICAL"] | None
    source_event: SourceEvent | None
    source_variants: list[SourceEvent] = []
    rule_id: str | None
    rule_version: str
    config_hash: str
    dependency_hash: str
    entity_ids: list[UUID]
    evidence: list[Evidence]
    as_of_ms: int
    available_time_ms: int | None
    statement: str
    reason: str
    exit_unknown: bool


class Acknowledgement(Scoped):
    id: UUID
    alert_id: UUID
    alert_revision_id: UUID
    actor_id: UUID
    as_of_ms: int
    meaning: Literal["SEEN_ONLY"] = "SEEN_ONLY"


def _check(
    previous: AlertRevision | None,
    *,
    identifier: UUID,
    session: UUID,
    run: UUID | None,
    revision: int,
    time: int,
    origin: str,
) -> None:
    if previous is not None and (
        previous.id,
        previous.session_id,
        previous.analysis_run_id,
        previous.revision,
        previous.origin,
    ) != (identifier, session, run, revision, origin):
        raise ContractError("ACCESS_DENIED")
    if previous is not None and time < previous.as_of_ms:
        raise ContractError("VERSION_CONFLICT")


def reduce_signal(previous: AlertRevision | None, signal: RuleSignal) -> AlertRevision:
    signal = RuleSignal.model_validate_json(signal.model_dump_json())
    _check(
        previous,
        identifier=signal.id,
        session=signal.session_id,
        run=signal.analysis_run_id,
        revision=signal.revision,
        time=signal.as_of_ms,
        origin="DETERMINISTIC",
    )
    if any(
        (e.session_id, e.analysis_run_id, e.revision)
        != (signal.session_id, signal.analysis_run_id, signal.revision)
        for e in signal.evidence
    ):
        raise ContractError("EVIDENCE_UNAVAILABLE")
    dependency = hashed(signal.model_dump(mode="json", exclude={"as_of_ms"}))
    if previous is not None and dependency == previous.dependency_hash:
        return previous
    version = previous.version + 1 if previous else 1
    return AlertRevision(
        session_id=signal.session_id,
        analysis_run_id=signal.analysis_run_id,
        revision=signal.revision,
        id=signal.id,
        revision_id=uuid5(signal.id, f"{version}:{dependency}"),
        previous_revision_id=previous.revision_id if previous else None,
        version=version,
        origin="DETERMINISTIC",
        status="CLEARED" if signal.status == "INACTIVE" else signal.status,
        priority=signal.priority,
        source_severity=None,
        source_event=None,
        rule_id=signal.rule_id,
        rule_version=signal.rule_version,
        config_hash=signal.config_hash,
        dependency_hash=dependency,
        entity_ids=signal.entity_ids,
        evidence=signal.evidence,
        as_of_ms=signal.as_of_ms,
        available_time_ms=signal.available_time_ms,
        statement=signal.statement,
        reason=signal.reason,
        exit_unknown=signal.exit_unknown,
    )


def reduce_source(
    previous: AlertRevision | None, ctx: RequestContext, event: SourceEvent, anchor: Evidence
) -> AlertRevision:
    event = SourceEvent.model_validate_json(event.model_dump_json())
    body = decode(event)
    if not isinstance(body, SourceAlert):
        raise ContractError("INVALID_INPUT")
    if (event.session_id, event.revision, event.analysis_run_id) != (
        ctx.session_id,
        ctx.input_revision,
        None,
    ) or (
        anchor.session_id,
        anchor.analysis_run_id,
        anchor.revision,
        anchor.segment_id,
        anchor.source_id,
        anchor.source_hash,
        anchor.kind,
    ) != (
        ctx.session_id,
        ctx.analysis_run_id,
        ctx.input_revision,
        event.id,
        event.source_id,
        event.source_hash,
        "EVENT",
    ):
        raise ContractError("EVIDENCE_UNAVAILABLE")
    if (
        event.event_time_ms > ctx.as_of_ms
        or ctx.mode == "AS_KNOWN"
        and (event.available_time_ms is None or event.available_time_ms > ctx.as_of_ms)
    ):
        raise ContractError("EVIDENCE_UNAVAILABLE")
    identifier = uuid5(
        event.source_id, f"source-alert:{ctx.analysis_run_id}:{ctx.input_revision}:{body.alert_key}"
    )
    _check(
        previous,
        identifier=identifier,
        session=ctx.session_id,
        run=ctx.analysis_run_id,
        revision=ctx.input_revision,
        time=ctx.as_of_ms,
        origin="SOURCE",
    )
    dependency = hashed(
        {"source_event": event.model_dump(mode="json"), "anchor": anchor.model_dump(mode="json")}
    )
    if previous is not None and dependency == previous.dependency_hash:
        return previous
    version = previous.version + 1 if previous else 1
    return AlertRevision(
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        id=identifier,
        revision_id=uuid5(identifier, f"{version}:{dependency}"),
        previous_revision_id=previous.revision_id if previous else None,
        version=version,
        origin="SOURCE",
        status=body.status,
        priority=None,
        source_severity=body.severity,
        source_event=event,
        rule_id=None,
        rule_version=body.profile_version,
        config_hash=hashed({"codec": body.profile_version, "source_hash": event.source_hash}),
        dependency_hash=dependency,
        entity_ids=[event.entity_id] if event.entity_id else [],
        evidence=[anchor],
        as_of_ms=ctx.as_of_ms,
        available_time_ms=event.available_time_ms,
        statement="External source alert; authority and severity remain with the source record.",
        reason="SOURCE_RECORD",
        exit_unknown=False,
    )


def seen(ctx: RequestContext, alert: AlertRevision) -> Acknowledgement:
    if (alert.session_id, alert.analysis_run_id, alert.revision) != (
        ctx.session_id,
        ctx.analysis_run_id,
        ctx.input_revision,
    ) or alert.as_of_ms > ctx.as_of_ms:
        raise ContractError("ACCESS_DENIED")
    return Acknowledgement(
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        id=uuid5(alert.revision_id, "seen:" + str(ctx.actor_id)),
        alert_id=alert.id,
        alert_revision_id=alert.revision_id,
        actor_id=ctx.actor_id,
        as_of_ms=ctx.as_of_ms,
    )


def reduce_source_group(
    previous: AlertRevision | None,
    ctx: RequestContext,
    events: list[SourceEvent],
    anchors: dict[UUID, Evidence],
) -> AlertRevision:
    """No source ordering is invented between contradictory simultaneous records."""
    if not events:
        raise ContractError("INVALID_INPUT")
    events = sorted(events, key=lambda event: str(event.id))
    checked = [reduce_source(None, ctx, event, anchors[event.id]) for event in events]
    if (
        len({alert.id for alert in checked}) != 1
        or len({event.event_time_ms for event in events}) != 1
    ):
        raise ContractError("INVALID_INPUT")
    if len(events) == 1:
        return reduce_source(previous, ctx, events[0], anchors[events[0].id])
    dependency = hashed({"simultaneous": [alert.dependency_hash for alert in checked]})
    template = reduce_source(previous, ctx, events[0], anchors[events[0].id])
    if previous is not None and previous.dependency_hash == dependency:
        return previous
    version = previous.version + 1 if previous else 1
    conflict = len({(alert.status, alert.source_severity) for alert in checked}) > 1
    return template.model_copy(
        update={
            "version": version,
            "revision_id": uuid5(template.id, f"{version}:{dependency}"),
            "previous_revision_id": previous.revision_id if previous else None,
            "dependency_hash": dependency,
            "source_variants": events,
            "evidence": [anchors[event.id] for event in events],
            "status": "UNKNOWN" if conflict else template.status,
            "source_event": None if conflict else events[0],
            "source_severity": None if conflict else template.source_severity,
            "reason": "SOURCE_ALERT_CONFLICT" if conflict else "DUPLICATE_SOURCE_RECORDS",
        }
    )
