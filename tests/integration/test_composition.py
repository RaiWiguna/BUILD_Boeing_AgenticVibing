from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.app import create_app
from backend.ports import CompositionOverrides
from backend.replay_contracts import ReplayEventRecord, ReplaySourceManifest


def manifest() -> ReplaySourceManifest:
    return ReplaySourceManifest.model_validate({
        "schema_version": "replay-1",
        "source_id": "composition-source",
        "source_kind": "synthetic",
        "source_ref": "fixture://composition",
        "content_hash": "b" * 64,
        "provenance": {"owner": "test", "version": "1", "derivation": "synthetic", "retention_reason": None},
        "permission_profile": {"reference": "local", "purpose": "test", "processing_scope": "test only"},
        "retention_until": "2027-01-01T00:00:00Z",
        "timebase": {"source_clock": "sim", "source_unit": "ms", "mapping_id": "offset-0",
                      "offset_ms": 0, "uncertainty_ms": 0, "alignment_status": "aligned"},
        "coverage": {"status": "known", "object_ids": ["AC-01"], "channel_ids": ["tower"],
                     "intervals": [{"start_ms": 0, "end_ms": 1000}], "missing_intervals": []},
        "layout": {"id": "fixture-layout", "version": "1", "name": "Local fixture",
                   "coordinate_system": "LOCAL_METRES", "physical_runway_id": "RWY-09-27",
                   "runway": [[0, -20], [1000, -20], [1000, 20], [0, 20]],
                   "protected_area": [[0, -50], [1000, -50], [1000, 50], [0, 50]],
                   "taxiways": [[[0, -100], [1000, -100]]], "hold_lines": [[[400, -60], [430, -60]]],
                   "directions": {"09": "RWY-09-27", "27": "RWY-09-27"}, "note": "Synthetic test only."},
    })


def record(ordinal: int = 1) -> ReplayEventRecord:
    return ReplayEventRecord.model_validate({
        "schema_version": "replay-1", "source_id": "composition-source",
        "source_event_id": f"source-event-{ordinal}",
        "source_time": {"value": ordinal * 100, "unit": "ms", "clock": "sim"},
        "event": {"id": f"source-event-{ordinal}", "ordinal": ordinal, "sim_ms": ordinal * 100,
                  "audit_utc": 1800000000.0, "type": "NOTE", "message": "test record", "data": {}},
        "quality": {"status": "nominal", "reasons": []},
    })


class FakeSource:
    def __init__(self):
        self.calls = []

    def manifest(self):
        self.calls.append(("manifest",))
        return manifest()

    def read(self, after_ordinal: int, until_ms: int | None = None):
        self.calls.append(("read", after_ordinal, until_ms))
        return [record(1), record(2)]


class FakePublicReader:
    def __init__(self):
        self.calls = []
        self.public_frame = {"sim_ms": 200, "session_id": "archived-source", "kind": "training", "tracks": []}

    def metadata(self, source_session_id: str):
        self.calls.append(("metadata", source_session_id))
        return {"id": source_session_id, "status": "ENDED"}

    def frame(self, source_session_id: str, at_ms: int | None = None):
        self.calls.append(("frame", source_session_id, at_ms))
        return self.public_frame.copy()

    def events(self, source_session_id: str, after_ordinal: int = 0, until_ms: int | None = None):
        self.calls.append(("events", source_session_id, after_ordinal, until_ms))
        return [{"ordinal": 1, "sim_ms": 100, "type": "NOTE", "message": "public"}]


class FakeDetector:
    def __init__(self):
        self.calls = []

    def evaluate(self, tracks, clearances, now_ms, config, runway_open, expected_ids, previous_tracks=None):
        self.calls.append((now_ms, tuple(sorted(expected_ids))))
        return {"predictions": [], "candidates": [],
                "runway": {"degraded_ids": [], "data_quality": "NOMINAL", "state": "UNKNOWN"}}


class FakeLifecycle:
    def __init__(self):
        self.calls = []

    def update(self, alerts, result, now_ms, emit_event):
        self.calls.append((now_ms, len(result["candidates"])))


