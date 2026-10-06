"""BE-06 result commit, evidence reads, and assist stream checks.

Every transcript/highlight/option below is an authored synthetic DTO fixture.
No audio is transcribed and no model/provider inference is run.
"""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import threading
import time
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.assist_service import AssistJobConfig, AssistResultConflict, PrivateWorkerRequest
from backend.ports import CompositionOverrides

OPERATOR_KEY = "be06-integration-test-operator-key"
JOB_CONFIG = AssistJobConfig(
    provider="synthetic-test-fixture",
    model="authored-no-inference-fixture",
    version="fixture-model-v1",
    config_version="fixture-config-v1",
    timeout_s=5.0,
    language="en",
)


class FakeClock:
    def __init__(self) -> None:
        self.wall = 1_800_000_000.0
        self.monotonic = 100.0

    def wall_time(self) -> float:
        return self.wall

    def monotonic_time(self) -> float:
        return self.monotonic


def _result(request: PrivateWorkerRequest) -> dict[str, Any]:
    """Fixed synthetic labels for persistence/schema tests, unrelated to WAV samples."""
    return {
        "job_id": request.job_id,
        "attempt_id": request.attempt_id,
        "asset_id": request.asset_id,
        "model_version": request.model_version,
        "config_version": request.config_version,
        "status": "completed",
        "source_session_id": request.source_session_id,
        "source_content_hash": request.source_content_hash,
        "asset_hash": request.asset_hash,
        "input_hash": request.input_hash,
        "analysis_id": request.analysis_id,
        "segments": [
            {
                "id": "seg-synthetic-1",
                "asset_id": request.asset_id,
                "start_ms": 0,
                "end_ms": 50,
                "channel_id": "surface",
                "speaker_label": "fixture-speaker",
                "speaker_source": "synthetic_fixture",
                "speaker_confidence": 0.7,
                "text": "Synthetic fixture segment one; not audio transcription.",
                "language": "en",
                "asr_confidence": 0.8,
                "model_version": request.model_version,
                "correction_status": "raw_fixture",
            },
            {
                "id": "seg-synthetic-2",
                "asset_id": request.asset_id,
                "start_ms": 50,
                "end_ms": 200,
                "channel_id": "surface",
                "speaker_label": "fixture-speaker",
                "speaker_source": "synthetic_fixture",
                "speaker_confidence": None,
                "text": "Synthetic fixture segment two; not audio transcription.",
                "language": "en",
                "asr_confidence": None,
                "model_version": request.model_version,
                "correction_status": "raw_fixture",
            },
        ],
        "entities": [
            {
                "segment_id": "seg-synthetic-1",
                "entity_type": "callsign",
                "candidate_value": "FIXTURE-01",
                "normalized_value": "FIXTURE-01",
                "confidence": 0.6,
                "alternatives": ["FIXTURE-01A"],
            },
        ],
        "highlights": [
            {
                "id": "highlight-synthetic-1",
                "category": "fixture_category",
                "review_priority": "high",
                "statement": "Synthetic review highlight fixture; no detector severity is assigned.",
                "transcript_segment_ids": ["seg-synthetic-1"],
                "session_event_ids": ["evt-0"],
                "uncertainty": "Authored fixture only; not domain-reviewed.",
                "provider_version": "synthetic-test-fixture",
                "rule_version": "fixture-rule-v1",
                "status": "candidate",
            },
        ],
        "options": [
            {
                "id": "option-synthetic-1",
                "replay_analysis_id": request.analysis_id,
                "option_statement": "Synthetic candidate option fixture; not an operational instruction.",
                "rationale": "Fixed test text linked to a synthetic replay event and fixture segment.",
                "supporting_evidence_ids": [
                    {"kind": "session_event", "id": "evt-0"},
                    {"kind": "transcript_segment", "id": "seg-synthetic-1"},
                ],
                "preconditions": ["Synthetic fixture only."],
                "unknowns": ["No provider inference or domain review."],
                "source_version": request.source_content_hash,
                "model_version": request.model_version,
                "rule_version": "fixture-rule-v1",
                "review_status": "candidate",
            },
        ],
    }


