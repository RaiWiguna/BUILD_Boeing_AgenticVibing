"""API-side transcript-to-memory lifecycle binding, with caller-owned UOW.

No provider SDK, platform internals or job handler. Reanalysis remains explicit.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid5

from flowlens.analysis.transcript_records import TranscriptDependency
from flowlens.analysis.transcripts import TranscriptLifecycle
from flowlens.contracts.models import RequestContext
from flowlens.contracts.ports import UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.intent.models import Candidate, Provenance
from flowlens.memory.models import AcceptedEvent, Invalidation
from flowlens.memory.service import MemoryService, repo


class TranscriptMemoryBinding:
    def __init__(self, transcripts: TranscriptLifecycle, memory: MemoryService) -> None:
        self.transcripts, self.memory = transcripts, memory

    def accept(
        self,
        context: RequestContext,
        candidate: Candidate,
        provenance: Provenance,
        recorded_at: datetime,
        uow: UnitOfWork,
    ) -> UUID:
        if context.analysis_run_id is None:
            raise ContractError("INVALID_INPUT")
        current = {s.id for s in self.transcripts.current_segments(context, uow)}
        if candidate.segment_id not in current:
            raise ContractError("SOURCE_REVISION_CHANGED")
        for evidence in candidate.evidence:
            self.transcripts.validate_evidence(context, evidence, uow)
        identifier = self.memory.accept(
            context,
            candidate,
            config_hash=provenance.config_hash,
            provenance=provenance,
            recorded_at=recorded_at,
            uow=uow,
        )
        # Replay still goes through MemoryService authority. Dependency IDs are
        # stable and refer to the exact transcript revision, not the latest text.
        dependency = TranscriptDependency(
            id=uuid5(identifier, "transcript-dependency"),
            session_id=context.session_id,
            analysis_run_id=context.analysis_run_id,
            revision=context.input_revision,
            input_hash=context.input_hash,
            transcript_ids=(candidate.segment_id,),
            kind="MEMORY",
        )
        from flowlens.analysis.transcripts import DEPENDENCY
        from flowlens.analysis.transcripts import repo as transcript_repo

        try:
            old = transcript_repo(uow, DEPENDENCY).get(context, dependency.id)
        except ContractError as exc:
            if exc.code != "EVIDENCE_UNAVAILABLE":
                raise
            self.transcripts.depend(context, dependency, uow)
        else:
            if old != dependency:
                raise ContractError("VERSION_CONFLICT")
        return identifier

    def invalidate_changes(
        self,
        context: RequestContext,
        *,
        recorded_at: datetime,
        reason: Literal["CORRECTION", "REANALYSIS"],
        uow: UnitOfWork,
        event_time_ms: int,
        available_time_ms: int | None,
    ) -> UUID | None:
        targets = tuple(
            event.id
            for event in repo(uow).inventory(context)
            if isinstance(event, AcceptedEvent)
            and self.transcripts.stale(context, uuid5(event.id, "transcript-dependency"), uow)
        )
        if not targets:
            return None
        event = Invalidation(
            id=uuid5(context.request_id, "invalidate:" + ":".join(map(str, targets))),
            session_id=context.session_id,
            analysis_run_id=context.analysis_run_id,
            revision=context.input_revision,
            input_hash=context.input_hash,
            event_time_ms=event_time_ms,
            available_time_ms=available_time_ms,
            recorded_at=recorded_at,
            targets=targets,
            reason=reason,
        )
        try:
            old = repo(uow).get(context, event.id)
        except ContractError as exc:
            if exc.code != "EVIDENCE_UNAVAILABLE":
                raise
        else:
            if old != event:
                raise ContractError("VERSION_CONFLICT")
            return old.id
        return self.memory.invalidate(context, event, uow)
