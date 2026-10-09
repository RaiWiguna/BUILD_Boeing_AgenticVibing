"""Opaque sessions and HTTP transport with deterministic time, real SQLite/Argon2."""

import importlib
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.auth.accounts import Accounts
from flowlens.core.errors import ContractError
from flowlens.core.host_config import HostSettings
from flowlens.storage.sqlite.database import Database
from pydantic import SecretStr

PASSWORD = "synthetic-session-password"


def sessions(database, accounts, clock):
    return importlib.import_module("flowlens.auth.sessions").Sessions(
        database, accounts, clock=clock
    )


@contextmanager
def client_app(tmp_path, https=False):
    origin = "https://localhost" if https else "http://127.0.0.1:8000"
    app = create_host(
        HostSettings(profile="test", database_path=tmp_path / "http.db", public_origin=origin)
    )
    with TestClient(app, base_url=origin) as client:
        app.state.accounts.bootstrap("admin", SecretStr(PASSWORD))
        yield app, client, origin


def login(client, origin, password=PASSWORD):
    return client.post(
        "/api/v1/auth/login",
        json={"login": "admin", "password": password},
        headers={"Origin": origin},
    )


def test_login_token_is_cookie_only_hashed_at_rest_and_logout_revokes(tmp_path):
    with client_app(tmp_path) as (app, client, origin):
        response = login(client, origin)
        assert response.status_code == 200
        token = client.cookies.get("flowlens_session")
        assert len(token) >= 40
        assert token not in response.text and PASSWORD not in response.text
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
        assert "Secure" not in cookie
        with app.state.transactions.begin() as uow:
            stored = uow.connection.execute(
                "SELECT token_hash FROM platform_auth_sessions"
            ).fetchone()[0]
            assert stored != token and len(stored) == 64
        snapshot = client.get("/api/v1/auth/session")
        assert snapshot.status_code == 200
        csrf = snapshot.json()["csrf_token"]
        logout = client.post(
            "/api/v1/auth/logout", headers={"Origin": origin, "X-CSRF-Token": csrf}
        )
        assert logout.status_code == 204
        assert client.get("/api/v1/auth/session").status_code == 401
        client.cookies.set("flowlens_session", token)
        assert client.get("/api/v1/auth/session").status_code == 401


def test_https_uses_secure_cookie_and_ignores_spoofed_forwarding(tmp_path):
    with client_app(tmp_path, https=True) as (_, client, origin):
        response = login(client, origin)
        assert response.status_code == 200
        assert "Secure" in response.headers["set-cookie"]
        assert client.get("/api/v1/auth/session").status_code == 200


@pytest.mark.parametrize("origin", [None, "null", "https://attacker.example"])
def test_login_origin_is_required_and_foreign_origin_does_not_create_session(tmp_path, origin):
    with client_app(tmp_path) as (app, client, _):
        headers = {} if origin is None else {"Origin": origin}
        response = client.post(
            "/api/v1/auth/login", json={"login": "admin", "password": PASSWORD}, headers=headers
        )
        assert response.status_code == 403
        with app.state.transactions.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_auth_sessions").fetchone()[0]
                == 0
            )


def test_csrf_denial_does_not_revoke_session(tmp_path):
    with client_app(tmp_path) as (_, client, origin):
        assert login(client, origin).status_code == 200
        assert client.post("/api/v1/auth/logout", headers={"Origin": origin}).status_code == 403
        assert client.get("/api/v1/auth/session").status_code == 200


def test_unknown_wrong_password_and_malformed_request_are_safe(tmp_path):
    with client_app(tmp_path) as (_, client, origin):
        for username in ("admin", "missing"):
            response = client.post(
                "/api/v1/auth/login",
                json={"login": username, "password": "wrong-password-123"},
                headers={"Origin": origin},
            )
            assert response.status_code == 401 and response.json()["code"] == "AUTH_REQUIRED"
            assert "wrong-password" not in response.text
        malformed = client.post(
            "/api/v1/auth/login",
            json={"login": "admin", "password": 123},
            headers={"Origin": origin},
        )
        assert malformed.status_code == 422


