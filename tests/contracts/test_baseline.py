"""Executable acceptance for frozen contracts, independent of A/B implementations."""

import importlib
import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def models():
    return importlib.import_module("flowlens.contracts.models")


def example(name):
    return json.loads((ROOT / "contracts/examples" / f"{name}.json").read_text())


def test_contract_version_is_explicit():
    assert importlib.import_module("flowlens").CONTRACT_VERSION == "1.0.0"


@pytest.mark.parametrize(
    "name", ["manifest", "transcript", "intent", "finding", "option", "review", "job_result"]
)
def test_valid_examples_round_trip(name):
    module = models()
    cls = module.EXAMPLE_MODELS[name]
    raw = json.dumps(example(name))
    obj = cls.model_validate_json(raw)
    assert cls.model_validate_json(obj.model_dump_json()) == obj


@pytest.mark.parametrize(
    "name",
    [
        "negative_time",
        "invalid_enum",
        "extra_command",
        "empty_unknown",
        "invalid_range",
        "wrong_scope",
        "invalid_hash",
        "nonfinite",
    ],
)
def test_invalid_examples_rejected(name):
    raw = example(f"invalid/{name}")
    with pytest.raises(ValidationError):
        models().EXAMPLE_MODELS[raw["model"]].model_validate_json(json.dumps(raw["payload"]))


def test_request_context_rejects_cross_scope_and_capability():
    m = models()
    context = m.RequestContext.model_validate_json(json.dumps(example("context")))
    errors = importlib.import_module("flowlens.core.errors")
    with pytest.raises(errors.ContractError, match="ACCESS_DENIED"):
        context.require("review", UUID("00000000-0000-0000-0000-000000000099"))
    with pytest.raises(errors.ContractError, match="ACCESS_DENIED"):
        context.require("truth", context.session_id)


def test_clock_mapping_keeps_unknown_alignment():
    m = models()
    known = m.ClockMapping(offset_ms=100, uncertainty_ms=5, timezone="UTC")
    assert known.to_session_ms(200) == 300
    unknown = m.ClockMapping(offset_ms=None, uncertainty_ms=None, timezone="UTC")
    assert unknown.to_session_ms(200) is None


def test_as_known_filters_future_and_unknown_availability():
    m = models()
    harness = importlib.import_module("flowlens.testing.harness")
    ctx = m.RequestContext.model_validate_json(json.dumps(example("context")))
    rows = [m.SourceEvent.model_validate_json(json.dumps(row)) for row in example("events")]
    reader = harness.FakePlatform(rows)
    assert [e.source_event_id for e in reader.read_events(ctx)] == ["instruction-1"]
    debrief = ctx.model_copy(update={"mode": "DEBRIEF"})
    assert len(reader.read_events(debrief)) == 3
    reader.revoke(ctx.actor_id)
    with pytest.raises(importlib.import_module("flowlens.core.errors").ContractError):
        reader.read_events(ctx)


def test_mock_adapter_not_permitted_in_production():
    comp = importlib.import_module("flowlens.core.modules")
    with pytest.raises(ValueError, match="MOCK"):
        comp.ModuleRegistry(profile="production").register(
            comp.ModuleRegistration(name="fake", mock=True)
        )


def test_configuration_is_fail_closed():
    config = importlib.import_module("flowlens.core.config")
    with pytest.raises(ValidationError):
        config.Settings(profile="production", api_workers=2)
    with pytest.raises(ValidationError):
        config.Settings(profile="production", api_workers=1)


def test_module_registration_rejects_version_and_duplicates():
    c = importlib.import_module("flowlens.core.modules")
    registry = c.ModuleRegistry(profile="test")
    registry.register(c.ModuleRegistration(name="analysis", mock=True))
    with pytest.raises(ValueError):
        registry.register(c.ModuleRegistration(name="analysis", mock=True))
    with pytest.raises(ValueError):
        registry.register(c.ModuleRegistration(name="old", contract_version="0.0.1"))


def test_safe_api_errors_do_not_echo_invalid_payload():
    from fastapi.testclient import TestClient

    app = importlib.import_module("flowlens.api.app").create_app(profile="test", track="A")
    with TestClient(app) as client:
        response = client.post("/_harness/validate/intent", json={"secret": "private-password"})
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_INPUT"
        assert "private-password" not in response.text
        assert client.get("/ready").json()["implementation"] == "BASELINE_ONLY"
        assert client.get("/openapi.json").status_code == 200


def test_schema_generation_matches_checked_in_files():
    gen = importlib.import_module("flowlens.contracts.generate")
    assert gen.generate(ROOT, check=True)


