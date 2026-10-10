"""Actual A/B composition, disposable SQL and deferred providers."""

import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from flowlens.contracts.models import RequestContext
from flowlens.core.host_config import HostSettings
from flowlens.storage.sqlite.database import AuthorizedRepository
from test_import_commit import committed as committed
from test_imports import importer as importer


@pytest.fixture
def media(importer, committed, tmp_path):
    from pathlib import Path

    from flowlens.assets.access import Assets
    from flowlens.assets.storage import PrivateFiles
    from flowlens.evidence.registry import EvidenceRegistry
    from test_import_commit import commit, context
    from test_import_metadata import prepare, request
    from test_imports import stage, upload

    preview = stage(
        importer,
        [
            upload(),
            upload(
                Path("tests/fixtures/events/availability.json").read_bytes(),
                role="events",
                filename="events.json",
                media_type="application/json",
            ),
        ],
    )

    def declaration(data):
        data["rights"]["export"] = "ALLOWED"
        for item in data["files"]:
            item["clock"] = {
                "timezone": "UTC",
                "method": "DECLARED_OFFSET",
                "offset_ms": 0,
                "uncertainty_ms": 10,
                "basis": "synthetic calibration",
                "reviewer": "fixture",
            }

    prepared = prepare(importer, preview, request(preview, modify=declaration))
    receipt = commit(committed, preview, prepared)
    files = PrivateFiles(tmp_path / "derivatives")
    assets = Assets(committed[1], files)
    try:
        yield (
            assets,
            EvidenceRegistry(committed[1], assets),
            context(committed, receipt),
            receipt,
            prepared,
        )
    finally:
        files.close()


def settings(tmp_path, profile="test"):
    return HostSettings(
        profile=profile,
        database_path=tmp_path / "db/state.sqlite",
        import_staging_path=tmp_path / "imports",
        raw_assets_path=tmp_path / "raw",
        artifact_staging_path=tmp_path / "artifacts",
        retention_journal_path=tmp_path / "journal",
    )


def test_composition_installs_real_b_schema_and_deferred_provider_status(tmp_path):
    from flowlens.integration import create_integrated_host

    app = create_integrated_host(settings(tmp_path))
    with TestClient(app) as client:
        with app.state.transactions.begin() as uow:
            names = {r[0] for r in uow.connection.execute("SELECT name FROM sqlite_master")}
            assert {
                "analysis_configurations",
                "analysis_transcript_raw",
                "analysis_memory_ledger",
                "analysis_advisory_ledger",
            } <= names
        assert app.state.jobs is not None
        assert app.state.jobs.policies["AUDIO"].ready()
        assert app.state.replay.snapshot_reader is not None
        assert client.get("/api/v1/integration-status").status_code == 401
        assert all(not m.mock for m in app.state.registry.modules)
        assert app.state.integration.status()["provider_verified"] is False
    with sqlite3.connect(tmp_path / "db/state.sqlite") as conn:
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_guarded_b_repository_extensions_preserve_authorization():
    calls = []
    ctx = RequestContext(
        actor_id=uuid4(),
        capabilities=["read"],
        session_id=uuid4(),
        analysis_run_id=uuid4(),
        input_revision=1,
        input_hash="a" * 64,
        as_of_ms=0,
        mode="DEBRIEF",
        request_id=uuid4(),
    )

    class Delegate:
        def inventory(self, context):
            calls.append("inventory")
            return ()

        def purge(self, context):
            calls.append("purge")

    wrapper = AuthorizedRepository(Delegate(), lambda context: calls.append("guard"))
    assert wrapper.inventory(ctx) == ()
    wrapper.purge(ctx)
    assert calls == ["guard", "inventory", "guard", "purge"]


def test_production_cannot_enable_mock_pipeline(tmp_path):
    from flowlens.integration import create_integrated_host

    app = create_integrated_host(settings(tmp_path, "development"))
    assert all(not p.ready() for p in app.state.integration.policies() if p.stage != "AUDIO")
    assert app.state.integration.status()["analysis_execution"] == "PROVIDER_CONFIGURATION_REQUIRED"


def test_production_remains_gated(tmp_path):
    with pytest.raises(ValueError, match="Production requires"):
        settings(tmp_path, "production")


