"""QA-05 native Playwright lifecycle and run artifacts.

The fixture server serves only the checked-in FE-05 authored fixture. The API
server, when requested, is a fresh local instance of the actual backend source
with a temporary SQLite database and a throwaway test operator key.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
VITE_ENTRY = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts"
TEST_OPERATOR_KEY = "qa05-local-throwaway-key"
_SERVER_PROCESSES: dict[str, tuple[subprocess.Popen[str], Any]] = {}
_SCREENSHOTS: list[str] = []
_REPORTS: list[dict[str, Any]] = []
_RUN_ID = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y%m%dT%H%M%S%f%z")
_RUN_DIR = ARTIFACT_ROOT / f"run-{_RUN_ID}"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "qa05_mode(name): source mode exercised by this browser test")


def pytest_sessionstart(session: pytest.Session) -> None:
    _RUN_DIR.mkdir(parents=True, exist_ok=True)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when != "call":
        return
    marker = report.nodeid.split("::", 1)[0]
    _REPORTS.append(
        {
            "test": report.nodeid,
            "outcome": report.outcome,
            "duration_s": round(report.duration, 3),
            "suite_file": Path(marker).name,
            **({"expected_failure": str(report.wasxfail)} if getattr(report, "wasxfail", None) else {}),
        }
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    try:
        playwright_version = version("playwright")
    except PackageNotFoundError:
        playwright_version = "unavailable"
    try:
        pytest_version = version("pytest")
    except PackageNotFoundError:
        pytest_version = "unavailable"
    manifest = {
        "task": "QA-05",
        "label": "actual native browser run; screenshot verifies UI rendering only, not domain correctness",
        "run_id": _RUN_ID,
        "client_date": "2026-10-06",
        "timezone": "Asia/Jakarta",
        "command": os.environ.get("QA05_COMMAND") or "python -m pytest " + " ".join(sys.argv[1:]),
        "exit_status": exitstatus,
        "environment": {
            "python": sys.version.split()[0],
            "playwright": playwright_version,
            "pytest": pytest_version,
            "browser": "Playwright Chromium (headless)",
            "fixture_profile": "FE-05 authored inline fixture-1; no ASR/provider/partner/server result",
            "qa01_canonical_fixture_bundle": "not present; F-COMM-01 used only as a documented target name",
            "qa04_mock_stack_launcher": "not present; QA-05 launches isolated Vite/backend processes only for its own tests",
        },
        "screenshots": sorted(set(_SCREENSHOTS)),
        "tests": _REPORTS,
        "summary": {
            "passed": sum(item["outcome"] == "passed" for item in _REPORTS),
            "failed": sum(item["outcome"] == "failed" for item in _REPORTS),
            "skipped": sum(item["outcome"] == "skipped" for item in _REPORTS),
            "expected_failures": sum("expected_failure" in item for item in _REPORTS),
        },
    }
    (_RUN_DIR / "result-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def pytest_unconfigure(config: pytest.Config) -> None:
    for process, log in reversed(list(_SERVER_PROCESSES.values())):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        log.close()
    _SERVER_PROCESSES.clear()


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


def _wait_for_url(url: str, process: subprocess.Popen[str], log_path: Path) -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            details = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            raise RuntimeError(f"QA-05 server exited before becoming ready ({url}).\n{details}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError):
            time.sleep(0.2)
    details = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    raise RuntimeError(f"QA-05 server did not become ready ({url}).\n{details}")


def _start_vite(name: str, mode: str, view: str | None = None) -> str:
    if name in _SERVER_PROCESSES:
        process, _ = _SERVER_PROCESSES[name]
        if process.poll() is not None:
            raise RuntimeError(f"QA-05 Vite process {name} exited unexpectedly.")
        return _SERVER_URLS[name]
    node = shutil.which("node")
    if not node or not VITE_ENTRY.exists():
        pytest.skip("Node/Vite runtime is unavailable for native browser replay.")
    port = _available_port()
    url = f"http://127.0.0.1:{port}"
    log = tempfile.NamedTemporaryFile(prefix=f"qa05-{name}-", suffix=".log", delete=False, mode="w+", encoding="utf-8")
    env = os.environ.copy()
    env["VITE_FLOWLENS_MODE"] = mode
    env.pop("VITE_FLOWLENS_FIXTURE_VIEW", None)
    if view:
        env["VITE_FLOWLENS_FIXTURE_VIEW"] = view
    process = subprocess.Popen(
        [node, str(VITE_ENTRY), "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=FRONTEND_DIR,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _SERVER_PROCESSES[name] = (process, log)
    _SERVER_URLS[name] = url
    _wait_for_url(url, process, Path(log.name))
    return url


_SERVER_URLS: dict[str, str] = {}


def _start_actual_backend(tmp_path_factory: pytest.TempPathFactory) -> str:
    name = "actual-backend"
    if name in _SERVER_PROCESSES:
        process, _ = _SERVER_PROCESSES[name]
        if process.poll() is not None:
            raise RuntimeError("QA-05 actual backend process exited unexpectedly.")
        return _SERVER_URLS[name]
    port = 8000  # frontend/vite.config.ts has the current API proxy fixed at this port.
    if not _port_is_free(port):
        pytest.skip("Port 8000 is occupied; QA-05 will not attach to an unrelated API process.")
    db_path = tmp_path_factory.mktemp("qa05-api") / "flowlens.sqlite3"
    backend_url = f"http://127.0.0.1:{port}"
    py_code = (
        "from backend.app import create_app; import uvicorn; "
        f"app=create_app(db_path={str(db_path)!r}, operator_key={TEST_OPERATOR_KEY!r}, run_clock=False); "
        "uvicorn.run(app, host='127.0.0.1', port=8000, log_level='error')"
    )
    log = tempfile.NamedTemporaryFile(prefix="qa05-backend-", suffix=".log", delete=False, mode="w+", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    process = subprocess.Popen(
        [sys.executable, "-c", py_code], cwd=REPO_ROOT, env=env,
        stdout=log, stderr=subprocess.STDOUT, text=True,
    )
    _SERVER_PROCESSES[name] = (process, log)
    _SERVER_URLS[name] = backend_url
    _wait_for_url(backend_url + "/health", process, Path(log.name))
    return backend_url


@pytest.fixture(scope="session")
def playwright_engine() -> Playwright:
    with sync_playwright() as engine:
        yield engine


@pytest.fixture(scope="session")
def browser(playwright_engine: Playwright) -> Browser:
    try:
        instance = playwright_engine.chromium.launch(headless=True)
    except Exception as error:
        pytest.skip(f"Native Playwright Chromium could not start: {error}")
    yield instance
    instance.close()


@pytest.fixture
def page(browser: Browser) -> Page:
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    current = context.new_page()
    yield current
    context.close()


@pytest.fixture
def ui_server(request: pytest.FixtureRequest) -> str:
    marker = request.node.get_closest_marker("qa05_mode")
    mode = marker.args[0] if marker and marker.args else "fixture"
    if mode == "fixture":
        return _start_vite("fixture-evaluator", "fixture", "evaluator")
    if mode == "training":
        return _start_vite("fixture-training", "fixture", "training")
    if mode == "api":
        return _start_vite("local-api-ui", "api")
    raise ValueError(f"Unknown QA-05 UI mode: {mode}")


@pytest.fixture
def actual_backend(tmp_path_factory: pytest.TempPathFactory) -> str:
    return _start_actual_backend(tmp_path_factory)


@pytest.fixture
def browser_diagnostics(page: Page) -> dict[str, list[str]]:
    diagnostics = {"console_errors": [], "page_errors": [], "failed_requests": [], "http_5xx": []}
    page.on("console", lambda message: diagnostics["console_errors"].append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: diagnostics["page_errors"].append(str(error)))
    page.on("requestfailed", lambda request: diagnostics["failed_requests"].append(f"{request.method} {request.url}: {request.failure}"))
    page.on("response", lambda response: diagnostics["http_5xx"].append(f"{response.status} {response.url}") if response.status >= 500 else None)
    return diagnostics


@pytest.fixture
def screenshot(page: Page):
    def capture(name: str, *, full_page: bool = True) -> str:
        path = _RUN_DIR / f"{name}.png"
        page.screenshot(path=str(path), full_page=full_page, animations="disabled")
        relative = path.relative_to(Path(__file__).resolve().parents[2]).as_posix()
        _SCREENSHOTS.append(relative)
        return relative

    return capture


def qa05_run_directory() -> Path:
    return _RUN_DIR
