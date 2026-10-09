"""Authorization is checked from durable state, never caller-provided DTOs."""

from uuid import uuid4

import pytest
from flowlens.auth.accounts import Accounts
from flowlens.auth.permissions import Permissions
from flowlens.auth.sessions import Sessions
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import Database
from pydantic import SecretStr


@pytest.fixture
def policy(tmp_path):
    now = [1000]
    with Database(tmp_path / "permissions.db") as db:
        accounts = Accounts(db)
        admin = accounts.bootstrap("admin", SecretStr("synthetic-password-initial"))
        accounts.change_password(
            admin.id,
            SecretStr("synthetic-password-initial"),
            SecretStr("synthetic-password-changed"),
        )
        sessions = Sessions(db, accounts, clock=lambda: now[0])
        auth = sessions.login("admin", SecretStr("synthetic-password-changed"), "local")
        service = Permissions(db, sessions)
        db.context_guard = service.enforce
        session, other, run = uuid4(), uuid4(), uuid4()
        with db.begin() as uow:
            for sid in (session, other):
                uow.connection.execute("INSERT INTO platform_sessions VALUES (?)", (str(sid),))
                uow.connection.execute(
                    "INSERT INTO platform_revisions VALUES (?,1,?)", (str(sid), "a" * 64)
                )
                uow.connection.execute(
                    "INSERT INTO platform_context_state VALUES (?,500,?)", (str(sid), "AS_KNOWN")
                )
            uow.connection.execute(
                "INSERT INTO platform_runs VALUES (?,?,1)", (str(session), str(run))
            )
            uow.commit()
        yield service, auth, session, other, run, now


def grant(p, capability="read", role="evaluator", expires_ms=10000):
    service, auth, session, *_ = p
    service.grant(
        auth.token.get_secret_value(),
        auth.account.id,
        session,
        capability,
        role=role,
        expires_ms=expires_ms,
    )


def context(p, **kw):
    service, auth, session, *_ = p
    return service.human_context(auth.token.get_secret_value(), session, **kw)


def test_admin_has_no_implicit_domain_access(policy):
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        context(policy)
    grant(policy)
    ctx = context(policy)
    assert ctx.capabilities == ["read"]
    assert ctx.as_of_ms == 500 and ctx.input_hash == "a" * 64
    assert ctx.actor_id == policy[1].account.id


@pytest.mark.parametrize("capability", ["audio", "export", "truth", "review", "analysis"])
def test_read_does_not_imply_sensitive_capabilities(policy, capability):
    grant(policy)
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        context(policy, required=capability)


def test_scope_and_client_forgery_denied(policy):
    grant(policy)
    service, auth, session, other, run, _ = policy
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.human_context(auth.token.get_secret_value(), other)
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        context(policy, run_id=uuid4())
    ctx = context(policy, run_id=run)
    for forged in (
        ctx.model_copy(update={"capabilities": ["read", "truth"]}),
        ctx.model_copy(update={"session_id": other}),
        ctx.model_copy(update={"as_of_ms": 999}),
        ctx.model_copy(update={"request_id": uuid4()}),
    ):
        with service.database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
            service.enforce(uow, forged)
    with service.database.begin() as uow:
        service.enforce(uow, ctx)


@pytest.mark.parametrize("cause", ["revoke", "expiry", "logout", "reset"])
def test_cached_context_revalidated_on_use(policy, cause):
    grant(policy)
    ctx = context(policy)
    service, auth, session, _, _, now = policy
    if cause == "revoke":
        service.revoke(auth.token.get_secret_value(), auth.account.id, session, "read")
    elif cause == "expiry":
        now[0] = 10000
    elif cause == "logout":
        service.sessions.logout(auth.token.get_secret_value())
    else:
        service.sessions.accounts.reset_password(
            auth.account.id, auth.account.id, SecretStr("synthetic-reset-password")
        )
    with service.database.begin() as uow, pytest.raises(ContractError):
        uow.repository("source_events").get(ctx, uuid4())


