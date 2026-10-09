"""Evidence-bound advisory records; no command, transmission or execution fields."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from flowlens.contracts.models import Contract, Evidence, GeometryResult, Hash, Text, Timed
from flowlens.intent.models import Provenance
from flowlens.memory.models import AcceptedEvent, Invalidation

NAMESPACE = "analysis.advisory"
Category = Literal[
    "CRITICAL_SLOT_UNCERTAIN",
    "READBACK_DISCREPANCY",
    "OPEN_LOOP",
    "SPEECH_RECORD_DISCREPANCY",
    "MOVEMENT_DIVERGENCE",
    "QUALITY_GAP",
]


class Fact(Timed):
    id: UUID
    label: Literal["SAID", "HEARD", "REPORTED", "OBSERVED", "SOURCE_ALERT", "SOURCE_RECORD"]
    statement: Text
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=64)
    entity_id: UUID | None
    source_severity: str | None = None


class ComparisonEligibility(Contract):
    identity_known: bool
    association_known: bool
    clock_aligned: bool
    coverage_known: bool
    instruction_applicable: bool
    track_fresh: bool


class Signal(Timed):
    """Authoritative source comparison/quality eligibility, never model authority.

    Platform adapter must attest identity, alignment, freshness, rule applicability
    and complete geometry/record support for evaluated external comparisons.
    """

    id: UUID
    category: Literal["SPEECH_RECORD_DISCREPANCY", "MOVEMENT_DIVERGENCE", "QUALITY_GAP"]
    status: Literal["SUPPORTED", "NOT_EVALUABLE"]
    evidence: tuple[Evidence, ...]
    entity_id: UUID | None
    rule_version: Text
    unknowns: tuple[Text, ...]
    fact_ids: tuple[UUID, ...]
    eligibility: ComparisonEligibility | None = None
    geometry: GeometryResult | None = None


class Inputs(Contract):
    events: tuple[AcceptedEvent | Invalidation, ...] = Field(max_length=4096)
    facts: tuple[Fact, ...] = Field(max_length=256)
    signals: tuple[Signal, ...] = Field(max_length=256)


class Finding(Contract):
    id: UUID
    category: Category
    statement: Text
    status: Literal["SUPPORTED", "NOT_EVALUABLE"]
    priority: Literal["INFO", "NOTICE", "ATTENTION"]
    evidence: tuple[Evidence, ...]
    entity_ids: tuple[UUID, ...]
    said: tuple[UUID, ...] = ()
    heard: tuple[UUID, ...] = ()
    observed: tuple[UUID, ...] = ()
    rule_version: str = "findings-1"
    unknowns: tuple[Text, ...]
    applicability: Literal["LAB_ONLY", "PARTNER_REPLAY_REVIEW"] = "LAB_ONLY"
    quality: Literal["SUPPORTED", "AMBIGUOUS", "MISSING"]


class Selection(Contract):
    """Provider selects supported facts and bounded hypothetical review templates.

    No free factual prose: every selected statement is rendered from the validated
    catalog. This deliberately conservative language policy needs domain evaluation.
    """

    status: Literal["COMPLETE", "PARTIAL", "INSUFFICIENT_CONTEXT"]
    fact_ids: tuple[UUID, ...] = Field(max_length=64)
    option_kinds: tuple[Literal["REVIEW_EVIDENCE", "COMPARE_OFFLINE_ALTERNATIVES"], ...] = Field(
        max_length=2
    )


class Option(Contract):
    statement: Text
    rationale_evidence: tuple[UUID, ...] = Field(min_length=1)
    preconditions: tuple[Text, ...] = Field(min_length=1)
    unknowns: tuple[Text, ...]
    consequences: tuple[Text, ...] = Field(min_length=1)
    applicability: Literal["LAB_ONLY"] = "LAB_ONLY"
    review_status: Literal["UNREVIEWED"] = "UNREVIEWED"


class Document(Contract):
    kind: Literal["FINDINGS", "BRIEF", "OPTIONS"]
    as_of_ms: int = Field(ge=0)
    mode: Literal["AS_KNOWN", "DEBRIEF"]
    input_digest: Hash
    findings: tuple[Finding, ...]
    facts: tuple[Fact, ...]
    options: tuple[Option, ...]
    status: Literal["COMPLETE", "PARTIAL", "INSUFFICIENT_CONTEXT"]
    provenance: Provenance
    prompt_version: Literal["advisory-select-1"] = "advisory-select-1"
    sections: tuple[str, ...] = (
        "KNOWN_SITUATION",
        "ACTIVE_INSTRUCTIONS_RESTRICTIONS",
        "OPEN_LOOPS",
        "FINDINGS",
        "UNKNOWNS_COVERAGE_GAPS",
    )
    active_instruction_ids: tuple[UUID, ...]
    open_loop_ids: tuple[UUID, ...]
    unknowns: tuple[Text, ...]
    limitations: tuple[Text, ...] = (
        "NOT_DOMAIN_VALIDATED",
        "HYPOTHETICAL_OFFLINE_REVIEW_ONLY",
        "MATCHING_SPEECH_IS_NOT_MOVEMENT_COMPLIANCE",
        "REPORT_CLEAR_IS_NOT_PHYSICAL_RUNWAY_CLEAR",
    )


class Review(Contract):
    kind: Literal["REVIEW"] = "REVIEW"
    document_id: UUID
    subject_id: UUID
    actor_id: UUID
    expected_version: int = Field(ge=1)
    decision: Literal[
        "UNDER_REVIEW",
        "CONFIRMED",
        "DISMISSED",
        "UNRESOLVED",
        "RELEVANT",
        "NOT_RELEVANT",
        "UNSUPPORTED",
    ]
    reason: Text = Field(max_length=2048)


class Invalidate(Contract):
    kind: Literal["INVALIDATE"] = "INVALIDATE"
    document_ids: tuple[UUID, ...] = Field(min_length=1, max_length=4096)
    reason: Literal["CORRECTION", "REANALYSIS"]


class Entry(Timed):
    id: UUID
    input_hash: Hash
    stream_id: UUID
    version: int = Field(ge=1)
    body: Annotated[Document | Review | Invalidate, Field(discriminator="kind")]


class Proposal(Contract):
    document: Document
    selection: Selection


class QueryResult(Contract):
    status: Literal["COMPLETE", "PARTIAL", "INSUFFICIENT_CONTEXT", "UNAVAILABLE"]
    items: tuple[Fact, ...]
    context_start_ms: int | None
    context_end_ms: int
    mode: Literal["AS_KNOWN", "DEBRIEF"]
    provenance: Provenance | None
