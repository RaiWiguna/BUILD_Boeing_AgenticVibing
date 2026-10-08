"""Atomic migration batches with immutable history and transaction-safe SQL."""

import hashlib
import json
import sqlite3
from collections.abc import Iterator, Sequence

from flowlens.core.modules import MigrationSpec, order_migrations


def statements(sql: str) -> Iterator[str]:
    pending = ""
    for character in sql:
        pending += character
        if character == ";" and sqlite3.complete_statement(pending):
            yield pending
            pending = ""
    if pending.strip():
        if sqlite3.complete_statement(pending + ";"):
            yield pending
        elif not all(
            not line.strip() or line.lstrip().startswith("--") for line in pending.splitlines()
        ):
            raise ValueError("Incomplete migration SQL.")


def checksum(spec: MigrationSpec) -> str:
    payload = json.dumps([spec.id, spec.owner, spec.depends_on, spec.sql], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def authorize(
    action: int, arg1: str | None, arg2: str | None, db: str | None, trigger: str | None
) -> int:
    denied = (
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
        sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    )
    if action in denied or "platform_schema_migrations" in (arg1, arg2):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def migrate(connection: sqlite3.Connection, specs: Sequence[MigrationSpec]) -> None:
    ordered = order_migrations(list(specs))
    for spec in ordered:
        prefix = "platform." if spec.owner == "A" else "analysis."
        if not spec.id.startswith(prefix):
            raise ValueError("Invalid migration owner namespace.")
    existing = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if existing and "platform_schema_migrations" not in existing:
        raise ValueError("Refusing unversioned database; explicit archive migration required.")
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS platform_schema_migrations(
            id TEXT PRIMARY KEY NOT NULL, checksum TEXT NOT NULL)""")
        applied = dict(connection.execute("SELECT id,checksum FROM platform_schema_migrations"))
        manifest = {spec.id: spec for spec in ordered}
        if any(
            identifier not in manifest or checksum(manifest[identifier]) != digest
            for identifier, digest in applied.items()
        ):
            raise ValueError("Applied migration manifest mismatch or downgrade.")
        if any(
            not set(manifest[identifier].depends_on) <= applied.keys() for identifier in applied
        ):
            raise ValueError("Applied migration history has missing dependencies.")
        for spec in ordered:
            if spec.id in applied:
                continue
            connection.set_authorizer(authorize)
            try:
                for statement in statements(spec.sql):
                    connection.execute(statement)
            finally:
                connection.set_authorizer(None)
            connection.execute(
                "INSERT INTO platform_schema_migrations VALUES (?,?)", (spec.id, checksum(spec))
            )
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("Migration foreign key violation.")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
