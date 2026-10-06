#!/usr/bin/env python3
"""Run the explicit, loopback-only QA-04 mock HTTP/WS + Vite stack.

This launcher consumes only the public, authored F-COMM-01 and F-REPLAY-01
fixtures. It never imports or starts the production backend and never connects
to a provider, operational feed, or remote service.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
import uvicorn


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures"
SYNTHETIC_LABEL = "SYNTHETIC / NOT OPERATIONALLY VALIDATED"
FIXTURE_ID = "F-COMM-01"
SOURCE_FIXTURE_ID = "F-REPLAY-01"
SOURCE_SESSION_ID = "SYN-COMM-01"
ANALYSIS_ID = "AN-SYN-01"
LOOPBACK = "127.0.0.1"
EXPECTED_ASSIST_FILES = {
    "audio-asset.json", "transcript.json", "entities.json", "highlights.json",
    "options.json", "failure-variants.json", "authorization-cases.json",
    "review-cases.json", "stream-cases.json", "invalid-contract-cases.json",
}
EXPECTED_REPLAY_FILES = {
    "catalog-scenarios.json", "source-events.jsonl", "public-frames.json",
    "geometry-cases.json", "quality-time-cases.json",
}
FORBIDDEN_OPTION_KEYS = {
    "command", "clearance", "instruction_action", "control_action", "execute",
    "execution_payload",
}


class FixtureValidationError(ValueError):
    """The requested fixture/profile is not a valid public QA fixture."""


class StackStartupError(RuntimeError):
    """A local mock or Vite service could not start safely."""


@dataclass(frozen=True)
class FixtureProfile:
    fixture_id: str
    manifest: Mapping[str, Any]
    replay_manifest: Mapping[str, Any]
    replay_events: tuple[Mapping[str, Any], ...]
    public_frames: Mapping[str, Any]
    catalogue: Mapping[str, Any]
    audio_asset: Mapping[str, Any]
    transcript: Mapping[str, Any]
    highlights: Mapping[str, Any]
    options: Mapping[str, Any]
    failure_variants: Mapping[str, Any]
    stream_cases: Mapping[str, Any]
    exact_byte_mismatches: tuple[str, ...]
    files_read: tuple[Path, ...]


@dataclass(frozen=True)
class MockCredentials:
    operator_key: str
    operator_token: str
    source_read_token: str
    review_token: str


def _contained_file(base: Path, relative: str) -> Path:
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as error:
        raise FixtureValidationError("Fixture manifest references a path outside its public root") from error
    if not candidate.is_file():
        raise FixtureValidationError(f"Public fixture file is missing: {relative}")
    return candidate


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FixtureValidationError(f"Invalid public fixture JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise FixtureValidationError(f"Expected a JSON object in public fixture file: {path.name}")
    return value


def _normalise_crlf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _verify_fixture_files(
    base: Path,
    manifest: Mapping[str, Any],
    expected_files: set[str],
) -> tuple[dict[str, Path], tuple[str, ...]]:
    hashes = manifest.get("artifact_hashes")
    if not isinstance(hashes, dict) or set(hashes) != expected_files:
        raise FixtureValidationError("Public fixture manifest file list does not match the supported profile")

    paths: dict[str, Path] = {}
    mismatches: list[str] = []
    for name, expected_hash in hashes.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise FixtureValidationError("Fixture manifest may name files only within its public fixture directory")
        path = _contained_file(base, name)
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise FixtureValidationError(f"Could not read public fixture file: {name}") from error
        exact_digest = hashlib.sha256(raw).hexdigest()
        if exact_digest == expected_hash:
            paths[name] = path
            continue
        normalized_digest = hashlib.sha256(_normalise_crlf(raw)).hexdigest()
        if normalized_digest != expected_hash:
            raise FixtureValidationError(f"Public fixture hash does not match manifest: {name}")
        mismatches.append(name)
        paths[name] = path
    return paths, tuple(sorted(mismatches))


def _reject_executable_option_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_OPTION_KEYS:
                raise FixtureValidationError("Fixture option contains a forbidden execution field")
            _reject_executable_option_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_executable_option_fields(item)


def load_fixture(fixture_id: str, project_root: Path = ROOT) -> FixtureProfile:
    """Load and validate the allowlisted public fixture without probing private roots."""
    if fixture_id != FIXTURE_ID:
        raise FixtureValidationError(f"Unknown public fixture/profile: {fixture_id}")

    fixture_root = (project_root / "tests" / "fixtures").resolve()
    assist_root = _contained_file(fixture_root, "assist/manifest.json").parent
    replay_root = _contained_file(fixture_root, "replay/manifest.json").parent
    assist_manifest_path = _contained_file(assist_root, "manifest.json")
    replay_manifest_path = _contained_file(replay_root, "manifest.json")
    assist_manifest = _read_json(assist_manifest_path)
    replay_manifest = _read_json(replay_manifest_path)

    if assist_manifest.get("bundle_id") != FIXTURE_ID or assist_manifest.get("schema_version") != "assist-1":
        raise FixtureValidationError("F-COMM-01 must use the supported assist-1 profile")
    if assist_manifest.get("source_bundle_id") != SOURCE_FIXTURE_ID:
        raise FixtureValidationError("F-COMM-01 does not reference the supported public replay fixture")
    if assist_manifest.get("source_manifest") != "../replay/manifest.json":
        raise FixtureValidationError("F-COMM-01 source manifest is outside the public fixture profile")
    if replay_manifest.get("bundle_id") != SOURCE_FIXTURE_ID or replay_manifest.get("schema_version") != "replay-1":
        raise FixtureValidationError("F-REPLAY-01 must use the supported replay-1 profile")
    if assist_manifest.get("source_session_id") != SOURCE_SESSION_ID:
        raise FixtureValidationError("Unexpected public fixture source session")
    if replay_manifest.get("source_id") != "SRC-SYN-COMM-01":
        raise FixtureValidationError("F-REPLAY-01 does not use the expected public synthetic source identity")
    assist_privacy = assist_manifest.get("privacy")
    replay_privacy = replay_manifest.get("privacy")
    if (not isinstance(assist_privacy, dict)
            or assist_privacy.get("classification") != "PUBLIC_SYNTHETIC_FIXTURE"
            or assist_privacy.get("private_data_included") is not False
            or assist_privacy.get("private_truth_oracles_embedded") is not False):
        raise FixtureValidationError("F-COMM-01 privacy declaration is unsupported")
    if (not isinstance(replay_privacy, dict)
            or replay_privacy.get("classification") != "PUBLIC_SYNTHETIC_FIXTURE"
            or replay_privacy.get("private_data_included") is not False
            or replay_privacy.get("private_truth_oracles_embedded") is not False):
        raise FixtureValidationError("F-REPLAY-01 privacy declaration is unsupported")
    if assist_manifest.get("label") != SYNTHETIC_LABEL or replay_manifest.get("label") != SYNTHETIC_LABEL:
        raise FixtureValidationError("Selected fixture is not explicitly marked synthetic and unvalidated")
    if assist_manifest.get("transcript_fixture_kind") != "stub/mock":
        raise FixtureValidationError("F-COMM-01 transcript must remain explicitly identified as a stub/mock")
    if assist_manifest.get("audio_bytes_available") is not False:
        raise FixtureValidationError("F-COMM-01 does not contain public audio bytes")
    readiness = assist_manifest.get("provider_readiness")
    if not isinstance(readiness, dict) or readiness.get("status") != "unavailable":
        raise FixtureValidationError("F-COMM-01 must not claim provider availability")

    assist_paths, assist_mismatches = _verify_fixture_files(assist_root, assist_manifest, EXPECTED_ASSIST_FILES)
    replay_paths, replay_mismatches = _verify_fixture_files(replay_root, replay_manifest, EXPECTED_REPLAY_FILES)
    source_events_hash = replay_manifest.get("content_hash")
    if source_events_hash != replay_manifest.get("artifact_hashes", {}).get("source-events.jsonl"):
        raise FixtureValidationError("F-REPLAY-01 source event digest does not match its public artifact hash")
    if assist_manifest.get("source_events_sha256") != source_events_hash:
        raise FixtureValidationError("F-COMM-01 source event digest does not match F-REPLAY-01")

    replay_events: list[Mapping[str, Any]] = []
    try:
        for line in replay_paths["source-events.jsonl"].read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise FixtureValidationError("Source event rows must be JSON objects")
                replay_events.append(event)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FixtureValidationError("Invalid public replay event fixture") from error

    public_frames = _read_json(replay_paths["public-frames.json"])
    catalogue = _read_json(replay_paths["catalog-scenarios.json"])
    audio_asset = _read_json(assist_paths["audio-asset.json"])
    transcript = _read_json(assist_paths["transcript.json"])
    highlights = _read_json(assist_paths["highlights.json"])
    options = _read_json(assist_paths["options.json"])
    failure_variants = _read_json(assist_paths["failure-variants.json"])
    stream_cases = _read_json(assist_paths["stream-cases.json"])

    if public_frames.get("source_session_id") != assist_manifest.get("source_session_id"):
        raise FixtureValidationError("Public frame fixture source does not match F-COMM-01")
    for payload in (transcript, highlights, options, stream_cases):
        if payload.get("source_session_id") != SOURCE_SESSION_ID or payload.get("replay_analysis_id") != ANALYSIS_ID:
            if payload is stream_cases and payload.get("source_session_id") == SOURCE_SESSION_ID:
                continue
            raise FixtureValidationError("Assist fixture projection has an unexpected source or analysis identity")
    if options.get("label") != SYNTHETIC_LABEL:
        raise FixtureValidationError("Evaluator option fixture must retain the synthetic/unvalidated label")
    if failure_variants.get("label") != SYNTHETIC_LABEL or stream_cases.get("label") != SYNTHETIC_LABEL:
        raise FixtureValidationError("Failure and stream variants must retain the synthetic/unvalidated label")
    _reject_executable_option_fields(options.get("options", []))

    return FixtureProfile(
        fixture_id=FIXTURE_ID,
        manifest=assist_manifest,
        replay_manifest=replay_manifest,
        replay_events=tuple(replay_events),
        public_frames=public_frames,
        catalogue=catalogue,
        audio_asset=audio_asset,
        transcript=transcript,
        highlights=highlights,
        options=options,
        failure_variants=failure_variants,
        stream_cases=stream_cases,
        exact_byte_mismatches=tuple(sorted(set(assist_mismatches + replay_mismatches))),
        files_read=tuple(sorted(
            [assist_manifest_path, replay_manifest_path, *assist_paths.values(), *replay_paths.values()],
            key=str,
        )),
    )


def _scenario(profile: FixtureProfile) -> dict[str, Any]:
    scenarios = profile.catalogue.get("scenarios")
    if not isinstance(scenarios, list):
        raise FixtureValidationError("Public catalogue fixture has no scenario mapping")
    item = next((row for row in scenarios if isinstance(row, dict) and row.get("canonical_id") == "S06"), None)
    if item is None or item.get("source_catalog_id") != "hold_violation":
        raise FixtureValidationError("F-COMM-01 public catalogue mapping is incomplete")
    return {
        "id": item["source_catalog_id"],
        "title": item["canonical_name"],
        "objective": "Authored synthetic replay fixture; no domain or operational validation is represented.",
        "version": str(profile.manifest.get("fixture_version", "synthetic-fixture")),
        "duration_s": 120,
        "domain_review": "not_reviewed",
        "aircraft_count": 0,
        "vehicle_count": 1,
    }


def _public_events(profile: FixtureProfile) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in profile.replay_events:
        event = row.get("event")
        if not isinstance(event, dict):
            continue
        projected = dict(event)
        projected.setdefault("id", row.get("source_event_id"))
        projected.setdefault("ordinal", 0)
        projected.setdefault("sim_ms", event.get("received_ms", event.get("source_time", {}).get("value", 0)))
        projected.setdefault("message", "Synthetic source event; not operational data.")
        if "issuer" in projected:
            projected.setdefault("actor", projected["issuer"])
        events.append(projected)
    return sorted(events, key=lambda event: (int(event.get("ordinal", 0)), str(event.get("id", ""))))


def _frame_at(profile: FixtureProfile, requested_ms: int) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]], Mapping[str, Any]]:
    if not isinstance(requested_ms, int) or requested_ms < 0:
        raise HTTPException(422, "at_ms must be a nonnegative integer session time")
    rows = profile.public_frames.get("frames")
    if not isinstance(rows, list):
        raise FixtureValidationError("Public frame fixture has no frame rows")
    candidates = [row for row in rows if isinstance(row, dict) and int(row.get("frame_ms", 0)) <= requested_ms]
    selected = max(candidates, key=lambda row: int(row.get("frame_ms", 0))) if candidates else None
    frame_ms = int(selected.get("frame_ms", 0)) if selected else 0

    events = [event for event in _public_events(profile) if int(event.get("sim_ms", 0)) <= frame_ms]
    tracks: list[dict[str, Any]] = []
    clearances: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") == "TRACK" and isinstance(event.get("track"), dict):
            track = dict(event["track"])
            track["stale"] = frame_ms - int(track.get("observed_ms", frame_ms)) > 3000
            tracks.append(track)
        elif event.get("type") == "CLEARANCE":
            clearances.append({
                "id": str(event.get("id", "")),
                "target": str(event.get("target", "")),
                "instruction": str(event.get("instruction", "unknown")),
                "runway": str(event.get("runway", "27")),
                "issued_ms": int(event.get("sim_ms", 0)),
                "issuer": str(event.get("issuer", "scenario_fixture")),
                "status": "recorded_fixture_event",
                "readback": "not_supplied_by_public_fixture",
                "event_id": str(event.get("id", "")),
            })
    return frame_ms, tracks, clearances, profile.replay_manifest.get("layout", {})


def _api_snapshot(profile: FixtureProfile, session_id: str = SOURCE_SESSION_ID) -> dict[str, Any]:
    scenario = _scenario(profile)
    frame_ms, tracks, clearances, layout = _frame_at(profile, 74600)
    events = [event for event in _public_events(profile) if int(event.get("sim_ms", 0)) <= frame_ms]
    session_metadata = {
        "id": SOURCE_SESSION_ID,
        "scenario": scenario,
        "condition": "synthetic-fixture",
        "seed": 1,
        "config": {"analysis_status": "unavailable", "source_profile": "replay-1"},
        "engine_version": "qa04-mock-fixture-only",
        "config_version": "qa01-2026-10-06.1",
        "kind": "review",
        "created_utc": 0,
    }
    return {
        "session_id": session_id,
        "source_session_id": SOURCE_SESSION_ID,
        "kind": "review",
        "sequence": 1,
        "sim_ms": frame_ms,
        "playback_ms": frame_ms,
        "review_end_ms": frame_ms,
        "revision": 0,
        "status": "READY",
        "speed": 1,
        "metadata": session_metadata,
        "layout": {
            "id": str(layout.get("id", "synthetic-lab")),
            "version": str(layout.get("version", "1.0")),
            "name": "Synthetic local layout",
            "coordinate_system": "LOCAL_METRES",
            "physical_runway_id": str(layout.get("physical_runway_id", "RWY-09-27")),
            "runway": layout.get("runway", []),
            "protected_area": layout.get("protected_area", []),
            "taxiways": layout.get("taxiways", []),
            "hold_lines": layout.get("hold_lines", []),
            "directions": layout.get("directions", {}),
            "note": "Synthetic fixture geometry; not an airport or operational layout.",
        },
        "tracks": tracks,
        "clearances": clearances,
        "requests": [],
        "predictions": [],
        "runway": {
            "open": False,
            "state": "UNKNOWN",
            "data_quality": "unknown",
            "observed_occupants": [],
            "degraded_ids": [],
        },
        "alerts": [],
        "events": events,
        "acknowledgements": [],
        "assessments": [],
        "complexity": {},
        "error": None,
        "seat": {"role": "observer", "label": "Synthetic fixture viewer"},
        "server_sent_utc_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
    }


def _transcript_items(profile: FixtureProfile) -> list[dict[str, Any]]:
    asset = profile.audio_asset.get("asset", {})
    audio_start = int(asset.get("audio_start", 0)) if isinstance(asset, dict) else 0
    segments = profile.transcript.get("segments", [])
    if not isinstance(segments, list):
        return []
    result = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        item = dict(segment)
        item["revision"] = 1
        item["raw_text"] = segment.get("text", "")
        item["session_start_ms"] = audio_start + int(segment.get("start_ms", 0))
        result.append(item)
    return result


def _highlight_items(profile: FixtureProfile) -> list[dict[str, Any]]:
    rows = profile.highlights.get("highlights", [])
    result: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        result.append({
            "id": row["id"],
            "revision": 1,
            "category": row["category"],
            "review_priority": row["review_priority"],
            "statement": row["statement"],
            "transcript_segment_ids": row.get("transcript_segment_ids", []),
            "session_event_ids": row.get("session_event_ids", []),
            "uncertainty": "; ".join(str(value) for value in row.get("uncertainty", [])),
            "provider_version": row["provider_version"],
            "rule_version": row["rule_version"],
            "status": row["status"],
            "linked_alert_id": row.get("linked_alert_id"),
            "link_status": row.get("link_status"),
        })
    return result


def _option_items(profile: FixtureProfile) -> list[dict[str, Any]]:
    rows = profile.options.get("options", [])
    result: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        result.append({
            "id": row["id"],
            "replay_analysis_id": row["replay_analysis_id"],
            "revision": 1,
            "option_statement": row["option_statement"],
            "rationale": row["rationale"],
            "supporting_evidence_ids": row.get("supporting_evidence_ids", []),
            "preconditions": row.get("preconditions", []),
            "unknowns": row.get("unknowns", []),
            "source_version": row.get("source_version", "synthetic-fixture-1"),
            "model_version": row.get("model_version", "stub-mock-1"),
            "rule_version": row.get("rule_version", "reconcile-fixture-1"),
            "review_status": row.get("review_status", "unresolved"),
        })
    return result


def _analysis_projection(profile: FixtureProfile) -> dict[str, Any]:
    analysis = profile.manifest.get("analysis", {})
    versions = analysis.get("versions", {}) if isinstance(analysis, dict) else {}
    return {
        "id": ANALYSIS_ID,
        "source_session_id": SOURCE_SESSION_ID,
        "kind": "assist",
        "source_version": versions.get("source", "synthetic-fixture-1"),
        "model_version": versions.get("model", "stub-mock-1"),
        "rule_version": versions.get("rule", "reconcile-fixture-1"),
        "input_hash": None,
        "transcript_revision_basis": None,
        "window_start_ms": analysis.get("window_start_ms"),
        "window_end_ms": analysis.get("window_end_ms"),
        "status": "fixture_only",
    }


def _mock_jobs(profile: FixtureProfile) -> list[dict[str, Any]]:
    cases = profile.failure_variants.get("cases", [])
    jobs: list[dict[str, Any]] = []
    for case in cases if isinstance(cases, list) else []:
        if not isinstance(case, dict) or case.get("id") not in {"worker-timeout", "worker-cancelled-late-result"}:
            continue
        status = str(case.get("status", case.get("expected_job_state", "failed")))
        error = "provider_unavailable; synthetic failure variant only; no inference was run." if status == "failed" else None
        jobs.append({
            "id": case["job_id"], "asset_id": "AUD-SYN-01", "status": status,
            "provider": None, "model": None, "version": None, "language": None,
            "started_utc": None, "finished_utc": None, "error": error,
            "chunk_progress": None,
        })
    return jobs


def _same_time_event_variant(profile: FixtureProfile) -> dict[str, Any]:
    source_events = _public_events(profile)
    variant_ms = 74600
    events = []
    for ordinal, event in enumerate(source_events, start=1):
        item = dict(event)
        item.update({
            "id": f"MOCK-F-COMM-01-SAME-TIME-{ordinal:04d}",
            "source_event_id": event.get("id"),
            "sim_ms": variant_ms,
            "ordinal": ordinal,
            "message": "QA-04 same-time ordering variant; not a canonical source event.",
            "mock_variant_only": True,
        })
        events.append(item)
    return {
        "variant": "same-time-ordering",
        "source_session_id": SOURCE_SESSION_ID,
        "label": SYNTHETIC_LABEL,
        "variant_only": True,
        "events": events,
        "note": "Authored transport exercise only; F-REPLAY-01 source event bytes are unchanged.",
    }


def _auth_token(header: str | None) -> str:
    if not header or not header.startswith("Bearer "):
        return ""
    return header[7:].strip()


def mock_ws_headers() -> list[tuple[bytes, bytes]]:
    return [
        (b"x-flowlens-mode", b"fixture-mock"),
        (b"x-flowlens-data-label", SYNTHETIC_LABEL.encode("ascii")),
    ]


def _create_mock_app(profile: FixtureProfile, credentials: MockCredentials) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.fixture = profile
    app.state.credentials = credentials

    @app.middleware("http")
    async def label_mock_response(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-FlowLens-Mode"] = "fixture-mock"
        response.headers["X-FlowLens-Data-Label"] = SYNTHETIC_LABEL
        return response

    token_roles = {
        credentials.operator_token: "operator",
        credentials.source_read_token: "source_read",
        credentials.review_token: "evaluator",
    }

    def authorize(authorization: str | None, *, evaluator: bool = False) -> str:
        token = _auth_token(authorization)
        role = next((value for candidate, value in token_roles.items() if hmac.compare_digest(token, candidate)), None)
        if role is None:
            raise HTTPException(status_code=401, detail="Mock fixture credential is invalid or expired")
        if evaluator and role not in {"operator", "evaluator"}:
            raise HTTPException(status_code=403, detail="Evaluator replay capability is required")
        return role

    def ensure_source(session_id: str) -> None:
        if session_id != SOURCE_SESSION_ID:
            raise HTTPException(status_code=404, detail="Synthetic replay source not found")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok", "version": "qa04-mock-1", "mode": "fixture-mock",
            "single_writer": False, "label": SYNTHETIC_LABEL,
        }

    @app.get("/api/v1/scenarios")
    def scenarios() -> dict[str, Any]:
        return {"items": [_scenario(profile)]}

    @app.get("/api/v1/scenarios/{scenario_id}")
    def scenario(scenario_id: str) -> dict[str, Any]:
        value = _scenario(profile)
        if scenario_id != value["id"]:
            raise HTTPException(status_code=404, detail="Synthetic fixture scenario not found")
        return value

    @app.get("/api/v1/mock/variants")
    def mock_variants(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        stream_ids = [
            str(case.get("id")) for case in profile.stream_cases.get("cases", [])
            if isinstance(case, dict)
        ]
        return {
            "label": SYNTHETIC_LABEL,
            "fixture_id": FIXTURE_ID,
            "available": ["same-time-ordering", "failed-job", *stream_ids],
            "provider_availability": "unavailable",
        }

    @app.get("/api/v1/mock/variants/same-time-events")
    def same_time_events(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        return _same_time_event_variant(profile)

    @app.post("/api/v1/auth/operator")
    async def authenticate(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except Exception as error:
            raise HTTPException(status_code=422, detail="Expected a JSON mock credential request") from error
        supplied = body.get("key") if isinstance(body, dict) else None
        if not isinstance(supplied, str) or not hmac.compare_digest(supplied, credentials.operator_key):
            raise HTTPException(status_code=401, detail="Invalid per-run mock test credential")
        return {"token": credentials.operator_token, "expires_in_s": 3600}

    @app.get("/api/v1/sessions")
    def sessions(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        return {"items": [{
            "id": SOURCE_SESSION_ID, "status": "READY", "scenario": _scenario(profile),
            "condition": "synthetic-fixture", "seed": 1, "kind": "review", "created_utc": 0,
        }]}

    @app.post("/api/v1/sessions")
    async def create_session() -> None:
        raise HTTPException(status_code=409, detail="The fixture mock is read-only and cannot create sessions")

    @app.get("/api/v1/sessions/{session_id}")
    def session_metadata(session_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        return {
            "id": SOURCE_SESSION_ID, "status": "READY", "scenario": _scenario(profile),
            "condition": "synthetic-fixture", "seed": 1, "kind": "review", "created_utc": 0,
        }

    @app.post("/api/v1/sessions/{session_id}/reviews", status_code=201)
    def open_review(session_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization, evaluator=True)
        ensure_source(session_id)
        return {
            "id": "MOCK-REVIEW-SYN-COMM-01", "source_id": SOURCE_SESSION_ID,
            "token": credentials.review_token, "source_read_token": credentials.source_read_token,
        }

    @app.get("/api/v1/sessions/{session_id}/snapshot")
    def snapshot(session_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        return _api_snapshot(profile, session_id)

    @app.get("/api/v1/sessions/{session_id}/replay-source")
    def replay_source(session_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        replay = profile.replay_manifest
        analysis = profile.manifest.get("analysis", {})
        return {
            "source_session_id": SOURCE_SESSION_ID,
            "source_id": replay.get("source_id"),
            "bundle_id": SOURCE_FIXTURE_ID,
            "source_kind": "synthetic",
            "label": SYNTHETIC_LABEL,
            "fixture_version": replay.get("fixture_version"),
            "content_hash": replay.get("content_hash"),
            "timebase": replay.get("timebase"),
            "coverage": replay.get("coverage"),
            "layout": replay.get("layout"),
            "analyses": [{
                "id": ANALYSIS_ID, "kind": "assist", "status": "fixture_only",
                "versions": analysis.get("versions", {}),
                "window_start_ms": analysis.get("window_start_ms"),
                "window_end_ms": analysis.get("window_end_ms"),
            }],
        }

    @app.get("/api/v1/sessions/{session_id}/replay-frame")
    def replay_frame(
        session_id: str,
        at_ms: int,
        analysis_id: str | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        if analysis_id not in {None, ANALYSIS_ID}:
            raise HTTPException(status_code=404, detail="Synthetic fixture analysis not found")
        frame_ms, tracks, _, _ = _frame_at(profile, at_ms)
        source_row = next((row for row in profile.public_frames.get("frames", [])
                           if isinstance(row, dict) and int(row.get("frame_ms", -1)) == frame_ms), None)
        source_row = source_row or {}
        _, _, clearances, layout = _frame_at(profile, at_ms)
        source_events = [event for event in _public_events(profile) if int(event.get("sim_ms", 0)) <= frame_ms]
        return {
            "source_session_id": SOURCE_SESSION_ID,
            "requested_ms": at_ms,
            "frame_ms": frame_ms,
            "analysis_id": analysis_id,
            "state": {
                "layout": {
                    "id": str(layout.get("id", "synthetic-lab")),
                    "version": str(layout.get("version", "1.0")),
                    "coordinate_system": "LOCAL_METRES",
                    "physical_runway_id": str(layout.get("physical_runway_id", "RWY-09-27")),
                    "runway": layout.get("runway", []),
                    "protected_area": layout.get("protected_area", []),
                    "taxiways": layout.get("taxiways", []),
                    "hold_lines": layout.get("hold_lines", []),
                    "directions": layout.get("directions", {}),
                },
                "tracks": tracks,
                "clearances": clearances,
                "requests": [],
                "predictions": source_row.get("predictions"),
                "alerts": source_row.get("alerts"),
                "runway": {"state": "UNKNOWN", "data_quality": "unknown"},
                "events": source_events,
            },
            "tracks": tracks,
            "alerts": [],
            "quality": "unknown",
            "analysis_status": "unavailable",
            "analysis_id": analysis_id,
            "source_event_ids": source_row.get("source_event_ids", []),
            "predictions": source_row.get("predictions"),
            "alert_analysis": source_row.get("alerts"),
            "label": SYNTHETIC_LABEL,
        }

    @app.get("/api/v1/sessions/{session_id}/events")
    def events(
        session_id: str,
        cursor: int = 0,
        limit: int = 100,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        if cursor < 0 or limit < 1 or limit > 500:
            raise HTTPException(status_code=422, detail="Invalid event cursor or page limit")
        items = [event for event in _public_events(profile) if int(event.get("ordinal", 0)) > cursor][:limit]
        return {"items": items, "next_cursor": int(items[-1]["ordinal"]) if items else cursor}

    @app.get("/api/v1/sessions/{session_id}/transcripts")
    def transcripts(
        session_id: str,
        analysis_id: str | None = None,
        until_ms: int | None = None,
        cursor: str | None = None,
        limit: int = 100,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        if analysis_id not in {None, ANALYSIS_ID} or limit < 1 or limit > 100:
            raise HTTPException(status_code=404, detail="Unsupported synthetic assist profile")
        items = _transcript_items(profile)
        if until_ms is not None:
            items = [item for item in items if int(item["session_start_ms"]) <= until_ms]
        if cursor not in {None, ""}:
            items = []
        jobs = _mock_jobs(profile)
        return {"items": items[:limit], "next_cursor": None, **({"job": jobs[0]} if jobs else {})}

    @app.get("/api/v1/sessions/{session_id}/transcription-jobs/{job_id}")
    def transcription_job(
        session_id: str,
        job_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        job = next((item for item in _mock_jobs(profile) if item["id"] == job_id), None)
        if job is None:
            raise HTTPException(status_code=404, detail="Synthetic fixture job not found")
        return job

    @app.get("/api/v1/sessions/{session_id}/highlights")
    def highlights(
        session_id: str,
        analysis_id: str | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        if analysis_id not in {None, ANALYSIS_ID}:
            raise HTTPException(status_code=404, detail="Synthetic fixture analysis not found")
        return {"items": _highlight_items(profile)}

    @app.get("/api/v1/sessions/{session_id}/replay-analyses/{analysis_id}/options")
    def options(
        session_id: str,
        analysis_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization, evaluator=True)
        ensure_source(session_id)
        if analysis_id != ANALYSIS_ID:
            raise HTTPException(status_code=404, detail="Synthetic fixture analysis not found")
        return {
            "state": "ready", "evaluator_access": "granted",
            "analysis": _analysis_projection(profile), "items": _option_items(profile),
        }

    @app.get("/api/v1/sessions/{session_id}/assist-snapshot")
    def assist_snapshot(
        session_id: str,
        analysis_id: str | None = None,
        until_ms: int | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        if analysis_id not in {None, ANALYSIS_ID}:
            raise HTTPException(status_code=404, detail="Synthetic fixture analysis not found")
        segments = _transcript_items(profile)
        if until_ms is not None:
            segments = [item for item in segments if int(item["session_start_ms"]) <= until_ms]
        return {
            "source_session_id": SOURCE_SESSION_ID,
            "analysis_id": ANALYSIS_ID,
            "sequence": 1,
            "provider_availability": "unavailable",
            "evaluator_access": "granted",
            "jobs": _mock_jobs(profile), "transcripts": segments, "highlights": _highlight_items(profile),
            "options": _option_items(profile), "review_annotations": [],
            "label": SYNTHETIC_LABEL,
        }

    @app.post("/api/v1/sessions/{session_id}/evidence")
    async def evidence(session_id: str, request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        try:
            body = await request.json()
        except Exception as error:
            raise HTTPException(status_code=422, detail="Expected typed evidence reference JSON") from error
        refs = body.get("refs", []) if isinstance(body, dict) else []
        until_ms = body.get("until_ms", 2**53 - 1) if isinstance(body, dict) else 2**53 - 1
        if not isinstance(refs, list) or not isinstance(until_ms, int) or until_ms < 0:
            raise HTTPException(status_code=422, detail="Invalid evidence scope")
        event_index = {str(item.get("id")): item for item in _public_events(profile)}
        transcript_index = {str(item.get("id")): item for item in _transcript_items(profile)}
        resolved: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for ref in refs:
            if not isinstance(ref, dict) or ref.get("kind") not in {"session_event", "transcript_segment", "detector_alert"} or not isinstance(ref.get("id"), str):
                raise HTTPException(status_code=422, detail="Evidence references must follow the typed public profile")
            key = (ref["kind"], ref["id"])
            value: Any = None
            available_ms: int | None = None
            if key[0] == "session_event":
                value = event_index.get(key[1])
                available_ms = int(value.get("sim_ms", 0)) if isinstance(value, dict) else None
            elif key[0] == "transcript_segment":
                value = transcript_index.get(key[1])
                available_ms = int(value.get("session_start_ms", 0)) if isinstance(value, dict) else None
            if value is not None and available_ms is not None and available_ms <= until_ms:
                resolved.append({"ref": key_to_ref(key), "state": "resolved", "summary": str(value.get("message", value.get("text", "Synthetic public fixture evidence."))), "item": value})
            else:
                unresolved.append({"ref": key_to_ref(key)})
        return {"items": resolved, "unresolved": unresolved}

    @app.get("/api/v1/sessions/{session_id}/audio-assets/{asset_id}/content")
    def audio_content(
        session_id: str,
        asset_id: str,
        authorization: str | None = Header(default=None),
    ) -> Response:
        authorize(authorization)
        ensure_source(session_id)
        if asset_id != profile.audio_asset.get("asset", {}).get("id"):
            raise HTTPException(status_code=404, detail="Synthetic audio asset not found")
        raise HTTPException(status_code=404, detail="This public fixture contains metadata only; audio bytes are unavailable")

    @app.get("/api/v1/sessions/{session_id}/audio-assets")
    def audio_assets(session_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(authorization)
        ensure_source(session_id)
        return {"items": [], "audio_bytes_available": False, "label": SYNTHETIC_LABEL}

    @app.post("/api/v1/sessions/{session_id}/commands")
    async def commands(session_id: str) -> None:
        ensure_source(session_id)
        raise HTTPException(status_code=405, detail="Mock fixture has no command or control path")

    @app.post("/api/v1/sessions/{session_id}/transcripts/{segment_id}/corrections")
    async def transcript_correction(session_id: str, segment_id: str) -> None:
        ensure_source(session_id)
        raise HTTPException(status_code=405, detail="Mock fixture does not persist reviewer changes")

    @app.post("/api/v1/sessions/{session_id}/highlights/{highlight_id}/review")
    async def highlight_review(session_id: str, highlight_id: str) -> None:
        ensure_source(session_id)
        raise HTTPException(status_code=405, detail="Mock fixture does not persist reviewer changes")

    @app.post("/api/v1/sessions/{session_id}/replay-analyses/{analysis_id}/options/{option_id}/review")
    async def option_review(session_id: str, analysis_id: str, option_id: str) -> None:
        ensure_source(session_id)
        raise HTTPException(status_code=405, detail="Mock fixture has no option execution or review persistence path")

    @app.websocket("/api/v1/sessions/{session_id}/stream")
    async def source_stream(websocket: WebSocket, session_id: str) -> None:
        await websocket.accept(headers=mock_ws_headers())
        try:
            first = await asyncio.wait_for(websocket.receive_json(), timeout=5)
            token = first.get("token", "") if isinstance(first, dict) else ""
            role = next((name for candidate, name in token_roles.items() if isinstance(token, str) and hmac.compare_digest(token, candidate)), None)
            if role is None:
                await websocket.close(code=4401, reason="Mock credential rejected")
                return
            ensure_source(session_id)
            await websocket.send_json(_api_snapshot(profile, session_id))
            if websocket.query_params.get("variant") == "expired-stream-auth":
                await websocket.close(code=4401, reason="Auth-expiry mock variant")
                return
            while True:
                await websocket.receive_text()
        except HTTPException:
            await websocket.close(code=4404, reason="Synthetic source not found")
        except asyncio.TimeoutError:
            await websocket.close(code=4401, reason="First-message authentication timed out")
        except WebSocketDisconnect:
            return

    @app.websocket("/api/v1/sessions/{session_id}/assist-stream")
    async def assist_stream(websocket: WebSocket, session_id: str) -> None:
        await websocket.accept(headers=mock_ws_headers())
        try:
            first = await asyncio.wait_for(websocket.receive_json(), timeout=5)
            token = first.get("token", "") if isinstance(first, dict) else ""
            role = next((name for candidate, name in token_roles.items() if isinstance(token, str) and hmac.compare_digest(token, candidate)), None)
            if role not in {"operator", "evaluator", "source_read"}:
                await websocket.close(code=4401, reason="Mock credential rejected")
                return
            ensure_source(session_id)
            await websocket.send_json(_assist_stream_snapshot(profile))
            variant = websocket.query_params.get("variant")
            case_ids = {
                str(case.get("id")) for case in profile.stream_cases.get("cases", [])
                if isinstance(case, dict)
            }
            if variant is not None and variant not in case_ids:
                await websocket.close(code=4400, reason="Unsupported QA-04 stream variant")
                return
            if variant == "assist-sequence-gap":
                option = next(iter(_option_items(profile)), None)
                if option is not None:
                    await websocket.send_json({
                        "schema_version": "assist-1", "source_session_id": SOURCE_SESSION_ID,
                        "sequence": 3, "type": "option", "payload": {"option": option},
                    })
                return
            if variant == "duplicate-assist-sequence":
                option = next(iter(_option_items(profile)), None)
                if option is not None:
                    duplicate = {
                        "schema_version": "assist-1", "source_session_id": SOURCE_SESSION_ID,
                        "sequence": 1, "type": "option", "payload": {"option": option},
                    }
                    await websocket.send_json(duplicate)
                    await websocket.send_json(duplicate)
                return
            while True:
                await websocket.receive_text()
        except HTTPException:
            await websocket.close(code=4404, reason="Synthetic source not found")
        except asyncio.TimeoutError:
            await websocket.close(code=4401, reason="First-message authentication timed out")
        except WebSocketDisconnect:
            return

    return app


def key_to_ref(key: tuple[str, str]) -> dict[str, str]:
    return {"kind": key[0], "id": key[1]}


def _assist_stream_snapshot(profile: FixtureProfile) -> dict[str, Any]:
    return {
        "schema_version": "assist-1",
        "source_session_id": SOURCE_SESSION_ID,
        "sequence": 1,
        "type": "snapshot",
        "payload": {
            "jobs": _mock_jobs(profile),
            "transcripts": _transcript_items(profile),
            "highlights": _highlight_items(profile),
            "options": _option_items(profile),
            "review_annotations": [],
        },
    }


def _safe_vite_environment(temp_root: Path) -> dict[str, str]:
    """Build an allowlisted child environment; no local credentials or Vite env files."""
    allowed_parent_keys = (
        "PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "COMSPEC", "PROCESSOR_ARCHITECTURE",
    )
    environment = {key: os.environ[key] for key in allowed_parent_keys if key in os.environ}
    home = temp_root / "home"
    home.mkdir(exist_ok=True)
    environment.update({
        "HOME": str(home), "USERPROFILE": str(home),
        "TEMP": str(temp_root), "TMP": str(temp_root),
        "VITE_FLOWLENS_MODE": "fixture",
        "VITE_FLOWLENS_FIXTURE_VIEW": "evaluator",
    })
    return environment


def _vite_config_source(frontend_root: Path, env_root: Path, api_port: int, web_port: int) -> str:
    root = json.dumps(str(frontend_root.resolve()))
    env = json.dumps(str(env_root.resolve()))
    return f"""import {{ defineConfig }} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({{
  root: {root},
  envDir: {env},
  plugins: [react()],
  server: {{
    host: '{LOOPBACK}',
    port: {web_port},
    strictPort: true,
    proxy: {{
      '/api': {{ target: 'http://{LOOPBACK}:{api_port}', ws: true }},
      '/health': 'http://{LOOPBACK}:{api_port}',
    }},
  }},
}})
"""


def _spawn_process(command: list[str], *, cwd: Path, environment: Mapping[str, str]) -> subprocess.Popen[Any]:
    kwargs: dict[str, Any] = {
        "cwd": str(cwd), "env": dict(environment),
        "stdin": subprocess.DEVNULL, "stdout": None, "stderr": None,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(command, **kwargs)


def stop_child_process(process: subprocess.Popen[Any], timeout_s: float = 4.0) -> None:
    """Stop a child process tree and wait until its root process exits."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            process.send_signal(getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM))
        except (OSError, ValueError):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
    try:
        process.wait(timeout=timeout_s)
        return
    except subprocess.TimeoutExpired:
        pass

    if os.name == "nt":
        taskkill = shutil.which("taskkill")
        if taskkill:
            subprocess.run(
                [taskkill, "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, timeout=timeout_s,
            )
        else:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            process.kill()
    try:
        process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout_s)


