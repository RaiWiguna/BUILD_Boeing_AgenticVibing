"""Local SQLite archive. Public frames and private branch checkpoints never share API serializers."""
import json
import sqlite3
from pathlib import Path
from typing import Any


class Archive:
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
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
        """)
        # Historical sessions remain readable; interrupted sessions never auto-resume.
        self.db.execute("UPDATE sessions SET status='INTERRUPTED' WHERE status IN ('RUNNING','PAUSED','READY')")
        self.db.commit()

    def create(self, id: str, metadata: dict) -> None:
        with self.db:
            self.db.execute("INSERT INTO sessions VALUES (?, ?, 'READY')", (id, json.dumps(metadata)))

    def save(self, id: str, status: str, events: list[dict], public: dict, private: dict,
             command: tuple[str, dict, dict] | None = None) -> None:
        with self.db:
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

    def reset_branch_archive(self, id: str) -> None:
        with self.db:
            for table in ("events", "frames", "commands"):
                self.db.execute(f"DELETE FROM {table} WHERE session_id=?", (id,))

    def truth_samples(self, id: str) -> list[dict[str, Any]]:
        return [{"sim_ms": r["sim_ms"], "mobiles": json.loads(r["private"])["simulator"]["mobiles"]}
                for r in self.db.execute("SELECT sim_ms, private FROM frames WHERE session_id=? AND sim_ms%1000=0 ORDER BY sim_ms", (id,))]
