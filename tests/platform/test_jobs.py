"""A06 API-owned job scheduling and accepted results using frozen fake B ports."""

from uuid import uuid4

import pytest
from flowlens.testing.harness import FakeAnalysis as FrozenFakeAnalysis
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer


class FakeAnalysis(FrozenFakeAnalysis):
    def validate(self, context, candidate, evidence):
        return candidate

    def accept(self, context, validated, uow):
        for record in validated.outputs:
            uow.repository("analysis.transcripts").append(context, record)


def configured(media, committed, importer):
    from flowlens.jobs.coordinator import Jobs, RunConfig, StagePolicy

    assets, registry, ctx, receipt, prepared = media
    importer[0].database.repositories["analysis.transcripts"] = TranscriptRepository
    module = FakeAnalysis()
    policy = StagePolicy(
        stage="STT",
        version="test-stt-1",
        rights=("cloud_audio",),
        outputs={"TranscriptSegment": "analysis.transcripts"},
        handler=module.accept,
        ready=lambda: True,
        reservation=100,
        config=RunConfig(
            model_version="MOCK",
            api_version="MOCK",
            sdk_version="MOCK",
            prompt_version="test-1",
            reducer_version="test-1",
            rule_version="test-1",
        ),
        concurrency=1,
        lease_ms=1000,
        max_attempts=3,
    )
    jobs = Jobs(
        importer[0].database, committed[2], assets, registry, module, [policy], allow_mock=True
    )
    rights = prepared.declaration.rights.model_copy(update={"cloud_audio": "ALLOWED"})
    token = committed[3].token.get_secret_value()
    committed[1].set_rights(
        token, receipt.session_id, receipt.source_id, rights, expected_version=1
    )
    return jobs, policy


def enqueue(media, configured_jobs, **kwargs):
    from flowlens.jobs.coordinator import RunConfig, StageInput

    jobs, _ = configured_jobs
    assets, _, ctx, receipt, prepared = media
    config = RunConfig(
        model_version="MOCK",
        api_version="MOCK",
        sdk_version="MOCK",
        prompt_version="test-1",
        reducer_version="test-1",
        rule_version="test-1",
    )
    return jobs.create(
        ctx,
        config,
        [
            StageInput(
                stage="STT",
                source_ids=[receipt.source_id],
                asset_ids=[prepared.manifest.assets[0].id],
            )
        ],
        budget=kwargs.get("budget", 300),
        deadline_ms=50000,
        expected_revision=ctx.input_revision,
        key=kwargs.get("key", "start"),
    )


def test_claim_heartbeat_expiry_budget_and_cancel(media, committed, importer):
    from flowlens.core.errors import ContractError

    configured_jobs = configured(media, committed, importer)
    jobs, _ = configured_jobs
    run = enqueue(media, configured_jobs)
    assert enqueue(media, configured_jobs) == run
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    client = jobs.client(worker.token.get_secret_value())
    lease = client.lease(worker.id, "STT")
    assert lease is not None and lease.analysis_run_id == run.id
    assert lease.asset_ids == [media[4].manifest.assets[0].id]
    assert client.lease(worker.id, "STT") is None
    assert jobs.inspect(media[2], run.id)["reserved"] == 100
    committed[4][0] += 500
    renewed = client.heartbeat(lease)
    assert renewed.expires_ms > lease.expires_ms
    committed[4][0] = renewed.expires_ms
    jobs.recover()
    assert client.cancelled(lease)
    assert jobs.inspect(media[2], run.id)["reserved"] == 0
    assert jobs.inspect(media[2], run.id)["used"] == 100
    committed[4][0] += 2000
    retry = client.lease(worker.id, "STT")
    assert retry and retry.attempt_id != lease.attempt_id
    jobs.cancel(
        media[2], run.id, key="cancel", expected_version=jobs.inspect(media[2], run.id)["version"]
    )
    assert client.cancelled(retry)
    with pytest.raises(ContractError):
        client.heartbeat(retry)
    assert jobs.inspect(media[2], run.id)["reserved"] == 0