def test_rate_limit_is_durable_and_happens_before_password_hashing(tmp_path, monkeypatch):
    path = tmp_path / "limits.db"
    now = [1000]
    with Database(path) as database:
        accounts = Accounts(database)
        accounts.bootstrap("admin", SecretStr(PASSWORD))
        auth = sessions(database, accounts, lambda: now[0])
        for _ in range(5):
            with pytest.raises(ContractError, match="AUTH_REQUIRED"):
                auth.login("admin", SecretStr("wrong-password-123"), "127.0.0.1")

        def fail(*args):
            raise AssertionError("Rate-limited attempt reached hashing")

        monkeypatch.setattr(accounts, "verify_credentials", fail)
        with pytest.raises(importlib.import_module("flowlens.auth.sessions").RateLimited):
            auth.login("admin", SecretStr(PASSWORD), "127.0.0.1")
    with Database(path) as database:
        auth = sessions(database, Accounts(database), lambda: now[0])
        with pytest.raises(importlib.import_module("flowlens.auth.sessions").RateLimited):
            auth.login("admin", SecretStr(PASSWORD), "127.0.0.2")
        now[0] += 60000
        assert auth.login("admin", SecretStr(PASSWORD), "127.0.0.2").account.login == "admin"


def test_idle_absolute_expiry_and_restart(tmp_path):
    path = tmp_path / "expiry.db"
    now = [1000]
    with Database(path) as database:
        accounts = Accounts(database)
        accounts.bootstrap("admin", SecretStr(PASSWORD))
        auth = sessions(database, accounts, lambda: now[0])
        issued = auth.login("admin", SecretStr(PASSWORD), "127.0.0.1")
        token = issued.token.get_secret_value()
        now[0] += 3599999
        assert auth.resolve(token).account.login == "admin"
    with Database(path) as database:
        auth = sessions(database, Accounts(database), lambda: now[0])
        assert auth.resolve(token).account.login == "admin"
        now[0] += 3600000
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            auth.resolve(token)
        now[0] += 60000
        token = auth.login("admin", SecretStr(PASSWORD), "127.0.0.1").token.get_secret_value()
        for _ in range(7):
            now[0] += 3599000
            auth.resolve(token)
        now[0] += 3599000 + 8000
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            auth.resolve(token)


def test_reset_deactivation_and_forced_change_http_flow(tmp_path):
    with client_app(tmp_path) as (app, client, origin):
        admin = app.state.accounts.verify_credentials("admin", SecretStr(PASSWORD))
        user = app.state.accounts.create(admin.id, "observer", SecretStr(PASSWORD))
        response = client.post(
            "/api/v1/auth/login",
            json={"login": "observer", "password": PASSWORD},
            headers={"Origin": origin},
        )
        assert response.status_code == 200 and response.json()["account"]["must_change_password"]
        csrf = response.json()["csrf_token"]
        old = client.cookies.get("flowlens_session")
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            app.state.sessions.resolve(old)
        changed = client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "changed-session-password"},
            headers={"Origin": origin, "X-CSRF-Token": csrf},
        )
        assert changed.status_code == 204
        assert client.get("/api/v1/auth/session").status_code == 401
        response = client.post(
            "/api/v1/auth/login",
            json={"login": "observer", "password": "changed-session-password"},
            headers={"Origin": origin},
        )
        assert response.status_code == 200
        app.state.accounts.reset_password(admin.id, user.id, SecretStr("temporary-reset-password"))
        assert client.get("/api/v1/auth/session").status_code == 401
        response = client.post(
            "/api/v1/auth/login",
            json={"login": "observer", "password": "temporary-reset-password"},
            headers={"Origin": origin},
        )
        assert response.status_code == 200
        app.state.accounts.deactivate(admin.id, user.id)
        assert client.get("/api/v1/auth/session").status_code == 401


def test_login_rotates_existing_cookie_and_http_rate_limit_has_retry_after(tmp_path):
    with client_app(tmp_path) as (_, client, origin):
        assert login(client, origin).status_code == 200
        original = client.cookies.get("flowlens_session")
        assert login(client, origin).status_code == 200
        assert client.cookies.get("flowlens_session") != original
        current = client.cookies.get("flowlens_session")
        client.cookies.clear()
        client.cookies.set("flowlens_session", original)
        assert client.get("/api/v1/auth/session").status_code == 401
        client.cookies.clear()
        client.cookies.set("flowlens_session", current)
        for _ in range(3):
            assert login(client, origin, "wrong-password-123").status_code == 401
        limited = login(client, origin)
        assert limited.status_code == 429
        assert int(limited.headers["retry-after"]) > 0
        assert limited.json()["code"] == "RATE_LIMITED"


