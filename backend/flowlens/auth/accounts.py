"""Internal account lifecycle; HTTP login/sessions and domain grants are later units."""

import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import Database, UnitOfWork
from pydantic import SecretStr


@dataclass(frozen=True)
class Account:
    id: UUID
    login: str
    active: bool
    is_admin: bool
    must_change_password: bool
    credential_version: int


def account(row: sqlite3.Row) -> Account:
    return Account(
        UUID(row["id"]),
        row["login"],
        bool(row["active"]),
        bool(row["is_admin"]),
        bool(row["must_change_password"]),
        row["credential_version"],
    )


def login_name(value: str) -> str:
    normalized = value.casefold()
    if not re.fullmatch(r"[a-z][a-z0-9._-]{2,63}", normalized):
        raise ContractError("INVALID_INPUT")
    return normalized


def password_value(secret: SecretStr) -> str:
    value = secret.get_secret_value()
    if len(value) < 12 or len(value.encode()) > 4096:
        raise ContractError("INVALID_INPUT")
    return value


class Passwords:
    def __init__(self) -> None:
        self.hasher = PasswordHasher(
            time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID
        )
        self.dummy_hash = self.hasher.hash(secrets.token_urlsafe(32))

    def hash(self, secret: SecretStr) -> str:
        return self.hasher.hash(password_value(secret))

    def verify(self, encoded: str, secret: SecretStr) -> bool:
        try:
            self.hasher.verify(encoded, password_value(secret))
            return True
        except (VerificationError, InvalidHashError, ContractError):
            return False


class AccountRepository:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def row(self, identifier: UUID) -> sqlite3.Row:
        self.uow.check_open()
        row: sqlite3.Row | None = self.uow.connection.execute(
            "SELECT * FROM platform_accounts WHERE id=?", (str(identifier),)
        ).fetchone()
        if row is None:
            raise ContractError("ACCESS_DENIED")
        return row

    def admin(self, identifier: UUID) -> Account:
        current = account(self.row(identifier))
        if not current.active or not current.is_admin or current.must_change_password:
            raise ContractError("ACCESS_DENIED")
        return current

    def insert(self, login: str, encoded: str, *, is_admin: bool, must_change: bool) -> Account:
        self.uow.check_open()
        identifier = uuid4()
        try:
            self.uow.connection.execute(
                "INSERT INTO platform_accounts"
                "(id,login,password_hash,active,is_admin,must_change_password,credential_version)"
                " VALUES (?,?,?,1,?,?,1)",
                (str(identifier), login, encoded, int(is_admin), int(must_change)),
            )
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorcode in (
                sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
                sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            ):
                raise ContractError("VERSION_CONFLICT") from None
            raise
        return account(self.row(identifier))

    def audit(self, actor: UUID | None, target: UUID, action: str) -> None:
        self.uow.check_open()
        self.uow.connection.execute(
            "INSERT INTO platform_account_audit"
            "(actor_id,target_id,action,recorded_at) VALUES (?,?,?,?)",
            (str(actor) if actor else None, str(target), action, datetime.now(UTC).isoformat()),
        )


