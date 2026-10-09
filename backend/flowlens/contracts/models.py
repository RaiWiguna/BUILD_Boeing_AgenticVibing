"""Provider-independent, strict, versioned domain/wire contracts.

UUID/datetime are parsed at JSON boundaries; Python construction requires native values.
"""

from datetime import datetime, timedelta
from typing import Annotated, Literal, Self
from uuid import UUID

from flowlens.core.errors import ContractError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Id = UUID
Ms = Annotated[int, Field(ge=0)]
Revision = Annotated[int, Field(ge=1)]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Number = Annotated[float, Field(allow_inf_nan=False)]
Quality = Literal["SUPPORTED", "AMBIGUOUS", "MISSING", "CONFLICTING"]
Mode = Literal["AS_KNOWN", "DEBRIEF"]
Capability = Literal["read", "audio", "review", "export", "truth", "analysis", "admin", "worker"]
SpeechAct = Literal[
    "REQUEST",
    "INSTRUCTION",
    "READBACK",
    "REPORT",
    "CORRECTION",
    "CANCELLATION",
    "COORDINATION",
    "HANDOFF",
    "INFORMATION",
    "UNKNOWN",
]
Action = Literal[
    "HOLD_SHORT",
    "CROSS_RUNWAY",
    "LINE_UP_WAIT",
    "TAKEOFF",
    "LAND",
    "TAXI",
    "VACATE",
    "CONTACT",
    "REPORT",
    "UNKNOWN",
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal["1.0.0"] = "1.0.0"


class RequestContext(Contract):
    actor_id: Id
    capabilities: list[Capability]
    session_id: Id
    analysis_run_id: Id | None
    input_revision: Revision
    input_hash: Hash
    as_of_ms: Ms
    mode: Mode
    request_id: Id

    def require(self, capability: Capability, session_id: Id, run_id: Id | None = None) -> None:
        if capability not in self.capabilities or session_id != self.session_id:
            raise ContractError("ACCESS_DENIED")
        if run_id is not None and run_id != self.analysis_run_id:
            raise ContractError("ACCESS_DENIED")


class ClockMapping(Contract):
    offset_ms: int | None
    uncertainty_ms: Ms | None
    timezone: Text
    mapping_version: Text = "clock-1"

    @model_validator(mode="after")
    def paired_alignment(self) -> Self:
        if (self.offset_ms is None) != (self.uncertainty_ms is None):
            raise ValueError("alignment and uncertainty must both be known or unknown")
        return self

    def to_session_ms(self, source_ms: Ms) -> int | None:
        if source_ms < 0:
            raise ValueError("negative source time")
        return None if self.offset_ms is None else source_ms + self.offset_ms


class Permissions(Contract):
    local: bool
    cloud: bool
    export: bool
    audio_export: bool
    basis: Text
    retention_days: Annotated[int, Field(ge=1)]


class Coverage(Contract):
    audio: bool
    tracks: bool
    vehicles: bool | None
    speaker_identity: bool | None
    quality: Quality
    gaps: list["TimeRange"] = []


class TimeRange(Contract):
    start_ms: Ms
    end_ms: Ms

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_ms <= self.start_ms:
            raise ValueError("range must have positive length")
        return self


class Asset(Contract):
    id: Id
    sha256: Hash
    duration_ms: Ms
    channels: Annotated[int, Field(ge=1, le=2)]
    sample_rate_hz: Annotated[int, Field(ge=8000, le=192000)]
    media_type: Literal["audio/wav", "audio/flac", "audio/mpeg", "audio/aiff"]
    # Fixture path is test-package metadata, never a private filesystem storage key.
    fixture_path: Annotated[str, Field(pattern=r"^tests/fixtures/audio/[A-Za-z0-9_.-]+$")] | None


class SourceManifest(Contract):
    id: Id
    session_id: Id
    source_kind: Literal["SYNTHETIC", "ROLEPLAY", "PUBLIC_CORPUS", "PARTNER_REPLAY"]
    source_label: Text
    source_hash: Hash
    revision: Revision
    permissions: Permissions
    clock: ClockMapping
    coverage: Coverage
    units: Literal["m"]
    coordinate_system: Text
    layout_version: Text | None
    assets: list[Asset]
    domain_validation: Literal["NOT_DOMAIN_VALIDATED", "DOMAIN_REVIEWED"]


class Scoped(Contract):
    session_id: Id
    analysis_run_id: Id | None
    revision: Revision


class Timed(Scoped):
    event_time_ms: Ms
    available_time_ms: Ms | None
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("recorded_at must be UTC RFC3339")
        return value


class Evidence(Scoped):
    id: Id
    kind: Literal["AUDIO", "TRANSCRIPT", "EVENT", "TRACK", "POLICY"]
    source_id: Id
    segment_id: Id | None
    start_ms: Ms | None
    end_ms: Ms | None
    quote: Text | None
    span_start: Ms | None
    span_end: Ms | None
    source_hash: Hash

    @model_validator(mode="after")
    def ranges(self) -> Self:
        for start, end in ((self.start_ms, self.end_ms), (self.span_start, self.span_end)):
            if (start is None) != (end is None) or (
                start is not None and end is not None and end <= start
            ):
                raise ValueError("paired, positive ranges required")
        if self.kind in ("AUDIO", "TRANSCRIPT") and self.start_ms is None:
            raise ValueError("audio/transcript requires a time range")
        if self.kind == "TRANSCRIPT" and (self.segment_id is None or self.span_start is None):
            raise ValueError("transcript requires segment and character span")
        return self


class Evidenced(Timed):
    evidence: Annotated[list[Evidence], Field(min_length=1)]

    @model_validator(mode="after")
    def same_scope(self) -> Self:
        for item in self.evidence:
            if (
                item.session_id != self.session_id
                or item.analysis_run_id != self.analysis_run_id
                or item.revision != self.revision
            ):
                raise ValueError("cross-session/run/revision evidence")
        return self


class SourceEvent(Timed):
    id: Id
    source_id: Id
    source_event_id: Text
    kind: Literal["INSTRUCTION", "TRACK", "ALERT", "QUALITY", "REPORT"]
    entity_id: Id | None
    source_hash: Hash
    quality: Quality
    statement: Text


class Track(SourceEvent):
    kind: Literal["TRACK"] = "TRACK"
    x_m: Number
    y_m: Number
    heading_deg: Annotated[float, Field(ge=0, lt=360, allow_inf_nan=False)]
    speed_mps: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    length_m: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    width_m: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    age_ms: Ms
    layout_version: Text


class GeometryResult(Scoped):
    entity_id: Id
    status: Literal["EVALUATED", "NOT_EVALUABLE"]
    reason: Text | None
    occupied: bool | None
    intervals: list[TimeRange]
    uncertainty_ms: Ms | None
    rule_version: Text
    layout_version: Text | None
    evidence: list[Evidence]

    @model_validator(mode="after")
    def eligibility(self) -> Self:
        if self.status == "NOT_EVALUABLE" and (self.reason is None or self.occupied is not None):
            raise ValueError("ineligible geometry must preserve unknown occupancy and reason")
        if self.status == "EVALUATED" and (self.layout_version is None or not self.evidence):
            raise ValueError("evaluated geometry requires layout and evidence")
        return self


class TranscriptSegment(Evidenced):
    id: Id
    source_id: Id
    start_ms: Ms
    end_ms: Ms
    channel: Annotated[int, Field(ge=0, le=1)]
    text: Text
    speaker_id: Id | None
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None
    quality: Quality
    origin: Literal["GOOGLE_STT", "HUMAN_CORRECTION", "MOCK"]
    provider_profile_version: Text
    supersedes_id: Id | None
    reason: Text | None

    @model_validator(mode="after")
    def lifecycle(self) -> Self:
        if self.end_ms <= self.start_ms:
            raise ValueError("invalid segment time range")
        if self.origin == "HUMAN_CORRECTION" and (
            self.supersedes_id is None or self.reason is None
        ):
            raise ValueError("corrections require prior revision and reason")
        return self


class CriticalSlot(Contract):
    value: Text | None
    quality: Quality
    evidence_ids: list[Id]
    alternatives: list[Text]
    unknowns: list[Text]

    @model_validator(mode="after")
    def supported(self) -> Self:
        if self.quality == "SUPPORTED" and (self.value is None or not self.evidence_ids):
            raise ValueError("supported slot needs value and evidence")
        if self.value is None and not self.unknowns:
            raise ValueError("null critical slot requires unknown reason")
        return self


class Intent(Evidenced):
    id: Id
    segment_ids: Annotated[list[Id], Field(min_length=1)]
    speech_act: SpeechAct
    role_candidate: Literal["CONTROLLER", "PILOT", "VEHICLE", "UNKNOWN"]
    entity_candidates: list[Id]
    actions: list[Action]
    callsign: CriticalSlot
    runway: CriticalSlot
    condition: Text | None
    negation: bool | None
    quality: Quality
    alternatives: list[Text]
    unknowns: list[Text]

    @model_validator(mode="after")
    def references(self) -> Self:
        evidence_ids = {e.id for e in self.evidence}
        for slot in (self.callsign, self.runway):
            if not set(slot.evidence_ids) <= evidence_ids:
                raise ValueError("slot evidence must be included")
        return self


class Association(Evidenced):
    id: Id
    source_intent_id: Id
    target_intent_id: Id | None
    entity_candidates: list[Id]
    relationship: Literal["READBACK_OF", "REPORT_FOR", "CORRECTION_OF", "CANCELS", "POSSIBLE_LINK"]
    status: Literal[
        "PROPOSED",
        "ACCEPTED_BY_VALIDATION",
        "CONFIRMED_BY_REVIEW",
        "AMBIGUOUS",
        "REJECTED",
        "SUPERSEDED",
    ]
    alternatives: list[Id]
    unknowns: list[Text]


class MemoryEvent(Evidenced):
    id: Id
    entity_id: Id
    intent_id: Id
    interpretation: Literal["CANDIDATE", "SUPPORTED", "AMBIGUOUS", "REVIEWED", "REJECTED"]
    instruction: Literal["ACTIVE", "SUPERSEDED", "CANCELLED", "COMPLETED_REPORTED", "UNKNOWN"]
    readback: Literal["NOT_OBSERVED", "MATCHED", "PARTIAL", "MISMATCH", "AMBIGUOUS", "CORRECTED"]
    movement: Literal["NOT_EVALUABLE", "CONSISTENT", "DIVERGENCE_CANDIDATE", "UNKNOWN"]
    reviewer: Literal["UNREVIEWED", "CONFIRMED", "DISMISSED", "UNRESOLVED"]
    dependency_hashes: list[Hash]
    reducer_version: Text


class OpenLoop(Evidenced):
    id: Id
    originating_id: Id
    entity_ids: list[Id]
    kind: Literal[
        "REQUEST_RESPONSE", "REPORT_EXPECTED", "COORDINATION_PENDING", "READBACK_EXPECTED"
    ]
    status: Literal["OPEN", "PARTIAL", "CLOSED_WITH_EVIDENCE", "CANCELLED", "SUPERSEDED", "UNKNOWN"]
    started_ms: Ms
    expected_window_ms: Ms | None
    coverage_known: bool
    closing_evidence_ids: list[Id]
    timer_profile_version: Text

    @model_validator(mode="after")
    def closure(self) -> Self:
        if self.status == "CLOSED_WITH_EVIDENCE" and (
            not self.coverage_known or not self.closing_evidence_ids
        ):
            raise ValueError("closure requires matching evidence and known coverage")
        if not set(self.closing_evidence_ids) <= {e.id for e in self.evidence}:
            raise ValueError("closing evidence not included")
        return self


class Finding(Evidenced):
    id: Id
    category: Literal[
        "CRITICAL_SLOT_UNCERTAIN",
        "READBACK_DISCREPANCY",
        "OPEN_LOOP",
        "SPEECH_RECORD_DISCREPANCY",
        "MOVEMENT_DIVERGENCE",
        "QUALITY_GAP",
    ]
    statement: Text
    priority: Literal["INFO", "NOTICE", "ATTENTION"]
    status: Literal["OPEN", "UNDER_REVIEW", "CONFIRMED", "DISMISSED", "UNRESOLVED", "SUPERSEDED"]
    entity_ids: list[Id]
    rule_version: Text
    model_version: Text | None
    quality: Quality
    applicability: Literal["LAB_ONLY", "PARTNER_REPLAY_REVIEW"]
    unknowns: list[Text]
    stale: bool


class Option(Evidenced):
    id: Id
    as_of_ms: Ms
    statement: Text
    rationale: Text
    preconditions: list[Text]
    unknowns: list[Text]
    consequences: list[Text]
    applicability: Literal["LAB_ONLY", "PARTNER_REPLAY_REVIEW"]
    review_status: Literal["UNREVIEWED", "RELEVANT", "NOT_RELEVANT", "UNSUPPORTED", "UNRESOLVED"]
    model_version: Text
    prompt_version: Text
    input_hash: Hash


class Review(Evidenced):
    id: Id
    target_id: Id
    target_revision: Revision
    actor_id: Id
    expected_version: Revision
    decision: Literal[
        "CONFIRMED",
        "DISMISSED",
        "UNRESOLVED",
        "RELEVANT",
        "NOT_RELEVANT",
        "UNSUPPORTED",
        "CORRECTION",
    ]
    reason: Text
    supersedes_id: Id | None


class FactualItem(Contract):
    statement: Text
    evidence_ids: Annotated[list[Id], Field(min_length=1)]
    unknowns: list[Text]


class Brief(Evidenced):
    id: Id
    as_of_ms: Ms
    items: list[FactualItem]
    labels: list[Text]
    model_version: Text
    prompt_version: Text

    @model_validator(mode="after")
    def item_references(self) -> Self:
        ids = {e.id for e in self.evidence}
        if any(not set(item.evidence_ids) <= ids for item in self.items):
            raise ValueError("factual item evidence must be included")
        return self


class QueryAnswer(Brief):
    question: Text
    status: Literal["COMPLETE", "PARTIAL", "INSUFFICIENT_CONTEXT", "UNAVAILABLE"]


class Usage(Contract):
    audio_ms: Ms | None
    input_tokens: Ms | None
    output_tokens: Ms | None
    cost_microunits: Ms | None
    latency_ms: Ms


class AnalysisRun(Scoped):
    id: Id
    status: Literal["QUEUED", "RUNNING", "PARTIAL", "COMPLETED", "FAILED", "CANCELLED"]
    input_hash: Hash
    config_hash: Hash
    model_version: Text
    api_version: Text
    sdk_version: Text
    prompt_version: Text
    reducer_version: Text
    rule_version: Text
    usage: Usage | None


class JobLease(Scoped):
    job_id: Id
    attempt_id: Id
    lease_id: Id
    owner_id: Id
    stage: Literal[
        "AUDIO", "STT", "INTENT", "ASSOCIATION", "MEMORY", "FINDINGS", "BRIEF", "QUERY", "EXPORT"
    ]
    input_hash: Hash
    config_hash: Hash
    expires_ms: Ms
    deadline_ms: Ms
    budget_microunits: Ms
    asset_ids: list[Id]

    @model_validator(mode="after")
    def deadline(self) -> Self:
        if self.expires_ms > self.deadline_ms:
            raise ValueError("lease cannot outlive deadline")
        return self


class JobResult(Scoped):
    job_id: Id
    attempt_id: Id
    lease_id: Id
    input_hash: Hash
    config_hash: Hash
    output_hash: Hash
    status: Literal["COMPLETE", "PARTIAL", "FAILED"]
    outputs: list[
        TranscriptSegment
        | Intent
        | Association
        | MemoryEvent
        | OpenLoop
        | Finding
        | Option
        | Brief
        | QueryAnswer
    ]
    evidence: list[Evidence]
    artifacts: list["ArtifactSubmission"] = []
    usage: Usage
    failure_code: (
        Literal[
            "PROVIDER_UNAVAILABLE",
            "PROVIDER_QUOTA_EXCEEDED",
            "INVALID_AI_OUTPUT",
            "BUDGET_EXCEEDED",
        ]
        | None
    )

    @model_validator(mode="after")
    def output_scope(self) -> Self:
        if self.status == "FAILED" and (
            self.failure_code is None or self.outputs or self.artifacts
        ):
            raise ValueError("failed result requires failure code and no accepted outputs")
        if self.status != "FAILED" and self.failure_code is not None:
            raise ValueError("successful result cannot carry failure code")
        for item in [*self.outputs, *self.evidence, *self.artifacts]:
            if (item.session_id, item.analysis_run_id, item.revision) != (
                self.session_id,
                self.analysis_run_id,
                self.revision,
            ):
                raise ValueError("result outputs must share session/run/revision")
        return self


class CommitReceipt(Scoped):
    id: Id
    job_id: Id
    attempt_id: Id
    output_hash: Hash
    sequence: Revision


class ArtifactSubmission(Scoped):
    id: Id
    kind: Literal["AUDIO_DERIVATIVE", "JSON_REPORT", "CSV_REPORT", "HTML_REPORT"]
    sha256: Hash
    size_bytes: Ms
    source_asset_id: Id | None
    transform_version: Text
    source_range: TimeRange | None
    derivative_range: TimeRange | None
    expires_at: datetime | None
    required_capability: Literal["audio", "export"]


class ProviderProfile(Contract):
    id: Id
    provider: Literal["GOOGLE_STT", "GEMINI"]
    model: Text
    transport: Literal["STT_V2_INLINE", "GEMINI_DEVELOPER_INTERACTIONS"]
    version: Text
    region: Text | None
    locale: Text | None
    timeout_seconds: Annotated[int, Field(ge=1, le=300)]
    store: Literal[False] = False
    readiness: Literal["UNVERIFIED", "READY", "UNAVAILABLE"]


class ToolRequest(Contract):
    name: Literal[
        "get_entity_memory",
        "get_transcript_window",
        "get_session_events",
        "get_observed_tracks",
        "get_active_rule_context",
        "get_evidence",
    ]
    entity_id: Id | None
    evidence_id: Id | None
    window: TimeRange | None
    limit: Annotated[int, Field(ge=1, le=100)] = 50


class Snapshot(Scoped):
    as_of_ms: Ms
    mode: Mode
    sequence: Ms
    events: list[SourceEvent]
    memory: list[MemoryEvent]
    findings: list[Finding]
    quality: Quality

    @model_validator(mode="after")
    def scope_and_as_of(self) -> Self:
        for row in [*self.events, *self.memory, *self.findings]:
            if row.session_id != self.session_id:
                raise ValueError("cross-session snapshot")
            if row.analysis_run_id is not None and row.analysis_run_id != self.analysis_run_id:
                raise ValueError("cross-run snapshot")
            if row.event_time_ms > self.as_of_ms:
                raise ValueError("future event in snapshot")
            if self.mode == "AS_KNOWN" and (
                row.available_time_ms is None or row.available_time_ms > self.as_of_ms
            ):
                raise ValueError("unavailable event in AS_KNOWN snapshot")
        return self


class PlaybackState(Scoped):
    status: Literal["PAUSED", "PLAYING", "SEEKING", "ENDED"]
    cursor_ms: Ms
    speed: Annotated[float, Field(gt=0, le=16, allow_inf_nan=False)]
    leader_id: Id | None
    view: Literal["LEADER", "FOLLOW", "LOCAL"]


class JobProgress(Scoped):
    job_id: Id
    stage: Text
    status: Literal["QUEUED", "RUNNING", "PARTIAL", "COMPLETED", "FAILED", "CANCELLED"]
    completed_units: Ms
    total_units: Ms | None


class ResyncRequired(Scoped):
    reason: Literal["SEQUENCE_GAP", "REVISION_CHANGED", "PERMISSION_CHANGED"]
    snapshot_sequence: Ms


class SourceQualityChanged(Scoped):
    source_id: Id
    coverage: Coverage


class StreamEvent(Contract):
    session_id: Id
    analysis_run_id: Id | None
    sequence: Revision
    type: Literal[
        "SNAPSHOT",
        "PLAYBACK_CHANGED",
        "JOB_PROGRESS",
        "TRANSCRIPT_REVISION",
        "MEMORY_CHANGED",
        "FINDING_CHANGED",
        "OPTION_READY",
        "REVIEW_ADDED",
        "SOURCE_QUALITY_CHANGED",
        "RESYNC_REQUIRED",
    ]
    recorded_at: datetime
    payload: (
        Snapshot
        | PlaybackState
        | JobProgress
        | TranscriptSegment
        | MemoryEvent
        | Finding
        | Option
        | Review
        | SourceQualityChanged
        | ResyncRequired
    )

    @field_validator("recorded_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("recorded_at must be UTC")
        return value

    @model_validator(mode="after")
    def typed_payload(self) -> Self:
        types = {
            "SNAPSHOT": Snapshot,
            "PLAYBACK_CHANGED": PlaybackState,
            "JOB_PROGRESS": JobProgress,
            "TRANSCRIPT_REVISION": TranscriptSegment,
            "MEMORY_CHANGED": MemoryEvent,
            "FINDING_CHANGED": Finding,
            "OPTION_READY": Option,
            "REVIEW_ADDED": Review,
            "SOURCE_QUALITY_CHANGED": SourceQualityChanged,
            "RESYNC_REQUIRED": ResyncRequired,
        }
        if not isinstance(self.payload, types[self.type]):
            raise ValueError("stream type/payload mismatch")
        if (
            self.payload.session_id != self.session_id
            or self.payload.analysis_run_id != self.analysis_run_id
        ):
            raise ValueError("stream payload scope mismatch")
        return self


EXAMPLE_MODELS: dict[str, type[Contract]] = {
    "manifest": SourceManifest,
    "transcript": TranscriptSegment,
    "intent": Intent,
    "finding": Finding,
    "option": Option,
    "review": Review,
    "job_result": JobResult,
    "context": RequestContext,
    "track": Track,
}
PUBLIC_MODELS: tuple[type[Contract], ...] = (
    ClockMapping,
    Permissions,
    Coverage,
    TimeRange,
    SourceManifest,
    Evidence,
    SourceEvent,
    Track,
    GeometryResult,
    TranscriptSegment,
    CriticalSlot,
    Intent,
    Association,
    MemoryEvent,
    OpenLoop,
    Finding,
    Option,
    Review,
    Brief,
    QueryAnswer,
    AnalysisRun,
    Snapshot,
    StreamEvent,
    ProviderProfile,
    PlaybackState,
    JobProgress,
    ResyncRequired,
    SourceQualityChanged,
)
INTERNAL_MODELS: tuple[type[Contract], ...] = (
    RequestContext,
    JobLease,
    JobResult,
    CommitReceipt,
    ArtifactSubmission,
    ToolRequest,
    Usage,
)
