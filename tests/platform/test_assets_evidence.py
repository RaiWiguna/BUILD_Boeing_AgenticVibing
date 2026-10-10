"""A05 authorized media and scoped evidence registry acceptance."""

import hashlib
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from test_import_commit import commit, context, ready
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_imports import upload


@pytest.fixture
def media(importer, committed, tmp_path):
    from flowlens.assets.access import Assets
    from flowlens.assets.storage import PrivateFiles
    from flowlens.evidence.registry import EvidenceRegistry

    preview, prepared = ready(
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
    receipt = commit(committed, preview, prepared)
    ctx = context(committed, receipt)
    artifacts = PrivateFiles(tmp_path / "derivatives")
    assets = Assets(committed[1], artifacts)
    evidence = EvidenceRegistry(committed[1], assets)
    try:
        yield assets, evidence, ctx, receipt, prepared
    finally:
        artifacts.close()


def test_audio_port_range_integrity_and_live_grant_denial(media, committed):
    from flowlens.core.errors import ContractError

    assets, _, ctx, receipt, prepared = media
    asset = prepared.manifest.assets[0]
    raw = Path("tests/fixtures/audio/hold-short.wav").read_bytes()
    assert assets.download(ctx, asset.id, 0, 64) == raw[:64]
    assert hashlib.sha256(assets.download(ctx, asset.id, 0, len(raw))).hexdigest() == asset.sha256
    for start, end in ((-1, 2), (5, 5), (0, len(raw) + 1)):
        with pytest.raises(ContractError):
            assets.download(ctx, asset.id, start, end)
    committed[2].revoke(
        committed[3].token.get_secret_value(), ctx.actor_id, receipt.session_id, "audio"
    )
    with pytest.raises(ContractError):
        assets.download(ctx, asset.id, 0, 64)


def event_evidence(media, committed):
    from flowlens.contracts.models import Evidence

    _, _, ctx, receipt, prepared = media
    record = committed[1].read_events(ctx)[0]
    return Evidence(
        id=uuid4(),
        kind="EVENT",
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        source_id=receipt.source_id,
        segment_id=record.id,
        source_hash=prepared.content_hash,
        start_ms=None,
        end_ms=None,
        quote=record.statement[:9],
        span_start=0,
        span_end=9,
    )


def test_registry_register_resolve_quote_hash_and_atomic_rollback(media, committed, importer):
    from flowlens.core.errors import ContractError

    registry, ctx = media[1], media[2]
    e = event_evidence(media, committed)
    with importer[0].database.begin() as uow:
        assert registry.register(ctx, e, uow) == e.id
    with pytest.raises(ContractError):
        registry.get(ctx, e.id)
    with importer[0].database.begin() as uow:
        registry.register(ctx, e, uow)
        uow.commit()
    assert registry.resolve(ctx, e) == e
    assert registry.get(ctx, e.id) == e
    for modified in (
        e.model_copy(update={"source_hash": "0" * 64}),
        e.model_copy(update={"quote": "Wrong text"}),
        e.model_copy(update={"session_id": uuid4()}),
    ):
        with pytest.raises(ContractError):
            registry.resolve(ctx, modified)


def test_audio_evidence_requires_actual_asset_mapping_and_range(media):
    from flowlens.contracts.models import Evidence
    from flowlens.core.errors import ContractError

    assets, registry, ctx, receipt, prepared = media
    e = Evidence(
        id=uuid4(),
        kind="AUDIO",
        session_id=ctx.session_id,
        analysis_run_id=None,
        revision=ctx.input_revision,
        source_id=receipt.source_id,
        segment_id=prepared.manifest.assets[0].id,
        source_hash=prepared.content_hash,
        start_ms=0,
        end_ms=1000,
        quote=None,
        span_start=None,
        span_end=None,
    )
    assert registry.resolve(ctx, e) == e
    with pytest.raises(ContractError):
        registry.resolve(ctx, e.model_copy(update={"end_ms": 1000000}))
    with pytest.raises(ContractError):
        registry.resolve(ctx, e.model_copy(update={"segment_id": uuid4()}))


def test_worker_minimal_asset_allowlist_and_cloud_gate(media, committed, importer):
    from flowlens.core.errors import ContractError

    assets, _, ctx, receipt, prepared = media
    permissions = committed[2]
    token = committed[3].token.get_secret_value()
    run = uuid4()
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_runs VALUES (?,?,?)",
            (str(receipt.session_id), str(run), ctx.input_revision),
        )
        uow.commit()
    worker = permissions.provision_worker(token, expires_ms=1000000)
    scope = permissions.bind_worker(
        token,
        worker.id,
        receipt.session_id,
        run,
        expires_ms=900000,
        source_ids=(receipt.source_id,),
        asset_ids=(prepared.manifest.assets[0].id,),
    )
    workerctx = permissions.worker_context(worker.token.get_secret_value(), scope)
    with pytest.raises(ContractError):
        assets.download(workerctx, prepared.manifest.assets[0].id, 0, 64)
    rights = prepared.declaration.rights.model_copy(
        update={"cloud_audio": "ALLOWED", "cloud_context": "ALLOWED"}
    )
    committed[1].set_rights(
        token, receipt.session_id, receipt.source_id, rights, expected_version=1
    )
    assert len(assets.download(workerctx, prepared.manifest.assets[0].id, 0, 64)) == 64
    with pytest.raises(ContractError):
        assets.download(workerctx, uuid4(), 0, 64)


