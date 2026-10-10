"""Standalone acceptance; platform authority, source truth and commit stay with caller."""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from flowlens.association import associate
from flowlens.contracts.models import RequestContext, TranscriptSegment
from flowlens.contracts.ports import EvidenceService, TransactionFactory, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistration
from flowlens.intent.models import Candidate, Provenance
from flowlens.intent.validation import validate, visible
from flowlens.loops import reconstruct_loops
from flowlens.memory.models import NAMESPACE, AcceptedEvent, Invalidation
from flowlens.memory.reducer import reconstruct
from flowlens.memory.store import MEMORY_MIGRATIONS, MemoryRepository, SQLiteMemoryRepository


@dataclass(frozen=True)
class AcceptedInputs:
    segments: Mapping[UUID, TranscriptSegment]
    identities: Mapping[UUID, tuple[str, ...]]
    roles: Mapping[UUID, str]
    coverage_known: bool


class AcceptanceAccess(Protocol):
    def authoritative(
        self,
        context: RequestContext,
        candidate: Candidate,
        config_hash: str,
        uow: UnitOfWork,
        *,
        provenance: Provenance,
    ) -> AcceptedInputs:
        """Check active lease/attempt, cancellation, deadline, revision, rights and
        bound config and authenticated worker provenance/candidate binding inside
        caller UOW, INCLUDING duplicate submissions. Return
        authoritative current transcripts, identity aliases and channel coverage.
        Real composition must implement this; no permissive default exists.
        """
        ...


def repo(uow: UnitOfWork) -> MemoryRepository:
    return cast(MemoryRepository, uow.repository(NAMESPACE))


class MemoryService:
    def __init__(self, access: AcceptanceAccess, evidence: EvidenceService) -> None:
        self.access, self.evidence = access, evidence

    def accept(
        self,
        context: RequestContext,
        candidate: Candidate,
        *,
        config_hash: str,
        provenance: Provenance,
        recorded_at: datetime,
        uow: UnitOfWork,
    ) -> UUID:
        context.require("analysis", context.session_id, context.analysis_run_id)
        candidate = Candidate.model_validate_json(candidate.model_dump_json())
        provenance = Provenance.model_validate_json(provenance.model_dump_json())
        if provenance.config_hash != config_hash or provenance.input_hash != context.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        inputs = self.access.authoritative(
            context, candidate, config_hash, uow, provenance=provenance
        )
        segments = inputs.segments
        candidate = validate(context, candidate, segments, inputs.identities, self.evidence)
        if candidate.role != "UNKNOWN" and inputs.roles.get(candidate.segment_id) != candidate.role:
            raise ContractError("INVALID_AI_OUTPUT")
        try:
            old = repo(uow).get(context, candidate.id)
        except ContractError as exc:
            if exc.code != "EVIDENCE_UNAVAILABLE":
                raise
        else:
            if not isinstance(old, AcceptedEvent) or (
                old.candidate != candidate
                or old.config_hash != config_hash
                or old.provenance != provenance
            ):
                raise ContractError("IDEMPOTENCY_CONFLICT")
            return old.id
        inventory = repo(uow).inventory(context)
        previous = []
        for item in inventory:
            if isinstance(item, AcceptedEvent):
                try:
                    visible(context, item)
                except ContractError:
                    continue
                if item.candidate.segment_id in segments:
                    previous.append(item.candidate)
        link = (
            None
            if candidate.speech_act == "INSTRUCTION"
            else associate(candidate, previous, segments)
        )
        segment = segments[candidate.segment_id]
        event = AcceptedEvent(
            id=candidate.id,
            session_id=context.session_id,
            analysis_run_id=context.analysis_run_id,
            revision=context.input_revision,
            input_hash=context.input_hash,
            config_hash=config_hash,
            provenance=provenance,
            candidate=candidate,
            link=link,
            event_time_ms=segment.event_time_ms,
            available_time_ms=segment.available_time_ms,
            recorded_at=recorded_at,
            coverage_known=inputs.coverage_known,
            dependency_hashes=(hashlib.sha256(segment.model_dump_json().encode()).hexdigest(),),
        )
        repo(uow).append(context, event)
        for ev in candidate.evidence:
            self.evidence.register(context, ev, uow)
        uow.audit(context, "INTENT_MEMORY_ACCEPTED", event.id)
        uow.enqueue_event(context, event)
        return event.id

    def invalidate(self, context: RequestContext, event: Invalidation, uow: UnitOfWork) -> UUID:
        context.require("review", context.session_id, context.analysis_run_id)
        event = Invalidation.model_validate_json(event.model_dump_json())
        visible(context, event)
        for target in event.targets:
            repo(uow).get(context, target)
        repo(uow).append(context, event)
        uow.audit(context, "MEMORY_INVALIDATED", event.id)
        uow.enqueue_event(context, event)
        return event.id

    def purge(self, context: RequestContext, uow: UnitOfWork) -> None:
        repo(uow).purge(context)
        uow.audit(context, "INTENT_MEMORY_PURGED", context.session_id)

    def stale(self, context: RequestContext, uow: UnitOfWork) -> tuple[UUID, ...]:
        events = repo(uow).inventory(context)
        included = []
        for event in events:
            try:
                visible(context, event)
            except ContractError:
                continue
            included.append(event)
        stale = {target for e in included if isinstance(e, Invalidation) for target in e.targets}
        accepted = [e for e in included if isinstance(e, AcceptedEvent)]
        stale.update(
            e.link.target_id
            for e in accepted
            if e.link
            and e.link.target_id is not None
            and e.link.relationship == "CORRECTION_OF"
            and e.link.status == "SUPPORTED"
        )
        changed = True
        while changed:
            changed = False
            for event in accepted:
                if event.link and event.link.target_id in stale and event.id not in stale:
                    # The correction is the replacement, not an invalid dependent.
                    if event.link.relationship == "CORRECTION_OF":
                        continue
                    stale.add(event.id)
                    changed = True
        return tuple(sorted(stale, key=str))


def register_memory(
    transactions: TransactionFactory,
    access: AcceptanceAccess,
    evidence: EvidenceService,
) -> ModuleRegistration:
    service = MemoryService(access, evidence)

    def inventory(context: RequestContext) -> tuple[AcceptedEvent | Invalidation, ...]:
        with transactions.begin() as uow:
            return repo(uow).inventory(context)

    return ModuleRegistration(
        name="intent_memory",
        mock=getattr(transactions, "profile", None) == "MOCK",
        services={
            "intent_memory": service,
            "intent_memory_inventory": inventory,
            "memory_reconstruct": reconstruct,
            "loop_reconstruct": reconstruct_loops,
        },
        repositories={NAMESPACE: SQLiteMemoryRepository},
        migrations=MEMORY_MIGRATIONS,
        purge_handler=service.purge,
        readiness=lambda: False,
        inventory_namespaces=(NAMESPACE,),
    )
