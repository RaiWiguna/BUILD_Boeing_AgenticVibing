"""Account lifecycle and private bootstrap on disposable real SQLite."""

import importlib
import json
import subprocess
import sys
from dataclasses import asdict
from uuid import UUID

import pytest
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import Database
from pydantic import SecretStr


def service(database):
    return importlib.import_module("flowlens.auth.accounts").Accounts(database)


def password(value="synthetic-password-one"):
    return SecretStr(value)


def test_bootstrap_is_once_and_passwords_are_argon2id_not_public(tmp_path):
    from argon2 import PasswordHasher

    with Database(tmp_path / "accounts.db") as database:
        accounts = service(database)
        admin = accounts.bootstrap("Admin", password())
        assert admin.login == "admin" and admin.is_admin and admin.active
        assert not admin.must_change_password
        UUID(str(admin.id))
        assert "password_hash" not in asdict(admin)
        with database.begin() as uow:
            encoded = uow.connection.execute(
                "SELECT password_hash FROM platform_accounts"
            ).fetchone()[0]
            assert encoded.startswith("$argon2id$")
            assert PasswordHasher().verify(encoded, password().get_secret_value())
            assert "synthetic-password" not in encoded
            assert uow.connection.execute("SELECT COUNT(*) FROM platform_grants").fetchone()[0] == 0
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            accounts.bootstrap("second", password())


@pytest.mark.parametrize(
    "login,secret",
    [
        ("bad login", password()),
        ("a", password()),
        ("admin", password("short")),
        ("admin", password("x" * 5000)),
    ],
)
def test_invalid_account_input_never_inserts_or_leaks(tmp_path, login, secret):
    with Database(tmp_path / "invalid.db") as database:
        with pytest.raises(ContractError, match="INVALID_INPUT") as error:
            service(database).bootstrap(login, secret)
        assert secret.get_secret_value() not in str(error.value)
        with database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_accounts").fetchone()[0] == 0
            )


def test_admin_create_and_reset_require_active_admin_and_force_password_change(tmp_path):
    with Database(tmp_path / "reset.db") as database:
        accounts = service(database)
        admin = accounts.bootstrap("admin", password())
        user = accounts.create(admin.id, "observer", password())
        assert user.must_change_password and not user.is_admin
        user = accounts.change_password(user.id, password(), password("synthetic-new-password"))
        prior = accounts.verify_credentials("observer", password("synthetic-new-password"))
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            accounts.reset_password(user.id, admin.id, password())
        reset = accounts.reset_password(admin.id, user.id, password("temporary-password-2"))
        assert reset.must_change_password
        assert reset.credential_version > prior.credential_version
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            accounts.require_access(user.id, prior.credential_version)
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            accounts.verify_credentials("observer", password("synthetic-new-password"))
        temporary = accounts.verify_credentials("observer", password("temporary-password-2"))
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            accounts.require_access(user.id, temporary.credential_version)
        changed = accounts.change_password(
            user.id, password("temporary-password-2"), password("permanent-password-3")
        )
        assert not changed.must_change_password
        assert accounts.require_access(user.id, changed.credential_version).id == user.id


def test_deactivation_is_durable_and_revokes_every_credential_snapshot(tmp_path):
    path = tmp_path / "deactivated.db"
    with Database(path) as database:
        accounts = service(database)
        admin = accounts.bootstrap("admin", password())
        user = accounts.create(admin.id, "observer", password())
        user = accounts.change_password(user.id, password(), password("changed-password-4"))
        accounts.deactivate(admin.id, user.id)
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            accounts.require_access(user.id, user.credential_version)
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            accounts.verify_credentials("observer", password("changed-password-4"))
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            accounts.change_password(user.id, password("changed-password-4"), password())
    with Database(path) as database:
        assert not service(database).get(user.id).active


def test_duplicates_last_admin_and_unknown_credentials_are_safe(tmp_path):
    with Database(tmp_path / "guards.db") as database:
        accounts = service(database)
        admin = accounts.bootstrap("admin", password())
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            accounts.create(admin.id, "ADMIN", password())
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            accounts.deactivate(admin.id, admin.id)
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            accounts.create(UUID(int=42), "intruder", password())
        for login in ("missing", "admin"):
            with pytest.raises(ContractError, match="AUTH_REQUIRED"):
                accounts.verify_credentials(login, password("wrong-password-123"))
        second = accounts.create(admin.id, "secondadmin", password(), is_admin=True)
        second = accounts.change_password(second.id, password(), password("second-password-234"))
        accounts.deactivate(second.id, admin.id)
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            accounts.create(admin.id, "intruder", password())
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            accounts.bootstrap("thirdadmin", password())


def test_password_hashing_occurs_without_a_write_transaction(tmp_path, monkeypatch):
    with Database(tmp_path / "unlocked.db") as database:
        accounts = service(database)
        real_hash = accounts.passwords.hash
        called = []

        def guarded(secret):
            assert database.active is False
            called.append(True)
            return real_hash(secret)

        monkeypatch.setattr(accounts.passwords, "hash", guarded)
        accounts.bootstrap("admin", password())
        assert called


