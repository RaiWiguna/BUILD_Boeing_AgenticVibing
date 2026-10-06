"""Synthetic and stub-only tests for BE-02 replay reduction."""

from __future__ import annotations

import pytest

from backend.models import SimulationConfig
from backend.replay_contracts import ReplayEventRecord, ReplaySourceManifest
from backend.replay_source import (
    ObservedStateReducer,
    ReplayImportConflict,
    ReplaySourceReader,
    build_replay_analysis,
)

SOURCE_ID = "synthetic-be02-source"


def manifest_payload(*, coverage_unknown: bool = False, alignment_unknown: bool = False) -> dict:
    coverage = (
        {"status": "unknown", "object_ids": None, "channel_ids": None, "intervals": None,
         "missing_intervals": None}
        if coverage_unknown
        else {"status": "known", "object_ids": ["AC-01"], "channel_ids": ["tower"],
              "intervals": [{"start_ms": 0, "end_ms": 100_000}], "missing_intervals": []}
    )
    timebase = (
        {"source_clock": "unknown-source-clock", "source_unit": "ms", "mapping_id": None,
         "offset_ms": None, "uncertainty_ms": None, "alignment_status": "unknown"}
        if alignment_unknown
        else {"source_clock": "fixture-clock", "source_unit": "ms", "mapping_id": "fixture-offset-0",
              "offset_ms": 0, "uncertainty_ms": 0, "alignment_status": "aligned"}
    )
    return {
        "schema_version": "replay-1",
        "source_id": SOURCE_ID,
        "source_kind": "synthetic",
        "source_ref": "fixture://be-02-inline",
        "content_hash": "c" * 64,
        "provenance": {"owner": "BE-02 test fixture", "version": "fixture-1",
                       "derivation": "authored synthetic fixture", "retention_reason": None},
        "permission_profile": {"reference": "local-synthetic", "purpose": "unit test",
                                "processing_scope": "test only"},
        "retention_until": "2027-01-01T00:00:00Z",
        "timebase": timebase,
        "coverage": coverage,
        "layout": {
            "id": "fixture-layout", "version": "layout-fixture-1", "name": "Synthetic test layout",
            "coordinate_system": "LOCAL_METRES", "physical_runway_id": "RWY-TEST",
            "runway": [[0, -20], [3000, -20], [3000, 20], [0, 20]],
            "protected_area": [[0, -75], [3000, -75], [3000, 75], [0, 75]],
            "taxiways": [[[0, -160], [3000, -160]]], "hold_lines": [[[1470, -95], [1530, -95]]],
            "directions": {"09": "RWY-TEST", "27": "RWY-TEST"},
            "note": "Authored synthetic fixture; no domain validation claimed.",
        },
    }


def make_record(
    ordinal: int,
    event_type: str,
    *,
    source_event_id: str | None = None,
    sim_ms: int | None = None,
    observed_ms: int | None = None,
    received_ms: int | None = None,
    object_id: str = "AC-01",
    x_m: float = 10.0,
    target: str | None = None,
    data: dict | None = None,
    message: str = "Synthetic fixture event.",
    quality_status: str = "nominal",
) -> ReplayEventRecord:
    event_id = source_event_id or f"fixture-event-{ordinal}"
    event: dict = {
        "id": event_id,
        "ordinal": ordinal,
        "sim_ms": sim_ms,
        "audit_utc": 1_800_000_000.5,
        "type": event_type,
        "message": message,
        "target": target,
        "data": data or {},
    }
    if event_type == "TRACK":
        assert sim_ms is not None
        observed = sim_ms if observed_ms is None else observed_ms
        received = sim_ms if received_ms is None else received_ms
        event.update(observed_ms=observed, received_ms=received)
        event["track"] = {
            "id": object_id, "callsign": f"FIX-{object_id}", "kind": "aircraft",
            "x_m": x_m, "y_m": 0.0, "speed_mps": 40.0, "heading_deg": 0.0,
            "phase": "final", "length_m": 35.0, "width_m": 32.0, "runway": "27",
            "route": [[3000.0, 0.0]], "owner": "tower", "observed_ms": observed,
            "received_ms": received, "source": "synthetic-fixture", "event_id": event_id,
        }
    quality = (
        {"status": quality_status, "reasons": [] if quality_status == "nominal" else ["synthetic fixture quality"]}
    )
    source_time = {"value": sim_ms, "unit": "ms", "clock": "fixture-clock"}
    if sim_ms is None:
        source_time["value"] = None
    return ReplayEventRecord.model_validate({
        "schema_version": "replay-1", "source_id": SOURCE_ID, "source_event_id": event_id,
        "source_time": source_time, "event": event, "quality": quality,
    })


