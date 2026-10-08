"""MOCK journeys for PRD E2E-01..05 and degraded states (frontend only, SYNTHETIC data).

Mock control flags live in memory, so each test toggles them after the last full page load.
"""

from playwright.sync_api import Page, expect

from .conftest import S1, S_AUDIO_ONLY, S_HOLD_SHORT, S_REPORT_CLEAR

# Runway 27 · segment T-10 (E-13, "holding short runway zero nine").
SEG_ZERO_NINE = "b9c8e3c5-b9ea-4bf8-8b2a-346ab65cf73c"


def test_import_saves_immutable_source_without_provider_call(login) -> None:
    page: Page = login(path="/sessions/import")
    page.get_by_role("button", name="Use sample files").click()
    page.get_by_role("button", name="Continue to preview").click()
    expect(page.get_by_text("Undetermined is never treated as allowed.")).to_be_visible()
    # Validation finishes first; Save session does not wait for the cloud-audio decision.
    expect(page.get_by_role("button", name="Save session")).to_be_enabled(timeout=10000)

    page.get_by_role("button", name="Audio to cloud").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_role("radio", name="Allowed").click()
    save_permission = dialog.get_by_role("button", name="Save permission")
    expect(save_permission).to_be_disabled()  # basis is required for ALLOWED
    dialog.get_by_label("Basis").fill("Synthetic data created for this project.")
    save_permission.click()

    page.get_by_role("button", name="Save session").click()
    expect(page.get_by_text("No provider call has been made.")).to_be_visible()
    # Provider profiles are "Not verified" in MOCK: analysis is blocked with a stated reason.
    expect(page.get_by_text("Analysis is blocked")).to_be_visible()
    expect(page.get_by_role("button", name="Start analysis")).to_be_disabled()


def test_e2e01_correction_keeps_original_and_marks_results_stale(login) -> None:
    page: Page = login(path=f"/s/{S1}/review/transcript?mode=debrief&t=322000&segment={SEG_ZERO_NINE}")
    detail = page.get_by_role("region", name="Segment detail")
    expect(detail.get_by_text("Original STT hypothesis")).to_be_visible()

    detail.get_by_label("Transcript correction").fill("Holding short runway two seven, Flow lens two one four.")
    detail.get_by_label("Correction reason").fill("Audio check: the pilot said two seven.")
    detail.get_by_role("button", name="Save revision").click()

    expect(detail.get_by_text("Derived results are stale")).to_be_visible()
    # The original hypothesis stays stored and visible next to the revision.
    expect(detail.get_by_text("runway zero nine").first).to_be_visible()
    detail.get_by_role("button", name="Re-analyse as new run").click()
    expect(page.get_by_text("Run #04 queued")).to_be_visible()
    # Re-analysis does not switch the run under the reviewer.
    expect(page.get_by_text("Run #03").first).to_be_visible()


def test_e2e01_memory_shows_revised_readback_in_debrief(login) -> None:
    page: Page = login(path=f"/s/{S1}/memory?mode=debrief&t=400000")
    expect(page.get_by_text("CORRECTED")).to_be_visible()
    expect(page.get_by_text("Discrepancy detected")).to_be_visible()  # earlier state stays in history


def test_e2e02_open_loop_stays_open_and_gap_is_coverage(login) -> None:
    page: Page = login(path=f"/s/{S_REPORT_CLEAR}/review/findings?mode=debrief&t=700000")
    findings = page.get_by_role("list", name="Findings in session")
    expect(findings.get_by_text("Report clear awaited")).to_be_visible()
    expect(page.get_by_text("Another aircraft speaking does not close it.")).to_be_visible()
    expect(findings.get_by_text("Audio gap 09:30–10:10")).to_be_visible()


