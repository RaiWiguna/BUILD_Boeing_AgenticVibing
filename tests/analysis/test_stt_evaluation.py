"""Evaluator preflight negatives; no evaluator data is supplied to providers."""

from pathlib import Path

from scripts.evaluation_stt import Plan, audit

PLAN = Path(__file__).resolve().parents[2] / "evaluation/protocols/stt-plan.json"


def test_tts_script_and_planned_held_out_never_produce_metrics():
    result = audit(Plan.model_validate_json(PLAN.read_bytes()))
    assert result["status"] == "BLOCKED" and result["metrics"] is None
    assert "AUDITED_LABELS_UNAVAILABLE" in result["blockers"]
    assert "REAL_OUTPUTS_UNAVAILABLE" in result["blockers"]
    assert "AUDITED_COHORT_COVERAGE_INCOMPLETE" in result["blockers"]


def test_family_and_identical_audio_split_leakage_rejected():
    plan = Plan.model_validate_json(PLAN.read_bytes())
    plan.cases[1] = plan.cases[0].model_copy(update={"id": "held-out", "split": "HELD_OUT"})
    result = audit(plan)
    assert "FAMILY_SPLIT_LEAKAGE" in result["blockers"]
    assert "AUDIO_SPLIT_LEAKAGE" in result["blockers"]
    assert result["metrics"] is None


def test_claimed_audit_hashes_require_artifact_review_before_scoring():
    plan = Plan.model_validate_json(PLAN.read_bytes())
    for case in plan.cases:
        case.label_status = "WAVEFORM_AUDITED"
        case.label_sha256 = "a" * 64
        case.real_response_sha256 = "b" * 64
        case.audio_sha256 = "c" * 64 if case.split == "HELD_OUT" else case.audio_sha256
        case.reviewers = ["reviewer-1", "reviewer-2"]
        case.pronunciation_audited = case.critical_slots_audited = case.alignment_audited = True
        case.verified_cohorts = plan.required_cohorts.copy()
    result = audit(plan)
    assert result["blockers"] == ["SCORING_ARTIFACT_REVIEW_REQUIRED"]
    assert result["metrics"] is None
