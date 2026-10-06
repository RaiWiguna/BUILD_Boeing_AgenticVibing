from __future__ import annotations

import importlib
import math
import socket
import sqlite3

import pytest
from pydantic import ValidationError

from backend.ports import PrivateCheckpointReader, ReplayArchiveReader, WorkerPort, WorkerRequest
from backend.replay_contracts import ReplayEventRecord, ReplaySourceManifest


def manifest_payload() -> dict:
    return {
        "schema_version": "replay-1",
        "source_id": "fixture-source-01",
        "source_kind": "synthetic",
        "source_ref": "fixture://replay-01",
        "content_hash": "a" * 64,
        "provenance": {
            "owner": "FlowLens fixture",
            "version": "fixture-1",
            "derivation": "authored synthetic contract fixture",
            "retention_reason": None,
        },
        "permission_profile": {
            "reference": "local-synthetic",
            "purpose": "contract testing",
            "processing_scope": "local fixture only",
        },
        "retention_until": "2027-01-01T00:00:00Z",
        "timebase": {
            "source_clock": "fixture-clock",
            "source_unit": "ms",
            "mapping_id": "offset-v1",
            "offset_ms": 500,
            "uncertainty_ms": 10,
            "alignment_status": "aligned",
        },
        "coverage": {
            "status": "known",
            "object_ids": ["AC-01"],
            "channel_ids": ["tower"],
            "intervals": [{"start_ms": 0, "end_ms": 5000}],
            "missing_intervals": [],
        },
        "layout": {
            "id": "fixture-layout",
            "version": "1",
            "name": "Fixture local layout",
            "coordinate_system": "LOCAL_METRES",
            "physical_runway_id": "RWY-09-27",
            "runway": [[0, -22.5], [3000, -22.5], [3000, 22.5], [0, 22.5]],
            "protected_area": [[0, -75], [3000, -75], [3000, 75], [0, 75]],
            "taxiways": [[[0, -160], [3000, -160]]],
            "hold_lines": [[[1470, -95], [1530, -95]]],
            "directions": {"27": "RWY-09-27", "09": "RWY-09-27"},
            "note": "Synthetic contract fixture; no domain validation claimed.",
        },
    }


def event_payload() -> dict:
    return {
        "schema_version": "replay-1",
        "source_id": "fixture-source-01",
        "source_event_id": "vendor-event-17",
        "source_time": {"value": 1.25, "unit": "s", "clock": "simulator-clock"},
        "event": {
            "id": "vendor-event-17",
            "ordinal": 4,
            "sim_ms": 1750,
            "audit_utc": 1799999999.75,
            "type": "TRACK",
            "message": "Observed track received.",
            "target": "AC-01",
            "observed_ms": 1600,
            "received_ms": 1750,
            "track": {
                "id": "AC-01",
                "callsign": "AC-01",
                "kind": "aircraft",
                "x_m": 125.5,
                "y_m": -7.0,
                "speed_mps": 44.0,
                "heading_deg": 0.0,
                "phase": "final",
                "length_m": 35.0,
                "width_m": 32.0,
                "runway": "27",
                "route": [[3000.0, 0.0]],
                "owner": "tower",
                "observed_ms": 1600,
                "received_ms": 1750,
                "source": "fixture-simulator",
                "event_id": "vendor-event-17",
            },
            "data": {"sample_quality": "nominal", "source_sequence": 4},
        },
        "quality": {"status": "nominal", "reasons": []},
    }


def test_manifest_and_event_round_trip_preserve_source_identity_time_and_quality():
    manifest = ReplaySourceManifest.model_validate(manifest_payload())
    record = ReplayEventRecord.model_validate(event_payload())

    assert ReplaySourceManifest.model_validate(manifest.model_dump(mode="json")) == manifest
    restored = ReplayEventRecord.model_validate(record.model_dump(mode="json"))
    assert restored == record
    assert restored.source_id == "fixture-source-01"
    assert restored.source_event_id == "vendor-event-17"
    assert restored.source_time.value == 1.25
    assert restored.source_time.unit == "s"
    assert restored.event.observed_ms == 1600
    assert restored.event.received_ms == restored.event.sim_ms == 1750
    assert restored.event.audit_utc == 1799999999.75
    assert restored.quality.status == "nominal"
    assert manifest.content_hash == "a" * 64
    assert manifest.timebase.offset_ms == 500
    assert manifest.provenance.version == "fixture-1"


