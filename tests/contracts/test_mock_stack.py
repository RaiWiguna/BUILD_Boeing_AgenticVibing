from __future__ import annotations

import hashlib
import json
import socket
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from scripts import run_mock_stack as launcher


@pytest.fixture(scope="module")
def fixture_profile() -> launcher.FixtureProfile:
    return launcher.load_fixture(launcher.FIXTURE_ID)


def test_public_fixture_profile_is_validated_without_private_fixture_reads(fixture_profile):
    assert fixture_profile.fixture_id == "F-COMM-01"
    assert fixture_profile.manifest["label"] == launcher.SYNTHETIC_LABEL
    assert fixture_profile.replay_manifest["label"] == launcher.SYNTHETIC_LABEL
    assert fixture_profile.manifest["source_bundle_id"] == "F-REPLAY-01"
    assert fixture_profile.manifest["audio_bytes_available"] is False
    assert fixture_profile.manifest["provider_readiness"]["status"] == "unavailable"
    assert all("private" not in path.parts for path in fixture_profile.files_read)
    assert all(path.parts[-2] in {"assist", "replay"} for path in fixture_profile.files_read)
    assert not any(path.name == "benchmark-manifest.json" for path in fixture_profile.files_read)


def test_unknown_fixture_and_non_allowlisted_profile_are_rejected(tmp_path):
    with pytest.raises(launcher.FixtureValidationError, match="Unknown public fixture"):
        launcher.load_fixture("F-PRIVATE-01", tmp_path)
    with pytest.raises(launcher.FixtureValidationError, match="Unknown public fixture"):
        launcher.load_fixture("../private/manifest.json", tmp_path)


def test_crlf_hash_diagnostic_keeps_exact_byte_mismatch_visible(tmp_path):
    content = b'{"label":"synthetic"}\r\n'
    expected = hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()
    (tmp_path / "public.json").write_bytes(content)
    paths, exact_mismatches = launcher._verify_fixture_files(
        tmp_path,
        {"artifact_hashes": {"public.json": expected}},
        {"public.json"},
    )
    assert paths["public.json"].read_bytes() == content
    assert exact_mismatches == ("public.json",)


def test_vite_child_environment_and_proxy_are_fixture_loopback_only(tmp_path, monkeypatch):
    monkeypatch.setenv("VITE_FLOWLENS_MODE", "api")
    monkeypatch.setenv("OPERATOR_KEY", "local-secret-must-not-be-inherited")
    monkeypatch.setenv("API_TOKEN", "local-token-must-not-be-inherited")
    environment = launcher._safe_vite_environment(tmp_path)
    assert environment["VITE_FLOWLENS_MODE"] == "fixture"
    assert environment["VITE_FLOWLENS_FIXTURE_VIEW"] == "evaluator"
    assert "OPERATOR_KEY" not in environment
    assert "API_TOKEN" not in environment
    assert set(environment).issubset({
        "PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "COMSPEC", "PROCESSOR_ARCHITECTURE",
        "HOME", "USERPROFILE", "TEMP", "TMP", "VITE_FLOWLENS_MODE", "VITE_FLOWLENS_FIXTURE_VIEW",
    })
    config = launcher._vite_config_source(Path("frontend"), tmp_path, 8000, 5173)
    assert "host: '127.0.0.1'" in config
    assert "http://127.0.0.1:8000" in config
    assert "localhost" not in config