def test_e2e03_divergence_candidate_becomes_not_evaluable_on_stale_track(login, mock_flag) -> None:
    page: Page = login(path=f"/s/{S_HOLD_SHORT}/review/findings?mode=debrief")
    expect(page.get_by_text("DIVERGENCE_CANDIDATE")).to_be_visible()
    expect(page.get_by_text("AI findings and source alerts are recorded separately.").first).to_be_visible()

    page.get_by_role("link", name="Open workspace").click()
    expect(page.get_by_role("heading", name="Workspace", level=1)).to_be_visible()
    mock_flag("Stale tracks")
    expect(page.get_by_text("Track stale (age 38 s)").first).to_be_visible()
    expect(page.get_by_text("NOT_EVALUABLE").first).to_be_visible()


def test_e2e04_audio_only_and_provider_outage_produce_no_fake_content(login, mock_flag) -> None:
    page: Page = login(path=f"/s/{S_AUDIO_ONLY}/workspace?mode=debrief")
    expect(page.get_by_text("Audio-only session")).to_be_visible()
    expect(page.get_by_text("Track not available").first).to_be_visible()
    expect(page.get_by_text("Analysis is partial").first).to_be_visible()

    page.goto(page.url.split("/s/")[0] + f"/s/{S1}/debrief")
    expect(page.get_by_text("Key item to review")).to_be_visible()
    mock_flag("Provider outage")
    page.get_by_role("button", name="Create brief revision").click()
    expect(page.get_by_text("The analysis provider is unavailable.").first).to_be_visible()
    # Stored briefs stay readable; no new revision is added.
    expect(page.get_by_text("Brief revision 3 created")).to_have_count(0)
    expect(page.get_by_text("Key item to review")).to_be_visible()


def test_e2e05_option_rating_is_append_only_and_observer_cannot_rate(login, page: Page) -> None:
    login(path=f"/s/{S1}/review/options?mode=debrief&t=322000")
    expect(page.get_by_text("cannot be executed or sent")).to_be_visible()
    expect(page.get_by_text("Insufficient context")).to_be_visible()
    rating = page.get_by_role("radiogroup", name="Rating")
    for radio in rating.get_by_role("radio").all():
        expect(radio).not_to_be_checked()
    rating.get_by_role("radio", name="Relevant", exact=True).click()
    page.get_by_role("textbox", name="Rating reason").fill("Pairing check matches the evidence.")
    page.get_by_role("button", name="Save rating").click()
    expect(page.get_by_text("Revision 1 · You")).to_be_visible()

    # Role switch clears cached data, returns to the catalogue and drops write access.
    options_url = page.url
    page.get_by_role("button", name="Account menu").click()
    page.get_by_role("menuitem", name="Observer").click()
    expect(page.get_by_role("heading", name="Sessions", level=1)).to_be_visible()
    page.goto(options_url)
    expect(page.get_by_text("Rating is read-only")).to_be_visible()
    expect(page.get_by_role("button", name="Save rating")).to_have_count(0)


def test_connection_lost_pauses_saving_without_queueing(login, mock_flag) -> None:
    page: Page = login(path=f"/s/{S1}/review/findings?mode=debrief&t=322000")
    expect(page.get_by_role("heading", name="Reviewer decision")).to_be_visible()
    mock_flag("Connection lost")
    expect(page.get_by_text("Connection to the server lost.")).to_be_visible()
    expect(page.get_by_text("Saving is paused while disconnected.")).to_be_visible()
    mock_flag("Connection lost")
    expect(page.get_by_text("Saving is paused while disconnected.")).to_have_count(0, timeout=8000)


def test_keyboard_replay_and_evidence_drawer_return_focus(login) -> None:
    page: Page = login(path=f"/s/{S1}/workspace?t=322000")
    expect(page.get_by_role("heading", name="Workspace", level=1)).to_be_visible()
    page.keyboard.press("Space")
    expect(page.get_by_role("button", name="Pause")).to_be_visible()
    page.keyboard.press("Space")
    expect(page.get_by_role("button", name="Play")).to_be_visible()

    trigger = page.get_by_role("button", name="Listen to evidence").first
    trigger.focus()
    page.keyboard.press("Enter")
    drawer = page.get_by_role("dialog", name="Evidence · F-03")
    expect(drawer).to_be_visible()
    page.keyboard.press("Escape")
    expect(drawer).to_have_count(0)
    expect(trigger).to_be_focused()
