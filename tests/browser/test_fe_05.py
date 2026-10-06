from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.qa05_mode("fixture")
def test_fe_05_narrow_viewport_keyboard_focus_and_no_browser_errors(page: Page, ui_server: str, browser_diagnostics, screenshot):
    page.goto(ui_server, wait_until="networkidle")
    expect(page.get_by_role("heading", name="Replay review workspace")).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(100)
    dimensions = page.evaluate("({width: innerWidth, documentWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth})")
    assert dimensions["documentWidth"] <= dimensions["width"], f"Horizontal clipping at 390px: {dimensions}"
    screenshot("fixture-evaluator-narrow-viewport")

    page.set_viewport_size({"width": 1280, "height": 800})
    slider = page.get_by_role("slider", name="Seek requested replay time in session milliseconds")
    slider.focus()
    expect(slider).to_be_focused()
    slider.press("Home")
    seek = page.get_by_role("button", name="Seek to 0 ms")
    slider.press("Tab")
    expect(seek).to_be_focused()
    outline = seek.evaluate("element => getComputedStyle(element).outlineStyle")
    assert outline != "none", "Keyboard focus must have a visible outline."
    assert browser_diagnostics["console_errors"] == []
    assert browser_diagnostics["page_errors"] == []
    assert browser_diagnostics["failed_requests"] == []
    assert browser_diagnostics["http_5xx"] == []
