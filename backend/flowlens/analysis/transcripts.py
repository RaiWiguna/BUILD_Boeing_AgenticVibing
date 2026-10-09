"""Append-only transcript lifecycle. Caller owns authority, UOW, commit and publication."""

import base64
import hashlib
import json
from collections.abc import Callable
from typing import cast
from uuid import UUID, uuid4

from flowlens.analysis.repository import scope
from flowlens.analysis.transcript_projection import CanonicalWord, deduplicate, project
from flowlens.analysis.transcript_records import (
    RawTranscript,
    TranscriptAudioLink,
    TranscriptChange,
    TranscriptDependency,
    TranscriptNotice,
    TranscriptRevision,
)
from flowlens.analysis.transcript_store import (
    RECORDS,
    TRANSCRIPT_MIGRATIONS,
    TranscriptRepository,
    factory,
)
from flowlens.contracts.models import Evidence, RequestContext, TranscriptSegment
from flowlens.contracts.ports import EvidenceService, TransactionFactory, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistration

RAW = "analysis.transcript.raw"
REVISION = "analysis.transcript.revision"
DEPENDENCY = "analysis.transcript.dependency"
CHANGE = "analysis.transcript.change"
Authority = Callable[[RequestContext, RawTranscript, UnitOfWork], None]


def repo(uow: UnitOfWork, namespace: str) -> TranscriptRepository:
    return cast(TranscriptRepository, uow.repository(namespace))