class FakeSource:
    """Inline read-only source; all records are authored synthetic fixtures."""

    def __init__(self, records: list[ReplayEventRecord], manifest: dict | None = None):
        self.records = records
        self._manifest = ReplaySourceManifest.model_validate(manifest or manifest_payload())
        self.calls: list[tuple[int, int | None]] = []

    def manifest(self) -> ReplaySourceManifest:
        return self._manifest

    def read(self, after_ordinal: int, until_ms: int | None = None) -> list[ReplayEventRecord]:
        self.calls.append((after_ordinal, until_ms))
        return [
            record for record in self.records
            if record.event.ordinal > after_ordinal
            and (until_ms is None or record.event.sim_ms is None or record.event.sim_ms <= until_ms)
        ]


def test_order_is_deterministic_and_same_time_ordinal_ties_are_applied_as_one_group():
    source_order = [
        make_record(5, "TRACK", sim_ms=100, x_m=30.0),
        make_record(2, "RUNWAY_OPEN", sim_ms=0),
        make_record(3, "CLEARANCE", sim_ms=100, target="AC-01",
                    data={"issuer": "synthetic", "instruction": "LAND", "runway": "27"}),
        make_record(4, "TRACK", sim_ms=100, x_m=20.0),
        make_record(6, "NOTE", sim_ms=100, message="unsupported; not parsed"),
    ]
    state_a = ObservedStateReducer(ReplaySourceReader(FakeSource(source_order))).build_state(100)
    state_b = ObservedStateReducer(ReplaySourceReader(FakeSource(list(reversed(source_order))))).build_state(100)

    assert state_a.public_projection() == state_b.public_projection()
    assert state_a.tracks["AC-01"].x_m == 30.0  # ordinal 5 wins the same-time tie
    assert state_a.runway_open is True
    assert state_a.clearances[0].instruction == "LAND"
    assert [ref.ordinal for ref in state_a.source_event_refs] == [2, 3, 4, 5, 6]


def test_identical_source_duplicates_are_deduplicated_and_conflicts_are_rejected():
    record = make_record(1, "NOTE", sim_ms=10)
    reader = ReplaySourceReader(FakeSource([record, record.model_copy(deep=True)]))
    assert len(reader.read()) == 1

    conflicting = make_record(1, "NOTE", source_event_id=record.source_event_id, sim_ms=10,
                              message="different payload")
    with pytest.raises(ReplayImportConflict, match="conflicting payloads"):
        ReplaySourceReader(FakeSource([record, conflicting])).read()

    paged_reader = ReplaySourceReader(FakeSource([make_record(1, "NOTE", sim_ms=10),
                                                  make_record(2, "NOTE", sim_ms=20)]))
    assert [item.event.ordinal for item in paged_reader.read(after_ordinal=1)] == [2]
    assert [item.event.ordinal for item in paged_reader.read(after_ordinal=-1)] == [1, 2]


def test_late_out_of_order_track_is_preserved_in_history_without_rolling_back_current_state():
    newest = make_record(1, "TRACK", sim_ms=1100, observed_ms=1000, received_ms=1100, x_m=100.0)
    late_old_sample = make_record(2, "TRACK", sim_ms=1200, observed_ms=900, received_ms=1200, x_m=5.0)
    state = ObservedStateReducer(ReplaySourceReader(FakeSource([late_old_sample, newest]))).build_state(1200)

    assert state.tracks["AC-01"].x_m == 100.0
    assert [ref.source_event_id for ref in state.track_history] == [newest.source_event_id, late_old_sample.source_event_id]
    assert state.previous_tracks == {}
    assert "out_of_order_track_ignored" in state.quality_reasons


def test_missing_alignment_unknown_coverage_and_unsupported_events_stay_degraded_and_unresolved():
    unaligned_manifest = manifest_payload(coverage_unknown=True, alignment_unknown=True)
    unaligned = make_record(1, "NOTE", source_event_id="unaligned-event", sim_ms=None,
                            quality_status="alignment_unknown")
    state = ObservedStateReducer(ReplaySourceReader(FakeSource([unaligned], unaligned_manifest))).build_state(500)
    assert state.tracks == {}
    assert state.clearances == ()
    assert state.coverage.object_ids is None
    assert state.coverage_status == "unknown"
    assert state.unresolved_records[0].reason == "unsupported_alignment"
    assert state.data_quality == "degraded"
    assert state.track_freshness == {}

    unsupported = make_record(2, "NOTE", sim_ms=200, data={"private_truth": {"future": True},
                                                           "checkpoint": {"mobiles": ["BAW123"]}})
    unsupported_state = ObservedStateReducer(ReplaySourceReader(FakeSource([unsupported]))).build_state(200)
    public = unsupported_state.public_projection()
    assert unsupported_state.unresolved_records[0].reason == "unsupported_event_type"
    assert unsupported_state.data_quality == "degraded"
    assert "private_truth" not in str(public)
    assert "checkpoint" not in str(public)


def test_cutoff_excludes_future_records_and_imported_state_has_no_synthetic_mobiles_or_clearances():
    earlier = make_record(1, "TRACK", sim_ms=100, x_m=10.0)
    future = make_record(2, "TRACK", sim_ms=200, x_m=20.0, object_id="FUTURE-01")
    source = FakeSource([earlier, future])
    state = ObservedStateReducer(ReplaySourceReader(source)).build_state(100)

    assert state.as_of_ms == 100
    assert set(state.tracks) == {"AC-01"}
    assert all(track.id not in {"BAW123", "ARFF-2"} for track in state.tracks.values())
    assert state.clearances == ()  # no Session constructor / initial synthetic clearance
    assert source.calls == [(-1, 100)]


