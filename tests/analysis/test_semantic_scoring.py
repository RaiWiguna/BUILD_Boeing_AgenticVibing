"""TEST_ONLY independent arithmetic oracle, validation and CLI isolation."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.semantic_scoring import (
    Bundle,
    Prediction,
    prediction_digest,
    score,
    strict_json,
    validate_raw_outputs,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "evaluation/fixtures/semantic-test-only.json"


def data():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def bind(body):
    predictions = tuple(Prediction.model_validate_json(json.dumps(p)) for p in body["predictions"])
    body["provenance"]["predictions_sha256"] = prediction_digest(predictions)
    return body


def bundle(body):
    return Bundle.model_validate_json(json.dumps(bind(body)))


def test_independent_count_oracle():
    result = score(bundle(data()))
    metrics = result["metrics"]
    # Six independent tabulated loop cases: three attempted closures, one premature,
    # one false closure, one missing; only one closure is correct with support.
    loops = metrics["TUNING/open_loop"]
    assert loops["exact_accuracy"] == 2 / 4
    assert loops["closure_precision"] == 1 / 3
    assert loops["counts"]["premature_closures"] == 1
    assert loops["counts"]["false_closures"] == 1
    assert loops["counts"]["missing"] == 1
    assert loops["counts"]["unassessable_answers"] == 1
    pair = metrics["TUNING/association"]
    assert pair["wrong_pair_rate"] == 1 / 2
    assert pair["exact_accuracy"] == 1 / 3  # missing output is in the known denominator
    assert pair["counts"]["ambiguity_abstentions"] == 1
    assert pair["counts"]["unassessable_answers"] == 1
    findings = metrics["TUNING/finding"]
    assert findings["finding_precision"] == 2 / 3
    assert findings["finding_recall"] == 2 / 3
    assert findings["supported_finding_precision"] == 1 / 3
    assert metrics["TUNING/brief_relevance"]["reviewer_relevance"] == 1 / 2
    assert metrics["TUNING/option_relevance"]["reviewer_relevance"] == 0
    assert result["acceptance_decision"] is None and result["thresholds"] == "UNSET"
    for task in (
        "speech_act",
        "callsign",
        "runway",
        "action",
        "negation",
        "condition",
        "correction",
        "cancellation",
    ):
        assert metrics[f"TUNING/{task}"]["exact_accuracy"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_label",
        "duplicate_prediction",
        "duplicate_evidence",
        "extra_prediction",
        "scope",
        "evidence_scope",
        "unknown_evidence",
        "unavailable_evidence",
        "future_evidence",
        "relevance_binding",
        "missing_review",
        "duplicate_reviewer",
        "closure_time",
        "future_closure",
        "invalid_label",
        "nonfinite",
        "coerced_revision",
        "extra_field",
        "naive_date",
        "hash",
        "missing_id",
        "fake_audit",
        "real_test_only",
    ],
)
def test_invalid_inputs_fail_closed(mutation):
    body = data()
    a, p = body["annotations"][0], body["predictions"][0]
    if mutation == "duplicate_label":
        body["annotations"].append(copy.deepcopy(a))
    elif mutation == "duplicate_prediction":
        body["predictions"].append(copy.deepcopy(p))
    elif mutation == "duplicate_evidence":
        body["evidence"].append(copy.deepcopy(body["evidence"][0]))
    elif mutation == "extra_prediction":
        p["id"] = "missing-label"
    elif mutation == "scope":
        p["scope"]["run"] = "other"
    elif mutation == "evidence_scope":
        body["evidence"][0]["scope"]["run"] = "other"
    elif mutation == "unknown_evidence":
        p["evidence_ids"] = ["not-in-inventory"]
    elif mutation == "unavailable_evidence":
        body["evidence"][0]["available_ms"] = None
    elif mutation == "future_evidence":
        body["evidence"][0]["available_ms"] = 20000
    elif mutation == "relevance_binding":
        next(a for a in body["annotations"] if a["task"] == "brief_relevance")["output_sha256"] = (
            "f" * 64
        )
    elif mutation == "missing_review":
        next(a for a in body["annotations"] if a["task"] == "brief_relevance")["reviews"] = []
    elif mutation == "duplicate_reviewer":
        r = next(a for a in body["annotations"] if a["task"] == "brief_relevance")
        r["reviews"] *= 2
    elif mutation == "closure_time":
        next(p for p in body["predictions"] if p["value"] == "CLOSED")["closed_at_ms"] = None
    elif mutation == "future_closure":
        next(p for p in body["predictions"] if p["value"] == "CLOSED")["closed_at_ms"] = 20000
    elif mutation == "invalid_label":
        a["expected"] = "UNRECOGNIZED_ACT"
    elif mutation == "nonfinite":
        a["scope"]["as_of_ms"] = float("nan")
    elif mutation == "coerced_revision":
        a["scope"]["revision"] = "1"
    elif mutation == "extra_field":
        a["hidden_truth"] = True
    elif mutation == "naive_date":
        body["provenance"]["executed_at"] = "2026-10-09T00:00:00"
    elif mutation == "hash":
        body["provenance"]["raw_output_sha256"] = "bad"
    elif mutation == "missing_id":
        del a["id"]
    elif mutation == "fake_audit":
        body["purpose"] = "AUDITED"
    elif mutation == "real_test_only":
        body["provenance"]["profile"] = "GOOGLE"
    with pytest.raises((ValidationError, ValueError)):
        bundle(body)


@pytest.mark.parametrize(
    "identity", ["session", "family", "speakers", "source_sha256", "input_sha256"]
)
def test_split_leakage(identity):
    body = data()
    a = copy.deepcopy(body["annotations"][0])
    a.update(id="held-out", acceptable_evidence=[], required_evidence=[])
    old = a["scope"]
    a["scope"] = dict(
        old,
        session="new",
        family="new",
        speakers=["new"],
        source_sha256="e" * 64,
        input_sha256="f" * 64,
        split="HELD_OUT",
    )
    a["scope"][identity] = old[identity]
    body["annotations"].append(a)
    with pytest.raises(ValidationError, match="SPLIT_LEAKAGE"):
        bundle(body)


def test_empty_denominators_and_unknown_are_not_success():
    body = data()
    body["annotations"] = [dict(body["annotations"][0], label_status="UNKNOWN", expected=None)]
    body["predictions"] = []
    result = score(bundle(body))["metrics"]["TUNING/speech_act"]
    assert result["exact_accuracy"] is None
    assert result["wrong_pair_rate"] is None
    assert result["counts"]["label_unknown"] == 1


def test_prediction_hash_verified_without_rebinding():
    body = data()
    body["predictions"][0]["value"] = "REPORT"
    with pytest.raises(ValidationError, match="HASH_MISMATCH"):
        Bundle.model_validate_json(json.dumps(body))


def test_cli_mode_default_and_invalid_file(tmp_path):
    command = [sys.executable, str(ROOT / "scripts/evaluation_semantic.py")]
    default = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=True)
    blocked = json.loads(default.stdout)
    assert blocked["status"] == "BLOCKED" and blocked["metrics"] is None
    assert blocked["real_gemini_calls"] == 0
    external = subprocess.run(command + ["--bundle", str(EXAMPLE)], capture_output=True, text=True)
    assert external.returncode == 2 and json.loads(external.stdout)["metrics"] is None
    test_only = subprocess.run(
        command + ["--bundle", str(EXAMPLE), "--test-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(test_only.stdout)
    assert report["status"] == "TEST_ONLY_ARITHMETIC"
    assert report["external_benchmark"]["metrics"] is None
    invalid = tmp_path / "bad.json"
    invalid.write_text('{"private_payload": "DO_NOT_ECHO"}', encoding="utf-8")
    result = subprocess.run(command + ["--bundle", str(invalid)], capture_output=True, text=True)
    assert result.returncode == 2 and "DO_NOT_ECHO" not in result.stdout + result.stderr


@pytest.mark.parametrize("text", ['{"id":1,"id":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_json_duplicate_keys_and_nonfinite(text):
    with pytest.raises(ValueError):
        strict_json(text.encode())


def test_reviewer_rating_is_not_predicted_self_grade():
    body = data()
    for prediction in body["predictions"]:
        if "relevance" in prediction["id"]:
            prediction["value"] = "RELEVANT"  # self-grade cannot improve reviewer rating
    report = score(bundle(body))
    assert report["metrics"]["TUNING/brief_relevance"]["reviewer_relevance"] == 1 / 2
    assert report["metrics"]["TUNING/option_relevance"]["reviewer_relevance"] == 0


def test_wrong_relationship_and_missing_support_are_errors():
    body = data()
    next(p for p in body["predictions"] if p["id"] == "association-0")["relationship"] = "CANCELS"
    next(p for p in body["predictions"] if p["id"] == "open_loop-0")["evidence_ids"] = []
    metrics = score(bundle(body))["metrics"]
    assert metrics["TUNING/association"]["wrong_pair_rate"] == 1
    assert metrics["TUNING/open_loop"]["closure_precision"] == 0


def test_raw_artifact_binding_failures():
    b = bundle(data())
    with pytest.raises(ValueError, match="RAW_HASH_MISMATCH"):
        validate_raw_outputs(b, b'{"outputs":{}}')
    import hashlib

    body = b'{"outputs":{}}'
    changed = b.model_copy(
        update={
            "provenance": b.provenance.model_copy(
                update={
                    "raw_output_sha256": hashlib.sha256(body).hexdigest(),
                }
            )
        }
    )
    with pytest.raises(ValueError, match="RAW_IDS_MISMATCH"):
        validate_raw_outputs(changed, body)