def test_truth_requires_evaluator_and_debrief(policy):
    grant(policy)
    with pytest.raises(ContractError, match="INVALID_INPUT"):
        grant(policy, "truth", role="observer")
    grant(policy, "truth")
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        context(policy, required="truth")
    service, _, sid, *_ = policy
    with service.database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_context_state SET mode='DEBRIEF' WHERE session_id=?", (str(sid),)
        )
        uow.commit()
    assert "truth" in context(policy, required="truth").capabilities


def test_worker_scope_is_separate_and_least_privilege(policy):
    grant(policy)
    grant(policy, "analysis")
    service, auth, sid, other, run, now = policy
    worker = service.provision_worker(auth.token.get_secret_value(), expires_ms=10000)
    scope = service.bind_worker(auth.token.get_secret_value(), worker.id, sid, run, expires_ms=9000)
    ctx = service.worker_context(worker.token.get_secret_value(), scope)
    assert set(ctx.capabilities) == {"read", "analysis", "worker"}
    assert ctx.mode == "AS_KNOWN" and ctx.session_id == sid
    assert not {"truth", "admin", "export", "audio", "review"} & set(ctx.capabilities)
    with pytest.raises(ContractError):
        service.human_context(worker.token.get_secret_value(), sid)
    with pytest.raises(ContractError):
        service.worker_context(auth.token.get_secret_value(), scope)
    with pytest.raises(ContractError):
        service.bind_worker(auth.token.get_secret_value(), worker.id, other, run, expires_ms=9000)
    service.revoke_worker(auth.token.get_secret_value(), worker.id)
    with service.database.begin() as uow, pytest.raises(ContractError):
        service.enforce(uow, ctx)


def test_scope_revision_change_rejects_old_context(policy):
    grant(policy)
    ctx = context(policy)
    service, _, sid, *_ = policy
    with service.database.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_revisions VALUES (?,2,?)", (str(sid), "b" * 64)
        )
        uow.commit()
    with (
        service.database.begin() as uow,
        pytest.raises(ContractError, match="SOURCE_REVISION_CHANGED"),
    ):
        service.enforce(uow, ctx)


def test_nonadmin_cannot_grant_and_grant_is_audited(policy):
    grant(policy)
    service, auth, *_ = policy
    with service.database.begin() as uow:
        assert (
            uow.connection.execute("SELECT action FROM platform_permission_audit").fetchone()[0]
            == "GRANT"
        )
        uow.connection.execute(
            "UPDATE platform_accounts SET is_admin=0 WHERE id=?", (str(auth.account.id),)
        )
        uow.commit()
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        grant(policy, "audio")


def seed_source(policy):
    from pathlib import Path

    from flowlens.contracts.models import SourceManifest

    service, _, sid, *_ = policy
    manifest = SourceManifest.model_validate_json(
        Path("contracts/examples/manifest.json").read_text()
    )
    manifest = manifest.model_copy(update={"session_id": sid})
    with service.database.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_sources VALUES (?,?,?,?,?)",
            (str(sid), str(manifest.id), 1, manifest.source_hash, manifest.model_dump_json()),
        )
        asset = manifest.assets[0]
        uow.connection.execute(
            "INSERT INTO platform_assets VALUES (?,?,?,?,?,?)",
            (str(sid), str(asset.id), str(manifest.id), 1, "private/synthetic.wav", asset.sha256),
        )
        uow.commit()
    return manifest


def test_human_asset_access_requires_explicit_audio(policy):
    grant(policy)
    source = seed_source(policy)
    service, *_ = policy
    ctx = context(policy)
    with service.database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.authorize_asset(uow, ctx, source.assets[0].id)
    grant(policy, "audio")
    ctx = context(policy)
    with service.database.begin() as uow:
        asset = service.authorize_asset(uow, ctx, source.assets[0].id)
        assert asset.sha256 == source.assets[0].sha256
        assert asset.fixture_path is None
        assert "private/" not in asset.model_dump_json()


