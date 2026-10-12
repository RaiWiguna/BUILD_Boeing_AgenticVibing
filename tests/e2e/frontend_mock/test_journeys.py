"""MOCK journeys E2E-01..05 (frontend only, SYNTHETIC data, no backend or provider)."""

from playwright.sync_api import Page, expect

from .conftest import S1


def test_sessions_list_has_no_mock_labels(login) -> None:
    page: Page = login()
    expect(page.get_by_role("heading", name="Sessions", level=1)).to_be_visible()
    expect(page.get_by_text("MOCK", exact=True)).to_have_count(0)


def test_as_known_hides_not_yet_available_findings(login) -> None:
    # F-03: event 05:19, available 05:22. At 05:20 As-known must not show it; Debrief may.
    page: Page = login(path=f"/s/{S1}/review/findings?mode=as-known&t=320000")
    expect(page.get_by_role("heading", name="Findings in session")).to_be_visible()
    expect(page.get_by_text("Runway mismatch")).to_have_count(0)
    # The As-known banner names what became available later and offers the full session.
    expect(page.get_by_text("Showing what was known at 05:20.0.")).to_be_visible()
    expect(page.get_by_text("became available later in the session")).to_be_visible()
    page.get_by_role("button", name="Show full session").click()
    list_ = page.get_by_role("list", name="Findings in session")
    expect(list_.get_by_text("Runway mismatch")).to_be_visible()


def test_finding_review_is_append_only_with_required_reason(login) -> None:
    page: Page = login(path=f"/s/{S1}/review/findings?mode=debrief&t=322000")
    decision = page.get_by_role("radiogroup", name="Decision")
    for radio in decision.get_by_role("radio").all():
        expect(radio).not_to_be_checked()
    save = page.get_by_role("button", name="Save review")
    expect(save).to_have_attribute("aria-disabled", "true")
    decision.get_by_role("radio", name="Cannot be determined yet").click()
    reason = page.get_by_role("textbox", name="Reason")
    reason.focus()
    reason.blur()
    expect(page.get_by_text("A reason is required")).to_be_visible()
    reason.fill("Speaker identity not confirmed in audio.")
    page.get_by_role("button", name="Save review").click()
    expect(page.get_by_text("Revision 1 · You")).to_be_visible()


def test_observer_review_is_read_only(login) -> None:
    page: Page = login("observer@flowlens.test", path=f"/s/{S1}/review/findings?mode=debrief&t=322000")
    expect(page.get_by_text("Review is read-only for your role")).to_be_visible()
    expect(page.get_by_role("button", name="Save review")).to_have_count(0)


def test_debrief_export_job_reaches_ready_without_audio(login) -> None:
    page: Page = login(path=f"/s/{S1}/debrief")
    expect(page.get_by_text("Key item to review")).to_be_visible()
    # Export lives in a sheet opened from the header (decision D-4).
    page.get_by_role("button", name="Export report").click()
    expect(page.get_by_role("dialog", name="Export report")).to_be_visible()
    expect(page.get_by_role("switch", name="Include audio")).to_be_disabled()
    expect(page.get_by_role("switch", name="Include provenance")).to_be_checked()
    page.get_by_role("button", name="Create export").click()
    expect(page.get_by_text("Ready").first).to_be_visible(timeout=6000)
    expect(page.get_by_role("button", name="Download").first).to_be_visible()


def test_tablet_viewport_workspace_renders(login, page: Page) -> None:
    page.set_viewport_size({"width": 1024, "height": 768})
    login(path=f"/s/{S1}/workspace?t=322000")
    expect(page.get_by_role("heading", name="Workspace", level=1)).to_be_visible()
    expect(page.get_by_text("No audio").first).to_be_visible()
