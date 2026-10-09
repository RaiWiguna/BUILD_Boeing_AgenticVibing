"""A03.3 durable mutation infrastructure, synthetic operations and real SQLite."""

import sqlite3
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from flowlens.auth.accounts import Accounts
from flowlens.auth.permissions import Permissions
from flowlens.auth.sessions import Sessions
from flowlens.contracts.models import Contract, SourceEvent
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import Database
from pydantic import SecretStr


class NoteInput(Contract):
    statement: str
    attributes: dict[str, int] = {}


@pytest.fixture
def platform(tmp_path):
    now = [1000]
    with Database(tmp_path / "mutations.db") as db:
        accounts = Accounts(db)
        initial, changed = (
            SecretStr("synthetic-mutation-initial"),
            SecretStr("synthetic-mutation-changed"),
        )
        admin = accounts.bootstrap("admin", initial)
        accounts.change_password(admin.id, initial, changed)
        sessions = Sessions(db, accounts, clock=lambda: now[0])
        auth = sessions.login("admin", changed, "local")
        permissions = Permissions(db, sessions)
        db.context_guard = permissions.enforce
        sid, run, other = uuid4(), uuid4(), uuid4()
        with db.begin() as uow:
            for identifier in (sid, other):
                uow.connection.execute(
                    "INSERT INTO platform_sessions VALUES (?)", (str(identifier),)
                )
                uow.connection.execute(
                    "INSERT INTO platform_revisions VALUES (?,1,?)", (str(identifier), "a" * 64)
                )
                uow.connection.execute(
                    "INSERT INTO platform_context_state VALUES (?,500,'AS_KNOWN')",
                    (str(identifier),),
                )
            uow.connection.execute("INSERT INTO platform_runs VALUES (?,?,1)", (str(sid), str(run)))
            uow.commit()
        for capability in ("read", "analysis", "review"):
            permissions.grant(
                auth.token.get_secret_value(),
                admin.id,
                sid,
                capability,
                role="evaluator",
                expires_ms=1000000,
            )
        yield db, permissions, auth, sid, run, other, now


def context(p, *, run=True):
    _, permissions, auth, sid, run_id, *_ = p
    return permissions.human_context(
        auth.token.get_secret_value(), sid, run_id=run_id if run else None
    )


def event(ctx, statement="synthetic observed note"):
    return SourceEvent(
        id=uuid4(),
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        event_time_ms=100,
        available_time_ms=100,
        recorded_at=datetime(2026, 10, 9, tzinfo=UTC),
        source_id=uuid4(),
        source_event_id="synthetic",
        kind="REPORT",
        entity_id=None,
        source_hash="a" * 64,
        quality="SUPPORTED",
        statement=statement,
    )


@pytest.mark.parametrize(
    "table", ["platform_audit", "platform_account_audit", "platform_permission_audit"]
)
@pytest.mark.parametrize("method", ["update", "delete", "replace"])
def test_all_existing_audit_tables_are_append_only(platform, table, method):
    db, *_ = platform
    ctx = context(platform)
    with db.begin() as uow:
        uow.audit(ctx, "NOTE_CREATED", uuid4())
        uow.commit()
    with db.begin() as uow:
        before = [tuple(row) for row in uow.connection.execute(f"SELECT * FROM {table}")]
        assert before
        with pytest.raises(sqlite3.DatabaseError):
            if method == "update":
                uow.connection.execute(f"UPDATE {table} SET action='TAMPERED'")
            elif method == "delete":
                uow.connection.execute(f"DELETE FROM {table}")
            else:
                uow.connection.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}")
        assert [tuple(row) for row in uow.connection.execute(f"SELECT * FROM {table}")] == before


def coordinator(p, handler=None):
    from flowlens.storage.sqlite.mutations import MutationOperation, Mutations

    def write(ctx, payload, uow):
        record = event(ctx, payload.statement)
        uow.repository("source_events").append(ctx, record)
        return record

    spec = MutationOperation(
        name="ADD_NOTE",
        namespace="platform.note",
        repository_namespace="source_events",
        capability="analysis",
        payload_type=NoteInput,
        apply=handler or write,
    )
    return Mutations(p[0], operations=(spec,))


