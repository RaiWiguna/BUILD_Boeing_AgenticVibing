"""A09.1 private report bytes and accepted result promotion through frozen fake B."""

import hashlib
import importlib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from flowlens.contracts.models import ArtifactSubmission, JobResult, Usage
from flowlens.core.errors import ContractError
from test_import_commit import commit, context
from test_import_commit import committed as committed
from test_import_metadata import prepare, request
from test_imports import importer as importer
from test_imports import stage, upload
from test_jobs import FakeAnalysis, configured


@pytest.fixture
def media(importer, committed, tmp_path):
    from flowlens.assets.access import Assets
    from flowlens.assets.storage import PrivateFiles
    from flowlens.evidence.registry import EvidenceRegistry

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

    def declared(d):
        d["rights"].update(
            export="ALLOWED",
            cloud_context="ALLOWED",
            cloud_audio="ALLOWED",
            basis="Synthetic fixture owner permits test export and fake processing",
        )
        for file in d["files"]:
            file["clock"] = {
                "timezone": "UTC",
                "method": "DECLARED_OFFSET",
                "offset_ms": 0,
                "uncertainty_ms": 0,
                "basis": "synthetic report oracle",
                "reviewer": "fixture",
            }

    prepared = prepare(importer, preview, request(preview, modify=declared))
    receipt = commit(committed, preview, prepared)
    ctx = context(committed, receipt)
    files = PrivateFiles(tmp_path / "derivatives")
    assets = Assets(committed[1], files)
    try:
        yield assets, EvidenceRegistry(committed[1], assets), ctx, receipt, prepared
    finally:
        files.close()


def exporting(media, committed, importer):
    from flowlens.jobs.coordinator import Jobs, StageInput

    _, base = configured(media, committed, importer)
    module = FakeAnalysis()
    policy = replace(
        base,
        stage="EXPORT",
        rights=("cloud_context",),
        outputs={},
        handler=module.accept,
        version="test-export-1",
    )
    rights = media[4].declaration.rights.model_copy(update={"cloud_context": "ALLOWED"})
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        media[3].session_id,
        media[3].source_id,
        rights,
        expected_version=2,
    )
    jobs = Jobs(
        importer[0].database, committed[2], media[0], media[1], module, [policy], allow_mock=True
    )
    run = jobs.create(
        media[2],
        policy.config,
        [StageInput(stage="EXPORT", source_ids=[media[3].source_id], asset_ids=[])],
        budget=300,
        deadline_ms=50000,
        expected_revision=media[2].input_revision,
        key="export-job",
    )
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    client = jobs.client(worker.token.get_secret_value())
    lease = client.lease(worker.id, "EXPORT")
    wc = jobs.context(worker.token.get_secret_value(), lease)
    return jobs, run, client, lease, wc


def spec(wc, body=b'{"label":"SYNTHETIC"}', kind="JSON_REPORT", **updates):
    extension = {"JSON_REPORT": "json", "CSV_REPORT": "csv", "HTML_REPORT": "html"}[kind]
    artifact = ArtifactSubmission(
        id=uuid4(),
        session_id=wc.session_id,
        analysis_run_id=wc.analysis_run_id,
        revision=wc.input_revision,
        kind=kind,
        sha256=hashlib.sha256(body).hexdigest(),
        size_bytes=len(body),
        source_asset_id=None,
        source_range=None,
        derivative_range=None,
        transform_version=f"report-{extension}-1",
        expires_at=None,
        required_capability="export",
    )
    return artifact.model_copy(update=updates)


def result(lease, artifact):
    from flowlens.jobs.coordinator import result_hash

    r = JobResult(
        session_id=lease.session_id,
        analysis_run_id=lease.analysis_run_id,
        revision=lease.revision,
        job_id=lease.job_id,
        attempt_id=lease.attempt_id,
        lease_id=lease.lease_id,
        input_hash=lease.input_hash,
        config_hash=lease.config_hash,
        output_hash="0" * 64,
        status="COMPLETE",
        outputs=[],
        evidence=[],
        artifacts=[artifact],
        usage=Usage(audio_ms=0, input_tokens=0, output_tokens=0, cost_microunits=1, latency_ms=1),
        failure_code=None,
    )
    return r.model_copy(update={"output_hash": result_hash(r)})


def lifecycle(media):
    return importlib.import_module("flowlens.artifacts.lifecycle").Artifacts(media[0])


@pytest.mark.parametrize(
    "kind,body",
    [
        ("JSON_REPORT", b'{"label":"SYNTHETIC"}'),
        ("CSV_REPORT", b"label,value\nSYNTHETIC,1\n"),
        ("HTML_REPORT", b"<!doctype html><html><body>SYNTHETIC</body></html>"),
    ],
)
def test_report_upload_private_until_atomic_accept_download_and_inventory(
    media, committed, importer, kind, body
):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    artifact = spec(wc, body, kind)
    assets = media[0]
    assert assets.submit(wc, artifact, iter([body])) == artifact.id
    reports = lifecycle(media)
    assert reports.submit(wc, artifact) == artifact.id
    human = committed[2].human_context(
        committed[3].token.get_secret_value(), wc.session_id, run_id=run.id
    )
    with pytest.raises(ContractError):
        b"".join(reports.download(human, artifact.id))
    committed_result = client.result(result(lease, artifact))
    assert committed_result == client.result(result(lease, artifact))
    assert b"".join(reports.download(human, artifact.id)) == body
    assert reports.inventory(human)[0].id == artifact.id
    assert str(assets.artifacts.root) not in reports.metadata(human, artifact.id).model_dump_json()