class Accounts:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.passwords = Passwords()

    def bootstrap(self, login: str, password: SecretStr) -> Account:
        name, encoded = login_name(login), self.passwords.hash(password)
        with self.database.begin() as uow:
            if (
                uow.connection.execute(
                    "SELECT 1 FROM platform_security_state WHERE name='bootstrap_admin'"
                ).fetchone()
                or uow.connection.execute(
                    "SELECT 1 FROM platform_accounts WHERE is_admin=1"
                ).fetchone()
            ):
                raise ContractError("VERSION_CONFLICT")
            repository = AccountRepository(uow)
            created = repository.insert(name, encoded, is_admin=True, must_change=False)
            uow.connection.execute(
                "INSERT INTO platform_security_state VALUES ('bootstrap_admin',?)",
                (str(created.id),),
            )
            repository.audit(None, created.id, "BOOTSTRAP_ADMIN")
            uow.commit()
        return created

    def get(self, identifier: UUID) -> Account:
        with self.database.begin() as uow:
            return account(AccountRepository(uow).row(identifier))

    def create(
        self, actor: UUID, login: str, password: SecretStr, *, is_admin: bool = False
    ) -> Account:
        name = login_name(login)
        if type(is_admin) is not bool:
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            authorized = AccountRepository(uow).admin(actor)
        encoded = self.passwords.hash(password)
        with self.database.begin() as uow:
            repository = AccountRepository(uow)
            if repository.admin(actor).credential_version != authorized.credential_version:
                raise ContractError("AUTH_REQUIRED")
            created = repository.insert(name, encoded, is_admin=is_admin, must_change=True)
            repository.audit(actor, created.id, "CREATE_ACCOUNT")
            uow.commit()
        return created

    def verify_credentials(self, login: str, password: SecretStr) -> Account:
        try:
            name = login_name(login)
        except ContractError:
            name = ""
        with self.database.begin() as uow:
            row = uow.connection.execute(
                "SELECT * FROM platform_accounts WHERE login=?", (name,)
            ).fetchone()
        encoded = row["password_hash"] if row else self.passwords.dummy_hash
        valid = self.passwords.verify(encoded, password)
        if not valid or row is None or not row["active"]:
            raise ContractError("AUTH_REQUIRED")
        verified = account(row)
        rehash = self.passwords.hasher.check_needs_rehash(encoded)
        replacement = self.passwords.hash(password) if rehash else None
        with self.database.begin() as uow:
            current = account(AccountRepository(uow).row(verified.id))
            if not current.active or current.credential_version != verified.credential_version:
                raise ContractError("AUTH_REQUIRED")
            if replacement is not None:
                uow.connection.execute(
                    "UPDATE platform_accounts SET password_hash=? WHERE id=?",
                    (replacement, str(current.id)),
                )
                AccountRepository(uow).audit(current.id, current.id, "REHASH_PASSWORD")
                uow.commit()
        return current

    def require_access(self, identifier: UUID, credential_version: int) -> Account:
        with self.database.begin() as uow:
            try:
                current = account(AccountRepository(uow).row(identifier))
            except ContractError:
                raise ContractError("AUTH_REQUIRED") from None
            if not current.active or current.credential_version != credential_version:
                raise ContractError("AUTH_REQUIRED")
            if current.must_change_password:
                raise ContractError("ACCESS_DENIED")
            return current

    def reset_password(self, actor: UUID, target: UUID, temporary_password: SecretStr) -> Account:
        with self.database.begin() as uow:
            authorized = AccountRepository(uow).admin(actor)
        encoded = self.passwords.hash(temporary_password)
        with self.database.begin() as uow:
            repository = AccountRepository(uow)
            if repository.admin(actor).credential_version != authorized.credential_version:
                raise ContractError("AUTH_REQUIRED")
            repository.row(target)
            uow.connection.execute(
                "UPDATE platform_accounts SET password_hash=?,must_change_password=1,"
                "credential_version=credential_version+1 WHERE id=?",
                (encoded, str(target)),
            )
            repository.audit(actor, target, "RESET_PASSWORD")
            updated = account(repository.row(target))
            uow.commit()
        return updated

    def change_password(
        self,
        target: UUID,
        current_password: SecretStr,
        new_password: SecretStr,
        *,
        expected_credential_version: int | None = None,
    ) -> Account:
        with self.database.begin() as uow:
            try:
                original = AccountRepository(uow).row(target)
            except ContractError:
                raise ContractError("AUTH_REQUIRED") from None
        if not original["active"] or not self.passwords.verify(
            original["password_hash"], current_password
        ):
            raise ContractError("AUTH_REQUIRED")
        if (
            expected_credential_version is not None
            and original["credential_version"] != expected_credential_version
        ):
            raise ContractError("AUTH_REQUIRED")
        if self.passwords.verify(original["password_hash"], new_password):
            raise ContractError("INVALID_INPUT")
        encoded = self.passwords.hash(new_password)
        with self.database.begin() as uow:
            repository = AccountRepository(uow)
            updated = repository.row(target)
            if (
                not updated["active"]
                or updated["credential_version"] != original["credential_version"]
            ):
                raise ContractError("AUTH_REQUIRED")
            uow.connection.execute(
                "UPDATE platform_accounts SET password_hash=?,must_change_password=0,"
                "credential_version=credential_version+1 WHERE id=?",
                (encoded, str(target)),
            )
            repository.audit(target, target, "CHANGE_PASSWORD")
            changed = account(repository.row(target))
            uow.commit()
        return changed

    def deactivate(self, actor: UUID, target: UUID) -> Account:
        with self.database.begin() as uow:
            repository = AccountRepository(uow)
            repository.admin(actor)
            current = account(repository.row(target))
            admins = uow.connection.execute(
                "SELECT COUNT(*) FROM platform_accounts WHERE active=1 AND is_admin=1"
            ).fetchone()[0]
            if current.active and current.is_admin and admins <= 1:
                raise ContractError("VERSION_CONFLICT")
            uow.connection.execute(
                "UPDATE platform_accounts SET active=0,"
                "credential_version=credential_version+1 WHERE id=?",
                (str(target),),
            )
            repository.audit(actor, target, "DEACTIVATE_ACCOUNT")
            deactivated = account(repository.row(target))
            uow.commit()
        return deactivated
