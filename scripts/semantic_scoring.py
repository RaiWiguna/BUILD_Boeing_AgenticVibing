"""Offline B04/B05 evaluator. No runtime imports, provider requests or inferred gold."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^\S+$")]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Value = Annotated[str, Field(min_length=1, max_length=512)]
Task = Literal[
    "speech_act",
    "callsign",
    "runway",
    "action",
    "negation",
    "condition",
    "correction",
    "cancellation",
    "association",
    "open_loop",
    "finding",
    "brief_relevance",
    "option_relevance",
]
RELEVANCE = {"brief_relevance", "option_relevance"}
Relationship = Literal["READBACK_OF", "REPORT_FOR", "CORRECTION_OF", "CANCELS"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class Scope(Record):
    session: Identifier
    run: Identifier
    revision: int = Field(ge=1)
    source_sha256: Hash
    input_sha256: Hash
    family: Identifier
    speakers: tuple[Identifier, ...] = Field(min_length=1, max_length=32)
    split: Literal["TUNING", "HELD_OUT"]
    as_of_ms: int = Field(ge=0)


class Review(Record):
    reviewer: Identifier
    experience_record: Identifier
    reviewed_at: datetime
    record_id: Identifier

    @model_validator(mode="after")
    def utc(self) -> Self:
        offset = self.reviewed_at.utcoffset()
        if offset is None or offset.total_seconds():
            raise ValueError("REVIEW_DATE_INVALID")
        return self


class Evidence(Record):
    id: Identifier
    scope: Scope
    content_sha256: Hash
    available_ms: int | None = Field(ge=0)


class Annotation(Record):
    id: Identifier
    subject_id: Identifier
    scope: Scope
    task: Task
    label_status: Literal["KNOWN", "AMBIGUOUS", "UNKNOWN"]
    expected: Value | None
    acceptable_evidence: tuple[Identifier, ...] = Field(max_length=64)
    earliest_close_ms: int | None = Field(ge=0)
    output_sha256: Hash | None
    reviews: tuple[Review, ...] = Field(max_length=8)
    adjudication: Review | None
    relationship: Relationship | None = None
    required_evidence: tuple[Identifier, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def shape(self) -> Self:
        if (self.label_status == "KNOWN") != (self.expected is not None):
            raise ValueError("LABEL_VALUE_INVALID")
        if len(set(self.acceptable_evidence)) != len(self.acceptable_evidence):
            raise ValueError("DUPLICATE_EVIDENCE")
        if len(set(self.required_evidence)) != len(self.required_evidence) or not set(
            self.required_evidence
        ) <= set(self.acceptable_evidence):
            raise ValueError("REQUIRED_EVIDENCE_INVALID")
        if (self.task == "association") != (self.relationship is not None):
            raise ValueError("RELATIONSHIP_INVALID")
        if len({r.reviewer for r in self.reviews}) != len(self.reviews):
            raise ValueError("DUPLICATE_REVIEWER")
        if self.task == "open_loop":
            if self.expected not in (None, "OPEN", "CLOSED"):
                raise ValueError("LOOP_VALUE_INVALID")
            if (self.expected == "CLOSED") != (self.earliest_close_ms is not None):
                raise ValueError("CLOSURE_TIME_REQUIRED")
            if self.earliest_close_ms is not None and self.earliest_close_ms > self.scope.as_of_ms:
                raise ValueError("CLOSURE_AFTER_AS_OF")
        elif self.earliest_close_ms is not None:
            raise ValueError("UNEXPECTED_CLOSURE_TIME")
        if self.task in RELEVANCE:
            if self.expected not in (None, "RELEVANT", "IRRELEVANT"):
                raise ValueError("RELEVANCE_VALUE_INVALID")
            if not self.reviews or self.output_sha256 is None:
                raise ValueError("RELEVANCE_REVIEW_REQUIRED")
        elif self.output_sha256 is not None:
            raise ValueError("UNEXPECTED_OUTPUT_BINDING")
        if self.task == "finding" and self.expected not in (None, "PRESENT", "ABSENT"):
            raise ValueError("FINDING_VALUE_INVALID")
        if self.task in {"correction", "cancellation", "negation"} and self.expected not in (
            None,
            "PRESENT",
            "ABSENT",
        ):
            raise ValueError("BOOLEAN_VALUE_INVALID")
        if self.task == "speech_act" and self.expected not in (
            None,
            "REQUEST",
            "INSTRUCTION",
            "READBACK",
            "REPORT",
            "CORRECTION",
            "CANCELLATION",
            "COORDINATION",
            "HANDOFF",
            "INFORMATION",
        ):
            raise ValueError("SPEECH_ACT_INVALID")
        if self.task == "action" and self.expected not in (
            None,
            "HOLD_SHORT",
            "CROSS_RUNWAY",
            "LINE_UP_WAIT",
            "TAKEOFF",
            "LAND",
            "TAXI",
            "VACATE",
            "CONTACT",
            "REPORT",
        ):
            raise ValueError("ACTION_INVALID")
        return self


class Prediction(Record):
    id: Identifier
    scope: Scope
    status: Literal["ANSWERED", "UNKNOWN", "ABSTAINED"]
    value: Value | None
    evidence_ids: tuple[Identifier, ...] = Field(max_length=64)
    closed_at_ms: int | None = Field(ge=0)
    output_sha256: Hash
    relationship: Relationship | None = None

    @model_validator(mode="after")
    def shape(self) -> Self:
        if (self.status == "ANSWERED") != (self.value is not None):
            raise ValueError("PREDICTION_VALUE_INVALID")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("DUPLICATE_EVIDENCE")
        if self.closed_at_ms is not None and self.status != "ANSWERED":
            raise ValueError("UNANSWERED_CLOSURE")
        return self


class Provenance(Record):
    profile: Literal["MOCK", "GOOGLE"]
    model: Identifier
    api_version: Identifier
    sdk_version: Identifier
    prompt_version: Identifier
    schema_sha256: Hash
    config_sha256: Hash
    raw_output_sha256: Hash
    predictions_sha256: Hash
    execution_record: Identifier
    calls: int = Field(ge=0)
    executed_at: datetime
    operator_review: Review | None

    @model_validator(mode="after")
    def utc(self) -> Self:
        offset = self.executed_at.utcoffset()
        if offset is None or offset.total_seconds():
            raise ValueError("EXECUTION_DATE_INVALID")
        return self


def prediction_digest(predictions: tuple[Prediction, ...]) -> str:
    """Versioned canonical normalized-output binding; list order is significant."""
    body = [p.model_dump(mode="json") for p in predictions]
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def strict_json(body: bytes) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def invalid_constant(value: str) -> object:
        raise ValueError("NONFINITE_JSON")

    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid_constant)


def validate_raw_outputs(bundle: Bundle, body: bytes) -> None:
    """Verify acquired raw envelope and per-output hashes; human audit owns projection."""
    if hashlib.sha256(body).hexdigest() != bundle.provenance.raw_output_sha256:
        raise ValueError("RAW_HASH_MISMATCH")
    raw = strict_json(body)
    if not isinstance(raw, dict) or set(raw) != {"outputs"} or not isinstance(raw["outputs"], dict):
        raise ValueError("RAW_ENVELOPE_INVALID")
    outputs = raw["outputs"]
    if set(outputs) != {p.id for p in bundle.predictions}:
        raise ValueError("RAW_IDS_MISMATCH")
    for p in bundle.predictions:
        digest = hashlib.sha256(
            json.dumps(
                outputs[p.id], sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ).hexdigest()
        if digest != p.output_sha256:
            raise ValueError("RAW_OUTPUT_BINDING_INVALID")


class Bundle(Record):
    version: Literal["b045-semantic-bundle-1"]
    protocol: Literal["b045-semantic-1"]
    purpose: Literal["TEST_ONLY", "AUDITED"]
    rights_record: Identifier
    rubric_record: Identifier
    protocol_review: Review | None
    thresholds: Literal["UNSET"]
    domain_status: Literal["NOT_DOMAIN_VALIDATED"]
    annotations: tuple[Annotation, ...] = Field(min_length=1, max_length=4096)
    predictions: tuple[Prediction, ...] = Field(max_length=4096)
    evidence: tuple[Evidence, ...] = Field(max_length=8192)
    provenance: Provenance

    @model_validator(mode="after")
    def consistent(self) -> Self:
        labels = {a.id: a for a in self.annotations}
        evidence = {e.id: e for e in self.evidence}
        if len(labels) != len(self.annotations) or len(evidence) != len(self.evidence):
            raise ValueError("DUPLICATE_ID")
        if len({p.id for p in self.predictions}) != len(self.predictions):
            raise ValueError("DUPLICATE_ID")
        if not {p.id for p in self.predictions} <= labels.keys():
            raise ValueError("UNEXPECTED_PREDICTION_ID")
        if prediction_digest(self.predictions) != self.provenance.predictions_sha256:
            raise ValueError("PREDICTIONS_HASH_MISMATCH")
        assignments: dict[tuple[str, str], str] = {}
        for scope in [a.scope for a in self.annotations] + [e.scope for e in self.evidence]:
            identities = [
                ("session", scope.session),
                ("source", scope.source_sha256),
                ("input", scope.input_sha256),
                ("family", scope.family),
                *(("speaker", s) for s in scope.speakers),
            ]
            for identity in identities:
                old = assignments.setdefault(identity, scope.split)
                if old != scope.split:
                    raise ValueError("SPLIT_LEAKAGE")
        for a in self.annotations:
            self.check_evidence(a.scope, a.acceptable_evidence, evidence)
        for p in self.predictions:
            a = labels[p.id]
            if p.scope != a.scope:
                raise ValueError("SCOPE_MISMATCH")
            self.check_evidence(p.scope, p.evidence_ids, evidence)
            if (a.task == "association" and p.status == "ANSWERED") != (p.relationship is not None):
                raise ValueError("RELATIONSHIP_INVALID")
            if a.task == "association" and p.status == "ANSWERED" and p.value == "NO_PAIR":
                if p.relationship is not None:
                    raise ValueError("RELATIONSHIP_INVALID")
            if a.task in {"finding", "correction", "cancellation", "negation"} and p.value not in (
                None,
                "PRESENT",
                "ABSENT",
            ):
                raise ValueError("PREDICTION_VOCABULARY_INVALID")
            if a.task in RELEVANCE and a.output_sha256 != p.output_sha256:
                raise ValueError("RELEVANCE_OUTPUT_MISMATCH")
            if a.task == "open_loop":
                if p.value not in (None, "OPEN", "CLOSED"):
                    raise ValueError("LOOP_VALUE_INVALID")
                if (p.value == "CLOSED") != (p.closed_at_ms is not None):
                    raise ValueError("CLOSURE_TIME_REQUIRED")
                if p.closed_at_ms is not None and p.closed_at_ms > p.scope.as_of_ms:
                    raise ValueError("CLOSURE_AFTER_AS_OF")
            elif p.closed_at_ms is not None:
                raise ValueError("UNEXPECTED_CLOSURE_TIME")
        if self.purpose == "AUDITED":
            self.check_audit()
        elif self.provenance.profile != "MOCK" or self.provenance.calls:
            raise ValueError("TEST_ONLY_REQUIRES_MOCK")
        return self

    @staticmethod
    def check_evidence(scope: Scope, ids: tuple[str, ...], inventory: dict[str, Evidence]) -> None:
        for identifier in ids:
            ev = inventory.get(identifier)
            if ev is None or ev.scope != scope:
                raise ValueError("EVIDENCE_SCOPE_INVALID")
            if ev.available_ms is None or ev.available_ms > scope.as_of_ms:
                raise ValueError("EVIDENCE_UNAVAILABLE")

    def check_audit(self) -> None:
        p = self.provenance
        if p.profile != "GOOGLE" or p.calls < 1 or p.operator_review is None:
            raise ValueError("REAL_OUTPUT_REVIEW_REQUIRED")
        if p.operator_review.reviewed_at < p.executed_at:
            raise ValueError("OUTPUT_REVIEW_BEFORE_EXECUTION")
        if self.protocol_review is None or self.protocol_review.reviewed_at >= p.executed_at:
            raise ValueError("PROTOCOL_NOT_FROZEN")
        if {a.scope.split for a in self.annotations} != {"TUNING", "HELD_OUT"}:
            raise ValueError("HELD_OUT_REQUIRED")
        for a in self.annotations:
            reviewers = {r.reviewer for r in a.reviews}
            if len(reviewers) < 2 or a.adjudication is None:
                raise ValueError("ANNOTATION_AUDIT_REQUIRED")
            if a.adjudication.reviewer in reviewers or any(
                r.reviewed_at > a.adjudication.reviewed_at for r in a.reviews
            ):
                raise ValueError("ADJUDICATION_INVALID")
            if a.task not in RELEVANCE and (
                a.adjudication.reviewed_at > self.protocol_review.reviewed_at
            ):
                raise ValueError("LABEL_NOT_FROZEN")
            if a.task in RELEVANCE and any(r.reviewed_at < p.executed_at for r in a.reviews):
                raise ValueError("RELEVANCE_REVIEW_BEFORE_EXECUTION")


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def score(bundle: Bundle) -> dict[str, object]:
    """Count exact semantic labels; relevance is ONLY the supplied reviewer rating."""
    bundle = Bundle.model_validate_json(bundle.model_dump_json())
    predictions = {p.id: p for p in bundle.predictions}
    groups: dict[str, Counter[str]] = {}
    for a in bundle.annotations:
        c = groups.setdefault(f"{a.scope.split}/{a.task}", Counter())
        c["total"] += 1
        p = predictions.get(a.id)
        state = "MISSING" if p is None else p.status
        c["prediction_unknown" if state == "UNKNOWN" else state.lower()] += 1
        c["label_unknown" if a.label_status == "UNKNOWN" else a.label_status.lower()] += 1
        answered = p is not None and p.status == "ANSWERED"
        if a.label_status != "KNOWN":
            c["unassessable_answers"] += answered
            c["unassessable_closures"] += (
                a.task == "open_loop" and p is not None and p.value == "CLOSED"
            )
            c["unassessable_findings"] += (
                a.task == "finding" and p is not None and p.value == "PRESENT"
            )
            c["ambiguity_abstentions"] += a.label_status == "AMBIGUOUS" and state == "ABSTAINED"
            continue
        if a.task in RELEVANCE:
            c["reviewed_outputs"] += p is not None
            c["relevant_outputs"] += p is not None and a.expected == "RELEVANT"
            continue
        correct = (
            answered
            and p is not None
            and p.value == a.expected
            and p.relationship == a.relationship
        )
        support = (
            answered
            and p is not None
            and bool(p.evidence_ids)
            and set(p.evidence_ids) <= set(a.acceptable_evidence)
            and set(a.required_evidence) <= set(p.evidence_ids)
        )
        c["correct"] += correct
        c["supported_answers"] += support
        if a.task == "association":
            paired = answered and p is not None and p.value != "NO_PAIR"
            c["assessable_pair_attempts"] += paired
            c["wrong_pairs"] += paired and not correct
            c["missed_pairs"] += a.expected != "NO_PAIR" and not paired
            c["correct_no_pair"] += correct and a.expected == "NO_PAIR"
        if a.task == "open_loop" and p is not None and p.value == "CLOSED":
            c["assessable_closures"] += 1
            premature = (
                a.expected == "CLOSED"
                and p.closed_at_ms is not None
                and a.earliest_close_ms is not None
                and p.closed_at_ms < a.earliest_close_ms
            )
            c["premature_closures"] += premature
            c["false_closures"] += a.expected == "OPEN"
            c["correct_supported_closures"] += correct and not premature and support
        if a.task == "finding":
            c["predicted_findings"] += answered and p is not None and p.value == "PRESENT"
            c["expected_findings"] += a.expected == "PRESENT"
            c["true_findings"] += correct and a.expected == "PRESENT"
            c["supported_true_findings"] += correct and a.expected == "PRESENT" and support
    metrics = {}
    for name, c in groups.items():
        metrics[name] = {
            "counts": dict(c),
            "exact_accuracy": None
            if name.split("/")[1] in RELEVANCE
            else ratio(c["correct"], c["known"]),
            "coverage": ratio(c["answered"], c["total"]),
            "wrong_pair_rate": ratio(c["wrong_pairs"], c["assessable_pair_attempts"]),
            "closure_precision": ratio(c["correct_supported_closures"], c["assessable_closures"]),
            "finding_precision": ratio(c["true_findings"], c["predicted_findings"]),
            "finding_recall": ratio(c["true_findings"], c["expected_findings"]),
            "supported_finding_precision": ratio(
                c["supported_true_findings"], c["predicted_findings"]
            ),
            "reviewer_relevance": ratio(c["relevant_outputs"], c["reviewed_outputs"]),
        }
    return {
        "status": "TEST_ONLY_ARITHMETIC" if bundle.purpose == "TEST_ONLY" else "DESCRIPTIVE_ONLY",
        "protocol": bundle.protocol,
        "metrics": metrics,
        "thresholds": "UNSET",
        "acceptance_decision": None,
        "domain_status": "NOT_DOMAIN_VALIDATED",
        "integrated_readiness": False,
    }
