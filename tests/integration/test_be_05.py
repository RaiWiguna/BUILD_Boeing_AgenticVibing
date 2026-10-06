"""BE-05 private audio asset and worker lifecycle integration checks."""

from __future__ import annotations

import hashlib
import io
import json
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.assist_service import AssistJobConfig, PrivateWorkerRequest
from backend.ports import CompositionOverrides

OPERATOR_KEY = "be05-integration-test-operator-key"
JOB_CONFIG = AssistJobConfig(
    provider="test-stub",
    model="no-inference-stub",
    version="stub-v1",
    config_version="test-config-v1",
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


@dataclass(frozen=True)
class WorkerResult:
    job_id: str
    attempt_id: str
    asset_id: str
    model_version: str
    config_version: str
    status: str


class ImmediateWorker:
    def __init__(self, status: str = "completed") -> None:
        self.status = status
        self.requests: list[PrivateWorkerRequest] = []
        self.file_checks: list[bool] = []
        self._lock = threading.Lock()

    def process(self, request: PrivateWorkerRequest) -> WorkerResult:
        assert isinstance(request, PrivateWorkerRequest)
        path = Path(request.local_asset_ref)
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == request.asset_hash
        forbidden = {"archive", "db", "operator_token", "private_checkpoint", "simulator_truth", "command"}
        assert forbidden.isdisjoint(vars(request))
        with self._lock:
            self.requests.append(request)
            self.file_checks.append(path.is_file())
        return WorkerResult(
            request.job_id,
            request.attempt_id,
            request.asset_id,
            request.model_version,
            request.config_version,
            self.status,
        )


class GateWorker:
    """First call blocks in its own worker thread; later calls complete immediately."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release_first = threading.Event()
        self.requests: list[PrivateWorkerRequest] = []
        self._lock = threading.Lock()

    def process(self, request: PrivateWorkerRequest) -> WorkerResult:
        with self._lock:
            index = len(self.requests)
            self.requests.append(request)
        if index == 0:
            self.started.set()
            self.release_first.wait(timeout=3)
        return WorkerResult(
            request.job_id,
            request.attempt_id,
            request.asset_id,
            request.model_version,
            request.config_version,
            "completed",
        )


def _record(source_id: str, ordinal: int, sim_ms: int) -> dict[str, Any]:
    event_id = f"evt-{ordinal}"
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
            "message": f"Synthetic fixture track {ordinal}.",
            "target": "AC101",
            "observed_ms": sim_ms,
            "received_ms": sim_ms,
            "track": {
                "id": "AC101",
                "callsign": "SYN101",
                "kind": "aircraft",
                "x_m": 100.0 + ordinal,
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


def _bundle(source_id: str) -> tuple[dict[str, Any], bytes, bytes]:
    records = [_record(source_id, 0, 100), _record(source_id, 1, 1000)]
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
            "derivation": "authored synthetic BE-05 integration fixture",
            "retention_reason": "temporary test data",
        },
        "permission_profile": {
            "reference": "local-synthetic-fixture",
            "purpose": "BE-05 fixture validation",
            "processing_scope": "temporary TestClient and SQLite test harness",
        },
        "retention_until": None,
        "timebase": {
            "source_clock": "fixture-clock",
            "source_unit": "ms",
            "mapping_id": "fixture-fixed-offset-v1",
            "offset_ms": 0,
            "uncertainty_ms": 0,
            "alignment_status": "aligned",
        },
        "coverage": {
            "status": "known",
            "object_ids": ["AC101"],
            "channel_ids": ["surface"],
            "intervals": [{"start_ms": 0, "end_ms": 1000}],
            "missing_intervals": [],
        },
        "layout": {
            "id": "be05-fixture-layout",
            "version": "1",
            "name": "BE-05 synthetic fixture layout",
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
    with wave.open(stream, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frames)
    return stream.getvalue()


def _asset_metadata(manifest: dict[str, Any], source_ref: str | None = None) -> dict[str, Any]:
    return {
        "source_kind": manifest["source_kind"],
        "source_ref": source_ref or manifest["source_id"],
        "channel_id": "surface",
        "audio_start": 100,
        "timebase": manifest["timebase"],
        "provenance": manifest["provenance"],
        "permission_profile": manifest["permission_profile"],
        "retention_until": manifest["retention_until"],
    }


def _operator(client: TestClient) -> str:
    response = client.post("/api/v1/auth/operator", json={"key": OPERATOR_KEY})
    assert response.status_code == 200
    return response.json()["token"]


def _import_source(client: TestClient, token: str, source_id: str) -> tuple[dict[str, Any], str]:
    manifest, manifest_bytes, event_bytes = _bundle(source_id)
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


def _upload(
    client: TestClient,
    token: str,
    source_session_id: str,
    metadata: dict[str, Any],
    audio: bytes | None = None,
    *,
    filename: str = "fixture.wav",
    content_type: str = "audio/wav",
) -> Any:
    return client.post(
        f"/api/v1/sessions/{source_session_id}/audio-assets",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio": (filename, audio if audio is not None else _wav(), content_type)},
        data={"metadata": json.dumps(metadata)},
    )


def _wait_until(predicate, timeout_s: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def _app(
    tmp_path: Path,
    *,
    clock: FakeClock | None = None,
    worker: Any = None,
    job_config: AssistJobConfig | None = None,
    run_clock: bool = False,
) -> TestClient:
    fake_clock = clock or FakeClock()
    app = create_app(
        db_path=tmp_path / "be05.sqlite3",
        operator_key=OPERATOR_KEY,
        run_clock=run_clock,
        ports=CompositionOverrides(worker=worker),
        wall_clock=fake_clock.wall_time,
        monotonic_clock=fake_clock.monotonic_time,
        audio_root=tmp_path / "private-audio",
        assist_config=job_config,
    )
    return TestClient(app)


def test_valid_upload_commits_private_file_asset_job_and_attempt_before_worker_dispatch(tmp_path: Path) -> None:
    worker = ImmediateWorker()
    with _app(tmp_path, worker=worker, job_config=JOB_CONFIG) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be05-commit-source")
        response = _upload(client, token, source_id, _asset_metadata(manifest))
        assert response.status_code == 201, response.text
        body = response.json()
        asset, job = body["asset"], body["job"]
        assert asset["hash"] == hashlib.sha256(_wav()).hexdigest()
        assert asset["duration_ms"] == 200
        assert asset["source_ref"] == manifest["source_id"]
        assert job["asset_id"] == asset["id"]
        assert job["attempts"][0]["attempt_id"] == job["attempt_id"]

        manager = client.app.state.manager
        stored_asset = manager.archive.db.execute(
            "SELECT metadata_json FROM assist_audio_assets WHERE asset_id=?", (asset["id"],)
        ).fetchone()
        stored_job = manager.assist_service.get_job(source_id, job["id"])
        assert stored_asset is not None and stored_job is not None
        assert stored_job["attempts"]
        assert not manager.archive.db.in_transaction
        private_audio = tmp_path / "private-audio" / f"{asset['id']}.wav"
        assert private_audio.is_file()
        serialized = json.dumps(body)
        assert str(tmp_path) not in serialized
        assert "local_asset_ref" not in serialized

        assert _wait_until(lambda: len(worker.requests) == 1)
        request = worker.requests[0]
        assert request.job_id == job["id"]
        assert request.attempt_id == job["attempt_id"]
        assert worker.file_checks == [True]
        assert not hasattr(request, "archive")
        assert not hasattr(request, "db")
        final_job = client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert final_job.status_code == 200
        assert final_job.json()["status"] == "completed"


def test_invalid_audio_metadata_hash_relation_and_permission_leave_no_partial_rows_or_dispatch(tmp_path: Path) -> None:
    worker = ImmediateWorker()
    with _app(tmp_path, worker=worker, job_config=JOB_CONFIG) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be05-invalid-source")
        base = _asset_metadata(manifest)
        cases = [
            (base, b"not a wav", "fixture.wav", "audio/wav"),
            (base | {"hash": "0" * 64}, _wav(), "fixture.wav", "audio/wav"),
            (_asset_metadata(manifest, "another-source"), _wav(), "fixture.wav", "audio/wav"),
            (base | {"permission_profile": base["permission_profile"] | {"purpose": "production inference"}},
             _wav(), "fixture.wav", "audio/wav"),
            (base | {"timebase": base["timebase"] | {"offset_ms": 50}}, _wav(), "fixture.wav", "audio/wav"),
            (base | {"channel_id": "private-channel"}, _wav(), "fixture.wav", "audio/wav"),
            (base, _wav(), "fixture.mp3", "audio/mpeg"),
        ]
        for metadata, audio, filename, content_type in cases:
            response = _upload(
                client, token, source_id, metadata, audio, filename=filename, content_type=content_type
            )
            assert response.status_code == 422, response.text
        malformed_json = client.post(
            f"/api/v1/sessions/{source_id}/audio-assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"audio": ("fixture.wav", _wav(), "audio/wav")},
            data={"metadata": "{broken"},
        )
        assert malformed_json.status_code == 422
        db = client.app.state.manager.archive.db
        assert db.execute("SELECT COUNT(*) FROM assist_audio_assets").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM transcription_jobs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM transcription_attempts").fetchone()[0] == 0
        assert list((tmp_path / "private-audio").iterdir()) == []
        assert worker.requests == []


def test_private_playback_and_source_read_token_scope_expiry_and_write_denials(tmp_path: Path) -> None:
    clock = FakeClock()
    with _app(tmp_path, clock=clock) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be05-audio-scope")
        _, other_source_id = _import_source(client, token, "be05-audio-other")
        uploaded = _upload(client, token, source_id, _asset_metadata(manifest))
        assert uploaded.status_code == 201
        asset_id = uploaded.json()["asset"]["id"]
        review = client.post(
            f"/api/v1/sessions/{source_id}/reviews", headers={"Authorization": f"Bearer {token}"}
        )
        assert review.status_code == 201
        source_read = review.json()["source_read_token"]
        source_headers = {"Authorization": f"Bearer {source_read}"}

        playback = client.get(
            f"/api/v1/sessions/{source_id}/audio-assets/{asset_id}/content", headers=source_headers
        )
        assert playback.status_code == 200
        assert playback.content == _wav()
        assert playback.headers["content-type"].startswith("audio/wav")
        assert str(tmp_path) not in playback.headers.get("content-disposition", "")
        job_id = uploaded.json()["job"]["id"]
        assert client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job_id}", headers=source_headers
        ).status_code == 200
        cross_source = client.get(
            f"/api/v1/sessions/{other_source_id}/audio-assets/{asset_id}/content", headers=source_headers
        )
        assert cross_source.status_code == 403

        forbidden = [
            (f"/api/v1/sessions/{source_id}/snapshot", "get", None),
            (f"/api/v1/sessions/{source_id}/commands", "post", {"command_id": "src-write", "expected_revision": 0, "type": "START"}),
            (f"/api/v1/sessions/{source_id}/seats", "post", {"role": "tower", "label": "seat"}),
            (f"/api/v1/sessions/{source_id}/branches", "post", {"at_ms": 100}),
        ]
        for path, method, payload in forbidden:
            if method == "get":
                response = client.get(path, headers=source_headers)
            else:
                response = client.post(path, headers=source_headers, json=payload)
            assert response.status_code == 403
        for action in ("cancel", "retry"):
            response = client.post(
                f"/api/v1/sessions/{source_id}/transcription-jobs/{job_id}/{action}",
                headers=source_headers,
            )
            assert response.status_code == 403
        source_token_upload = _upload(client, source_read, source_id, _asset_metadata(manifest))
        assert source_token_upload.status_code == 403
        blocked_import = client.post(
            "/api/v1/replay-imports",
            headers=source_headers,
            files={"manifest": ("m.json", b"{}", "application/json"), "events": ("e.jsonl", b"", "text/plain")},
        )
        assert blocked_import.status_code == 403

        clock.wall += 8 * 3600 + 1
        expired = client.get(
            f"/api/v1/sessions/{source_id}/audio-assets/{asset_id}/content", headers=source_headers
        )
        assert expired.status_code == 401


def test_cancel_timeout_retry_and_stale_worker_result_cannot_change_active_attempt(tmp_path: Path) -> None:
    clock = FakeClock()
    worker = GateWorker()
    config = AssistJobConfig(
        provider="test-stub", model="stub", version="v1", config_version="cfg1", timeout_s=2.0
    )
    with _app(tmp_path, clock=clock, worker=worker, job_config=config) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be05-lifecycle-source")
        uploaded = _upload(client, token, source_id, _asset_metadata(manifest))
        assert uploaded.status_code == 201
        original = uploaded.json()["job"]
        assert worker.started.wait(timeout=1)

        clock.monotonic += 3.0
        timed_out = client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{original['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert timed_out.status_code == 200
        assert timed_out.json()["status"] == "failed"
        assert timed_out.json()["error"]["code"] == "timeout"
        old_attempt = timed_out.json()["attempts"][0]
        assert old_attempt["status"] == "failed"
        assert old_attempt["attempt_id"] == original["attempt_id"]

        retried = client.post(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{original['id']}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retried.status_code == 202
        new_job = retried.json()
        assert new_job["attempt_id"] != original["attempt_id"]
        assert len(new_job["attempts"]) == 2
        assert _wait_until(lambda: client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{original['id']}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["status"] == "completed")

        # Let the timed-out thread return a successful but obsolete result.
        worker.release_first.set()
        time.sleep(0.05)
        final_job = client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{original['id']}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert final_job["status"] == "completed"
        assert final_job["attempt_id"] == new_job["attempt_id"]
        assert final_job["attempts"][0]["status"] == "failed"
        assert final_job["attempts"][1]["status"] == "completed"


def test_explicit_cancel_is_terminal_and_slow_worker_does_not_block_reads_or_clock(tmp_path: Path) -> None:
    clock = FakeClock()
    worker = GateWorker()
    with _app(tmp_path, clock=clock, worker=worker, job_config=JOB_CONFIG, run_clock=True) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be05-slow-source")
        uploaded = _upload(client, token, source_id, _asset_metadata(manifest))
        assert uploaded.status_code == 201
        job = uploaded.json()["job"]
        assert worker.started.wait(timeout=1)

        replay_read = client.get(
            f"/api/v1/sessions/{source_id}/replay-source", headers={"Authorization": f"Bearer {token}"}
        )
        assert replay_read.status_code == 200
        cancelled = client.post(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job['id']}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        created = client.post(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={"scenario_id": "overlap", "seed": 8},
        )
        assert created.status_code == 201
        session_id = created.json()["id"]
        started = client.post(
            f"/api/v1/sessions/{session_id}/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={"command_id": "be05-clock-start", "expected_revision": 0, "type": "START"},
        )
        assert started.status_code == 200
        assert _wait_until(lambda: session_id in client.app.state.manager.last)
        clock.monotonic += 1.0
        assert _wait_until(lambda: client.get(
            f"/api/v1/sessions/{session_id}/snapshot", headers={"Authorization": f"Bearer {token}"}
        ).json().get("sim_ms", 0) > 0)

        worker.release_first.set()
        time.sleep(0.05)
        still_cancelled = client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert still_cancelled.status_code == 200
        assert still_cancelled.json()["status"] == "cancelled"


def test_default_missing_worker_is_explicit_and_be04_routes_remain_compatible(tmp_path: Path) -> None:
    with _app(tmp_path) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be05-no-provider-source")
        uploaded = _upload(client, token, source_id, _asset_metadata(manifest))
        assert uploaded.status_code == 201
        job = uploaded.json()["job"]
        assert job["status"] == "failed"
        assert job["error"]["code"] == "job_configuration_unavailable"
        assert job["provider"] is None
        assert not job["attempts"][0]["started_utc"]

        review = client.post(
            f"/api/v1/sessions/{source_id}/reviews", headers={"Authorization": f"Bearer {token}"}
        )
        assert review.status_code == 201
        assert client.get(
            f"/api/v1/sessions/{source_id}/replay-source",
            headers={"Authorization": f"Bearer {review.json()['source_read_token']}"},
        ).status_code == 200

        created = client.post(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={"scenario_id": "overlap", "seed": 3},
        )
        assert created.status_code == 201
        session_id = created.json()["id"]
        command = client.post(
            f"/api/v1/sessions/{session_id}/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={"command_id": "be05-compat-start", "expected_revision": 0, "type": "START"},
        )
        assert command.status_code == 200
        snapshot = client.get(
            f"/api/v1/sessions/{session_id}/snapshot", headers={"Authorization": f"Bearer {token}"}
        )
        assert snapshot.status_code == 200
        assert snapshot.json()["kind"] == "training"
        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as socket:
            socket.send_json({"token": token})
            assert socket.receive_json()["session_id"] == session_id


def test_worker_reported_failure_is_safe_and_terminal(tmp_path: Path) -> None:
    worker = ImmediateWorker(status="failed")
    with _app(tmp_path, worker=worker, job_config=JOB_CONFIG) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be05-worker-failure-source")
        uploaded = _upload(client, token, source_id, _asset_metadata(manifest))
        assert uploaded.status_code == 201
        job_id = uploaded.json()["job"]["id"]
        assert _wait_until(lambda: client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["status"] == "failed")
        job = client.get(
            f"/api/v1/sessions/{source_id}/transcription-jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert job["error"] == {"code": "worker_failed", "message": "Worker could not process this asset."}
        assert job["attempts"][0]["status"] == "failed"
        serialized = json.dumps(job)
        assert "segments" not in serialized
        assert "transcript" not in serialized
