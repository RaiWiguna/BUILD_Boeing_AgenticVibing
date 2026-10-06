from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize("scenario", ["duplicate", "gap", "outage"])
def test_assist_stream_duplicate_gap_and_transport_reconnect(
    page: Page, qa04_mock_stack, scenario: str,
):
    """Run the FE adapter in Chromium against QA-04's public synthetic mock stream."""
    page.goto(qa04_mock_stack.web_url, wait_until="networkidle")
    page.evaluate(
        """async ({scenario, token, sourceId}) => {
          const { ApiReplayReviewAdapter } = await import('/src/adapters/apiReplayReview.ts');
          const state = window.__qa05 = { updates: [], states: [], openCount: 0, cleanup: null };
          const nativeFetch = window.fetch.bind(window);
          let firstSocket = true;
          const transport = {
            request: (input, init) => nativeFetch(input, init),
            openWebSocket: (url) => {
              state.openCount += 1;
              if (scenario === 'outage' && firstSocket) {
                firstSocket = false;
                const failed = { readyState: 0, onopen: null, onmessage: null, onerror: null, onclose: null,
                  send() {}, close() { this.readyState = 3; } };
                setTimeout(() => {
                  failed.readyState = 1;
                  failed.onopen?.(new Event('open'));
                  setTimeout(() => {
                    failed.readyState = 3;
                    failed.onclose?.({ code: 1006, reason: 'QA-only synthetic transport outage' });
                  }, 10);
                }, 0);
                return failed;
              }
              const target = new URL(url, location.href);
              if (scenario === 'duplicate') target.searchParams.set('variant', 'duplicate-assist-sequence');
              if (scenario === 'gap') target.searchParams.set('variant', 'assist-sequence-gap');
              return new WebSocket(target.toString());
            },
          };
          const adapter = new ApiReplayReviewAdapter({
            transport,
            scope: { source_session_id: sourceId },
            replay_assist_profile: true,
            reconnect_min_ms: 100,
            reconnect_max_ms: 100,
            credentials: { reviewer: { token } },
          });
          state.cleanup = adapter.subscribeAssist(
            sourceId,
            (update) => state.updates.push(update.type),
            (connection, message) => state.states.push({ connection, message: message ?? '' }),
          );
        }""",
        {
            "scenario": scenario,
            "token": qa04_mock_stack.credentials.operator_token,
            "sourceId": "SYN-COMM-01",
        },
    )

    if scenario == "duplicate":
        page.wait_for_function("window.__qa05.updates.includes('snapshot')", timeout=8_000)
        page.wait_for_timeout(250)
        result = page.evaluate("(({updates, states, openCount}) => ({updates, states, openCount}))(window.__qa05)")
        assert result["updates"].count("snapshot") == 1
        assert "candidate" not in result["updates"], "Duplicate sequence 1 option deltas must be ignored."
        assert result["openCount"] == 1
        assert result["states"][-1]["connection"] == "connected"
    elif scenario == "gap":
        page.wait_for_function(
            "window.__qa05.states.some(item => item.message.includes('Assist sequence gap')) && window.__qa05.openCount >= 2",
            timeout=8_000,
        )
        result = page.evaluate("(({updates, states, openCount}) => ({updates, states, openCount}))(window.__qa05)")
        assert result["updates"].count("snapshot") >= 2, "A gap must reconnect and accept a new full snapshot."
        assert "candidate" not in result["updates"], "The missing sequence delta must not be merged."
    else:
        page.wait_for_function(
            "window.__qa05.states.some(item => item.message.includes('QA-only synthetic transport outage')) && window.__qa05.updates.includes('snapshot') && window.__qa05.openCount >= 2",
            timeout=8_000,
        )
        result = page.evaluate("(({updates, states, openCount}) => ({updates, states, openCount}))(window.__qa05)")
        assert result["updates"].count("snapshot") == 1
        assert result["states"][-1]["connection"] == "connected"

    page.evaluate("window.__qa05.cleanup()")


def test_source_stream_retains_last_frame_during_outage_then_accepts_reconnect_snapshot(
    page: Page, qa04_mock_stack,
):
    """Verify frozen last-frame behavior and that a reconnect snapshot restores connected state."""
    page.goto(qa04_mock_stack.web_url, wait_until="networkidle")
    page.evaluate(
        """async ({token, sourceId}) => {
          const { ApiReplayReviewAdapter } = await import('/src/adapters/apiReplayReview.ts');
          const state = window.__qa05 = { frames: [], states: [], openCount: 0, cleanup: null };
          const transport = {
            request: (input, init) => fetch(input, init),
            openWebSocket: (url) => {
              const attempt = ++state.openCount;
              const socket = new WebSocket(url);
              let outageInjected = false;
              const bridge = {
                get readyState() { return socket.readyState; },
                onopen: null, onmessage: null, onerror: null, onclose: null,
                send: (data) => socket.send(data),
                close: (code, reason) => socket.close(code, reason),
              };
              socket.onopen = (event) => bridge.onopen?.(event);
              socket.onmessage = (event) => {
                bridge.onmessage?.(event);
                if (attempt === 1 && !outageInjected) {
                  outageInjected = true;
                  setTimeout(() => socket.close(4001, 'QA-only source outage'), 10);
                }
              };
              socket.onerror = (event) => bridge.onerror?.(event);
              socket.onclose = (event) => bridge.onclose?.(event);
              return bridge;
            },
          };
          const adapter = new ApiReplayReviewAdapter({
            transport,
            scope: { source_session_id: sourceId },
            reconnect_min_ms: 100,
            reconnect_max_ms: 100,
            credentials: { source_read: { token } },
          });
          state.cleanup = adapter.subscribeSource(
            sourceId,
            (frame) => state.frames.push(frame ? {
              frame_ms: frame.frame_ms,
              connection_message: frame.connection_message ?? '',
            } : null),
            (connection, message) => state.states.push({ connection, message: message ?? '' }),
          );
        }""",
        {
            "token": qa04_mock_stack.credentials.source_read_token,
            "sourceId": "SYN-COMM-01",
        },
    )
    page.wait_for_function(
        "window.__qa05.openCount >= 2 && window.__qa05.states.some(item => item.message.includes('QA-only source outage'))",
        timeout=8_000,
    )
    page.wait_for_timeout(250)
    result = page.evaluate("(({frames, states, openCount}) => ({frames, states, openCount}))(window.__qa05)")
    assert result["frames"][0]["frame_ms"] <= 74600
    assert any("QA-only source outage" in frame["connection_message"] for frame in result["frames"] if frame)
    assert result["states"][-1]["connection"] == "connected", (
        "The full reconnect snapshot must clear the disconnected label even when its sequence duplicates the last frame."
    )
    page.evaluate("window.__qa05.cleanup()")
