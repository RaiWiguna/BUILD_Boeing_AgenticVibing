"""Disposable B01 acceptance, without Package A implementation imports."""

import ast
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from uuid import UUID

import pytest
from flowlens.analysis.config import AnalysisConfig
from flowlens.analysis.module import AnalysisFoundation, register_analysis
from flowlens.analysis.repository import NAMESPACE
from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
from flowlens.contracts.models import JobResult, RequestContext, TranscriptSegment
from flowlens.core.errors import ContractError
from flowlens.core.modules import MigrationSpec, ModuleRegistry, order_migrations
from flowlens.testing.analysis import PLATFORM_REFERENCE, AnalysisReferenceTransactions
from flowlens.testing.harness import FakePlatform
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def context():
    return RequestContext.model_validate_json(
        (ROOT / "contracts/examples/context.json").read_text()
    )


@pytest.fixture
def foundation(tmp_path, context):
    transactions = AnalysisReferenceTransactions(tmp_path / "b01.db")
    transactions.seed(context)
    return transactions, AnalysisFoundation(AnalysisConfig(profile="test"), transactions)


def counts(transactions):
    with closing(sqlite3.connect(transactions.path)) as conn:
        return tuple(
            conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in (
                "analysis_configurations",
                "reference_events",
                "reference_audit",
                "reference_records",
            )
        )


def test_config_and_registration(foundation):
    transactions, _ = foundation
    config = AnalysisConfig(profile="test")
    assert config.digest() == AnalysisConfig.model_validate_json(config.model_dump_json()).digest()
    assert config.digest() != AnalysisConfig().digest()
    for fields in ({"profile": "MOCK"}, {"pipeline_enabled": True}, {"credential": "secret"}):
        with pytest.raises(ValidationError):
            AnalysisConfig(**fields)
    with pytest.raises(ValidationError):
        config.profile = "production"
    registration = register_analysis(config, transactions)
    assert registration.contract_version == "1.0.0"
    assert registration.mock
    assert registration.migrations == ANALYSIS_MIGRATIONS
    assert registration.repositories.keys() == {NAMESPACE}
    assert registration.inventory_namespaces == (NAMESPACE,)
    assert registration.purge_handler
    assert registration.readiness() is False
    assert registration.snapshot_reader is None
    assert registration.job_handlers == {}
    assert registration.routes == ()
    ModuleRegistry(profile="test").register(registration)
    with pytest.raises(ValueError, match="MOCK"):
        ModuleRegistry(profile="production").register(registration)
    with pytest.raises(ValueError, match="MOCK"):
        register_analysis(AnalysisConfig(profile="production"), transactions)


def test_upgrade_order_and_immutable_manifest(tmp_path, context):
    transactions = AnalysisReferenceTransactions(tmp_path / "upgrade.db", install_analysis=False)
    transactions.seed(context)
    manifest = (*ANALYSIS_MIGRATIONS, PLATFORM_REFERENCE)
    assert [item.id for item in order_migrations(list(manifest))] == [
        "platform.0001",
        "analysis.0001",
    ]
    transactions.migrate(manifest)
    transactions.migrate(manifest)
    with transactions.begin() as uow:
        assert uow.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert uow.conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert uow.conn.execute("SELECT id FROM platform_runs").fetchone()[0] == str(
            context.analysis_run_id
        )
    with pytest.raises(ValueError, match="downgrade"):
        transactions.migrate((PLATFORM_REFERENCE,))
    with pytest.raises(ValueError, match="changed"):
        transactions.migrate(
            (
                PLATFORM_REFERENCE,
                MigrationSpec("analysis.0001", "B", ("platform.0001",), "SELECT 1;"),
            )
        )
    with pytest.raises(ValueError, match="dependency"):
        transactions.migrate(ANALYSIS_MIGRATIONS)


