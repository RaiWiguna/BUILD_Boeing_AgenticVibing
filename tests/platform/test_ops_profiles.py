"""A09.2 admin metadata versions and frozen fake diagnostics never prove providers."""

import importlib
from uuid import uuid4

import pytest
from flowlens.contracts.models import ProviderProfile
from flowlens.core.errors import ContractError
from test_imports import importer as importer


def profile(**changes):
    return ProviderProfile(
        id=uuid4(),
        provider="GEMINI",
        model="gemini-3.8-flash",
        transport="GEMINI_DEVELOPER_INTERACTIONS",
        version="synthetic-config-1",
        region=None,
        locale=None,
        timeout_seconds=60,
        readiness="UNVERIFIED",
        **changes,
    )


class FakeAdapter:
    def check(self, p):
        return p.model_copy(update={"readiness": "READY"})

    def transcribe(self, context, lease, audio):
        raise AssertionError("A09.2 must not transcribe")

    def extract(self, context, segments):
        raise AssertionError("A09.2 must not extract")


def service(importer, adapter=None):
    module = importlib.import_module("flowlens.ops.providers")
    registered = (
        {} if adapter is None else {"GEMINI": module.AdapterBinding(adapter=adapter, mock=True)}
    )
    return module.Providers(
        importer[0].database, importer[0].sessions, adapters=registered, allow_mock=True
    )


def test_versioned_admin_profile_mock_check_and_idempotency(importer):
    s = service(importer, FakeAdapter())
    token = importer[1].token.get_secret_value()
    p = profile()
    first = s.save(token, p, expected_version=0, key="create")
    assert first.revision == 1 and first.verification == "UNVERIFIED"
    assert first == s.save(token, p, expected_version=0, key="create")
    checked = s.check(token, p.id, expected_version=1, key="check")
    assert checked.verification == "MOCK" and checked.profile.readiness == "READY"
    assert checked.provider_verified is False
    assert checked == s.check(token, p.id, expected_version=1, key="check")
    second = s.save(
        token,
        p.model_copy(update={"version": "synthetic-config-2"}),
        expected_version=1,
        key="update",
    )
    assert second.revision == 2 and second.profile.readiness == "UNVERIFIED"
    assert second.config_hash != first.config_hash
    with pytest.raises(ContractError):
        s.check(token, p.id, expected_version=1, key="stale")
    assert len(s.history(token, p.id)) == 2


@pytest.mark.parametrize(
    "value", ["https://secret.example/key", "raw transcript content", "AIza" + "x" * 35]
)
def test_untrusted_profile_metadata_is_rejected_without_persistence(importer, value):
    s = service(importer)
    with pytest.raises(ContractError):
        s.save(
            importer[1].token.get_secret_value(),
            profile().model_copy(update={"model": value}),
            expected_version=0,
            key="unsafe",
        )
    assert s.inventory(importer[1].token.get_secret_value()) == []


def test_exception_and_returned_profile_mutation_are_sanitized(importer):
    class Bad:
        def check(self, p):
            raise RuntimeError("secret-key raw transcript /private/path")

    s = service(importer, Bad())
    token = importer[1].token.get_secret_value()
    p = profile()
    s.save(token, p, expected_version=0, key="create")
    outcome = s.check(token, p.id, expected_version=1, key="failure")
    assert (
        outcome.profile.readiness == "UNAVAILABLE" and outcome.failure_code == "ADAPTER_UNAVAILABLE"
    )
    assert "secret-key" not in outcome.model_dump_json()


def test_no_adapter_cannot_be_labelled_verified(importer):
    s = service(importer)
    token = importer[1].token.get_secret_value()
    p = profile()
    s.save(token, p, expected_version=0, key="create")
    result = s.check(token, p.id, expected_version=1, key="check")
    assert result.failure_code == "ADAPTER_NOT_CONFIGURED" and not result.provider_verified


def test_binding_options_mismatch_and_mutated_return_are_not_trusted(importer):
    from flowlens.ops.providers import ProviderOptions

    token = importer[1].token.get_secret_value()
    p = profile()
    s = service(importer, FakeAdapter())
    first = s.save(
        token, p, options=ProviderOptions(terms_profile="PAID"), expected_version=0, key="create"
    )
    assert first.options.terms_profile == "PAID"
    assert s.check(token, p.id, expected_version=1, key="check").failure_code == "CONFIG_NOT_BOUND"

    class Mutating:
        def check(self, p):
            return p.model_copy(update={"model": "private-transcript", "readiness": "READY"})

    other = profile()
    bad = service(importer, Mutating())
    bad.save(token, other, expected_version=0, key="create-other")
    result = bad.check(token, other.id, expected_version=1, key="other-check")
    assert result.failure_code == "INVALID_DIAGNOSTIC"
    assert "private-transcript" not in result.model_dump_json()