def test_joint_maintenance_snapshot_restore(tmp_path):
    from flowlens.integration import create_integrated_host
    from flowlens.recovery.maintenance import Maintenance, Paths
    from flowlens.recovery.snapshots import Snapshots

    cfg = settings(tmp_path)
    with TestClient(create_integrated_host(cfg)):
        pass
    paths = Paths(
        database=cfg.database_path,
        raw=cfg.raw_assets_path,
        artifacts=cfg.artifact_staging_path,
        imports=cfg.import_staging_path,
        journal=cfg.retention_journal_path,
    )
    with Maintenance(paths) as owner:
        assert len(owner.database.specs) == 23
        receipt = Snapshots(owner).create(tmp_path / "backup")
    restored = Snapshots.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=paths.journal,
        expected_manifest_hash=receipt.manifest_hash,
    )
    with Maintenance(restored.paths) as owner:
        owner.check()
        with owner.database.begin() as uow:
            assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()


def pipeline(media, committed, importer, tmp_path):
    from flowlens.integration import create_integrated_host
    from flowlens.integration.catalog import JOINT_MIGRATIONS, repositories
    from flowlens.jobs.coordinator import Jobs
    from flowlens.storage.sqlite.migrate import migrate

    db = importer[0].database
    with db._connect() as conn:
        migrate(conn, JOINT_MIGRATIONS)
    db.repositories.update(repositories())
    app = create_integrated_host(settings(tmp_path / "host"))
    app.state.transactions = db
    app.state.permissions = committed[2]
    app.state.sessions = importer[0].sessions
    app.state.assets = media[0]
    app.state.evidence = media[1]
    app.state.sources = media[0].sources
    engine = app.state.integration
    app.state.jobs = Jobs(
        db, committed[2], media[0], media[1], engine, engine.policies(), allow_mock=True
    )
    rights = media[4].declaration.rights.model_copy(
        update={"cloud_audio": "ALLOWED", "cloud_context": "ALLOWED", "export": "DENIED"}
    )
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        media[3].session_id,
        media[3].source_id,
        rights,
        expected_version=1,
    )
    return app, engine