def execute(
    service,
    ctx,
    target,
    *,
    key="synthetic-key-01",
    version=0,
    statement="synthetic note",
    payload=None,
    publish=None,
):
    return service.execute(
        ctx,
        "ADD_NOTE",
        target_id=target,
        key=key,
        expected_version=version,
        payload=payload or NoteInput(statement=statement),
        publish=publish,
    )


def counts(db):
    with db.begin() as uow:
        return tuple(
            uow.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "platform_records",
                "platform_audit",
                "platform_events",
                "platform_mutation_receipts",
                "platform_mutation_versions",
            )
        )


def test_duplicate_key_is_one_effect_and_stable_receipt(platform):
    ctx, target = context(platform), uuid4()
    service, published = coordinator(platform), []
    receipt = execute(service, ctx, target, publish=published.append)
    assert (receipt.target_id, receipt.version, receipt.sequence) == (target, 1, 1)
    retry_context = context(platform)
    assert execute(service, retry_context, target, publish=published.append) == receipt
    assert counts(platform[0]) == (1, 1, 1, 1, 1)
    assert published == [receipt]
    assert service.version(retry_context, "ADD_NOTE", target) == 1


def test_canonical_payload_key_order_and_new_request_id_are_not_new_effect(platform):
    service, target = coordinator(platform), uuid4()
    first = execute(
        service,
        context(platform),
        target,
        payload=NoteInput(statement="same", attributes={"a": 1, "b": 2}),
    )
    retry = execute(
        service,
        context(platform),
        target,
        payload=NoteInput(statement="same", attributes={"b": 2, "a": 1}),
    )
    assert first == retry
    assert counts(platform[0]) == (1, 1, 1, 1, 1)


@pytest.mark.parametrize("changed", ["payload", "version"])
def test_same_key_with_changed_request_conflicts_without_effect(platform, changed):
    ctx, service, target = context(platform), coordinator(platform), uuid4()
    execute(service, ctx, target)
    with pytest.raises(ContractError, match="IDEMPOTENCY_CONFLICT"):
        execute(
            service,
            ctx,
            target,
            statement="different" if changed == "payload" else "synthetic note",
            version=1 if changed == "version" else 0,
        )
    assert counts(platform[0]) == (1, 1, 1, 1, 1)


def test_optimistic_version_conflict_and_old_receipt_after_later_mutation(platform):
    ctx, service, target = context(platform), coordinator(platform), uuid4()
    first = execute(service, ctx, target)
    with pytest.raises(ContractError, match="VERSION_CONFLICT"):
        execute(service, ctx, target, key="new-key", version=0)
    later = execute(service, ctx, target, key="new-key", version=1, statement="next")
    assert (later.version, later.sequence) == (2, 2)
    assert execute(service, ctx, target) == first
    assert service.version(ctx, "ADD_NOTE", target) == 2
    assert counts(platform[0]) == (2, 2, 2, 2, 1)


@pytest.mark.parametrize(
    "fault", ["domain", "scope", "commit", "rollback", "raw_commit", "caught_commit"]
)
def test_faults_and_callback_transaction_control_roll_back_everything(platform, fault):
    ctx, target = context(platform), uuid4()
    published = []

    def fail(context, payload, uow):
        record = event(context, payload.statement)
        uow.repository("source_events").append(context, record)
        if fault == "domain":
            raise RuntimeError("synthetic domain failure")
        if fault == "scope":
            return record.model_copy(update={"session_id": uuid4()})
        if fault == "commit":
            uow.commit()
        elif fault == "rollback":
            uow.rollback()
        elif fault == "raw_commit":
            uow.connection.commit()
        else:
            try:
                uow.commit()
            except RuntimeError:
                pass
        return record

    service = coordinator(platform, fail)
    with pytest.raises((RuntimeError, sqlite3.DatabaseError, ContractError)):
        execute(service, ctx, target, publish=published.append)
    assert counts(platform[0]) == (0, 0, 0, 0, 0)
    assert service.version(ctx, "ADD_NOTE", target) == 0
    assert published == []


