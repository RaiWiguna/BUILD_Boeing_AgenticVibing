"""API-side standalone acceptance. Caller owns the UOW and final job transition."""

import time
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from flowlens.analysis.transcript_projection import project
from flowlens.analysis.transcript_records import RawTranscript
from flowlens.analysis.transcripts import TranscriptLifecycle
from flowlens.contracts.models import ArtifactSubmission, RequestContext
from flowlens.contracts.ports import EvidenceService, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.providers.stt.models import AuthorizedChunk, STTConfig, STTFailure
from flowlens.providers.stt.provenance import MAX_PROVENANCE_BYTES, decode, validate_raw


class AcceptanceAccess(Protocol):
    def staged(
        self, context: RequestContext, artifact_id: UUID, uow: UnitOfWork
    ) -> tuple[ArtifactSubmission, bytes]:
        """Load bounded immutable staged bytes after scope/owner/capability checks."""
        ...

    def authoritative(
        self, context: RequestContext, raw: RawTranscript, uow: UnitOfWork
    ) -> tuple[AuthorizedChunk, bytes]:
        """Check active job/attempt/lease, input revision, rights and config in UOW.

        Return server-owned binding/audio. Replays must pass these checks too.
        Check cancellation/revocation on every call; never trust candidate metadata.
        """
        ...


class PrivateTranscriptIngest:
    def __init__(
        self, config: STTConfig, access: AcceptanceAccess, evidence: EvidenceService
    ) -> None:
        self.config, self.access = config, access
        self.lifecycle = TranscriptLifecycle(evidence, self.authority)

    def authority(self, context: RequestContext, raw: RawTranscript, uow: UnitOfWork) -> None:
        binding, audio = self.access.authoritative(context, raw, uow)
        now = time.time_ns() // 1_000_000
        if now >= min(binding.lease.expires_ms, binding.lease.deadline_ms):
            raise ContractError("LEASE_EXPIRED")
        if (
            context.session_id,
            context.analysis_run_id,
            context.input_revision,
            context.input_hash,
        ) != (
            binding.context.session_id,
            binding.context.analysis_run_id,
            binding.context.input_revision,
            binding.context.input_hash,
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        try:
            validate_raw(self.config, binding, audio, raw)
        except STTFailure:
            raise ContractError("INVALID_AI_OUTPUT") from None

    def accept(
        self,
        context: RequestContext,
        artifact_id: UUID,
        recorded_at: datetime,
        origin: Literal["GOOGLE_STT", "MOCK"],
        uow: UnitOfWork,
    ) -> UUID:
        context.require("analysis", context.session_id, context.analysis_run_id)
        context.require("audio", context.session_id, context.analysis_run_id)
        artifact, payload = self.access.staged(context, artifact_id, uow)
        # Bounded canonical decoder below verifies staged hash and every manifest field.
        if (
            type(payload) is not bytes
            or len(payload) > MAX_PROVENANCE_BYTES
            or artifact.id != artifact_id
        ):
            raise ContractError("INVALID_AI_OUTPUT")
        try:
            raw = RawTranscript.model_validate_json(payload)
        except ValueError:
            raise ContractError("INVALID_AI_OUTPUT") from None
        self.authority(context, raw, uow)
        binding, audio = self.access.authoritative(context, raw, uow)
        try:
            raw = decode(self.config, binding, audio, artifact, payload)
        except STTFailure:
            raise ContractError("INVALID_AI_OUTPUT") from None
        self.lifecycle.store_raw(context, raw, uow)
        for segment in project(raw, recorded_at=recorded_at, origin=origin):
            # Preserve the original API receipt time on exact replay.
            try:
                existing = self.lifecycle.revision(context, segment.id, uow)
            except ContractError as exc:
                if exc.code != "EVIDENCE_UNAVAILABLE":
                    raise
                self.lifecycle.add_original(context, raw.id, segment, uow)
            else:
                if (
                    existing.raw_id != raw.id
                    or existing.correction_revision != 0
                    or existing.segment
                    not in project(raw, recorded_at=existing.segment.recorded_at, origin=origin)
                ):
                    raise ContractError("VERSION_CONFLICT")
        return raw.id
