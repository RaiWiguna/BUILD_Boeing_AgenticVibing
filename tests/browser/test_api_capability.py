from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from conftest import TEST_OPERATOR_KEY
from scripts.run_mock_stack import SYNTHETIC_LABEL


@pytest.mark.qa05_mode("api")
def test_api_mode_does_not_fall_back_for_legacy_training_review(page: Page, ui_server: str, actual_backend: str, browser_diagnostics, screenshot):
    """The legacy synthetic-session UI stays in API mode and never substitutes fixture replay data."""
    page.goto(ui_server, wait_until="networkidle")
    page.get_by_label("Local operator key").fill(TEST_OPERATOR_KEY)
    page.get_by_role("button", name="Connect").click()
    expect(page.get_by_label("Training session", exact=True)).to_be_visible()
    page.get_by_role("button", name="Create synthetic session").click()
    expect(page.locator("#session-heading")).not_to_have_text("Session data", timeout=10_000)
    session_copy = page.locator("#session-heading").locator("xpath=following-sibling::p").inner_text()
    session_id = next(part.strip() for part in session_copy.split("·") if re.fullmatch(r"[0-9a-f]{12}", part.strip()))

    # Independently end the temporary local session so CURRENT_SOURCE can open a frozen review.
    # This test-only operator credential is never sent to source-read routes.
    auth = page.context.request.post(
        f"{actual_backend}/api/v1/auth/operator", data={"key": TEST_OPERATOR_KEY}
    )
    assert auth.status == 200
    operator_token = auth.json()["token"]
    ended = page.context.request.post(
        f"{actual_backend}/api/v1/sessions/{session_id}/commands",
        headers={"Authorization": f"Bearer {operator_token}"},
        data={"command_id": "qa05-end-temporary-session", "expected_revision": 0, "type": "END"},
    )
    assert ended.status == 200, ended.text()

    page.get_by_role("button", name="Refresh data").click()
    expect(page.get_by_role("button", name="Open review")).to_be_enabled(timeout=10_000)
    page.get_by_role("button", name="Open review").click()
    expect(page.get_by_text("The current backend does not issue a separate source-read credential.")).to_be_visible(timeout=10_000)
    expect(page.get_by_text("API DEBRIEF", exact=True)).to_be_visible()
    expect(page.get_by_text("Transcript content is unavailable in this view. Existing replay context remains separate.")).to_be_visible()
    expect(page.get_by_text("Evaluator capability is unknown for this view. No highlights or options are shown.")).to_be_visible()
    expect(page.get_by_text("FIXTURE DEBRIEF", exact=True)).to_have_count(0)
    expect(page.get_by_text("Hypothetical option candidate", exact=True)).to_have_count(0)

    # The route exists in current source; this synthetic training session is not an imported replay source.
    openapi = page.context.request.get(f"{actual_backend}/openapi.json").json()
    assert "/api/v1/sessions/{id}/transcripts" in openapi["paths"]
    route_probe = page.context.request.get(
        f"{actual_backend}/api/v1/sessions/{session_id}/transcripts",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert route_probe.status == 404
    assert route_probe.json()["detail"] == "Replay source not found"
    screenshot("real-api-legacy-training-no-fixture-fallback")

    assert browser_diagnostics["page_errors"] == []
    assert browser_diagnostics["http_5xx"] == []


@pytest.mark.qa05_mode("api")
def test_real_api_role_contexts_cannot_elevate_or_read_instructor_report(page: Page, actual_backend: str):
    """Four role tokens are scoped against the real current API; instructor report contents are never read."""
    login = page.context.request.post(f"{actual_backend}/api/v1/auth/operator", data={"key": TEST_OPERATOR_KEY})
    assert login.status == 200
    instructor_token = login.json()["token"]
    created = page.context.request.post(
        f"{actual_backend}/api/v1/sessions",
        headers={"Authorization": f"Bearer {instructor_token}"},
        data={"scenario_id": "safe_cross", "seed": 505, "condition": "baseline"},
    )
    assert created.status == 201, created.text()
    session_id = created.json()["id"]

    for role in ("tower", "ground", "observer"):
        response = page.context.request.post(
            f"{actual_backend}/api/v1/sessions/{session_id}/seats",
            headers={"Authorization": f"Bearer {instructor_token}"},
            data={"role": role, "label": f"QA05 {role} participant"},
        )
        assert response.status == 201, response.text()
        seat_token = response.json()["token"]
        snapshot = page.context.request.get(
            f"{actual_backend}/api/v1/sessions/{session_id}/snapshot",
            headers={"Authorization": f"Bearer {seat_token}"},
        )
        assert snapshot.status == 200
        projection = snapshot.json()
        assert projection["seat"]["role"] == role
        assert projection["predictions"] == []  # baseline projection redacts instructor-only explanations
        report = page.context.request.get(
            f"{actual_backend}/api/v1/sessions/{session_id}/report?format=json",
            headers={"Authorization": f"Bearer {seat_token}"},
        )
        assert report.status == 403
        role_switch = page.context.request.post(
            f"{actual_backend}/api/v1/sessions/{session_id}/seats",
            headers={"Authorization": f"Bearer {seat_token}"},
            data={"role": "instructor", "label": "attempted role escalation"},
        )
        assert role_switch.status == 403

    assert page.locator("body").count() == 1


@pytest.mark.qa05_mode("api")
def test_current_api_imported_replay_cutoff_scope_review_and_debrief(page: Page, actual_backend: str):
    """Exercise real additive routes with only the public synthetic F-REPLAY-01 input."""
    docs = page.goto(f"{actual_backend}/docs", wait_until="domcontentloaded")
    assert docs is not None and docs.status == 200
    request = page.context.request
    login = request.post(f"{actual_backend}/api/v1/auth/operator", data={"key": TEST_OPERATOR_KEY})
    assert login.status == 200
    operator_token = login.json()["token"]
    operator_headers = {"Authorization": f"Bearer {operator_token}"}

    fixture_root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "replay"
    fixture_manifest_bytes = (fixture_root / "manifest.json").read_bytes()
    fixture_event_bytes = (fixture_root / "source-events.jsonl").read_bytes().replace(b"\r\n", b"\n")
    fixture_manifest = json.loads(fixture_manifest_bytes)
    assert fixture_manifest["label"] == SYNTHETIC_LABEL
    assert fixture_manifest["privacy"]["private_data_included"] is False
    assert hashlib.sha256(fixture_event_bytes).hexdigest() == fixture_manifest["content_hash"]
    # The public QA-01 fixture manifest carries catalog/privacy fields beyond the
    # backend's strict normalized ReplaySourceManifest. Project only the public
    # normalized fields and add the schema-required layout/coverage metadata here;
    # this test-only projection is not a canonical fixture mapping.
    projected_events = []
    for line in fixture_event_bytes.splitlines():
        record = json.loads(line)
        event = record["event"]
        # The backend DTO keeps type-specific event data namespaced. Preserve the
        # public fixture values while projecting that shape for this import call.
        event["data"] = {
            key: event.pop(key)
            for key in ("issuer", "channel", "duration_ms", "instruction", "runway")
            if key in event
        }
        if record["source_time"]["clock"] != fixture_manifest["timebase"]["source_clock"]:
            # The fixture keeps observation time (74180 ms) on a separate
            # source clock; current normalized imports have one manifest
            # timebase. Retain that observation as event.observed_ms and map
            # availability to its receive/session time for this API exercise.
            record["source_time"] = {
                "value": event["sim_ms"],
                "unit": fixture_manifest["timebase"]["source_unit"],
                "clock": fixture_manifest["timebase"]["source_clock"],
            }
        projected_events.append(record)
    event_bytes = b"\n".join(
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        for record in projected_events
    ) + b"\n"

    manifest = {
        "schema_version": fixture_manifest["schema_version"],
        "source_id": fixture_manifest["source_id"],
        "source_kind": fixture_manifest["source_kind"],
        "source_ref": fixture_manifest["source_ref"],
        "content_hash": hashlib.sha256(event_bytes).hexdigest(),
        "provenance": {
            **fixture_manifest["provenance"],
            "derivation": f"{SYNTHETIC_LABEL}; {fixture_manifest['provenance']['derivation']}",
            "retention_reason": "Public synthetic browser test input; no real source is retained.",
        },
        "permission_profile": fixture_manifest["permission_profile"],
        "retention_until": fixture_manifest["retention_until"],
        "timebase": fixture_manifest["timebase"],
        "coverage": {"status": "known", **fixture_manifest["coverage"]},
        "layout": {**fixture_manifest["layout"], "name": "Synthetic local replay test layout"},
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    imported = request.post(
        f"{actual_backend}/api/v1/replay-imports",
        headers=operator_headers,
        multipart={
            "manifest": {"name": "manifest.json", "mimeType": "application/json", "buffer": manifest_bytes},
            "events": {"name": "source-events.jsonl", "mimeType": "application/x-ndjson", "buffer": event_bytes},
        },
    )
    assert imported.status == 201, imported.text()
    source_id = imported.json()["source_session_id"]
    assert imported.json()["source_id"] == manifest["source_id"]

    paths = request.get(f"{actual_backend}/openapi.json").json()["paths"]
    required_paths = {
        "/api/v1/replay-imports",
        "/api/v1/sessions/{id}/replay-source",
        "/api/v1/sessions/{id}/replay-frame",
        "/api/v1/sessions/{id}/evidence",
        "/api/v1/sessions/{id}/transcripts",
        "/api/v1/sessions/{id}/highlights",
        "/api/v1/sessions/{id}/replay-analyses/{analysis_id}/options",
        "/api/v1/sessions/{id}/debrief",
    }
    assert required_paths.issubset(paths)
    assert not any(path.endswith("/execute") for path in paths), "No option execute endpoint is exposed."

    review_response = request.post(f"{actual_backend}/api/v1/sessions/{source_id}/reviews", headers=operator_headers)
    assert review_response.status == 201, review_response.text()
    review = review_response.json()
    assert review["source_id"] == source_id
    assert review.get("source_read_token")
    source_headers = {"Authorization": f"Bearer {review['source_read_token']}"}

    source = request.get(f"{actual_backend}/api/v1/sessions/{source_id}/replay-source", headers=source_headers)
    assert source.status == 200, source.text()
    assert source.json()["source_session_id"] == source_id
    assert source.json()["manifest"]["source_kind"] == "synthetic"
    assert SYNTHETIC_LABEL in source.json()["manifest"]["provenance"]["derivation"]

    frame_before_receipt = request.get(
        f"{actual_backend}/api/v1/sessions/{source_id}/replay-frame",
        params={"at_ms": 74529}, headers=source_headers,
    )
    assert frame_before_receipt.status == 200, frame_before_receipt.text()
    frame_json = frame_before_receipt.json()
    assert frame_json["requested_ms"] == 74529
    assert frame_json["frame_ms"] == 73020
    assert frame_json["frame_ms"] <= frame_json["requested_ms"]
    frame_at_receipt = request.get(
        f"{actual_backend}/api/v1/sessions/{source_id}/replay-frame",
        params={"at_ms": 74530}, headers=source_headers,
    )
    assert frame_at_receipt.status == 200
    assert frame_at_receipt.json()["frame_ms"] == 74530

    refs = [
        {"kind": "session_event", "id": "EVT-CLR-021"},
        {"kind": "session_event", "id": "EVT-TRK-088"},
    ]
    cutoff = request.post(
        f"{actual_backend}/api/v1/sessions/{source_id}/evidence",
        headers=source_headers,
        data={"refs": refs, "until_ms": 74529},
    )
    assert cutoff.status == 200, cutoff.text()
    cutoff_json = cutoff.json()
    assert {item["ref"]["id"] for item in cutoff_json["items"]} == {"EVT-CLR-021"}
    assert {item["ref"]["id"] for item in cutoff_json["unresolved"]} == {"EVT-TRK-088"}
    complete = request.post(
        f"{actual_backend}/api/v1/sessions/{source_id}/evidence",
        headers=source_headers,
        data={"refs": refs, "until_ms": 74530},
    )
    assert complete.status == 200, complete.text()
    assert {item["ref"]["id"] for item in complete.json()["items"]} == {"EVT-CLR-021", "EVT-TRK-088"}
    assert complete.json()["unresolved"] == []

    # No worker/model/audio bytes are present in this API process or the replay fixture.
    runtime = request.get(f"{actual_backend}/api/v1/runtime-manifest", headers=operator_headers)
    assert runtime.status == 200, runtime.text()
    providers = runtime.json()["optional_providers"]
    assert providers["assist_worker"]["available"] is False
    assert providers["assist_worker"]["inference_verified"] is False
    assert providers["local_model"]["available"] is False
    transcripts = request.get(f"{actual_backend}/api/v1/sessions/{source_id}/transcripts", headers=source_headers)
    assert transcripts.status == 200, transcripts.text()
    assert transcripts.json()["items"] == []

    # Source-read scope is read-only and cannot be widened to another source or evaluator options.
    other_source = request.get(
        f"{actual_backend}/api/v1/sessions/QA05-OTHER-SYNTHETIC/replay-frame",
        params={"at_ms": 0}, headers=source_headers,
    )
    assert other_source.status == 403
    assert request.post(
        f"{actual_backend}/api/v1/sessions/{source_id}/commands",
        headers=source_headers,
        data={"command_id": "qa05-source-read-command", "expected_revision": 0, "type": "SEEK", "value": 0},
    ).status == 403
    assert request.get(
        f"{actual_backend}/api/v1/sessions/{source_id}/replay-analyses/AN-SYN-01/options",
        headers=source_headers,
    ).status == 403

    # The review control token can seek the frozen review; it cannot clear or mutate the source session.
    seek = request.post(
        f"{actual_backend}/api/v1/sessions/{review['id']}/commands",
        headers={"Authorization": f"Bearer {review['token']}"},
        data={"command_id": "qa05-review-seek", "expected_revision": 0, "type": "SEEK", "value": 73.02},
    )
    assert seek.status == 200, seek.text()
    review_snapshot = request.get(
        f"{actual_backend}/api/v1/sessions/{review['id']}/snapshot",
        headers={"Authorization": f"Bearer {review['token']}"},
    )
    assert review_snapshot.status == 200
    assert review_snapshot.json()["playback_ms"] == 73020
    source_command = request.post(
        f"{actual_backend}/api/v1/sessions/{source_id}/commands",
        headers=operator_headers,
        data={"command_id": "qa05-imported-source-command", "expected_revision": 0, "type": "START"},
    )
    assert source_command.status == 409

    for role in ("tower", "ground", "observer"):
        seat = request.post(
            f"{actual_backend}/api/v1/sessions/{source_id}/seats",
            headers=operator_headers,
            data={"role": role, "label": f"QA05 imported replay {role}"},
        )
        assert seat.status == 201, seat.text()
        participant = {"Authorization": f"Bearer {seat.json()['token']}"}
        assert request.get(f"{actual_backend}/api/v1/sessions/{source_id}/replay-source", headers=participant).status == 403
        assert request.get(f"{actual_backend}/api/v1/sessions/{source_id}/debrief", headers=participant).status == 403

    debrief = request.get(f"{actual_backend}/api/v1/sessions/{source_id}/debrief?format=json", headers=operator_headers)
    assert debrief.status == 200, debrief.text()
    assert source_id in json.dumps(debrief.json())