def test_publication_failure_is_durable_and_retry_returns_original_receipt(platform):
    service, ctx, target = coordinator(platform), context(platform), uuid4()

    def fail(receipt):
        raise RuntimeError("private provider secret")

    with pytest.raises(RuntimeError, match="Commit is durable") as error:
        execute(service, ctx, target, publish=fail)
    assert "private provider" not in str(error.value)
    assert counts(platform[0]) == (1, 1, 1, 1, 1)
    retry = execute(service, context(platform), target)
    assert (retry.version, retry.sequence) == (1, 1)
    assert counts(platform[0]) == (1, 1, 1, 1, 1)


@pytest.mark.parametrize("cause", ["revoke", "logout", "forged", "expired_proof"])
def test_retry_rechecks_authority_before_receipt_lookup(platform, cause):
    db, permissions, auth, sid, _, _, now = platform
    service, ctx, target = coordinator(platform), context(platform), uuid4()
    execute(service, ctx, target)
    if cause == "revoke":
        permissions.revoke(auth.token.get_secret_value(), auth.account.id, sid, "analysis")
    elif cause == "logout":
        permissions.sessions.logout(auth.token.get_secret_value())
    elif cause == "forged":
        ctx = ctx.model_copy(update={"actor_id": uuid4()})
    else:
        now[0] += 300000
    with pytest.raises(ContractError):
        execute(service, ctx, target)
    assert counts(db) == (1, 1, 1, 1, 1)


def test_restart_preserves_receipt_version_and_one_effect(platform):
    db, _, auth, sid, run, _, now = platform
    ctx, target = context(platform), uuid4()
    first = execute(coordinator(platform), ctx, target)
    path = db.path
    db.close()
    with Database(path) as reopened:
        permissions = Permissions(
            reopened, Sessions(reopened, Accounts(reopened), clock=lambda: now[0])
        )
        reopened.context_guard = permissions.enforce
        replacement = (reopened, permissions, auth, sid, run, uuid4(), now)
        service = coordinator(replacement)
        assert execute(service, context(replacement), target) == first
        assert service.version(context(replacement), "ADD_NOTE", target) == 1
        assert counts(reopened) == (1, 1, 1, 1, 1)


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_requests_have_one_winner_or_same_receipt(platform, same_key):
    from concurrent.futures import ThreadPoolExecutor

    service, ctx, target = coordinator(platform), context(platform), uuid4()

    def request(index):
        try:
            return execute(service, ctx, target, key="same" if same_key else f"key-{index}")
        except ContractError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(request, range(8)))
    if same_key:
        assert all(item == outcomes[0] for item in outcomes)
    else:
        assert outcomes.count("VERSION_CONFLICT") == 7
    assert counts(platform[0]) == (1, 1, 1, 1, 1)


@pytest.mark.parametrize("bad", ["", "space key", "x" * 129, "secret\nkey", 12])
def test_invalid_idempotency_key_has_no_effect(platform, bad):
    service, ctx, target = coordinator(platform), context(platform), uuid4()
    with pytest.raises(ContractError, match="INVALID_INPUT"):
        execute(service, ctx, target, key=bad)
    assert counts(platform[0]) == (0, 0, 0, 0, 0)


def test_worker_cannot_bypass_future_lease_coordinator_via_general_mutation(platform):
    _, permissions, auth, sid, run, *_ = platform
    worker = permissions.provision_worker(auth.token.get_secret_value(), expires_ms=1000000)
    scope = permissions.bind_worker(
        auth.token.get_secret_value(), worker.id, sid, run, expires_ms=900000
    )
    ctx = permissions.worker_context(worker.token.get_secret_value(), scope)
    service = coordinator(platform)
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        execute(service, ctx, uuid4())
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.version(ctx, "ADD_NOTE", uuid4())
    assert counts(platform[0]) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    "sql",
    [
        "PRAGMA recursive_triggers=OFF",
        "PRAGMA writable_schema=ON",
        "PRAGMA foreign_keys=OFF",
        "DROP TRIGGER platform_append_only_platform_audit_update",
        "DROP TABLE platform_audit",
        "ALTER TABLE platform_audit RENAME TO moved_audit",
    ],
)
def test_runtime_cannot_remove_or_disable_immutable_protection(platform, sql):
    with platform[0].begin() as uow, pytest.raises(sqlite3.DatabaseError):
        uow.connection.execute(sql)


