from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.qa05_mode("fixture")
def test_fe_03_transcript_provenance_and_conflict_reconcile_retry(page: Page, ui_server: str, screenshot):
    requests: list[str] = []
    page.on("request", lambda request: requests.append(f"{request.method} {request.url}"))
    page.goto(ui_server, wait_until="networkidle")

    segment = page.locator("#transcript-SEG-FE05-COR-02")
    expect(segment).to_contain_text("AUTHORED RAW TEXT · NOT ASR")
    expect(segment).to_contain_text("Tug four, cross runway twenty seven.")
    expect(segment).to_contain_text("CURRENT REVISION · r2")
    expect(segment).to_contain_text("Tug four, hold short runway twenty seven.")
    expect(segment).to_contain_text("ground · Ground · authored label")
    expect(segment).to_contain_text("Asset time")
    expect(segment).to_contain_text("audio-relative")
    expect(segment).to_contain_text("UNKNOWN · not placed on replay timeline")
    expect(segment).to_contain_text("Speaker provenance")
    expect(segment).to_contain_text("Unavailable")
    expect(segment).to_contain_text("authored-fixture-not-ASR")
    expect(segment).to_contain_text("Correction is an append-only reviewer revision. The raw text above is retained.")

    editor = segment.get_by_role("textbox", name="Corrected text draft · source text stays preserved")
    editor.fill("QA reviewer draft: retain as a local practice example.")
    segment.get_by_role("button", name="Submit correction").click()

    status = segment.locator(".review-status-message")
    expect(status).to_contain_text("CONFLICT")
    expect(status).to_contain_text("draft retained; refresh before retry")
    expect(editor).to_have_value("QA reviewer draft: retain as a local practice example.")
    expect(segment.get_by_role("button", name="Submit correction")).to_be_disabled()

    segment.get_by_role("button", name="Refresh / reconcile").click()
    expect(status).to_contain_text("refreshed; explicit retry available")
    expect(editor).to_have_value("QA reviewer draft: retain as a local practice example.")
    retry = segment.get_by_role("button", name="Retry with revision 3")
    expect(retry).to_be_enabled()
    retry.click()
    expect(status).to_contain_text("ACCEPTED · FIXTURE MEMORY ONLY · revision 4")
    expect(status).to_contain_text("no server persistence")
    expect(segment).to_contain_text("Tug four, cross runway twenty seven.")
    expect(segment).to_contain_text("QA reviewer draft: retain as a local practice example.")
    expect(segment).to_contain_text("CURRENT REVISION · r4")
    expect(page.locator(".reviewer-notes")).to_contain_text("QA reviewer draft: retain as a local practice example.")
    screenshot("fixture-transcript-conflict-reconciled")
    assert not any("/commands" in request for request in requests)