class TranscriptRepository:
    def __init__(self, connection, check):
        self.connection, self.check = connection, check

    def append(self, context, record):
        self.check()
        self.connection.execute(
            "INSERT INTO platform_records VALUES ('analysis.transcripts',?,?,?,?,?,?)",
            (
                str(record.id),
                str(context.session_id),
                str(context.analysis_run_id),
                context.input_revision,
                type(record).__name__,
                record.model_dump_json(),
            ),
        )
        return record.id

    def get(self, context, record_id):
        from flowlens.contracts.models import TranscriptSegment

        self.check()
        row = self.connection.execute(
            "SELECT payload FROM platform_records WHERE namespace='analysis.transcripts' AND id=? "
            "AND session_id=? AND run_id=? AND revision=?",
            (
                str(record_id),
                str(context.session_id),
                str(context.analysis_run_id),
                context.input_revision,
            ),
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return TranscriptSegment.model_validate_json(row[0])


def candidate(media, jobs, worker, lease, *, status="COMPLETE", cost=20):
    from datetime import UTC, datetime

    from flowlens.contracts.models import Evidence, JobResult, TranscriptSegment, Usage
    from flowlens.jobs.coordinator import result_hash

    wc = jobs.context(worker.token.get_secret_value(), lease)
    e = Evidence(
        id=uuid4(),
        kind="AUDIO",
        session_id=wc.session_id,
        analysis_run_id=wc.analysis_run_id,
        revision=wc.input_revision,
        source_id=media[3].source_id,
        segment_id=lease.asset_ids[0],
        source_hash=media[4].content_hash,
        start_ms=0,
        end_ms=1000,
        quote=None,
        span_start=None,
        span_end=None,
    )
    segment = TranscriptSegment(
        id=uuid4(),
        session_id=wc.session_id,
        analysis_run_id=wc.analysis_run_id,
        revision=wc.input_revision,
        event_time_ms=1000,
        available_time_ms=None,
        recorded_at=datetime(2026, 10, 9, tzinfo=UTC),
        evidence=[e],
        source_id=e.source_id,
        start_ms=0,
        end_ms=1000,
        channel=0,
        text="Synthetic phrase",
        speaker_id=None,
        confidence=None,
        quality="MISSING",
        origin="MOCK",
        provider_profile_version="MOCK",
        supersedes_id=None,
        reason=None,
    )
    r = JobResult(
        session_id=wc.session_id,
        analysis_run_id=wc.analysis_run_id,
        revision=wc.input_revision,
        job_id=lease.job_id,
        attempt_id=lease.attempt_id,
        lease_id=lease.lease_id,
        input_hash=lease.input_hash,
        config_hash=lease.config_hash,
        output_hash="0" * 64,
        status=status,
        outputs=[segment],
        evidence=[e],
        artifacts=[],
        usage=Usage(
            audio_ms=1000, input_tokens=0, output_tokens=0, cost_microunits=cost, latency_ms=5
        ),
        failure_code=None,
    )
    return r.model_copy(update={"output_hash": result_hash(r)})


def active(media, committed, importer):
    cfg = configured(media, committed, importer)
    jobs = cfg[0]
    importer[0].database.repositories["analysis.transcripts"] = TranscriptRepository
    run = enqueue(media, cfg)
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    client = jobs.client(worker.token.get_secret_value())
    lease = client.lease(worker.id, "STT")
    return jobs, run, worker, client, lease


def test_atomic_result_receipt_usage_evidence_and_event(media, committed, importer):
    from flowlens.core.errors import ContractError

    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)
    receipt = client.result(result)
    assert client.result(result) == receipt
    state = jobs.inspect(media[2], run.id)
    assert state["run"]["status"] == "COMPLETED"
    assert state["used"] == 20 and state["reserved"] == 0
    assert state["run"]["usage"]["audio_ms"] == 1000
    with importer[0].database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_receipts").fetchone()[0] == 1
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 1
        assert (
            uow.connection.execute(
                "SELECT COUNT(*) FROM platform_records WHERE namespace='analysis.transcripts'"
            ).fetchone()[0]
            == 1
        )
        assert uow.connection.execute(
            "SELECT payload FROM platform_events WHERE sequence=? AND session_id=?",
            (receipt.sequence, str(lease.session_id)),
        ).fetchone()
    with pytest.raises(ContractError):
        client.result(result.model_copy(update={"output_hash": "f" * 64}))


@pytest.mark.parametrize(
    "boundary", ["domain", "evidence", "artifact", "audit", "receipt", "event", "before_commit"]
)
def test_result_failure_rolls_back_every_effect(media, committed, importer, boundary):
    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)

    def fail(point):
        if point == boundary:
            raise RuntimeError("synthetic result fault")

    jobs.fault = fail
    with pytest.raises(RuntimeError):
        client.result(result)
    with importer[0].database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_receipts").fetchone()[0] == 0
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 0
        assert (
            uow.connection.execute(
                "SELECT COUNT(*) FROM platform_records WHERE namespace='analysis.transcripts'"
            ).fetchone()[0]
            == 0
        )
        assert (
            uow.connection.execute(
                "SELECT COUNT(*) FROM platform_events WHERE run_id=?", (str(run.id),)
            ).fetchone()[0]
            == 0
        )
    assert jobs.inspect(media[2], run.id)["reserved"] == 100
    jobs.fault = None
    client.result(result)