def test_unauthorized_mutation_requires_real_context_guard(tmp_path):
    from pathlib import Path

    from flowlens.contracts.models import RequestContext

    with Database(tmp_path / "unguarded.db") as db:
        p = (db,)
        ctx = RequestContext.model_validate_json(
            Path("contracts/examples/context.json").read_text()
        )
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            execute(coordinator(p), ctx, uuid4())
        assert counts(db) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    "table",
    [
        "platform_audit",
        "platform_events",
        "platform_mutation_receipts",
        "platform_mutation_versions",
    ],
)
def test_storage_fault_after_domain_write_rolls_back_all_mutation_state(platform, table):
    db, *_ = platform
    with db.begin() as uow:
        uow.connection.execute(
            f"CREATE TRIGGER platform_test_failure BEFORE INSERT ON {table} "
            "BEGIN SELECT RAISE(ABORT,'synthetic storage failure'); END;"
        )
        uow.commit()
    published = []
    with pytest.raises(sqlite3.IntegrityError):
        execute(coordinator(platform), context(platform), uuid4(), publish=published.append)
    assert counts(db) == (0, 0, 0, 0, 0)
    assert published == []


def test_failed_commit_has_no_receipt_success_or_publication(platform):
    db, *_ = platform
    with db.begin() as uow:
        uow.connection.execute(
            "CREATE TABLE platform_test_deferred(id TEXT REFERENCES platform_sessions(id) "
            "DEFERRABLE INITIALLY DEFERRED)"
        )
        uow.commit()

    def invalid_commit(ctx, payload, uow):
        record = event(ctx, payload.statement)
        uow.repository("source_events").append(ctx, record)
        uow.connection.execute("INSERT INTO platform_test_deferred VALUES ('absent')")
        return record

    published = []
    with pytest.raises(sqlite3.IntegrityError):
        execute(
            coordinator(platform, invalid_commit),
            context(platform),
            uuid4(),
            publish=published.append,
        )
    assert counts(db) == (0, 0, 0, 0, 0)
    assert published == []


def test_evidence_audit_receipt_and_event_rollback_share_one_uow(platform):
    from flowlens.contracts.models import Evidence

    db, *_ = platform
    ctx = context(platform)
    source_id = uuid4()
    with db.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_sources VALUES (?,?,?,?,?)",
            (str(ctx.session_id), str(source_id), 1, "a" * 64, "{}"),
        )
        uow.connection.execute(
            "CREATE TRIGGER platform_test_receipt_failure "
            "BEFORE INSERT ON platform_mutation_receipts "
            "BEGIN SELECT RAISE(ABORT,'receipt failure'); END;"
        )
        uow.commit()

    def write_with_evidence(ctx, payload, uow):
        record = event(ctx, payload.statement)
        uow.repository("source_events").append(ctx, record)
        evidence = Evidence(
            id=uuid4(),
            session_id=ctx.session_id,
            analysis_run_id=ctx.analysis_run_id,
            revision=ctx.input_revision,
            kind="EVENT",
            source_id=source_id,
            segment_id=None,
            start_ms=None,
            end_ms=None,
            quote=None,
            span_start=None,
            span_end=None,
            source_hash="a" * 64,
        )
        uow.repository("evidence").append(ctx, evidence)
        return record

    with pytest.raises(sqlite3.IntegrityError):
        execute(coordinator(platform, write_with_evidence), ctx, uuid4())
    assert counts(db) == (0, 0, 0, 0, 0)
    with db.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 0


def test_mutation_receipts_cannot_be_changed_removed_or_replaced(platform):
    ctx, service = context(platform), coordinator(platform)
    execute(service, ctx, uuid4())
    for sql in (
        "UPDATE platform_mutation_receipts SET version=99",
        "DELETE FROM platform_mutation_receipts",
        "INSERT OR REPLACE INTO platform_mutation_receipts "
        "SELECT * FROM platform_mutation_receipts",
    ):
        with platform[0].begin() as uow, pytest.raises(sqlite3.DatabaseError):
            uow.connection.execute(sql)
    assert counts(platform[0]) == (1, 1, 1, 1, 1)


