"""Real HTTP validates admin/CSRF and emits bounded safe operational metadata."""

import json
import logging

import pytest
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.ops.providers import AdapterBinding, Providers
from flowlens.ops.usage import UsageReader
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_ops_health import ops
from test_ops_profiles import FakeAdapter, profile

ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def wire(media, committed, importer, tmp_path):
    health, journal = ops(media, committed, importer, tmp_path)
    app = create_host(HostSettings(profile="test"))
    app.state.permissions = committed[2]
    app.state.sessions = committed[2].sessions
    app.state.providers = Providers(
        importer[0].database,
        importer[0].sessions,
        adapters={"GEMINI": AdapterBinding(FakeAdapter(), True)},
        allow_mock=True,
    )
    app.state.usage = UsageReader(committed[2])
    app.state.controls = health.state.controls
    app.state.ops = health
    with TestClient(app, base_url=ORIGIN) as client:
        client.cookies.set("flowlens_session", committed[3].token.get_secret_value())
        yield client, app, {"Origin": ORIGIN, "X-CSRF-Token": committed[3].csrf_token}
    journal.close()


def test_profiles_checks_strict_body_csrf_and_safe_audit(wire):
    client, app, headers = wire
    value = {"profile": profile().model_dump(mode="json"), "expected_version": 0, "key": "create"}
    url = "/api/v1/admin/provider-profiles"
    assert client.post(url, json=value).status_code == 403
    response = client.post(url, json=value, headers=headers)
    assert response.status_code == 200 and response.json()["revision"] == 1
    pid = response.json()["profile"]["id"]
    check = client.post(
        url + f"/{pid}/checks", json={"key": "check", "expected_version": 1}, headers=headers
    )
    assert check.status_code == 200 and check.json()["verification"] == "MOCK"
    assert check.json()["provider_verified"] is False
    assert client.get(url).json()[0]["verification"] == "MOCK"
    assert (
        client.post(url, json=value | {"secret": "untrusted"}, headers=headers).status_code == 422
    )
    assert client.post(url, content="x" * 16385, headers=headers).status_code == 413
    assert client.post(url, content='{"key":"a","key":"b"}', headers=headers).status_code == 422
    audit = client.get("/api/v1/admin/ops-audit?limit=1")
    assert audit.status_code == 200 and audit.json()["next_cursor"] is not None
    assert client.get("/api/v1/admin/disk").status_code == 200
    assert client.get("/api/v1/admin/usage").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/ready").json()["integration_gate"] == "NOT_STARTED"
    assert response.headers["cache-control"] == "no-store"


def test_log_http_omits_body_query_token_and_exception_text(wire, caplog):
    client, app, headers = wire
    with caplog.at_level(logging.INFO, logger="flowlens.ops"):
        client.post(
            "/api/v1/admin/provider-profiles?note=private-query",
            content="private-body",
            headers=headers,
        )
    assert caplog.records
    records = [json.loads(r.message) for r in caplog.records if r.name == "flowlens.ops"]
    assert records[-1]["event"] == "HTTP_REQUEST"
    assert "private-query" not in caplog.text and "private-body" not in caplog.text
    assert "flowlens_session" not in caplog.text


def test_non_admin_cannot_read_or_mutate_operations(wire, importer, committed):
    client, app, headers = wire
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_accounts SET is_admin=0 WHERE id=?", (str(committed[3].account.id),)
        )
        uow.commit()
    for path in ("provider-profiles", "ops-audit", "usage", "disk"):
        assert client.get("/api/v1/admin/" + path).status_code == 403
    value = {"profile": profile().model_dump(mode="json"), "expected_version": 0, "key": "denied"}
    assert (
        client.post("/api/v1/admin/provider-profiles", json=value, headers=headers).status_code
        == 403
    )
    assert client.get("/ready").status_code == 200


def test_provider_outage_keeps_actual_cached_snapshot_available(wire, media):
    from test_ops_profiles import FakeAdapter

    client, app, headers = wire

    class Unavailable(FakeAdapter):
        def check(self, p):
            return p.model_copy(update={"readiness": "UNAVAILABLE"})

    app.state.providers.adapters["GEMINI"] = AdapterBinding(Unavailable(), True)
    p = profile()
    client.post(
        "/api/v1/admin/provider-profiles",
        json={"profile": p.model_dump(mode="json"), "expected_version": 0, "key": "outage-config"},
        headers=headers,
    ).raise_for_status()
    result = client.post(
        f"/api/v1/admin/provider-profiles/{p.id}/checks",
        json={"expected_version": 1, "key": "outage-check"},
        headers=headers,
    )
    assert result.status_code == 200 and result.json()["profile"]["readiness"] == "UNAVAILABLE"
    assert client.get("/ready").status_code == 200
    response = client.get(f"/api/v1/sessions/{media[2].session_id}/snapshot")
    assert response.status_code == 200 and response.json()["session_id"] == str(media[2].session_id)
