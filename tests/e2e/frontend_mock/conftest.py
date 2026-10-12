"""MOCK frontend journeys (Python Playwright) against `vite preview` / `vite dev`.

Opt-in: requires `pytest-playwright` (`uv add --dev pytest-playwright`) and a running
frontend at FLOWLENS_FRONTEND_URL (default http://localhost:4173). Skips otherwise.
Results are reported as MOCK journeys, separate from the backend gate.
"""

import os
import urllib.parse
import urllib.request

import pytest

pytest.importorskip("playwright.sync_api", reason="pytest-playwright not installed")

BASE_URL = os.environ.get("FLOWLENS_FRONTEND_URL", "http://localhost:4173").rstrip("/")
# Deterministic MOCK ids (hash of the seed key), see frontend/src/api/adapters/mock/ids.ts.
S1 = "36f6320a-58a3-44dd-8663-6f3b6bbefa23"  # Runway 27 · Readback
S_HOLD_SHORT = "1e27daf2-973a-4acf-80b4-75bb3ad8e715"  # Hold short · Vehicle
S_REPORT_CLEAR = "1e57f034-9588-4ee1-889c-7121282504cb"  # Report clear · Coverage gap
S_AUDIO_ONLY = "bb00c92f-9336-42a6-80f5-7d0cae62f442"  # Audio-only · Tower
DEMO_PASSWORD = "flowlens-demo"


def _reachable(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:  # noqa: S310 - local dev host only
            return r.status < 500
    except OSError:
        return False


@pytest.fixture(autouse=True)
def track_registration():
    """Override the backend harness fixture: these journeys only drive the MOCK frontend."""
    yield None


@pytest.fixture(scope="session")
def base_url() -> str:
    if not BASE_URL.startswith(("http://localhost", "http://127.0.0.1")):
        pytest.skip("MOCK journeys only run against a local dev host")
    if not _reachable(BASE_URL):
        pytest.skip(f"frontend not running at {BASE_URL}")
    return BASE_URL


@pytest.fixture
def login(page, base_url):
    def _login(email: str = "evaluator@flowlens.test", path: str = "/sessions"):
        page.goto(f"{base_url}/login?next={urllib.parse.quote(path, safe='/')}")
        page.get_by_label("Email").fill(email)
        page.get_by_label("Password", exact=True).fill(DEMO_PASSWORD)
        page.get_by_role("button", name="Sign in").click()
        # `/login?next=/sessions` also matches a glob on the target path; wait for the redirect itself.
        page.wait_for_url(lambda url: "/login" not in url)
        return page

    return _login


@pytest.fixture
def mock_flag(page):
    """Toggle a Mock control scenario switch. Flags live in memory: a full page load resets them."""

    # Developer controls are hidden unless enabled for the browser (routes.tsx).
    page.add_init_script("localStorage.setItem('flowlens.devtools', '1')")

    def _toggle(label: str):
        page.get_by_role("button", name="Open mock control").click()
        page.get_by_role("dialog", name="Mock control").get_by_role("switch", name=label).click()
        page.get_by_role("button", name="Close mock control").click()

    return _toggle