class FixedWorker:
    """Returns a fixed synthetic result and receives no archive or command capability."""

    def __init__(self, factory: Callable[[PrivateWorkerRequest], Any] | None = None) -> None:
        self.factory = factory or _result
        self.requests: list[PrivateWorkerRequest] = []
        self.results: list[Any] = []

    def process(self, request: PrivateWorkerRequest) -> Any:
        assert isinstance(request, PrivateWorkerRequest)
        assert not {"archive", "db", "connection", "command", "command_executor", "operator_token"}.intersection(
            vars(request)
        )
        self.requests.append(request)
        result = self.factory(request)
        self.results.append(result)
        return result


class GateWorker(FixedWorker):
    """Waits in the worker thread until a test releases its fixed result."""

    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def process(self, request: PrivateWorkerRequest) -> Any:
        self.requests.append(request)
        self.started.set()
        self.release.wait(timeout=5)
        result = self.factory(request)
        self.results.append(result)
        return result


def _event(source_id: str, event_id: str, ordinal: int, sim_ms: int) -> dict[str, Any]:
    return {
        "schema_version": "replay-1",
        "source_id": source_id,
        "source_event_id": event_id,
        "source_time": {"value": sim_ms, "unit": "ms", "clock": "fixture-clock"},
        "quality": {"status": "nominal", "reasons": []},
        "event": {
            "id": event_id,
            "ordinal": ordinal,
            "sim_ms": sim_ms,
            "audit_utc": None,
            "type": "TRACK",
            "message": "Authored synthetic BE-06 source event.",
            "target": "AC101",
            "observed_ms": sim_ms,
            "received_ms": sim_ms,
            "track": {
                "id": "AC101",
                "callsign": "SYN101",
                "kind": "aircraft",
                "x_m": 100.0,
                "y_m": 20.0,
                "speed_mps": 35.0,
                "heading_deg": 90.0,
                "phase": "TAXI",
                "length_m": 36.0,
                "width_m": 4.0,
                "runway": "09",
                "route": [[100.0, 20.0], [200.0, 20.0]],
                "owner": "ground",
                "observed_ms": sim_ms,
                "received_ms": sim_ms,
                "source": "synthetic-fixture",
                "event_id": event_id,
            },
            "data": {"fixture_kind": "synthetic"},
        },
    }