@pytest.mark.parametrize(
    "right, kwargs, code",
    [
        ("local", {}, "SOURCE_PERMISSION_REQUIRED"),
        ("cloud", {"cloud": True}, "CLOUD_TRANSFER_BLOCKED"),
        ("export", {"export": True}, "SOURCE_PERMISSION_REQUIRED"),
        ("audio_export", {"audio_export": True}, "SOURCE_PERMISSION_REQUIRED"),
    ],
)
def test_source_rights_rechecked_on_use(policy, right, kwargs, code):
    for capability in ("read", "audio", "export", "analysis"):
        grant(policy, capability)
    source = seed_source(policy)
    service, *_ = policy
    ctx = context(policy)
    with service.database.begin() as uow:
        assert service.require_source_rights(uow, ctx, source.id, **kwargs).id == source.id
        denied = source.model_copy(
            update={"permissions": source.permissions.model_copy(update={right: False})}
        )
        uow.connection.execute(
            "UPDATE platform_sources SET payload=? WHERE session_id=? AND id=?",
            (denied.model_dump_json(), str(ctx.session_id), str(source.id)),
        )
        uow.commit()
    with service.database.begin() as uow, pytest.raises(ContractError, match=code):
        service.require_source_rights(uow, ctx, source.id, **kwargs)


@pytest.mark.parametrize(
    "cause", ["scope_revoke", "scope_expiry", "worker_expiry", "context_expiry"]
)
def test_worker_cached_context_expires_and_revokes(policy, cause):
    grant(policy)
    grant(policy, "analysis")
    service, auth, sid, _, run, now = policy
    worker = service.provision_worker(auth.token.get_secret_value(), expires_ms=1000000)
    scope = service.bind_worker(
        auth.token.get_secret_value(), worker.id, sid, run, expires_ms=900000
    )
    ctx = service.worker_context(worker.token.get_secret_value(), scope)
    if cause == "scope_revoke":
        service.revoke_scope(auth.token.get_secret_value(), scope)
    else:
        now[0] = {"scope_expiry": 900000, "worker_expiry": 1000000, "context_expiry": 301000}[cause]
    with service.database.begin() as uow, pytest.raises(ContractError):
        service.enforce(uow, ctx)
    if cause == "context_expiry":
        assert service.worker_context(worker.token.get_secret_value(), scope).session_id == sid
    elif cause != "scope_revoke":
        with pytest.raises(ContractError):
            service.worker_context(worker.token.get_secret_value(), scope)


def test_worker_only_bound_sources_and_assets_no_inventory(policy):
    grant(policy)
    grant(policy, "analysis")
    source = seed_source(policy)
    service, auth, sid, _, run, _ = policy
    worker = service.provision_worker(auth.token.get_secret_value(), expires_ms=10000)
    empty = service.bind_worker(auth.token.get_secret_value(), worker.id, sid, run, expires_ms=9000)
    ctx = service.worker_context(worker.token.get_secret_value(), empty)
    with service.database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.require_source_rights(uow, ctx, source.id)
    with service.database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.authorize_asset(uow, ctx, source.assets[0].id)
    scope = service.bind_worker(
        auth.token.get_secret_value(),
        worker.id,
        sid,
        run,
        expires_ms=9000,
        asset_ids=(source.assets[0].id,),
    )
    ctx = service.worker_context(worker.token.get_secret_value(), scope)
    with service.database.begin() as uow:
        assert service.authorize_asset(uow, ctx, source.assets[0].id).fixture_path is None
        assert service.require_source_rights(uow, ctx, source.id, cloud=True).id == source.id
        assert worker.token.get_secret_value() not in str(
            uow.connection.execute("SELECT * FROM platform_workers").fetchall()
        )
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.bind_worker(
            auth.token.get_secret_value(),
            worker.id,
            sid,
            run,
            expires_ms=9000,
            asset_ids=(uuid4(),),
        )
    with service.database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_worker_scopes").fetchone()[0] == 2
        )


def test_old_nullable_grants_fail_closed_and_missing_state_denied(policy):
    service, auth, sid, *_ = policy
    with service.database.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_grants(account_id,session_id,capability) VALUES (?,?,?)",
            (str(auth.account.id), str(sid), "read"),
        )
        uow.commit()
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        context(policy)
    grant(policy)
    with service.database.begin() as uow:
        uow.connection.execute("DELETE FROM platform_context_state WHERE session_id=?", (str(sid),))
        uow.commit()
    with pytest.raises(ContractError, match="NOT_EVALUABLE"):
        context(policy)


