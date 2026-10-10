"""Offline evaluator only. Never import this module from backend/runtime code.

Schema and arithmetic are usable with TEST_ONLY inputs. Benchmark loading requires
audited waveform labels and an operator-reviewed real Google receipt. Receipt
attestation and protobuf reconstruction are not a Google cryptographic signature.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING, Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from flowlens.analysis.transcript_records import RawTranscript
    from flowlens.providers.stt.models import AuthorizedChunk

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]
COHORTS = {
    "callsign",
    "runway",
    "action",
    "condition",
    "negation",
    "clipped_boundary",
    "overlap",
    "repetition",
    "gaps",
    "channels",
    "correction",
    "ambiguity",
    "word_alignment",
    "segment_alignment",
}


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class Range(Record):
    start_ns: int = Field(ge=0)
    end_ns: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_ns <= self.start_ns:
            raise ValueError("RANGE_INVALID")
        return self


class Review(Record):
    reviewer: Identifier
    reviewed_at: datetime
    waveform_listened: Literal[True]

    @model_validator(mode="after")
    def utc(self) -> Self:
        offset = self.reviewed_at.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("REVIEW_DATE_INVALID")
        return self


class Span(Record):
    text: str = Field(max_length=16384, repr=False)
    range: Range | None
    ambiguity: Literal["CLEAR", "AMBIGUOUS", "MISSING", "NOT_EVALUABLE"]
    alternatives: tuple[str, ...] = Field(max_length=16, repr=False)
    clipped: bool


class Slot(Record):
    kind: Literal["callsign", "runway", "action", "condition", "negation"]
    token_start: int = Field(ge=0)
    token_end: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=4096, repr=False)
    range: Range
    ambiguity: Literal["CLEAR", "AMBIGUOUS", "MISSING", "NOT_EVALUABLE"]
    alternatives: tuple[str, ...] = Field(max_length=16, repr=False)


class Label(Record):
    version: Literal["b03-waveform-label-1"]
    purpose: Literal["TEST_ONLY", "WAVEFORM_AUDITED"]
    case_id: Identifier
    session: Identifier
    family: Identifier
    speakers: tuple[Identifier, ...] = Field(min_length=1, max_length=32)
    split: Literal["TUNING", "HELD_OUT"]
    source_sha256: Hash
    audio_sha256: Hash
    source_id: UUID
    channel: int = Field(ge=0, le=1)
    source_range: Range
    rights_record: Identifier
    annotation_revision: int = Field(gt=0)
    transcript: str = Field(max_length=16384, repr=False)
    words: tuple[Span, ...] = Field(max_length=512, repr=False)
    segments: tuple[Span, ...] = Field(max_length=128, repr=False)
    slots: tuple[Slot, ...] = Field(max_length=128, repr=False)
    cohorts: tuple[Identifier, ...] = Field(max_length=32)
    reviews: tuple[Review, ...] = Field(max_length=8)
    adjudicator: Identifier
    adjudicated_at: datetime
    adjudication_record: Identifier
    domain_status: Literal["NOT_DOMAIN_VALIDATED"]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        tokens = tokenize(self.transcript)
        if len(tokens) > 512 or not set(self.cohorts) <= COHORTS:
            raise ValueError("LABEL_SCOPE_INVALID")
        if [t for word in self.words for t in tokenize(word.text)] != tokens:
            raise ValueError("WORD_TRANSCRIPT_MISMATCH")
        if any(len(tokenize(word.text)) != 1 for word in self.words):
            raise ValueError("WORD_INVALID")
        if [t for segment in self.segments for t in tokenize(segment.text)] != tokens:
            raise ValueError("SEGMENT_TRANSCRIPT_MISMATCH")
        spans: tuple[Span | Slot, ...] = (*self.words, *self.segments, *self.slots)
        for span in spans:
            if span.range and not (
                self.source_range.start_ns
                <= span.range.start_ns
                < span.range.end_ns
                <= self.source_range.end_ns
            ):
                raise ValueError("LABEL_RANGE_INVALID")
            if span.ambiguity == "CLEAR" and span.alternatives:
                raise ValueError("AMBIGUITY_INVALID")
        for slot in self.slots:
            if not 0 <= slot.token_start < slot.token_end <= len(tokens):
                raise ValueError("SLOT_RANGE_INVALID")
            if tokenize(slot.quote) != tokens[slot.token_start : slot.token_end]:
                raise ValueError("SLOT_QUOTE_INVALID")
            if slot.ambiguity == "CLEAR" and any(
                word.ambiguity != "CLEAR" or word.clipped
                for word in self.words[slot.token_start : slot.token_end]
            ):
                raise ValueError("SLOT_AMBIGUITY_INVALID")
        date = self.adjudicated_at
        offset = date.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("ADJUDICATION_DATE_INVALID")
        if self.purpose == "WAVEFORM_AUDITED" and (
            len({r.reviewer for r in self.reviews}) < 2
            or self.adjudicator in {r.reviewer for r in self.reviews}
            or any(r.reviewed_at > date for r in self.reviews)
        ):
            raise ValueError("REVIEW_INCOMPLETE")
        return self


class Prediction(Record):
    transcript: str = Field(max_length=16384, repr=False)
    words: tuple[Span, ...] = Field(max_length=512, repr=False)
    segments: tuple[Span, ...] = Field(max_length=128, repr=False)
    unknown_session_clock: bool


def tokenize(text: str) -> list[str]:
    """Frozen v1: Unicode casefold, whitespace split, preserve punctuation/numbers.

    Deliberately no callsign, number, negation or punctuation repair.
    """
    return text.casefold().split()


def align(reference: list[str], hypothesis: list[str]) -> list[tuple[int | None, int | None]]:
    """Levenshtein; deterministic ties: diagonal, deletion, insertion. Bounded DP."""
    if len(reference) > 512 or len(hypothesis) > 512:
        raise ValueError("TOKEN_LIMIT")
    rows = [list(range(len(hypothesis) + 1))]
    for i, token in enumerate(reference, 1):
        row = [i]
        for j, predicted in enumerate(hypothesis, 1):
            row.append(min(rows[-1][j - 1] + (token != predicted), rows[-1][j] + 1, row[-1] + 1))
        rows.append(row)
    i, j = len(reference), len(hypothesis)
    pairs: list[tuple[int | None, int | None]] = []
    while i or j:
        if i and j and rows[i][j] == rows[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1]):
            i, j = i - 1, j - 1
            pairs.append((i, j))
        elif i and rows[i][j] == rows[i - 1][j] + 1:
            i -= 1
            pairs.append((i, None))
        else:
            j -= 1
            pairs.append((None, j))
    return pairs[::-1]


def summary(values: list[float]) -> dict[str, int | float | None]:
    ordered = sorted(values)
    return {
        "count": len(values),
        "median_ms": median(values) if values else None,
        "p95_ms": ordered[math.ceil(0.95 * len(values)) - 1] if values else None,
        "max_ms": max(values) if values else None,
    }


def timing(reference: tuple[Span, ...], hypothesis: tuple[Span, ...]) -> dict[str, object]:
    pairs = align(
        [" ".join(tokenize(s.text)) for s in reference],
        [" ".join(tokenize(s.text)) for s in hypothesis],
    )
    counts: Counter[str] = Counter()
    starts: list[float] = []
    ends: list[float] = []
    for a, b in pairs:
        if a is None:
            counts["unmatched_prediction"] += 1
            continue
        ref = reference[a]
        counts["reference_spans"] += 1
        if ref.ambiguity != "CLEAR" or ref.clipped:
            counts["excluded_ambiguous_or_clipped"] += 1
            continue
        if b is None or tokenize(ref.text) != tokenize(hypothesis[b].text):
            counts["unmatched_reference"] += 1
            if b is not None:
                counts["unmatched_prediction"] += 1
            continue
        counts["text_matches"] += 1
        pred = hypothesis[b]
        if ref.range is None:
            counts["missing_reference_timing"] += 1
        elif pred.range is None:
            counts["missing_prediction_timing"] += 1
        else:
            counts["timed_matches"] += 1
            starts.append(abs(ref.range.start_ns - pred.range.start_ns) / 1_000_000)
            ends.append(abs(ref.range.end_ns - pred.range.end_ns) / 1_000_000)
    keys = (
        "reference_spans",
        "text_matches",
        "timed_matches",
        "unmatched_reference",
        "unmatched_prediction",
        "missing_reference_timing",
        "missing_prediction_timing",
        "excluded_ambiguous_or_clipped",
    )
    return {**{key: counts[key] for key in keys}, "start": summary(starts), "end": summary(ends)}


def score(label: Label, prediction: Prediction) -> dict[str, object]:
    """Arithmetic only; this function does not certify benchmark eligibility."""
    ref, hyp = tokenize(label.transcript), tokenize(prediction.transcript)
    pairs = align(ref, hyp)
    counts: Counter[str] = Counter()
    for a, b in pairs:
        if a is None:
            counts["insertions"] += 1
        elif b is None:
            counts["deletions"] += 1
        elif ref[a] != hyp[b]:
            counts["substitutions"] += 1
    clear = all(w.ambiguity == "CLEAR" and not w.clipped for w in label.words)
    wer = {key: counts[key] if clear else 0 for key in ("substitutions", "deletions", "insertions")}
    wer.update(
        reference_words=len(ref) if clear else 0, excluded_reference_words=0 if clear else len(ref)
    )
    error_count = sum(wer[k] for k in ("substitutions", "deletions", "insertions"))
    slots: dict[str, dict[str, int]] = {}
    mapped = {a: b for a, b in pairs if a is not None}
    for slot in label.slots:
        values = slots.setdefault(
            slot.kind,
            {"eligible": 0, "errors": 0, "ambiguous": 0, "missing": 0, "not_evaluable": 0},
        )
        if slot.ambiguity != "CLEAR":
            values[slot.ambiguity.lower()] += 1
            continue
        values["eligible"] += 1
        indices = [mapped[i] for i in range(slot.token_start, slot.token_end)]
        valid = all(i is not None for i in indices)
        if valid:
            first, last = indices[0], indices[-1]
            if first is None or last is None:
                raise ValueError("SLOT_ALIGNMENT_INVALID")
            valid = hyp[first : last + 1] == ref[slot.token_start : slot.token_end]
        if not valid:
            values["errors"] += 1
    return {
        "purpose": label.purpose,
        "wer": {**wer, "value": error_count / len(ref) if clear and ref else None},
        "critical_slots": slots,
        "word_alignment": timing(label.words, prediction.words),
        "segment_alignment": timing(label.segments, prediction.segments),
        "unknown_session_clock": prediction.unknown_session_clock,
    }


class FileRef(Record):
    path: str = Field(min_length=1, max_length=256)
    sha256: Hash


def json_payload(payload: bytes) -> bytes:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError("JSON_CONSTANT_INVALID")

    json.loads(payload, object_pairs_hook=unique, parse_constant=invalid_constant)
    return payload


def read_file(root: Path, reference: FileRef, limit: int) -> bytes:
    # Reject traversal, Windows drives/ADS, absolute paths, symlink/junction escape.
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", reference.path):
        raise ValueError("ARTIFACT_PATH_INVALID")
    relative = Path(reference.path)
    target = (root / relative).resolve()
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not target.is_relative_to(root.resolve())
    ):
        raise ValueError("ARTIFACT_PATH_INVALID")
    with target.open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit or hashlib.sha256(payload).hexdigest() != reference.sha256:
        raise ValueError("ARTIFACT_HASH_OR_SIZE_INVALID")
    return payload


class Receipt(Record):
    version: Literal["b03-google-receipt-1"]
    origin: Literal["REAL_GOOGLE_STT"]
    operator: Identifier
    reviewed_at: datetime
    executed_at: datetime
    evidence_record: Identifier
    raw_sha256: Hash
    response_sha256: Hash
    config_sha256: Hash
    binding_sha256: Hash
    sdk_version: Identifier
    api_version: Literal["v2"]
    provider_calls: Literal[1]
    attempted_audio_ms: int = Field(gt=0, le=60000)
    latency_ms: int = Field(ge=0)
    real_execution_verified: Literal[True]

    @model_validator(mode="after")
    def dates(self) -> Self:
        for date in (self.executed_at, self.reviewed_at):
            offset = date.utcoffset()
            if offset is None or offset.total_seconds() != 0:
                raise ValueError("RECEIPT_DATE_INVALID")
        if self.executed_at > self.reviewed_at:
            raise ValueError("RECEIPT_DATE_INVALID")
        return self


class Entry(Record):
    label: FileRef
    raw: FileRef
    binding: FileRef
    receipt: FileRef
    source_audio: FileRef
    chunk_audio: FileRef


class Bundle(Record):
    version: Literal["b03-scoring-bundle-1"]
    normalization: Literal["casefold-whitespace-preserve-punctuation-1"]
    protocol_frozen_at: datetime
    protocol_reviewers: tuple[Identifier, ...] = Field(min_length=2, max_length=8)
    protocol_record: Identifier
    entries: tuple[Entry, ...] = Field(min_length=2, max_length=64)


def load_entry(root: Path, entry: Entry) -> tuple[Label, Prediction, Receipt]:
    # Lazy, offline imports: provider code never imports evaluator truth.
    from flowlens.analysis.transcript_records import RawTranscript
    from flowlens.providers.stt.models import AuthorizedChunk

    label = Label.model_validate_json(json_payload(read_file(root, entry.label, 262144)))
    if label.purpose != "WAVEFORM_AUDITED":
        raise ValueError("LABEL_NOT_AUDITED")
    raw = RawTranscript.model_validate_json(
        json_payload(read_file(root, entry.raw, 8 * 1024 * 1024))
    )
    binding = AuthorizedChunk.model_validate_json(
        json_payload(read_file(root, entry.binding, 524288))
    )
    receipt = Receipt.model_validate_json(json_payload(read_file(root, entry.receipt, 16384)))
    audio = read_file(root, entry.chunk_audio, 9_999_999)
    read_file(root, entry.source_audio, 32 * 1024 * 1024)
    validate_output(label, raw, binding, receipt, entry, audio)
    return label, prediction_from_raw(raw), receipt


def validate_output(
    label: Label,
    raw: RawTranscript,
    binding: AuthorizedChunk,
    receipt: Receipt,
    entry: Entry,
    audio: bytes,
) -> None:
    """Consistency only; usable with TEST_ONLY units, never grants real origin."""
    from flowlens.providers.stt.models import STTConfig
    from flowlens.providers.stt.provenance import validate_raw

    config = STTConfig.model_validate_json(raw.config_json)
    receipt_offset = receipt.reviewed_at.utcoffset()
    if (
        label.source_sha256 != raw.source_hash
        or label.source_sha256 != entry.source_audio.sha256
        or label.audio_sha256 != raw.chunk_hash
        or label.audio_sha256 != entry.chunk_audio.sha256
        or label.source_id != raw.source_id
        or label.channel != raw.channel
        or (label.source_range.start_ns, label.source_range.end_ns)
        != (raw.source_range.start_ns, raw.source_range.end_ns)
        or label.session != str(raw.session_id)
        or receipt.raw_sha256 != entry.raw.sha256
        or receipt.response_sha256 != raw.response_hash
        or receipt.binding_sha256 != entry.binding.sha256
        or receipt.config_sha256 != config.digest()
        or receipt.sdk_version != raw.sdk_version
        or receipt.attempted_audio_ms
        != math.ceil((raw.source_range.end_ns - raw.source_range.start_ns) / 1_000_000)
        or receipt_offset is None
        or receipt_offset.total_seconds() != 0
    ):
        raise ValueError("OUTPUT_PROVENANCE_INVALID")
    validate_raw(config, binding, audio, raw)


def prediction_from_raw(raw: RawTranscript) -> Prediction:
    words: list[Span] = []
    segments: list[Span] = []
    texts: list[str] = []
    for hypothesis in raw.hypotheses:
        if hypothesis.alternative_index != 0:
            continue
        texts.append(hypothesis.text)
        for word in hypothesis.words:
            words.append(
                Span(
                    text=word.text,
                    range=None
                    if word.source is None
                    else Range(start_ns=word.source.start_ns, end_ns=word.source.end_ns),
                    ambiguity="CLEAR",
                    alternatives=(),
                    clipped=False,
                )
            )
        # A result end offset alone does not supply a segment start. Missing is explicit.
        interval = None
        if hypothesis.words and all(w.source is not None for w in hypothesis.words):
            first, last = hypothesis.words[0].source, hypothesis.words[-1].source
            if first is None or last is None:
                raise ValueError("SEGMENT_ALIGNMENT_INVALID")
            interval = Range(start_ns=first.start_ns, end_ns=last.end_ns)
        segments.append(
            Span(
                text=hypothesis.text,
                range=interval,
                ambiguity="CLEAR",
                alternatives=(),
                clipped=False,
            )
        )
    return Prediction(
        transcript=" ".join(texts),
        words=tuple(words),
        segments=tuple(segments),
        unknown_session_clock=raw.session_range is None,
    )


def validate_splits(labels: list[Label]) -> None:
    """Also usable on TEST_ONLY metadata; does not grant audit/benchmark eligibility."""
    splits: dict[tuple[str, str], str] = {}
    seen: set[str] = set()
    coverage: dict[str, set[str]] = {"TUNING": set(), "HELD_OUT": set()}
    for label in labels:
        if label.case_id in seen:
            raise ValueError("DUPLICATE_CASE")
        seen.add(label.case_id)
        identities = [
            ("session", label.session),
            ("family", label.family),
            ("source", label.source_sha256),
            ("audio", label.audio_sha256),
        ]
        identities.extend(("speaker", speaker) for speaker in label.speakers)
        for identity in identities:
            if splits.setdefault(identity, label.split) != label.split:
                raise ValueError("SPLIT_LEAKAGE")
        coverage[label.split].update(label.cohorts)
    if any(not COHORTS <= covered for covered in coverage.values()):
        raise ValueError("AUDITED_COHORT_COVERAGE_INCOMPLETE")


def validate_freeze(frozen_at: datetime, adjudicated_at: datetime, executed_at: datetime) -> None:
    if executed_at < frozen_at or adjudicated_at > frozen_at:
        raise ValueError("UNFROZEN_CASE")


def benchmark(root: Path, bundle: Bundle) -> dict[str, object]:
    """Atomic validation: never emit partial metrics if any artifact is invalid."""
    offset = bundle.protocol_frozen_at.utcoffset()
    if len(set(bundle.protocol_reviewers)) < 2 or offset is None or offset.total_seconds() != 0:
        raise ValueError("PROTOCOL_NOT_FROZEN")
    loaded = [load_entry(root, entry) for entry in bundle.entries]
    validate_splits([label for label, _, _ in loaded])
    results: dict[str, list[dict[str, object]]] = {"TUNING": [], "HELD_OUT": []}
    for label, prediction, receipt in loaded:
        if label.purpose != "WAVEFORM_AUDITED":
            raise ValueError("LABEL_NOT_AUDITED")
        validate_freeze(bundle.protocol_frozen_at, label.adjudicated_at, receipt.executed_at)
        results[label.split].append(score(label, prediction))
    return {
        "status": "SCORED",
        "domain_status": "NOT_DOMAIN_VALIDATED",
        "unit": "B03_OFFLINE_CHUNK_BENCHMARK",
        "normalization": bundle.normalization,
        "metrics": results,
        "case_count": len(loaded),
    }
