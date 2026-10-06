"""Synthetic/stub integration of BE-01 replay ports with the BE-02 reducer."""

from __future__ import annotations

import socket
import sqlite3

from backend.models import SimulationConfig
from backend.replay_contracts import ReplayEventRecord, ReplaySourceManifest
from backend.replay_source import ReplaySourceReader, build_replay_analysis

SOURCE_ID = "synthetic-analysis-source"


def _manifest() -> ReplaySourceManifest:
    return ReplaySourceManifest.model_validate({
        "schema_version": "replay-1",
        "source_id": SOURCE_ID,
        "source_kind": "synthetic",
        "source_ref": "fixture://be-02-integration",
        "content_hash": "d" * 64,
        "provenance": {"owner": "integration fixture", "version": "fixture-2",
                       "derivation": "inline synthetic fixture", "retention_reason": None},
        "permission_profile": {"reference": "local-synthetic", "purpose": "integration test",
                                "processing_scope": "test only"},
        "retention_until": "2027-01-01T00:00:00Z",
        "timebase": {"source_clock": "fixture-clock", "source_unit": "ms", "mapping_id": "offset-0",
                     "offset_ms": 0, "uncertainty_ms": 0, "alignment_status": "aligned"},
        "coverage": {"status": "known", "object_ids": ["AC-01"], "channel_ids": ["tower"],
                     "intervals": [{"start_ms": 0, "end_ms": 1000}], "missing_intervals": []},
        "layout": {"id": "fixture-layout", "version": "layout-2", "name": "Synthetic test layout",
                   "coordinate_system": "LOCAL_METRES", "physical_runway_id": "RWY-TEST",
                   "runway": [[0, -20], [3000, -20], [3000, 20], [0, 20]],
                   "protected_area": [[0, -75], [3000, -75], [3000, 75], [0, 75]],
                   "taxiways": [[[0, -160], [3000, -160]]],
                   "hold_lines": [[[1470, -95], [1530, -95]]],
                   "directions": {"09": "RWY-TEST", "27": "RWY-TEST"},
                   "note": "Synthetic fixture only; not domain reviewed."},
    })


def _record(
    ordinal: int,
    event_type: str,
    *,
    sim_ms: int,
    source_event_id: str | None = None,
    target: str | None = None,
    data: dict | None = None,
) -> ReplayEventRecord:
    event_id = source_event_id or f"fixture-{ordinal}"
    event: dict = {"id": event_id, "ordinal": ordinal, "sim_ms": sim_ms,
                   "audit_utc": 1_800_000_000.75, "type": event_type,
                   "message": "Inline synthetic event.", "target": target, "data": data or {}}
    if event_type == "TRACK":
        event.update({"observed_ms": sim_ms - 20, "received_ms": sim_ms,
                      "track": {"id": "AC-01", "callsign": "FIX-AC-01", "kind": "aircraft",
                                "x_m": 100.0, "y_m": 0.0, "speed_mps": 40.0, "heading_deg": 0.0,
                                "phase": "final", "length_m": 35.0, "width_m": 32.0, "runway": "27",
                                "route": [[3000.0, 0.0]], "owner": "tower", "observed_ms": sim_ms - 20,
                                "received_ms": sim_ms, "source": "synthetic-fixture", "event_id": event_id}})
    return ReplayEventRecord.model_validate({
        "schema_version": "replay-1", "source_id": SOURCE_ID, "source_event_id": event_id,
        "source_time": {"value": sim_ms, "unit": "ms", "clock": "fixture-clock"},
        "event": event, "quality": {"status": "nominal", "reasons": []},
    })


class FakeReplayEventSource:
    def __init__(self, records: list[ReplayEventRecord]):
        self.records = records
        self._manifest = _manifest()
        self.calls: list[tuple[int, int | None]] = []

    def manifest(self) -> ReplaySourceManifest:
        return self._manifest

    def read(self, after_ordinal: int, until_ms: int | None = None):
        self.calls.append((after_ordinal, until_ms))
        return [record for record in self.records
                if record.event.ordinal > after_ordinal and record.event.sim_ms is not None
                and (until_ms is None or record.event.sim_ms <= until_ms)]


class StubDetector:
    version = "stub-detector-2"

    def __init__(self):
        self.calls: list[dict] = []
        self.layout_versions: list[str] = []

    def evaluate_with_layout(
        self, *, tracks, clearances, now_ms, config, runway_open, expected_ids, previous_tracks, layout
    ):
        self.layout_versions.append(layout.version)
        return self.evaluate(tracks, clearances, now_ms, config, runway_open, expected_ids, previous_tracks)

    def evaluate(self, tracks, clearances, now_ms, config, runway_open, expected_ids, previous_tracks=None):
        self.calls.append({"now_ms": now_ms, "tracks": dict(tracks), "clearances": list(clearances),
                           "runway_open": runway_open, "expected_ids": list(expected_ids),
                           "previous_tracks": dict(previous_tracks or {})})
        evidence = [track.event_id for track in tracks.values()]
        return {
            "predictions": [{"source_event_id": item, "model_version": "stub-model-2"} for item in evidence],
            "candidates": ([{"rule": "STUB-RULE", "rule_version": "stub-rule-2",
                             "evidence_event_ids": evidence}] if evidence else []),
            "runway": {"open": runway_open, "degraded_ids": []},
        }