def test_http_projection_auth_scope_and_no_derived_safety_claim(fixture_profile):
    runtime = launcher.MockStackRuntime(fixture_profile, api_port=0, web_port=0)
    try:
        with TestClient(runtime.app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["mode"] == "fixture-mock"
            assert health.json()["label"] == launcher.SYNTHETIC_LABEL
            assert health.headers["x-flowlens-mode"] == "fixture-mock"
            assert health.headers["x-flowlens-data-label"] == launcher.SYNTHETIC_LABEL

            assert client.get("/api/v1/sessions").status_code == 401
            assert client.post("/api/v1/auth/operator", json={"key": "not-the-run-key"}).status_code == 401
            login = client.post("/api/v1/auth/operator", json={"key": runtime.credentials.operator_key})
            assert login.status_code == 200
            assert login.json()["token"] == runtime.credentials.operator_token
            assert runtime.credentials.operator_key not in health.text

            bearer = {"Authorization": f"Bearer {runtime.credentials.source_read_token}"}
            sessions = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {runtime.credentials.operator_token}"})
            assert sessions.status_code == 200
            assert sessions.json()["items"][0]["id"] == "SYN-COMM-01"

            snapshot = client.get("/api/v1/sessions/SYN-COMM-01/snapshot", headers=bearer)
            assert snapshot.status_code == 200
            body = snapshot.json()
            assert body["metadata"]["condition"] == "synthetic-fixture"
            assert body["runway"]["state"] == "UNKNOWN"
            assert body["runway"]["data_quality"] == "unknown"
            assert body["predictions"] == []
            assert body["alerts"] == []
            assert body["metadata"]["config"]["analysis_status"] == "unavailable"
            assert client.get("/api/v1/sessions/SYN-COMM-01/replay-source", headers=bearer).json()["label"] == launcher.SYNTHETIC_LABEL

            # No control/command or execution path is exposed by the fixture stack.
            command = client.post("/api/v1/sessions/SYN-COMM-01/commands", headers=bearer, json={"type": "START"})
            assert command.status_code == 405
            assert "command or control path" in command.json()["detail"]
    finally:
        runtime.close()


def test_public_frame_cutoff_preserves_source_only_unknown_analysis(fixture_profile):
    runtime = launcher.MockStackRuntime(fixture_profile, api_port=0, web_port=0)
    try:
        with TestClient(runtime.app) as client:
            headers = {"Authorization": f"Bearer {runtime.credentials.source_read_token}"}
            before_clearance = client.get(
                "/api/v1/sessions/SYN-COMM-01/replay-frame?at_ms=73019", headers=headers,
            ).json()
            assert before_clearance["frame_ms"] == 72400
            assert before_clearance["tracks"] == []
            assert before_clearance["predictions"] is None
            assert before_clearance["alert_analysis"] is None
            assert before_clearance["analysis_status"] == "unavailable"

            at_track_receipt = client.get(
                "/api/v1/sessions/SYN-COMM-01/replay-frame?at_ms=74530", headers=headers,
            ).json()
            assert at_track_receipt["frame_ms"] == 74530
            assert [track["event_id"] for track in at_track_receipt["tracks"]] == ["EVT-TRK-088"]
            assert at_track_receipt["frame_ms"] <= at_track_receipt["requested_ms"]
            assert at_track_receipt["quality"] == "unknown"

            events = client.get("/api/v1/sessions/SYN-COMM-01/events?cursor=0&limit=50", headers=headers).json()
            assert [row["ordinal"] for row in events["items"]] == [1, 2]
            assert events["next_cursor"] == 2
    finally:
        runtime.close()


def test_assist_projection_keeps_stub_possible_link_and_audio_unavailable(fixture_profile):
    runtime = launcher.MockStackRuntime(fixture_profile, api_port=0, web_port=0)
    try:
        with TestClient(runtime.app) as client:
            source_headers = {"Authorization": f"Bearer {runtime.credentials.source_read_token}"}
            reviewer_headers = {"Authorization": f"Bearer {runtime.credentials.review_token}"}
            before_segment = client.get(
                "/api/v1/sessions/SYN-COMM-01/transcripts?until_ms=72399", headers=source_headers,
            ).json()
            assert before_segment["items"] == []
            transcript = client.get(
                "/api/v1/sessions/SYN-COMM-01/transcripts?until_ms=72400", headers=source_headers,
            ).json()
            assert transcript["items"][0]["id"] == "SEG-TWR-006"
            assert transcript["items"][0]["session_start_ms"] == 72400
            assert "stub" in transcript["items"][0]["text"]

            highlights = client.get("/api/v1/sessions/SYN-COMM-01/highlights", headers=source_headers).json()
            assert highlights["items"][0]["link_status"] == "possible_link"
            assert client.get(
                "/api/v1/sessions/SYN-COMM-01/replay-analyses/AN-SYN-01/options", headers=source_headers,
            ).status_code == 403
            options = client.get(
                "/api/v1/sessions/SYN-COMM-01/replay-analyses/AN-SYN-01/options", headers=reviewer_headers,
            ).json()
            assert options["analysis"]["status"] == "fixture_only"
            assert options["items"][0]["review_status"] == "unresolved"
            assert not launcher.FORBIDDEN_OPTION_KEYS.intersection(options["items"][0])

            audio = client.get(
                "/api/v1/sessions/SYN-COMM-01/audio-assets/AUD-SYN-01/content", headers=source_headers,
            )
            assert audio.status_code == 404
            assert "audio bytes are unavailable" in audio.json()["detail"]

            failed_job = client.get(
                "/api/v1/sessions/SYN-COMM-01/transcription-jobs/JOB-SYN-001", headers=source_headers,
            )
            assert failed_job.status_code == 200
            assert failed_job.json()["status"] == "failed"
            assert "provider_unavailable" in failed_job.json()["error"]
            transcript_with_job = client.get(
                "/api/v1/sessions/SYN-COMM-01/transcripts", headers=source_headers,
            ).json()
            assert transcript_with_job["job"]["status"] == "failed"

            variants = client.get("/api/v1/mock/variants", headers=reviewer_headers).json()
            assert variants["label"] == launcher.SYNTHETIC_LABEL
            assert "assist-sequence-gap" in variants["available"]
            same_time = client.get(
                "/api/v1/mock/variants/same-time-events", headers=source_headers,
            )
            rows = same_time.json()["events"]
            assert same_time.headers["x-flowlens-mode"] == "fixture-mock"
            assert same_time.json()["variant_only"] is True
            assert len({row["sim_ms"] for row in rows}) == 1
            assert [row["ordinal"] for row in rows] == sorted(row["ordinal"] for row in rows)
    finally:
        runtime.close()


def test_websocket_profiles_authenticate_first_message_and_send_fixture_snapshots(fixture_profile):
    runtime = launcher.MockStackRuntime(fixture_profile, api_port=0, web_port=0)
    try:
        with TestClient(runtime.app) as client:
            with client.websocket_connect("/api/v1/sessions/SYN-COMM-01/stream") as websocket:
                websocket.send_json({"token": runtime.credentials.source_read_token})
                message = websocket.receive_json()
                assert message["source_session_id"] == "SYN-COMM-01"
                assert message["runway"]["data_quality"] == "unknown"

            with client.websocket_connect("/api/v1/sessions/SYN-COMM-01/assist-stream") as websocket:
                websocket.send_json({"token": runtime.credentials.source_read_token, "analysis_id": "AN-SYN-01"})
                message = websocket.receive_json()
                assert message["schema_version"] == "assist-1"
                assert message["type"] == "snapshot"
                assert message["payload"]["highlights"][0]["link_status"] == "possible_link"

            with client.websocket_connect(
                "/api/v1/sessions/SYN-COMM-01/assist-stream?variant=assist-sequence-gap",
            ) as websocket:
                websocket.send_json({"token": runtime.credentials.source_read_token})
                assert websocket.receive_json()["sequence"] == 1
                gap = websocket.receive_json()
                assert gap["sequence"] == 3
                assert gap["type"] == "option"

            with client.websocket_connect(
                "/api/v1/sessions/SYN-COMM-01/assist-stream?variant=duplicate-assist-sequence",
            ) as websocket:
                websocket.send_json({"token": runtime.credentials.source_read_token})
                assert websocket.receive_json()["sequence"] == 1
                duplicate_a = websocket.receive_json()
                duplicate_b = websocket.receive_json()
                assert duplicate_a["sequence"] == duplicate_b["sequence"] == 1

            with client.websocket_connect("/api/v1/sessions/SYN-COMM-01/stream") as websocket:
                websocket.send_json({"token": "invalid"})
                with pytest.raises(WebSocketDisconnect) as closed:
                    websocket.receive_json()
                assert closed.value.code == 4401

            with client.websocket_connect(
                "/api/v1/sessions/SYN-COMM-01/stream?variant=expired-stream-auth",
            ) as websocket:
                websocket.send_json({"token": runtime.credentials.source_read_token})
                assert websocket.receive_json()["source_session_id"] == "SYN-COMM-01"
                with pytest.raises(WebSocketDisconnect) as expired:
                    websocket.receive_json()
                assert expired.value.code == 4401
    finally:
        runtime.close()


def test_occupied_port_and_vite_startup_failure_release_temp_state(fixture_profile, monkeypatch):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((launcher.LOOPBACK, 0))
    occupied_port = listener.getsockname()[1]
    runtime = launcher.MockStackRuntime(fixture_profile, api_port=occupied_port, web_port=0)
    temp_root = runtime.temp_root
    try:
        with pytest.raises(OSError):
            runtime.start_api()
    finally:
        runtime.close()
        listener.close()
    assert not temp_root.exists()

    failing = launcher.MockStackRuntime(fixture_profile, api_port=0, web_port=0)
    temp_root = failing.temp_root
    failing.start_api()
    monkeypatch.setattr(launcher.shutil, "which", lambda _: None)
    with pytest.raises(launcher.StackStartupError, match="Node.js is unavailable"):
        failing.start_frontend()
    api_thread = failing._server_thread
    failing.close()
    assert not temp_root.exists()
    assert api_thread is not None and not api_thread.is_alive()


def test_per_run_credentials_are_isolated_and_not_left_after_cleanup(fixture_profile):
    first = launcher.MockStackRuntime(fixture_profile, api_port=0, web_port=0)
    second = launcher.MockStackRuntime(fixture_profile, api_port=0, web_port=0)
    first_root = first.temp_root
    first_credential_file = first.storage_root / "mock-test-credentials.json"
    try:
        assert first.credentials.operator_key != second.credentials.operator_key
        assert first.credentials.operator_token != second.credentials.operator_token
        assert first_credential_file.is_file()
        saved = json.loads(first_credential_file.read_text(encoding="utf-8"))
        assert saved["operator_key"] == first.credentials.operator_key
        assert saved["operator_token"] == first.credentials.operator_token
    finally:
        first.close()
        second.close()
    assert not first_root.exists()


def test_child_process_tree_is_stopped_and_reaped(tmp_path):
    child = launcher._spawn_process(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        environment=launcher._safe_vite_environment(tmp_path),
    )
    launcher.stop_child_process(child, timeout_s=0.5)
    assert child.poll() is not None


def test_ctrl_c_path_stops_server_and_removes_per_run_resources(fixture_profile, monkeypatch, capsys):
    def free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((launcher.LOOPBACK, 0))
            return probe.getsockname()[1]

    runtime_type = launcher.MockStackRuntime
    instances = []

    def capture_runtime(*args, **kwargs):
        runtime = runtime_type(*args, **kwargs)
        instances.append(runtime)
        return runtime

    def interrupt_before_frontend(_runtime):
        raise KeyboardInterrupt

    monkeypatch.setattr(launcher, "MockStackRuntime", capture_runtime)
    monkeypatch.setattr(runtime_type, "start_frontend", interrupt_before_frontend)
    result = launcher.main([
        "--fixture", "F-COMM-01", "--api-port", str(free_port()), "--web-port", str(free_port()),
    ])
    assert result == 0
    assert "Stopping mock stack" in capsys.readouterr().out
    runtime = instances[0]
    assert not runtime.temp_root.exists()
    assert runtime._server_thread is not None and not runtime._server_thread.is_alive()
