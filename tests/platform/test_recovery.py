"""A09.3 disposable consistent snapshots, isolated restore and current deletion authority."""

import importlib
from pathlib import Path

import pytest
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_retention import journal


def paths(media, importer, tmp_path):
    module = importlib.import_module("flowlens.recovery.maintenance")
    j = journal(tmp_path / "current-journal")
    j.close()
    return module.Paths(
        database=importer[0].database.path,
        raw=media[0].sources.files.root,
        artifacts=media[0].artifacts.root,
        imports=importer[0].root,
        journal=tmp_path / "current-journal",
    )


def stop_fixture(media, importer):
    media[0].sources.files.close()
    media[0].artifacts.close()
    importer[0].close()
    importer[0].database.close()


def service(p, now):
    return importlib.import_module("flowlens.recovery.maintenance").Maintenance(
        p, clock=lambda: now[0]
    )


def test_live_owner_blocks_offline_backup(media, importer, tmp_path):
    p = paths(media, importer, tmp_path)
    with pytest.raises(RuntimeError):
        with service(p, importer[2]):
            pass
    assert media[0].sources.files.root.exists()


def test_sqlite_assets_snapshot_restore_preserves_scope_hashes_grants_and_history(
    media, committed, importer, tmp_path
):
    p = paths(media, importer, tmp_path)
    sid = media[2].session_id
    input_hash = media[2].input_hash
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as maintenance:
        created = cls(maintenance).create(tmp_path / "backup")
        assert created.files >= 4 and created.sessions == 1
        assert str(p.database) not in created.model_dump_json()
    restored = cls.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=p.journal,
        expected_manifest_hash=created.manifest_hash,
        clock=lambda: now[0],
    )
    assert restored.status == "RESTORED_ISOLATED"
    with service(restored.paths, now) as maintenance:
        with maintenance.database.begin() as uow:
            assert (
                uow.connection.execute(
                    "SELECT input_hash FROM platform_revisions WHERE session_id=?", (str(sid),)
                ).fetchone()[0]
                == input_hash
            )
            assert (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_grants WHERE session_id=?", (str(sid),)
                ).fetchone()[0]
                > 0
            )
            assert uow.connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert maintenance.check()["source_packages"] == 1
    assert p.database.exists()


def test_restore_applies_newer_external_marker_before_target_publication(
    media, committed, importer, tmp_path
):
    p = paths(media, importer, tmp_path)
    sid = media[2].session_id
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as maintenance:
        receipt = cls(maintenance).create(tmp_path / "backup")
        with maintenance.database.begin() as uow:
            preview = maintenance.retention._inventory(uow, sid)
        maintenance.journal.record(sid, "USER_REQUEST", preview.inventory_hash, now[0])
    restored = cls.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=p.journal,
        expected_manifest_hash=receipt.manifest_hash,
        clock=lambda: now[0],
    )
    assert restored.purged_sessions == [sid]
    with service(restored.paths, now) as maintenance:
        assert maintenance.check()["source_packages"] == 0
        with maintenance.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_records").fetchone()[0] == 0
            )


def test_backup_uses_committed_wal_not_only_main_file(media, importer, tmp_path):
    import sqlite3
    from uuid import uuid4

    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        reader = sqlite3.connect(p.database, isolation_level=None)
        try:
            reader.execute("BEGIN")
            reader.execute("SELECT COUNT(*) FROM platform_recovery_audit").fetchone()
            marker = str(uuid4())
            with m.database.begin() as uow:
                uow.connection.execute(
                    "INSERT INTO platform_recovery_audit VALUES (?,?,?,?,?,?)",
                    (marker, "BACKUP_CREATED", str(uuid4()), "a" * 64, 0, now[0]),
                )
                uow.commit()
            assert Path(str(p.database) + "-wal").stat().st_size > 0
            created = cls(m).create(tmp_path / "backup")
        finally:
            reader.close()
    snapshot = sqlite3.connect(tmp_path / "backup" / "snapshot.sqlite")
    try:
        assert (
            snapshot.execute(
                "SELECT id FROM platform_recovery_audit WHERE id=?", (marker,)
            ).fetchone()[0]
            == marker
        )
    finally:
        snapshot.close()
    assert cls.verify(tmp_path / "backup", created.manifest_hash).id == created.id