class StubLifecycle:
    def __init__(self):
        self.calls: list[int] = []

    def update(self, alerts, result, now_ms, emit_event):
        self.calls.append(now_ms)
        if result["candidates"]:
            key = result["candidates"][0]["rule"]
            alerts[key] = {"status": "ACTIVE", "calculated_ms": now_ms,
                           "evidence_event_ids": result["candidates"][0]["evidence_event_ids"]}
            emit_event("ALERT_OPEN", "Synthetic lifecycle stub transition.", rule=key)


def test_source_to_analysis_uses_be01_ports_and_preserves_immutable_evidence(monkeypatch):
    def no_database(*_args, **_kwargs):
        raise AssertionError("BE-02 replay analysis must not open SQLite")

    def no_network(*_args, **_kwargs):
        raise AssertionError("BE-02 replay analysis must not open a network socket")

    monkeypatch.setattr(sqlite3, "connect", no_database)
    monkeypatch.setattr(socket, "socket", no_network)

    records = [
        _record(1, "RUNWAY_OPEN", sim_ms=0, data={"physical_runway_id": "RWY-TEST"}),
        _record(2, "CLEARANCE", sim_ms=50, target="AC-01",
                data={"issuer": "synthetic", "instruction": "LAND", "runway": "27"}),
        _record(3, "TRACK", sim_ms=100, target="AC-01"),
        _record(4, "READBACK", sim_ms=100, target="AC-01", data={"readback": "ACKNOWLEDGED"}),
        _record(5, "ALERT_OPEN", sim_ms=110, target="AC-01", data={"source_rule": "NATIVE-SOURCE"}),
        _record(6, "UNSUPPORTED", sim_ms=120,
                data={"private_truth": {"scheduled_future": True}, "checkpoint": {"mobiles": ["BAW123"]}}),
    ]
    original_records = [record.model_dump(mode="json") for record in records]
    source = FakeReplayEventSource(records)
    detector = StubDetector()
    lifecycle = StubLifecycle()
    reader = ReplaySourceReader(source)

    analysis = build_replay_analysis(
        reader, detector, lifecycle, config=SimulationConfig(), window_start_ms=0, window_end_ms=200,
        source_session_id="source-session-fixture-2", analysis_id="analysis-fixture-2",
        config_version="stub-config-2",
    )

    assert analysis.metadata.source_id == SOURCE_ID
    assert analysis.metadata.source_session_id == "source-session-fixture-2"
    assert analysis.metadata.kind == "detector"
    assert analysis.metadata.input_hash and len(analysis.metadata.input_hash) == 64
    assert analysis.metadata.versions == {
        "schema_version": "replay-1",
        "layout_version": "layout-2",
        "source_version": "fixture-2",
        "config_version": "stub-config-2",
        "detector_version": "stub-detector-2",
        "model_versions": ["stub-model-2"],
        "rule_versions": ["stub-rule-2"],
    }
    assert analysis.metadata.window_start_ms == 0
    assert analysis.metadata.window_end_ms == 200
    assert analysis.metadata.status == "completed_degraded"  # unsupported source event remains unresolved
    assert [frame.at_ms for frame in analysis.frames] == [0, 50, 100, 110, 120]
    frame_99 = next(frame for frame in analysis.frames if frame.at_ms == 50)
    frame_100 = next(frame for frame in analysis.frames if frame.at_ms == 100)
    assert frame_99.state.tracks == {}
    assert frame_100.state.tracks["AC-01"].received_ms == 100
    assert frame_100.state.clearances[0].readback == "ACKNOWLEDGED"
    assert frame_100.detector_result["candidates"][0]["evidence_event_ids"] == [f"{SOURCE_ID}:fixture-3"]
    assert len(frame_100.lifecycle_events) == 1
    native_frame = next(frame for frame in analysis.frames if frame.at_ms == 110)
    assert [item.ref.event_type for item in native_frame.state.native_source_alerts] == ["ALERT_OPEN"]
    assert "native_source_alerts" not in native_frame.detector_result
    final_public = analysis.frames[-1].public_projection()
    serialized_public = str(final_public)
    assert "private_truth" not in serialized_public
    assert "checkpoint" not in serialized_public
    assert "BAW123" not in serialized_public
    assert [record.model_dump(mode="json") for record in records] == original_records
    assert source._manifest.content_hash == "d" * 64
    assert set(detector.layout_versions) == {"layout-2"}
    assert all(frame.layout_binding == "source_layout_parameter" for frame in analysis.frames)
    assert [call["now_ms"] for call in detector.calls].count(100) == 1
    assert len(detector.calls) == len(lifecycle.calls) == 5
    assert source.calls == [(-1, 200)]

    repeat = build_replay_analysis(
        ReplaySourceReader(FakeReplayEventSource(records)), StubDetector(), StubLifecycle(),
        config=SimulationConfig(), window_start_ms=0, window_end_ms=200,
        source_session_id="source-session-fixture-2", analysis_id="analysis-fixture-repeat",
        config_version="stub-config-2",
    )
    assert repeat.metadata.input_hash == analysis.metadata.input_hash