def test_fixture_hashes_and_clock_ranges():
    import hashlib
    import wave

    manifest = example("manifest")
    for asset in manifest["assets"]:
        path = ROOT / asset["fixture_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
        with wave.open(str(path)) as wav:
            assert wav.getnchannels() == asset["channels"]
            assert wav.getframerate() == asset["sample_rate_hz"]
            assert abs(wav.getnframes() / wav.getframerate() * 1000 - asset["duration_ms"]) <= 1


def test_nan_and_coercion_rejected_in_python():
    m = models()
    raw = example("track")
    track = m.Track.model_validate_json(json.dumps(raw))
    for update in ({"speed_mps": float("nan")}, {"speed_mps": float("inf")}, {"age_ms": "5"}):
        with pytest.raises(ValidationError):
            m.Track.model_validate({**track.model_dump(), **update})


def test_timezone_and_unknown_slot_semantics():
    m = models()
    raw = example("transcript")
    for stamp in ("2026-10-08T07:00:00+07:00", "2026-10-08T00:00:00"):
        with pytest.raises(ValidationError):
            m.TranscriptSegment.model_validate_json(json.dumps({**raw, "recorded_at": stamp}))
    with pytest.raises(ValidationError):
        m.CriticalSlot(value=None, quality="MISSING", evidence_ids=[], alternatives=[], unknowns=[])


def test_stream_type_requires_matching_payload():
    m = models()
    stream = {
        "session_id": example("context")["session_id"],
        "analysis_run_id": example("context")["analysis_run_id"],
        "sequence": 1,
        "type": "OPTION_READY",
        "recorded_at": "2026-10-08T00:00:00Z",
        "payload": example("review"),
    }
    with pytest.raises(ValidationError):
        m.StreamEvent.model_validate_json(json.dumps(stream))


def test_snapshot_rejects_cross_session_items():
    m = models()
    context = example("context")
    wrong = example("events")[0]
    wrong["session_id"] = "00000000-0000-0000-0000-000000000099"
    snapshot = {
        "session_id": context["session_id"],
        "analysis_run_id": context["analysis_run_id"],
        "revision": 1,
        "as_of_ms": 20000,
        "mode": "AS_KNOWN",
        "sequence": 0,
        "events": [wrong],
        "memory": [],
        "findings": [],
        "quality": "MISSING",
    }
    with pytest.raises(ValidationError):
        m.Snapshot.model_validate_json(json.dumps(snapshot))


@pytest.mark.parametrize(
    "code,status",
    [
        ("AUTH_REQUIRED", 401),
        ("VERSION_CONFLICT", 409),
        ("PROVIDER_UNAVAILABLE", 503),
        ("BUDGET_EXCEEDED", 429),
        ("INVALID_AI_OUTPUT", 422),
        ("EVIDENCE_UNAVAILABLE", 404),
    ],
)
def test_http_error_semantics_are_frozen(code, status):
    from fastapi.testclient import TestClient

    errors = importlib.import_module("flowlens.core.errors")
    app = importlib.import_module("flowlens.api.app").create_app(profile="test")

    @app.get("/_harness/failure")
    def failure():
        raise errors.ContractError(code)

    with TestClient(app) as client:
        response = client.get("/_harness/failure")
        assert response.status_code == status
        assert response.json()["code"] == code


def test_job_result_can_carry_open_loop_and_query_outputs():
    raw = example("job_result")
    common = {
        key: example("finding")[key]
        for key in (
            "session_id",
            "analysis_run_id",
            "revision",
            "event_time_ms",
            "available_time_ms",
            "recorded_at",
            "evidence",
        )
    }
    loop = {
        **common,
        "id": "00000000-0000-0000-0000-000000000080",
        "originating_id": example("intent")["id"],
        "entity_ids": [],
        "kind": "READBACK_EXPECTED",
        "status": "OPEN",
        "started_ms": 100,
        "expected_window_ms": None,
        "coverage_known": False,
        "closing_evidence_ids": [],
        "timer_profile_version": "lab-1",
    }
    query = {
        **common,
        "id": "00000000-0000-0000-0000-000000000081",
        "as_of_ms": 20000,
        "items": [],
        "labels": ["MOCK"],
        "model_version": "MOCK",
        "prompt_version": "mock-1",
        "question": "Which callsign was heard?",
        "status": "INSUFFICIENT_CONTEXT",
    }
    raw["outputs"] = [loop, query]
    parsed = models().JobResult.model_validate_json(json.dumps(raw))
    assert isinstance(parsed.outputs[0], models().OpenLoop)
    assert isinstance(parsed.outputs[1], models().QueryAnswer)


def test_job_result_derivative_artifact_scope_is_validated():
    raw = example("job_result")
    artifact = {
        "session_id": raw["session_id"],
        "analysis_run_id": raw["analysis_run_id"],
        "revision": 1,
        "id": "00000000-0000-0000-0000-000000000082",
        "kind": "AUDIO_DERIVATIVE",
        "sha256": "d" * 64,
        "size_bytes": 100,
        "source_asset_id": example("manifest")["assets"][0]["id"],
        "transform_version": "resample-1",
        "source_range": {"start_ms": 0, "end_ms": 100},
        "derivative_range": {"start_ms": 0, "end_ms": 100},
        "expires_at": None,
        "required_capability": "audio",
    }
    raw["artifacts"] = [artifact]
    assert len(models().JobResult.model_validate_json(json.dumps(raw)).artifacts) == 1
    artifact["session_id"] = "00000000-0000-0000-0000-000000000099"
    with pytest.raises(ValidationError):
        models().JobResult.model_validate_json(json.dumps(raw))
