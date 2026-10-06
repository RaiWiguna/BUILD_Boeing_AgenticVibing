from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from conftest import TEST_OPERATOR_KEY


@pytest.mark.qa05_mode("api")
def test_real_current_api_keeps_additive_routes_unavailable_without_source_read(page: Page, ui_server: str, actual_backend: str, browser_diagnostics, screenshot):
    """Real current-source API E2E; it does not claim the proposed replay/assist API exists."""
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
    expect(page.get_by_text("Backend does not implement the scoped assist review routes.", exact=False)).to_have_count(0)
    expect(page.get_by_text("The inspected backend has no transcript, highlight, candidate, or assist-stream routes for this replay profile.", exact=False).first).to_be_visible()
    expect(page.get_by_text("Transcript content is unavailable in this view. Existing replay context remains separate.")).to_be_visible()
    expect(page.get_by_text("Evaluator capability is unknown for this view. No highlights or options are shown.")).to_be_visible()
    expect(page.get_by_text("No ASR, AI provider, partner simulator, server result, domain review or operational validation is represented.")).to_have_count(0)
    expect(page.get_by_text("FIXTURE DEBRIEF", exact=True)).to_have_count(0)
    expect(page.get_by_text("Export unavailable: the current report route is instructor-only and can contain restricted ground truth. No participant-safe assist export route is present.")).to_be_visible()

    # Existing backend has no transcript/evidence/audio/options/review endpoints. An unauthenticated route probe
    # records availability only; it does not attach the operator or review-control token to source reads.
    route_probe = page.context.request.get(f"{actual_backend}/api/v1/sessions/{session_id}/transcripts")
    assert route_probe.status == 404
    screenshot("real-api-current-source-unavailable-capabilities")

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