def test_command_is_only_a_receipt_and_source_alerts_remain_native_evidence():
    command = make_record(
        1, "COMMAND", sim_ms=10, target="BAW123",
        data={"command": {"type": "CLEARANCE", "target": "BAW123", "instruction": "LAND"}},
    )
    native_alert = make_record(2, "ALERT_OPEN", sim_ms=20, target="AC-01",
                               data={"rule": "SOURCE-RULE", "severity": "INFO"})
    state = ObservedStateReducer(ReplaySourceReader(FakeSource([command, native_alert]))).build_state(20)

    assert state.clearances == ()
    assert len(state.control_receipts) == 1
    assert len(state.native_source_alerts) == 1
    assert state.native_source_alerts[0].ref.event_type == "ALERT_OPEN"
    projection = state.public_projection()
    assert "detector_alerts" not in projection
    assert projection["native_source_alerts"][0]["data"]["rule"] == "SOURCE-RULE"


class RecordingDetector:
    version = "synthetic-detector-stub-1"

    def __init__(self):
        self.calls: list[tuple[int, list[str]]] = []

    def evaluate(self, tracks, clearances, now_ms, config, runway_open, expected_ids, previous_tracks=None):
        self.calls.append((now_ms, sorted(tracks)))
        return {"predictions": [], "candidates": [], "runway": {"open": runway_open, "degraded_ids": []}}


class RecordingLifecycle:
    def __init__(self):
        self.calls: list[int] = []

    def update(self, alerts, result, now_ms, emit_event):
        self.calls.append(now_ms)


def test_track_observation_is_not_used_before_received_time_and_native_alert_is_not_detector_output():
    runway = make_record(1, "RUNWAY_OPEN", sim_ms=0,
                         data={"physical_runway_id": "RWY-TEST"})
    track = make_record(2, "TRACK", sim_ms=74530, observed_ms=74180, received_ms=74530, x_m=120.0)
    source = FakeSource([track, runway])
    detector = RecordingDetector()
    lifecycle = RecordingLifecycle()
    before = [record.model_dump(mode="json") for record in source.records]

    analysis = build_replay_analysis(
        ReplaySourceReader(source), detector, lifecycle, config=SimulationConfig(),
        window_start_ms=74180, window_end_ms=74600, source_session_id="fixture-session-01",
        analysis_id="analysis-fixture-01", config_version="fixture-config-1",
    )

    assert [frame.at_ms for frame in analysis.frames] == [74180, 74530]
    assert detector.calls == [(74180, []), (74530, ["AC-01"])]
    assert lifecycle.calls == [74180, 74530]
    assert analysis.frames[0].state.tracks == {}
    assert analysis.frames[1].state.tracks["AC-01"].observed_ms == 74180
    assert analysis.frames[1].state.tracks["AC-01"].received_ms == 74530
    assert analysis.metadata.source_session_id == "fixture-session-01"
    assert analysis.metadata.window_start_ms == 74180
    assert analysis.metadata.window_end_ms == 74600
    assert analysis.metadata.versions["layout_version"] == "layout-fixture-1"
    assert "scenario_version" not in analysis.metadata.versions
    assert analysis.frames[0].layout_binding == "not_exposed_by_detector_port"
    assert analysis.metadata.status == "completed_degraded"
    assert [record.model_dump(mode="json") for record in source.records] == before


def test_structured_clearance_cancel_readback_coordination_and_runway_changes_are_reduced():
    records = [
        make_record(1, "RUNWAY_CONFIG", sim_ms=0, data={"physical_runway_id": "RWY-TEST", "open": True}),
        make_record(2, "CLEARANCE", sim_ms=100, target="AC-01",
                    data={"issuer": "synthetic", "instruction": "HOLD_SHORT", "runway": "27"}),
        make_record(3, "READBACK", sim_ms=120, target="AC-01", data={"readback": "ACKNOWLEDGED"}),
        make_record(4, "COORDINATION", sim_ms=130, target="VEH-01",
                    data={"request_type": "RUNWAY_CROSSING_REQUEST", "channel": "ground"}),
        make_record(5, "CANCEL", sim_ms=140, target="AC-01"),
        make_record(6, "RUNWAY_CLOSED", sim_ms=150, data={"physical_runway_id": "RWY-TEST"}),
    ]
    state = ObservedStateReducer(ReplaySourceReader(FakeSource(records))).build_state(150)

    assert state.runway_open is False
    assert state.clearances[0].status == "CANCELLED"
    assert state.clearances[0].readback == "ACKNOWLEDGED"
    assert state.requests[0]["target"] == "VEH-01"
    assert [item["runway_open"] for item in state.runway_configuration_events] == [True, False]