def test_successful_login_upgrades_old_hash_without_changing_credential_version(tmp_path):
    from argon2 import PasswordHasher
    from argon2.low_level import Type

    with Database(tmp_path / "rehash.db") as database:
        accounts = Accounts(database)
        admin = accounts.bootstrap("admin", SecretStr(PASSWORD))
        old = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1, type=Type.ID).hash(
            PASSWORD
        )
        with database.begin() as uow:
            uow.connection.execute(
                "UPDATE platform_accounts SET password_hash=? WHERE id=?", (old, str(admin.id))
            )
            uow.commit()
        auth = sessions(database, accounts, lambda: 1000)
        assert (
            auth.login("admin", SecretStr(PASSWORD), "127.0.0.1").account.credential_version
            == admin.credential_version
        )
        with database.begin() as uow:
            stored = uow.connection.execute(
                "SELECT password_hash FROM platform_accounts"
            ).fetchone()[0]
            assert not accounts.passwords.hasher.check_needs_rehash(stored)


def test_http_login_rollback_never_issues_cookie_on_audit_failure(tmp_path):
    with client_app(tmp_path) as (app, client, origin):
        with app.state.transactions.begin() as uow:
            uow.connection.execute("""CREATE TRIGGER platform_test_login_fault
                BEFORE INSERT ON platform_account_audit WHEN NEW.action='LOGIN'
                BEGIN SELECT RAISE(ABORT,'injected'); END;""")
            uow.commit()
        response = login(client, origin)
        assert response.status_code == 500
        assert "set-cookie" not in response.headers
        assert client.cookies.get("flowlens_session") is None
        with app.state.transactions.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_auth_sessions").fetchone()[0]
                == 0
            )


def test_blocked_hasher_and_peer_limit_are_fail_closed(tmp_path):
    module = importlib.import_module("flowlens.auth.sessions")
    with Database(tmp_path / "hashslots.db") as database:
        accounts = Accounts(database)
        accounts.bootstrap("admin", SecretStr(PASSWORD))
        auth = sessions(database, accounts, lambda: 1000)
        auth.hash_slots.acquire()
        auth.hash_slots.acquire()
        try:
            with pytest.raises(module.RateLimited):
                auth.login("admin", SecretStr(PASSWORD), "127.0.0.1")
        finally:
            auth.hash_slots.release()
            auth.hash_slots.release()
        for index in range(19):
            auth.reserve_login(f"user{index}", "127.0.0.1")
        with pytest.raises(module.RateLimited):
            auth.reserve_login("freshuser", "127.0.0.1")


@pytest.mark.parametrize(
    "value",
    [
        "http://example.org",
        "https://user:private-password@example.org",
        "https://example.org/path",
        "https://example.org?token=secret",
        "https://example.org:0",
    ],
)
def test_invalid_origin_config_is_rejected(value):
    with pytest.raises(ValueError):
        HostSettings(public_origin=value)


def test_cookie_only_auth_and_session_denial_do_not_extend_idle_deadline(tmp_path):
    path = tmp_path / "restricted.db"
    now = [1000]
    with Database(path) as database:
        accounts = Accounts(database)
        admin = accounts.bootstrap("admin", SecretStr(PASSWORD))
        accounts.create(admin.id, "observer", SecretStr(PASSWORD))
        auth = sessions(database, accounts, lambda: now[0])
        issued = auth.login("observer", SecretStr(PASSWORD), "127.0.0.1")
        now[0] += 3599999
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            auth.resolve(issued.token.get_secret_value())
        now[0] += 1
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            auth.resolve(issued.token.get_secret_value(), allow_password_change=True)
    with client_app(tmp_path) as (_, client, _):
        response = client.get(
            "/api/v1/auth/session?token=synthetic-old-token",
            headers={"Authorization": "Bearer synthetic-old-token"},
        )
        assert response.status_code == 401


def test_password_endpoint_requires_csrf_and_rejects_actor_injection(tmp_path):
    with client_app(tmp_path) as (_, client, origin):
        response = login(client, origin)
        payload = {"current_password": PASSWORD, "new_password": "new-session-password-123"}
        assert (
            client.post(
                "/api/v1/auth/password", json=payload, headers={"Origin": origin}
            ).status_code
            == 403
        )
        payload["account_id"] = "attacker-choice"
        response = client.post(
            "/api/v1/auth/password",
            json=payload,
            headers={"Origin": origin, "X-CSRF-Token": response.json()["csrf_token"]},
        )
        assert response.status_code == 422


def test_password_change_attempts_share_account_rate_budget(tmp_path):
    with client_app(tmp_path) as (_, client, origin):
        response = login(client, origin)
        headers = {"Origin": origin, "X-CSRF-Token": response.json()["csrf_token"]}
        payload = {
            "current_password": "incorrect-password-123",
            "new_password": "new-session-password-123",
        }
        for _ in range(4):
            assert (
                client.post("/api/v1/auth/password", json=payload, headers=headers).status_code
                == 401
            )
        assert (
            client.post("/api/v1/auth/password", json=payload, headers=headers).status_code == 429
        )
