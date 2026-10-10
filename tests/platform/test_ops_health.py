"""Local readiness probes actual SQLite/private roots; cloud gates stay independent."""

import importlib
from types import SimpleNamespace

from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.replay.controls import Controls
from flowlens.replay.snapshots import Replay
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_jobs import configured
from test_retention import coordinator


def ops(media, committed, importer, tmp_path):
    jobs, policy = configured(media, committed, importer)
    r, j = coordinator(media, committed, tmp_path)
    state = SimpleNamespace(
        transactions=importer[0].database,
        imports=importer[0],
        raw_files=media[0].sources.files,
        artifact_files=media[0].artifacts,
        tombstones=j,
        retention=r,
        jobs=jobs,
        controls=Controls(Replay(committed[1])),
    )
    cls = importlib.import_module("flowlens.ops.health").Operations
    return cls(state, HostSettings(profile="test"), PLATFORM_MIGRATIONS, profile="MOCK"), j


def test_local_dependencies_real_probe_and_provider_not_a_restart_trigger(
    media, committed, importer, tmp_path
):
    service, journal = ops(media, committed, importer, tmp_path)
    try:
        report = service.ready()
        assert report["ready"] is True and report["scope"] == "LOCAL_PLATFORM"
        assert report["integration_gate"] == "NOT_STARTED"
        assert report["provider_verified"] is False
        assert set(report["dependencies"].values()) == {"READY"}
        assert str(importer[0].database.path) not in str(report)
        with importer[0].database.begin() as uow:
            assert uow.connection.execute("SELECT value FROM platform_ops_probe").fetchone()[0] == 0
    finally:
        journal.close()


def test_disk_full_and_write_failure_have_bounded_status(media, committed, importer, tmp_path):
    service, journal = ops(media, committed, importer, tmp_path)
    try:
        service.free_bytes = lambda fd: 0
        report = service.ready()
        assert report["ready"] is False and "DISK_LOW" in report["dependencies"].values()
        assert (
            service.disk(committed[3].token.get_secret_value())["roots"]["raw"]["free_bytes"] == 0
        )
    finally:
        journal.close()


def test_unconfigured_default_stays_unready_with_dependency_details():
    from fastapi.testclient import TestClient

    with TestClient(create_host(HostSettings(profile="test"))) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["dependencies"]["database"] == "NOT_CONFIGURED"
        assert client.get("/release.json").json()["domain_validation"] == "NOT_DOMAIN_VALIDATED"


def test_corrupt_journal_is_an_actual_dependency(media, committed, importer, tmp_path):
    service, journal = ops(media, committed, importer, tmp_path)
    try:
        (journal.files.root / "head.json").write_bytes(b"invalid synthetic journal")
        response = service.ready()
        assert response["dependencies"]["tombstones"] == "UNAVAILABLE"
        assert response["ready"] is False
    finally:
        journal.close()


def test_storage_write_failure_is_unavailable_and_does_not_expose_error(
    media, committed, importer, tmp_path, monkeypatch
):
    service, journal = ops(media, committed, importer, tmp_path)
    import flowlens.ops.health as health

    def failed(fd, body):
        raise OSError("private-path raw transcript secret-key")

    monkeypatch.setattr(health.os, "write", failed)
    try:
        report = service.ready()
        assert report["ready"] is False
        assert report["dependencies"]["raw"] == "UNAVAILABLE"
        assert "secret-key" not in str(report) and "private-path" not in str(report)
    finally:
        journal.close()


def test_complete_host_local_ready_with_fake_provider_outage_and_safe_release(
    media, committed, importer, tmp_path
):
    from fastapi.testclient import TestClient
    from flowlens.ops.providers import AdapterBinding
    from test_jobs import FakeAnalysis, TranscriptRepository, configured
    from test_ops_profiles import FakeAdapter, profile

    _, policy = configured(media, committed, importer)
    settings = HostSettings(
        profile="test",
        database_path=tmp_path / "fresh" / "data.db",
        import_staging_path=tmp_path / "fresh-imports",
        raw_assets_path=tmp_path / "fresh-raw",
        artifact_staging_path=tmp_path / "fresh-artifacts",
        retention_journal_path=tmp_path / "fresh-journal",
        release_sha="a" * 40,
        lock_sha256="b" * 64,
    )

    class Unavailable(FakeAdapter):
        def check(self, value):
            return value.model_copy(update={"readiness": "UNAVAILABLE"})

    app = create_host(
        settings,
        analysis_module=FakeAnalysis(),
        job_policies=[policy],
        repository_factories={"analysis.transcripts": TranscriptRepository},
        provider_adapters={"GEMINI": AdapterBinding(Unavailable(), True)},
    )
    with TestClient(app) as client:
        from pydantic import SecretStr

        admin = app.state.accounts.bootstrap("admin", SecretStr("synthetic-health-initial"))
        app.state.accounts.change_password(
            admin.id, SecretStr("synthetic-health-initial"), SecretStr("synthetic-health-changed")
        )
        token = app.state.sessions.login(
            "admin", SecretStr("synthetic-health-changed"), "local"
        ).token.get_secret_value()
        p = profile()
        app.state.providers.save(token, p, expected_version=0, key="create")
        result = app.state.providers.check(token, p.id, expected_version=1, key="check")
        assert result.profile.readiness == "UNAVAILABLE" and result.verification == "MOCK"
        response = client.get("/ready")
        assert response.status_code == 200 and response.json()["profile"] == "MOCK"
        assert response.json()["provider_verified"] is False
        release = client.get("/release.json")
        assert (
            release.json()["source_sha"] == "a" * 40 and release.json()["lock_sha256"] == "b" * 64
        )
        assert "platform.0017" in release.json()["schema_versions"]
        assert str(tmp_path) not in release.text
    assert app.state.providers is None and app.state.usage is None
