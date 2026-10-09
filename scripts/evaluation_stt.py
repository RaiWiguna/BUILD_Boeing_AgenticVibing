"""Evaluator-only readiness audit, never imported by runtime/provider/observer.

No metrics are emitted until audited waveform labels AND real outputs exist.
Planned cohorts are requirements, not claims of existing audio coverage.
"""

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

try:
    from scripts.stt_scoring import COHORTS, Bundle, benchmark, json_payload
except ModuleNotFoundError:  # Direct script entrypoint has scripts/ on sys.path.
    from stt_scoring import COHORTS, Bundle, benchmark, json_payload


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    family: str
    split: Literal["TUNING", "HELD_OUT"]
    audio_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    label_status: Literal["PLANNED", "TTS_NOT_GOLD", "WAVEFORM_AUDITED"]
    label_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    reviewers: list[str]
    pronunciation_audited: bool
    critical_slots_audited: bool
    alignment_audited: bool
    verified_cohorts: list[str]
    real_response_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal["b03-evaluation-1"]
    domain_status: Literal["NOT_DOMAIN_VALIDATED"]
    required_cohorts: list[str]
    cases: list[Case]


def audit(plan: Plan) -> dict[str, object]:
    blockers = set()
    families: dict[str, str] = {}
    seen: set[str] = set()
    audio_splits: dict[str, str] = {}
    verified: dict[str, set[str]] = {"TUNING": set(), "HELD_OUT": set()}
    if set(plan.required_cohorts) != COHORTS:
        blockers.add("COHORT_PLAN_INCOMPLETE")
    for case in plan.cases:
        if case.id in seen:
            blockers.add("DUPLICATE_CASE")
        seen.add(case.id)
        if families.setdefault(case.family, case.split) != case.split:
            blockers.add("FAMILY_SPLIT_LEAKAGE")
        if (
            case.audio_sha256
            and audio_splits.setdefault(case.audio_sha256, case.split) != case.split
        ):
            blockers.add("AUDIO_SPLIT_LEAKAGE")
        if (
            case.label_status != "WAVEFORM_AUDITED"
            or not case.audio_sha256
            or not case.label_sha256
            or len(set(case.reviewers)) < 2
            or not all(
                (case.pronunciation_audited, case.critical_slots_audited, case.alignment_audited)
            )
        ):
            blockers.add("AUDITED_LABELS_UNAVAILABLE")
        else:
            verified[case.split].update(case.verified_cohorts)
        if not case.real_response_sha256:
            blockers.add("REAL_OUTPUTS_UNAVAILABLE")
        if not set(case.verified_cohorts) <= COHORTS:
            blockers.add("UNKNOWN_COHORT")
    if not any(c.split == "HELD_OUT" for c in plan.cases):
        blockers.add("HELD_OUT_UNAVAILABLE")
    if any(not COHORTS <= cohort for cohort in verified.values()):
        blockers.add("AUDITED_COHORT_COVERAGE_INCOMPLETE")
    # Hash assertions alone are not verified label/output artifacts; downstream
    # scoring must load them, verify hashes, schema, reviewers and model provenance.
    blockers.add("SCORING_ARTIFACT_REVIEW_REQUIRED")
    return {
        "unit": "B03_EVALUATION_PREFLIGHT",
        "status": "BLOCKED",
        "blockers": sorted(blockers),
        "case_count": len(plan.cases),
        "domain_status": plan.domain_status,
        "metrics": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("evaluation/protocols/stt-plan.json"))
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    try:
        selected = args.bundle if args.bundle is not None else args.plan
        with selected.open("rb") as stream:
            payload = stream.read(262145)
        if len(payload) > 262144:
            raise ValueError("bounded plan")
        payload = json_payload(payload)
        if args.bundle is None:
            report = audit(Plan.model_validate_json(payload))
        else:
            report = benchmark(
                args.artifact_root or selected.parent, Bundle.model_validate_json(payload)
            )
    except Exception:
        report = {
            "status": "BLOCKED",
            "blockers": ["SCORING_ARTIFACTS_INVALID" if args.bundle else "PLAN_INVALID"],
            "metrics": None,
        }
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
