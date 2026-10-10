"""Actual subprocess maintenance on initialized empty storage; no private output leaks."""

import json
import subprocess
import sys

from flowlens.assets.storage import PrivateFiles
from flowlens.retention.journal import Tombstones
from flowlens.storage.sqlite.database import Database


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-m", "flowlens.cli.maintenance", *map(str, args)],
        capture_output=True,
        text=True,
    )


def test_actual_cli_backup_verify_restore_check_and_sanitized_failure(tmp_path):
    db = tmp_path / "source-db" / "data.sqlite"
    with Database(db):
        pass
    roots = {
        name: tmp_path / ("source-" + name) for name in ("raw", "artifacts", "imports", "journal")
    }
    for name, path in roots.items():
        handle = Tombstones(path) if name == "journal" else PrivateFiles(path)
        handle.close()
    source = [
        "--database",
        db,
        *[part for name, path in roots.items() for part in ("--" + name, path)],
    ]
    backup = tmp_path / "backup"
    created = invoke("backup", *source, "--destination", backup)
    assert created.returncode == 0, created.stderr
    receipt = json.loads(created.stdout)
    assert str(tmp_path) not in created.stdout
    verified = invoke("verify", "--backup", backup, "--manifest-hash", receipt["manifest_hash"])
    assert (
        verified.returncode == 0
        and json.loads(verified.stdout)["status"] == "VERIFIED_LOCAL_SNAPSHOT"
    )
    target = tmp_path / "restored"
    restored = invoke(
        "restore",
        "--backup",
        backup,
        "--target",
        target,
        "--journal",
        roots["journal"],
        "--manifest-hash",
        receipt["manifest_hash"],
    )
    assert restored.returncode == 0, restored.stderr
    assert "paths" not in json.loads(restored.stdout) and str(tmp_path) not in restored.stdout
    checked = invoke(
        "check",
        "--database",
        target / "db" / "data.sqlite",
        "--raw",
        target / "raw",
        "--artifacts",
        target / "artifacts",
        "--imports",
        target / "imports",
        "--journal",
        roots["journal"],
    )
    assert checked.returncode == 0 and json.loads(checked.stdout)["source_packages"] == 0
    denied = invoke(
        "restore",
        "--backup",
        backup,
        "--target",
        target,
        "--journal",
        roots["journal"],
        "--manifest-hash",
        receipt["manifest_hash"],
    )
    assert (
        denied.returncode != 0
        and "Traceback" not in denied.stderr
        and str(tmp_path) not in denied.stderr
    )
    invalid = invoke("--private-key=should-not-appear")
    assert invalid.returncode != 0 and "should-not-appear" not in invalid.stderr


def test_actual_cli_owner_lock_and_schema17_upgrade(tmp_path):
    from flowlens.auth.accounts import Accounts
    from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS
    from pydantic import SecretStr

    db = tmp_path / "source-db" / "data.sqlite"
    roots = {
        name: tmp_path / ("source-" + name) for name in ("raw", "artifacts", "imports", "journal")
    }
    for name, path in roots.items():
        handle = Tombstones(path) if name == "journal" else PrivateFiles(path)
        handle.close()
    args = [
        "--database",
        db,
        *[part for name, path in roots.items() for part in ("--" + name, path)],
    ]
    with Database(db, migrations=PLATFORM_MIGRATIONS[:17]) as owner:
        actor = Accounts(owner).bootstrap("admin", SecretStr("synthetic-initial-upgrade"))
        refused = invoke("check", *args)
        assert refused.returncode != 0 and "Traceback" not in refused.stderr
    checked = invoke("check", *args)
    assert checked.returncode == 0, checked.stderr
    with Database(db) as owner:
        with owner.begin() as uow:
            assert uow.connection.execute("SELECT id FROM platform_accounts").fetchone()[0] == str(
                actor.id
            )
            assert (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_schema_migrations"
                ).fetchone()[0]
                == 18
            )