def test_host_attaches_live_guard_to_injected_repositories(tmp_path):
    from pathlib import Path

    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.contracts.models import RequestContext
    from flowlens.core.host_config import HostSettings

    app = create_host(HostSettings(profile="test", database_path=tmp_path / "host.db"))
    touched = []

    class FakeRepository:
        def get(self, context, record_id):
            touched.append(record_id)
            raise AssertionError("forged caller reached repository")

        def append(self, context, record):
            raise AssertionError("forged caller reached repository")

    with TestClient(app):
        database = app.state.transactions
        database.repositories["analysis.test"] = lambda connection, check_open: FakeRepository()
        ctx = RequestContext.model_validate_json(
            Path("contracts/examples/context.json").read_text()
        )
        with database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
            uow.repository("analysis.test").get(ctx, uuid4())
        with database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
            uow.audit(ctx, "READ", uuid4())
        with database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
            uow.enqueue_event(ctx, ctx)
        assert touched == []
    assert app.state.permissions is None


def test_repository_cross_run_and_rollback_use_real_context(policy):
    import json
    from pathlib import Path

    from flowlens.contracts.models import SourceEvent

    grant(policy)
    grant(policy, "analysis")
    service, _, sid, _, run, _ = policy
    ctx = context(policy, run_id=run)
    template = SourceEvent.model_validate_json(
        json.dumps(json.loads(Path("contracts/examples/events.json").read_text())[0])
    )
    record = template.model_copy(update={"session_id": sid, "analysis_run_id": run})
    with service.database.begin() as uow:
        uow.repository("source_events").append(ctx, record)
        assert uow.repository("source_events").get(ctx, record.id) == record
        # Implicit rollback keeps domain and event effects out of durable state.
        uow.enqueue_event(ctx, record)
    with service.database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_records").fetchone()[0] == 0
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_events").fetchone()[0] == 0
        uow.repository("source_events").append(ctx, record)
        uow.commit()
    with service.database.begin() as uow:
        another = uuid4()
        uow.connection.execute("INSERT INTO platform_runs VALUES (?,?,1)", (str(sid), str(another)))
        uow.commit()
    different = context(policy, run_id=another)
    with service.database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        uow.repository("source_events").get(different, record.id)


def test_failed_grant_audit_rolls_back_permission(policy):
    import sqlite3

    service, _, sid, *_ = policy
    with service.database.begin() as uow:
        uow.connection.execute(
            "CREATE TRIGGER fail_permission_audit BEFORE INSERT ON platform_permission_audit "
            "BEGIN SELECT RAISE(ABORT,'synthetic audit failure'); END"
        )
        uow.commit()
    with pytest.raises(sqlite3.IntegrityError):
        grant(policy)
    with service.database.begin() as uow:
        assert (
            uow.connection.execute(
                "SELECT COUNT(*) FROM platform_grants WHERE session_id=?", (str(sid),)
            ).fetchone()[0]
            == 0
        )


def test_context_has_bounded_lifetime_and_rejects_clock_reversal(policy):
    grant(policy, expires_ms=1000000)
    service, _, _, _, _, now = policy
    ctx = context(policy)
    now[0] = 999
    with service.database.begin() as uow, pytest.raises(ContractError):
        service.enforce(uow, ctx)
    now[0] = 301000
    with service.database.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.enforce(uow, ctx)
    refreshed = context(policy)
    with service.database.begin() as uow:
        service.enforce(uow, refreshed)
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_context_receipts").fetchone()[0]
            == 1
        )