def test_http_range_headers_suffix_and_denied_request(tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings
    from flowlens.imports.staging import ImportPreview
    from pydantic import SecretStr
    from test_import_metadata import declaration

    app = create_host(
        HostSettings(
            profile="test",
            database_path=tmp_path / "db" / "http.db",
            import_staging_path=tmp_path / "staging",
            raw_assets_path=tmp_path / "raw",
        )
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        admin = app.state.accounts.bootstrap("admin", SecretStr("synthetic-import-initial"))
        app.state.accounts.change_password(
            admin.id, SecretStr("synthetic-import-initial"), SecretStr("synthetic-import-changed")
        )
        auth = app.state.sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
        client.cookies.set("flowlens_session", auth.token.get_secret_value())
        h = {
            "Origin": app.state.settings.origin,
            "X-CSRF-Token": auth.csrf_token,
            "Idempotency-Key": "upload",
        }
        body = Path("tests/fixtures/audio/hold-short.wav").read_bytes()
        preview = ImportPreview.model_validate_json(
            client.post(
                "/api/v1/imports", headers=h, files={"audio": ("sample.wav", body, "audio/wav")}
            ).text
        )
        base = f"/api/v1/imports/{preview.id}"
        h["Idempotency-Key"] = "metadata"
        client.post(
            base + "/metadata",
            headers=h,
            json={"expected_revision": 0, "declaration": declaration(preview)},
        )
        h["Idempotency-Key"] = "commit"
        result = client.post(base + "/commit", headers=h, json={"expected_revision": 1}).json()
        sid = UUID(result["session_id"])
        url = f"/api/v1/assets/{preview.files[0].id}/audio"
        assert client.get(url, headers={"Range": "bytes=0-9"}).status_code == 403
        for cap in ("read", "audio"):
            app.state.permissions.grant(
                auth.token.get_secret_value(),
                admin.id,
                sid,
                cap,
                role="evaluator",
                expires_ms=app.state.sessions.clock() + 100000,
            )
        r = client.get(url, headers={"Range": "bytes=0-9"})
        assert r.status_code == 206 and r.content == body[:10]
        assert r.headers["Content-Range"] == f"bytes 0-9/{len(body)}"
        assert r.headers["Content-Length"] == "10" and r.headers["Cache-Control"] == "no-store"
        assert client.get(url, headers={"Range": "bytes=-10"}).content == body[-10:]
        assert client.get(url, headers={"Range": "bytes=999999999-"}).status_code == 416
        assert client.get(url, headers={"Range": "bytes=0-1,3-4"}).status_code == 416
        assert client.get(url).content == body
        assert str(tmp_path) not in str(dict(r.headers))


def test_derivative_submission_validated_idempotent_and_private(media, committed, importer):
    import io

    import soundfile
    from flowlens.contracts.models import ArtifactSubmission, TimeRange
    from flowlens.core.errors import ContractError
    from flowlens.imports.staging import ImportFailure

    assets, _, ctx, receipt, prepared = media
    permissions = committed[2]
    token = committed[3].token.get_secret_value()
    run = uuid4()
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_runs VALUES (?,?,?)",
            (str(receipt.session_id), str(run), ctx.input_revision),
        )
        uow.commit()
    rights = prepared.declaration.rights.model_copy(update={"cloud_audio": "ALLOWED"})
    committed[1].set_rights(
        token, receipt.session_id, receipt.source_id, rights, expected_version=1
    )
    worker = permissions.provision_worker(token, expires_ms=1000000)
    scope = permissions.bind_worker(
        token,
        worker.id,
        receipt.session_id,
        run,
        expires_ms=900000,
        source_ids=(receipt.source_id,),
        asset_ids=(prepared.manifest.assets[0].id,),
    )
    wc = permissions.worker_context(worker.token.get_secret_value(), scope)
    buffer = io.BytesIO()
    soundfile.write(buffer, [0.0] * 500, 8000, format="WAV", subtype="PCM_16")
    body = buffer.getvalue()
    artifact = ArtifactSubmission(
        id=uuid4(),
        kind="AUDIO_DERIVATIVE",
        session_id=wc.session_id,
        analysis_run_id=run,
        revision=wc.input_revision,
        sha256=hashlib.sha256(body).hexdigest(),
        size_bytes=len(body),
        source_asset_id=prepared.manifest.assets[0].id,
        transform_version="resample-1",
        source_range=TimeRange(start_ms=10, end_ms=73),
        derivative_range=TimeRange(start_ms=0, end_ms=63),
        expires_at=None,
        required_capability="audio",
    )
    assert assets.submit(wc, artifact, iter([body])) == artifact.id
    assert assets.submit(wc, artifact, iter([body])) == artifact.id
    assert assets.staged(wc, artifact.id)[0] == artifact
    with pytest.raises(ImportFailure):
        assets.submit(
            wc, artifact.model_copy(update={"id": uuid4(), "sha256": "0" * 64}), iter([body])
        )
    with pytest.raises(ContractError):
        assets.submit(
            wc,
            artifact.model_copy(
                update={"id": uuid4(), "source_range": TimeRange(start_ms=0, end_ms=100000)}
            ),
            iter([body]),
        )
    with pytest.raises(ContractError):
        assets.staged(ctx, artifact.id)
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    # Use the real transport/error boundary without starting a second DB owner.
    app = create_host(HostSettings(profile="test"))
    app.state.assets = assets
    app.state.permissions = permissions
    app.state.sessions = importer[0].sessions
    app.state.transactions = importer[0].database
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        h = {
            "Authorization": "Bearer " + worker.token.get_secret_value(),
            "X-Artifact-Metadata": artifact.model_dump_json(),
        }
        url = f"/internal/artifacts/{artifact.id}?scope_id={scope}"
        response = client.put(url, headers=h, content=body)
        assert response.status_code == 200 and response.json() == {"id": str(artifact.id)}
        assert client.put(url, headers=h, content=body[:-1]).status_code == 422
        assert client.put(url, headers=h, content=body + b"x").status_code == 422
        assert client.put(url, content=body).status_code == 401
        assert len(list(assets.artifacts.root.iterdir())) == 2  # lock + one durable candidate


def test_event_evidence_future_and_unknown_availability_are_unavailable(media, committed, importer):
    from flowlens.contracts.models import Evidence
    from flowlens.core.errors import ContractError

    _, registry, ctx, receipt, prepared = media
    records = committed[1].read_events(ctx)
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_context_state SET as_of_ms=150,mode='AS_KNOWN' WHERE session_id=?",
            (str(ctx.session_id),),
        )
        uow.commit()
    fresh = committed[2].human_context(committed[3].token.get_secret_value(), ctx.session_id)
    for record in records:
        if (
            record.available_time_ms is None
            or record.available_time_ms > 150
            or record.event_time_ms > 150
        ):
            e = Evidence(
                id=uuid4(),
                kind="EVENT",
                session_id=ctx.session_id,
                analysis_run_id=None,
                revision=ctx.input_revision,
                source_id=receipt.source_id,
                segment_id=record.id,
                source_hash=prepared.content_hash,
                start_ms=None,
                end_ms=None,
                quote=None,
                span_start=None,
                span_end=None,
            )
            with pytest.raises(ContractError) as error:
                registry.resolve(fresh, e)
            assert error.value.code == "EVIDENCE_UNAVAILABLE"