def _bundle(source_id: str, *, aligned: bool = True) -> tuple[dict[str, Any], bytes, bytes]:
    records = [_event(source_id, "evt-0", 0, 100), _event(source_id, "evt-1", 1, 1000)]
    if not aligned:
        for record in records:
            event = record["event"]
            event["sim_ms"] = None
            event["type"] = "UNALIGNED_FIXTURE"
            event["target"] = None
            event["observed_ms"] = None
            event["received_ms"] = None
            event["track"] = None
            event["data"] = {}
            record["source_time"]["value"] = None
            record["quality"] = {
                "status": "alignment_unknown",
                "reasons": ["synthetic fixture has no session-time mapping"],
            }
    event_bytes = b"".join(
        (json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for item in records
    )
    manifest: dict[str, Any] = {
        "schema_version": "replay-1",
        "source_id": source_id,
        "source_kind": "synthetic",
        "source_ref": "private-fixture-source-locator",
        "content_hash": hashlib.sha256(event_bytes).hexdigest(),
        "provenance": {
            "owner": None,
            "version": "fixture-v1",
            "derivation": "authored synthetic BE-06 integration fixture",
            "retention_reason": "temporary test data",
        },
        "permission_profile": {
            "reference": "local-synthetic-fixture",
            "purpose": "BE-06 fixture validation",
            "processing_scope": "temporary TestClient and SQLite test harness",
        },
        "retention_until": None,
        "timebase": {
            "source_clock": "fixture-clock",
            "source_unit": "ms",
            "mapping_id": "fixture-fixed-offset-v1" if aligned else None,
            "offset_ms": 0 if aligned else None,
            "uncertainty_ms": 0 if aligned else None,
            "alignment_status": "aligned" if aligned else "unknown",
        },
        "coverage": {
            "status": "known" if aligned else "unknown",
            "object_ids": ["AC101"] if aligned else None,
            "channel_ids": ["surface"] if aligned else None,
            "intervals": [{"start_ms": 0, "end_ms": 1000}] if aligned else None,
            "missing_intervals": [] if aligned else None,
        },
        "layout": {
            "id": "be06-fixture-layout",
            "version": "1",
            "name": "BE-06 synthetic fixture layout",
            "coordinate_system": "LOCAL_METRES",
            "physical_runway_id": "RWY-TEST",
            "runway": [[0, 0], [1000, 0]],
            "protected_area": [[0, -75], [1000, -75], [1000, 75], [0, 75]],
            "taxiways": [[[0, 200], [1000, 200]]],
            "hold_lines": [[[400, 0], [400, 40]]],
            "directions": {"09": "eastbound", "27": "westbound"},
            "note": "Synthetic fixture only; not operational data.",
        },
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return manifest, manifest_bytes, event_bytes


def _wav(duration_ms: int = 200) -> bytes:
    sample_rate = 8000
    frames = sample_rate * duration_ms // 1000
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\x00\x00" * frames)
    return stream.getvalue()


def _asset_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_kind": manifest["source_kind"],
        "source_ref": manifest["source_id"],
        "channel_id": "surface",
        "audio_start": 100,
        "timebase": manifest["timebase"],
        "provenance": manifest["provenance"],
        "permission_profile": manifest["permission_profile"],
        "retention_until": manifest["retention_until"],
    }


def _client(
    tmp_path: Path,
    *,
    worker: Any | None,
    clock: FakeClock | None = None,
) -> TestClient:
    fake_clock = clock or FakeClock()
    app = create_app(
        db_path=tmp_path / "be06.sqlite3",
        operator_key=OPERATOR_KEY,
        ports=CompositionOverrides(worker=worker),
        wall_clock=fake_clock.wall_time,
        monotonic_clock=fake_clock.monotonic_time,
        audio_root=tmp_path / "private-audio",
        assist_config=JOB_CONFIG,
    )
    return TestClient(app)


def _operator(client: TestClient) -> str:
    response = client.post("/api/v1/auth/operator", json={"key": OPERATOR_KEY})
    assert response.status_code == 200
    return response.json()["token"]


def _import_source(
    client: TestClient, token: str, source_id: str, *, aligned: bool = True
) -> tuple[dict[str, Any], str]:
    manifest, manifest_bytes, event_bytes = _bundle(source_id, aligned=aligned)
    response = client.post(
        "/api/v1/replay-imports",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "manifest": ("manifest.json", manifest_bytes, "application/json"),
            "events": ("events.jsonl", event_bytes, "application/x-ndjson"),
        },
    )
    assert response.status_code == 201, response.text
    return manifest, response.json()["source_session_id"]


def _upload(client: TestClient, token: str, source_id: str, manifest: dict[str, Any]) -> Any:
    return client.post(
        f"/api/v1/sessions/{source_id}/audio-assets",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio": ("fixture.wav", _wav(), "audio/wav")},
        data={"metadata": json.dumps(_asset_metadata(manifest))},
    )


def _wait_job(client: TestClient, token: str, source_id: str, job_id: str, timeout_s: float = 2.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        response = client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        job = response.json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.01)
    raise AssertionError("worker attempt did not reach a terminal state")


