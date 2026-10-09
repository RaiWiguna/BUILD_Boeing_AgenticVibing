"""Explicit read-only archive conversion; historical payloads remain quarantined."""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from flowlens.storage.sqlite.database import Database

PROFILE = "legacy-2660222-archive-1"
NAMESPACE = UUID("f9526f99-15d3-4f62-b8c5-22f48a7b3400")
COLUMNS = {
    "sessions": ("id", "metadata", "status"),
    "events": ("session_id", "ordinal", "data"),
    "frames": ("session_id", "sim_ms", "sequence", "public", "private"),
    "commands": ("session_id", "command_id", "request", "response"),
}
QUERIES = {
    "sessions": "SELECT * FROM sessions ORDER BY id",
    "events": "SELECT * FROM events ORDER BY session_id,ordinal",
    "frames": "SELECT * FROM frames ORDER BY session_id,sim_ms",
    "commands": "SELECT * FROM commands ORDER BY session_id,command_id",
}
SCHEMAS = {
    "sessions": "PRAGMA table_info(sessions)",
    "events": "PRAGMA table_info(events)",
    "frames": "PRAGMA table_info(frames)",
    "commands": "PRAGMA table_info(commands)",
}
MAX_ROWS = 1_000_000
MAX_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class ImportSummary:
    digest: str
    counts: dict[str, int]
    profile: str = PROFILE


def invalid_constant(value: str) -> Any:
    raise ValueError("Nonfinite archive JSON.")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate archive JSON key.")
        result[key] = value
    return result


def document(raw: object) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise ValueError("Archive JSON text required.")
    try:
        value = json.loads(raw, parse_constant=invalid_constant, object_pairs_hook=unique_object)
        # Reject overflow such as 1e999, also nested, while retaining original text in storage.
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Invalid archive JSON.") from None
    if not isinstance(value, dict):
        raise ValueError("Archive JSON object required.")
    return value


def integer(value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > 2**63 - 1:
        raise ValueError("Invalid archive integer.")
    return value


def snapshot(path: Path) -> dict[str, list[sqlite3.Row]]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("A regular legacy source file is required.")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if (
            tables != set(COLUMNS)
            or connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')"
            ).fetchone()
        ):
            raise ValueError("Unsupported legacy archive schema.")
        for table, columns in COLUMNS.items():
            if tuple(row[1] for row in connection.execute(SCHEMAS[table])) != columns:
                raise ValueError("Unsupported legacy archive columns.")
        if (
            connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or connection.execute("PRAGMA foreign_key_check").fetchone()
        ):
            raise ValueError("Invalid legacy archive integrity.")
        result: dict[str, list[sqlite3.Row]] = {}
        size, count = 0, 0
        for table in COLUMNS:
            rows = []
            for row in connection.execute(QUERIES[table]):
                count += 1
                size += sum(len(item.encode()) for item in row if isinstance(item, str))
                if count > MAX_ROWS or size > MAX_BYTES:
                    raise ValueError("Legacy archive exceeds conversion limits.")
                rows.append(row)
            result[table] = rows
        return result
    except sqlite3.DatabaseError:
        raise ValueError("Legacy archive cannot be read.") from None
    finally:
        connection.close()


