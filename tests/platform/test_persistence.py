"""Real platform persistence tests, always on disposable database paths."""

import importlib
import json
import sqlite3
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from flowlens.contracts.models import Evidence, RequestContext, SourceEvent
from flowlens.core.errors import ContractError
from flowlens.core.modules import MigrationSpec

ROOT = Path(__file__).resolve().parents[2]


def storage():
    return importlib.import_module("flowlens.storage.sqlite.database")


def migrations():
    return importlib.import_module("flowlens.storage.sqlite.schema").PLATFORM_MIGRATIONS


def context():
    return RequestContext.model_validate_json(
        (ROOT / "contracts/examples/context.json").read_text()
    )


def event():
    return SourceEvent.model_validate_json(
        json.dumps(json.loads((ROOT / "contracts/examples/events.json").read_text())[0])
    )


def seed(uow, ctx):
    uow.connection.execute("INSERT INTO platform_sessions(id) VALUES (?)", (str(ctx.session_id),))
    uow.connection.execute(
        "INSERT INTO platform_revisions(session_id,revision,input_hash) VALUES (?,?,?)",
        (str(ctx.session_id), ctx.input_revision, ctx.input_hash),
    )
    if ctx.analysis_run_id:
        uow.connection.execute(
            "INSERT INTO platform_runs(session_id,id,revision) VALUES (?,?,?)",
            (str(ctx.session_id), str(ctx.analysis_run_id), ctx.input_revision),
        )


def test_fresh_schema_has_platform_tables_only_and_constraints(tmp_path):
    with storage().Database(tmp_path / "platform.db") as db:
        with db.begin() as uow:
            names = {row[0] for row in uow.connection.execute("SELECT name FROM sqlite_master")}
            assert {
                "platform_accounts",
                "platform_grants",
                "platform_sessions",
                "platform_revisions",
                "platform_sources",
                "platform_assets",
                "platform_runs",
                "platform_jobs",
                "platform_attempts",
                "platform_receipts",
                "platform_records",
                "platform_evidence",
                "platform_audit",
                "platform_events",
                "platform_replay",
                "platform_artifacts",
            } <= names
            assert not any(name.startswith("analysis_") for name in names)
            assert uow.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert uow.connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            with pytest.raises(sqlite3.IntegrityError):
                uow.connection.execute(
                    "INSERT INTO platform_revisions VALUES ('missing',1,?)", ("a" * 64,)
                )


def test_upgrade_preserves_rows_and_checksums_prevent_drift(tmp_path):
    path = tmp_path / "upgrade.db"
    specs = migrations()
    with storage().Database(path, migrations=specs[:1]) as db:
        with db.begin() as uow:
            seed(uow, context())
            uow.commit()
    with storage().Database(path) as db:
        with db.begin() as uow:
            assert uow.connection.execute("SELECT id FROM platform_sessions").fetchone()[0] == str(
                context().session_id
            )
    with pytest.raises(ValueError, match="migration"):
        storage().Database(
            path, migrations=(replace(specs[0], sql=specs[0].sql + "\n-- changed"), *specs[1:])
        )
    with pytest.raises(ValueError, match="migration"):
        storage().Database(path, migrations=specs[:1])
    # Startup failures release ownership so a corrected manifest can open normally.
    with storage().Database(path):
        pass


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE platform_broken(id TEXT); INVALID SQL;",
        "CREATE TABLE platform_broken(id TEXT); COMMIT;",
        "PRAGMA foreign_keys=OFF;",
    ],
)
def test_failed_migration_is_atomic_and_transaction_control_is_denied(tmp_path, sql):
    path = tmp_path / "failure.db"
    with storage().Database(path):
        pass
    bad = MigrationSpec("platform.9001", "A", ("platform.0002",), sql)
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        storage().Database(path, migrations=(*migrations(), bad))
    with storage().Database(path) as db:
        with db.begin() as uow:
            assert (
                uow.connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='platform_broken'"
                ).fetchone()
                is None
            )
            assert uow.connection.execute(
                "SELECT COUNT(*) FROM platform_schema_migrations"
            ).fetchone()[0] == len(migrations())