def _counts(db: sqlite3.Connection) -> dict[str, int]:
    tables = (
        "assist_analyses", "assist_transcript_segments", "assist_candidate_entities",
        "assist_highlights", "assist_options", "assist_result_receipts", "assist_stream_state",
        "assist_stream_events",
    )
    return {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def test_atomic_commit_reopen_receipt_and_be04_compatibility(tmp_path: Path) -> None:
    worker = FixedWorker()
    database = tmp_path / "be06.sqlite3"
    with _client(tmp_path, worker=worker) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be06-atomic-source")
        source_before = client.app.state.manager.archive.replay_source(source_id)
        uploaded = _upload(client, token, source_id, manifest)
        assert uploaded.status_code == 201, uploaded.text
        job_id = uploaded.json()["job"]["id"]
        completed = _wait_job(client, token, source_id, job_id)
        assert completed["status"] == "completed"
        receipt = completed["result_receipt"]
        assert receipt["source_session_id"] == source_id
        assert receipt["attempt_id"] == completed["attempt_id"]
        assert receipt["analysis_id"]
        assert receipt["sequence"] == 5
        assert len(worker.requests) == 1
        request = worker.requests[0]
        assert request.source_content_hash == manifest["content_hash"]
        assert request.asset_hash == uploaded.json()["asset"]["hash"]
        assert request.input_hash and request.layout_version == "1"
        manager = client.app.state.manager
        assert manager.assist_service._storage._db is manager.archive.db
        assert _counts(manager.archive.db) == {
            "assist_analyses": 1,
            "assist_transcript_segments": 2,
            "assist_candidate_entities": 1,
            "assist_highlights": 1,
            "assist_options": 1,
            "assist_result_receipts": 1,
            "assist_stream_state": 1,
            "assist_stream_events": 5,
        }
        source_after = manager.archive.replay_source(source_id)
        assert source_before["content_hash"] == source_after["content_hash"]
        assert source_before["event_bytes"] == source_after["event_bytes"]
        replay_metadata = client.get(
            f"/api/v1/sessions/{source_id}/replay-source", headers={"Authorization": f"Bearer {token}"}
        )
        assert replay_metadata.status_code == 200
        assist_metadata = next(
            item for item in replay_metadata.json()["analyses"] if item["id"] == receipt["analysis_id"]
        )
        assert assist_metadata["kind"] == "assist"
        assert assist_metadata["versions"]["source_version"] == manifest["content_hash"]
        assert assist_metadata["window_start_ms"] == 100 and assist_metadata["window_end_ms"] == 300
        source_evidence = client.post(
            f"/api/v1/sessions/{source_id}/evidence",
            headers={"Authorization": f"Bearer {token}"},
            json={"refs": [{"kind": "session_event", "id": "evt-0"}], "until_ms": 100},
        )
        assert source_evidence.status_code == 200
        assert len(source_evidence.json()["items"]) == 1
        assert client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={receipt['analysis_id']}&until_ms=300",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        created = client.post(
            "/api/v1/sessions", headers={"Authorization": f"Bearer {token}"},
            json={"scenario_id": "overlap", "seed": 19},
        )
        assert created.status_code == 201
        synthetic_id = created.json()["id"]
        command = client.post(
            f"/api/v1/sessions/{synthetic_id}/commands", headers={"Authorization": f"Bearer {token}"},
            json={"command_id": "be06-compat-start", "expected_revision": 0, "type": "START"},
        )
        assert command.status_code == 200
        with client.websocket_connect(f"/api/v1/sessions/{synthetic_id}/stream") as socket:
            socket.send_json({"token": token})
            source_snapshot = socket.receive_json()
            assert source_snapshot["kind"] == "training"
            assert "assist-1" != source_snapshot.get("schema_version")

    # Reopening a read-only SQLite connection after TestClient shutdown proves the
    # receipt, all result rows, terminal job state, and stream sequence were durable.
    reopened = sqlite3.connect(database)
    reopened.row_factory = sqlite3.Row
    try:
        counts = _counts(reopened)
        assert counts["assist_analyses"] == 1
        assert counts["assist_transcript_segments"] == 2
        assert counts["assist_candidate_entities"] == 1
        assert counts["assist_highlights"] == 1
        assert counts["assist_options"] == 1
        row = reopened.execute("SELECT receipt_json FROM assist_result_receipts").fetchone()
        durable_receipt = json.loads(row["receipt_json"])
        assert durable_receipt["receipt_id"] == receipt["receipt_id"]
        assert reopened.execute("SELECT status FROM transcription_jobs").fetchone()["status"] == "completed"
        assert reopened.execute("SELECT sequence FROM assist_stream_state").fetchone()["sequence"] == 5
        analysis = reopened.execute(
            "SELECT kind, input_hash, versions_json, result_json FROM assist_analyses"
        ).fetchone()
        assert analysis["kind"] == "assist" and len(analysis["input_hash"]) == 64
        assert json.loads(analysis["versions_json"])["transcript_revision_basis"] == "raw"
        assert len(json.loads(analysis["result_json"])["segments"]) == 2
        option = json.loads(reopened.execute("SELECT payload_json FROM assist_options").fetchone()["payload_json"])
        assert option["supporting_evidence_ids"][0] == {"kind": "session_event", "id": "evt-0"}
    finally:
        reopened.close()


