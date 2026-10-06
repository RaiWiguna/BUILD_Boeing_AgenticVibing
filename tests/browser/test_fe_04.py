from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.qa05_mode("fixture")
def test_fe_04_debrief_ai_outage_audio_unavailable_and_scope(page: Page, ui_server: str, screenshot):
    page.goto(ui_server, wait_until="networkidle")
    candidate_panel = page.get_by_role("region", name="Highlights and candidate options")
    expect(candidate_panel).to_contain_text("Authored synthetic fixture · no AI provider, server result, partner data, or operational evidence is represented.")
    expect(candidate_panel).not_to_contain_text("AI PROVIDER AVAILABLE")
    expect(page.get_by_role("heading", name="Source audio playback")).to_be_visible()
    expect(page.get_by_text("Fixture mode contains no audio bytes; playback is unavailable.")).to_be_visible()

    debrief = page.get_by_role("region", name="Evidence debrief")
    expect(debrief).to_contain_text("FIXTURE DEBRIEF")
    expect(debrief).to_contain_text("not ASR output, partner replay, server results, domain review, or operational evidence")
    expect(debrief).to_contain_text("replay alignment is unknown")
    expect(candidate_panel).to_contain_text("No operational suitability or procedure is asserted.")
    expect(debrief).to_contain_text("No operational action is available.")
    # Participant-safe UI must not open or render the instructor-only report/truth route.
    expect(page.get_by_role("button", name="Export report")).to_have_count(0)
    expect(debrief).to_contain_text("the current report route is instructor-only and can contain restricted ground truth")


@pytest.mark.qa05_mode("fixture")
@pytest.mark.xfail(strict=True, reason="FE-05 fixture subscription replaces provider_availability=unavailable with unknown in its snapshot projection")
def test_fe_04_fixture_provider_unavailable_badge(page: Page, ui_server: str):
    """Expected UI boundary; currently xfailed because the FE-05 subscription projection says Unknown."""
    page.goto(ui_server, wait_until="networkidle")
    expect(page.get_by_role("region", name="Highlights and candidate options")).to_contain_text("AI PROVIDER UNAVAILABLE")
    screenshot("fixture-evidence-debrief")


@pytest.mark.qa05_mode("training")
def test_fe_04_training_view_has_no_evaluator_options(page: Page, ui_server: str):
    page.goto(ui_server, wait_until="networkidle")
    expect(page.get_by_text("AUTHORED SYNTHETIC · TRAINING VIEW", exact=True)).to_be_visible()
    expect(page.get_by_text("Evaluator capability is denied for this view. No highlights or options are shown.")).to_be_visible()
    expect(page.get_by_text("Hypothetical option candidate", exact=True)).to_have_count(0)
    expect(page.get_by_text("Candidate outputs are unavailable or evaluator access was not granted; no options are included in this debrief.")).to_be_visible()
    expect(page.locator(".transcript-segment").first).to_contain_text("Correction editor unavailable: evaluator review scope is denied. No correction request was sent.")
    assert page.get_by_label("Supported speed").count() == 1
    assert page.get_by_label("role", exact=True).count() == 0