@pytest.mark.parametrize("phase", ["after_database", "after_assets", "before_publish"])
def test_backup_failure_never_promotes_partial_or_alters_source(media, importer, tmp_path, phase):
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        backup = cls(m)

        def fail(point):
            if point == phase:
                raise OSError("synthetic disk failure private-path")

        backup.fault = fail
        with pytest.raises(OSError):
            backup.create(tmp_path / "backup")
        assert not (tmp_path / "backup").exists()
        assert not list(tmp_path.glob(".snapshot-*.tmp"))
        assert m.check()["source_packages"] == 1
        backup.fault = lambda point: None
        assert backup.create(tmp_path / "backup").sessions == 1


def test_tampered_bytes_and_existing_target_are_denied(media, importer, tmp_path):
    import os

    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        receipt = cls(m).create(tmp_path / "backup")
        with pytest.raises(ValueError):
            cls(m).create(tmp_path / "backup")
    manifest = cls.verify(tmp_path / "backup", receipt.manifest_hash)
    file = next(f for f in manifest.files if f.path.endswith(".raw"))
    target = tmp_path / "backup" / file.path
    os.chmod(target, 0o600)
    target.write_bytes(b"synthetic tamper")
    with pytest.raises(ValueError):
        cls.restore(
            tmp_path / "backup",
            tmp_path / "restored",
            journal_path=p.journal,
            expected_manifest_hash=receipt.manifest_hash,
            clock=lambda: now[0],
        )
    assert not (tmp_path / "restored").exists()


def test_restore_expired_source_never_reopens_and_backup_prune_enforces_schedule(
    media, importer, tmp_path
):
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        receipt = cls(m).create(tmp_path / "backup")
        with m.database.begin() as uow:
            expiry = uow.connection.execute(
                "SELECT MAX(expires_ms) FROM platform_source_packages"
            ).fetchone()[0]
    now[0] = expiry
    restored = cls.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=p.journal,
        expected_manifest_hash=receipt.manifest_hash,
        clock=lambda: now[0],
    )
    with service(restored.paths, now) as m:
        assert m.check()["source_packages"] == 0
    assert (
        cls.prune(
            tmp_path / "backup",
            journal_path=p.journal,
            expected_manifest_hash=receipt.manifest_hash,
            clock=lambda: now[0],
        )
        == "REMOVED"
    )
    assert not (tmp_path / "backup").exists()


def test_manifest_traversal_and_symlink_are_rejected_even_with_recomputed_hash(
    media, importer, tmp_path
):
    import json

    from flowlens.imports.metadata import hashed

    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        receipt = cls(m).create(tmp_path / "backup")
    manifest_file = tmp_path / "backup" / "manifest.json"
    manifest_file.chmod(0o600)
    original = json.loads(manifest_file.read_text())
    bad = json.loads(json.dumps(original))
    bad["manifest"]["files"][1]["path"] = "../outside-private-file"
    bad["manifest_hash"] = hashed(bad["manifest"])
    manifest_file.write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        cls.verify(tmp_path / "backup", bad["manifest_hash"])
    manifest_file.write_text(json.dumps(original))
    link = tmp_path / "alias"
    link.symlink_to(tmp_path / "backup", target_is_directory=True)
    with pytest.raises(ValueError):
        cls.verify(link, receipt.manifest_hash)


def test_restore_current_journal_missing_or_corrupt_denies_without_publishing(
    media, importer, tmp_path
):
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        receipt = cls(m).create(tmp_path / "backup")
    (p.journal / "head.json").write_bytes(b"corrupt authority")
    with pytest.raises(ValueError):
        cls.restore(
            tmp_path / "backup",
            tmp_path / "restored",
            journal_path=p.journal,
            expected_manifest_hash=receipt.manifest_hash,
            clock=lambda: now[0],
        )
    assert not (tmp_path / "restored").exists()
    assert not list(tmp_path.glob(".restore-*.tmp"))