@pytest.mark.parametrize(
    "case,mutate",
    [
        ("foreign evidence", lambda body, req: body["options"][0]["supporting_evidence_ids"].__setitem__(
            0, {"kind": "session_event", "id": "another-source:evt-0"})),
        ("dangling evidence", lambda body, req: body["options"][0]["supporting_evidence_ids"].__setitem__(
            0, {"kind": "session_event", "id": "not-in-source"})),
        ("top-level action", lambda body, req: body.__setitem__("command", {"type": "CLEARANCE"})),
        ("nested action", lambda body, req: body["options"][0].__setitem__("clearance", {"runway": "09"})),
        ("source id mismatch", lambda body, req: body.__setitem__("source_session_id", "foreign-source-session")),
        ("source hash mismatch", lambda body, req: body.__setitem__("source_content_hash", "0" * 64)),
        ("asset hash mismatch", lambda body, req: body.__setitem__("asset_hash", "0" * 64)),
        ("input hash mismatch", lambda body, req: body.__setitem__("input_hash", "0" * 64)),
        ("model version mismatch", lambda body, req: body.__setitem__("model_version", "other-model")),
        ("config version mismatch", lambda body, req: body.__setitem__("config_version", "other-config")),
        ("job mismatch", lambda body, req: body.__setitem__("job_id", "other-job")),
        ("attempt mismatch", lambda body, req: body.__setitem__("attempt_id", "stale-attempt")),
        ("cancelled result", lambda body, req: body.__setitem__("status", "cancelled")),
        ("timeout result", lambda body, req: body.__setitem__("status", "timeout")),
        ("DTO invalid confidence", lambda body, req: body["segments"][0].__setitem__("asr_confidence", 1.1)),
        ("evidence outside analysis window", lambda body, req: body["options"][0]["supporting_evidence_ids"].__setitem__(
            0, {"kind": "session_event", "id": "evt-1"})),
    ],
)
def test_invalid_results_leave_no_partial_rows_or_source_changes(
    tmp_path: Path,
    case: str,
    mutate: Callable[[dict[str, Any], PrivateWorkerRequest], None],
) -> None:
    def invalid_result(request: PrivateWorkerRequest) -> dict[str, Any]:
        body = _result(request)
        mutate(body, request)
        return body

    worker = FixedWorker(invalid_result)
    with _client(tmp_path / case.replace(" ", "-"), worker=worker) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, f"be06-invalid-{case.replace(' ', '-')}")
        manager = client.app.state.manager
        source_before = manager.archive.replay_source(source_id)
        uploaded = _upload(client, token, source_id, manifest)
        assert uploaded.status_code == 201, uploaded.text
        job = _wait_job(client, token, source_id, uploaded.json()["job"]["id"])
        assert job["status"] == "failed", case
        assert job["error"]["code"] == "worker_result_invalid", case
        assert _counts(manager.archive.db) == {
            "assist_analyses": 0,
            "assist_transcript_segments": 0,
            "assist_candidate_entities": 0,
            "assist_highlights": 0,
            "assist_options": 0,
            "assist_result_receipts": 0,
            "assist_stream_state": 0,
            "assist_stream_events": 0,
        }, case
        source_after = manager.archive.replay_source(source_id)
        assert source_before["content_hash"] == source_after["content_hash"]
        assert source_before["event_bytes"] == source_after["event_bytes"]
        assert manager.archive.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0] == 0


def test_idempotent_retry_returns_same_receipt_and_changed_payload_conflicts_atomically(tmp_path: Path) -> None:
    worker = FixedWorker()
    with _client(tmp_path, worker=worker) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be06-idempotent-source")
        uploaded = _upload(client, token, source_id, manifest)
        job = _wait_job(client, token, source_id, uploaded.json()["job"]["id"])
        assert job["status"] == "completed"
        request = worker.requests[0]
        service = client.app.state.manager.assist_service
        accepted = service._validate_worker_result(worker.results[0], request)
        before = _counts(client.app.state.manager.archive.db)
        sequence = service.stream_sequence(source_id)
        same = service.commit_result(accepted, request)
        assert same == job["result_receipt"]
        assert _counts(client.app.state.manager.archive.db) == before
        assert service.stream_sequence(source_id) == sequence

        changed_payload = dict(worker.results[0])
        changed_payload["options"] = [dict(changed_payload["options"][0])]
        changed_payload["options"][0]["option_statement"] = "Changed payload for the same attempt."
        changed = service._validate_worker_result(changed_payload, request)
        with pytest.raises(AssistResultConflict):
            service.commit_result(changed, request)
        assert _counts(client.app.state.manager.archive.db) == before
        assert service.stream_sequence(source_id) == sequence