def test_upgrade_preserves_existing_audit_and_adds_protection(tmp_path):
    from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

    path = tmp_path / "upgrade.db"
    with Database(
        path,
        migrations=PLATFORM_MIGRATIONS[
            : next(
                index
                for index, spec in enumerate(PLATFORM_MIGRATIONS)
                if spec.id == "platform.0007"
            )
        ],
    ) as db:
        with db.begin() as uow:
            sid = str(uuid4())
            uow.connection.execute("INSERT INTO platform_sessions VALUES (?)", (sid,))
            uow.connection.execute(
                "INSERT INTO platform_audit VALUES "
                "(1,?,'actor','request','HISTORICAL','target','2026-10-09T00:00:00+00:00')",
                (sid,),
            )
            uow.commit()
    with Database(path) as db:
        with db.begin() as uow:
            assert (
                uow.connection.execute("SELECT action FROM platform_audit").fetchone()[0]
                == "HISTORICAL"
            )
            assert uow.connection.execute("PRAGMA foreign_key_check").fetchall() == []
            with pytest.raises(sqlite3.DatabaseError):
                uow.connection.execute("DELETE FROM platform_audit")
    # Triggers still enforce append-only data on independent SQLite connections.
    with sqlite3.connect(path) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE platform_audit SET action='TAMPERED'")


def test_callback_without_persisted_result_cannot_report_success(platform):
    service = coordinator(platform, lambda ctx, payload, uow: event(ctx, payload.statement))
    with pytest.raises(ContractError, match="EVIDENCE_UNAVAILABLE"):
        execute(service, context(platform), uuid4())
    assert counts(platform[0]) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("bad", [-1, True, "1", 2**63 - 1])
def test_invalid_expected_version_has_no_effect(platform, bad):
    with pytest.raises(ContractError, match="INVALID_INPUT"):
        execute(coordinator(platform), context(platform), uuid4(), version=bad)
    assert counts(platform[0]) == (0, 0, 0, 0, 0)


def test_receipt_and_audit_store_hashes_and_ids_without_raw_key_or_body(platform):
    service, ctx, target = coordinator(platform), context(platform), uuid4()
    execute(
        service,
        ctx,
        target,
        key="synthetic-private-idempotency-key",
        statement="synthetic-private-note",
    )
    with platform[0].begin() as uow:
        for table in ("platform_mutation_receipts", "platform_audit"):
            rows = [tuple(row) for row in uow.connection.execute(f"SELECT * FROM {table}")]
            assert "synthetic-private" not in repr(rows)
        row = uow.connection.execute(
            "SELECT key_hash,request_hash FROM platform_mutation_receipts"
        ).fetchone()
        assert all(len(value) == 64 for value in row)


def test_review_only_callback_uses_registered_repository_ports_without_analysis_grant(platform):
    from flowlens.storage.sqlite.mutations import MutationOperation, Mutations

    db, permissions, auth, sid, *_ = platform
    permissions.revoke(auth.token.get_secret_value(), auth.account.id, sid, "analysis")
    ctx = context(platform)
    stored = []

    class FakeReviewRepository:
        def __init__(self, connection, check_open):
            self.connection, self.check_open = connection, check_open

        def append(self, ctx, record):
            self.check_open()
            ctx.require("review", ctx.session_id, ctx.analysis_run_id)
            self.connection.execute(
                "INSERT INTO platform_records VALUES (?,?,?,?,?,?,?)",
                (
                    "analysis.review",
                    str(record.id),
                    str(ctx.session_id),
                    str(ctx.analysis_run_id),
                    ctx.input_revision,
                    "SourceEvent",
                    record.model_dump_json(),
                ),
            )
            return record.id

        def get(self, ctx, record_id):
            self.check_open()
            row = self.connection.execute(
                "SELECT payload FROM platform_records WHERE namespace='analysis.review' AND id=?",
                (str(record_id),),
            ).fetchone()
            return SourceEvent.model_validate_json(row[0])

    db.repositories["analysis.review"] = FakeReviewRepository

    def apply(ctx, payload, uow):
        record = event(ctx, payload.statement)
        uow.repository("analysis.review").append(ctx, record)
        stored.append(record.id)
        return record

    spec = MutationOperation(
        name="REVIEW_NOTE",
        namespace="analysis.notes",
        repository_namespace="analysis.review",
        capability="review",
        payload_type=NoteInput,
        apply=apply,
    )
    service = Mutations(db, operations=(spec,))
    result = service.execute(
        ctx,
        "REVIEW_NOTE",
        target_id=uuid4(),
        key="review-key",
        expected_version=0,
        payload=NoteInput(statement="review note"),
    )
    assert "analysis" not in ctx.capabilities
    assert result.record_id == stored[0]
    assert counts(db) == (1, 1, 1, 1, 1)


