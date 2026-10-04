"""Atomic import/archive checks with synthetic bundles and temporary SQLite files."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from backend.replay_import import (
    ArchiveReplayEventSource,
    ReplayImportConflict,
    ReplayImportService,
    ReplayImportValidationError,
    SQLiteReplayArchiveReader,
    UnsupportedReplayFormat,
)
from backend.storage import Archive


def _manifest(source_id: str, events: bytes, **changes: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "replay-1",
        "source_id": source_id,
        "source_kind": "synthetic",
        "source_ref": f"synthetic://fixtures/{source_id}",
        "content_hash": hashlib.sha256(events).hexdigest(),
        "provenance": {
            "owner": None,
            "version": None,
            "derivation": "authored synthetic BE-03 fixture",
            "retention_reason": "temporary test fixture",
        },
        "permission_profile": {
            "reference": "local-synthetic-test-profile",
            "purpose": "automated import test",
            "processing_scope": "temporary SQLite test harness",
        },
        "retention_until": None,
        "timebase": {
            "source_clock": "fixture-clock",
            "source_unit": "ms",
            "mapping_id": "fixed-offset-v1",
            "offset_ms": 20,
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
            "id": "fixture-layout",
            "version": "1",
            "name": "Synthetic test layout",
            "coordinate_system": "LOCAL_METRES",
            "physical_runway_id": "RWY-TEST",
            "runway": [[0, 0], [1000, 0]],
            "protected_area": [[0, -75], [1000, -75], [1000, 75], [0, 75]],
            "taxiways": [[[0, 200], [1000, 200]]],
            "hold_lines": [[[400, 0], [400, 40]]],
            "directions": {"09": "eastbound", "27": "westbound"},
            "note": "Synthetic fixture geometry; not operational data.",
        },
    }
    result.update(changes)
    return result


def _record(
    source_id: str,
    ordinal: int,
    *,
    source_time_ms: int = 80,
    event_id: str | None = None,
    message: str | None = None,
    sim_ms: int | None = None,
    quality_status: str = "nominal",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_event_id = event_id or f"evt-{ordinal}"
    session_ms = source_time_ms + 20 if sim_ms is None else sim_ms
    reasons = [] if quality_status == "nominal" else ["fixture quality condition"]
    return {
        "schema_version": "replay-1",
        "source_id": source_id,
        "source_event_id": source_event_id,
        "source_time": {"value": source_time_ms, "unit": "ms", "clock": "fixture-clock"},
        "quality": {"status": quality_status, "reasons": reasons},
        "event": {
            "id": source_event_id,
            "ordinal": ordinal,
            "sim_ms": session_ms,
            "audit_utc": None,
            "type": "TRACK",
            "message": message or f"Observed synthetic object {ordinal}.",
            "target": "AC101",
            "observed_ms": session_ms - 5,
            "received_ms": session_ms,
            "track": {
                "id": "AC101",
                "callsign": "SYN101",
                "kind": "aircraft",
                "x_m": 10.0 + ordinal,
                "y_m": 20.0,
                "speed_mps": 35.0,
                "heading_deg": 90.0,
                "phase": "TAXI",
                "length_m": 36.0,
                "width_m": 4.0,
                "runway": "09",
                "route": [[10.0, 20.0], [20.0, 20.0]],
                "owner": "ground",
                "observed_ms": session_ms - 5,
                "received_ms": session_ms,
                "source": "synthetic-fixture",
                "event_id": source_event_id,
            },
            "data": data or {"sample_kind": "synthetic"},
        },
    }


def _jsonl(*records: dict[str, Any]) -> bytes:
    return b"".join(
        (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        for record in records
    )


def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _bundle(source_id: str, *records: dict[str, Any]) -> tuple[bytes, bytes]:
    event_bytes = _jsonl(*records)
    return _manifest_bytes(_manifest(source_id, event_bytes)), event_bytes


def _import(archive: Archive, manifest_bytes: bytes, event_bytes: bytes):
    return ReplayImportService(archive).import_bundle(manifest_bytes, event_bytes)


def _analysis_metadata(source: dict[str, Any], analysis_id: str) -> dict[str, Any]:
    return {
        "id": analysis_id,
        "source_id": source["source_id"],
        "source_session_id": source["source_session_id"],
        "kind": "detector",
        "input_hash": "a" * 64,
        "versions": {"schema_version": "replay-1", "layout_version": "1"},
        "window_start_ms": 100,
        "window_end_ms": 300,
        "status": "completed_degraded",
    }


def _analysis_frame(analysis_id: str, at_ms: int, marker: str) -> dict[str, Any]:
    return {
        "analysis_id": analysis_id,
        "at_ms": at_ms,
        "state": {
            "source_id": "source-1",
            "as_of_ms": at_ms,
            "coverage_status": "known",
            "tracks": {},
            "data_quality": "degraded",
            "simulator_truth": {"hidden": True},
        },
        "detector_result": {"predictions": [{"marker": marker}], "private_schedule": ["hidden"]},
        "alerts": {"fixture-alert": {"message": marker}},
        "lifecycle_events": [],
        "status": "evaluated",
        "layout_binding": "source_layout_parameter",
        "private_checkpoint": {"secret": "hidden"},
    }


def test_import_reopens_with_manifest_hash_source_records_and_analysis(tmp_path: Path) -> None:
    database = tmp_path / "archive.sqlite"
    event_bytes = _jsonl(_record("source-1", 0, source_time_ms=80))
    manifest_bytes = _manifest_bytes(_manifest("source-1", event_bytes))

    archive = Archive(database)
    receipt = _import(archive, manifest_bytes, event_bytes)
    assert receipt.import_status == "completed"
    assert not receipt.idempotent
    stored = archive.replay_source(receipt.source_session_id)
    assert stored is not None
    assert stored["manifest"]["source_id"] == "source-1"
    assert stored["content_hash"] == hashlib.sha256(event_bytes).hexdigest()
    assert stored["event_bytes"] == event_bytes
    source = ArchiveReplayEventSource(archive, receipt.source_session_id)
    records = source.read(-1)
    assert len(records) == 1
    assert records[0].source_event_id == "evt-0"
    assert records[0].event.ordinal == 0
    assert records[0].source_time.value == 80
    assert records[0].quality.status == "nominal"
    assert records[0].event.track is not None
    assert records[0].event.track.x_m == 10.0

    reader = SQLiteReplayArchiveReader(archive)
    metadata = reader.metadata(receipt.source_session_id)
    assert metadata is not None
    assert metadata["manifest"]["schema_version"] == "replay-1"
    assert "source_ref" not in metadata["manifest"]
    analysis_id = "analysis-v1"
    archive.save_replay_analysis(
        _analysis_metadata(stored, analysis_id),
        [_analysis_frame(analysis_id, 100, "first"), _analysis_frame(analysis_id, 300, "last")],
    )
    archive.close()

    reopened = Archive(database)
    try:
        reopened_source = reopened.replay_source(receipt.source_session_id)
        assert reopened_source is not None
        assert reopened_source["manifest"]["source_id"] == "source-1"
        assert reopened_source["event_bytes"] == event_bytes
        reopened_events = ArchiveReplayEventSource(reopened, receipt.source_session_id).read(-1)
        assert [item.source_event_id for item in reopened_events] == ["evt-0"]
        assert reopened_events[0].source_time.value == 80
        assert reopened_events[0].quality.status == "nominal"
        assert reopened_events[0].event.track is not None
        assert reopened_events[0].event.track.x_m == 10.0
        reopened_reader = SQLiteReplayArchiveReader(reopened)
        reopened_metadata = reopened_reader.metadata(receipt.source_session_id)
        frame_at_200 = reopened_reader.frame(receipt.source_session_id, 200, analysis_id)
        frame_at_350 = reopened_reader.frame(receipt.source_session_id, 350, analysis_id)
        assert reopened_metadata is not None
        assert reopened_metadata["analyses"][0]["id"] == analysis_id
        assert frame_at_200 is not None and frame_at_200["frame_ms"] == 100
        assert frame_at_350 is not None and frame_at_350["frame_ms"] == 300
    finally:
        reopened.close()


def test_hash_uses_exact_jsonl_bytes_and_unsupported_profiles_are_rejected(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive.sqlite")
    events = _jsonl(_record("hash-source", 0))
    manifest = _manifest("hash-source", events)
    with pytest.raises(ReplayImportValidationError, match="exact events JSONL bytes"):
        _import(archive, _manifest_bytes(manifest), events + b" ")

    unsupported = {**manifest, "schema_version": "vendor-raw-1"}
    unsupported["content_hash"] = hashlib.sha256(events).hexdigest()
    with pytest.raises(UnsupportedReplayFormat, match="only normalized"):
        _import(archive, _manifest_bytes(unsupported), events)
    assert archive.replay_sources_for_idempotency("hash-source") is None
    archive.close()


def test_identical_retry_is_idempotent_but_source_hash_or_manifest_change_conflicts(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive.sqlite")
    events = _jsonl(_record("same-source", 0))
    manifest = _manifest("same-source", events)
    original = _import(archive, _manifest_bytes(manifest), events)
    reordered_manifest = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    retried = _import(archive, reordered_manifest, events)
    assert retried.idempotent
    assert retried.source_session_id == original.source_session_id
    assert retried.receipt_id == original.receipt_id

    changed_events = events[:-1] + b"  \n"
    changed_hash_manifest = _manifest("same-source", changed_events)
    with pytest.raises(ReplayImportConflict, match="different replay content or manifest"):
        _import(archive, _manifest_bytes(changed_hash_manifest), changed_events)

    changed_metadata = {**manifest, "source_ref": "synthetic://different-reference"}
    with pytest.raises(ReplayImportConflict, match="different replay content or manifest"):
        _import(archive, _manifest_bytes(changed_metadata), events)
    committed = archive.replay_source(original.source_session_id)
    assert committed is not None
    assert committed["event_bytes"] == events
    archive.close()


def test_duplicate_identical_event_is_deduplicated_and_conflicting_payload_is_rejected(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive.sqlite")
    record = _record("duplicates", 0, event_id="same-event")
    event_bytes = _jsonl(record, record)
    receipt = _import(archive, _manifest_bytes(_manifest("duplicates", event_bytes)), event_bytes)
    assert len(ArchiveReplayEventSource(archive, receipt.source_session_id).read(-1)) == 1

    conflict_source_record = _record("conflicting-duplicates", 0, event_id="same-event")
    conflict = {
        **conflict_source_record,
        "event": {**conflict_source_record["event"], "message": "different payload"},
    }
    matching_conflict_record = _record("conflicting-duplicates", 0, event_id="same-event")
    conflict_bytes = _jsonl(matching_conflict_record, conflict)
    with pytest.raises(ReplayImportConflict, match="conflicting payloads"):
        _import(archive, _manifest_bytes(_manifest("conflicting-duplicates", conflict_bytes)), conflict_bytes)
    assert archive.replay_sources_for_idempotency("conflicting-duplicates") is None
    archive.close()


def test_invalid_final_record_and_injected_commit_failure_leave_no_partial_receipt_or_source(
    tmp_path: Path,
) -> None:
    database = tmp_path / "archive.sqlite"
    archive = Archive(database)
    stable_events = _jsonl(_record("stable-source", 0))
    stable_receipt = _import(
        archive,
        _manifest_bytes(_manifest("stable-source", stable_events)),
        stable_events,
    )

    first = _record("invalid-tail", 0)
    invalid_last = _record("not-the-manifest-source", 1)
    invalid_bytes = _jsonl(first, invalid_last)
    with pytest.raises(ReplayImportValidationError, match="source_id does not match"):
        _import(
            archive,
            _manifest_bytes(_manifest("invalid-tail", invalid_bytes)),
            invalid_bytes,
        )
    assert archive.replay_sources_for_idempotency("invalid-tail") is None

    failed_events = _jsonl(_record("commit-failure", 0))
    failed_manifest = _manifest_bytes(_manifest("commit-failure", failed_events))

    def fail_commit() -> None:
        raise RuntimeError("injected SQLite transaction failure")

    archive._before_replay_import_commit = fail_commit  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="injected SQLite"):
        _import(archive, failed_manifest, failed_events)
    archive.close()

    reopened = Archive(database)
    try:
        assert reopened.replay_sources_for_idempotency("commit-failure") is None
        assert reopened.replay_sources_for_idempotency("invalid-tail") is None
        stable = reopened.replay_source(stable_receipt.source_session_id)
        assert stable is not None
        assert stable["event_bytes"] == stable_events
        receipt_count = reopened.db.execute("SELECT COUNT(*) FROM replay_import_receipts").fetchone()[0]
        assert receipt_count == 1
    finally:
        reopened.close()


def test_legacy_synthetic_archive_and_same_time_analysis_namespaces_remain_separate(tmp_path: Path) -> None:
    database = tmp_path / "archive.sqlite"
    legacy_public = {"sim_ms": 100, "sequence": 1, "tracks": {"AC1": {"x_m": 1}}}
    legacy_private = {"simulator": {"mobiles": [{"id": "truth-1"}]}}
    legacy_db = sqlite3.connect(database)
    legacy_db.executescript(
        """
        CREATE TABLE sessions (id TEXT PRIMARY KEY, metadata TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TABLE events (
            session_id TEXT NOT NULL REFERENCES sessions(id), ordinal INTEGER NOT NULL,
            data TEXT NOT NULL, PRIMARY KEY(session_id, ordinal));
        CREATE TABLE frames (
            session_id TEXT NOT NULL REFERENCES sessions(id), sim_ms INTEGER NOT NULL,
            sequence INTEGER NOT NULL, public TEXT NOT NULL, private TEXT NOT NULL,
            PRIMARY KEY(session_id, sim_ms));
        CREATE TABLE commands (
            session_id TEXT NOT NULL REFERENCES sessions(id), command_id TEXT NOT NULL,
            request TEXT NOT NULL, response TEXT NOT NULL,
            PRIMARY KEY(session_id, command_id));
        """
    )
    legacy_db.execute(
        "INSERT INTO sessions VALUES (?, ?, ?)",
        ("synthetic-session", json.dumps({"id": "synthetic-session", "kind": "training"}), "ENDED"),
    )
    legacy_db.execute(
        "INSERT INTO frames VALUES (?, ?, ?, ?, ?)",
        (
            "synthetic-session",
            100,
            1,
            json.dumps(legacy_public),
            json.dumps(legacy_private),
        ),
    )
    legacy_db.commit()
    legacy_db.close()

    # Opening a pre-BE-03 database installs only additive replay tables.
    archive = Archive(database)
    assert archive.replay_schema_version == 1
    legacy_metadata = archive.metadata("synthetic-session")
    assert legacy_metadata is not None and legacy_metadata["status"] == "ENDED"

    events = _jsonl(_record("analysis-source", 0))
    receipt = _import(archive, _manifest_bytes(_manifest("analysis-source", events)), events)
    source = archive.replay_source(receipt.source_session_id)
    assert source is not None
    first_id = "analysis-first"
    second_id = "analysis-second"
    archive.save_replay_analysis(
        _analysis_metadata(source, first_id), [_analysis_frame(first_id, 100, "first")]
    )
    archive.save_replay_analysis(
        _analysis_metadata(source, second_id), [_analysis_frame(second_id, 100, "second")]
    )

    stored_legacy = archive.frame("synthetic-session", 100)
    assert stored_legacy == (legacy_public, legacy_private)
    first_frame = archive.replay_analysis_frame(receipt.source_session_id, first_id, 100)
    second_frame = archive.replay_analysis_frame(receipt.source_session_id, second_id, 100)
    assert first_frame is not None and first_frame["detector_result"]["predictions"][0]["marker"] == "first"
    assert second_frame is not None and second_frame["detector_result"]["predictions"][0]["marker"] == "second"
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        archive.db.execute(
            "UPDATE replay_source_events SET ordinal=5 WHERE source_id='analysis-source'"
        )
    archive.close()


def test_frame_cutoff_and_event_cutoff_are_applied_before_paging(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive.sqlite")
    records = (
        _record("paging-source", 0, source_time_ms=80),
        _record("paging-source", 1, source_time_ms=280),
        _record("paging-source", 2, source_time_ms=80, event_id="evt-same-time-2"),
    )
    events = _jsonl(*records)
    receipt = _import(archive, _manifest_bytes(_manifest("paging-source", events)), events)
    source = archive.replay_source(receipt.source_session_id)
    assert source is not None
    analysis_id = "paging-analysis"
    frames = [_analysis_frame(analysis_id, ms, str(ms)) for ms in (100, 200, 300)]
    archive.save_replay_analysis(_analysis_metadata(source, analysis_id), frames)
    reader = SQLiteReplayArchiveReader(archive)

    frame = reader.frame(receipt.source_session_id, 250, analysis_id)
    assert frame is not None
    assert frame["frame_ms"] == 200
    assert frame["frame_ms"] <= frame["requested_ms"]
    assert reader.frame(receipt.source_session_id, 99, analysis_id) is None
    assert reader.frame(receipt.source_session_id, 250) is None

    first_page = reader.events(receipt.source_session_id, after_ordinal=-1, until_ms=200, limit=1)
    second_page = reader.events(receipt.source_session_id, after_ordinal=0, until_ms=200, limit=1)
    assert [item["event"]["ordinal"] for item in first_page] == [0]
    assert [item["event"]["ordinal"] for item in second_page] == [2]
    assert all(item["event"]["sim_ms"] <= 200 for item in (*first_page, *second_page))
    archive.close()


def test_public_reader_returns_projection_without_private_fields_or_write_capability(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive.sqlite")
    events = _jsonl(_record("public-source", 0))
    receipt = _import(archive, _manifest_bytes(_manifest("public-source", events)), events)
    source = archive.replay_source(receipt.source_session_id)
    assert source is not None
    analysis_id = "public-analysis"
    archive.save_replay_analysis(
        _analysis_metadata(source, analysis_id), [_analysis_frame(analysis_id, 100, "public")]
    )
    reader = SQLiteReplayArchiveReader(archive)
    metadata = reader.metadata(receipt.source_session_id)
    assert metadata is not None
    assert "source_ref" not in metadata["manifest"]
    frame = reader.frame(receipt.source_session_id, 100, analysis_id)
    serialized = json.dumps(frame)
    for forbidden in ("private_checkpoint", "simulator_truth", "private_schedule", "hidden"):
        assert forbidden not in serialized
    public_events = reader.events(receipt.source_session_id)
    assert public_events[0]["event"]["track"]["callsign"] == "SYN101"
    assert not hasattr(reader, "save_replay_analysis")
    assert not hasattr(reader, "command")
    assert not hasattr(reader, "reset_branch_archive")
    archive.close()


def test_private_record_fields_are_rejected_instead_of_becoming_public_events(tmp_path: Path) -> None:
    archive = Archive(tmp_path / "archive.sqlite")
    record = _record("private-input", 0, data={"simulator_truth": {"id": "hidden"}})
    events = _jsonl(record)
    with pytest.raises(ReplayImportValidationError, match="unsupported private field"):
        _import(archive, _manifest_bytes(_manifest("private-input", events)), events)
    assert archive.replay_sources_for_idempotency("private-input") is None
    archive.close()


def test_unknown_time_is_preserved_as_unresolved_and_excluded_from_cutoff_public_page(
    tmp_path: Path,
) -> None:
    archive = Archive(tmp_path / "archive.sqlite")
    source_id = "unknown-time-source"
    record = _record(source_id, 0)
    record["source_time"]["value"] = None
    record["quality"] = {"status": "alignment_unknown", "reasons": ["source clock not mapped"]}
    record["event"].update(
        {"sim_ms": None, "observed_ms": None, "received_ms": None, "track": None}
    )
    event_bytes = _jsonl(record)
    manifest = _manifest(
        source_id,
        event_bytes,
        timebase={
            "source_clock": "fixture-clock",
            "source_unit": "ms",
            "mapping_id": None,
            "offset_ms": None,
            "uncertainty_ms": None,
            "alignment_status": "unknown",
        },
    )
    receipt = _import(archive, _manifest_bytes(manifest), event_bytes)

    internal_records = ArchiveReplayEventSource(archive, receipt.source_session_id).read(-1, until_ms=200)
    assert len(internal_records) == 1
    assert internal_records[0].event.sim_ms is None
    assert internal_records[0].event.track is None
    assert internal_records[0].quality.status == "alignment_unknown"
    public_reader = SQLiteReplayArchiveReader(archive)
    assert public_reader.events(receipt.source_session_id, until_ms=200) == ()
    archive.close()