def test_scoped_reads_evaluator_options_historical_cutoff_and_paging(tmp_path: Path) -> None:
    worker = FixedWorker()
    with _client(tmp_path, worker=worker) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be06-scope-source")
        _, other_source_id = _import_source(client, token, "be06-scope-other")
        uploaded = _upload(client, token, source_id, manifest)
        job = _wait_job(client, token, source_id, uploaded.json()["job"]["id"])
        analysis_id = job["result_receipt"]["analysis_id"]
        headers = {"Authorization": f"Bearer {token}"}

        before = client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={analysis_id}&until_ms=299&limit=1",
            headers=headers,
        )
        assert before.status_code == 200 and before.json()["items"] == []
        first_page = client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={analysis_id}&until_ms=300&limit=1",
            headers=headers,
        )
        assert first_page.status_code == 200
        assert len(first_page.json()["items"]) == 1
        assert first_page.json()["next_cursor"]
        first_segment = first_page.json()["items"][0]
        assert first_segment["time_alignment"] == "aligned"
        second_page = client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={analysis_id}&until_ms=300&limit=1"
            f"&cursor={first_page.json()['next_cursor']}",
            headers=headers,
        )
        assert second_page.status_code == 200
        assert len(second_page.json()["items"]) == 1
        assert second_page.json()["next_cursor"] is None
        wrong_scope = client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={analysis_id}&until_ms=299&cursor={first_page.json()['next_cursor']}",
            headers=headers,
        )
        assert wrong_scope.status_code == 422

        earlier_options = client.get(
            f"/api/v1/sessions/{source_id}/replay-analyses/{analysis_id}/options?until_ms=299",
            headers=headers,
        )
        assert earlier_options.status_code == 200 and earlier_options.json()["items"] == []
        options = client.get(
            f"/api/v1/sessions/{source_id}/replay-analyses/{analysis_id}/options?until_ms=300",
            headers=headers,
        )
        assert options.status_code == 200 and len(options.json()["items"]) == 1
        highlights = client.get(
            f"/api/v1/sessions/{source_id}/highlights?analysis_id={analysis_id}&until_ms=300",
            headers=headers,
        )
        assert highlights.status_code == 200
        assert highlights.json()["items"][0]["review_priority"] == "high"
        assert "severity" not in highlights.json()["items"][0]

        evidence_before = client.post(
            f"/api/v1/sessions/{source_id}/evidence", headers=headers,
            json={"refs": [{"kind": "transcript_segment", "id": "seg-synthetic-1"}], "until_ms": 299},
        )
        assert evidence_before.status_code == 200 and evidence_before.json()["unresolved"]
        evidence_at_end = client.post(
            f"/api/v1/sessions/{source_id}/evidence", headers=headers,
            json={"refs": [{"kind": "transcript_segment", "id": "seg-synthetic-1"}], "until_ms": 300},
        )
        assert len(evidence_at_end.json()["items"]) == 1

        review = client.post(f"/api/v1/sessions/{source_id}/reviews", headers=headers)
        assert review.status_code == 201
        source_headers = {"Authorization": f"Bearer {review.json()['source_read_token']}"}
        assert client.app.state.manager.identity(token)["evaluator_replay"] is True
        assert client.app.state.manager.identity(review.json()["source_read_token"])["evaluator_replay"] is False
        assert client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={analysis_id}&until_ms=300",
            headers=source_headers,
        ).status_code == 200
        evaluator_snapshot = client.get(
            f"/api/v1/sessions/{source_id}/assist-snapshot?analysis_id={analysis_id}&until_ms=300",
            headers=headers,
        ).json()
        assert len(evaluator_snapshot["payload"]["options"]) == 1
        read_snapshot = client.get(
            f"/api/v1/sessions/{source_id}/assist-snapshot?analysis_id={analysis_id}&until_ms=300",
            headers=source_headers,
        ).json()
        assert read_snapshot["payload"]["options"] == []
        assert client.get(
            f"/api/v1/sessions/{source_id}/replay-analyses/{analysis_id}/options?evaluator_only=true",
            headers=source_headers,
        ).status_code == 403
        assert client.get(
            f"/api/v1/sessions/{other_source_id}/transcripts", headers=source_headers,
        ).status_code == 403
        assert client.post(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job['id']}/retry", headers=source_headers,
        ).status_code == 403
        assert client.post(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job['id']}/cancel", headers=source_headers,
        ).status_code == 403
        assert _upload(client, review.json()["source_read_token"], source_id, manifest).status_code == 403