def test_two_claimants_and_two_results_have_one_effect(media, committed, importer):
    from concurrent.futures import ThreadPoolExecutor

    cfg = configured(media, committed, importer)
    jobs = cfg[0]
    importer[0].database.repositories["analysis.transcripts"] = TranscriptRepository
    run = enqueue(media, cfg)
    workers = [
        committed[2].provision_worker(committed[3].token.get_secret_value(), expires_ms=1000000)
        for _ in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(
            pool.map(lambda w: jobs.client(w.token.get_secret_value()).lease(w.id, "STT"), workers)
        )
    assert sum(item is not None for item in leases) == 1
    winner = next(i for i, item in enumerate(leases) if item is not None)
    worker, lease = workers[winner], leases[winner]
    result = candidate(media, jobs, worker, lease)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(
            pool.map(
                lambda _: jobs.client(worker.token.get_secret_value()).result(result), range(2)
            )
        )
    assert receipts[0] == receipts[1]
    assert jobs.inspect(media[2], run.id)["used"] == 20


@pytest.mark.parametrize(
    "failure",
    [
        "expired",
        "cancel",
        "rights",
        "grant",
        "worker",
        "revision",
        "config",
        "hash",
        "quote",
        "channel",
        "budget",
        "scope",
        "availability",
    ],
)
def test_invalid_results_never_write_domain(media, committed, importer, failure):
    from flowlens.core.errors import ContractError
    from flowlens.jobs.coordinator import result_hash

    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)
    if failure == "expired":
        committed[4][0] = lease.expires_ms
    elif failure == "cancel":
        jobs.cancel(
            media[2],
            run.id,
            key="cancel",
            expected_version=jobs.inspect(media[2], run.id)["version"],
        )
    elif failure == "rights":
        rights = media[4].declaration.rights.model_copy(update={"cloud_audio": "DENIED"})
        committed[1].set_rights(
            committed[3].token.get_secret_value(),
            media[3].session_id,
            media[3].source_id,
            rights,
            expected_version=2,
        )
    elif failure == "grant":
        committed[2].revoke(
            committed[3].token.get_secret_value(),
            media[2].actor_id,
            media[2].session_id,
            "analysis",
        )
    elif failure == "worker":
        committed[2].revoke_worker(committed[3].token.get_secret_value(), worker.id)
    elif failure == "revision":
        with importer[0].database.begin() as uow:
            uow.connection.execute(
                "INSERT INTO platform_revisions VALUES (?,2,?)",
                (str(media[2].session_id), "a" * 64),
            )
            uow.commit()
    elif failure == "config":
        with importer[0].database.begin() as uow:
            uow.connection.execute(
                "UPDATE platform_run_state SET config_hash=? WHERE id=?", ("f" * 64, str(run.id))
            )
            uow.commit()
    elif failure == "hash":
        result = result.model_copy(update={"output_hash": "f" * 64})
    elif failure == "quote":
        e = result.evidence[0].model_copy(
            update={"quote": "invented", "span_start": 0, "span_end": 8}
        )
        result = result.model_copy(
            update={
                "evidence": [e],
                "outputs": [result.outputs[0].model_copy(update={"evidence": [e]})],
            }
        )
    elif failure == "channel":
        result = result.model_copy(
            update={"outputs": [result.outputs[0].model_copy(update={"channel": 1})]}
        )
    elif failure == "budget":
        result = result.model_copy(
            update={"usage": result.usage.model_copy(update={"cost_microunits": 101})}
        )
    elif failure == "scope":
        result = result.model_copy(update={"session_id": uuid4()})
    elif failure == "availability":
        result = result.model_copy(
            update={"outputs": [result.outputs[0].model_copy(update={"available_time_ms": 1000})]}
        )
    if failure not in ("hash", "scope"):
        result = result.model_copy(update={"output_hash": result_hash(result)})
    with pytest.raises(ContractError):
        client.result(result)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute(
                "SELECT COUNT(*) FROM platform_records WHERE namespace='analysis.transcripts'"
            ).fetchone()[0]
            == 0
        )
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_receipts").fetchone()[0] == 0


def test_validate_outside_lock_rechecks_after_revocation(media, committed, importer):
    from flowlens.core.errors import ContractError

    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)

    def validate(ctx, candidate, evidence):
        assert not importer[0].database.active
        evidence.resolve(ctx, candidate.evidence[0])
        committed[2].revoke(
            committed[3].token.get_secret_value(),
            media[2].actor_id,
            media[2].session_id,
            "analysis",
        )
        return candidate

    jobs.module.validate = validate
    with pytest.raises(ContractError):
        client.result(result)
    jobs.recover()
    with pytest.raises(ContractError):
        jobs.inspect(media[2], run.id)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute(
                "SELECT reserved FROM platform_run_state WHERE id=?", (str(run.id),)
            ).fetchone()[0]
            == 0
        )
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_receipts").fetchone()[0] == 0


@pytest.mark.parametrize(
    "mode", ["commit", "caught_commit", "raw_commit", "rollback", "missing_write", "wrong_write"]
)
def test_domain_callback_cannot_escape_transaction_or_skip_readback(
    media, committed, importer, mode
):
    from dataclasses import replace

    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)

    def handler(ctx, result, uow):
        if mode in ("commit", "caught_commit", "rollback", "raw_commit"):
            uow.repository("analysis.transcripts").append(ctx, result.outputs[0])
        if mode == "commit":
            uow.commit()
        elif mode == "caught_commit":
            try:
                uow.commit()
            except RuntimeError:
                pass
        elif mode == "raw_commit":
            import sqlite3

            try:
                uow.connection.execute("COMMIT")
            except sqlite3.DatabaseError:
                pass
        elif mode == "rollback":
            uow.rollback()
        elif mode == "wrong_write":
            uow.repository("analysis.transcripts").append(
                ctx, result.outputs[0].model_copy(update={"text": "wrong"})
            )

    jobs.policies["STT"] = replace(jobs.policies["STT"], handler=handler)
    from flowlens.core.errors import ContractError

    with pytest.raises((RuntimeError, KeyError, ContractError)):
        client.result(result)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute(
                "SELECT COUNT(*) FROM platform_records WHERE namespace='analysis.transcripts'"
            ).fetchone()[0]
            == 0
        )
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_receipts").fetchone()[0] == 0


