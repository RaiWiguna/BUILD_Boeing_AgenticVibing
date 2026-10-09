"""Executable offline evaluator; external default stays BLOCKED with metrics=null."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError
from semantic_scoring import Bundle, score, strict_json, validate_raw_outputs


def read_bounded(path: Path) -> bytes:
    with path.open("rb") as stream:
        body = stream.read(8 * 1024 * 1024 + 1)
    if len(body) > 8 * 1024 * 1024:
        raise ValueError("INPUT_TOO_LARGE")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--test-only", action="store_true")
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--schema", action="store_true")
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(Bundle.model_json_schema(), indent=2))
        return 0
    blocked: dict[str, object] = {
        "status": "BLOCKED",
        "metrics": None,
        "thresholds": "UNSET",
        "acceptance_decision": None,
        "integrated_readiness": False,
        "blockers": ["AUDITED_SEMANTIC_BENCHMARK_PENDING", "GEMINI_EXTERNAL_ACCEPTANCE_PENDING"],
        "real_stt_calls": 0,
        "real_gemini_calls": 0,
        "real_smoke": "NOT_RUN",
    }
    if args.bundle is None:
        print(json.dumps(blocked))
        return 0
    try:
        bundle = Bundle.model_validate_json(json.dumps(strict_json(read_bounded(args.bundle))))
        if (bundle.purpose == "TEST_ONLY") != args.test_only:
            raise ValueError("MODE_MISMATCH")
        if not args.test_only:
            if args.raw_output is None:
                raise ValueError("ACQUIRED_RAW_OUTPUTS_REQUIRED")
            validate_raw_outputs(bundle, read_bounded(args.raw_output))
        report = score(bundle)
        if args.test_only:
            report["external_benchmark"] = blocked
        print(json.dumps(report, allow_nan=False))
        return 0
    except (OSError, ValueError, ValidationError):
        blocked["code"] = "BUNDLE_INVALID_OR_MODE_MISMATCH"
        print(json.dumps(blocked))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
