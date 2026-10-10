"""Authenticated local rules/alerts/seen transport over real sources and scoped replay time."""

import pytest
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.replay.controls import Controls
from flowlens.replay.snapshots import Replay
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_rule_service import service, source

ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def wire(importer, committed, tmp_path):
    receipt, _ = source(importer, committed)
    rules, files, _ = service(committed, tmp_path)
    app = create_host(HostSettings(profile="test"))
    app.state.permissions = committed[2]
    app.state.sessions = committed[2].sessions
    app.state.transactions = importer[0].database
    app.state.rules = rules
    app.state.controls = Controls(Replay(committed[1]))
    token = committed[3].token.get_secret_value()
    app.state.controls.command(
        token,
        receipt.session_id,
        "SEEK",
        view="LOCAL",
        value=1000,
        key="rule-cursor",
        expected_version=0,
    )
    with TestClient(app, base_url=ORIGIN) as client:
        client.cookies.set("flowlens_session", token)
        yield (
            client,
            app,
            receipt.session_id,
            {"Origin": ORIGIN, "X-CSRF-Token": committed[3].csrf_token},
        )
    files.close()


def test_rest_rules_publish_seen_and_scoped_history(wire):
    client, app, sid, headers = wire
    base = f"/api/v1/sessions/{sid}"
    suffix = "?view=LOCAL&mode=AS_KNOWN"
    result = client.get(base + "/rules" + suffix)
    assert result.status_code == 200 and result.json()["as_of_ms"] == 1000
    assert result.json()["evaluation_version"] == 0
    assert result.headers["Cache-Control"] == "no-store"
    response = client.post(
        base + "/rules/evaluations" + suffix,
        json={"key": "publish", "expected_version": 0},
        headers=headers,
    )
    assert response.status_code == 200 and response.json()["version"] == 1
    assert client.get(base + "/rules" + suffix).json()["evaluation_version"] == 1
    alert = next(a for a in response.json()["alerts"] if a["status"] == "ACTIVE")
    page = client.get(base + "/alerts" + suffix + "&limit=1")
    assert page.status_code == 200 and len(page.json()["items"]) == 1
    history = client.get(base + f"/alerts/{alert['id']}/history" + suffix)
    assert history.status_code == 200 and history.json()["items"][-1]["status"] == "ACTIVE"
    seen = client.post(
        base + f"/alerts/{alert['id']}/seen" + suffix,
        json={"key": "seen", "expected_version": 1},
        headers=headers,
    )
    assert seen.status_code == 200 and seen.json()["meaning"] == "SEEN_ONLY"
    assert client.get(base + "/indicators" + suffix).json()["label"] == "EXPERIMENTAL_NOT_WORKLOAD"
    assert str(app.state.rules.sources.files.root) not in response.text


def test_strict_body_csrf_and_current_access_loss(wire, committed):
    client, app, sid, headers = wire
    url = f"/api/v1/sessions/{sid}/rules/evaluations?view=LOCAL"
    assert client.post(url, json={"key": "missing-csrf", "expected_version": 0}).status_code == 403
    assert (
        client.post(url, json={"key": "x", "expected_version": True}, headers=headers).status_code
        == 422
    )
    assert (
        client.post(
            url, json={"key": "x", "expected_version": 0, "as_of_ms": 99999}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, content='{"key":"x","key":"other","expected_version":0}', headers=headers
        ).status_code
        == 422
    )
    assert client.post(url, content="x" * 4097, headers=headers).status_code == 413
    committed[2].revoke(committed[3].token.get_secret_value(), committed[3].account.id, sid, "read")
    assert client.get(f"/api/v1/sessions/{sid}/rules?view=LOCAL").status_code == 403
    assert (
        client.post(
            url, json={"key": "revoked", "expected_version": 0}, headers=headers
        ).status_code
        == 403
    )


def test_host_composes_and_cleans_rules_service(tmp_path):
    settings = HostSettings(
        profile="test",
        database_path=tmp_path / "db" / "data.db",
        import_staging_path=tmp_path / "imports",
        raw_assets_path=tmp_path / "raw",
        artifact_staging_path=tmp_path / "derived",
    )
    app = create_host(settings)
    with TestClient(app):
        assert app.state.rules is not None and app.state.rules.sources is app.state.sources
    assert app.state.rules is None and app.state.geometry is None