def test_prune_retains_valid_source_then_removes_on_current_marker(media, importer, tmp_path):
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        receipt = cls(m).create(tmp_path / "backup")
        with m.database.begin() as uow:
            inventory = m.retention._inventory(uow, media[2].session_id)
    assert (
        cls.prune(
            tmp_path / "backup",
            journal_path=p.journal,
            expected_manifest_hash=receipt.manifest_hash,
            clock=lambda: now[0],
        )
        == "RETAINED"
    )
    j = journal(p.journal)
    j.record(media[2].session_id, "USER_REQUEST", inventory.inventory_hash, now[0])
    j.close()
    assert (
        cls.prune(
            tmp_path / "backup",
            journal_path=p.journal,
            expected_manifest_hash=receipt.manifest_hash,
            clock=lambda: now[0],
        )
        == "REMOVED"
    )


@pytest.mark.parametrize(
    "phase", ["after_verify", "after_files", "after_reconciliation", "before_publish"]
)
def test_restore_failure_never_exposes_partial_target_and_retry_succeeds(
    media, importer, tmp_path, phase
):
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        created = cls(m).create(tmp_path / "backup")

    def fail(point):
        if point == phase:
            raise OSError("synthetic restore disk boundary")

    with pytest.raises(OSError):
        cls.restore(
            tmp_path / "backup",
            tmp_path / "restored",
            journal_path=p.journal,
            expected_manifest_hash=created.manifest_hash,
            clock=lambda: now[0],
            fault=fail,
        )
    assert not (tmp_path / "restored").exists()
    assert not list(tmp_path.glob(".restore-*.tmp"))
    assert cls.verify(tmp_path / "backup", created.manifest_hash).id == created.id
    restored = cls.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=p.journal,
        expected_manifest_hash=created.manifest_hash,
        clock=lambda: now[0],
    )
    assert restored.status == "RESTORED_ISOLATED"


def test_prune_damaged_expired_snapshot_retries_after_partial_erasure(
    media, importer, tmp_path, monkeypatch
):
    import flowlens.recovery.snapshots as module

    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = module.Snapshots
    with service(p, now) as m:
        created = cls(m).create(tmp_path / "backup")
    now[0] = created.removal_due_ms
    manifest = cls.verify(tmp_path / "backup", created.manifest_hash)
    damaged = tmp_path / "backup" / next(f.path for f in manifest.files if f.path.endswith(".raw"))
    damaged.chmod(0o600)
    damaged.write_bytes(b"corrupted expired fixture")
    original = module.shutil.rmtree

    def partial(path):
        (path / "manifest.json").unlink()
        raise OSError("synthetic deletion boundary")

    monkeypatch.setattr(module.shutil, "rmtree", partial)
    with pytest.raises(OSError):
        cls.prune(
            tmp_path / "backup",
            journal_path=p.journal,
            expected_manifest_hash=created.manifest_hash,
            clock=lambda: now[0],
        )
    monkeypatch.setattr(module.shutil, "rmtree", original)
    assert (
        cls.prune(
            tmp_path / "backup",
            journal_path=p.journal,
            expected_manifest_hash=created.manifest_hash,
            clock=lambda: now[0],
        )
        == "REMOVED"
    )
    assert (
        cls.prune(
            tmp_path / "backup",
            journal_path=p.journal,
            expected_manifest_hash=created.manifest_hash,
            clock=lambda: now[0],
        )
        == "ALREADY_REMOVED"
    )
    assert not list(tmp_path.glob(".retired-*.tmp"))


def test_restore_invokes_frozen_fake_purge_before_publication(media, importer, tmp_path):
    from flowlens.testing.harness import FakeAnalysis

    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        created = cls(m).create(tmp_path / "backup")
        with m.database.begin() as uow:
            inventory = m.retention._inventory(uow, media[2].session_id)
        m.journal.record(media[2].session_id, "USER_REQUEST", inventory.inventory_hash, now[0])
    calls = []

    class Observed(FakeAnalysis):
        def purge(self, ctx, uow):
            calls.append(ctx.session_id)
            super().purge(ctx, uow)

    fake = Observed()
    restored = cls.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=p.journal,
        expected_manifest_hash=created.manifest_hash,
        clock=lambda: now[0],
        callbacks={"analysis": fake.purge},
    )
    assert calls == [media[2].session_id] and restored.purged_sessions == calls


