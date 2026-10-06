from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.qa05_mode("fixture")
def test_options_boundary_no_command_or_state_change(page: Page, ui_server: str, screenshot):
    requests: list[str] = []
    page.on("request", lambda request: requests.append(f"{request.method} {request.url}"))
    page.goto(ui_server, wait_until="networkidle")
    candidate_panel = page.get_by_role("region", name="Highlights and candidate options")
    expect(candidate_panel).to_contain_text("Evaluator replay view only")
    expect(candidate_panel).to_contain_text("Hypothetical option candidate")
    expect(candidate_panel).to_contain_text("Typed supporting evidence refs")
    expect(candidate_panel).to_contain_text("No execute, send-clearance, command, severity, or lifecycle action exists here.")

    alert = page.locator("#alert-ALERT-FE-03-01")
    expect(alert).to_contain_text("DATA_DEGRADED")
    expect(alert).to_contain_text("ACTIVE")
    candidate = candidate_panel.locator(".option-card").filter(has_text="OPT-FE05-SYN-01")
    candidate.get_by_role("button", name="Confirmed").click()
    expect(candidate.locator(".review-status-message")).to_contain_text("ACCEPTED · FIXTURE MEMORY ONLY")
    expect(candidate.locator(".review-status")).to_contain_text("confirmed")
    expect(alert).to_contain_text("DATA_DEGRADED")
    expect(alert).to_contain_text("ACTIVE")
    expect(page.get_by_role("button", name=re.compile("execute|send clearance", re.I))).to_have_count(0)
    assert not any("/commands" in request or "clearance" in request.lower() for request in requests)
    screenshot("fixture-evaluator-options-boundary")


def _mount_review_editor(page: Page, ui_server: str) -> None:
    page.goto(ui_server, wait_until="networkidle")
    page.evaluate(
        """async () => {
          const componentSource = await (await fetch('/src/features/assist/ReviewEditor.tsx')).text();
          const mainSource = await (await fetch('/src/main.tsx')).text();
          const reactPath = componentSource.match(/from\\s+[\"']([^\"']*react\\.js(?:\\?[^\"']*)?)[\"']/)?.[1];
          const domPath = mainSource.match(/from\\s+[\"']([^\"']*react-dom_client\\.js(?:\\?[^\"']*)?)[\"']/)?.[1];
          if (!reactPath || !domPath) throw new Error('Could not locate Vite React runtime modules for the isolated ReviewEditor test.');
          const reactModule = await import(reactPath);
          const React = reactModule.createElement ? reactModule : reactModule.default;
          const domModule = await import(domPath);
          const createRoot = domModule.createRoot ?? domModule.default?.createRoot;
          if (!createRoot) throw new Error(`ReactDOM client exports: ${Object.keys(domModule).join(',')}; default exports: ${Object.keys(domModule.default ?? {}).join(',')}`);
          const { ReviewEditor } = await import('/src/features/assist/ReviewEditor.tsx');
          const { ApiRequestError } = await import('/src/api.ts');
          const host = document.createElement('div');
          host.id = 'qa05-review-editor-root';
          document.body.append(host);
          window.__qa05 = { calls: [], resolve: null, reject: null, refreshCalls: 0, ApiRequestError };
          function Harness() {
            const [revision, setRevision] = React.useState(4);
            const onSubmit = (decision, text, reason, requestId) => new Promise((resolve, reject) => {
              window.__qa05.calls.push({ decision, text, reason, requestId, expectedRevision: revision });
              window.__qa05.resolve = resolve;
              window.__qa05.reject = reject;
            });
            const onRefresh = async () => { window.__qa05.refreshCalls += 1; setRevision(5); };
            return React.createElement(ReviewEditor, {
              targetId: 'QA05-COMPONENT-CASE', expectedRevision: revision,
              initialText: 'Authored draft before submit.', correction: true,
              onSubmit, onRefresh,
            });
          }
          window.__qa05.root = createRoot(host);
          window.__qa05.root.render(React.createElement(Harness));
        }"""
    )
    expect(page.locator("#qa05-review-editor-root").get_by_role("textbox", name="Corrected text draft · source text stays preserved")).to_be_visible()


@pytest.mark.parametrize("outcome", ["accepted", "conflict", "unauthorized", "unavailable", "error"])
def test_review_editor_receipt_states_are_distinct(page: Page, ui_server: str, outcome: str):
    """Render the actual FE-05 ReviewEditor with explicit QA-owned delayed response stubs."""
    _mount_review_editor(page, ui_server)
    editor_root = page.locator("#qa05-review-editor-root")
    draft = editor_root.get_by_role("textbox", name="Corrected text draft · source text stays preserved")
    draft.fill("QA05 retained draft text.")
    editor_root.get_by_role("button", name="Submit correction").click()

    status = page.locator("#qa05-review-editor-root .review-status-message")
    expect(status).to_contain_text("PENDING · request")
    expect(draft).to_be_disabled()
    expect(editor_root.get_by_role("button", name="Submitting…")).to_be_disabled()
    call = page.evaluate("window.__qa05.calls.at(-1)")
    assert call["decision"] == "corrected"
    assert call["text"] == "QA05 retained draft text."
    assert call["expectedRevision"] == 4

    if outcome == "accepted":
        page.evaluate("window.__qa05.resolve({request_id: window.__qa05.calls.at(-1).requestId, revision: 5, status: 'accepted', authority: 'server', message: 'stub receipt only'})")
        expect(status).to_contain_text("ACCEPTED · SERVER RECEIPT · revision 5")
    elif outcome == "conflict":
        page.evaluate("window.__qa05.resolve({request_id: window.__qa05.calls.at(-1).requestId, revision: 5, status: 'conflict', message: 'stub stale revision'})")
        expect(status).to_contain_text("CONFLICT · stub stale revision")
        expect(status).to_contain_text("draft retained; refresh before retry")
        expect(draft).to_have_value("QA05 retained draft text.")
        expect(editor_root.get_by_role("button", name="Submit correction")).to_be_disabled()
        editor_root.get_by_role("button", name="Refresh / reconcile").click()
        expect(status).to_contain_text("refreshed; explicit retry available")
        expect(editor_root.get_by_role("button", name="Retry with revision 5")).to_be_enabled()
        expect(draft).to_have_value("QA05 retained draft text.")
        editor_root.get_by_role("button", name="Retry with revision 5").click()
        expect(status).to_contain_text("PENDING · request")
        calls = page.evaluate("window.__qa05.calls")
        assert calls[0]["requestId"] != calls[1]["requestId"], "Retry must use a fresh explicit request identity."
        page.evaluate("window.__qa05.resolve({request_id: window.__qa05.calls.at(-1).requestId, revision: 6, status: 'accepted', authority: 'server'})")
        expect(status).to_contain_text("ACCEPTED · SERVER RECEIPT · revision 6")
    elif outcome == "unauthorized":
        page.evaluate("window.__qa05.reject(new window.__qa05.ApiRequestError('unauthorized', 'source-review credential expired', 401, 'expired'))")
        expect(status).to_contain_text("UNAUTHORIZED · source-review credential expired")
    elif outcome == "unavailable":
        page.evaluate("window.__qa05.resolve({request_id: window.__qa05.calls.at(-1).requestId, revision: 4, status: 'unavailable', message: 'stub route unavailable'})")
        expect(status).to_contain_text("UNAVAILABLE · stub route unavailable")
    else:
        page.evaluate("window.__qa05.reject(new Error('stub storage failure'))")
        expect(status).to_contain_text("ERROR · stub storage failure")
