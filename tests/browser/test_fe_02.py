from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


def _set_seek_draft(page: Page, milliseconds: int) -> None:
    page.evaluate(
        """(value) => {
          const slider = document.querySelector('#replay-time-range');
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(slider, String(value));
          slider.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        milliseconds,
    )
    page.get_by_role("button", name=f"Seek to {milliseconds} ms").click()


@pytest.mark.qa05_mode("fixture")
def test_fe_02_typed_evidence_link_states_and_unknown_alignment(page: Page, ui_server: str, screenshot):
    requests: list[str] = []
    page.on("request", lambda request: requests.append(f"{request.method} {request.url}"))
    page.goto(ui_server, wait_until="networkidle")
    expect(page.get_by_role("heading", name="Highlights and candidate options")).to_be_visible()

    # A linked transcript ref stays audio-relative because alignment is explicitly unknown.
    linked_highlight = page.locator(".candidate-card").filter(has_text="HI-FE05-LINKED-01")
    expect(linked_highlight).to_contain_text("Link state")
    expect(linked_highlight).to_contain_text("linked")
    linked_highlight.locator('[id="evidence-transcript_segment-SEG-FE05-COR-02"]').click()
    # FE-05 passes the replay cutoff into a transcript lookup even when alignment is unknown;
    # the adapter safely leaves replay time unchanged and reports unresolved at that cutoff.
    expect(linked_highlight).to_contain_text("UNRESOLVED · this exact reference is missing, outside the selected time, or outside the available scope.")
    expect(page.locator(".timeline-footer")).to_contain_text("requested 74600 ms")
    expect(page.locator('[data-lane="transcript"]')).to_contain_text("SESSION ALIGNMENT UNKNOWN · SHOWN OUTSIDE THE TIMELINE")
    expect(page.locator('[data-lane="transcript"]')).to_contain_text("audio-relative 3400–4600 ms")

    # Proximity-only evidence is rendered as possible_link and does not merge identities.
    possible_highlight = page.locator(".candidate-card").filter(has_text="HI-FE05-POSSIBLE-02")
    possible_highlight.locator('[id="evidence-session_event-SYN-FE-03:TRACK:TUG-04"]').click()
    expect(page.get_by_text("Opened exact source reference at 74360 ms SIM through the read-only frame port. No replay command was sent.")).to_be_visible()
    expect(page.locator(".timeline-footer")).to_contain_text("requested 74360 ms")
    expect(page.get_by_text("possible link", exact=True).first).to_be_visible()

    # The linked clearance is outside this selected cutoff, so it stays unresolved and does not move replay time.
    _set_seek_draft(page, 73_000)
    linked_highlight.locator('[id="evidence-session_event-SYN-FE-03:CLR:01"]').click()
    expect(linked_highlight.get_by_text("UNRESOLVED · this exact reference is missing, outside the selected time, or outside the available scope.")).to_be_visible()
    expect(page.locator(".timeline-footer")).to_contain_text("requested 73000 ms")
    screenshot("fixture-evidence-cutoff")
    assert not any("/commands" in request for request in requests)


@pytest.mark.qa05_mode("fixture")
def test_fe_02_api_adapter_marks_typed_evidence_unavailable_without_source_read(page: Page, ui_server: str):
    """Browser module check only: no fabricated source-read credential and no network request."""
    page.goto(ui_server, wait_until="networkidle")
    result = page.evaluate(
        """async () => {
          const { ApiReplayReviewAdapter } = await import('/src/adapters/apiReplayReview.ts');
          const adapter = new ApiReplayReviewAdapter({ scope: { source_session_id: 'QA05-NO-SOURCE-READ' } });
          return await adapter.resolveEvidence('QA05-NO-SOURCE-READ', [
            { kind: 'session_event', id: 'EVT-QA05-UNAVAILABLE' },
          ], 1000);
        }"""
    )
    assert result == [{"ref": {"kind": "session_event", "id": "EVT-QA05-UNAVAILABLE"}, "state": "unavailable"}]
