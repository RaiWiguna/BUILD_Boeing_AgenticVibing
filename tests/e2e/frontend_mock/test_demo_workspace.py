"""DEMO track journeys (ADR 0003): import with the recording made before the main one
(87.wav) → processing → saved workspace with audio; main recording only; unknown file.

Needs the demo stack (deploy/compose/local/compose.demo.yml) behind the frontend's `/api/demo`
proxy and the prepared scenario in data/demo-scenarios/ (scripts/demo/fetch_scenario.sh).
Each run stores one workspace named "E2E demo …" in the local demo database.
"""

import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from .conftest import _reachable

SCENARIO = Path(__file__).resolve().parents[3] / "data" / "demo-scenarios" / "kagc-2022-09-10-88"
AUDIO = SCENARIO / "88.wav"
ADSB = SCENARIO / "kagc_adsb_2022-09-10_88.csv"
AUDIO_87 = SCENARIO / "87.wav"
ADSB_87 = SCENARIO / "kagc_adsb_2022-09-10_87.csv"


@pytest.fixture
def demo_backend(base_url):
    if not all(p.exists() for p in (AUDIO, ADSB, AUDIO_87, ADSB_87)):
        pytest.skip("prepared scenario files missing (run scripts/demo/fetch_scenario.sh)")
    if not _reachable(f"{base_url}/api/demo/health"):
        pytest.skip("demo backend not reachable through the frontend proxy")
    return base_url


def test_demo_import_with_recording_before(login, demo_backend) -> None:
    page: Page = login(path="/sessions/import")
    name = f"E2E demo {uuid.uuid4().hex[:6]}"
    page.get_by_label("Session name").fill(name)
    # All files at once: each one lands in its recorded lane (87 before, 88 main).
    page.locator('input[type="file"][multiple]').set_input_files([str(AUDIO_87), str(ADSB_87), str(AUDIO), str(ADSB)])
    expect(page.get_by_role("region", name="Before").get_by_text("87.wav")).to_be_visible()
    expect(page.get_by_role("region", name="Before").get_by_text(ADSB_87.name)).to_be_visible()
    main = page.get_by_role("region", name="Main recording")
    expect(main.get_by_text("88.wav")).to_be_visible()
    expect(main.get_by_text(ADSB.name)).to_be_visible()
    page.get_by_role("button", name="Upload and process").click()

    expect(page.get_by_role("list", name="Processing steps").get_by_text("Speech recognition")).to_be_visible(timeout=15000)
    page.wait_for_url("**/s/*/workspace**", timeout=60000)
    expect(page.get_by_text("is ready to play")).to_be_visible()  # toast
    expect(page.get_by_text("2 recordings").first).to_be_visible()
    expect(page.get_by_role("button", name="Add recording")).to_have_count(0)
    expect(page.get_by_text("MOCK", exact=True)).to_have_count(0)

    page.get_by_role("button", name="Skip to 01:45").click()
    page.get_by_role("button", name="Play replay").click()
    transcript = page.get_by_label("Transcript so far")
    expect(transcript).to_contain_text("turn right at Bravo", timeout=12000)
    expect(page.get_by_text("Readback matches · right at B1 not read back")).to_be_visible(timeout=25000)
    page.get_by_role("button", name="Pause replay").click()
    expect(page.get_by_text("Callsign incomplete")).to_have_count(0)

    page.goto(f"{demo_backend}/sessions")
    expect(page.get_by_role("link", name=name)).to_be_visible()


def test_demo_import_main_only_plays(login, demo_backend) -> None:
    page: Page = login(path="/sessions/import")
    page.get_by_label("Session name").fill(f"E2E main {uuid.uuid4().hex[:6]}")
    page.locator('input[type="file"][multiple]').set_input_files([str(AUDIO), str(ADSB)])
    page.get_by_role("button", name="Upload and process").click()
    page.wait_for_url("**/s/*/workspace**", timeout=45000)
    page.get_by_role("button", name="Play replay").click()
    expect(page.get_by_label("Transcript so far")).to_contain_text("opposite direction", timeout=8000)
    expect(page.get_by_text("Callsign incomplete")).to_be_visible(timeout=20000)


def test_demo_import_flags_unknown_file(login, demo_backend, tmp_path) -> None:
    page: Page = login(path="/sessions/import")
    other = tmp_path / "tower.wav"
    other.write_bytes(AUDIO.read_bytes()[:4096])
    page.get_by_label("Session name").fill(f"E2E reject {uuid.uuid4().hex[:6]}")
    page.locator('input[type="file"][multiple]').set_input_files([str(other), str(ADSB)])
    expect(page.get_by_text("Not a recording of this scenario")).to_be_visible()
    expect(page.get_by_role("button", name="Upload and process")).to_be_disabled()
