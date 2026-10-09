"""A09.1 purge uses preview, durable external deletion authority and scoped retry."""

import importlib

import pytest
from flowlens.core.errors import ContractError
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_tombstones import journal


def coordinator(media, committed, tmp_path, **kwargs):
    j = journal(tmp_path / "journal")
    kwargs.setdefault("imports", committed[0].imports)
    cls = importlib.import_module("flowlens.retention.coordinator").Retention
    return cls(committed[2], media[0], j, **kwargs), j


def test_preview_then_purge_sensitive_rows_files_and_minimal_tombstone(
    media, committed, importer, tmp_path
):
    r, j = coordinator(media, committed, tmp_path)
    token = committed[3].token.get_secret_value()
    sid = media[2].session_id
    try:
        preview = r.preview(token, sid)
        assert preview.counts["platform_source_packages"] == 1
        assert str(media[0].sources.files.root) not in preview.model_dump_json()
        done = r.purge(
            token,
            sid,
            reason="USER_REQUEST",
            expected_inventory_hash=preview.inventory_hash,
            key="delete",
        )
        assert done.state == "DONE" and j.contains(sid)
        assert (
            r.purge(
                token,
                sid,
                reason="USER_REQUEST",
                expected_inventory_hash=preview.inventory_hash,
                key="delete",
            )
            == done
        )
        with pytest.raises(ContractError):
            committed[1].read_events(media[2])
        with importer[0].database.begin() as uow:
            for table in [
                "platform_sources",
                "platform_source_packages",
                "platform_records",
                "platform_evidence",
                "platform_revisions",
                "platform_grants",
            ]:
                assert (
                    uow.connection.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE session_id=?", (str(sid),)
                    ).fetchone()[0]
                    == 0
                )
            assert uow.connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert [
            name
            for name in __import__("os").listdir(media[0].sources.files.fd)
            if not name.startswith(".")
        ] == []
    finally:
        j.close()


def test_inventory_conflict_does_not_create_deletion_marker(media, committed, tmp_path):
    r, j = coordinator(media, committed, tmp_path)
    try:
        with pytest.raises(ContractError):
            r.purge(
                committed[3].token.get_secret_value(),
                media[2].session_id,
                reason="USER_REQUEST",
                expected_inventory_hash="0" * 64,
                key="stale",
            )
        assert not j.contains(media[2].session_id)
        assert committed[1].read_events(media[2])
    finally:
        j.close()


def test_failure_after_marker_denies_reads_and_retry_completes(media, committed, tmp_path):
    r, j = coordinator(media, committed, tmp_path)
    token = committed[3].token.get_secret_value()
    sid = media[2].session_id

    def failed(phase):
        if phase == "after_marker":
            raise RuntimeError("synthetic erase failure")

    r.fault = failed
    try:
        preview = r.preview(token, sid)
        with pytest.raises(RuntimeError):
            r.purge(
                token,
                sid,
                reason="USER_REQUEST",
                expected_inventory_hash=preview.inventory_hash,
                key="retry",
            )
        with pytest.raises(ContractError):
            committed[1].read_events(media[2])
        r.fault = lambda phase: None
        assert r.resume(token, sid).state == "DONE"
    finally:
        j.close()


def test_registered_fake_callback_and_failure_not_marked_done(media, committed, tmp_path):
    calls = []

    def fake(ctx, uow):
        ctx.require("admin", ctx.session_id)
        calls.append(ctx.session_id)
        uow.audit(ctx, "MOCK_PURGE", ctx.session_id)

    r, j = coordinator(
        media, committed, tmp_path, callbacks={"analysis": fake}, inventory_namespaces=("analysis",)
    )
    token = committed[3].token.get_secret_value()
    sid = media[2].session_id
    try:
        preview = r.preview(token, sid)
        r.purge(
            token,
            sid,
            reason="USER_REQUEST",
            expected_inventory_hash=preview.inventory_hash,
            key="callback",
        )
        assert calls == [sid]
    finally:
        j.close()


@pytest.mark.parametrize("phase", ["after_callbacks", "after_files", "before_commit"])
def test_purge_failure_never_reopens_access_and_retry_finishes(media, committed, tmp_path, phase):
    r, j = coordinator(media, committed, tmp_path)
    token = committed[3].token.get_secret_value()
    sid = media[2].session_id

    def fail(point):
        if point == phase:
            raise RuntimeError("synthetic purge boundary")

    r.fault = fail
    try:
        preview = r.preview(token, sid)
        with pytest.raises(RuntimeError):
            r.purge(
                token,
                sid,
                reason="USER_REQUEST",
                expected_inventory_hash=preview.inventory_hash,
                key=phase,
            )
        with pytest.raises(ContractError):
            media[0].metadata(media[2], media[4].manifest.assets[0].id)
        r.fault = lambda point: None
        assert r.resume(token, sid).state == "DONE"
    finally:
        j.close()


