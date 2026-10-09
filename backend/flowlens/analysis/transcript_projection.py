"""Conservative exact-time overlap reconciliation and frozen DTO projection."""

import math
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid5

from pydantic import Field

from flowlens.analysis.transcript_records import Offset, RawTranscript
from flowlens.contracts.models import Contract, Evidence, TranscriptSegment


class WordReference(Contract):
    raw_id: UUID
    hypothesis_index: int
    word_index: int


class CanonicalWord(Contract):
    text: str = Field(repr=False)
    source: Offset | None
    channel: int
    references: tuple[WordReference, ...]
    boundary_quality: Literal["SINGLE", "EXACT_OVERLAP", "AMBIGUOUS"]


def deduplicate(records: tuple[RawTranscript, ...]) -> tuple[CanonicalWord, ...]:
    """Only exact text AND exact source timing inside genuine chunk overlap can merge.

    Different timings, unaligned words, and near matches are retained as ambiguous.
    This deliberately under-deduplicates jittered STT; no tolerance is calibrated yet.
    """
    result: list[CanonicalWord] = []
    owners: list[RawTranscript] = []
    active: list[int] = []
    comparisons = 0
    if len(records) > 4096:
        raise ValueError("Transcript reconciliation limit.")
    seen: set[UUID] = set()
    for raw in sorted(records, key=lambda r: (r.channel, r.source_range.start_ns, str(r.id))):
        raw = RawTranscript.model_validate_json(raw.model_dump_json())
        if raw.id in seen:
            raise ValueError("Duplicate raw record.")
        seen.add(raw.id)
        active = [
            i
            for i in active
            if owners[i].channel == raw.channel
            and owners[i].source_range.end_ns > raw.source_range.start_ns
        ]
        if len(result) + sum(len(h.words) for h in raw.hypotheses) > 65536:
            raise ValueError("Transcript reconciliation limit.")
        for h_index, hypothesis in enumerate(raw.hypotheses):
            if hypothesis.alternative_index != 0:
                continue
            for w_index, word in enumerate(hypothesis.words):
                reference = WordReference(
                    raw_id=raw.id, hypothesis_index=h_index, word_index=w_index
                )
                matches: list[int] = []
                ambiguous: list[int] = []
                for index in active:
                    comparisons += 1
                    if comparisons > 1_000_000:
                        raise ValueError("Transcript reconciliation work limit.")
                    prior, owner = result[index], owners[index]
                    same = (
                        owner.session_id,
                        owner.analysis_run_id,
                        owner.revision,
                        owner.input_hash,
                        owner.config_hash,
                        owner.source_id,
                        owner.source_hash,
                        owner.channel,
                        owner.coverage_segment,
                    ) == (
                        raw.session_id,
                        raw.analysis_run_id,
                        raw.revision,
                        raw.input_hash,
                        raw.config_hash,
                        raw.source_id,
                        raw.source_hash,
                        raw.channel,
                        raw.coverage_segment,
                    )
                    a, b = (
                        max(owner.source_range.start_ns, raw.source_range.start_ns),
                        min(owner.source_range.end_ns, raw.source_range.end_ns),
                    )
                    if not same or owner.chunk_id == raw.chunk_id or a >= b:
                        continue
                    if (
                        word.source is not None
                        and prior.source is not None
                        and a <= word.source.start_ns < word.source.end_ns <= b
                        and a <= prior.source.start_ns < prior.source.end_ns <= b
                    ):
                        if word.text == prior.text and word.source == prior.source:
                            matches.append(index)
                        elif max(word.source.start_ns, prior.source.start_ns) < min(
                            word.source.end_ns, prior.source.end_ns
                        ):
                            ambiguous.append(index)
                    elif word.source is None or prior.source is None:
                        ambiguous.append(index)
                if len(matches) == 1 and not ambiguous:
                    index = matches[0]
                    prior = result[index]
                    result[index] = prior.model_copy(
                        update={
                            "references": (*prior.references, reference),
                            "boundary_quality": "EXACT_OVERLAP",
                        }
                    )
                    continue
                for index in [*matches, *ambiguous]:
                    result[index] = result[index].model_copy(
                        update={"boundary_quality": "AMBIGUOUS"}
                    )
                result.append(
                    CanonicalWord(
                        text=word.text,
                        source=word.source,
                        channel=raw.channel,
                        references=(reference,),
                        boundary_quality="AMBIGUOUS" if matches or ambiguous else "SINGLE",
                    )
                )
                owners.append(raw)
                active.append(len(result) - 1)
    return tuple(result)


def project(
    raw: RawTranscript, *, recorded_at: datetime, origin: Literal["GOOGLE_STT", "MOCK"]
) -> tuple[TranscriptSegment, ...]:
    """Project original hypotheses only when the session clock exists.

    Wire ranges are outward millisecond enclosures; missing word alignment uses
    explicitly marked CHUNK_RANGE, never synthesized word timestamps/availability.
    Canonical word view is separate; raw text/punctuation is never silently rewritten.
    """
    raw = RawTranscript.model_validate_json(raw.model_dump_json())
    if raw.session_range is None:
        return ()
    result: list[TranscriptSegment] = []
    for hypothesis in raw.hypotheses:
        if hypothesis.alternative_index != 0 or not hypothesis.text.strip():
            continue
        aligned = bool(hypothesis.words) and all(w.session is not None for w in hypothesis.words)
        ranges = [w.session for w in hypothesis.words if w.session is not None]
        start_ns = min(r.start_ns for r in ranges) if aligned else raw.session_range.start_ns
        end_ns = max(r.end_ns for r in ranges) if aligned else raw.session_range.end_ns
        start_ms, end_ms = start_ns // 1_000_000, math.ceil(end_ns / 1_000_000)
        identifier = uuid5(raw.id, f"result:{hypothesis.result_index}")
        evidence = Evidence(
            id=uuid5(identifier, "transcript-evidence"),
            session_id=raw.session_id,
            analysis_run_id=raw.analysis_run_id,
            revision=raw.revision,
            kind="TRANSCRIPT",
            source_id=raw.source_id,
            segment_id=identifier,
            start_ms=start_ms,
            end_ms=end_ms,
            quote=hypothesis.text,
            span_start=0,
            span_end=len(hypothesis.text),
            source_hash=raw.source_hash,
        )
        result.append(
            TranscriptSegment(
                id=identifier,
                session_id=raw.session_id,
                analysis_run_id=raw.analysis_run_id,
                revision=raw.revision,
                event_time_ms=start_ms,
                available_time_ms=None,
                recorded_at=recorded_at,
                source_id=raw.source_id,
                start_ms=start_ms,
                end_ms=end_ms,
                channel=raw.channel,
                text=hypothesis.text,
                speaker_id=None,
                confidence=hypothesis.confidence,
                quality="AMBIGUOUS",
                origin=origin,
                provider_profile_version=raw.profile_version,
                supersedes_id=None,
                reason="WORD_RANGE" if aligned else "CHUNK_RANGE_ALIGNMENT_UNKNOWN",
                evidence=[evidence],
            )
        )
    return tuple(result)