def test_transcript_evidence_verifies_anchor_quote_without_granting_raw_audio(
    media, committed, importer
):
    from datetime import UTC, datetime

    from flowlens.contracts.models import Evidence, TranscriptSegment
    from flowlens.core.errors import ContractError

    _, registry, ctx, receipt, prepared = media
    anchor = Evidence(
        id=uuid4(),
        kind="AUDIO",
        session_id=ctx.session_id,
        analysis_run_id=None,
        revision=ctx.input_revision,
        source_id=receipt.source_id,
        segment_id=prepared.manifest.assets[0].id,
        source_hash=prepared.content_hash,
        start_ms=0,
        end_ms=1000,
        quote=None,
        span_start=None,
        span_end=None,
    )
    segment = TranscriptSegment(
        id=uuid4(),
        session_id=ctx.session_id,
        analysis_run_id=None,
        revision=ctx.input_revision,
        event_time_ms=0,
        available_time_ms=None,
        recorded_at=datetime(2026, 10, 9, tzinfo=UTC),
        source_id=receipt.source_id,
        start_ms=0,
        end_ms=1000,
        channel=0,
        text="Synthetic phrase",
        speaker_id=None,
        confidence=None,
        quality="MISSING",
        origin="MOCK",
        provider_profile_version="fixture",
        supersedes_id=None,
        reason=None,
        evidence=[anchor],
    )

    class Repository:
        def get(self, context, identifier):
            if identifier != segment.id:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            return segment

        def append(self, context, record):
            return record.id

    importer[0].database.repositories["analysis.transcripts"] = lambda connection, guard: (
        Repository()
    )
    e = Evidence(
        id=uuid4(),
        kind="TRANSCRIPT",
        session_id=ctx.session_id,
        analysis_run_id=None,
        revision=ctx.input_revision,
        source_id=receipt.source_id,
        segment_id=segment.id,
        source_hash=prepared.content_hash,
        start_ms=0,
        end_ms=1000,
        quote="Synthetic",
        span_start=0,
        span_end=9,
    )
    committed[2].revoke(
        committed[3].token.get_secret_value(), ctx.actor_id, receipt.session_id, "audio"
    )
    fresh = committed[2].human_context(committed[3].token.get_secret_value(), receipt.session_id)
    assert registry.resolve(fresh, e) == e
    with pytest.raises(ContractError):
        registry.resolve(fresh, anchor)
    segment = segment.model_copy(
        update={"evidence": [anchor.model_copy(update={"end_ms": 1000000})]}
    )
    with pytest.raises(ContractError):
        registry.resolve(fresh, e)


def test_audio_evidence_missing_file_is_unavailable(media):
    from flowlens.contracts.models import Evidence
    from flowlens.core.errors import ContractError
    from flowlens.imports.staging import ImportFailure

    assets, registry, ctx, receipt, prepared = media
    asset = prepared.manifest.assets[0]
    next(assets.sources.files.root.rglob(str(asset.id) + ".raw")).unlink()
    evidence = Evidence(
        id=uuid4(),
        kind="AUDIO",
        session_id=ctx.session_id,
        analysis_run_id=None,
        revision=ctx.input_revision,
        source_id=receipt.source_id,
        segment_id=asset.id,
        source_hash=prepared.content_hash,
        start_ms=0,
        end_ms=1000,
        quote=None,
        span_start=None,
        span_end=None,
    )
    with pytest.raises((ContractError, ImportFailure)):
        registry.resolve(ctx, evidence)