def test_worker_token_scope_cannot_cross_principal(policy):
    grant(policy)
    grant(policy, "analysis")
    service, auth, sid, _, run, _ = policy
    first = service.provision_worker(auth.token.get_secret_value(), expires_ms=10000)
    second = service.provision_worker(auth.token.get_secret_value(), expires_ms=10000)
    scope = service.bind_worker(auth.token.get_secret_value(), first.id, sid, run, expires_ms=9000)
    with pytest.raises(ContractError, match="AUTH_REQUIRED"):
        service.worker_context(second.token.get_secret_value(), scope)
    with service.database.begin() as uow:
        stored = uow.connection.execute(
            "SELECT token_hash FROM platform_workers WHERE id=?", (str(first.id),)
        ).fetchone()[0]
        assert len(stored) == 64 and stored != first.token.get_secret_value()
    assert first.token.get_secret_value() not in repr(first)


def test_upgrade_preserves_old_grants_without_escalation(tmp_path):
    from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

    path = tmp_path / "upgrade.db"
    account_id, sid = uuid4(), uuid4()
    with Database(
        path,
        migrations=PLATFORM_MIGRATIONS[
            : next(
                index
                for index, spec in enumerate(PLATFORM_MIGRATIONS)
                if spec.id == "platform.0006"
            )
        ],
    ) as db:
        with db.begin() as uow:
            uow.connection.execute(
                "INSERT INTO platform_accounts(id,login,password_hash,active) "
                "VALUES (?,'legacy','unused',1)",
                (str(account_id),),
            )
            uow.connection.execute("INSERT INTO platform_sessions VALUES (?)", (str(sid),))
            uow.connection.execute(
                "INSERT INTO platform_grants VALUES (?,?,'truth')", (str(account_id), str(sid))
            )
            uow.commit()
    with Database(path) as db:
        with db.begin() as uow:
            row = uow.connection.execute("SELECT * FROM platform_grants").fetchone()
            assert (
                row["capability"] == "truth"
                and row["role"] == "observer"
                and row["expires_ms"] is None
            )
            assert uow.connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_receipt_and_revocation_persist_across_owner_restart(policy):
    grant(policy)
    service, auth, sid, _, _, now = policy
    ctx = context(policy)
    path = service.database.path
    service.database.close()
    with Database(path) as reopened:
        permissions = Permissions(
            reopened, Sessions(reopened, Accounts(reopened), clock=lambda: now[0])
        )
        reopened.context_guard = permissions.enforce
        with reopened.begin() as uow:
            permissions.enforce(uow, ctx)
        permissions.revoke(auth.token.get_secret_value(), auth.account.id, sid, "read")
        with reopened.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
            permissions.enforce(uow, ctx)


def test_audio_export_also_requires_general_export_right(policy):
    for capability in ("read", "audio", "export"):
        grant(policy, capability)
    source = seed_source(policy)
    service, _, sid, *_ = policy
    ctx = context(policy)
    source = source.model_copy(
        update={"permissions": source.permissions.model_copy(update={"export": False})}
    )
    with service.database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_sources SET payload=? WHERE session_id=?",
            (source.model_dump_json(), str(sid)),
        )
        uow.commit()
    with (
        service.database.begin() as uow,
        pytest.raises(ContractError, match="SOURCE_PERMISSION_REQUIRED"),
    ):
        service.require_source_rights(uow, ctx, source.id, audio_export=True)


@pytest.mark.parametrize("cause", ["missing", "hash", "invalid", "session"])
def test_source_integrity_and_scope_fail_closed(policy, cause):
    grant(policy)
    source = seed_source(policy)
    service, _, sid, other, *_ = policy
    ctx = context(policy)
    with service.database.begin() as uow:
        if cause == "missing":
            source_id = uuid4()
        else:
            source_id = source.id
            payload = {
                "hash": source.model_copy(update={"source_hash": "b" * 64}).model_dump_json(),
                "invalid": "{}",
                "session": source.model_copy(update={"session_id": other}).model_dump_json(),
            }[cause]
            uow.connection.execute(
                "UPDATE platform_sources SET payload=? WHERE session_id=?", (payload, str(sid))
            )
            uow.commit()
    with (
        service.database.begin() as uow,
        pytest.raises(ContractError, match="SOURCE_PERMISSION_REQUIRED"),
    ):
        service.require_source_rights(uow, ctx, source_id)