def test_minimal_input_live_scope_and_no_inventory(media, committed, importer):
    from flowlens.core.errors import ContractError

    jobs, run, worker, client, lease = active(media, committed, importer)
    payload = jobs.input(worker.token.get_secret_value(), lease)
    assert payload["records"] == []  # audio consent does not grant context transfer
    assert len(payload["audio"]) == 1
    assert payload["config"]["model_version"] == "MOCK"
    assert not any(
        word in str(payload) for word in ("storage_key", "package_id", "private", "token_hash")
    )
    ctx = jobs.context(worker.token.get_secret_value(), lease)
    jobs.cancel(
        media[2], run.id, key="cancel", expected_version=jobs.inspect(media[2], run.id)["version"]
    )
    with pytest.raises(ContractError):
        jobs.assets.download(ctx, lease.asset_ids[0], 0, 64)
    with pytest.raises(ContractError):
        jobs.input(worker.token.get_secret_value(), lease)


@pytest.mark.parametrize("status", ["PARTIAL", "FAILED"])
def test_partial_and_transient_failure_with_bounded_retry(media, committed, importer, status):
    from flowlens.jobs.coordinator import result_hash

    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(
        media, jobs, worker, lease, status="PARTIAL" if status == "PARTIAL" else "COMPLETE"
    )
    if status == "FAILED":
        result = result.model_copy(
            update={
                "status": "FAILED",
                "outputs": [],
                "evidence": [],
                "failure_code": "PROVIDER_UNAVAILABLE",
            }
        )
        result = result.model_copy(update={"output_hash": result_hash(result)})
    original = client.result(result)
    assert client.result(result) == original
    state = jobs.inspect(media[2], run.id)
    if status == "PARTIAL":
        assert state["run"]["status"] == "PARTIAL"
    else:
        assert state["jobs"][0]["state"] == "RETRY_WAIT"
        for _attempt_number in (2, 3):
            committed[4][0] += 4000
            retry = client.lease(worker.id, "STT")
            assert retry and retry.attempt_id != lease.attempt_id
            failed = result.model_copy(
                update={"attempt_id": retry.attempt_id, "lease_id": retry.lease_id}
            )
            client.result(failed)
        state = jobs.inspect(media[2], run.id)
        assert state["run"]["status"] == "FAILED" and state["jobs"][0]["attempt_count"] == 3
        assert state["used"] == 60 and state["reserved"] == 0
        assert client.lease(worker.id, "STT") is None


def test_unknown_usage_charged_conservatively_and_publication_failure_resync(
    media, committed, importer
):
    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease, cost=None)
    calls = []

    def publish(sid, seq):
        assert not importer[0].database.active
        calls.append((sid, seq))
        raise RuntimeError("synthetic publication failure")

    jobs.publish = publish
    with pytest.raises(RuntimeError, match="Commit is durable"):
        client.result(result)
    receipt = client.result(result)
    assert calls == [(lease.session_id, receipt.sequence)]
    assert jobs.inspect(media[2], run.id)["used"] == 100
    assert jobs.inspect(media[2], run.id)["run"]["usage"]["cost_microunits"] is None
    with importer[0].database.begin() as uow:
        assert uow.connection.execute(
            "SELECT payload FROM platform_events WHERE session_id=? AND sequence=?",
            (str(lease.session_id), receipt.sequence),
        ).fetchone()


def test_stable_receipt_is_not_revocation_bypass(media, committed, importer):
    from flowlens.core.errors import ContractError

    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)
    receipt = client.result(result)
    committed[4][0] = lease.expires_ms + 1000
    assert client.result(result) == receipt
    rights = media[4].declaration.rights.model_copy(update={"cloud_audio": "DENIED"})
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        media[3].session_id,
        media[3].source_id,
        rights,
        expected_version=2,
    )
    with pytest.raises(ContractError):
        client.result(result)