def test_expiry_and_live_export_revoke_deny_each_chunk(media, committed, importer):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    body = b"x" * 70000
    artifact = spec(wc, body, "CSV_REPORT", expires_at=datetime.fromtimestamp(2, UTC))
    media[0].submit(wc, artifact, iter([body]))
    client.result(result(lease, artifact))
    human = committed[2].human_context(
        committed[3].token.get_secret_value(), wc.session_id, run_id=run.id
    )
    reports = lifecycle(media)
    stream = reports.download(human, artifact.id)
    assert len(next(stream)) == 65536
    committed[4][0] = 2000
    with pytest.raises(ContractError):
        next(stream)
    with pytest.raises(ContractError):
        reports.metadata(human, artifact.id)
    stream.close()


def test_creator_export_revocation_blocks_pending_submission(media, committed, importer):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    committed[2].revoke(
        committed[3].token.get_secret_value(), media[2].actor_id, wc.session_id, "export"
    )
    with pytest.raises(ContractError):
        media[0].submit(wc, spec(wc), iter([b'{"label":"SYNTHETIC"}']))


@pytest.mark.parametrize(
    "updates",
    [
        {"transform_version": "../../outside"},
        {"required_capability": "audio"},
        {"session_id": uuid4()},
        {"sha256": "0" * 64},
    ],
)
def test_invalid_report_metadata_or_hash_not_promoted(media, committed, importer, updates):
    from flowlens.imports.staging import ImportFailure

    jobs, run, client, lease, wc = exporting(media, committed, importer)
    with pytest.raises((ContractError, ImportFailure)):
        media[0].submit(wc, spec(wc, **updates), iter([b'{"label":"SYNTHETIC"}']))
    with importer[0].database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_artifacts").fetchone()[0] == 0
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_artifact_staging").fetchone()[0]
            == 0
        )


def test_result_fault_leaves_report_pending_and_retry_promotes_once(media, committed, importer):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    artifact = spec(wc)
    media[0].submit(wc, artifact, iter([b'{"label":"SYNTHETIC"}']))

    def failed(phase):
        if phase == "artifact":
            raise RuntimeError("synthetic promotion fault")

    jobs.fault = failed
    with pytest.raises(RuntimeError):
        client.result(result(lease, artifact))
    with importer[0].database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_artifacts").fetchone()[0] == 0
        assert (
            uow.connection.execute("SELECT accepted FROM platform_artifact_staging").fetchone()[0]
            == 0
        )
    jobs.fault = None
    client.result(result(lease, artifact))
    assert (
        len(
            lifecycle(media).inventory(
                committed[2].human_context(
                    committed[3].token.get_secret_value(), wc.session_id, run_id=run.id
                )
            )
        )
        == 1
    )


def test_expired_report_is_omitted_from_inventory(media, committed, importer):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    artifact = spec(wc, expires_at=datetime.fromtimestamp(2, UTC))
    media[0].submit(wc, artifact, iter([b'{"label":"SYNTHETIC"}']))
    client.result(result(lease, artifact))
    human = committed[2].human_context(
        committed[3].token.get_secret_value(), wc.session_id, run_id=run.id
    )
    committed[4][0] = 2000
    assert lifecycle(media).inventory(human) == []


def test_expired_accepted_report_bytes_erased_and_restart_tolerates_tombstone(
    media, committed, importer
):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    artifact = spec(wc, expires_at=datetime.fromtimestamp(2, UTC))
    media[0].submit(wc, artifact, iter([b'{"label":"SYNTHETIC"}']))
    client.result(result(lease, artifact))
    with importer[0].database.begin() as uow:
        package = uow.connection.execute(
            "SELECT package_id FROM platform_artifact_staging WHERE id=?", (str(artifact.id),)
        ).fetchone()[0]
    committed[4][0] = 2000
    media[0].recover_artifacts()
    assert not (media[0].artifacts.root / package).exists()
    media[0].recover_artifacts()


def test_export_revoke_between_report_chunks_is_live(media, committed, importer):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    body = b"x" * 70000
    artifact = spec(wc, body, "CSV_REPORT")
    media[0].submit(wc, artifact, iter([body]))
    client.result(result(lease, artifact))
    human = committed[2].human_context(
        committed[3].token.get_secret_value(), wc.session_id, run_id=run.id
    )
    stream = lifecycle(media).download(human, artifact.id)
    try:
        assert len(next(stream)) == 65536
        committed[2].revoke(
            committed[3].token.get_secret_value(), human.actor_id, wc.session_id, "export"
        )
        with pytest.raises(ContractError):
            next(stream)
    finally:
        stream.close()


def test_truncated_report_upload_has_no_rows_or_private_package(media, committed, importer):
    from flowlens.imports.staging import ImportFailure

    jobs, run, client, lease, wc = exporting(media, committed, importer)
    artifact = spec(wc)
    with pytest.raises(ImportFailure):
        media[0].submit(wc, artifact, iter([b"{"]))
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_artifact_staging").fetchone()[0]
            == 0
        )
    assert not [p for p in media[0].artifacts.root.iterdir() if not p.name.startswith(".")]