def test_authenticated_real_ab_pipeline_review_export_and_recovery(
    media, committed, importer, tmp_path
):
    from flowlens.contracts.models import Evidence, JobResult, Usage
    from flowlens.integration.engine import CONFIG, IntentSubmission, intent_projection
    from flowlens.intent.models import Candidate, Provenance, QuoteSlot
    from flowlens.jobs.coordinator import StageInput, result_hash
    from test_jobs import candidate as transcript_candidate

    app, engine = pipeline(media, committed, importer, tmp_path)
    jobs = app.state.jobs
    run = jobs.create(
        media[2],
        CONFIG,
        [
            StageInput(
                stage="STT",
                source_ids=[media[3].source_id],
                asset_ids=[media[4].manifest.assets[0].id],
            ),
            StageInput(stage="INTENT", source_ids=[media[3].source_id]),
            StageInput(stage="FINDINGS", source_ids=[media[3].source_id]),
            StageInput(stage="BRIEF", source_ids=[media[3].source_id]),
        ],
        budget=5000,
        deadline_ms=50000,
        expected_revision=1,
        key="integrated",
    )
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    token = worker.token.get_secret_value()
    lease = jobs.client(token).lease(worker.id, "STT")
    result = transcript_candidate(media, jobs, worker, lease)
    headers = {"Authorization": "Bearer " + token}
    http = TestClient(app, base_url="http://127.0.0.1:8000")
    receipt = http.post(
        f"/internal/jobs/{lease.job_id}/results",
        headers=headers,
        json=result.model_dump(mode="json"),
    )
    assert receipt.status_code == 200, receipt.text
    lease = jobs.client(token).lease(worker.id, "INTENT")
    ctx = jobs.context(token, lease)
    assert ctx.mode == "DEBRIEF"
    segment = result.outputs[0]
    ev = Evidence(
        id=uuid4(),
        kind="TRANSCRIPT",
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=1,
        source_id=segment.source_id,
        segment_id=segment.id,
        source_hash=media[4].content_hash,
        start_ms=segment.start_ms,
        end_ms=segment.end_ms,
        quote=segment.text,
        span_start=0,
        span_end=len(segment.text),
    )
    unknown = QuoteSlot(
        value=None,
        quality="MISSING",
        evidence_ids=(),
        alternatives=(),
        unknowns=("No grounded identity",),
    )
    intent = Candidate(
        id=uuid4(),
        segment_id=segment.id,
        speech_act="UNKNOWN",
        role="UNKNOWN",
        entity_candidates=(),
        callsign=unknown,
        runway=unknown,
        actions=("UNKNOWN",),
        action_evidence_ids=(),
        condition=unknown,
        negation=unknown,
        evidence=(ev,),
        unknowns=("Synthetic mock provider",),
    )
    provenance = Provenance(
        profile="MOCK",
        model="MOCK",
        api_version="integration-1",
        sdk_version="locked",
        prompt_version="intent-1",
        schema_hash="a" * 64,
        config_hash=lease.config_hash,
        input_hash=ctx.input_hash,
        request_hashes=(),
        response_hashes=(),
        calls=0,
        total_tokens=0,
    )
    accepted = JobResult(
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=1,
        job_id=lease.job_id,
        attempt_id=lease.attempt_id,
        lease_id=lease.lease_id,
        input_hash=ctx.input_hash,
        config_hash=lease.config_hash,
        output_hash="0" * 64,
        status="COMPLETE",
        outputs=[intent_projection(ctx, intent, segment)],
        evidence=[ev],
        usage=Usage(audio_ms=0, input_tokens=0, output_tokens=0, cost_microunits=0, latency_ms=0),
        failure_code=None,
    )
    accepted = accepted.model_copy(update={"output_hash": result_hash(accepted)})
    packet = IntentSubmission(result=accepted, candidates=(intent,), provenance=provenance)
    assert (
        http.post("/internal/analysis/intents", json=packet.model_dump(mode="json")).status_code
        == 401
    )
    response = http.post(
        "/internal/analysis/intents", headers=headers, json=packet.model_dump(mode="json")
    )
    assert response.status_code == 200, response.text
    assert (
        http.post(
            "/internal/analysis/intents", headers=headers, json=packet.model_dump(mode="json")
        ).json()
        == response.json()
    )
    read = committed[2].human_context(
        committed[3].token.get_secret_value(),
        ctx.session_id,
        run_id=run.id,
    )
    with engine.database.begin() as uow:
        assert len(engine.memory_rows(read, uow)) == 1
    assert engine.snapshot(read).quality == "AMBIGUOUS"
    http.cookies.set("flowlens_session", committed[3].token.get_secret_value())
    with engine.database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_context_state SET mode='AS_KNOWN' WHERE session_id=?",
            (str(ctx.session_id),),
        )
        uow.commit()
    records = http.get(f"/api/v1/sessions/{ctx.session_id}/analysis-runs/{run.id}/records")
    assert records.status_code == 200
    assert len(records.json()["records"]) == 0  # Unknown historical availability is hidden.
    with engine.database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_context_state SET mode='DEBRIEF',as_of_ms=10000 WHERE session_id=?",
            (str(ctx.session_id),),
        )
        uow.commit()
    records = http.get(f"/api/v1/sessions/{ctx.session_id}/analysis-runs/{run.id}/records")
    assert len(records.json()["records"]) == 2

    http.cookies.clear()
    for stage in ("FINDINGS", "BRIEF"):
        next_lease = jobs.client(token).lease(worker.id, stage)
        assert next_lease is not None
        prepared = http.post(
            "/internal/analysis/prepare", headers=headers, json=next_lease.model_dump(mode="json")
        )
        assert prepared.status_code == 200, prepared.text
        data = accepted.model_dump(mode="json")
        data.update(
            job_id=str(next_lease.job_id),
            attempt_id=str(next_lease.attempt_id),
            lease_id=str(next_lease.lease_id),
            config_hash=next_lease.config_hash,
            outputs=prepared.json()["outputs"],
            evidence=[],
        )
        derived = JobResult.model_validate_json(__import__("json").dumps(data))
        derived = derived.model_copy(update={"output_hash": result_hash(derived)})
        if stage == "BRIEF":
            empty = derived.model_copy(update={"outputs": []})
            empty = empty.model_copy(update={"output_hash": result_hash(empty)})
            rejected = http.post(
                f"/internal/jobs/{next_lease.job_id}/results",
                headers=headers,
                json=empty.model_dump(mode="json"),
            )
            assert rejected.status_code == 422, rejected.text
        response = http.post(
            f"/internal/jobs/{next_lease.job_id}/results",
            headers=headers,
            json=derived.model_dump(mode="json"),
        )
        assert response.status_code == 200, response.text
    with engine.database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM analysis_advisory_ledger").fetchone()[0]
            == 1
        )

    http.cookies.set("flowlens_session", committed[3].token.get_secret_value())
    prefix = f"/api/v1/sessions/{ctx.session_id}/analysis-runs/{run.id}/advisory"
    inventory = http.get(prefix)
    assert inventory.status_code == 200, inventory.text
    document_id = inventory.json()["entries"][0]["id"]
    h = {
        "Origin": app.state.settings.origin,
        "X-CSRF-Token": committed[3].csrf_token,
        "Idempotency-Key": "review-1",
    }
    body = {
        "subject_id": document_id,
        "expected_version": 1,
        "decision": "UNRESOLVED",
        "reason": "Synthetic integration reviewer",
    }
    review_path = prefix + f"/{document_id}/reviews"
    assert http.post(review_path, headers=h, json=body).status_code == 403
    committed[2].grant(
        committed[3].token.get_secret_value(),
        committed[3].account.id,
        ctx.session_id,
        "review",
        role="evaluator",
        expires_ms=1000000,
    )
    reviewed = http.post(review_path, headers=h, json=body)
    assert reviewed.status_code == 200, reviewed.text
    assert http.post(review_path, headers=h, json=body).json() == reviewed.json()
    assert http.post(review_path, headers=h, json={**body, "reason": "Changed"}).status_code == 409
    report_path = prefix + f"/{document_id}/report"
    assert http.get(report_path).status_code == 403
    rights = media[4].declaration.rights.model_copy(
        update={"cloud_audio": "ALLOWED", "cloud_context": "ALLOWED", "export": "ALLOWED"}
    )
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        media[3].session_id,
        media[3].source_id,
        rights,
        expected_version=2,
    )
    for format in ("JSON", "CSV", "HTML"):
        exported = http.get(report_path, params={"format": format})
        assert exported.status_code == 200, exported.text
        assert exported.headers["Cache-Control"] == "no-store"
        assert str(tmp_path) not in exported.text
    from flowlens.advisory.models import Document
    from flowlens.advisory.service import repo as advisory_repo
    from flowlens.integration.advisory import Access

    human = committed[2].human_context(
        committed[3].token.get_secret_value(), ctx.session_id, run_id=run.id
    )
    with engine.database.begin() as uow:
        document = next(
            row for row in advisory_repo(uow).inventory(human) if isinstance(row.body, Document)
        )
        empty = document.model_copy(
            update={"body": document.body.model_copy(update={"facts": (), "findings": ()})}
        )
        assert Access(engine).authorize(human, empty, uow).evidence_ids == ()
    committed[2].revoke(
        committed[3].token.get_secret_value(), committed[3].account.id, ctx.session_id, "export"
    )
    assert http.get(report_path).status_code == 403
    from flowlens.recovery.maintenance import Maintenance
    from flowlens.recovery.snapshots import Snapshots
    from test_recovery import paths, stop_fixture

    p = paths(media, importer, tmp_path)
    stop_fixture(media, importer)
    with Maintenance(p, clock=lambda: importer[2][0]) as owner:
        saved = Snapshots(owner).create(tmp_path / "joint-backup")
    restored = Snapshots.restore(
        tmp_path / "joint-backup",
        tmp_path / "joint-restore",
        journal_path=p.journal,
        expected_manifest_hash=saved.manifest_hash,
        clock=lambda: importer[2][0],
    )
    with Maintenance(restored.paths, clock=lambda: importer[2][0]) as owner:
        owner.check()
        with owner.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM analysis_memory_ledger").fetchone()[0]
                == 1
            )
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM analysis_advisory_ledger").fetchone()[
                    0
                ]
                == 2
            )
            assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()
        from flowlens.integration.catalog import TABLES
        from pydantic import SecretStr

        fresh = owner.sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
        preview = owner.retention.preview(fresh.token.get_secret_value(), ctx.session_id)
        assert preview.counts["analysis_memory_ledger"] == 1
        assert preview.counts["analysis_advisory_ledger"] == 2
        owner.retention.purge(
            fresh.token.get_secret_value(),
            ctx.session_id,
            reason="USER_REQUEST",
            expected_inventory_hash=preview.inventory_hash,
            key="joint-delete",
        )
        with owner.database.begin() as uow:
            for table in TABLES:
                assert (
                    uow.connection.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE session_id=?", (str(ctx.session_id),)
                    ).fetchone()[0]
                    == 0
                )
            assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()
    erased = Snapshots.restore(
        tmp_path / "joint-backup",
        tmp_path / "joint-erased-restore",
        journal_path=p.journal,
        expected_manifest_hash=saved.manifest_hash,
        clock=lambda: importer[2][0],
    )
    assert erased.purged_sessions == [ctx.session_id]
    with Maintenance(erased.paths, clock=lambda: importer[2][0]) as owner:
        with owner.database.begin() as uow:
            for table in TABLES:
                assert (
                    uow.connection.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE session_id=?", (str(ctx.session_id),)
                    ).fetchone()[0]
                    == 0
                )