def test_host_worker_job_routes_bounded_and_auth_scoped(media, committed, importer):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.contracts.models import JobLease
    from flowlens.core.host_config import HostSettings

    cfg = configured(media, committed, importer)
    jobs = cfg[0]
    importer[0].database.repositories["analysis.transcripts"] = TranscriptRepository
    app = create_host(HostSettings(profile="test"))
    app.state.permissions = committed[2]
    app.state.sessions = importer[0].sessions
    app.state.transactions = importer[0].database
    app.state.jobs = jobs
    app.state.assets = media[0]
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as http:
        assert http.post("/internal/jobs/lease", json={"stage": "STT"}).status_code == 401
        http.cookies.set("flowlens_session", committed[3].token.get_secret_value())
        h = {
            "Origin": app.state.settings.origin,
            "X-CSRF-Token": committed[3].csrf_token,
            "Idempotency-Key": "httpstart",
        }
        from flowlens.jobs.coordinator import RunConfig

        config = RunConfig(
            model_version="MOCK",
            api_version="MOCK",
            sdk_version="MOCK",
            prompt_version="test-1",
            reducer_version="test-1",
            rule_version="test-1",
        )
        created = http.post(
            f"/api/v1/sessions/{media[2].session_id}/analysis-runs",
            headers=h,
            json={
                "config": config.model_dump(mode="json"),
                "jobs": [
                    {
                        "stage": "STT",
                        "source_ids": [str(media[3].source_id)],
                        "asset_ids": [str(media[4].manifest.assets[0].id)],
                    }
                ],
                "budget_microunits": 300,
                "deadline_ms": 50000,
                "expected_revision": 1,
            },
        )
        assert created.status_code == 202
        h = {"Authorization": "Bearer " + worker.token.get_secret_value()}
        assert (
            http.post("/internal/jobs/lease", headers=h, json={"stage": "STT"}).status_code == 403
        )
        http.cookies.clear()
        leased = http.post("/internal/jobs/lease", headers=h, json={"stage": "STT"})
        assert leased.status_code == 200
        lease = JobLease.model_validate_json(__import__("json").dumps(leased.json()["lease"]))
        prefix = f"/internal/jobs/{lease.job_id}"
        body = lease.model_dump(mode="json")
        assert http.post(prefix + "/input", headers=h, json=body).json()["records"] == []
        assert http.post(prefix + "/heartbeat", headers=h, json=body).status_code == 200
        result = candidate(media, jobs, worker, lease)
        r = http.post(prefix + "/results", headers=h, json=result.model_dump(mode="json"))
        assert r.status_code == 200
        assert (
            http.post(prefix + "/results", headers=h, json=result.model_dump(mode="json")).json()
            == r.json()
        )
        assert r.headers["Cache-Control"] == "no-store"
        assert (
            http.post(
                "/internal/jobs/lease", headers=h, json={"stage": "STT", "actor_id": str(worker.id)}
            ).status_code
            == 422
        )
        assert (
            http.post(
                "/internal/jobs/lease",
                headers={**h, "Content-Type": "application/json"},
                content=b" " * 5000,
            ).status_code
            == 422
        )


def test_restart_active_lease_then_expired_attempt_recovers(media, committed, importer):
    from flowlens.assets.access import Assets
    from flowlens.auth.accounts import Accounts
    from flowlens.auth.permissions import Permissions
    from flowlens.auth.sessions import Sessions
    from flowlens.evidence.registry import EvidenceRegistry
    from flowlens.jobs.coordinator import Jobs
    from flowlens.sources.store import Sources
    from flowlens.storage.sqlite.database import Database

    jobs, run, worker, client, lease = active(media, committed, importer)
    path = importer[0].database.path
    importer[0].database.close()
    with Database(path, repositories={"analysis.transcripts": TranscriptRepository}) as db:
        perms = Permissions(db, Sessions(db, Accounts(db), clock=lambda: committed[4][0]))
        db.context_guard = perms.enforce
        assets = Assets(Sources(db, perms, committed[0].files), media[0].artifacts)
        restarted = Jobs(
            db,
            perms,
            assets,
            EvidenceRegistry(assets.sources, assets),
            FakeAnalysis(),
            list(jobs.policies.values()),
            allow_mock=True,
        )
        assert not restarted.client(worker.token.get_secret_value()).cancelled(lease)
        assert restarted.inspect(media[2], run.id)["reserved"] == 100
        committed[4][0] = lease.expires_ms
        restarted.recover()
        assert restarted.client(worker.token.get_secret_value()).cancelled(lease)
        assert restarted.inspect(media[2], run.id)["reserved"] == 0
        assert not db.active
        with db.begin() as uow:
            assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()


