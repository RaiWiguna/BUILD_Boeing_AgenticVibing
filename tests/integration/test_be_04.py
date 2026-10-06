"""BE-04 replay transport, access scoping, and compatibility checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app

OPERATOR_KEY = "be04-test-operator-key"


def _record(source_id: str, ordinal: int, sim_ms: int, *, message: str | None = None) -> dict[str, Any]:
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
            "message": message or f"Synthetic track sample {ordinal}.",
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


def _bundle(source_id: str, *, changed: bool = False) -> tuple[bytes, bytes]:
    records = [
        _record(source_id, 0, 100, message="Changed source payload." if changed else None),
        _record(source_id, 1, 100),
        _record(source_id, 2, 300),
    ]
    event_bytes = b"".join(
        (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        for record in records
    )
    manifest = {
        "schema_version": "replay-1",
        "source_id": source_id,
        "source_kind": "synthetic",
        "source_ref": "C:/private/local-export/events.jsonl",
        "content_hash": hashlib.sha256(event_bytes).hexdigest(),
        "provenance": {
            "owner": None,
            "version": "fixture-1",
            "derivation": "authored synthetic BE-04 test fixture",
            "retention_reason": "temporary test data",
        },
        "permission_profile": {
            "reference": "local-synthetic-test-profile",
            "purpose": "BE-04 automated test",
            "processing_scope": "temporary SQLite test harness",
        },
        "retention_until": None,
        "timebase": {
            "source_clock": "fixture-clock",
            "source_unit": "ms",
            "mapping_id": "fixed-offset-v1",
            "offset_ms": 0,
            "uncertainty_ms": 0,
            "alignment_status": "aligned",
        },
        "coverage": {
            "status": "known",
            "object_ids": ["AC101"],
            "channel_ids": ["surface"],
            "intervals": [{"start_ms": 0, "end_ms": 300}],
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
            "note": "Synthetic fixture only; not operational data.",
        },
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return manifest_bytes, event_bytes


def _upload(client: TestClient, token: str, bundle: tuple[bytes, bytes]):
    manifest_bytes, event_bytes = bundle
    return client.post(
        "/api/v1/replay-imports",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "manifest": ("manifest.json", manifest_bytes, "application/json"),
            "events": ("events.jsonl", event_bytes, "application/x-ndjson"),
        },
    )


@pytest.fixture
def client(tmp_path: Path):
    now = [1_800_000_000.0]
    app = create_app(
        tmp_path / "be04.sqlite",
        operator_key=OPERATOR_KEY,
        run_clock=False,
        wall_clock=lambda: now[0],
        monotonic_clock=lambda: now[0],
    )
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/auth/operator", json={"key": OPERATOR_KEY})
        assert response.status_code == 200
        yield test_client, response.json()["token"], now


def _imported(client: TestClient, token: str, source_id: str = "source-be04") -> dict[str, Any]:
    response = _upload(client, token, _bundle(source_id))
    assert response.status_code == 201, response.text
    return response.json()


def _save_analysis(client: TestClient, source_session_id: str, analysis_id: str = "analysis-be04") -> None:
    manager = client.app.state.manager
    metadata = manager.replay_import_reader.metadata(source_session_id)
    assert metadata is not None
    stored = manager.archive.replay_source(source_session_id)
    assert stored is not None
    analysis = {
        "id": analysis_id,
        "source_id": stored["source_id"],
        "source_session_id": source_session_id,
        "kind": "detector",
        "input_hash": "a" * 64,
        "versions": {"schema_version": "replay-1", "layout_version": "1"},
        "window_start_ms": 100,
        "window_end_ms": 300,
        "status": "completed_degraded",
    }
    frames: list[dict[str, Any]] = []
    for at_ms in (100, 200, 300):
        frames.append(
            {
                "analysis_id": analysis_id,
                "at_ms": at_ms,
                "state": {
                    "source_id": stored["source_id"],
                    "as_of_ms": at_ms,
                    "coverage_status": "known",
                    "coverage": metadata["manifest"]["coverage"],
                    "tracks": {"AC101": {"id": "AC101", "x_m": float(at_ms)}},
                    "clearances": [],
                    "requests": [],
                    "runway": {"open": True},
                    "simulator_truth": {"secret": "must not leak"},
                },
                "detector_result": {"predictions": [{"sample_ms": at_ms}], "private_schedule": ["hidden"]},
                "alerts": {"alert-be04": {"id": "alert-be04", "severity": "AMBER"}},
                "lifecycle_events": [],
                "status": "evaluated",
                "private_checkpoint": {"secret": "hidden"},
            }
        )
    manager.archive.save_replay_analysis(analysis, frames)


def test_import_receipt_retry_conflicts_and_invalid_upload_are_atomic(client) -> None:
    test_client, token, _ = client
    bundle = _bundle("import-atomic")
    first = _upload(test_client, token, bundle)
    assert first.status_code == 201
    receipt = first.json()
    assert set(receipt) == {"source_session_id", "source_id", "import_status"}
    assert receipt["source_session_id"].startswith("replay-")
    assert receipt["source_id"] == "import-atomic"
    assert receipt["import_status"] == "completed"
    retry = _upload(test_client, token, bundle)
    assert retry.status_code == 201
    assert retry.json() == receipt

    changed_manifest, changed_events = _bundle("import-atomic", changed=True)
    hash_conflict = _upload(test_client, token, (bundle[0], changed_events))
    assert hash_conflict.status_code == 422
    identity_conflict = _upload(test_client, token, (changed_manifest, changed_events))
    assert identity_conflict.status_code == 409

    malformed = _upload(test_client, token, (b"{bad json", bundle[1]))
    assert malformed.status_code == 422
    missing_part = test_client.post(
        "/api/v1/replay-imports",
        headers={"Authorization": f"Bearer {token}"},
        files={"manifest": ("manifest.json", bundle[0], "application/json")},
    )
    assert missing_part.status_code == 422
    archive = test_client.app.state.manager.archive
    assert archive.replay_sources_for_idempotency("import-atomic") is not None
    assert archive.replay_sources_for_idempotency("malformed-source") is None
    count = archive.db.execute("SELECT COUNT(*) FROM replay_import_receipts").fetchone()[0]
    assert count == 1


def test_public_source_frame_analysis_and_event_cursor_are_scoped(client) -> None:
    test_client, token, _ = client
    imported = _imported(test_client, token)
    source_session_id = imported["source_session_id"]
    _save_analysis(test_client, source_session_id)

    source = test_client.get(
        f"/api/v1/sessions/{source_session_id}/replay-source",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert source.status_code == 200
    source_body = source.json()
    assert source_body["source_id"] == "source-be04"
    assert source_body["analyses"][0]["id"] == "analysis-be04"
    serialized_source = json.dumps(source_body)
    for forbidden in ("source_ref", "local-export", "private_checkpoint", "simulator_truth", "private_schedule"):
        assert forbidden not in serialized_source

    historical = test_client.get(
        f"/api/v1/sessions/{source_session_id}/replay-frame",
        params={"at_ms": 150, "analysis_id": "analysis-be04"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert historical.status_code == 200
    historical_body = historical.json()
    assert historical_body["frame_ms"] == 100
    assert historical_body["frame_ms"] <= historical_body["requested_ms"]
    assert historical_body["state"]["predictions"] == [{"sample_ms": 100}]
    assert historical_body["state"]["analysis_id"] == "analysis-be04"

    source_only = test_client.get(
        f"/api/v1/sessions/{source_session_id}/replay-frame",
        params={"at_ms": 250},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert source_only.status_code == 200
    source_only_state = source_only.json()["state"]
    assert source_only.json()["frame_ms"] == 100
    assert source_only_state["predictions"] is None
    assert source_only_state["alerts"] is None
    assert source_only_state["tracks"]["AC101"]["x_m"] == 101.0
    serialized_frame = json.dumps(historical_body)
    for forbidden in ("source_ref", "private_checkpoint", "simulator_truth", "private_schedule"):
        assert forbidden not in serialized_frame

    unavailable = test_client.get(
        f"/api/v1/sessions/{source_session_id}/replay-frame",
        params={"at_ms": 50, "analysis_id": "analysis-be04"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unavailable.status_code == 200
    assert unavailable.json()["frame_ms"] is None
    assert unavailable.json()["state"]["predictions"] is None
    assert unavailable.json()["state"]["alerts"] is None

    page_one = test_client.get(
        f"/api/v1/sessions/{source_session_id}/events",
        params={"limit": 1, "until_ms": 200},
        headers={"Authorization": f"Bearer {token}"},
    )
    page_two = test_client.get(
        f"/api/v1/sessions/{source_session_id}/events",
        params={"limit": 1, "until_ms": 200, "cursor": page_one.json()["next_cursor"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert [page_one.json()["items"][0]["event"]["ordinal"],
            page_two.json()["items"][0]["event"]["ordinal"]] == [0, 1]
    assert all(item["event"]["sim_ms"] <= 200 for page in (page_one, page_two) for item in page.json()["items"])
    after_cutoff = test_client.get(
        f"/api/v1/sessions/{source_session_id}/events",
        params={"limit": 1, "until_ms": 200, "cursor": page_two.json()["next_cursor"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_cutoff.json()["items"] == []


def test_evidence_resolves_only_available_references(client) -> None:
    test_client, token, _ = client
    source_session_id = _imported(test_client, token, "evidence-source")["source_session_id"]
    _save_analysis(test_client, source_session_id)
    url = f"/api/v1/sessions/{source_session_id}/evidence"

    response = test_client.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "refs": [
                {"kind": "session_event", "id": "evt-0"},
                {"kind": "session_event", "id": "evt-2"},
                {"kind": "session_event", "id": "missing-event"},
                {"kind": "transcript_segment", "id": "segment-1"},
                {"kind": "detector_alert", "id": "alert-be04"},
            ],
            "until_ms": 150,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert [entry["ref"]["id"] for entry in body["items"]] == ["evt-0"]
    reasons = {entry["ref"]["id"]: entry["reason"] for entry in body["unresolved"]}
    assert reasons == {
        "evt-2": "outside_time_window",
        "missing-event": "not_found",
        "segment-1": "not_available",
        "alert-be04": "analysis_not_selected",
    }

    derived = test_client.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"refs": [{"kind": "detector_alert", "id": "alert-be04"}],
              "until_ms": 200, "analysis_id": "analysis-be04"},
    )
    assert derived.status_code == 200
    assert derived.json()["items"][0]["item"]["alert"]["id"] == "alert-be04"


def test_source_read_token_scope_expiry_and_read_only_controls(client) -> None:
    test_client, token, now = client
    imported = _imported(test_client, token, "scoped-source")
    source_id = imported["source_session_id"]
    created_review = test_client.post(
        f"/api/v1/sessions/{source_id}/reviews", headers={"Authorization": f"Bearer {token}"}
    )
    assert created_review.status_code == 201
    review = created_review.json()
    source_read_token = review["source_read_token"]
    read_headers = {"Authorization": f"Bearer {source_read_token}"}
    assert test_client.get(f"/api/v1/sessions/{source_id}/replay-source", headers=read_headers).status_code == 200

    other = _imported(test_client, token, "other-source")
    cross_source = test_client.get(
        f"/api/v1/sessions/{other['source_session_id']}/replay-frame",
        params={"at_ms": 100}, headers=read_headers,
    )
    assert cross_source.status_code == 403
    for path, method, payload in (
        (f"/api/v1/sessions/{source_id}/commands", "post",
         {"command_id": "source-write", "expected_revision": 0, "type": "START"}),
        (f"/api/v1/sessions/{source_id}/seats", "post", {"role": "tower", "label": "Seat"}),
        (f"/api/v1/sessions/{source_id}/branches", "post", {"at_ms": 100}),
    ):
        response = getattr(test_client, method)(path, headers=read_headers, json=payload)
        assert response.status_code == 403
    import_blocked = _upload(test_client, source_read_token, _bundle("read-token-import"))
    assert import_blocked.status_code == 403
    assert test_client.get(f"/api/v1/sessions/{source_id}/snapshot", headers=read_headers).status_code == 403

    review_headers = {"Authorization": f"Bearer {review['token']}"}
    initial_events = test_client.get(f"/api/v1/sessions/{review['id']}/events", headers=review_headers)
    assert initial_events.status_code == 200
    assert initial_events.json() == {"items": [], "next_cursor": None}
    seek = test_client.post(
        f"/api/v1/sessions/{review['id']}/commands",
        headers=review_headers,
        json={"command_id": "seek-review", "expected_revision": 0, "type": "SEEK", "value": 0.2},
    )
    assert seek.status_code == 200
    visible_events = test_client.get(
        f"/api/v1/sessions/{review['id']}/events", params={"limit": 1}, headers=review_headers
    )
    assert visible_events.status_code == 200
    assert visible_events.json()["items"][0]["event"]["ordinal"] == 0
    simulator_control = test_client.post(
        f"/api/v1/sessions/{review['id']}/commands",
        headers=review_headers,
        json={"command_id": "no-simulator-clearance", "expected_revision": 1, "type": "CLEARANCE",
              "target": "AC101", "instruction": "LAND", "runway": "09"},
    )
    assert simulator_control.status_code == 409
    snapshot = test_client.get(f"/api/v1/sessions/{review['id']}/snapshot", headers=review_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["playback_ms"] == 200
    assert snapshot.json()["predictions"] is None
    assert snapshot.json()["alerts"] is None
    serialized_review = json.dumps(snapshot.json())
    for forbidden in ("source_ref", "local-export", "private_checkpoint", "simulator_truth", "private_schedule"):
        assert forbidden not in serialized_review
    branch = test_client.post(
        f"/api/v1/sessions/{review['id']}/branches", headers=review_headers, json={"at_ms": 100}
    )
    assert branch.status_code == 409
    mutate_source = test_client.post(
        f"/api/v1/sessions/{source_id}/commands",
        headers={"Authorization": f"Bearer {token}"},
        json={"command_id": "source-start", "expected_revision": 0, "type": "START"},
    )
    assert mutate_source.status_code == 409
    stored = test_client.app.state.manager.archive.replay_source(source_id)
    assert stored is not None
    assert stored["event_bytes"] == _bundle("scoped-source")[1]
    assert stored["content_hash"] == hashlib.sha256(_bundle("scoped-source")[1]).hexdigest()
    assert test_client.app.state.manager.archive.replay_source("read-token-import") is None

    now[0] += 8 * 3600 + 1
    expired = test_client.get(f"/api/v1/sessions/{source_id}/replay-source", headers=read_headers)
    assert expired.status_code == 401


def test_synthetic_login_command_snapshot_and_first_message_websocket_compatibility(client) -> None:
    test_client, token, _ = client
    created = test_client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"scenario_id": "overlap", "seed": 7},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]
    command = test_client.post(
        f"/api/v1/sessions/{session_id}/commands",
        headers={"Authorization": f"Bearer {token}"},
        json={"command_id": "start-compat", "expected_revision": 0, "type": "START"},
    )
    assert command.status_code == 200
    snapshot = test_client.get(
        f"/api/v1/sessions/{session_id}/snapshot", headers={"Authorization": f"Bearer {token}"}
    )
    assert snapshot.status_code == 200
    assert snapshot.json()["kind"] == "training"
    with test_client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as socket:
        socket.send_json({"token": token})
        message = socket.receive_json()
        assert message["session_id"] == session_id
        assert message["kind"] == "training"
        assert "seat" in message