def test_migration_batch_failure_is_atomic(tmp_path):
    transactions = AnalysisReferenceTransactions(tmp_path / "failure.db", install_analysis=False)
    bad = MigrationSpec("analysis.bad", "B", ("analysis.0001",), "INVALID SQL;")
    with pytest.raises(sqlite3.OperationalError):
        transactions.migrate((PLATFORM_REFERENCE, *ANALYSIS_MIGRATIONS, bad))
    with transactions.begin() as uow:
        assert not uow.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='analysis_configurations'"
        ).fetchall()
        assert [row[0] for row in uow.conn.execute("SELECT id FROM mock_migrations")] == [
            "platform.0001"
        ]


def test_shared_uow_evidence_audit_event_rollback_and_publication(foundation, context):
    transactions, service = foundation
    segment = TranscriptSegment.model_validate_json(
        (ROOT / "contracts/examples/transcript.json").read_text()
    )
    evidence_service = FakePlatform([], [segment])
    published = []

    def publish():
        with transactions.begin() as uow:
            assert len(uow.repository(NAMESPACE).inventory(context)) == 1
        published.append("committed")

    for commit in (False, True):
        with transactions.begin() as uow:
            identifier = service.configure(context, uow)
            evidence_id = evidence_service.register(context, segment.evidence[0], uow)
            assert uow.repository(NAMESPACE).get(context, identifier).id == identifier
            assert uow.repository("evidence").get(context, evidence_id) == segment.evidence[0]
            uow.after_commit(publish)
            assert published == []
            if commit:
                uow.commit()
        assert counts(transactions) == ((1, 1, 1, 1) if commit else (0, 0, 0, 0))
    assert published == ["committed"]


@pytest.mark.parametrize("failure", ["audit", "event", "exception"])
def test_partial_domain_failure_rolls_back(foundation, context, monkeypatch, failure):
    transactions, service = foundation
    with pytest.raises(RuntimeError):
        with transactions.begin() as uow:

            def fail(*args):
                raise RuntimeError("injected")

            if failure != "exception":
                monkeypatch.setattr(uow, "audit" if failure == "audit" else "enqueue_event", fail)
            service.configure(context, uow)
            raise RuntimeError("injected after domain/audit/event")
    assert counts(transactions) == (0, 0, 0, 0)


@pytest.mark.parametrize(
    "update",
    [
        {"session_id": UUID(int=91)},
        {"analysis_run_id": UUID(int=92)},
        {"input_revision": 2},
        {"input_hash": "f" * 64},
        {"capabilities": []},
        {"analysis_run_id": None},
    ],
)
def test_repository_read_scope(foundation, context, update):
    transactions, service = foundation
    with transactions.begin() as uow:
        identifier = service.configure(context, uow)
        uow.commit()
    with transactions.begin() as uow:
        with pytest.raises(ContractError):
            uow.repository(NAMESPACE).get(context.model_copy(update=update), identifier)


def test_write_scope_hash_duplicates_and_lifecycle(foundation, context):
    transactions, service = foundation
    with transactions.begin() as uow:
        identifier = service.configure(context, uow)
        repository = uow.repository(NAMESPACE)
        record = repository.get(context, identifier)
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            repository.append(context, record)
        for changed in (
            record.model_copy(update={"session_id": UUID(int=99)}),
            record.model_copy(update={"input_hash": "f" * 64}),
        ):
            with pytest.raises(ContractError):
                repository.append(context, changed)
        with pytest.raises(ValidationError):
            repository.append(context, record.model_copy(update={"config_hash": "f" * 64}))
        with pytest.raises(ContractError):
            service.configure(context.model_copy(update={"input_hash": "f" * 64}), uow)
        uow.commit()
    with pytest.raises(RuntimeError, match="closed"):
        repository.get(context, identifier)
    assert len(service.inventory(context)) == 1