@pytest.mark.parametrize(
    "boundary,exit_code,expected", [("before_commit", 91, 0), ("publication", 92, 1)]
)
def test_actual_process_crash_result_recovery(tmp_path, boundary, exit_code, expected):
    import json
    import subprocess
    import sys

    from flowlens.assets.access import Assets
    from flowlens.assets.storage import PrivateFiles
    from flowlens.auth.accounts import Accounts
    from flowlens.auth.permissions import Permissions
    from flowlens.auth.sessions import Sessions
    from flowlens.contracts.models import JobResult, RequestContext
    from flowlens.evidence.registry import EvidenceRegistry
    from flowlens.jobs.coordinator import Jobs, RunConfig, StagePolicy
    from flowlens.sources.store import Sources
    from flowlens.storage.sqlite.database import Database

    script = tmp_path / "job_crash.py"
    script.write_text("""import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/"tests/platform"))
from test_imports import importer
from test_import_commit import committed
from test_assets_evidence import media
from test_jobs import active,candidate
root=Path(sys.argv[1]);root.mkdir()
ig=importer.__wrapped__(root);i=next(ig)
cg=committed.__wrapped__(i,root);c=next(cg)
mg=media.__wrapped__(i,c,root);m=next(mg)
jobs,run,worker,client,lease=active(m,c,i)
result=candidate(m,jobs,worker,lease)
control=root/"control.json"
control.write_text(json.dumps({"token":worker.token.get_secret_value(),"result":result.model_dump(mode="json"),"ctx":m[2].model_dump(mode="json"),"run_id":str(run.id)}))
control.chmod(0o600)
if sys.argv[2]=="before_commit":jobs.fault=lambda p:os._exit(91) if p=="before_commit" else None
else:jobs.publish=lambda sid,seq:os._exit(92)
client.result(result)
""")
    state = tmp_path / "state"
    crash = subprocess.run(
        [sys.executable, str(script), str(state), boundary], capture_output=True, timeout=30
    )
    assert crash.returncode == exit_code  # never print captured credentials/tracebacks
    control = json.loads((state / "control.json").read_text())
    result = JobResult.model_validate_json(json.dumps(control["result"]))
    ctx = RequestContext.model_validate_json(json.dumps(control["ctx"]))
    module = FakeAnalysis()
    p = StagePolicy(
        stage="STT",
        version="test-stt-1",
        rights=("cloud_audio",),
        outputs={"TranscriptSegment": "analysis.transcripts"},
        handler=module.accept,
        ready=lambda: True,
        reservation=100,
        config=RunConfig(
            model_version="MOCK",
            api_version="MOCK",
            sdk_version="MOCK",
            prompt_version="test-1",
            reducer_version="test-1",
            rule_version="test-1",
        ),
        concurrency=1,
        lease_ms=1000,
        max_attempts=3,
    )
    with Database(
        state / "data.db", repositories={"analysis.transcripts": TranscriptRepository}
    ) as db:
        permissions = Permissions(db, Sessions(db, Accounts(db), clock=lambda: 1000))
        db.context_guard = permissions.enforce
        raw = PrivateFiles(state / "raw")
        derived = PrivateFiles(state / "derivatives")
        try:
            assets = Assets(Sources(db, permissions, raw), derived)
            assets.recover_artifacts()
            jobs = Jobs(
                db,
                permissions,
                assets,
                EvidenceRegistry(assets.sources, assets),
                module,
                [p],
                allow_mock=True,
            )
            with db.begin() as uow:
                assert (
                    uow.connection.execute("SELECT COUNT(*) FROM platform_receipts").fetchone()[0]
                    == expected
                )
                assert (
                    uow.connection.execute(
                        "SELECT COUNT(*) FROM platform_records "
                        "WHERE namespace='analysis.transcripts'"
                    ).fetchone()[0]
                    == expected
                )
                assert (
                    uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0]
                    == expected
                )
                assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()
            receipt = jobs.client(control["token"]).result(result)
            assert jobs.client(control["token"]).result(result) == receipt
            assert jobs.inspect(ctx, result.analysis_run_id)["reserved"] == 0
        finally:
            raw.close()
            derived.close()


def test_upgrade_previous_schema_preserves_source_and_migration_history(tmp_path):
    from flowlens.storage.sqlite.database import Database
    from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

    path = tmp_path / "upgrade.db"
    with Database(path, migrations=PLATFORM_MIGRATIONS[:11]) as db:
        with db.begin() as uow:
            before = dict(
                uow.connection.execute("SELECT id,checksum FROM platform_schema_migrations")
            )
            sid = uuid4()
            uow.connection.execute("INSERT INTO platform_sessions VALUES (?)", (str(sid),))
            uow.commit()
    with Database(path) as db:
        with db.begin() as uow:
            after = dict(
                uow.connection.execute("SELECT id,checksum FROM platform_schema_migrations")
            )
            assert len(after) == len(PLATFORM_MIGRATIONS) and all(
                after[k] == v for k, v in before.items()
            )
            assert uow.connection.execute("SELECT id FROM platform_sessions").fetchone()[0] == str(
                sid
            )
            assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()


def test_derivative_and_new_transcript_quote_commit_atomically(media, committed, importer):
    import hashlib
    import io

    import soundfile
    from flowlens.contracts.models import ArtifactSubmission, Evidence, TimeRange
    from flowlens.jobs.coordinator import result_hash

    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)
    buf = io.BytesIO()
    soundfile.write(buf, [0.0] * 500, 8000, format="WAV", subtype="PCM_16")
    body = buf.getvalue()
    ctx = jobs.context(worker.token.get_secret_value(), lease)
    artifact = ArtifactSubmission(
        id=uuid4(),
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        kind="AUDIO_DERIVATIVE",
        sha256=hashlib.sha256(body).hexdigest(),
        size_bytes=len(body),
        source_asset_id=lease.asset_ids[0],
        transform_version="chunk-1",
        source_range=TimeRange(start_ms=10, end_ms=73),
        derivative_range=TimeRange(start_ms=0, end_ms=63),
        expires_at=None,
        required_capability="audio",
    )
    jobs.assets.submit(ctx, artifact, iter([body]))
    segment = result.outputs[0]
    quote = Evidence(
        id=uuid4(),
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        kind="TRANSCRIPT",
        source_id=segment.source_id,
        segment_id=segment.id,
        source_hash=media[4].content_hash,
        start_ms=0,
        end_ms=1000,
        quote="Synthetic",
        span_start=0,
        span_end=9,
    )
    result = result.model_copy(
        update={"artifacts": [artifact], "evidence": [*result.evidence, quote]}
    )
    result = result.model_copy(update={"output_hash": result_hash(result)})

    def fail(point):
        if point == "artifact":
            raise RuntimeError("synthetic artifact transaction fault")

    jobs.fault = fail
    with pytest.raises(RuntimeError):
        client.result(result)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute(
                "SELECT accepted FROM platform_artifact_staging WHERE id=?", (str(artifact.id),)
            ).fetchone()[0]
            == 0
        )
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_artifacts").fetchone()[0] == 0
    jobs.fault = None
    client.result(result)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute(
                "SELECT accepted FROM platform_artifact_staging WHERE id=?", (str(artifact.id),)
            ).fetchone()[0]
            == 1
        )
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_artifacts").fetchone()[0] == 1
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 2
    jobs.assets.recover_artifacts()
    reader = committed[2].human_context(
        committed[3].token.get_secret_value(), media[2].session_id, run_id=run.id
    )
    assert jobs.evidence.get(reader, quote.id) == quote