def test_http_mutation_retry_conflicts_and_failure_never_returns_saved_success(platform):
    from dataclasses import asdict

    from fastapi import APIRouter, Request
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.auth.transport import http_context
    from flowlens.core.host_config import HostSettings
    from flowlens.core.modules import ModuleRegistration
    from flowlens.storage.sqlite.mutations import MutationOperation

    db, _, auth, sid, run, _, now = platform
    path = db.path
    db.close()
    router, failures = APIRouter(), [False]

    def apply(ctx, payload, uow):
        record = event(ctx, payload.statement)
        uow.repository("source_events").append(ctx, record)
        if failures[0]:
            raise RuntimeError("private password /private/audio.wav SELECT")
        return record

    spec = MutationOperation(
        name="ADD_NOTE",
        namespace="platform.note",
        repository_namespace="source_events",
        capability="analysis",
        payload_type=NoteInput,
        apply=apply,
    )

    @router.post("/api/v1/sessions/{session_id}/notes/{target_id}")
    def note(
        request: Request,
        session_id: UUID,
        target_id: UUID,
        payload: NoteInput,
        expected_version: int = 0,
    ):
        ctx = http_context(request, session_id, run_id=run, required="analysis")
        return asdict(
            request.app.state.mutations.execute(
                ctx,
                "ADD_NOTE",
                target_id=target_id,
                key=request.headers.get("Idempotency-Key", ""),
                expected_version=expected_version,
                payload=payload,
            )
        )

    app = create_host(
        HostSettings(profile="test", database_path=path),
        modules=(ModuleRegistration("mutation-probe", mock=True, routes=(router,)),),
        mutation_operations=(spec,),
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        app.state.sessions.clock = lambda: now[0]
        client.cookies.set("flowlens_session", auth.token.get_secret_value())
        headers = {
            "Origin": app.state.settings.origin,
            "X-CSRF-Token": auth.csrf_token,
            "Idempotency-Key": "http-key",
        }
        url = f"/api/v1/sessions/{sid}/notes/{uuid4()}"
        first = client.post(url, headers=headers, json={"statement": "synthetic note"})
        assert first.status_code == 200
        assert (
            client.post(url, headers=headers, json={"statement": "synthetic note"}).json()
            == first.json()
        )
        conflict = client.post(url, headers=headers, json={"statement": "different"})
        assert conflict.status_code == 409 and conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
        conflict = client.post(
            url, headers={**headers, "Idempotency-Key": "new-key"}, json={"statement": "different"}
        )
        assert conflict.status_code == 409 and conflict.json()["code"] == "VERSION_CONFLICT"
        failures[0] = True
        failed = client.post(
            url + "?expected_version=1",
            headers={**headers, "Idempotency-Key": "new-key"},
            json={"statement": "different"},
        )
        assert failed.status_code == 500 and failed.json()["code"] == "INTERNAL_ERROR"
        assert all(value not in failed.text for value in ("private password", "/private", "SELECT"))
        assert counts(app.state.transactions) == (1, 1, 1, 1, 1)
        assert client.get("/ready").status_code == 503
    assert app.state.mutations is None and app.state.transactions is None


def test_independent_connection_cannot_replace_receipt_with_a_new_id(platform):
    ctx = context(platform)
    execute(coordinator(platform), ctx, uuid4())
    with sqlite3.connect(platform[0].path) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT OR REPLACE INTO platform_mutation_receipts "
            "SELECT ?,session_id,run_scope,run_id,revision,actor_id,operation,namespace,target_id,"
            "key_hash,request_hash,version,sequence,record_id,audit_id "
            "FROM platform_mutation_receipts",
            (str(uuid4()),),
        )