def test_fk_and_check_constraints(foundation, context):
    transactions, service = foundation
    with transactions.begin() as uow:
        with pytest.raises(sqlite3.IntegrityError):
            service.configure(context.model_copy(update={"analysis_run_id": UUID(int=99)}), uow)
        for values in (
            (
                "x",
                str(context.session_id),
                str(context.analysis_run_id),
                0,
                "a" * 64,
                "b" * 64,
                "{}",
            ),
            ("x", "absent", "absent", 1, "a" * 64, "b" * 64, "{}"),
            (
                "x",
                str(context.session_id),
                str(context.analysis_run_id),
                1,
                "short",
                "b" * 64,
                "{}",
            ),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                uow.conn.execute(
                    "INSERT INTO analysis_configurations VALUES (?,?,?,?,?,?,?)", values
                )


def test_inventory_purge_scope_and_rollback(foundation, context):
    transactions, service = foundation
    other = context.model_copy(update={"analysis_run_id": UUID(int=99)})
    transactions.seed(other)
    for ctx in (context, other):
        with transactions.begin() as uow:
            service.configure(ctx, uow)
            uow.commit()
    assert len(service.inventory(context)) == len(service.inventory(other)) == 1
    with transactions.begin() as uow:
        with pytest.raises(ContractError):
            service.purge(context, uow)
    admin = context.model_copy(update={"capabilities": ["read", "admin"]})
    with transactions.begin() as uow:
        service.purge(admin, uow)
    assert len(service.inventory(context)) == 1
    with transactions.begin() as uow:
        service.purge(admin, uow)
        uow.commit()
    assert service.inventory(context) == []
    assert len(service.inventory(other)) == 1


def test_unavailable_pipeline_rejects_results(foundation, context):
    transactions, service = foundation
    result = JobResult.model_validate_json(
        (ROOT / "contracts/examples/job_result.json").read_text()
    )
    with pytest.raises(ContractError, match="NOT_EVALUABLE"):
        service.validate(context, result, FakePlatform([]))
    with transactions.begin() as uow:
        with pytest.raises(ContractError, match="NOT_EVALUABLE"):
            service.accept(context, result, uow)
    with pytest.raises(ContractError, match="NOT_EVALUABLE"):
        service.snapshot(context)
    assert counts(transactions) == (0, 0, 0, 0)


def test_publication_failure_keeps_durable_configuration(foundation, context):
    transactions, service = foundation

    def fail_publication():
        raise RuntimeError("transport unavailable")

    with pytest.raises(RuntimeError, match="transport unavailable"):
        with transactions.begin() as uow:
            service.configure(context, uow)
            uow.after_commit(fail_publication)
            uow.commit()
    assert counts(transactions) == (1, 1, 1, 0)
    reopened = AnalysisReferenceTransactions(transactions.path)
    recovered = AnalysisFoundation(AnalysisConfig(profile="test"), reopened)
    assert recovered.inventory(context) == service.inventory(context)


def test_write_permission_and_parent_hash_are_checked(foundation, context):
    transactions, service = foundation
    with transactions.begin() as uow:
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            service.configure(context.model_copy(update={"capabilities": ["read"]}), uow)
        # Server context alone cannot override the authoritative reference revision hash.
        uow.conn.execute("UPDATE platform_revisions SET input_hash=?", ("f" * 64,))
        with pytest.raises(ContractError, match="SOURCE_REVISION_CHANGED"):
            service.configure(context, uow)
    assert counts(transactions) == (0, 0, 0, 0)


def test_runtime_import_boundary():
    allowed = ("flowlens.analysis", "flowlens.contracts", "flowlens.core")
    for path in (ROOT / "backend/flowlens/analysis").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            elif isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            for name in names:
                assert not name.startswith("evaluation"), (path, name)
                if name.startswith("flowlens"):
                    assert name.startswith(allowed), (path, name)


def test_standalone_b01_cleanup():
    proc = subprocess.run(
        [sys.executable, "-m", "flowlens.testing.analysis"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["profile"] == "MOCK"
    assert result["pipeline_ready"] is False
    assert result["provider_calls"] == 0
    assert result["database"] == "disposable-cleaned"