def test_hash_corruption_is_fail_closed(tmp_path):
    with Database(tmp_path / "corrupt.db") as database:
        accounts = service(database)
        accounts.bootstrap("admin", password())
        with database.begin() as uow:
            uow.connection.execute("UPDATE platform_accounts SET password_hash='invalid'")
            uow.commit()
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            accounts.verify_credentials("admin", password())


def test_private_file_bootstrap_cli_and_safe_failure(tmp_path):
    secret = tmp_path / "bootstrap.secret"
    secret.write_text(password().get_secret_value() + "\n")
    secret.chmod(0o600)
    database = tmp_path / "bootstrap.db"
    command = [
        sys.executable,
        "-m",
        "flowlens.cli.bootstrap_admin",
        "--database",
        str(database),
        "--login",
        "admin",
        "--password-file",
        str(secret),
    ]
    first = subprocess.run(command, capture_output=True, text=True, timeout=15)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["login"] == "admin"
    second = subprocess.run(command, capture_output=True, text=True, timeout=15)
    assert second.returncode != 0
    assert "synthetic-password" not in first.stdout + first.stderr + second.stdout + second.stderr
    secret.chmod(0o644)
    command[command.index(str(database))] = str(tmp_path / "bad.db")
    insecure = subprocess.run(command, capture_output=True, text=True, timeout=15)
    assert insecure.returncode != 0
    assert not (tmp_path / "bad.db").exists()


def test_upgrade_preserves_existing_account_without_promoting_it(tmp_path):
    from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

    path = tmp_path / "upgrade.db"
    identifier = str(UUID(int=1))
    with Database(path, migrations=PLATFORM_MIGRATIONS[:3]) as database:
        with database.begin() as uow:
            uow.connection.execute(
                "INSERT INTO platform_accounts VALUES (?,?,?,?)",
                (identifier, "legacy", "unverified-old-hash", 1),
            )
            uow.commit()
    with Database(path) as database:
        account = service(database).get(UUID(identifier))
        assert not account.is_admin
        assert account.must_change_password


def test_account_and_bootstrap_marker_roll_back_if_audit_fails(tmp_path):
    import sqlite3

    with Database(tmp_path / "rollback.db") as database:
        accounts = service(database)
        with database.begin() as uow:
            uow.connection.execute("""CREATE TRIGGER platform_test_account_fault
                BEFORE INSERT ON platform_account_audit
                BEGIN SELECT RAISE(ABORT,'injected'); END;""")
            uow.commit()
        with pytest.raises(sqlite3.IntegrityError):
            accounts.bootstrap("admin", password())
        with database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_accounts").fetchone()[0] == 0
            )
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_security_state").fetchone()[0]
                == 0
            )
            uow.connection.execute("DROP TRIGGER platform_test_account_fault")
            uow.commit()
        accounts.bootstrap("admin", password())


def test_concurrent_bootstrap_has_exactly_one_admin(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    with Database(tmp_path / "race.db") as database:
        accounts = service(database)

        def bootstrap(login):
            try:
                return accounts.bootstrap(login, password()).login
            except ContractError as error:
                assert error.code == "VERSION_CONFLICT"
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(bootstrap, ("adminone", "admintwo")))
        assert sum(result is not None for result in results) == 1


def test_admin_credential_change_during_hashing_rejects_pending_mutation(tmp_path, monkeypatch):
    with Database(tmp_path / "race-reset.db") as database:
        accounts = service(database)
        admin = accounts.bootstrap("admin", password())
        original_hash = accounts.passwords.hash

        def interrupt(secret):
            encoded = original_hash(secret)
            with database.begin() as uow:
                uow.connection.execute(
                    "UPDATE platform_accounts SET credential_version=credential_version+1 "
                    "WHERE id=?",
                    (str(admin.id),),
                )
                uow.commit()
            return encoded

        monkeypatch.setattr(accounts.passwords, "hash", interrupt)
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            accounts.create(admin.id, "pending", password())


def test_real_hashes_use_distinct_salts_and_audit_contains_no_secrets(tmp_path):
    with Database(tmp_path / "salts.db") as database:
        accounts = service(database)
        admin = accounts.bootstrap("admin", password())
        accounts.create(admin.id, "observer", password())
        with database.begin() as uow:
            hashes = [
                row[0]
                for row in uow.connection.execute("SELECT password_hash FROM platform_accounts")
            ]
            assert hashes[0] != hashes[1]
            audit = [
                tuple(row) for row in uow.connection.execute("SELECT * FROM platform_account_audit")
            ]
            assert "synthetic-password" not in repr(audit)
            assert "$argon2" not in repr(audit)


def test_host_exposes_internal_account_service_only_during_lifespan(tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    app = create_host(HostSettings(profile="test", database_path=tmp_path / "host.db"))
    with TestClient(app) as client:
        assert app.state.accounts.database is app.state.transactions
        assert client.post("/api/v1/auth/login", json={}).status_code == 422
        assert client.get("/ready").status_code == 503
    assert app.state.accounts is None
