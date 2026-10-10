"""A09.1 real transport over frozen fake export and disposable private storage."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.replay.controls import Controls
from flowlens.replay.snapshots import Replay
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_report_artifacts import exporting, lifecycle, result, spec
from test_report_artifacts import media as media
from test_retention import coordinator

ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def wire(media, committed, importer, tmp_path):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    payload = b'<html><script>alert("SYNTHETIC")</script></html>'
    artifact = spec(wc, payload, "HTML_REPORT")
    media[0].submit(wc, artifact, iter([payload]))
    client.result(result(lease, artifact))
    retention, journal = coordinator(media, committed, tmp_path, imports=importer[0])
    app = create_host(HostSettings(profile="test"))
    app.state.permissions = committed[2]
    app.state.sessions = committed[2].sessions
    app.state.artifacts = lifecycle(media)
    app.state.retention = retention
    app.state.controls = Controls(Replay(committed[1]))
    with TestClient(app, base_url=ORIGIN) as browser:
        browser.cookies.set("flowlens_session", committed[3].token.get_secret_value())
        yield (
            browser,
            app,
            wc.session_id,
            run.id,
            artifact.id,
            payload,
            {
                "Origin": ORIGIN,
                "X-CSRF-Token": committed[3].csrf_token,
            },
        )
    journal.close()


def test_accepted_report_attachment_headers_inventory_and_scope(wire):
    client, app, sid, run, aid, payload, headers = wire
    url = f"/api/v1/sessions/{sid}/artifacts/{aid}/download?run_id={run}"
    response = client.get(url)
    assert response.status_code == 200 and response.content == payload
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["content-security-policy"] == "sandbox; default-src 'none'"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert client.head(url).status_code == 200
    inventory = client.get(f"/api/v1/sessions/{sid}/artifacts?run_id={run}")
    assert inventory.status_code == 200 and inventory.json()[0]["id"] == str(aid)
    assert str(app.state.artifacts.assets.artifacts.root) not in inventory.text
    assert client.get(url.replace(str(sid), str(uuid4()))).status_code in (403, 422)
    assert client.get(url.replace(str(run), str(uuid4()))).status_code in (403, 422)


def test_admin_preview_purge_csrf_strict_body_and_audit(wire):
    client, app, sid, run, aid, payload, headers = wire
    base = f"/api/v1/admin/sessions/{sid}"
    preview = client.get(base + "/purge-preview")
    assert preview.status_code == 200
    value = {
        "key": "purge",
        "reason": "USER_REQUEST",
        "expected_inventory_hash": preview.json()["inventory_hash"],
    }
    assert client.post(base + "/purge", json=value).status_code == 403
    assert (
        client.post(
            base + "/purge", json=value | {"contents": "untrusted"}, headers=headers
        ).status_code
        == 422
    )
    assert client.post(base + "/purge", content="x" * 4097, headers=headers).status_code == 413
    done = client.post(base + "/purge", json=value, headers=headers)
    assert done.status_code == 200 and done.json()["state"] == "DONE"
    audit = client.get(base + "/audit")
    assert audit.status_code == 200 and [r["action"] for r in audit.json()["items"]] == [
        "PURGE_COMPLETED"
    ]
    assert "SYNTHETIC" not in audit.text
    assert client.get(f"/api/v1/sessions/{sid}/artifacts?run_id={run}").status_code == 403


def test_host_composes_retention_separate_journal_and_closes(tmp_path):
    settings = HostSettings(
        profile="test",
        database_path=tmp_path / "db" / "data.db",
        import_staging_path=tmp_path / "imports",
        raw_assets_path=tmp_path / "raw",
        artifact_staging_path=tmp_path / "reports",
        retention_journal_path=tmp_path / "journal",
    )
    app = create_host(settings)
    with TestClient(app):
        assert app.state.retention is not None and app.state.artifacts is not None
        assert app.state.retention.recover() == []
    assert app.state.retention is None and app.state.tombstones is None
    with TestClient(app):
        assert app.state.retention.recover() == []
    with pytest.raises(ValueError):
        HostSettings.model_validate(
            settings.model_dump() | {"retention_journal_path": tmp_path / "db" / "journal"}
        )
