"""TEST_ONLY arithmetic/loader inputs. No waveform gold or benchmark evidence."""

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from scripts.stt_scoring import (
    COHORTS,
    Bundle,
    Entry,
    FileRef,
    Label,
    Prediction,
    Range,
    Receipt,
    Review,
    Slot,
    Span,
    align,
    benchmark,
    json_payload,
    load_entry,
    prediction_from_raw,
    read_file,
    score,
    summary,
    timing,
    validate_freeze,
    validate_output,
    validate_splits,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 9, tzinfo=UTC)


def span(text, start=0, end=1_000_000_000, **changes):
    return Span(
        text=text,
        range=Range(start_ns=start, end_ns=end),
        ambiguity="CLEAR",
        alternatives=(),
        clipped=False,
    ).model_copy(update=changes)


def label(text="hold short runway two", **changes):
    words = tuple(
        span(word, i * 1_000_000_000, (i + 1) * 1_000_000_000)
        for i, word in enumerate(text.split())
    )
    data = dict(
        version="b03-waveform-label-1",
        purpose="TEST_ONLY",
        case_id="test-only",
        session=str(uuid4()),
        family="test-family",
        speakers=("test-speaker",),
        split="TUNING",
        source_sha256="a" * 64,
        audio_sha256="b" * 64,
        source_id=uuid4(),
        channel=0,
        source_range=Range(start_ns=0, end_ns=10_000_000_000),
        rights_record="TEST_ONLY",
        annotation_revision=1,
        transcript=text,
        words=words,
        segments=(span(text, 0, len(words) * 1_000_000_000),) if words else (),
        slots=(),
        cohorts=(),
        reviews=(),
        adjudicator="test-adjudicator",
        adjudicated_at=NOW,
        adjudication_record="TEST_ONLY",
        domain_status="NOT_DOMAIN_VALIDATED",
    )
    data.update(changes)
    return Label(**data)


def prediction(text, words=None, segments=None):
    return Prediction(
        transcript=text,
        words=tuple(span(w) for w in text.split()) if words is None else words,
        segments=(span(text),) if segments is None else segments,
        unknown_session_clock=True,
    )


def slot(kind="action", start=0, end=2, quote="hold short", **changes):
    return Slot(
        kind=kind,
        token_start=start,
        token_end=end,
        quote=quote,
        range=Range(start_ns=0, end_ns=2_000_000_000),
        ambiguity="CLEAR",
        alternatives=(),
    ).model_copy(update=changes)


@pytest.mark.parametrize(
    "reference,hypothesis,expected",
    [
        ("a b c", "a x c", (1, 0, 0, 3, 1 / 3)),
        ("a b c", "a c", (0, 1, 0, 3, 1 / 3)),
        ("a b", "a x b", (0, 0, 1, 2, 0.5)),
        ("a a b", "a b", (0, 1, 0, 3, 1 / 3)),
        ("", "a", (0, 0, 1, 0, None)),
        ("a", "", (0, 1, 0, 1, 1.0)),
        ("HOLD short", "hold SHORT", (0, 0, 0, 2, 0.0)),
        ("two", "2", (1, 0, 0, 1, 1.0)),
        ("hold.", "hold", (1, 0, 0, 1, 1.0)),
    ],
)
def test_test_only_wer_denominators(reference, hypothesis, expected):
    result = score(label(reference), prediction(hypothesis))
    assert result["purpose"] == "TEST_ONLY"
    wer = result["wer"]
    assert (
        tuple(
            wer[k] for k in ("substitutions", "deletions", "insertions", "reference_words", "value")
        )
        == expected
    )


def test_ambiguous_or_clipped_case_excluded_from_wer_not_treated_as_gold():
    words = (span("hold", ambiguity="AMBIGUOUS", alternatives=("go",)), span("short"))
    result = score(label("hold short", words=words), prediction("go short"))
    assert result["wer"]["value"] is None
    assert result["wer"]["reference_words"] == 0
    assert result["wer"]["excluded_reference_words"] == 2
    assert result["word_alignment"]["excluded_ambiguous_or_clipped"] == 1


@pytest.mark.parametrize(
    "text,errors",
    [
        ("hold short runway two", 0),
        ("hold runway two", 1),
        ("hold not short runway two", 1),
        ("hold long runway two", 1),
    ],
)
def test_critical_slot_deletion_insertion_substitution(text, errors):
    result = score(label(slots=(slot(),)), prediction(text))
    assert result["critical_slots"]["action"]["eligible"] == 1
    assert result["critical_slots"]["action"]["errors"] == errors


