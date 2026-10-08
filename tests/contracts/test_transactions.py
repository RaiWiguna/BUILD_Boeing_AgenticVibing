import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def harness():
    return importlib.import_module("flowlens.testing.harness")


def result():
    m = importlib.import_module("flowlens.contracts.models")
    return m.JobResult.model_validate_json(
        (ROOT / "contracts/examples/job_result.json").read_text()
    )


def test_result_commit_is_atomic_and_idempotent(tmp_path):
    h = harness()
    store = h.SQLiteHarness(tmp_path / "disposable.db")
    candidate = result()
    store.seed_job(candidate)
    published = []
    receipt = store.accept(candidate, now_ms=100, publish=published.append)
    assert store.accept(candidate, now_ms=100, publish=published.append) == receipt
    assert len(published) == 1
    assert store.counts() == {"receipts": 1, "results": 1, "events": 1}
    assert h.SQLiteHarness(tmp_path / "disposable.db").counts() == store.counts()


@pytest.mark.parametrize(
    "change,code",
    [
        ({"cancelled": True}, "JOB_CANCELLED"),
        ({"expires_ms": 10}, "LEASE_EXPIRED"),
        ({"revision": 2}, "SOURCE_REVISION_CHANGED"),
        ({"rights": False}, "CLOUD_TRANSFER_BLOCKED"),
        ({"config_hash": "f" * 64}, "VERSION_CONFLICT"),
        ({"lease_id": "00000000-0000-0000-0000-000000000099"}, "LEASE_EXPIRED"),
    ],
)
def test_result_eligibility_failure_has_no_writes(tmp_path, change, code):
    h = harness()
    store = h.SQLiteHarness(tmp_path / "disposable.db")
    candidate = result()
    store.seed_job(candidate, **change)
    with pytest.raises(importlib.import_module("flowlens.core.errors").ContractError, match=code):
        store.accept(candidate, now_ms=100)
    assert all(value == 0 for value in store.counts().values())


def test_failure_rolls_back_domain_evidence_receipt_and_event(tmp_path):
    store = harness().SQLiteHarness(tmp_path / "disposable.db")
    candidate = result()
    store.seed_job(candidate)
    published = []
    with pytest.raises(RuntimeError, match="injected"):
        store.accept(candidate, now_ms=100, fail_before_commit=True, publish=published.append)
    assert all(value == 0 for value in store.counts().values())
    assert published == []
    assert store.accept(candidate, now_ms=100)


def test_different_payload_same_attempt_conflicts(tmp_path):
    store = harness().SQLiteHarness(tmp_path / "disposable.db")
    candidate = result()
    store.seed_job(candidate)
    store.accept(candidate, now_ms=100)
    changed = candidate.model_copy(update={"output_hash": "b" * 64})
    with pytest.raises(
        importlib.import_module("flowlens.core.errors").ContractError, match="IDEMPOTENCY_CONFLICT"
    ):
        store.accept(changed, now_ms=100)


def test_scope_foreign_key_is_enforced(tmp_path):
    import sqlite3

    store = harness().SQLiteHarness(tmp_path / "disposable.db")
    with store.transaction() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO analysis_results VALUES (?, ?, ?)",
                ("missing-session", "attempt", "{}"),
            )


def test_upgrade_and_migration_order(tmp_path):
    h = harness()
    path = tmp_path / "disposable.db"
    h.SQLiteHarness(path, target_version=1)
    upgraded = h.SQLiteHarness(path, target_version=2)
    assert upgraded.schema_version() == 2
    assert upgraded.foreign_keys_enabled()


def test_upgrade_preserves_historical_ids(tmp_path):
    store = harness().SQLiteHarness(tmp_path / "upgrade.db", target_version=1)
    candidate = result()
    store.seed_job(candidate)
    upgraded = harness().SQLiteHarness(tmp_path / "upgrade.db")
    receipt = upgraded.accept(candidate, now_ms=100)
    assert receipt.attempt_id == candidate.attempt_id
    assert receipt.session_id == candidate.session_id


@pytest.mark.parametrize(
    "change,code",
    [
        ({"run_id": "00000000-0000-0000-0000-000000000099"}, "ACCESS_DENIED"),
        ({"deadline_ms": 100}, "LEASE_EXPIRED"),
        ({"budget_microunits": 0}, "BUDGET_EXCEEDED"),
    ],
)
def test_result_scope_deadline_budget_are_part_of_frozen_commit(tmp_path, change, code):
    store = harness().SQLiteHarness(tmp_path / "disposable.db")
    candidate = result()
    store.seed_job(candidate, **change)
    with pytest.raises(importlib.import_module("flowlens.core.errors").ContractError, match=code):
        store.accept(candidate, now_ms=100)
    assert all(value == 0 for value in store.counts().values())


def test_rollback_includes_evidence_and_audit(tmp_path):
    store = harness().SQLiteHarness(tmp_path / "disposable.db")
    candidate = result()
    store.seed_job(candidate)
    with pytest.raises(RuntimeError):
        store.accept(candidate, now_ms=100, fail_before_commit=True)
    with store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM platform_evidence").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM platform_audit").fetchone()[0] == 0
    store.accept(candidate, now_ms=100)
    with store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM platform_evidence").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM platform_audit").fetchone()[0] == 1
