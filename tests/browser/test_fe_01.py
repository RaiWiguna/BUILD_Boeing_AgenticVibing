from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.qa05_mode("fixture")
def test_fe_01_setup_map_seek_and_cutoff(page: Page, ui_server: str, browser_diagnostics, screenshot):
    requests: list[str] = []
    page.on("request", lambda request: requests.append(f"{request.method} {request.url}"))
    page.goto(ui_server, wait_until="networkidle")

    expect(page.get_by_role("heading", name="Replay review workspace")).to_be_visible()
    expect(page.get_by_text("FIXTURE MODE", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Synthetic replay review fixture")).to_be_visible()
    expect(page.locator(".source-context-panel").get_by_text("SYNTHETIC / NOT OPERATIONALLY VALIDATED", exact=True)).to_be_visible()
    expect(page.get_by_role("img", name=re.compile("runway layout and track positions"))).to_be_visible()
    expect(page.locator(".track-data-row.is-last-known")).to_contain_text("LAST-KNOWN · STALE")
    expect(page.locator(".timeline-footer")).to_contain_text("Actual frame 74600 ms · requested 74600 ms")
    screenshot("fixture-evaluator-desktop")

    slider = page.get_by_role("slider", name="Seek requested replay time in session milliseconds")
    slider.focus()
    slider.press("Home")
    expect(page.get_by_role("button", name="Seek to 0 ms")).to_be_visible()
    slider.press("Tab")
    seek_start = page.get_by_role("button", name="Seek to 0 ms")
    expect(seek_start).to_be_focused()
    seek_start.click()
    expect(page.locator(".timeline-footer")).to_contain_text("Actual frame 0 ms · requested 0 ms")

    # Set the native range input to a replay cutoff, then use the visible Seek action.
    page.evaluate(
        """() => {
          const slider = document.querySelector('#replay-time-range');
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(slider, '73500');
          slider.dispatchEvent(new Event('input', { bubbles: true }));
        }"""
    )
    seek_cutoff = page.get_by_role("button", name="Seek to 73500 ms")
    expect(seek_cutoff).to_be_enabled()
    seek_cutoff.click()
    expect(page.locator(".timeline-footer")).to_contain_text("Actual frame 0 ms · requested 73500 ms")
    expect(page.locator(".timeline-lane").filter(has_text="SOURCE / COMMUNICATION")).to_contain_text("Authored synthetic phrase for timeline layout only; not transcribed audio.")
    expect(page.locator(".timeline-lane").filter(has_text="STRUCTURED CLEARANCE")).to_contain_text("Synthetic HOLD_SHORT clearance recorded for TUG-04.")
    timeline = page.locator(".replay-timeline-panel")
    expect(timeline.get_by_text("Synthetic last-known vehicle position; this sample is stale at the displayed frame.")).to_have_count(0)
    expect(timeline.get_by_text("Authored deterministic alert fixture; no operational inference.")).to_have_count(0)
    # The returned frame never exceeds the selected cutoff; this is a UI fixture check, not a geometry oracle.
    assert not any("/api/" in request or request.endswith("/health") for request in requests)
    assert browser_diagnostics == {"console_errors": [], "page_errors": [], "failed_requests": [], "http_5xx": []}


@pytest.mark.qa05_mode("fixture")
def test_mock_stack_is_explicit_frontend_fixture_only(page: Page, ui_server: str):
    """QA-05 inline FE fixture check; this is not the absent QA-04 mock-stack launcher."""
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    page.goto(ui_server, wait_until="networkidle")
    expect(page.get_by_text("FIXTURE MODE", exact=True)).to_be_visible()
    expect(page.get_by_text("No ASR, AI provider, partner simulator, server result, domain review or operational validation is represented.")).to_be_visible()
    assert not any("/api/" in request or request.endswith("/health") for request in requests)
