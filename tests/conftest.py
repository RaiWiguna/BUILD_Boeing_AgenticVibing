"""Same contract suite, selectable standalone track; no A/B business dependency."""

import pytest


def pytest_addoption(parser):
    parser.addoption("--track", choices=("A", "B"), default="A")


@pytest.fixture(autouse=True)
def track_registration(request, tmp_path):
    from flowlens.testing.harness import build_harness

    bundle = build_harness(request.config.getoption("--track"), db_path=tmp_path / "contract.db")
    assert bundle.profile == "MOCK"
    yield bundle