def test_unaligned_transcript_is_marked_uncertain_and_not_in_historical_time_reads(tmp_path: Path) -> None:
    def unaligned_result(request: PrivateWorkerRequest) -> dict[str, Any]:
        body = _result(request)
        body["highlights"] = []
        body["options"] = []
        return body

    worker = FixedWorker(unaligned_result)
    with _client(tmp_path, worker=worker) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be06-unaligned-source", aligned=False)
        metadata = _asset_metadata(manifest)
        metadata["audio_start"] = None
        uploaded = client.post(
            f"/api/v1/sessions/{source_id}/audio-assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"audio": ("fixture.wav", _wav(), "audio/wav")},
            data={"metadata": json.dumps(metadata)},
        )
        assert uploaded.status_code == 201, uploaded.text
        job = _wait_job(client, token, source_id, uploaded.json()["job"]["id"])
        assert job["status"] == "completed"
        analysis_id = job["result_receipt"]["analysis_id"]
        headers = {"Authorization": f"Bearer {token}"}
        historical = client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={analysis_id}&until_ms=1000",
            headers=headers,
        )
        assert historical.status_code == 200 and historical.json()["items"] == []
        full = client.get(
            f"/api/v1/sessions/{source_id}/transcripts?analysis_id={analysis_id}", headers=headers,
        )
        assert full.status_code == 200
        assert full.json()["items"][0]["time_alignment"] == "unknown"
        assert "unknown" in full.json()["items"][0]["alignment_uncertainty"].lower()