def validate(rows: dict[str, list[sqlite3.Row]]) -> None:
    identifiers: set[str] = set()
    for row in rows["sessions"]:
        identifier = row["id"]
        if (
            not isinstance(identifier, str)
            or not identifier
            or len(identifier) > 128
            or identifier in identifiers
        ):
            raise ValueError("Invalid legacy session identifier.")
        identifiers.add(identifier)
        metadata = document(row["metadata"])
        if metadata.get("id") != identifier or row["status"] not in (
            "READY",
            "RUNNING",
            "PAUSED",
            "ENDED",
            "INTERRUPTED",
        ):
            raise ValueError("Invalid legacy session metadata/status.")
    for table in ("events", "frames", "commands"):
        keys: set[tuple[object, ...]] = set()
        for row in rows[table]:
            key: tuple[object, ...]
            if row["session_id"] not in identifiers:
                raise ValueError("Orphan legacy row.")
            if table == "events":
                ordinal = integer(row["ordinal"], 1)
                event = document(row["data"])
                if integer(event.get("ordinal"), 1) != ordinal:
                    raise ValueError("Inconsistent legacy event ordinal.")
                integer(event.get("sim_ms"))
                key = (row["session_id"], ordinal)
            elif table == "frames":
                timing, sequence = integer(row["sim_ms"]), integer(row["sequence"])
                public = document(row["public"])
                document(row["private"])
                if (
                    integer(public.get("sim_ms")) != timing
                    or integer(public.get("sequence")) != sequence
                ):
                    raise ValueError("Inconsistent legacy frame keys.")
                key = (row["session_id"], timing)
            else:
                identifier = row["command_id"]
                if not isinstance(identifier, str) or not identifier or len(identifier) > 100:
                    raise ValueError("Invalid legacy command identifier.")
                document(row["request"])
                response = document(row["response"])
                if response.get("command_id") != identifier:
                    raise ValueError("Inconsistent legacy command keys.")
                key = (row["session_id"], identifier)
            if key in keys:
                raise ValueError("Duplicate legacy row key.")
            keys.add(key)


def import_archive(source: Path, target: Database) -> ImportSummary:
    if source.exists() and source.samefile(target.path):
        raise ValueError("Legacy source and destination must differ.")
    rows = snapshot(source)
    validate(rows)
    payload = json.dumps(
        {table: [list(row) for row in values] for table, values in rows.items()},
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    digest = hashlib.sha256((PROFILE + payload).encode()).hexdigest()
    counts = {table: len(values) for table, values in rows.items()}
    with target.begin() as uow:
        connection = uow.connection
        if connection.execute(
            "SELECT 1 FROM platform_legacy_imports WHERE digest=?", (digest,)
        ).fetchone():
            return ImportSummary(digest, counts)
        for row in rows["sessions"]:
            if connection.execute(
                "SELECT 1 FROM platform_legacy_sessions WHERE legacy_id=?", (row["id"],)
            ).fetchone():
                raise ValueError("Legacy session ID conflict; archive changed.")
        connection.execute(
            "INSERT INTO platform_legacy_imports VALUES (?,?,?)",
            (digest, PROFILE, json.dumps(counts)),
        )
        for row in rows["sessions"]:
            identifier = str(uuid5(NAMESPACE, row["id"]))
            connection.execute("INSERT INTO platform_sessions VALUES (?)", (identifier,))
            connection.execute(
                "INSERT INTO platform_revisions VALUES (?,?,?)", (identifier, 1, digest)
            )
            runtime_status = (
                "INTERRUPTED" if row["status"] in ("READY", "RUNNING", "PAUSED") else row["status"]
            )
            connection.execute(
                "INSERT INTO platform_legacy_sessions VALUES (?,?,?,?,?,?)",
                (row["id"], identifier, digest, row["metadata"], row["status"], runtime_status),
            )
        connection.executemany(
            "INSERT INTO platform_legacy_events VALUES (?,?,?)",
            (tuple(row) for row in rows["events"]),
        )
        connection.executemany(
            "INSERT INTO platform_legacy_frames VALUES (?,?,?,?)",
            (
                (row["session_id"], row["sim_ms"], row["sequence"], row["public"])
                for row in rows["frames"]
            ),
        )
        connection.executemany(
            "INSERT INTO platform_legacy_private_frames VALUES (?,?,?)",
            ((row["session_id"], row["sim_ms"], row["private"]) for row in rows["frames"]),
        )
        connection.executemany(
            "INSERT INTO platform_legacy_commands VALUES (?,?,?,?)",
            (tuple(row) for row in rows["commands"]),
        )
        uow.commit()
    return ImportSummary(digest, counts)
