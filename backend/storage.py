"""Local SQLite archive. Public frames and private branch checkpoints never share API serializers."""
import json
import sqlite3
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ReplayArchiveConflict(ValueError):
    """An immutable replay identity was reused for different committed data."""


class ReplayArchiveIntegrityError(RuntimeError):
    """The replay archive contains an internally inconsistent committed source."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class Archive:
    def __init__(self, path: str | Path):
        path = Path(path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, metadata TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                session_id TEXT NOT NULL REFERENCES sessions(id), ordinal INTEGER NOT NULL,
                data TEXT NOT NULL, PRIMARY KEY(session_id, ordinal));
            CREATE TABLE IF NOT EXISTS frames (
                session_id TEXT NOT NULL REFERENCES sessions(id), sim_ms INTEGER NOT NULL,
                sequence INTEGER NOT NULL, public TEXT NOT NULL, private TEXT NOT NULL,
                PRIMARY KEY(session_id, sim_ms));
            CREATE TABLE IF NOT EXISTS commands (
                session_id TEXT NOT NULL REFERENCES sessions(id), command_id TEXT NOT NULL,
                request TEXT NOT NULL, response TEXT NOT NULL,
                PRIMARY KEY(session_id, command_id));

            -- Replay data uses a separate, additive namespace. Synthetic frames
            -- keep their existing (session_id, sim_ms) primary key unchanged.
            CREATE TABLE IF NOT EXISTS replay_archive_schema (
                version INTEGER PRIMARY KEY, installed_utc TEXT NOT NULL);
            INSERT OR IGNORE INTO replay_archive_schema(version, installed_utc)
                VALUES (1, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));
            CREATE TABLE IF NOT EXISTS replay_sources (
                source_id TEXT PRIMARY KEY,
                source_session_id TEXT NOT NULL UNIQUE,
                content_hash TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                manifest_metadata_json TEXT NOT NULL,
                event_bytes BLOB NOT NULL,
                metadata_json TEXT NOT NULL,
                imported_utc TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS replay_source_events (
                source_id TEXT NOT NULL REFERENCES replay_sources(source_id),
                source_event_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                sim_ms INTEGER,
                record_json TEXT NOT NULL,
                PRIMARY KEY(source_id, source_event_id),
                UNIQUE(source_id, ordinal));
            CREATE INDEX IF NOT EXISTS replay_source_events_time_idx
                ON replay_source_events(source_id, sim_ms, ordinal);
            CREATE TABLE IF NOT EXISTS replay_import_receipts (
                receipt_id TEXT NOT NULL UNIQUE,
                source_id TEXT PRIMARY KEY REFERENCES replay_sources(source_id),
                source_session_id TEXT NOT NULL UNIQUE REFERENCES replay_sources(source_session_id),
                import_status TEXT NOT NULL CHECK(import_status = 'completed'),
                content_hash TEXT NOT NULL,
                completed_utc TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS replay_analyses (
                analysis_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES replay_sources(source_id),
                source_session_id TEXT NOT NULL REFERENCES replay_sources(source_session_id),
                kind TEXT NOT NULL CHECK(kind IN ('detector', 'assist')),
                input_hash TEXT NOT NULL,
                window_start_ms INTEGER NOT NULL CHECK(window_start_ms >= 0),
                window_end_ms INTEGER NOT NULL CHECK(window_end_ms >= window_start_ms),
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_utc TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS replay_analyses_source_idx
                ON replay_analyses(source_session_id, created_utc, analysis_id);
            CREATE TABLE IF NOT EXISTS replay_analysis_frames (
                analysis_id TEXT NOT NULL REFERENCES replay_analyses(analysis_id),
                at_ms INTEGER NOT NULL CHECK(at_ms >= 0),
                frame_json TEXT NOT NULL,
                PRIMARY KEY(analysis_id, at_ms));

            CREATE TRIGGER IF NOT EXISTS replay_sources_no_update
                BEFORE UPDATE ON replay_sources BEGIN
                    SELECT RAISE(ABORT, 'replay sources are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_sources_no_delete
                BEFORE DELETE ON replay_sources BEGIN
                    SELECT RAISE(ABORT, 'replay sources are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_source_events_no_update
                BEFORE UPDATE ON replay_source_events BEGIN
                    SELECT RAISE(ABORT, 'replay source events are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_source_events_no_delete
                BEFORE DELETE ON replay_source_events BEGIN
                    SELECT RAISE(ABORT, 'replay source events are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_import_receipts_no_update
                BEFORE UPDATE ON replay_import_receipts BEGIN
                    SELECT RAISE(ABORT, 'replay import receipts are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_import_receipts_no_delete
                BEFORE DELETE ON replay_import_receipts BEGIN
                    SELECT RAISE(ABORT, 'replay import receipts are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_analyses_no_update
                BEFORE UPDATE ON replay_analyses BEGIN
                    SELECT RAISE(ABORT, 'replay analyses are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_analyses_no_delete
                BEFORE DELETE ON replay_analyses BEGIN
                    SELECT RAISE(ABORT, 'replay analyses are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_analysis_frames_no_update
                BEFORE UPDATE ON replay_analysis_frames BEGIN
                    SELECT RAISE(ABORT, 'replay analysis frames are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS replay_analysis_frames_no_delete
                BEFORE DELETE ON replay_analysis_frames BEGIN
                    SELECT RAISE(ABORT, 'replay analysis frames are immutable'); END;
        """)
        replay_schema_version = self.db.execute(
            "SELECT MAX(version) FROM replay_archive_schema"
        ).fetchone()[0]
        if replay_schema_version is None or replay_schema_version > 1:
            raise RuntimeError(f"unsupported replay archive schema version {replay_schema_version!r}")
        self.replay_schema_version = int(replay_schema_version)
        # Historical sessions remain readable; interrupted sessions never auto-resume.
        self.db.execute("UPDATE sessions SET status='INTERRUPTED' WHERE status IN ('RUNNING','PAUSED','READY')")
        self.db.commit()

    def create(self, id: str, metadata: dict) -> None:
        with self.db:
            self.db.execute("INSERT INTO sessions VALUES (?, ?, 'READY')", (id, json.dumps(metadata)))

    def save(self, id: str, status: str, events: list[dict], public: dict, private: dict,
             command: tuple[str, dict, dict] | None = None) -> None:
        with self.db:
            # A branch can be prepared in memory and only become visible with its
            # first complete frame. Normal sessions already have this row.
            self.db.execute(
                "INSERT OR IGNORE INTO sessions(id, metadata, status) VALUES (?, ?, ?)",
                (id, json.dumps(public["metadata"], allow_nan=False), status),
            )
            self.db.execute("UPDATE sessions SET status=? WHERE id=?", (status, id))
            self.db.executemany("INSERT OR IGNORE INTO events VALUES (?, ?, ?)",
                                [(id, e["ordinal"], json.dumps(e, allow_nan=False)) for e in events])
            self.db.execute("INSERT OR REPLACE INTO frames VALUES (?, ?, ?, ?, ?)",
                            (id, public["sim_ms"], public["sequence"], json.dumps(public, allow_nan=False),
                             json.dumps(private, allow_nan=False)))
            if command:
                key, request, response = command
                self.db.execute("INSERT INTO commands VALUES (?, ?, ?, ?)",
                                (id, key, json.dumps(request), json.dumps(response)))

    def list_sessions(self) -> list[dict]:
        return [{**json.loads(r["metadata"]), "status": r["status"]}
                for r in self.db.execute("SELECT * FROM sessions ORDER BY rowid DESC")]

    def metadata(self, id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM sessions WHERE id=?", (id,)).fetchone()
        return {**json.loads(row["metadata"]), "status": row["status"]} if row else None

    def frame(self, id: str, sim_ms: int | None = None) -> tuple[dict, dict] | None:
        row = self.db.execute(
            "SELECT * FROM frames WHERE session_id=? AND sim_ms<=? ORDER BY sim_ms DESC LIMIT 1",
            (id, sim_ms if sim_ms is not None else 2**63-1)).fetchone()
        return (json.loads(row["public"]), json.loads(row["private"])) if row else None

    def events(self, id: str, cursor: int = 0, limit: int = 100, until_ms: int | None = None) -> list[dict]:
        rows = self.db.execute("SELECT data FROM events WHERE session_id=? AND ordinal>? ORDER BY ordinal LIMIT ?",
                               (id, cursor, limit)).fetchall()
        result = [json.loads(r["data"]) for r in rows]
        return [e for e in result if until_ms is None or e["sim_ms"] <= until_ms]

    def all_events(self, id: str) -> list[dict]:
        return [json.loads(r["data"]) for r in self.db.execute(
            "SELECT data FROM events WHERE session_id=? ORDER BY ordinal", (id,))]

    def command(self, id: str, key: str) -> tuple[dict, dict] | None:
        row = self.db.execute("SELECT request, response FROM commands WHERE session_id=? AND command_id=?",
                              (id, key)).fetchone()
        return (json.loads(row["request"]), json.loads(row["response"])) if row else None

    def close(self) -> None:
        self.db.close()

    def backup_to(self, destination: str | Path) -> Path:
        """Create a consistent SQLite snapshot at an operator-owned local path.

        The destination is a trusted caller choice, never request data from the
        public API. SQLite's backup API includes committed WAL contents; callers
        own the destination directory and retention policy.
        """
        requested = Path(destination).expanduser()
        if requested.is_symlink():
            raise ValueError("backup destination must not be a symbolic link")
        target_path = requested.resolve()
        if target_path == self.path:
            raise ValueError("backup destination must differ from the live archive")
        if target_path.exists() and not target_path.is_file():
            raise ValueError("backup destination must be a file path")
        if not target_path.parent.is_dir():
            raise ValueError("backup destination directory must already exist")

        target = sqlite3.connect(target_path)
        try:
            self.db.backup(target)
            target.commit()
            integrity = target.execute("PRAGMA integrity_check").fetchone()
            foreign_key_errors = target.execute("PRAGMA foreign_key_check").fetchall()
            if integrity is None or integrity[0] != "ok" or foreign_key_errors:
                raise sqlite3.DatabaseError("SQLite backup failed integrity verification")
        finally:
            target.close()
        return target_path

    def commit_replay_source(
        self,
        *,
        source_id: str,
        content_hash: str,
        manifest_json: str,
        manifest_metadata_json: str,
        event_bytes: bytes,
        records: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Persist a fully validated replay source and completed receipt atomically."""
        source_session_id = f"replay-{uuid.uuid4().hex}"
        receipt_id = f"import-{uuid.uuid4().hex}"
        now = datetime.now(UTC).isoformat()
        metadata = {
            "source_session_id": source_session_id,
            "source_id": source_id,
            "kind": "replay_source",
            "schema_version": "replay-1",
            "content_hash": content_hash,
            "import_status": "completed",
        }
        metadata_json = _canonical_json(metadata)

        with self.db:
            existing = self.db.execute(
                "SELECT * FROM replay_sources WHERE source_id=?", (source_id,)
            ).fetchone()
            if existing is not None:
                if (
                    existing["content_hash"] != content_hash
                    or existing["manifest_metadata_json"] != manifest_metadata_json
                    or bytes(existing["event_bytes"]) != event_bytes
                ):
                    raise ReplayArchiveConflict(
                        f"source_id {source_id!r} already belongs to different replay content or manifest"
                    )
                receipt = self.db.execute(
                    "SELECT * FROM replay_import_receipts WHERE source_id=?", (source_id,)
                ).fetchone()
                if receipt is None or receipt["import_status"] != "completed":
                    raise ReplayArchiveIntegrityError(
                        f"committed replay source {source_id!r} has no completed import receipt"
                    )
                return {
                    "source_session_id": existing["source_session_id"],
                    "source_id": source_id,
                    "import_status": receipt["import_status"],
                    "receipt_id": receipt["receipt_id"],
                    "content_hash": existing["content_hash"],
                    "idempotent": True,
                }

            self.db.execute(
                """INSERT INTO replay_sources
                   (source_id, source_session_id, content_hash, manifest_json,
                    manifest_metadata_json, event_bytes, metadata_json, imported_utc)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source_id,
                    source_session_id,
                    content_hash,
                    manifest_json,
                    manifest_metadata_json,
                    sqlite3.Binary(event_bytes),
                    metadata_json,
                    now,
                ),
            )
            for record in records:
                event = record["event"]
                self.db.execute(
                    """INSERT INTO replay_source_events
                       (source_id, source_event_id, ordinal, sim_ms, record_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        source_id,
                        record["source_event_id"],
                        event["ordinal"],
                        event["sim_ms"],
                        _canonical_json(record),
                    ),
                )
            self.db.execute(
                """INSERT INTO replay_import_receipts
                   (receipt_id, source_id, source_session_id, import_status, content_hash, completed_utc)
                   VALUES (?, ?, ?, 'completed', ?, ?)""",
                (receipt_id, source_id, source_session_id, content_hash, now),
            )
            self._before_replay_import_commit()

        return {
            "source_session_id": source_session_id,
            "source_id": source_id,
            "import_status": "completed",
            "receipt_id": receipt_id,
            "content_hash": content_hash,
            "idempotent": False,
        }

    def _before_replay_import_commit(self) -> None:
        """Failure-injection seam; production archives leave this as a no-op."""

    def replay_source(self, source_session_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            """SELECT s.*, r.receipt_id, r.import_status, r.completed_utc
               FROM replay_sources s LEFT JOIN replay_import_receipts r USING(source_id)
               WHERE s.source_session_id=?""",
            (source_session_id,),
        ).fetchone()
        if row is None:
            return None
        if row["receipt_id"] is None or row["import_status"] != "completed":
            raise ReplayArchiveIntegrityError("replay source is visible without a completed receipt")
        return {
            "source_id": row["source_id"],
            "source_session_id": row["source_session_id"],
            "content_hash": row["content_hash"],
            "manifest": json.loads(row["manifest_json"]),
            "manifest_metadata": json.loads(row["manifest_metadata_json"]),
            "event_bytes": bytes(row["event_bytes"]),
            "metadata": json.loads(row["metadata_json"]),
            "receipt": {
                "receipt_id": row["receipt_id"],
                "import_status": row["import_status"],
                "completed_utc": row["completed_utc"],
            },
        }

    def replay_sources_for_idempotency(self, source_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT source_session_id, content_hash, manifest_metadata_json, event_bytes "
            "FROM replay_sources WHERE source_id=?",
            (source_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "source_session_id": row["source_session_id"],
            "content_hash": row["content_hash"],
            "manifest_metadata_json": row["manifest_metadata_json"],
            "event_bytes": bytes(row["event_bytes"]),
        }

    def replay_source_records(
        self,
        source_session_id: str,
        *,
        after_ordinal: int = -1,
        until_ms: int | None = None,
        limit: int | None = None,
        include_unknown_time: bool = False,
    ) -> list[dict[str, Any]]:
        """Read ordered records, filtering the historical cutoff before pagination."""
        if after_ordinal < -1:
            raise ValueError("after_ordinal must be -1 or greater")
        if until_ms is not None and until_ms < 0:
            raise ValueError("until_ms must be nonnegative")
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive")
        source = self.db.execute(
            "SELECT source_id FROM replay_sources WHERE source_session_id=?", (source_session_id,)
        ).fetchone()
        if source is None:
            return []
        sql = (
            "SELECT record_json FROM replay_source_events WHERE source_id=? AND ordinal>?"
        )
        params: list[Any] = [source["source_id"], after_ordinal]
        if until_ms is not None:
            # Public history hides unknown-time rows at a cutoff; the internal
            # reducer may retain them as unresolved evidence.
            if include_unknown_time:
                sql += " AND (sim_ms IS NULL OR sim_ms<=?)"
            else:
                sql += " AND sim_ms IS NOT NULL AND sim_ms<=?"
            params.append(until_ms)
        sql += " ORDER BY ordinal"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return [json.loads(row["record_json"]) for row in self.db.execute(sql, params)]

    def save_replay_analysis(
        self, metadata: Mapping[str, Any], frames: Sequence[Mapping[str, Any]]
    ) -> None:
        """Append one immutable analysis version and its public frame payloads."""
        analysis_id = metadata["id"]
        source_id = metadata["source_id"]
        source_session_id = metadata["source_session_id"]
        kind = metadata["kind"]
        start_ms = metadata["window_start_ms"]
        end_ms = metadata["window_end_ms"]
        input_hash = metadata["input_hash"]
        status = metadata["status"]
        if any(not isinstance(value, str) or not value for value in (
            analysis_id, source_id, source_session_id, input_hash, status,
        )):
            raise ValueError("analysis identity, input_hash, and status must be nonempty strings")
        if kind not in {"detector", "assist"}:
            raise ValueError("analysis kind must be detector or assist")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (start_ms, end_ms)):
            raise ValueError("analysis window times must be integer milliseconds")
        if start_ms < 0 or end_ms < start_ms:
            raise ValueError("analysis window must be nonnegative and ordered")
        metadata_json = _canonical_json(metadata)
        frame_items: list[tuple[int, str]] = []
        seen_times: set[int] = set()
        for frame in frames:
            at_ms = frame["at_ms"]
            if isinstance(at_ms, bool) or not isinstance(at_ms, int) or at_ms < 0:
                raise ValueError("analysis frame time must be nonnegative integer milliseconds")
            if at_ms in seen_times:
                raise ReplayArchiveConflict(f"analysis {analysis_id!r} repeats frame time {at_ms}")
            if frame["analysis_id"] != analysis_id or not start_ms <= at_ms <= end_ms:
                raise ReplayArchiveConflict(f"frame does not belong to analysis {analysis_id!r} window")
            seen_times.add(at_ms)
            frame_items.append((at_ms, _canonical_json(frame)))
        now = datetime.now(UTC).isoformat()
        with self.db:
            source = self.db.execute(
                "SELECT source_id FROM replay_sources WHERE source_session_id=?", (source_session_id,)
            ).fetchone()
            if source is None or source["source_id"] != source_id:
                raise ReplayArchiveConflict("analysis source identity does not match an imported replay source")
            existing = self.db.execute(
                "SELECT metadata_json FROM replay_analyses WHERE analysis_id=?", (analysis_id,)
            ).fetchone()
            if existing is not None:
                existing_frames = [
                    (row["at_ms"], row["frame_json"])
                    for row in self.db.execute(
                        "SELECT at_ms, frame_json FROM replay_analysis_frames WHERE analysis_id=? ORDER BY at_ms",
                        (analysis_id,),
                    )
                ]
                if existing["metadata_json"] == metadata_json and existing_frames == sorted(frame_items):
                    return
                raise ReplayArchiveConflict(f"analysis_id {analysis_id!r} is already committed")
            self.db.execute(
                """INSERT INTO replay_analyses
                   (analysis_id, source_id, source_session_id, kind, input_hash, window_start_ms,
                    window_end_ms, status, metadata_json, created_utc)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    analysis_id,
                    source_id,
                    source_session_id,
                    kind,
                    input_hash,
                    start_ms,
                    end_ms,
                    status,
                    metadata_json,
                    now,
                ),
            )
            self.db.executemany(
                "INSERT INTO replay_analysis_frames(analysis_id, at_ms, frame_json) VALUES (?, ?, ?)",
                [(analysis_id, at_ms, frame_json) for at_ms, frame_json in frame_items],
            )

    def replay_analyses(self, source_session_id: str) -> list[dict[str, Any]]:
        return [
            json.loads(row["metadata_json"])
            for row in self.db.execute(
                "SELECT metadata_json FROM replay_analyses WHERE source_session_id=? "
                "ORDER BY created_utc, analysis_id",
                (source_session_id,),
            )
        ]

    def replay_analysis_frame(
        self, source_session_id: str, analysis_id: str, at_ms: int | None
    ) -> dict[str, Any] | None:
        if at_ms is not None and at_ms < 0:
            raise ValueError("at_ms must be nonnegative")
        sql = (
            "SELECT f.frame_json FROM replay_analysis_frames f "
            "JOIN replay_analyses a USING(analysis_id) "
            "WHERE a.source_session_id=? AND a.analysis_id=?"
        )
        params: list[Any] = [source_session_id, analysis_id]
        if at_ms is not None:
            sql += " AND f.at_ms<=?"
            params.append(at_ms)
        sql += " ORDER BY f.at_ms DESC LIMIT 1"
        row = self.db.execute(sql, params).fetchone()
        return json.loads(row["frame_json"]) if row else None

    def replay_session_metadata(self, source_session_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT metadata_json FROM replay_sources WHERE source_session_id=?", (source_session_id,)
        ).fetchone()
        return json.loads(row["metadata_json"]) if row else None

    def reset_branch_archive(self, id: str) -> None:
        with self.db:
            for table in ("events", "frames", "commands"):
                self.db.execute(f"DELETE FROM {table} WHERE session_id=?", (id,))

    def truth_samples(self, id: str) -> list[dict[str, Any]]:
        return [{"sim_ms": r["sim_ms"], "mobiles": json.loads(r["private"])["simulator"]["mobiles"]}
                for r in self.db.execute("SELECT sim_ms, private FROM frames WHERE session_id=? AND sim_ms%1000=0 ORDER BY sim_ms", (id,))]