def test_expiry_or_new_marker_during_backup_prevents_publication(media, importer, tmp_path):
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        backup = cls(m)
        with m.database.begin() as uow:
            inventory = m.retention._inventory(uow, media[2].session_id)

        def deleted(phase):
            if phase == "after_assets":
                m.journal.record(
                    media[2].session_id, "USER_REQUEST", inventory.inventory_hash, now[0]
                )

        backup.fault = deleted
        with pytest.raises(ValueError):
            backup.create(tmp_path / "backup")
        assert not (tmp_path / "backup").exists()
        assert not list(tmp_path.glob(".snapshot-*.tmp"))


def test_durable_backup_audit_failure_is_reported_as_pending_not_false_rollback(
    media, importer, tmp_path, monkeypatch
):
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:

        def fail(*args):
            raise OSError("synthetic audit persistence failure")

        monkeypatch.setattr(m, "audit", fail)
        receipt = cls(m).create(tmp_path / "backup")
        assert receipt.status == "BACKUP_DURABLE_AUDIT_PENDING"
    assert cls.verify(tmp_path / "backup", receipt.manifest_hash).id == receipt.id


def test_actual_copy_enospc_leaves_source_and_destination_unmodified(
    media, importer, tmp_path, monkeypatch
):
    import errno

    import flowlens.recovery.snapshots as module

    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    with service(p, now) as m:

        def no_space(fd, data):
            raise OSError(errno.ENOSPC, "synthetic full disk")

        monkeypatch.setattr(module.os, "write", no_space)
        with pytest.raises(OSError):
            module.Snapshots(m).create(tmp_path / "backup")
        assert not (tmp_path / "backup").exists()
        assert not list(tmp_path.glob(".snapshot-*.tmp"))
        assert m.check()["source_packages"] == 1


def test_publish_fsync_failure_rolls_back_new_destination(media, importer, tmp_path, monkeypatch):
    import flowlens.recovery.snapshots as module

    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    original = module._fsync
    with service(p, now) as m:

        def fail(path):
            if path == tmp_path and (tmp_path / "backup").exists():
                raise OSError("synthetic parent fsync failure")
            original(path)

        monkeypatch.setattr(module, "_fsync", fail)
        with pytest.raises(OSError):
            module.Snapshots(m).create(tmp_path / "backup")
        assert not (tmp_path / "backup").exists()
        assert not list(tmp_path.glob(".snapshot-*.tmp"))
        assert m.check()["source_packages"] == 1


def test_candidate_cleanup_skips_active_and_crash_cleans_private_orphan(media, importer, tmp_path):
    import json
    import subprocess
    import sys

    from flowlens.recovery.candidates import cleanup, release, reserve

    active = tmp_path / ".snapshot-00000000-0000-0000-0000-000000000001.tmp"
    fd = reserve(active)
    active.mkdir(mode=0o700)
    try:
        assert cleanup(tmp_path) == {"removed_candidates": 0, "active_candidates": 1}
    finally:
        active.rmdir()
        release(active, fd)
    p = paths(media, importer, tmp_path)
    stop_fixture(media, importer)
    code = """
import json,os,sys
from pathlib import Path
from flowlens.recovery.maintenance import Paths,Maintenance
from flowlens.recovery.snapshots import Snapshots
p=Paths(**{k:Path(v) for k,v in json.loads(sys.argv[1]).items()})
with Maintenance(p,clock=lambda:1000) as m:
    s=Snapshots(m)
    s.fault=lambda phase:os._exit(83) if phase=='after_assets' else None
    s.create(Path(sys.argv[2]))
"""
    run = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            json.dumps({k: str(v) for k, v in p.model_dump().items()}),
            str(tmp_path / "backup"),
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 83 and not (tmp_path / "backup").exists()
    assert list(tmp_path.glob(".snapshot-*.tmp"))
    assert cleanup(tmp_path) == {"removed_candidates": 1, "active_candidates": 0}
    assert not list(tmp_path.glob(".snapshot-*.tmp"))
    with service(p, importer[2]) as m:
        assert m.check()["source_packages"] == 1
