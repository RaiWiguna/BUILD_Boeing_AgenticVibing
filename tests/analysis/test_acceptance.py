"""B06 cross-registration acceptance and runner failure propagation."""

import asyncio
import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest
from flowlens.analysis.config import AnalysisConfig
from flowlens.analysis.module import register_analysis
from flowlens.core.modules import ModuleRegistry
from flowlens.testing.acceptance import command, local_checks, manifest
from flowlens.testing.advisory import AdvisoryReferenceTransactions
from flowlens.testing.analysis import AnalysisReferenceTransactions
from flowlens.testing.intent_memory import context


def test_cross_packet_caller_uow_restart_cancel_purge():
    result = asyncio.run(local_checks())
    assert result["status"] == "passed"
    assert result["profile"] == "MOCK"
    assert result["database"] == "disposable-cleaned"
    assert result["mock_provider_calls"] == 1
    assert result["real_provider_calls"] == result["real_stt_calls"] == 0
    assert result["real_gemini_calls"] == 0
    assert result["integrated_pipeline_ready"] is False
    assert result["real_smoke"] == "NOT_RUN"
    assert result["benchmark_metrics"] is None
    assert result["B03_EXTERNAL_ACCEPTANCE_PENDING"] == [
        "STT_ACCOUNT_LOGIN_REQUIRED",
        "AUDITED_BENCHMARK_PENDING",
    ]
    assert result["B04_EXTERNAL_ACCEPTANCE_PENDING"] == [
        "GEMINI_ACCOUNT_ACCESS_UNVERIFIED",
        "REAL_GEMINI_SMOKE_PENDING",
        "AUDITED_SEMANTIC_BENCHMARK_PENDING",
    ]
    inventory = result["manifest"]
    assert [m["id"] for m in inventory["migrations"]] == [
        "platform.0001",
        "analysis.0001",
        "analysis.0002",
        "analysis.0003",
        "analysis.0004",
    ]
    assert [m["name"] for m in inventory["modules"]] == [
        "analysis",
        "analysis_transcripts",
        "intent_memory",
        "advisory",
    ]


def test_upgrade_from_b01_preserves_configuration_and_platform(tmp_path):
    ctx = context()
    path = tmp_path / "upgrade.db"
    tx = AnalysisReferenceTransactions(path)
    tx.seed(ctx)
    service = register_analysis(AnalysisConfig(profile="test"), tx).services["analysis"]
    with tx.begin() as uow:
        identifier = service.configure(ctx, uow)
        uow.commit()
    original = service.inventory(ctx)
    upgraded = AdvisoryReferenceTransactions(path)
    for _ in range(2):
        restarted = AdvisoryReferenceTransactions(path)
        with restarted.begin() as uow:
            record = uow.repository("analysis.configuration").get(ctx, identifier)
            assert record == original[0]
            assert uow.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert not uow.conn.execute("PRAGMA foreign_key_check").fetchall()
            assert uow.conn.execute("SELECT count(*) FROM platform_runs").fetchone()[0] == 1
    with closing(sqlite3.connect(upgraded.path)) as conn:
        assert [r[0] for r in conn.execute("SELECT id FROM mock_migrations ORDER BY id")] == [
            "analysis.0001",
            "analysis.0002",
            "analysis.0003",
            "analysis.0004",
            "platform.0001",
        ]


@pytest.mark.parametrize("defect", ["ready", "handler", "snapshot", "inventory", "version"])
def test_manifest_rejects_false_readiness_or_placeholder_hooks(tmp_path, defect):
    tx = AdvisoryReferenceTransactions(tmp_path / "manifest.db")
    reg = register_analysis(AnalysisConfig(profile="test"), tx)
    changes = {
        "ready": {"readiness": lambda: True},
        "handler": {"job_handlers": {"PLACEHOLDER": lambda *_: None}},
        "snapshot": {"snapshot_reader": lambda _: None},
        "inventory": {"inventory_namespaces": ()},
        "version": {"contract_version": "2.0.0"},
    }
    with pytest.raises((RuntimeError, ValueError)):
        manifest((replace(reg, **changes[defect]),))


def test_registry_rejects_mock_production_and_namespace_collision(tmp_path):
    tx = AdvisoryReferenceTransactions(tmp_path / "registry.db")
    reg = register_analysis(AnalysisConfig(profile="test"), tx)
    with pytest.raises(ValueError, match="MOCK"):
        ModuleRegistry(profile="production").register(reg)
    duplicate = replace(reg, name="collision", migrations=())
    with pytest.raises(RuntimeError, match="namespace"):
        manifest((reg, duplicate))


def test_runner_preserves_failure_and_timeout(monkeypatch):
    import subprocess

    monkeypatch.setattr(
        "flowlens.testing.acceptance.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 7, "failed assertion", "diagnostic"),
    )
    result = command(("-m", "pytest"))
    assert result["status"] == "FAIL" and result["exit_code"] == 7
    assert result["stdout"] == "failed assertion"

    def timeout(*a, **k):
        raise subprocess.TimeoutExpired(a, 300)

    monkeypatch.setattr("flowlens.testing.acceptance.subprocess.run", timeout)
    assert command(("-m", "pytest"))["status"] == "TIMEOUT"


def test_runner_default_and_suite_selection(monkeypatch, capsys):
    from flowlens.testing import acceptance

    seen = []

    def fake_command(args):
        seen.append(args)
        return {"status": "FAIL", "exit_code": 9}

    monkeypatch.setattr(acceptance, "command", fake_command)
    monkeypatch.setattr("sys.argv", ["acceptance", "--suite"])
    with pytest.raises(SystemExit) as exc:
        acceptance.main()
    assert exc.value.code == 1
    assert seen[-2:] == [
        ("-m", "pytest", "tests/analysis", "tests/contracts", "--track", "B", "-q"),
        ("-m", "pytest", "tests/contracts", "--track", "A", "-q"),
    ]
    import json

    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "failed"
    assert result["suite"] == "RUN"
