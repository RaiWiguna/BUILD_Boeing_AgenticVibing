import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("track", ["A", "B"])
def test_standalone_harness_cli(track):
    proc = subprocess.run(
        [sys.executable, "-m", "flowlens.testing", "--track", track],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    status = json.loads(proc.stdout)
    assert status["track"] == track
    assert status["profile"] == "MOCK"
    assert status["provider_calls"] == 0


def test_no_runtime_import_of_evaluator_truth_or_worker_sqlite():
    import ast

    for file in (ROOT / "backend/flowlens").rglob("*.py"):
        tree = ast.parse(file.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not any(name.startswith("evaluation") for name in names), file
            if "workers" in file.parts:
                assert not any(
                    name.startswith(("sqlite3", "flowlens.storage", "flowlens.testing"))
                    for name in names
                ), file


def test_registry_migration_dependencies_are_ordered():
    m = importlib.import_module("flowlens.core.modules")
    ordered = m.order_migrations(
        [
            m.MigrationSpec("analysis.0001", "B", ("platform.0001",), "SELECT 1;"),
            m.MigrationSpec("platform.0001", "A", (), "SELECT 1;"),
        ]
    )
    assert [item.id for item in ordered] == ["platform.0001", "analysis.0001"]


def test_public_schema_does_not_include_truth_or_secret_fields():
    m = importlib.import_module("flowlens.contracts.models")
    blocked = {
        "truth",
        "evaluation_label",
        "private_schedule",
        "api_key",
        "secret",
        "raw_path",
        "command",
        "execute",
        "sql",
    }
    for model in m.PUBLIC_MODELS:
        assert not blocked.intersection(model.model_fields)


def test_module_registration_executes_transaction_snapshot_and_purge(tmp_path):
    m = importlib.import_module("flowlens.contracts.models")
    h = importlib.import_module("flowlens.testing.harness")
    ctx = m.RequestContext.model_validate_json(
        (ROOT / "contracts/examples/context.json").read_text()
    )
    result = m.JobResult.model_validate_json(
        (ROOT / "contracts/examples/job_result.json").read_text()
    )
    bundle = h.build_harness("A", db_path=tmp_path / "module.db")
    registration = bundle.registry.modules[0]
    with bundle.transactions.begin() as uow:
        registration.job_handlers["MOCK"](ctx, result, uow)
        uow.commit()
    assert registration.snapshot_reader(ctx).quality == "MISSING"
    with bundle.transactions.begin() as uow:
        with pytest.raises(importlib.import_module("flowlens.core.errors").ContractError):
            registration.purge_handler(ctx, uow)
        admin = ctx.model_copy(update={"capabilities": [*ctx.capabilities, "admin"]})
        registration.purge_handler(admin, uow)
        uow.commit()