def test_condition_negation_ambiguity_have_separate_denominators():
    slots = (slot("condition"), slot("negation", ambiguity="AMBIGUOUS", alternatives=("not",)))
    result = score(label(slots=slots), prediction("hold short runway two"))
    assert result["critical_slots"]["condition"]["eligible"] == 1
    assert result["critical_slots"]["negation"] == {
        "eligible": 0,
        "errors": 0,
        "ambiguous": 1,
        "missing": 0,
        "not_evaluable": 0,
    }


def test_independent_start_end_errors_and_percentiles():
    reference = (span("hold", 100_000_000, 600_000_000), span("short", 700_000_000, 900_000_000))
    predicted = (span("hold", 150_000_000, 580_000_000), span("short", 600_000_000, 950_000_000))
    result = timing(reference, predicted)
    assert result["timed_matches"] == 2
    assert result["start"] == {"count": 2, "median_ms": 75.0, "p95_ms": 100.0, "max_ms": 100.0}
    assert result["end"] == {"count": 2, "median_ms": 35.0, "p95_ms": 50.0, "max_ms": 50.0}
    assert summary([]) == {"count": 0, "median_ms": None, "p95_ms": None, "max_ms": None}


def test_missing_offsets_and_unmatched_do_not_manufacture_alignment():
    result = timing((span("a"), span("b"), span("c")), (span("a", range=None), span("x")))
    assert result["text_matches"] == 1
    assert result["missing_prediction_timing"] == 1
    assert result["unmatched_reference"] == 2
    assert result["unmatched_prediction"] == 1
    assert result["timed_matches"] == 0
    assert result["start"]["median_ms"] is None


def test_segment_boundaries_are_scored_independently_and_clock_unknown_retained():
    ref = label("hold short", segments=(span("hold short", 0, 2_000_000_000),))
    pred = prediction(
        "hold short", words=(), segments=(span("hold short", 100_000_000, 1_900_000_000),)
    )
    result = score(ref, pred)
    assert result["word_alignment"]["unmatched_reference"] == 2
    assert result["segment_alignment"]["start"]["median_ms"] == 100
    assert result["unknown_session_clock"] is True


@pytest.mark.parametrize(
    "change",
    [
        {"source_sha256": "bad"},
        {"channel": 2},
        {"annotation_revision": 0},
        {"cohorts": ("invented",)},
        {"transcript": "changed"},
        {"source_range": Range(start_ns=0, end_ns=1)},
        {"slots": (slot(quote="go around"),)},
        {"slots": (slot(end=100),)},
        {"adjudicated_at": datetime(2026, 10, 9)},
        {"purpose": "WAVEFORM_AUDITED"},
    ],
)
def test_label_rejects_schema_scope_review_and_range_gaps(change):
    with pytest.raises(ValidationError):
        label(**change)


def test_no_clear_slot_over_ambiguous_word():
    with pytest.raises(ValidationError, match="SLOT_AMBIGUITY_INVALID"):
        label(
            "hold short", words=(span("hold", ambiguity="MISSING"), span("short")), slots=(slot(),)
        )


def test_review_requires_explicit_utc_and_waveform():
    with pytest.raises(ValidationError):
        Review(reviewer="test", reviewed_at=NOW.replace(tzinfo=None), waveform_listened=True)
    with pytest.raises(ValidationError):
        Review(reviewer="test", reviewed_at=NOW, waveform_listened=False)


def test_token_dp_is_bounded_and_repetition_tie_deterministic():
    with pytest.raises(ValueError, match="TOKEN_LIMIT"):
        align(["x"] * 513, [])
    assert align(["a", "a"], ["a"]) == [(0, None), (1, 0)]


def file_ref(tmp_path, payload, name="test-only.json"):
    (tmp_path / name).write_bytes(payload)
    return FileRef(path=name, sha256=hashlib.sha256(payload).hexdigest())


@pytest.mark.parametrize(
    "path",
    [
        "../outside",
        "/absolute",
        "C:/private",
        "a:secret",
        "https://example.com/file",
        "a\\..\\private",
    ],
)
def test_loader_rejects_path_escape_and_urls(tmp_path, path):
    with pytest.raises(ValueError, match="ARTIFACT_PATH_INVALID"):
        read_file(tmp_path, FileRef(path=path, sha256="a" * 64), 32)