def test_migration_statement_parser_handles_semicolons_and_triggers(tmp_path):
    extra = MigrationSpec(
        "platform.9001",
        "A",
        ("platform.0002",),
        """
        CREATE TABLE platform_probe(value TEXT);
        CREATE TABLE platform_probe_log(value TEXT);
        CREATE TRIGGER platform_probe_insert AFTER INSERT ON platform_probe BEGIN
          INSERT INTO platform_probe_log VALUES ('first;second');
          INSERT INTO platform_probe_log VALUES (NEW.value);
        END;
        INSERT INTO platform_probe VALUES ('value;with;semicolons');
    """,
    )
    with storage().Database(tmp_path / "triggers.db", migrations=(*migrations(), extra)) as db:
        with db.begin() as uow:
            assert [
                row[0] for row in uow.connection.execute("SELECT value FROM platform_probe_log")
            ] == ["first;second", "value;with;semicolons"]


def test_legacy_unversioned_db_is_not_modified(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE old_sessions(id TEXT)")
    path.chmod(0o600)
    with pytest.raises(ValueError, match="unversioned"):
        storage().Database(path)
    with sqlite3.connect(path) as conn:
        assert (
            conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'platform_%'").fetchall()
            == []
        )


def test_database_owner_lock_across_processes_and_release(tmp_path):
    path = tmp_path / "owner.db"
    with storage().Database(path):
        with pytest.raises(RuntimeError, match="owner"):
            storage().Database(path)
        script = (
            "from pathlib import Path; "
            "from flowlens.storage.sqlite.database import Database; "
            "Database(Path(__import__('sys').argv[1]))"
        )
        proc = subprocess.run(
            [sys.executable, "-c", script, str(path)], capture_output=True, text=True, timeout=10
        )
        assert proc.returncode != 0
        assert "owner" in proc.stderr
    with storage().Database(path):
        pass
    assert path.stat().st_mode & 0o077 == 0


def test_repository_scope_and_lifecycle(tmp_path):
    ctx = context()
    # Source events are source-scoped; the fixture has no analysis run.
    ctx = ctx.model_copy(update={"analysis_run_id": event().analysis_run_id})
    with storage().Database(tmp_path / "records.db") as db:
        with db.begin() as uow:
            seed(uow, ctx)
            repo = uow.repository("source_events")
            assert repo.append(ctx, event()) == event().id
            uow.commit()
        with pytest.raises(RuntimeError, match="closed"):
            repo.get(ctx, event().id)
        with db.begin() as uow:
            assert uow.repository("source_events").get(ctx, event().id) == event()
            wrong = ctx.model_copy(update={"session_id": UUID(int=99)})
            with pytest.raises(ContractError, match="ACCESS_DENIED"):
                uow.repository("source_events").get(wrong, event().id)
            with pytest.raises(ContractError, match="ACCESS_DENIED"):
                uow.repository("source_events").append(wrong, event())
            with pytest.raises(ContractError, match="ACCESS_DENIED"):
                uow.repository("source_events").get(
                    ctx.model_copy(update={"capabilities": []}), event().id
                )
            with pytest.raises(ContractError, match="VERSION_CONFLICT"):
                uow.repository("source_events").append(ctx, event())
            with pytest.raises(ValueError):
                uow.repository("analysis")


def test_unknown_session_and_cross_run_are_not_auto_created(tmp_path):
    with storage().Database(tmp_path / "scope.db") as db:
        ctx = context().model_copy(update={"analysis_run_id": event().analysis_run_id})
        with db.begin() as uow:
            with pytest.raises(sqlite3.IntegrityError):
                uow.repository("source_events").append(ctx, event())
            seed(uow, ctx)
            wrong = ctx.model_copy(update={"analysis_run_id": UUID(int=99)})
            with pytest.raises(ContractError, match="ACCESS_DENIED"):
                uow.repository("source_events").append(wrong, event())


def test_all_writes_and_callbacks_roll_back_on_exception_or_missing_commit(tmp_path):
    with storage().Database(tmp_path / "rollback.db") as db:
        ctx = context().model_copy(update={"analysis_run_id": event().analysis_run_id})
        with db.begin() as uow:
            seed(uow, ctx)
            uow.commit()
        published = []
        for fault in (False, True):
            try:
                with db.begin() as uow:
                    uow.repository("source_events").append(ctx, event())
                    uow.audit(ctx, "APPEND_EVENT", event().id)
                    uow.enqueue_event(ctx, event())
                    uow.after_commit(lambda: published.append("event"))
                    if fault:
                        raise RuntimeError("injected")
            except RuntimeError:
                assert fault
        with db.begin() as uow:
            for table in ("platform_records", "platform_audit", "platform_events"):
                assert uow.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert published == []


def test_commit_callbacks_observe_durable_state_and_failures_do_not_rollback(tmp_path):
    with storage().Database(tmp_path / "callbacks.db") as db:
        ctx = context().model_copy(update={"analysis_run_id": event().analysis_run_id})
        with db.begin() as uow:
            seed(uow, ctx)
            uow.commit()
        observed = []

        def publish():
            with db.begin() as reader:
                observed.append(reader.repository("source_events").get(ctx, event().id))

        def fail():
            raise RuntimeError("private SQL exception")

        with pytest.raises(RuntimeError, match="publication"):
            with db.begin() as uow:
                uow.repository("source_events").append(ctx, event())
                uow.after_commit(fail)
                uow.after_commit(publish)
                uow.commit()
        assert observed == [event()]
        with db.begin() as uow:
            assert uow.repository("source_events").get(ctx, event().id) == event()


def test_sequences_are_session_scoped_and_durable(tmp_path):
    path = tmp_path / "events.db"
    ctx = context().model_copy(update={"analysis_run_id": event().analysis_run_id})
    with storage().Database(path) as db:
        with db.begin() as uow:
            seed(uow, ctx)
            assert uow.enqueue_event(ctx, event()) == 1
            assert uow.enqueue_event(ctx, event()) == 2
            uow.commit()
    with storage().Database(path) as db:
        with db.begin() as uow:
            assert uow.enqueue_event(ctx, event()) == 3
            uow.commit()


def test_host_owns_db_only_during_lifespan_and_readiness_stays_incomplete(tmp_path):
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    config = HostSettings(profile="test", database_path=tmp_path / "host.db")
    app = create_host(config)
    assert not config.database_path.exists()
    with TestClient(app) as client:
        assert app.state.transactions is not None
        with pytest.raises(RuntimeError, match="owner"):
            storage().Database(config.database_path)
        assert client.get("/ready").status_code == 503
        assert "database_path" not in client.get("/release.json").text
    with storage().Database(config.database_path):
        pass


def test_evidence_fk_and_receipt_uniqueness(tmp_path):
    ctx = context()
    evidence = Evidence.model_validate_json(
        json.dumps(
            json.loads((ROOT / "contracts/examples/transcript.json").read_text())["evidence"][0]
        )
    )
    ctx = ctx.model_copy(update={"analysis_run_id": evidence.analysis_run_id})
    with storage().Database(tmp_path / "evidence.db") as db:
        with db.begin() as uow:
            seed(uow, ctx)
            with pytest.raises(sqlite3.IntegrityError):
                uow.repository("evidence").append(ctx, evidence)
            uow.connection.execute(
                "INSERT INTO platform_sources VALUES (?,?,?,?,?)",
                (
                    str(ctx.session_id),
                    str(evidence.source_id),
                    ctx.input_revision,
                    evidence.source_hash,
                    "{}",
                ),
            )
            uow.repository("evidence").append(ctx, evidence)
            assert uow.repository("evidence").get(ctx, evidence.id) == evidence
            # Receipts cannot exist outside the scoped attempt hierarchy.
            with pytest.raises(sqlite3.IntegrityError):
                uow.connection.execute(
                    "INSERT INTO platform_receipts VALUES (?,?,?,?)",
                    (str(ctx.session_id), "missing", "a" * 64, "{}"),
                )
            uow.connection.execute(
                "INSERT INTO platform_jobs VALUES (?,?,?,?)",
                (str(ctx.session_id), "job", str(ctx.analysis_run_id), ctx.input_revision),
            )
            uow.connection.execute(
                "INSERT INTO platform_attempts VALUES (?,?,?,?)",
                (str(ctx.session_id), "attempt", "job", "lease"),
            )
            receipt = (str(ctx.session_id), "attempt", "a" * 64, "{}")
            uow.connection.execute("INSERT INTO platform_receipts VALUES (?,?,?,?)", receipt)
            with pytest.raises(sqlite3.IntegrityError):
                uow.connection.execute("INSERT INTO platform_receipts VALUES (?,?,?,?)", receipt)
            uow.commit()


def test_failed_commit_rolls_back_and_never_publishes(tmp_path):
    spec = MigrationSpec(
        "platform.9001",
        "A",
        ("platform.0002",),
        """
        CREATE TABLE platform_deferred(id TEXT REFERENCES platform_sessions(id)
            DEFERRABLE INITIALLY DEFERRED);
    """,
    )
    with storage().Database(tmp_path / "deferred.db", migrations=(*migrations(), spec)) as db:
        calls = []
        with pytest.raises(sqlite3.IntegrityError):
            with db.begin() as uow:
                uow.connection.execute("INSERT INTO platform_deferred VALUES ('absent')")
                uow.after_commit(lambda: calls.append("published"))
                uow.commit()
        assert calls == []
        with db.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_deferred").fetchone()[0] == 0
            )