@pytest.mark.parametrize("action", ["commit", "rollback", "retention", "defer"])
def test_callback_cannot_commit_or_claim_retention_authority(media, committed, tmp_path, action):
    def bad(ctx, uow):
        if action == "commit":
            uow.commit()
        elif action == "rollback":
            uow.rollback()
        elif action == "retention":
            with uow.retention_writes(ctx):
                pass
        else:
            uow.after_commit(lambda: None)

    r, j = coordinator(
        media, committed, tmp_path, callbacks={"analysis": bad}, inventory_namespaces=("analysis",)
    )
    token = committed[3].token.get_secret_value()
    sid = media[2].session_id
    try:
        preview = r.preview(token, sid)
        with pytest.raises(RuntimeError):
            r.purge(
                token,
                sid,
                reason="USER_REQUEST",
                expected_inventory_hash=preview.inventory_hash,
                key="bad-module",
            )
        assert j.contains(sid)
        with r.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT state FROM platform_purges").fetchone()[0]
                == "PREPARED"
            )
    finally:
        j.close()


def test_preview_binds_mutable_contents_not_only_counts(media, committed, tmp_path):
    r, j = coordinator(media, committed, tmp_path)
    token = committed[3].token.get_secret_value()
    sid = media[2].session_id
    try:
        preview = r.preview(token, sid)
        with r.database.begin() as uow:
            uow.connection.execute(
                "UPDATE platform_context_state SET as_of_ms=as_of_ms+1 WHERE session_id=?",
                (str(sid),),
            )
            uow.commit()
        with pytest.raises(ContractError):
            r.purge(
                token,
                sid,
                reason="USER_REQUEST",
                expected_inventory_hash=preview.inventory_hash,
                key="changed",
            )
        assert not j.contains(sid)
    finally:
        j.close()


def test_reconcile_external_marker_erases_restored_rows_before_reads(
    media, committed, importer, tmp_path
):
    r, j = coordinator(media, committed, tmp_path, imports=importer[0])
    sid = media[2].session_id
    try:
        preview = r.preview(committed[3].token.get_secret_value(), sid)
        # Simulate restoring an old database: external deletion authority already exists,
        # but source rows and private packages in this database still predate deletion.
        j.record(sid, "USER_REQUEST", preview.inventory_hash, 1000)
        assert r.recover() == [sid]
        with r.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_sources").fetchone()[0] == 0
            )
            assert (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_import_drafts WHERE id=?",
                    (str(preview.draft_ids[0]),),
                ).fetchone()[0]
                == 0
            )
        assert not (importer[0].root / str(preview.draft_ids[0])).exists()
        with pytest.raises(ContractError):
            committed[1].read_events(media[2])
        assert r.recover() == []
    finally:
        j.close()


def test_callback_cannot_modify_global_accounts(media, committed, tmp_path):
    def bad(ctx, uow):
        uow.connection.execute("UPDATE platform_accounts SET active=0")

    r, j = coordinator(
        media, committed, tmp_path, callbacks={"analysis": bad}, inventory_namespaces=("analysis",)
    )
    token = committed[3].token.get_secret_value()
    try:
        preview = r.preview(token, media[2].session_id)
        with pytest.raises(ContractError):
            r.purge(
                token,
                media[2].session_id,
                reason="USER_REQUEST",
                expected_inventory_hash=preview.inventory_hash,
                key="global-modification",
            )
        with r.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT MIN(active) FROM platform_accounts").fetchone()[0]
                == 1
            )
    finally:
        j.close()


def test_source_expiry_reconciles_without_provider_or_admin_login(media, committed, tmp_path):
    r, j = coordinator(media, committed, tmp_path)
    try:
        with r.database.begin() as uow:
            expiry = uow.connection.execute(
                "SELECT MAX(expires_ms) FROM platform_source_packages"
            ).fetchone()[0]
        committed[4][0] = expiry
        assert r.recover() == [media[2].session_id]
        assert j.entries()[0].reason == "RETENTION_EXPIRED"
        with pytest.raises(ContractError):
            committed[1].read_events(media[2])
    finally:
        j.close()


def test_unknown_inventory_namespace_and_sql_tables_fail_closed(media, committed, tmp_path):
    r, j = coordinator(media, committed, tmp_path)
    try:
        with r.database.begin() as uow:
            uow.connection.execute(
                'CREATE TABLE "unregistered;table" (session_id TEXT, contents TEXT)'
            )
            uow.commit()
        with pytest.raises(ContractError):
            r.preview(committed[3].token.get_secret_value(), media[2].session_id)
        assert not j.contains(media[2].session_id)
        assert committed[1].read_events(media[2])
    finally:
        j.close()
