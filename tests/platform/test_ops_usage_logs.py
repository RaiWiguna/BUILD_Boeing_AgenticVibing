"""Usage keeps provider unknowns distinct from reservations; logs exclude user input."""

import importlib
import json
import logging

import pytest
from flowlens.core.errors import ContractError
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_jobs import active, candidate


def test_usage_reservation_and_reported_totals_no_double_charge(media, committed, importer):
    jobs, run, worker, client, lease = active(media, committed, importer)
    cls = importlib.import_module("flowlens.ops.usage").UsageReader
    service = cls(committed[2])
    before = service.read(media[2])
    assert before.reserved_microunits == lease.budget_microunits and before.used_microunits == 0
    assert before.reported_usage.audio_ms is None
    assert before.provider_billing_verified is False
    value = candidate(media, jobs, worker, lease)
    client.result(value)
    client.result(value)
    after = service.read(media[2])
    assert after.attempts == 1 and after.reserved_microunits == 0
    assert after.reported_usage == value.usage
    assert after.used_microunits == value.usage.cost_microunits
    assert after.remaining_microunits == after.budget_microunits - after.used_microunits


def test_safe_log_schema_never_serializes_untrusted_fields(caplog):
    mod = importlib.import_module("flowlens.ops.logs")
    with caplog.at_level(logging.INFO, logger="flowlens.ops"):
        mod.emit(
            event="HTTP_REQUEST",
            request_id="not-a-uuid",
            transcript="private transcript",
            token="secret",
        )
        mod.emit(event="HTTP_REQUEST", status=500, latency_ms=5)
    assert len(caplog.records) == 1
    data = json.loads(caplog.records[0].message)
    assert data["status"] == 500 and "private transcript" not in caplog.text
    assert "secret" not in caplog.text and "not-a-uuid" not in caplog.text


def test_unknown_reported_cost_stays_unknown_even_when_reservation_charged(
    media, committed, importer
):
    jobs, run, worker, client, lease = active(media, committed, importer)
    value = candidate(media, jobs, worker, lease)
    from flowlens.jobs.coordinator import result_hash

    value = value.model_copy(
        update={"usage": value.usage.model_copy(update={"cost_microunits": None})}
    )
    value = value.model_copy(update={"output_hash": result_hash(value)})
    client.result(value)
    service = importlib.import_module("flowlens.ops.usage").UsageReader(committed[2])
    report = service.read(media[2])
    assert report.used_microunits == lease.budget_microunits
    assert report.reported_usage.cost_microunits is None
    assert not report.provider_billing_verified


def test_budget_invariant_and_revoked_scope_are_denied(media, committed, importer):
    jobs, run, worker, client, lease = active(media, committed, importer)
    service = importlib.import_module("flowlens.ops.usage").UsageReader(committed[2])
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_run_state SET reserved=reserved+1 WHERE id=?", (str(run.id),)
        )
        uow.commit()
    with pytest.raises(ContractError):
        service.read(media[2])
    committed[2].revoke(
        committed[3].token.get_secret_value(), media[2].actor_id, media[2].session_id, "analysis"
    )
    with pytest.raises(ContractError):
        service.read(media[2])


def test_job_log_only_after_durable_commit_not_rollback(media, committed, importer, caplog):
    jobs, run, worker, client, lease = active(media, committed, importer)
    value = candidate(media, jobs, worker, lease)

    def failed(phase):
        if phase == "audit":
            raise RuntimeError("private provider exception")

    jobs.fault = failed
    with caplog.at_level(logging.INFO, logger="flowlens.ops"):
        with pytest.raises(RuntimeError):
            client.result(value)
        assert not [r for r in caplog.records if "JOB_ATTEMPT_FINISHED" in r.message]
        jobs.fault = lambda phase: None
        client.result(value)
        client.result(value)
    events = [json.loads(r.message) for r in caplog.records if "JOB_ATTEMPT_FINISHED" in r.message]
    assert len(events) == 1 and events[0]["stage"] == "STT"
    assert "private provider exception" not in caplog.text and "Synthetic phrase" not in caplog.text


def test_supported_json_log_sink_emits_without_global_sdk_debug():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from flowlens.ops.logs import configure, emit; configure(); configure(); "
            "emit(event='HTTP_REQUEST',status=200,latency_ms=5)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stderr.splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["status"] == 200
    assert result.stdout == ""