@pytest.mark.parametrize("tamper", [False, True])
def test_actual_b_audio_worker_uses_authenticated_a_ports(
    media, committed, importer, tmp_path, tamper
):
    from flowlens.audio import AudioTools
    from flowlens.integration.audio import AUDIO_CONFIG
    from flowlens.jobs.coordinator import StageInput
    from flowlens.workers.audio.http import AudioPorts
    from flowlens.workers.audio.models import WorkerConfig
    from flowlens.workers.audio.worker import AudioWorker

    app, engine = pipeline(media, committed, importer, tmp_path)
    jobs = app.state.jobs
    run = jobs.create(
        media[2],
        AUDIO_CONFIG,
        [
            StageInput(
                stage="AUDIO",
                source_ids=[media[3].source_id],
                asset_ids=[media[4].manifest.assets[0].id],
            )
        ],
        budget=1000,
        deadline_ms=50000,
        expected_revision=1,
        key="audio-real",
    )
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    rights = media[4].declaration.rights.model_copy(
        update={"cloud_audio": "DENIED", "cloud_context": "DENIED"}
    )
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        media[3].session_id,
        media[3].source_id,
        rights,
        expected_version=2,
    )
    ports = AudioPorts(
        TestClient(app, base_url="http://127.0.0.1:8000"), worker.token.get_secret_value()
    )
    errors = []
    for method in ("lease", "heartbeat", "cancelled", "resolve", "download", "submit", "result"):
        original = getattr(ports, method)

        def observe(*args, _method=method, _original=original, **kwargs):
            try:
                return _original(*args, **kwargs)
            except Exception as exc:
                errors.append((_method, type(exc).__name__, getattr(exc, "code", "INTERNAL")))
                raise

        setattr(ports, method, observe)

    class Executor(AudioWorker):
        def process(self, binding, guard):
            artifacts = super().process(binding, guard)
            if not tamper:
                return artifacts
            import hashlib
            import json
            import os

            spec, facts, package = media[0].staged(binding.context, artifacts[-1].id)
            with media[0].artifacts.open(package, facts) as descriptor:
                data = json.loads(os.read(descriptor, 2 * 1024**2))
            data["job_id"] = str(uuid4())
            body = json.dumps(data).encode()
            changed = spec.model_copy(
                update={
                    "id": uuid4(),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "size_bytes": len(body),
                }
            )
            ports.submit(binding.context, changed, [body])
            return [*artifacts[:-1], changed]

    outcome = Executor(
        WorkerConfig(worker_id=worker.id, scratch_root=tmp_path.resolve(), heartbeat_seconds=0.1),
        ports,
        ports,
        ports,
        AudioTools.discover(),
        now=lambda: importer[2][0],
    ).run_once()
    if tamper:
        assert outcome.status != "RECEIPT"
        assert any(code == "INVALID_AI_OUTPUT" for _, _, code in errors)
        with engine.database.begin() as uow:
            assert (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_artifact_staging WHERE accepted=1"
                ).fetchone()[0]
                == 0
            )
        return
    assert outcome.status == "RECEIPT", (outcome, errors)
    assert jobs.inspect(media[2], run.id)["run"]["status"] == "COMPLETED"
    with engine.database.begin() as uow:
        rows = uow.connection.execute(
            "SELECT spec FROM platform_artifact_staging WHERE accepted=1"
        ).fetchall()
        assert len(rows) >= 2
        assert any("audio-worker-provenance-1" in row[0] for row in rows)


def test_integrated_bootstrap_cli_accepts_initialized_joint_schema(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    from flowlens.integration.catalog import JOINT_MIGRATIONS
    from flowlens.storage.sqlite.database import Database

    root = tmp_path.resolve()
    with Database(root / "state.sqlite", migrations=JOINT_MIGRATIONS):
        pass
    secret = root / "bootstrap-password"
    secret.write_text("synthetic-cli-password")
    secret.chmod(0o600)
    response = subprocess.run(
        [
            sys.executable,
            "-m",
            "flowlens.cli.bootstrap_admin",
            "--integrated",
            "--database",
            str(root / "state.sqlite"),
            "--login",
            "admin",
            "--password-file",
            str(secret),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path("backend").resolve())},
        timeout=15,
    )
    assert response.returncode == 0, response.stderr
    assert "synthetic-cli-password" not in response.stdout + response.stderr
    with sqlite3.connect(root / "state.sqlite") as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM platform_schema_migrations").fetchone()[0]
            == 23
        )
        assert connection.execute("SELECT COUNT(*) FROM platform_accounts").fetchone()[0] == 1
