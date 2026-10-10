"""External deletion journal is authoritative after restoring an older database."""

import importlib
from uuid import uuid4

import pytest
from flowlens.core.errors import ContractError
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer


def journal(path):
    return importlib.import_module("flowlens.retention.journal").Tombstones(path)


def test_durable_idempotent_minimal_marker_and_reopen(tmp_path):
    root = tmp_path / "journal"
    sid = uuid4()
    j = journal(root)
    first = j.record(sid, "USER_REQUEST", "a" * 64, 1000)
    assert j.contains(sid) and not j.contains(uuid4())
    assert first == j.record(sid, "USER_REQUEST", "a" * 64, 2000)
    assert (
        "transcript" not in first.model_dump_json()
        and "source_label" not in first.model_dump_json()
    )
    j.close()
    j = journal(root)
    try:
        assert j.contains(sid) and j.entries() == [first]
    finally:
        j.close()


def test_record_conflict_and_single_owner(tmp_path):
    j = journal(tmp_path / "journal")
    try:
        sid = uuid4()
        j.record(sid, "USER_REQUEST", "a" * 64, 1000)
        with pytest.raises(ContractError):
            j.record(sid, "RETENTION_EXPIRED", "b" * 64, 1000)
        with pytest.raises((ValueError, OSError)):
            journal(tmp_path / "journal")
    finally:
        j.close()


def test_truncated_or_corrupt_journal_fails_closed(tmp_path):
    root = tmp_path / "journal"
    j = journal(root)
    j.record(uuid4(), "USER_REQUEST", "a" * 64, 1000)
    j.close()
    (root / "ledger.jsonl").write_bytes(b"")
    with pytest.raises(ValueError):
        journal(root)


def test_marker_blocks_old_database_context_and_new_receipts(media, committed, tmp_path):
    j = journal(tmp_path / "journal")
    try:
        j.record(media[2].session_id, "USER_REQUEST", "a" * 64, 1000)
        # Older restored DB still has source rows/credentials; the external journal is current.
        committed[2].deny_session = j.contains
        with pytest.raises(ContractError):
            committed[1].read_events(media[2])
        with pytest.raises(ContractError):
            committed[2].human_context(committed[3].token.get_secret_value(), media[2].session_id)
    finally:
        committed[2].deny_session = None
        j.close()