def test_default_host_does_not_enable_fake_analysis_and_jobs(media, committed, importer, tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    cfg = configured(media, committed, importer)
    _, policy = cfg
    settings = HostSettings(
        profile="test",
        database_path=tmp_path / "host-db" / "state.db",
        import_staging_path=tmp_path / "host-import",
        raw_assets_path=tmp_path / "host-raw",
        artifact_staging_path=tmp_path / "host-derived",
    )
    with TestClient(
        create_host(
            settings,
            analysis_module=FakeAnalysis(),
            job_policies=[policy],
            repository_factories={"analysis.transcripts": TranscriptRepository},
        )
    ) as http:
        assert http.app.state.jobs is not None
        assert (
            http.app.state.transactions.repositories["analysis.transcripts"] is TranscriptRepository
        )
        assert http.get("/health").json()["profile"] == "MOCK"
        assert http.get("/ready").status_code == 503
    with TestClient(create_host(HostSettings(profile="test"))) as http:
        assert http.app.state.jobs is None
        assert http.get("/ready").status_code == 503


@pytest.mark.parametrize(
    "invalid",
    [
        "budget",
        "config",
        "ready",
        "policy_version",
        "scope_revoke",
        "creator_reset",
        "deadline",
        "wrong_worker",
        "mock_origin",
    ],
)
def test_registered_policy_eligibility_is_live(media, committed, importer, invalid):
    from dataclasses import replace

    from flowlens.core.errors import ContractError
    from flowlens.jobs.coordinator import StageInput

    cfg = configured(media, committed, importer)
    jobs, p = cfg
    if invalid == "budget":
        with pytest.raises(ContractError) as exc:
            enqueue(media, cfg, budget=99)
        assert exc.value.code == "BUDGET_EXCEEDED"
        return
    if invalid == "config":
        wrong = p.config.model_copy(update={"model_version": "unregistered-model"})
        with pytest.raises(ContractError) as exc:
            jobs.create(
                media[2],
                wrong,
                [
                    StageInput(
                        stage="STT",
                        source_ids=[media[3].source_id],
                        asset_ids=[media[4].manifest.assets[0].id],
                    )
                ],
                budget=300,
                deadline_ms=50000,
                expected_revision=1,
                key="wrong",
            )
        assert exc.value.code == "VERSION_CONFLICT"
        return
    if invalid == "ready":
        jobs.policies["STT"] = replace(p, ready=lambda: False)
        with pytest.raises(ContractError) as exc:
            enqueue(media, (jobs, p))
        assert exc.value.code == "PROVIDER_UNAVAILABLE"
        return
    enqueue(media, cfg)
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    client = jobs.client(worker.token.get_secret_value())
    lease = client.lease(worker.id, "STT")
    result = candidate(media, jobs, worker, lease)
    if invalid == "policy_version":
        jobs.policies["STT"] = replace(p, version="new-policy-2")
    elif invalid == "scope_revoke":
        committed[2].revoke_scope(
            committed[3].token.get_secret_value(),
            jobs.scope(worker.token.get_secret_value(), lease),
        )
    elif invalid == "creator_reset":
        importer[0].sessions.accounts.reset_password(
            media[2].actor_id,
            media[2].actor_id,
            __import__("pydantic").SecretStr("synthetic-job-reset-password"),
        )
    elif invalid == "deadline":
        committed[4][0] = lease.deadline_ms
    elif invalid == "wrong_worker":
        other = committed[2].provision_worker(
            committed[3].token.get_secret_value(), expires_ms=1000000
        )
        client = jobs.client(other.token.get_secret_value())
    elif invalid == "mock_origin":
        jobs.allow_mock = False
    with pytest.raises(ContractError):
        client.result(result)
    with importer[0].database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_receipts").fetchone()[0] == 0


def test_nonlease_operator_scope_cannot_bypass_active_job_guard(media, committed, importer):
    from flowlens.core.errors import ContractError

    jobs, run, worker, client, lease = active(media, committed, importer)
    manual = committed[2].bind_worker(
        committed[3].token.get_secret_value(),
        worker.id,
        media[2].session_id,
        run.id,
        expires_ms=900000,
        source_ids=(media[3].source_id,),
        asset_ids=(lease.asset_ids[0],),
    )
    forged = committed[2].worker_context(worker.token.get_secret_value(), manual)
    with pytest.raises(ContractError):
        jobs.assets.download(forged, lease.asset_ids[0], 0, 64)


def test_receipt_wins_if_other_request_commits_before_context_creation(media, committed, importer):
    jobs, run, worker, client, lease = active(media, committed, importer)
    result = candidate(media, jobs, worker, lease)
    original = jobs.permissions.worker_context
    accepted = []

    def race(token, scope):
        jobs.permissions.worker_context = original
        accepted.append(client.result(result))
        return original(token, scope)

    jobs.permissions.worker_context = race
    assert client.result(result) == accepted[0]
    assert jobs.inspect(media[2], run.id)["used"] == 20


def test_context_input_filters_unknown_and_future_availability(media, committed, importer):
    from dataclasses import replace

    from flowlens.jobs.coordinator import StageInput

    cfg = configured(media, committed, importer)
    jobs, p = cfg
    p = replace(p, stage="INTENT", rights=("cloud_context",), outputs={})
    jobs.policies = {"INTENT": p}
    rights = media[4].declaration.rights.model_copy(update={"cloud_context": "ALLOWED"})
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        media[3].session_id,
        media[3].source_id,
        rights,
        expected_version=2,
    )
    jobs.create(
        media[2],
        p.config,
        [StageInput(stage="INTENT", source_ids=[media[3].source_id])],
        budget=300,
        deadline_ms=50000,
        expected_revision=1,
        key="context",
    )
    worker = committed[2].provision_worker(
        committed[3].token.get_secret_value(), expires_ms=1000000
    )
    lease = jobs.client(worker.token.get_secret_value()).lease(worker.id, "INTENT")
    payload = jobs.input(worker.token.get_secret_value(), lease)
    assert payload["audio"] == []
    assert [e["source_event_id"] for e in payload["records"]] == ["instruction-1"]
    ctx = jobs.context(worker.token.get_secret_value(), lease)
    assert [e.source_event_id for e in media[0].sources.read_events(ctx)] == ["instruction-1"]