class RecordingWriter:
    def __init__(self, delegate):
        self.delegate = delegate
        self.creates = []
        self.saves = []
        self.command_lookups = []

    def create(self, session_id, metadata):
        self.creates.append(session_id)
        self.delegate.create(session_id, metadata)

    def save(self, session_id, status, events, public_frame, private_checkpoint, command=None):
        self.saves.append((session_id, command, [event["type"] for event in events]))
        self.delegate.save(session_id, status, events, public_frame, private_checkpoint, command)

    def command(self, session_id, command_id):
        self.command_lookups.append((session_id, command_id))
        return self.delegate.command(session_id, command_id)


@dataclass(frozen=True)
class FakeWorkerRequest:
    job_id: str = "job-01"
    attempt_id: str = "attempt-01"
    asset_id: str = "asset-01"
    local_asset_ref: str = "private://validated-local-asset"
    model_version: str = "stub-model-1"
    config_version: str = "stub-config-1"
    public_evidence: tuple[dict, ...] = ()


@dataclass(frozen=True)
class FakeWorkerResult:
    job_id: str
    attempt_id: str
    asset_id: str
    model_version: str
    config_version: str
    status: str = "completed"


class FakeWorker:
    def __init__(self):
        self.calls = []

    def process(self, request: FakeWorkerRequest) -> FakeWorkerResult:
        self.calls.append(request)
        return FakeWorkerResult(request.job_id, request.attempt_id, request.asset_id,
                                request.model_version, request.config_version)


def test_injected_ports_are_used_once_and_control_capabilities_stay_separate(tmp_path):
    source = FakeSource()
    reader = FakePublicReader()
    detector = FakeDetector()
    lifecycle = FakeLifecycle()
    worker = FakeWorker()
    writers = []

    def writer_factory(archive):
        writer = RecordingWriter(archive)
        writers.append(writer)
        return writer

    fixed_clock = lambda: 1_800_000_000.0
    app = create_app(
        db_path=tmp_path / "composition.sqlite3",
        operator_key="injected-test-operator-key",
        run_clock=False,
        ports=CompositionOverrides(
            replay_event_source=source,
            replay_archive_reader=reader,
            session_writer_factory=writer_factory,
            detector=detector,
            alert_lifecycle=lifecycle,
            worker=worker,
        ),
        wall_clock=fixed_clock,
        monotonic_clock=lambda: 42.0,
    )

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/operator", json={"key": "injected-test-operator-key"})
        assert login.status_code == 200
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/v1/sessions", headers=headers,
                              json={"scenario_id": "overlap", "seed": 42, "condition": "flowlens"})
        assert created.status_code == 201
        session_id = created.json()["id"]
        assert created.json()["engine_version"] != created.json()["config_version"]
        assert created.json()["created_utc"] == fixed_clock()

        response = client.post(
            f"/api/v1/sessions/{session_id}/commands",
            headers=headers,
            json={"command_id": "be01-cmd-1", "expected_revision": 0, "type": "CLEARANCE",
                  "target": "ARFF-2", "instruction": "HOLD_SHORT", "runway": "27"},
        )
        assert response.status_code == 200
        assert response.json()["revision"] == 1
        assert response.json()["command_id"] == "be01-cmd-1"

        snapshot = client.get(f"/api/v1/sessions/{session_id}/snapshot", headers=headers).json()
        assert snapshot["kind"] == "training"
        assert snapshot["revision"] == 1
        assert snapshot["server_sent_utc_ms"] == int(fixed_clock() * 1000)
        assert "payload" not in snapshot  # main stream remains a direct snapshot

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as socket:
            socket.send_json({"token": token})
            stream_snapshot = socket.receive_json()
        assert stream_snapshot["kind"] == "training"
        assert stream_snapshot["session_id"] == session_id
        assert "payload" not in stream_snapshot

        ended = client.post(
            f"/api/v1/sessions/{session_id}/commands",
            headers=headers,
            json={"command_id": "be01-end-1", "expected_revision": 1, "type": "END"},
        )
        assert ended.status_code == 200
        branched = client.post(f"/api/v1/sessions/{session_id}/branches", headers=headers, json={"at_ms": 0})
        assert branched.status_code == 201
        branch_id = branched.json()["id"]
        branch_snapshot = client.get(f"/api/v1/sessions/{branch_id}/snapshot", headers=headers).json()
        assert branch_snapshot["kind"] == "training"
        assert branch_snapshot["status"] == "PAUSED"

        review = client.post(f"/api/v1/sessions/{session_id}/reviews", headers=headers)
        assert review.status_code == 201
        review_id = review.json()["id"]
        review_headers = {"Authorization": f"Bearer {review.json()['token']}"}
        review_snapshot = client.get(f"/api/v1/sessions/{review_id}/snapshot", headers=review_headers).json()
        assert review_snapshot["kind"] == "review"
        seek = client.post(
            f"/api/v1/sessions/{review_id}/commands",
            headers=review_headers,
            json={"command_id": "be01-seek-1", "expected_revision": 0, "type": "SEEK", "value": 0},
        )
        assert seek.status_code == 200
        assert seek.json()["revision"] == 1

        manager = app.state.manager
        loaded_manifest, records = manager.read_replay_source(after_ordinal=0, until_ms=300)
        assert loaded_manifest.source_id == "composition-source"
        assert [item.event.ordinal for item in records] == [1, 2]
        public_frame = manager.read_public_frame("archived-source", 100)
        assert public_frame == reader.public_frame
        assert "private_checkpoint" not in public_frame
        assert manager.read_public_events("archived-source", 0, 1000)[0]["type"] == "NOTE"
        worker_result = manager.run_worker(FakeWorkerRequest())
        assert worker_result.status == "completed"
        assert len(worker.calls) == 1
        assert not hasattr(worker.calls[0], "command")
        assert not hasattr(worker.calls[0], "database")

    assert len(writers) == 1
    assert writers[0].creates == [session_id, branch_id]
    assert len(writers[0].saves) == 4  # session, two commands, and one restored branch frame
    assert [bool(item[1]) for item in writers[0].saves] == [False, True, True, False]
    assert writers[0].command_lookups == [(session_id, "be01-cmd-1"), (session_id, "be01-end-1")]
    assert len(detector.calls) == len(lifecycle.calls) == 4
    assert source.calls == [("manifest",), ("read", 0, 300)]
    assert [call[0] for call in reader.calls] == ["frame", "events"]


