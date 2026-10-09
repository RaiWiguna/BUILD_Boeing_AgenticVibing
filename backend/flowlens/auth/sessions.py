"""Durable opaque sessions, revocation stamps and bounded login work."""

import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import BoundedSemaphore
from uuid import UUID

from flowlens.auth.accounts import Account, AccountRepository, Accounts, account, login_name
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import Database, UnitOfWork
from pydantic import SecretStr

IDLE_MS = 60 * 60 * 1000
ABSOLUTE_MS = 8 * 60 * 60 * 1000
WINDOW_MS = 60 * 1000


class RateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__("RATE_LIMITED")


@dataclass(frozen=True)
class AuthSession:
    account: Account
    token: SecretStr
    expires_ms: int

    @property
    def csrf_token(self) -> str:
        return csrf_token(self.token.get_secret_value())


def csrf_token(token: str) -> str:
    return hmac.new(token.encode(), b"flowlens.csrf.v1", hashlib.sha256).hexdigest()


def token_hash(token: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise ContractError("AUTH_REQUIRED")
    return hashlib.sha256(token.encode()).hexdigest()


class Sessions:
    def __init__(
        self, database: Database, accounts: Accounts, *, clock: Callable[[], int] | None = None
    ) -> None:
        self.database = database
        self.accounts = accounts
        self.clock = clock or (lambda: time.time_ns() // 1_000_000)
        self.hash_slots = BoundedSemaphore(2)

    def reserve_login(self, login: str, peer: str) -> None:
        try:
            name = login_name(login)
        except ContractError:
            name = login.casefold()
        subjects = (("account:" + name, 5), ("peer:" + peer, 20))
        now = self.clock()
        with self.database.begin() as uow:
            uow.connection.execute(
                "DELETE FROM platform_login_limits WHERE window_ms<=?", (now - WINDOW_MS,)
            )
            for subject, limit in subjects:
                key = hashlib.sha256(subject.encode()).hexdigest()
                row = uow.connection.execute(
                    "SELECT * FROM platform_login_limits WHERE key_digest=?", (key,)
                ).fetchone()
                if row is not None and (now < row["window_ms"] or row["attempts"] >= limit):
                    raise RateLimited((row["window_ms"] + WINDOW_MS - now + 999) // 1000)
                if (
                    row is None
                    and uow.connection.execute(
                        "SELECT COUNT(*) FROM platform_login_limits"
                    ).fetchone()[0]
                    >= 10000
                ):
                    raise RateLimited(60)
                uow.connection.execute(
                    "INSERT INTO platform_login_limits VALUES (?,?,1) "
                    "ON CONFLICT(key_digest) DO UPDATE SET attempts=attempts+1",
                    (key, now),
                )
            uow.commit()

    def login(
        self, login: str, password: SecretStr, peer: str, *, previous_token: str | None = None
    ) -> AuthSession:
        self.reserve_login(login, peer)
        if not self.hash_slots.acquire(blocking=False):
            raise RateLimited(1)
        try:
            verified = self.accounts.verify_credentials(login, password)
        finally:
            self.hash_slots.release()
        token = secrets.token_urlsafe(32)
        now = self.clock()
        with self.database.begin() as uow:
            repository = AccountRepository(uow)
            current = account(repository.row(verified.id))
            if not current.active or current.credential_version != verified.credential_version:
                raise ContractError("AUTH_REQUIRED")
            uow.connection.execute(
                "DELETE FROM platform_auth_sessions WHERE expires_ms<=? OR revoked=1", (now,)
            )
            if previous_token:
                try:
                    prior = token_hash(previous_token)
                except ContractError:
                    prior = ""
                uow.connection.execute(
                    "UPDATE platform_auth_sessions SET revoked=1 WHERE token_hash=?", (prior,)
                )
            uow.connection.execute(
                "INSERT INTO platform_auth_sessions VALUES (?,?,?,?,?,?,0)",
                (
                    token_hash(token),
                    str(current.id),
                    current.credential_version,
                    now,
                    now,
                    now + ABSOLUTE_MS,
                ),
            )
            repository.audit(current.id, current.id, "LOGIN")
            uow.commit()
        return AuthSession(current, SecretStr(token), now + ABSOLUTE_MS)

    def authenticate(
        self, uow: UnitOfWork, digest: str, *, allow_password_change: bool = False
    ) -> Account:
        """Validate within the caller's transaction; no independent authorization snapshot."""
        uow.check_open()
        now = self.clock()
        row = uow.connection.execute(
            "SELECT * FROM platform_auth_sessions WHERE token_hash=?", (digest,)
        ).fetchone()
        if (
            row is None
            or row["revoked"]
            or now < row["last_seen_ms"]
            or now >= row["expires_ms"]
            or now >= row["last_seen_ms"] + IDLE_MS
        ):
            raise ContractError("AUTH_REQUIRED")
        current = account(AccountRepository(uow).row(UUID(row["account_id"])))
        if not current.active or current.credential_version != row["credential_version"]:
            raise ContractError("AUTH_REQUIRED")
        if current.must_change_password and not allow_password_change:
            raise ContractError("ACCESS_DENIED")
        return current

    def resolve(self, token: str, *, allow_password_change: bool = False) -> AuthSession:
        digest = token_hash(token)
        with self.database.begin() as uow:
            current = self.authenticate(uow, digest, allow_password_change=allow_password_change)
            row = uow.connection.execute(
                "SELECT expires_ms FROM platform_auth_sessions WHERE token_hash=?", (digest,)
            ).fetchone()
            uow.connection.execute(
                "UPDATE platform_auth_sessions SET last_seen_ms=? WHERE token_hash=?",
                (self.clock(), digest),
            )
            uow.commit()
        return AuthSession(current, SecretStr(token), row["expires_ms"])

    def logout(self, token: str) -> None:
        digest = token_hash(token)
        with self.database.begin() as uow:
            row = uow.connection.execute(
                "SELECT account_id,revoked FROM platform_auth_sessions WHERE token_hash=?",
                (digest,),
            ).fetchone()
            if row is not None and not row["revoked"]:
                uow.connection.execute(
                    "UPDATE platform_auth_sessions SET revoked=1 WHERE token_hash=?", (digest,)
                )
                identifier = UUID(row["account_id"])
                AccountRepository(uow).audit(identifier, identifier, "LOGOUT")
            uow.commit()

    def change_password(self, session: AuthSession, current: SecretStr, new: SecretStr) -> None:
        active = self.resolve(session.token.get_secret_value(), allow_password_change=True)
        self.reserve_login(active.account.login, "password-change:" + str(active.account.id))
        if not self.hash_slots.acquire(blocking=False):
            raise RateLimited(1)
        try:
            self.accounts.change_password(
                active.account.id,
                current,
                new,
                expected_credential_version=active.account.credential_version,
            )
        finally:
            self.hash_slots.release()