def test_retry_preserves_unknown_usage_from_lost_attempt(media, committed, importer):
    jobs, run, worker, client, lease = active(media, committed, importer)
    committed[4][0] = lease.expires_ms
    jobs.recover()
    committed[4][0] += 2000
    retry = client.lease(worker.id, "STT")
    client.result(candidate(media, jobs, worker, retry))
    state = jobs.inspect(media[2], run.id)
    assert state["used"] == 120 and state["reserved"] == 0
    assert state["run"]["usage"]["cost_microunits"] is None
    assert state["run"]["usage"]["audio_ms"] is None


def test_cancel_optimistic_version_and_stable_retry(media, committed, importer):
    from flowlens.core.errors import ContractError

    jobs, run, worker, client, lease = active(media, committed, importer)
    version = jobs.inspect(media[2], run.id)["version"]
    with pytest.raises(ContractError) as exc:
        jobs.cancel(media[2], run.id, key="cancel", expected_version=version - 1)
    assert exc.value.code == "VERSION_CONFLICT"
    assert not client.cancelled(lease)
    jobs.cancel(media[2], run.id, key="cancel", expected_version=version)
    after = jobs.inspect(media[2], run.id)
    jobs.cancel(media[2], run.id, key="cancel", expected_version=version)
    assert jobs.inspect(media[2], run.id) == after
    with pytest.raises(ContractError) as exc:
        jobs.cancel(media[2], run.id, key="cancel", expected_version=version + 1)
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"


def test_inspect_reaps_expired_reservation_without_worker_poll(media, committed, importer):
    jobs, run, worker, client, lease = active(media, committed, importer)
    committed[4][0] = lease.expires_ms
    state = jobs.inspect(media[2], run.id)
    assert state["reserved"] == 0 and state["used"] == 100
    assert state["jobs"][0]["state"] == "RETRY_WAIT"


@pytest.mark.parametrize(
    "table", ["platform_receipts", "platform_run_requests", "platform_run_cancels"]
)
def test_all_job_receipts_are_immutable_in_ordinary_sql(media, committed, importer, table):
    import sqlite3

    jobs, run, worker, client, lease = active(media, committed, importer)
    client.result(candidate(media, jobs, worker, lease))
    version = jobs.inspect(media[2], run.id)["version"]
    jobs.cancel(media[2], run.id, key="cancel", expected_version=version)
    with importer[0].database._connect() as connection:
        before = [tuple(row) for row in connection.execute(f"SELECT * FROM {table}")]
        assert before
        for sql in (
            f"UPDATE {table} SET actor_id=actor_id"
            if table != "platform_receipts"
            else f"UPDATE {table} SET payload=payload",
            f"DELETE FROM {table}",
            f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}",
        ):
            with pytest.raises(sqlite3.DatabaseError):
                connection.execute(sql)
        assert [tuple(row) for row in connection.execute(f"SELECT * FROM {table}")] == before