def test_legacy_synthetic_app_login_stream_and_baseline_redaction_remain_compatible(tmp_path):
    fixed_clock = lambda: 1_800_000_100.0
    app = create_app(
        db_path=tmp_path / "compatibility.sqlite3",
        operator_key="compatibility-test-key",
        run_clock=False,
        wall_clock=fixed_clock,
        monotonic_clock=lambda: 84.0,
    )

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/operator", json={"key": "compatibility-test-key"})
        assert login.status_code == 200
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/v1/sessions", headers=headers,
                              json={"scenario_id": "overlap", "seed": 42, "condition": "baseline"})
        assert created.status_code == 201
        session_id = created.json()["id"]
        snapshot = client.get(f"/api/v1/sessions/{session_id}/snapshot", headers=headers).json()
        assert snapshot["kind"] == "training"
        assert snapshot["predictions"] == []
        assert snapshot["metadata"]["condition"] == "baseline"
        assert snapshot["metadata"]["engine_version"] == "0.1.0"
        assert snapshot["metadata"]["config_version"] == "lab-sop-1"

        assessment = client.post(
            f"/api/v1/sessions/{session_id}/assessments", headers=headers,
            json={"type": "bookmark", "text": "instructor-only note", "values": {}},
        )
        assert assessment.status_code == 201
        seat = client.post(
            f"/api/v1/sessions/{session_id}/seats", headers=headers,
            json={"role": "ground", "label": "Ground 1"},
        )
        assert seat.status_code == 201
        ground_headers = {"Authorization": f"Bearer {seat.json()['token']}"}
        ground_snapshot = client.get(f"/api/v1/sessions/{session_id}/snapshot", headers=ground_headers).json()
        assert ground_snapshot["assessments"] == []
        assert all(event["type"] != "ASSESSMENT" for event in ground_snapshot["events"])

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as socket:
            socket.send_json({"token": token})
            stream_snapshot = socket.receive_json()
        assert stream_snapshot["kind"] == "training"
        assert stream_snapshot["session_id"] == session_id
        assert stream_snapshot["predictions"] == []

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as socket:
            socket.send_json({"token": "invalid"})
            with pytest.raises(WebSocketDisconnect):
                socket.receive_json()

        reader = app.state.manager.replay_archive_reader
        archived_projection = app.state.manager.read_public_frame(session_id)
        assert archived_projection is not None
        assert "private" not in archived_projection
        assert "simulator" not in archived_projection
        assert not hasattr(reader, "checkpoint")