class TranscriptLifecycle:
    def __init__(self, evidence: EvidenceService, authority: Authority) -> None:
        self.evidence, self.authority = evidence, authority

    def notice(
        self, context: RequestContext, uow: UnitOfWork, identifier: UUID, action: str
    ) -> None:
        notice = TranscriptNotice.model_validate(
            {
                "id": identifier,
                "session_id": context.session_id,
                "analysis_run_id": context.analysis_run_id,
                "revision": context.input_revision,
                "action": action,
            }
        )
        uow.audit(context, action, identifier)
        uow.enqueue_event(context, notice)

    def store_raw(self, context: RequestContext, raw: RawTranscript, uow: UnitOfWork) -> UUID:
        context.require("analysis", raw.session_id, raw.analysis_run_id)
        raw = RawTranscript.model_validate_json(raw.model_dump_json())
        if (str(raw.session_id), str(raw.analysis_run_id), raw.revision) != scope(context):
            raise ContractError("ACCESS_DENIED")
        if raw.input_hash != context.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        # Platform checks active job/lease, cancellation, config/artifact binding and
        # provider-response validation inside this same transaction, even on replay.
        self.authority(context, raw, uow)
        try:
            payload = base64.b64decode(raw.response_base64, validate=True)
        except ValueError:
            raise ContractError("INVALID_AI_OUTPUT") from None
        if (
            hashlib.sha256(payload).hexdigest() != raw.response_hash
            or hashlib.sha256(raw.config_json.encode()).hexdigest() != raw.config_hash
        ):
            raise ContractError("INVALID_AI_OUTPUT")
        try:
            existing = repo(uow, RAW).get(context, raw.id)
        except ContractError as exc:
            if exc.code != "EVIDENCE_UNAVAILABLE":
                raise
        else:
            if existing != raw:
                raise ContractError("VERSION_CONFLICT")
            return raw.id
        repo(uow, RAW).append(context, raw)
        self.notice(context, uow, raw.id, "RAW_STORED")
        return raw.id

    def add_original(
        self, context: RequestContext, raw_id: UUID, segment: TranscriptSegment, uow: UnitOfWork
    ) -> UUID:
        raw = repo(uow, RAW).get(context, raw_id)
        if not isinstance(raw, RawTranscript):
            raise ContractError("INVALID_INPUT")
        self.authority(context, raw, uow)
        segment = TranscriptSegment.model_validate_json(segment.model_dump_json())
        if segment.origin not in ("MOCK", "GOOGLE_STT") or segment not in project(
            raw, recorded_at=segment.recorded_at, origin=segment.origin
        ):
            raise ContractError("INVALID_AI_OUTPUT")
        record = TranscriptRevision(
            id=segment.id,
            session_id=raw.session_id,
            analysis_run_id=raw.analysis_run_id,
            revision=raw.revision,
            input_hash=raw.input_hash,
            raw_id=raw.id,
            original_id=segment.id,
            previous_id=None,
            correction_revision=0,
            actor_id=context.actor_id,
            segment=segment,
        )
        try:
            old = repo(uow, REVISION).get(context, record.id)
        except ContractError as exc:
            if exc.code != "EVIDENCE_UNAVAILABLE":
                raise
        else:
            if old != record:
                raise ContractError("VERSION_CONFLICT")
            return record.id
        repo(uow, REVISION).append(context, record)
        for evidence in segment.evidence:
            self.validate_evidence(context, evidence, uow)
            self.evidence.register(context, evidence, uow)
        self.notice(context, uow, segment.id, "TRANSCRIPT_ADDED")
        return segment.id

    def revision(
        self, context: RequestContext, identifier: UUID, uow: UnitOfWork
    ) -> TranscriptRevision:
        result = repo(uow, REVISION).get(context, identifier)
        if not isinstance(result, TranscriptRevision):
            raise ContractError("INVALID_INPUT")
        return result

    def current_segments(
        self, context: RequestContext, uow: UnitOfWork
    ) -> tuple[TranscriptSegment, ...]:
        current: dict[UUID, TranscriptRevision] = {}
        for record in repo(uow, REVISION).inventory(context):
            if isinstance(record, TranscriptRevision):
                old = current.get(record.original_id)
                if old is None or record.correction_revision > old.correction_revision:
                    current[record.original_id] = record
        return tuple(
            sorted((r.segment for r in current.values()), key=lambda s: (s.start_ms, str(s.id)))
        )

    def canonical_provider_words(
        self, context: RequestContext, uow: UnitOfWork
    ) -> tuple[CanonicalWord, ...]:
        return deduplicate(
            tuple(r for r in repo(uow, RAW).inventory(context) if isinstance(r, RawTranscript))
        )

    def validate_evidence(
        self, context: RequestContext, evidence: Evidence, uow: UnitOfWork
    ) -> Evidence:
        evidence = Evidence.model_validate_json(evidence.model_dump_json())
        if (str(evidence.session_id), str(evidence.analysis_run_id), evidence.revision) != scope(
            context
        ):
            raise ContractError("ACCESS_DENIED")
        if evidence.segment_id is None or evidence.kind not in ("TRANSCRIPT", "AUDIO"):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if evidence.kind == "AUDIO":
            context.require("audio", context.session_id, context.analysis_run_id)
        record = self.revision(context, evidence.segment_id, uow)
        segment = record.segment
        raw = repo(uow, RAW).get(context, record.raw_id)
        if not isinstance(raw, RawTranscript) or raw.session_range is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (
            evidence.source_id != raw.source_id
            or evidence.source_hash != raw.source_hash
            or evidence.start_ms is None
            or evidence.end_ms is None
            or evidence.start_ms < segment.start_ms
            or evidence.end_ms > segment.end_ms
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if evidence.kind == "TRANSCRIPT" and (
            evidence.span_start is None
            or evidence.span_end is None
            or evidence.span_end > len(segment.text)
            or segment.text[evidence.span_start : evidence.span_end] != evidence.quote
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if evidence.kind == "AUDIO" and (
            evidence.quote is not None
            or evidence.span_start is not None
            or evidence.span_end is not None
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        return evidence

    def resolve_audio(
        self, context: RequestContext, segment_id: UUID, uow: UnitOfWork
    ) -> TranscriptAudioLink:
        context.require("audio", context.session_id, context.analysis_run_id)
        record = self.revision(context, segment_id, uow)
        raw = repo(uow, RAW).get(context, record.raw_id)
        if not isinstance(raw, RawTranscript):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        metadata = json.loads(raw.preparation_json)
        return TranscriptAudioLink(
            raw_id=raw.id,
            segment_id=segment_id,
            source_id=raw.source_id,
            source_asset_id=UUID(metadata["asset_id"]),
            chunk_id=raw.chunk_id,
            source_hash=raw.source_hash,
            chunk_hash=raw.chunk_hash,
            channel=raw.channel,
            chunk_source_range=raw.source_range,
            chunk_session_range=raw.session_range,
            uncertainty_ms=raw.uncertainty_ms,
        )

    def correct(
        self,
        context: RequestContext,
        previous_id: UUID,
        segment: TranscriptSegment,
        uow: UnitOfWork,
    ) -> UUID:
        context.require("review", context.session_id, context.analysis_run_id)
        context.require("analysis", context.session_id, context.analysis_run_id)
        segment = TranscriptSegment.model_validate_json(segment.model_dump_json())
        previous = self.revision(context, previous_id, uow)
        siblings = [
            r
            for r in repo(uow, REVISION).inventory(context)
            if isinstance(r, TranscriptRevision) and r.original_id == previous.original_id
        ]
        if max(r.correction_revision for r in siblings) != previous.correction_revision:
            raise ContractError("VERSION_CONFLICT")
        # Text/attribution corrections retain observed audio timing, source and availability.
        immutable = (
            "session_id",
            "analysis_run_id",
            "revision",
            "source_id",
            "start_ms",
            "end_ms",
            "channel",
            "event_time_ms",
            "available_time_ms",
            "provider_profile_version",
        )
        if (
            any(getattr(segment, f) != getattr(previous.segment, f) for f in immutable)
            or segment.supersedes_id != previous_id
            or segment.origin != "HUMAN_CORRECTION"
            or segment.reason is None
            or not segment.reason.strip()
            or len(segment.reason) > 4096
            or segment.recorded_at < previous.segment.recorded_at
            or segment.confidence is not None
            or segment.quality != "AMBIGUOUS"
        ):
            raise ContractError("INVALID_INPUT")
        record = TranscriptRevision(
            id=segment.id,
            session_id=context.session_id,
            analysis_run_id=previous.analysis_run_id,
            revision=context.input_revision,
            input_hash=context.input_hash,
            raw_id=previous.raw_id,
            original_id=previous.original_id,
            previous_id=previous_id,
            correction_revision=previous.correction_revision + 1,
            actor_id=context.actor_id,
            segment=segment,
        )
        repo(uow, REVISION).append(context, record)
        for evidence in segment.evidence:
            self.validate_evidence(context, evidence, uow)
            self.evidence.register(context, evidence, uow)
        change = TranscriptChange(
            id=uuid4(),
            session_id=context.session_id,
            analysis_run_id=previous.analysis_run_id,
            revision=context.input_revision,
            input_hash=context.input_hash,
            original_id=previous.original_id,
            replacement_id=segment.id,
            reason="CORRECTION",
        )
        repo(uow, CHANGE).append(context, change)
        self.notice(context, uow, segment.id, "CORRECTION")
        return segment.id

    def depend(
        self, context: RequestContext, dependency: TranscriptDependency, uow: UnitOfWork
    ) -> UUID:
        dependency = TranscriptDependency.model_validate_json(dependency.model_dump_json())
        for identifier in dependency.transcript_ids:
            self.revision(context, identifier, uow)
        return repo(uow, DEPENDENCY).append(context, dependency)

    def invalidate_for_reanalysis(
        self, context: RequestContext, transcript_id: UUID, uow: UnitOfWork
    ) -> UUID:
        context.require("analysis", context.session_id, context.analysis_run_id)
        original = self.revision(context, transcript_id, uow)
        change = TranscriptChange(
            id=uuid4(),
            session_id=context.session_id,
            analysis_run_id=original.analysis_run_id,
            revision=context.input_revision,
            input_hash=context.input_hash,
            original_id=original.original_id,
            replacement_id=None,
            reason="REANALYSIS",
        )
        repo(uow, CHANGE).append(context, change)
        self.notice(context, uow, change.id, "REANALYSIS")
        return change.id

    def stale(self, context: RequestContext, dependency_id: UUID, uow: UnitOfWork) -> bool:
        dependency = repo(uow, DEPENDENCY).get(context, dependency_id)
        if not isinstance(dependency, TranscriptDependency):
            raise ContractError("INVALID_INPUT")
        changes = [
            r for r in repo(uow, CHANGE).inventory(context) if isinstance(r, TranscriptChange)
        ]
        for identifier in dependency.transcript_ids:
            revision = self.revision(context, identifier, uow)
            chain = [
                r
                for r in repo(uow, REVISION).inventory(context)
                if isinstance(r, TranscriptRevision) and r.original_id == revision.original_id
            ]
            if any(
                c.original_id == revision.original_id and c.reason == "REANALYSIS" for c in changes
            ):
                return True
            if max(r.correction_revision for r in chain) > revision.correction_revision:
                return True
        return False

    def purge(self, context: RequestContext, uow: UnitOfWork) -> None:
        for namespace in reversed(RECORDS):
            repo(uow, namespace).purge(context)
        uow.audit(context, "TRANSCRIPT_PURGED", context.session_id)


def register_transcripts(
    transactions: TransactionFactory, evidence: EvidenceService, authority: Authority
) -> ModuleRegistration:
    """Separate registration: existing B01 entrypoint and migration digest stay unchanged."""
    service = TranscriptLifecycle(evidence, authority)
    return ModuleRegistration(
        name="analysis_transcripts",
        mock=getattr(transactions, "profile", None) == "MOCK",
        services={"transcript_lifecycle": service},
        repositories={n: factory(n) for n in RECORDS},
        migrations=TRANSCRIPT_MIGRATIONS,
        inventory_namespaces=tuple(RECORDS),
        purge_handler=service.purge,
        readiness=lambda: False,
    )