@pytest.mark.parametrize(
    "factory,payload",
    [
        (ReplaySourceManifest.model_validate, manifest_payload() | {"unexpected": True}),
        (ReplayEventRecord.model_validate, event_payload() | {"private_truth": {"future": True}}),
        (ReplaySourceManifest.model_validate, manifest_payload() | {"schema_version": "replay-99"}),
        (ReplayEventRecord.model_validate, event_payload() | {"schema_version": "vendor-raw"}),
    ],
)
def test_extra_fields_and_unsupported_profiles_are_rejected(factory, payload):
    with pytest.raises(ValidationError):
        factory(payload)


def test_nonfinite_and_invalid_timestamps_are_rejected():
    bad_source_time = event_payload()
    bad_source_time["source_time"]["value"] = math.inf
    with pytest.raises(ValidationError):
        ReplayEventRecord.model_validate(bad_source_time)

    bad_sim_time = event_payload()
    bad_sim_time["event"]["sim_ms"] = -1
    with pytest.raises(ValidationError):
        ReplayEventRecord.model_validate(bad_sim_time)

    bad_audit_time = event_payload()
    bad_audit_time["event"]["audit_utc"] = math.nan
    with pytest.raises(ValidationError):
        ReplayEventRecord.model_validate(bad_audit_time)

    bad_source_time["source_time"]["value"] = "1250"
    with pytest.raises(ValidationError):
        ReplayEventRecord.model_validate(bad_source_time)


def test_missing_data_remains_unknown_and_does_not_become_zero_or_fresh():
    payload = manifest_payload()
    payload["coverage"] = {
        "status": "unknown",
        "object_ids": None,
        "channel_ids": None,
        "intervals": None,
        "missing_intervals": None,
    }
    payload["timebase"] = {
        "source_clock": "unknown-clock",
        "source_unit": "ms",
        "mapping_id": None,
        "offset_ms": None,
        "uncertainty_ms": None,
        "alignment_status": "unknown",
    }
    manifest = ReplaySourceManifest.model_validate(payload)
    record_data = event_payload()
    record_data["source_time"]["value"] = None
    record_data["quality"] = {"status": "alignment_unknown", "reasons": ["source clock mapping unknown"]}
    record_data["event"]["observed_ms"] = None
    record_data["event"]["sim_ms"] = None
    record_data["event"]["track"] = None
    record = ReplayEventRecord.model_validate(record_data)

    assert manifest.coverage.status == "unknown"
    assert manifest.coverage.object_ids is None
    assert manifest.timebase.offset_ms is None
    assert record.source_time.value is None
    assert record.event.observed_ms is None
    assert record.event.sim_ms is None
    assert record.quality.status == "alignment_unknown"


def test_public_reader_and_worker_ports_do_not_expose_private_or_command_capabilities():
    public_names = {name for name in dir(ReplayArchiveReader) if not name.startswith("_")}
    worker_input_names = {name for name in dir(WorkerRequest) if not name.startswith("_")}
    worker_methods = {name for name in dir(WorkerPort) if not name.startswith("_")}
    private_capabilities = {"checkpoint", "truth", "truth_samples", "private", "database", "command"}

    assert not (public_names & private_capabilities)
    assert not (worker_input_names & private_capabilities)
    assert not (worker_methods & {"database", "command", "archive", "execute_command"})
    assert "checkpoint" in dir(PrivateCheckpointReader)


def test_importing_contracts_and_ports_opens_no_database_or_network(monkeypatch):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("contract imports must have no I/O side effects")

    monkeypatch.setattr(sqlite3, "connect", unexpected)
    monkeypatch.setattr(socket, "socket", unexpected)
    importlib.import_module("backend.replay_contracts")
    importlib.import_module("backend.ports")
