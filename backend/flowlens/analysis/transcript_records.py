"""Private immutable transcript records; not additions to frozen wire contracts."""

from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from flowlens.contracts.models import Contract, TranscriptSegment


class Offset(Contract):
    start_ns: int = Field(ge=0)
    end_ns: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_ns <= self.start_ns:
            raise ValueError("Invalid offset.")
        return self


class Word(Contract):
    text: str = Field(min_length=1, max_length=4096, repr=False)
    local: Offset | None
    source: Offset | None
    session: Offset | None
    confidence: float | None = Field(ge=0, le=1)


class Hypothesis(Contract):
    result_index: int = Field(ge=0)
    alternative_index: int = Field(ge=0)
    text: str = Field(max_length=65536, repr=False)
    language: str = Field(max_length=64)
    confidence: float | None = Field(ge=0, le=1)
    end_ns: int | None = Field(default=None, ge=0)
    words: tuple[Word, ...] = Field(max_length=8192, repr=False)


class RawTranscript(Contract):
    id: UUID
    session_id: UUID
    analysis_run_id: UUID
    revision: int = Field(gt=0)
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    job_id: UUID
    attempt_id: UUID
    lease_id: UUID
    source_id: UUID
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    chunk_id: UUID
    chunk_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    channel: int = Field(ge=0, le=1)
    coverage_segment: int = Field(ge=0)
    source_range: Offset
    session_range: Offset | None
    uncertainty_ms: int | None = Field(ge=0)
    profile_version: Literal["stt-v2-1"] = "stt-v2-1"
    sdk_version: str
    config_json: str = Field(max_length=8192, repr=False)
    preparation_json: str = Field(max_length=524288, repr=False)
    # Exact serialized SDK response, base64 for private persistence. Never diagnostics/export.
    response_base64: str = Field(max_length=1398104, repr=False)
    response_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    hypotheses: tuple[Hypothesis, ...] = Field(max_length=256, repr=False)
    status: Literal["COMPLETE", "NO_SPEECH", "PARTIAL"]
    billed_ns: int | None = Field(ge=0)


class TranscriptRevision(Contract):
    id: UUID
    session_id: UUID
    analysis_run_id: UUID
    revision: int = Field(gt=0)
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_id: UUID
    original_id: UUID
    previous_id: UUID | None
    correction_revision: int = Field(ge=0)
    actor_id: UUID
    segment: TranscriptSegment = Field(repr=False)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.segment.id,
            self.segment.session_id,
            self.segment.analysis_run_id,
            self.segment.revision,
        ) != (self.id, self.session_id, self.analysis_run_id, self.revision):
            raise ValueError("Revision scope mismatch.")
        if self.correction_revision == 0:
            if self.previous_id is not None or self.original_id != self.id:
                raise ValueError("Invalid original revision.")
            if self.segment.origin not in ("GOOGLE_STT", "MOCK"):
                raise ValueError("Original requires provider provenance.")
        elif self.previous_id is None or self.segment.supersedes_id != self.previous_id:
            raise ValueError("Invalid correction chain.")
        elif self.segment.origin != "HUMAN_CORRECTION":
            raise ValueError("Correction requires human provenance.")
        return self


class TranscriptDependency(Contract):
    id: UUID
    session_id: UUID
    analysis_run_id: UUID
    revision: int = Field(gt=0)
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    transcript_ids: tuple[UUID, ...] = Field(min_length=1, max_length=4096)
    kind: Literal["INTENT", "ASSOCIATION", "MEMORY", "FINDING", "BRIEF"]


class TranscriptChange(Contract):
    id: UUID
    session_id: UUID
    analysis_run_id: UUID
    revision: int = Field(gt=0)
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    original_id: UUID
    replacement_id: UUID | None
    reason: Literal["CORRECTION", "REANALYSIS"]


class TranscriptNotice(Contract):
    """Safe internal ledger metadata. Publication remains platform-owned."""

    id: UUID
    session_id: UUID
    analysis_run_id: UUID
    revision: int
    action: Literal["RAW_STORED", "TRANSCRIPT_ADDED", "CORRECTION", "REANALYSIS"]


class TranscriptAudioLink(Contract):
    raw_id: UUID
    segment_id: UUID
    source_id: UUID
    source_asset_id: UUID
    chunk_id: UUID
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    chunk_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    channel: int = Field(ge=0, le=1)
    chunk_source_range: Offset
    chunk_session_range: Offset | None
    uncertainty_ms: int | None = Field(ge=0)
