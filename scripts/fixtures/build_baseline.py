"""Rebuild deterministic non-sensitive fixture metadata; preserve checked-in speech waveform."""

import hashlib
import json
import wave
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]


def identifier(value: int) -> str:
    return str(UUID(int=value))


def write(path: str, value: object) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main() -> None:
    speech_path = ROOT / "tests/fixtures/audio/hold-short.wav"
    with wave.open(str(speech_path)) as wav:
        rate = wav.getframerate()
        channels = wav.getnchannels()
        duration = round(wav.getnframes() / rate * 1000)
    digest = hashlib.sha256(speech_path.read_bytes()).hexdigest()
    # Silence explicitly exercises no-speech later; not a speech-quality benchmark.
    with wave.open(str(ROOT / "tests/fixtures/audio/silence.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)
    scope = {"session_id": identifier(1), "analysis_run_id": identifier(2), "revision": 1}
    timed = {
        **scope,
        "event_time_ms": 100,
        "available_time_ms": 200,
        "recorded_at": "2026-10-08T00:00:00Z",
    }
    ctx = {
        "actor_id": identifier(3),
        "capabilities": ["read", "audio", "review", "analysis"],
        "session_id": identifier(1),
        "analysis_run_id": identifier(2),
        "input_revision": 1,
        "input_hash": digest,
        "as_of_ms": 20000,
        "mode": "AS_KNOWN",
        "request_id": identifier(4),
    }
    text = "Flow lens two one four, hold short of runway two seven."
    evidence = {
        **scope,
        "id": identifier(5),
        "kind": "TRANSCRIPT",
        "source_id": identifier(6),
        "segment_id": identifier(7),
        "start_ms": 0,
        "end_ms": duration,
        "quote": text,
        "span_start": 0,
        "span_end": len(text),
        "source_hash": digest,
    }
    transcript = {
        **timed,
        "id": identifier(7),
        "source_id": identifier(6),
        "start_ms": 0,
        "end_ms": duration,
        "channel": 0,
        "text": text,
        "speaker_id": None,
        "confidence": None,
        "quality": "AMBIGUOUS",
        "origin": "MOCK",
        "provider_profile_version": "MOCK-1",
        "supersedes_id": None,
        "reason": None,
        "evidence": [evidence],
    }

    def slot(value: str) -> dict[str, object]:
        return {
            "value": value,
            "quality": "SUPPORTED",
            "evidence_ids": [identifier(5)],
            "alternatives": [],
            "unknowns": [],
        }

    intent = {
        **timed,
        "id": identifier(8),
        "evidence": [evidence],
        "segment_ids": [identifier(7)],
        "speech_act": "INSTRUCTION",
        "role_candidate": "CONTROLLER",
        "entity_candidates": [identifier(9)],
        "actions": ["HOLD_SHORT"],
        "callsign": slot("FLN214"),
        "runway": slot("27"),
        "condition": None,
        "negation": None,
        "quality": "AMBIGUOUS",
        "alternatives": [],
        "unknowns": ["MOCK intent, not provider verified"],
    }
    finding = {
        **timed,
        "id": identifier(10),
        "evidence": [evidence],
        "category": "CRITICAL_SLOT_UNCERTAIN",
        "statement": "Check callsign attribution.",
        "priority": "NOTICE",
        "status": "OPEN",
        "entity_ids": [identifier(9)],
        "rule_version": "synthetic-1",
        "model_version": "MOCK",
        "quality": "AMBIGUOUS",
        "applicability": "LAB_ONLY",
        "unknowns": ["speaker identity"],
        "stale": False,
    }
    option = {
        **timed,
        "id": identifier(11),
        "evidence": [evidence],
        "as_of_ms": 20000,
        "statement": "Evaluator could inspect the original audio.",
        "rationale": "Speaker attribution is unknown.",
        "preconditions": ["Audio grant"],
        "unknowns": ["Speaker identity"],
        "consequences": ["Hypothesis: resolve attribution"],
        "applicability": "LAB_ONLY",
        "review_status": "UNREVIEWED",
        "model_version": "MOCK",
        "prompt_version": "mock-1",
        "input_hash": digest,
    }
    review = {
        **timed,
        "id": identifier(12),
        "evidence": [evidence],
        "target_id": identifier(10),
        "target_revision": 1,
        "actor_id": identifier(3),
        "expected_version": 1,
        "decision": "UNRESOLVED",
        "reason": "MOCK review pending audio inspection",
        "supersedes_id": None,
    }
    job = {
        **scope,
        "job_id": identifier(13),
        "attempt_id": identifier(14),
        "lease_id": identifier(15),
        "input_hash": digest,
        "config_hash": "a" * 64,
        "output_hash": "c" * 64,
        "status": "COMPLETE",
        "outputs": [intent],
        "evidence": [evidence],
        "usage": {
            "audio_ms": duration,
            "input_tokens": None,
            "output_tokens": None,
            "cost_microunits": None,
            "latency_ms": 0,
        },
        "failure_code": None,
    }
    manifest = {
        "id": identifier(6),
        "session_id": identifier(1),
        "source_kind": "SYNTHETIC",
        "source_label": "Synthetic TTS / NOT_DOMAIN_VALIDATED",
        "source_hash": digest,
        "revision": 1,
        "permissions": {
            "local": True,
            "cloud": True,
            "export": True,
            "audio_export": True,
            "basis": "Project-authored fictional TTS fixture",
            "retention_days": 30,
        },
        "clock": {"offset_ms": 0, "uncertainty_ms": 0, "timezone": "UTC"},
        "coverage": {
            "audio": True,
            "tracks": False,
            "vehicles": None,
            "speaker_identity": None,
            "quality": "AMBIGUOUS",
            "gaps": [],
        },
        "units": "m",
        "coordinate_system": "FICTIONAL_LOCAL_XY",
        "layout_version": None,
        "domain_validation": "NOT_DOMAIN_VALIDATED",
        "assets": [
            {
                "id": identifier(16),
                "sha256": digest,
                "duration_ms": duration,
                "channels": channels,
                "sample_rate_hz": rate,
                "media_type": "audio/wav",
                "fixture_path": "tests/fixtures/audio/hold-short.wav",
            }
        ],
    }
    events = [
        {
            **timed,
            "id": identifier(20),
            "source_id": identifier(6),
            "source_event_id": "instruction-1",
            "analysis_run_id": None,
            "kind": "INSTRUCTION",
            "entity_id": identifier(9),
            "source_hash": digest,
            "quality": "SUPPORTED",
            "statement": "Synthetic source instruction",
        }
    ]
    events += [
        {
            **events[0],
            "id": identifier(21),
            "source_event_id": "later-available",
            "event_time_ms": 300,
            "available_time_ms": 40000,
        },
        {
            **events[0],
            "id": identifier(22),
            "source_event_id": "unknown-availability",
            "event_time_ms": 500,
            "available_time_ms": None,
        },
    ]
    track = {
        **events[0],
        "id": identifier(23),
        "source_event_id": "track-1",
        "kind": "TRACK",
        "x_m": 0.0,
        "y_m": 0.0,
        "heading_deg": 0.0,
        "speed_mps": 0.0,
        "length_m": 20.0,
        "width_m": 4.0,
        "age_ms": 0,
        "layout_version": "fictional-1",
    }
    for name, value in {
        "context": ctx,
        "manifest": manifest,
        "transcript": transcript,
        "intent": intent,
        "finding": finding,
        "option": option,
        "review": review,
        "job_result": job,
        "events": events,
        "track": track,
    }.items():
        write(f"contracts/examples/{name}.json", value)
    import copy

    cases = {
        "negative_time": ("transcript", transcript, {"start_ms": -1}),
        "invalid_enum": ("intent", intent, {"speech_act": "EXECUTE"}),
        "extra_command": ("option", option, {"command": "send-clearance"}),
        "empty_unknown": ("intent", intent, {"unknowns": [""]}),
        "invalid_range": ("transcript", transcript, {"end_ms": 0}),
        "invalid_hash": ("manifest", manifest, {"source_hash": "invalid"}),
        "nonfinite": ("track", track, {"speed_mps": float("inf")}),
    }
    for name, (model, payload, update) in cases.items():
        value = {"model": model, "payload": {**payload, **update}}
        if name == "nonfinite":
            # JSON standard cannot represent infinity: use a valid JSON string, also invalid number.
            value["payload"]["speed_mps"] = "Infinity"
        write(f"contracts/examples/invalid/{name}.json", value)
    wrong = copy.deepcopy(intent)
    wrong["evidence"][0]["session_id"] = identifier(99)
    write("contracts/examples/invalid/wrong_scope.json", {"model": "intent", "payload": wrong})
    write("tests/fixtures/manifests/synthetic-audio.json", manifest)
    write("tests/fixtures/events/availability.json", events)
    write("tests/fixtures/events/track.json", track)
    write(
        "tests/fixtures/layouts/fictional-runway.json",
        {
            "version": "fictional-1",
            "units": "m",
            "coordinates": "FICTIONAL_LOCAL_XY",
            "runway_polygon": [[-100.0, -10.0], [100.0, -10.0], [100.0, 10.0], [-100.0, 10.0]],
            "hold_line": [[-30.0, -20.0], [-30.0, 20.0]],
            "protection_margin_m": 5.0,
        },
    )
    write(
        "evaluation/fixtures/oracles/baseline.json",
        {
            "oracle_version": "independent-1",
            "method": "Hand-derived rectangle/time examples",
            "cases": [
                {
                    "id": "footprint-overlap",
                    "center_xy": [0, 0],
                    "size_xy": [20, 4],
                    "expected_occupied": True,
                },
                {
                    "id": "center-outside-footprint-overlap",
                    "center_xy": [105, 0],
                    "size_xy": [20, 4],
                    "expected_occupied": True,
                },
                {
                    "id": "fully-outside",
                    "center_xy": [120, 0],
                    "size_xy": [20, 4],
                    "expected_occupied": False,
                },
                {
                    "id": "time-overlap",
                    "interval_a_ms": [100, 300],
                    "interval_b_ms": [200, 400],
                    "expected_overlap_ms": 100,
                },
            ],
        },
    )
    write(
        "evaluation/fixtures/labels/baseline.json",
        {
            "label_version": "baseline-1",
            "status": "NOT_GOLD_NOT_DOMAIN_VALIDATED",
            "waveform": "tests/fixtures/audio/hold-short.wav",
            "pronunciation_audit": "PENDING",
            "script_intention": (
                "Flow lens two one four, hold short of runway two seven. "
                "Holding short of runway two seven, Flow lens two one four."
            ),
            "expected_semantics_from_script": {
                "callsign": "FLN214",
                "runway": "27",
                "action": "HOLD_SHORT",
            },
            "split": "tuning",
            "speaker": "macOS Samantha TTS",
            "not_for_provider_context": True,
        },
    )


if __name__ == "__main__":
    main()