def test_loader_bounded_bytes_and_hash(tmp_path):
    reference = file_ref(tmp_path, b"TEST_ONLY")
    assert read_file(tmp_path, reference, 9) == b"TEST_ONLY"
    with pytest.raises(ValueError, match="HASH_OR_SIZE"):
        read_file(tmp_path, reference, 8)
    with pytest.raises(ValueError, match="HASH_OR_SIZE"):
        read_file(tmp_path, reference.model_copy(update={"sha256": "a" * 64}), 32)


@pytest.mark.parametrize("payload", [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_duplicate_json_and_nonfinite_rejected(payload):
    with pytest.raises(ValueError):
        json_payload(payload)


def entry_with_test_label(tmp_path):
    reference = file_ref(tmp_path, label().model_dump_json().encode())
    absent = FileRef(path="absent.json", sha256="a" * 64)
    return Entry(
        label=reference,
        raw=absent,
        binding=absent,
        receipt=absent,
        source_audio=absent,
        chunk_audio=absent,
    )


def test_test_only_label_blocks_before_loading_output_or_audio(tmp_path):
    with pytest.raises(ValueError, match="LABEL_NOT_AUDITED"):
        load_entry(tmp_path, entry_with_test_label(tmp_path))


def test_benchmark_invalid_bundle_emits_no_partial_metrics(tmp_path):
    entry = entry_with_test_label(tmp_path)
    bundle = Bundle(
        version="b03-scoring-bundle-1",
        normalization="casefold-whitespace-preserve-punctuation-1",
        protocol_frozen_at=NOW,
        protocol_reviewers=("test1", "test2"),
        protocol_record="TEST_ONLY",
        entries=(entry, entry),
    )
    with pytest.raises(ValueError, match="LABEL_NOT_AUDITED"):
        benchmark(tmp_path, bundle)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(bundle.model_dump_json())
    run = subprocess.run(
        [sys.executable, "scripts/evaluation_stt.py", "--bundle", str(bundle_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    result = json.loads(run.stdout)
    assert result == {
        "status": "BLOCKED",
        "metrics": None,
        "blockers": ["SCORING_ARTIFACTS_INVALID"],
    }
    assert "absent" not in run.stdout and str(tmp_path) not in run.stdout


def test_mock_receipt_cannot_claim_real_provider():
    with pytest.raises(ValidationError):
        Receipt(
            version="b03-google-receipt-1",
            origin="MOCK",
            operator="test",
            reviewed_at=NOW,
            executed_at=NOW,
            evidence_record="TEST_ONLY",
            raw_sha256="a" * 64,
            response_sha256="b" * 64,
            config_sha256="c" * 64,
            binding_sha256="d" * 64,
            sdk_version="2.41.0",
            api_version="v2",
            provider_calls=1,
            attempted_audio_ms=1000,
            latency_ms=1,
            real_execution_verified=True,
        )


def test_runtime_import_does_not_load_scoring_or_truth():
    code = (
        "import sys; import flowlens.providers.stt.execution; import flowlens.bindings.stt; "
        "assert not any(m.startswith(('scripts.stt_scoring',"
        "'scripts.evaluation_stt','evaluation')) "
        "for m in sys.modules)"
    )
    subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, check=True, timeout=15
    )


def split_pair():
    first = label(cohorts=tuple(sorted(COHORTS)))
    second = label(
        case_id="held-out-test-only",
        family="other-family",
        speakers=("other-speaker",),
        source_sha256="c" * 64,
        audio_sha256="d" * 64,
        split="HELD_OUT",
        cohorts=tuple(sorted(COHORTS)),
    )
    return first, second


@pytest.mark.parametrize(
    "field", ["session", "family", "speakers", "source_sha256", "audio_sha256"]
)
def test_session_family_speaker_and_transformed_source_leakage(field):
    first, second = split_pair()
    second = second.model_copy(update={field: getattr(first, field)})
    with pytest.raises(ValueError, match="SPLIT_LEAKAGE"):
        validate_splits([first, second])


def test_split_coverage_duplicate_and_missing_held_out():
    first, second = split_pair()
    validate_splits([first, second])
    with pytest.raises(ValueError, match="DUPLICATE_CASE"):
        validate_splits([first, first])
    with pytest.raises(ValueError, match="COVERAGE_INCOMPLETE"):
        validate_splits([first])
    with pytest.raises(ValueError, match="COVERAGE_INCOMPLETE"):
        validate_splits([first, second.model_copy(update={"cohorts": ()})])


def mock_output_unit():
    """MOCK SDK and TEST_ONLY label/receipt IDs; no real-origin evidence or benchmark."""
    from flowlens.providers.stt.adapter import map_response
    from flowlens.testing.stt import mock_binding, mock_config, mock_response

    config = mock_config()
    binding, audio = mock_binding(config, offset_ms=None)
    raw = map_response(config, binding, mock_response())

    def ref(digest):
        return FileRef(path="TEST_ONLY", sha256=digest)

    entry = Entry(
        label=ref("a" * 64),
        raw=ref(hashlib.sha256(raw.model_dump_json().encode()).hexdigest()),
        binding=ref(hashlib.sha256(binding.model_dump_json().encode()).hexdigest()),
        receipt=ref("a" * 64),
        source_audio=ref(raw.source_hash),
        chunk_audio=ref(raw.chunk_hash),
    )
    # REAL_GOOGLE_STT is a schema field under test, not an assertion of actual execution.
    receipt = Receipt(
        version="b03-google-receipt-1",
        origin="REAL_GOOGLE_STT",
        operator="TEST_ONLY",
        reviewed_at=NOW,
        executed_at=NOW,
        evidence_record="TEST_ONLY",
        raw_sha256=entry.raw.sha256,
        response_sha256=raw.response_hash,
        config_sha256=raw.config_hash,
        binding_sha256=entry.binding.sha256,
        sdk_version=raw.sdk_version,
        api_version="v2",
        provider_calls=1,
        attempted_audio_ms=3000,
        latency_ms=1,
        real_execution_verified=True,
    )
    target = label(
        "hold",
        session=str(raw.session_id),
        source_id=raw.source_id,
        source_sha256=raw.source_hash,
        audio_sha256=raw.chunk_hash,
        source_range=Range(start_ns=raw.source_range.start_ns, end_ns=raw.source_range.end_ns),
        channel=raw.channel,
    )
    return target, raw, binding, receipt, entry, audio


def test_test_only_output_consistency_and_projection_are_not_benchmark():
    target, raw, binding, receipt, entry, audio = mock_output_unit()
    assert target.purpose == "TEST_ONLY"
    validate_output(target, raw, binding, receipt, entry, audio)
    predicted = prediction_from_raw(raw)
    assert predicted.unknown_session_clock is True
    assert predicted.words[0].range.start_ns == 100_000_000
    assert predicted.segments[0].range.end_ns == 500_000_000


@pytest.mark.parametrize(
    "field,value",
    [
        ("session", "wrong-session"),
        ("source_id", uuid4()),
        ("channel", 1),
        ("source_sha256", "d" * 64),
        ("audio_sha256", "e" * 64),
    ],
)
def test_output_label_scope_and_hash_mismatch(field, value):
    target, raw, binding, receipt, entry, audio = mock_output_unit()
    with pytest.raises(ValueError, match="OUTPUT_PROVENANCE_INVALID"):
        validate_output(
            target.model_copy(update={field: value}), raw, binding, receipt, entry, audio
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("raw_sha256", "d" * 64),
        ("response_sha256", "e" * 64),
        ("config_sha256", "f" * 64),
        ("binding_sha256", "a" * 64),
        ("sdk_version", "wrong-sdk"),
        ("attempted_audio_ms", 1),
    ],
)
def test_output_receipt_bindings_rejected(field, value):
    target, raw, binding, receipt, entry, audio = mock_output_unit()
    with pytest.raises(ValueError, match="OUTPUT_PROVENANCE_INVALID"):
        validate_output(
            target, raw, binding, receipt.model_copy(update={field: value}), entry, audio
        )


def test_output_sdk_reconstruction_detects_mutated_hypothesis():
    from flowlens.providers.stt.models import STTFailure

    target, raw, binding, receipt, entry, audio = mock_output_unit()
    changed = raw.model_copy(
        update={"hypotheses": (raw.hypotheses[0].model_copy(update={"text": "TEST_ONLY tamper"}),)}
    )
    with pytest.raises(STTFailure, match="STT_OUTPUT_INVALID"):
        validate_output(target, changed, binding, receipt, entry, audio)


@pytest.mark.parametrize(
    "review_days,execution_days,valid",
    [
        (-1, 1, True),
        (0, 0, True),
        (1, 2, False),
        (-2, -1, False),
    ],
)
def test_test_only_freeze_precedes_execution_and_follows_label_adjudication(
    review_days, execution_days, valid
):
    reviewed = NOW + timedelta(days=review_days)
    executed = NOW + timedelta(days=execution_days)
    if valid:
        validate_freeze(NOW, reviewed, executed)
    else:
        with pytest.raises(ValueError, match="UNFROZEN_CASE"):
            validate_freeze(NOW, reviewed, executed)
