"""Synthetic archive matching storage.py at pre-reset commit 2660222."""

import importlib
import json
import sqlite3
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.storage.sqlite.database import Database


def legacy():
    return importlib.import_module("flowlens.storage.sqlite.legacy")


def archive(path):
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE sessions(id TEXT PRIMARY KEY,
                metadata TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE events(session_id TEXT NOT NULL REFERENCES sessions(id),
                ordinal INTEGER NOT NULL,
                data TEXT NOT NULL, PRIMARY KEY(session_id,ordinal));
            CREATE TABLE frames(session_id TEXT NOT NULL REFERENCES sessions(id),
                sim_ms INTEGER NOT NULL,
                sequence INTEGER NOT NULL, public TEXT NOT NULL, private TEXT NOT NULL,
                PRIMARY KEY(session_id,sim_ms));
            CREATE TABLE commands(session_id TEXT NOT NULL REFERENCES sessions(id),
                command_id TEXT NOT NULL,
                request TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(session_id,command_id));
        """)
        for identifier, status in (("abcdef123456", "RUNNING"), ("fedcba654321", "ENDED")):
            connection.execute(
                "INSERT INTO sessions VALUES (?,?,?)",
                (
                    identifier,
                    json.dumps({"id": identifier, "kind": "training", "seed": 42}),
                    status,
                ),
            )
            connection.execute(
                "INSERT INTO events VALUES (?,?,?)",
                (
                    identifier,
                    1,
                    json.dumps(
                        {
                            "session_id": identifier,
                            "ordinal": 1,
                            "sim_ms": 0,
                            "type": "SESSION_CREATED",
                        }
                    ),
                ),
            )
            connection.execute(
                "INSERT INTO frames VALUES (?,?,?,?,?)",
                (
                    identifier,
                    0,
                    1,
                    json.dumps({"session_id": identifier, "sim_ms": 0, "sequence": 1}),
                    '{ "simulator": {"mobiles": []}, "event_ordinal": 1 }',
                ),
            )
            connection.execute(
                "INSERT INTO commands VALUES (?,?,?,?)",
                (
                    identifier,
                    "command-1",
                    '{ "command": {"type":"START"}, "role":"instructor" }',
                    json.dumps(
                        {"session_id": identifier, "command_id": "command-1", "revision": 1}
                    ),
                ),
            )
    path.chmod(0o600)
    return path


def test_migration_preserves_original_ids_json_and_private_boundary(tmp_path):
    source = archive(tmp_path / "old.db")
    before = source.read_bytes()
    with Database(tmp_path / "new.db") as target:
        summary = legacy().import_archive(source, target)
        assert summary.counts == {"sessions": 2, "events": 2, "frames": 2, "commands": 2}
        with target.begin() as uow:
            rows = uow.connection.execute(
                "SELECT legacy_id,original_status,runtime_status "
                "FROM platform_legacy_sessions ORDER BY legacy_id"
            ).fetchall()
            assert [tuple(row) for row in rows] == [
                ("abcdef123456", "RUNNING", "INTERRUPTED"),
                ("fedcba654321", "ENDED", "ENDED"),
            ]
            assert (
                uow.connection.execute(
                    "SELECT command_id FROM platform_legacy_commands LIMIT 1"
                ).fetchone()[0]
                == "command-1"
            )
            assert (
                uow.connection.execute(
                    "SELECT ordinal FROM platform_legacy_events LIMIT 1"
                ).fetchone()[0]
                == 1
            )
            assert uow.connection.execute(
                "SELECT sim_ms,sequence FROM platform_legacy_frames LIMIT 1"
            ).fetchone()[:] == (0, 1)
            private = uow.connection.execute(
                "SELECT private FROM platform_legacy_private_frames LIMIT 1"
            ).fetchone()[0]
            assert private == '{ "simulator": {"mobiles": []}, "event_ordinal": 1 }'
            public_columns = [
                row[1]
                for row in uow.connection.execute("PRAGMA table_info(platform_legacy_frames)")
            ]
            assert "private" not in public_columns
            # Quarantine payloads never become observer events or provider-ready source records.
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_records").fetchone()[0] == 0
            )
            assert uow.connection.execute("SELECT COUNT(*) FROM platform_events").fetchone()[0] == 0
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_accounts").fetchone()[0] == 0
            )
    assert source.read_bytes() == before


def test_identical_retry_is_idempotent_changed_legacy_id_conflicts(tmp_path):
    source = archive(tmp_path / "old.db")
    with Database(tmp_path / "new.db") as target:
        first = legacy().import_archive(source, target)
        assert legacy().import_archive(source, target) == first
        with sqlite3.connect(source) as conn:
            conn.execute("UPDATE sessions SET status='PAUSED' WHERE id='abcdef123456'")
        with pytest.raises(ValueError, match="conflict"):
            legacy().import_archive(source, target)
        with target.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_legacy_imports").fetchone()[0]
                == 1
            )


@pytest.mark.parametrize(
    "mutation",
    [
        "ALTER TABLE sessions ADD COLUMN unexpected TEXT",
        "ALTER TABLE events RENAME TO events_original",
        "UPDATE events SET data='not-json'",
        'UPDATE events SET data=\'{"ordinal":99,"sim_ms":0}\'',
        'UPDATE frames SET public=\'{"sim_ms":-1,"sequence":1}\'',
        'UPDATE commands SET response=\'{"command_id":"other"}\'',
        'UPDATE sessions SET metadata=\'{"id":"other"}\'',
        "UPDATE sessions SET status='UNKNOWN'",
        'UPDATE sessions SET metadata=\'{"id":"abcdef123456","id":"abcdef123456"}\' '
        "WHERE id='abcdef123456'",
        'UPDATE sessions SET metadata=\'{"id":"abcdef123456","x":1e999}\' '
        "WHERE id='abcdef123456'",
        "INSERT INTO events VALUES ('orphan',1,'{\"ordinal\":1,\"sim_ms\":0}')",
        'UPDATE sessions SET metadata=\'{"id":"abcdef123456","x":NaN}\' WHERE id=\'abcdef123456\'',
    ],
)
def test_unsupported_malformed_or_inconsistent_archive_has_no_import_writes(tmp_path, mutation):
    source = archive(tmp_path / "bad.db")
    with sqlite3.connect(source) as conn:
        conn.execute(mutation)
    with Database(tmp_path / "target.db") as target:
        with pytest.raises(ValueError):
            legacy().import_archive(source, target)
        with target.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_legacy_sessions").fetchone()[
                    0
                ]
                == 0
            )


def test_import_commit_failure_rolls_back_all_archive_tables(tmp_path):
    source = archive(tmp_path / "old.db")
    with Database(tmp_path / "target.db") as target:
        with target.begin() as uow:
            uow.connection.execute("""CREATE TRIGGER platform_test_fault BEFORE INSERT
                ON platform_legacy_commands BEGIN SELECT RAISE(ABORT,'injected'); END;""")
            uow.commit()
        with pytest.raises(sqlite3.IntegrityError):
            legacy().import_archive(source, target)
        with target.begin() as uow:
            for table in (
                "platform_sessions",
                "platform_legacy_sessions",
                "platform_legacy_events",
                "platform_legacy_frames",
                "platform_legacy_private_frames",
                "platform_legacy_commands",
                "platform_legacy_imports",
            ):
                assert uow.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_wal_snapshot_includes_committed_rows_and_same_file_is_rejected(tmp_path):
    source = archive(tmp_path / "wal.db")
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute(
            "INSERT INTO events VALUES (?,?,?)",
            ("abcdef123456", 2, '{"ordinal":2,"sim_ms":100,"type":"SESSION_STARTED"}'),
        )
        writer.commit()
        with Database(tmp_path / "new.db") as target:
            assert legacy().import_archive(source, target).counts["events"] == 3
            with pytest.raises(ValueError):
                legacy().import_archive(target.path, target)


def test_legacy_credentials_and_mutating_routes_are_not_restored():
    with pytest.raises(ValueError):
        HostSettings.from_environment({"FLOWLENS_OPERATOR_KEY": "synthetic-old-key"})
    with TestClient(create_host(HostSettings(profile="test"))) as client:
        for path in (
            "/api/v1/auth/operator",
            "/api/v1/sessions/abcdef123456/commands",
            "/api/v1/sessions/abcdef123456/seats",
        ):
            response = client.post(
                path,
                json={"key": "synthetic-old-key"},
                headers={"Authorization": "Bearer synthetic-old-token"},
            )
            assert response.status_code == 404
            assert "synthetic-old" not in response.text


def test_migration_cli_synthetic_smoke_and_sanitized_failure(tmp_path):
    source = archive(tmp_path / "old.db")
    target = tmp_path / "new.db"
    module = "flowlens.cli.migrate_archive"
    proc = subprocess.run(
        [sys.executable, "-m", module, "--source", str(source), "--target", str(target)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["counts"]["sessions"] == 2
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            module,
            "--source",
            str(tmp_path / "private-password.db"),
            "--target",
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode != 0
    assert "private-password" not in proc.stderr