def test_nested_and_closed_uow_and_unsafe_paths_fail(tmp_path):
    path = tmp_path / "closed.db"
    with storage().Database(path) as db:
        with db.begin() as uow:
            with pytest.raises(RuntimeError, match="nested"):
                with db.begin():
                    pass
            uow.rollback()
            with pytest.raises(RuntimeError, match="closed"):
                uow.commit()
    with pytest.raises(RuntimeError, match="closed"):
        with db.begin():
            pass
    alias = tmp_path / "alias.db"
    alias.symlink_to(path)
    with pytest.raises(ValueError, match="symlink"):
        storage().Database(alias)
    path.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        storage().Database(path)


def test_host_storage_failure_is_sanitized_and_does_not_mark_ready(tmp_path):
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    path = tmp_path / "private-password.db"
    path.write_text("not a database")
    path.chmod(0o600)
    app = create_host(HostSettings(database_path=path))
    with pytest.raises(RuntimeError, match="storage startup") as failure:
        with TestClient(app):
            pass
    assert "private-password" not in str(failure.value)
    assert app.state.transactions is None


def test_concurrent_transactions_have_unique_durable_sequence(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    ctx = context().model_copy(update={"analysis_run_id": event().analysis_run_id})
    with storage().Database(tmp_path / "threads.db") as db:
        with db.begin() as uow:
            seed(uow, ctx)
            uow.commit()

        def append(_):
            with db.begin() as uow:
                sequence = uow.enqueue_event(ctx, event())
                uow.commit()
                return sequence

        with ThreadPoolExecutor(max_workers=4) as pool:
            assert sorted(pool.map(append, range(12))) == list(range(1, 13))


def test_repository_factory_injection_uses_same_transaction_and_guard(tmp_path):
    from flowlens.storage.sqlite.repository import PlatformRepository

    # A test-owned adapter checks the injection boundary, not a real B implementation.
    def factory(connection, guard):
        return PlatformRepository(connection, "source_events", guard)

    ctx = context().model_copy(update={"analysis_run_id": event().analysis_run_id})
    with storage().Database(tmp_path / "extension.db", repositories={"analysis": factory}) as db:
        with db.begin() as uow:
            seed(uow, ctx)
            repository = uow.repository("analysis")
            repository.append(ctx, event())
            uow.commit()
        with pytest.raises(RuntimeError, match="closed"):
            repository.get(ctx, event().id)
        with db.begin() as uow:
            assert uow.repository("source_events").get(ctx, event().id) == event()


def test_environment_database_path_remains_local_and_private(tmp_path):
    from flowlens.core.host_config import HostSettings

    config = HostSettings.from_environment({"FLOWLENS_DB_PATH": str(tmp_path / "env.db")})
    assert config.database_path == tmp_path / "env.db"
    for value in ("", "sqlite://private-password"):
        with pytest.raises(ValueError):
            HostSettings.from_environment({"FLOWLENS_DB_PATH": value})
