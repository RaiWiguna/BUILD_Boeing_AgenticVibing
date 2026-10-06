from __future__ import annotations

from playwright.sync_api import Page, expect

from scripts.run_mock_stack import SYNTHETIC_LABEL


def test_qa04_mock_launcher_opens_explicit_fixture_evaluator_ui(
    page: Page, qa04_mock_stack, screenshot,
):
    """Exercise the QA-04 loopback mock and its Vite child in native Chromium."""
    health = page.request.get(f"{qa04_mock_stack.api_url}/health")
    assert health.status == 200
    assert health.headers.get("x-flowlens-mode") == "fixture-mock"
    assert health.headers.get("x-flowlens-data-label") == SYNTHETIC_LABEL
    assert health.json()["mode"] == "fixture-mock"

    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    page.goto(qa04_mock_stack.web_url, wait_until="networkidle")

    expect(page.get_by_role("heading", name="Replay review workspace")).to_be_visible()
    expect(page.get_by_text("FIXTURE MODE", exact=True)).to_be_visible()
    expect(page.locator(".source-context-panel").get_by_text(SYNTHETIC_LABEL, exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Highlights and candidate options")).to_be_visible()
    expect(page.get_by_text("Fixture mode contains no audio bytes; playback is unavailable.")).to_be_visible()
    expect(page.get_by_text("No operational action is available.")).to_be_visible()

    assert not any("/commands" in url or "/audio-assets/" in url for url in requests)
    assert not any("https://" in url for url in requests)
    screenshot("qa04-mock-stack-fixture-evaluator")