def test_check_revalidates_admin_and_revision_after_callback(importer):
    token = importer[1].token.get_secret_value()
    p = profile()
    calls = []

    class Racing:
        def check(self, value):
            # This transaction proves callback executes outside A's DB lock.
            s.save(
                token, p.model_copy(update={"version": "changed"}), expected_version=1, key="race"
            )
            calls.append(True)
            return value.model_copy(update={"readiness": "READY"})

    s = service(importer, Racing())
    s.save(token, p, expected_version=0, key="create")
    with pytest.raises(ContractError):
        s.check(token, p.id, expected_version=1, key="check")
    assert calls == [True]
    assert s.inventory(token)[0].revision == 2
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_provider_checks").fetchone()[0]
            == 0
        )


def test_profile_audit_failure_rolls_back_config_and_receipt(importer):
    import sqlite3

    s = service(importer)
    token = importer[1].token.get_secret_value()
    p = profile()
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "CREATE TRIGGER synthetic_ops_failure BEFORE INSERT ON "
            "platform_ops_audit BEGIN SELECT RAISE(ABORT,'synthetic failure'); END;"
        )
        uow.commit()
    with pytest.raises(sqlite3.IntegrityError):
        s.save(token, p, expected_version=0, key="create")
    assert s.inventory(token) == []
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_ops_requests").fetchone()[0] == 0
        )
        uow.connection.execute("DROP TRIGGER synthetic_ops_failure")
        uow.commit()
    assert s.save(token, p, expected_version=0, key="create").revision == 1


def test_provider_profile_survives_schema_upgrade_and_owner_restart(tmp_path):
    from flowlens.auth.accounts import Accounts
    from flowlens.auth.sessions import Sessions
    from flowlens.ops.providers import Providers
    from flowlens.storage.sqlite.database import Database
    from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS
    from pydantic import SecretStr

    path = tmp_path / "db" / "data.sqlite"
    with Database(path, migrations=PLATFORM_MIGRATIONS[:16]) as db:
        accounts = Accounts(db)
        actor = accounts.bootstrap("admin", SecretStr("synthetic-initial-password"))
        accounts.change_password(
            actor.id,
            SecretStr("synthetic-initial-password"),
            SecretStr("synthetic-changed-password"),
        )
        auth = Sessions(db, accounts, clock=lambda: 1000).login(
            "admin", SecretStr("synthetic-changed-password"), "local"
        )
        token = auth.token.get_secret_value()
    p = profile()
    with Database(path) as db:
        sessions = Sessions(db, Accounts(db), clock=lambda: 1000)
        s = Providers(db, sessions)
        created = s.save(token, p, expected_version=0, key="create")
    with Database(path) as db:
        s = Providers(db, Sessions(db, Accounts(db), clock=lambda: 1000))
        assert s.inventory(token) == [created]
        assert s.history(token, p.id) == [created]


def test_admin_revoked_during_diagnostic_cannot_commit(importer):
    token = importer[1].token.get_secret_value()
    p = profile()

    class Revoking:
        def check(self, value):
            with importer[0].database.begin() as uow:
                uow.connection.execute(
                    "UPDATE platform_accounts SET is_admin=0 WHERE id=?",
                    (str(importer[1].account.id),),
                )
                uow.commit()
            return value.model_copy(update={"readiness": "READY"})

    s = service(importer, Revoking())
    s.save(token, p, expected_version=0, key="create")
    with pytest.raises(ContractError):
        s.check(token, p.id, expected_version=1, key="check")
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_provider_checks").fetchone()[0]
            == 0
        )


def test_secret_signature_in_other_metadata_fields_is_rejected(importer):
    s = service(importer)
    token = importer[1].token.get_secret_value()
    with pytest.raises(ContractError):
        s.save(
            token,
            profile().model_copy(update={"version": "ghp_" + "x" * 36}),
            expected_version=0,
            key="unsafe-version",
        )
    assert s.inventory(token) == []