class MockStackRuntime:
    """Owns per-run credentials, mock server, Vite child, and all temporary files."""

    def __init__(self, profile: FixtureProfile, api_port: int = 8000, web_port: int = 5173):
        if not (0 <= api_port <= 65535 and 0 <= web_port <= 65535):
            raise ValueError("Ports must be in range 0..65535")
        if api_port != 0 and api_port == web_port:
            raise ValueError("Mock API and Vite require different loopback ports")
        self.profile = profile
        self.api_port = api_port
        self.web_port = web_port
        self._temporary = tempfile.TemporaryDirectory(prefix="atc-flowlens-qa04-")
        self.temp_root = Path(self._temporary.name)
        self.storage_root = self.temp_root / "storage"
        self.env_root = self.temp_root / "vite-env"
        self.storage_root.mkdir()
        self.env_root.mkdir()
        self._closed = False
        self._server_socket: socket.socket | None = None
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._vite_process: subprocess.Popen[Any] | None = None
        self._vite_config: Path | None = None
        self.credentials = MockCredentials(
            operator_key=secrets.token_urlsafe(32),
            operator_token=secrets.token_urlsafe(32),
            source_read_token=secrets.token_urlsafe(32),
            review_token=secrets.token_urlsafe(32),
        )
        credential_file = self.storage_root / "mock-test-credentials.json"
        credential_file.write_text(json.dumps({
            "operator_key": self.credentials.operator_key,
            "operator_token": self.credentials.operator_token,
            "source_read_token": self.credentials.source_read_token,
            "review_token": self.credentials.review_token,
        }), encoding="utf-8")
        try:
            credential_file.chmod(0o600)
        except OSError:
            pass
        self.app = _create_mock_app(profile, self.credentials)

    @property
    def api_url(self) -> str:
        return f"http://{LOOPBACK}:{self.api_port}"

    @property
    def web_url(self) -> str:
        return f"http://{LOOPBACK}:{self.web_port}"

    def start_api(self, startup_timeout_s: float = 5.0) -> None:
        if self._server_thread is not None:
            raise StackStartupError("Mock HTTP/WS server is already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((LOOPBACK, self.api_port))
        except OSError:
            listener.close()
            raise
        self.api_port = int(listener.getsockname()[1])
        self._server_socket = listener
        config = uvicorn.Config(
            self.app, host=LOOPBACK, port=self.api_port, log_level="critical",
            access_log=False, lifespan="off", ws="websockets",
        )
        self._server = uvicorn.Server(config)
        self._server_thread = threading.Thread(
            target=self._server.run, kwargs={"sockets": [listener]},
            name="qa04-mock-http-ws", daemon=True,
        )
        self._server_thread.start()
        deadline = time.monotonic() + startup_timeout_s
        while time.monotonic() < deadline:
            if self._server.started:
                self._probe_http()
                self._probe_websockets()
                return
            if not self._server_thread.is_alive():
                raise StackStartupError("Mock HTTP/WS server exited during startup")
            time.sleep(0.025)
        raise StackStartupError("Mock HTTP/WS server did not become ready before the startup deadline")

    def _probe_http(self) -> None:
        try:
            with urllib.request.urlopen(f"{self.api_url}/health", timeout=1.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
                mode_header = response.headers.get("X-FlowLens-Mode")
                data_label = response.headers.get("X-FlowLens-Data-Label")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise StackStartupError("Mock HTTP health probe failed on loopback") from error
        if (payload.get("status") != "ok" or payload.get("mode") != "fixture-mock"
                or mode_header != "fixture-mock" or data_label != SYNTHETIC_LABEL):
            raise StackStartupError("Mock HTTP health probe returned an unsupported profile")

    def _probe_websockets(self) -> None:
        try:
            from websockets.sync.client import connect

            with connect(
                f"ws://{LOOPBACK}:{self.api_port}/api/v1/sessions/{SOURCE_SESSION_ID}/stream",
                open_timeout=2,
                close_timeout=1,
            ) as websocket:
                websocket.send(json.dumps({"token": self.credentials.source_read_token}))
                source = json.loads(websocket.recv(timeout=2))
            with connect(
                f"ws://{LOOPBACK}:{self.api_port}/api/v1/sessions/{SOURCE_SESSION_ID}/assist-stream",
                open_timeout=2,
                close_timeout=1,
            ) as websocket:
                websocket.send(json.dumps({"token": self.credentials.source_read_token, "analysis_id": ANALYSIS_ID}))
                assist = json.loads(websocket.recv(timeout=2))
        except Exception as error:
            raise StackStartupError("Mock HTTP/WS transport probe failed on loopback") from error
        if source.get("source_session_id") != SOURCE_SESSION_ID:
            raise StackStartupError("Mock source WebSocket returned an unsupported projection")
        if assist.get("schema_version") != "assist-1" or assist.get("source_session_id") != SOURCE_SESSION_ID:
            raise StackStartupError("Mock assist WebSocket returned an unsupported profile")

    def start_frontend(self, startup_timeout_s: float = 20.0) -> None:
        if self._vite_process is not None:
            raise StackStartupError("Vite is already started")
        frontend_root = ROOT / "frontend"
        node = shutil.which("node")
        vite_entry = frontend_root / "node_modules" / "vite" / "bin" / "vite.js"
        if not node:
            raise StackStartupError("Node.js is unavailable; the launcher did not download dependencies")
        if not vite_entry.is_file():
            raise StackStartupError(
                "Frontend dependencies are unavailable: frontend/node_modules/vite/bin/vite.js is missing; "
                "installing or downloading dependencies is outside this launcher"
            )

        self._vite_config = frontend_root / f".qa04-vite-{secrets.token_hex(8)}.mjs"
        self._vite_config.write_text(
            _vite_config_source(frontend_root, self.env_root, self.api_port, self.web_port),
            encoding="utf-8",
        )
        command = [
            node, str(vite_entry), "--config", str(self._vite_config),
            "--host", LOOPBACK, "--port", str(self.web_port), "--strictPort",
        ]
        self._vite_process = _spawn_process(
            command, cwd=frontend_root, environment=_safe_vite_environment(self.temp_root),
        )
        deadline = time.monotonic() + startup_timeout_s
        while time.monotonic() < deadline:
            if self._vite_process.poll() is not None:
                code = self._vite_process.returncode
                raise StackStartupError(f"Vite exited during startup with code {code}")
            try:
                with urllib.request.urlopen(self.web_url, timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.1)
        raise StackStartupError("Vite did not become ready on loopback before the startup deadline")

    def wait(self) -> None:
        while True:
            if self._vite_process is not None and self._vite_process.poll() is not None:
                raise StackStartupError(f"Vite exited unexpectedly with code {self._vite_process.returncode}")
            if self._server is not None and self._server_thread is not None and not self._server_thread.is_alive():
                raise StackStartupError("Mock HTTP/WS server exited unexpectedly")
            time.sleep(0.25)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._vite_process is not None:
            try:
                stop_child_process(self._vite_process)
            except (OSError, subprocess.TimeoutExpired):
                pass
            self._vite_process = None
        if self._server is not None:
            self._server.should_exit = True
        if self._server_thread is not None and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)
            if self._server_thread.is_alive() and self._server is not None:
                self._server.force_exit = True
                self._server_thread.join(timeout=2.0)
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None
        if self._vite_config is not None:
            try:
                self._vite_config.unlink(missing_ok=True)
            except OSError:
                pass
            self._vite_config = None
        self._temporary.cleanup()

    def __enter__(self) -> "MockStackRuntime":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the QA-04 loopback fixture/mock stack")
    parser.add_argument("--fixture", required=True, help="Allowlisted public fixture ID (currently F-COMM-01)")
    parser.add_argument("--api-port", type=int, default=8000, help="Loopback mock API port (default: 8000)")
    parser.add_argument("--web-port", type=int, default=5173, help="Loopback Vite port (default: 5173)")
    args = parser.parse_args(argv)
    if not (1 <= args.api_port <= 65535 and 1 <= args.web_port <= 65535):
        parser.error("ports must be between 1 and 65535")
    if args.api_port == args.web_port:
        parser.error("--api-port and --web-port must be different")
    return args


def _print_startup(runtime: MockStackRuntime, profile: FixtureProfile) -> None:
    print(f"Fixture/profile: {profile.fixture_id} + {SOURCE_FIXTURE_ID} ({SOURCE_SESSION_ID})")
    print(f"Mode: FIXTURE MOCK; UI mode VITE_FLOWLENS_MODE=fixture, evaluator view")
    print(f"Label: {SYNTHETIC_LABEL}")
    print(f"Frontend: {runtime.web_url}")
    print(f"Mock HTTP: {runtime.api_url}/health (available; loopback)")
    print(f"Mock source WS: ws://{LOOPBACK}:{runtime.api_port}/api/v1/sessions/{SOURCE_SESSION_ID}/stream (available)")
    print(f"Mock assist WS: ws://{LOOPBACK}:{runtime.api_port}/api/v1/sessions/{SOURCE_SESSION_ID}/assist-stream (available)")
    print("Provider/audio bytes: unavailable; mock has no provider/feed connection or audio waveform")
    print("QA-only variants: failed job, same-time event ordering, duplicate/gap resync, expired stream auth")
    if profile.exact_byte_mismatches:
        names = ", ".join(profile.exact_byte_mismatches)
        print(
            "Fixture hash note: exact-byte SHA-256 differs on this CRLF checkout; "
            f"LF-normalized content matches the public manifest ({names})."
        )
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        profile = load_fixture(args.fixture)
    except FixtureValidationError as error:
        print(f"Fixture error: {error}", file=sys.stderr)
        return 2

    runtime: MockStackRuntime | None = None
    try:
        runtime = MockStackRuntime(profile, api_port=args.api_port, web_port=args.web_port)
        runtime.start_api()
        _print_startup(runtime, profile)
        runtime.start_frontend()
        print("Vite UI: available (loopback); Ctrl+C stops the stack")
        runtime.wait()
        return 0
    except KeyboardInterrupt:
        print("Stopping mock stack and cleaning temporary resources...")
        return 0
    except (OSError, StackStartupError, FixtureValidationError) as error:
        print(f"Mock stack startup failed: {error}", file=sys.stderr)
        return 1
    finally:
        if runtime is not None:
            runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