def test_cancelled_and_timed_out_attempts_cannot_commit_late_results(tmp_path: Path) -> None:
    for terminal in ("cancelled", "timeout"):
        case_root = tmp_path / terminal
        clock = FakeClock()
        worker = GateWorker()
        with _client(case_root, worker=worker, clock=clock) as client:
            token = _operator(client)
            manifest, source_id = _import_source(client, token, f"be06-{terminal}-source")
            uploaded = _upload(client, token, source_id, manifest)
            job_id = uploaded.json()["job"]["id"]
            assert worker.started.wait(timeout=2)
            request = worker.requests[0]
            if terminal == "cancelled":
                stopped = client.post(
                    f"/api/v1/sessions/{source_id}/transcription-jobs/{job_id}/cancel",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert stopped.status_code == 200 and stopped.json()["status"] == "cancelled"
            else:
                clock.monotonic += JOB_CONFIG.timeout_s + 1
                stopped = client.get(
                    f"/api/v1/sessions/{source_id}/transcription-jobs/{job_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert stopped.status_code == 200 and stopped.json()["status"] == "failed"
                assert stopped.json()["error"]["code"] == "timeout"
            valid = client.app.state.manager.assist_service._validate_worker_result(_result(request), request)
            with pytest.raises(AssistResultConflict):
                client.app.state.manager.assist_service.commit_result(valid, request)
            assert all(value == 0 for value in _counts(client.app.state.manager.archive.db).values())
            worker.release.set()


def test_stale_attempt_cannot_commit_after_retry_has_completed(tmp_path: Path) -> None:
    class FirstAttemptGate(FixedWorker):
        def __init__(self) -> None:
            super().__init__()
            self.first_started = threading.Event()
            self.release_first = threading.Event()

        def process(self, request: PrivateWorkerRequest) -> Any:
            self.requests.append(request)
            if len(self.requests) == 1:
                self.first_started.set()
                self.release_first.wait(timeout=5)
            result = self.factory(request)
            self.results.append(result)
            return result

    worker = FirstAttemptGate()
    with _client(tmp_path, worker=worker) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be06-stale-attempt-source")
        uploaded = _upload(client, token, source_id, manifest)
        original_job = uploaded.json()["job"]
        assert worker.first_started.wait(timeout=2)
        old_request = worker.requests[0]
        cancel = client.post(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{original_job['id']}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel.status_code == 200
        retried = client.post(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{original_job['id']}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retried.status_code == 202
        latest = _wait_job(client, token, source_id, original_job["id"])
        assert latest["status"] == "completed"
        assert latest["attempt_id"] != old_request.attempt_id
        old_result = client.app.state.manager.assist_service._validate_worker_result(_result(old_request), old_request)
        with pytest.raises(AssistResultConflict):
            client.app.state.manager.assist_service.commit_result(old_result, old_request)
        assert _counts(client.app.state.manager.archive.db)["assist_analyses"] == 1
        assert _counts(client.app.state.manager.archive.db)["assist_result_receipts"] == 1
        worker.release_first.set()


def test_assist_stream_auth_snapshot_reconnect_and_ordered_typed_updates(tmp_path: Path) -> None:
    worker = GateWorker()
    with _client(tmp_path, worker=worker) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be06-stream-source")
        uploaded = _upload(client, token, source_id, manifest)
        assert uploaded.status_code == 201
        assert worker.started.wait(timeout=2)
        with client.websocket_connect(f"/api/v1/sessions/{source_id}/assist-stream") as socket:
            socket.send_json({"token": token, "after_sequence": 0})
            initial = socket.receive_json()
            assert initial["schema_version"] == "assist-1"
            assert initial["type"] == "snapshot"
            assert initial["sequence"] == 0
            worker.release.set()
            messages = [socket.receive_json() for _ in range(5)]
            assert [message["type"] for message in messages] == [
                "segment", "segment", "highlight", "option", "job_progress",
            ]
            assert [message["sequence"] for message in messages] == [1, 2, 3, 4, 5]
            assert all(message["source_session_id"] == source_id for message in messages)

        completed = _wait_job(client, token, source_id, uploaded.json()["job"]["id"])
        analysis_id = completed["result_receipt"]["analysis_id"]
        with client.websocket_connect(f"/api/v1/sessions/{source_id}/assist-stream") as reconnect:
            reconnect.send_json({"token": token, "after_sequence": 0, "analysis_id": analysis_id, "until_ms": 300})
            resumed = reconnect.receive_json()
            assert resumed["type"] == "snapshot"
            assert resumed["sequence"] == 5
            assert len(resumed["payload"]["options"]) == 1

        review = client.post(
            f"/api/v1/sessions/{source_id}/reviews", headers={"Authorization": f"Bearer {token}"},
        )
        with client.websocket_connect(f"/api/v1/sessions/{source_id}/assist-stream") as read_only:
            read_only.send_json({"token": review.json()["source_read_token"], "until_ms": 300})
            snapshot = read_only.receive_json()
            assert snapshot["type"] == "snapshot"
            assert snapshot["payload"]["options"] == []


def test_assist_stream_sequence_gap_resyncs_with_authorized_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(tmp_path, worker=None) as client:
        token = _operator(client)
        _, source_id = _import_source(client, token, "be06-gap-source")
        service = client.app.state.manager.assist_service
        calls = 0

        def gapped_events(_source: str, _after: int) -> list[dict[str, Any]]:
            nonlocal calls
            calls += 1
            if calls == 1:
                return [{"sequence": 2}]
            return []

        monkeypatch.setattr(service, "stream_events", gapped_events)
        with client.websocket_connect(f"/api/v1/sessions/{source_id}/assist-stream") as socket:
            socket.send_json({"token": token})
            initial = socket.receive_json()
            resynced = socket.receive_json()
            assert initial["type"] == "snapshot" and initial["sequence"] == 0
            assert resynced["type"] == "snapshot" and resynced["sequence"] == 0
            assert calls >= 2
