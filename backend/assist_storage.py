"""Additive audio/job persistence on the server-owned Archive connection.

This adapter deliberately receives the existing connection and never opens a
second SQLite writer. Files live beside this metadata in a separate private
store managed by :mod:`backend.assist_service`.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import Any


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class AssistStorage:
    """Persist audio assets, jobs, and immutable attempt receipts via Archive.db."""

    def __init__(self, db: sqlite3.Connection):
        self._db = db
        self._install_schema()

    def _install_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS assist_audio_assets (
                asset_id TEXT PRIMARY KEY,
                source_session_id TEXT NOT NULL REFERENCES replay_sources(source_session_id),
                content_hash TEXT NOT NULL,
                duration_ms INTEGER NOT NULL CHECK(duration_ms > 0),
                metadata_json TEXT NOT NULL,
                created_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS assist_audio_assets_source_idx
                ON assist_audio_assets(source_session_id, created_utc, asset_id);
            CREATE TABLE IF NOT EXISTS transcription_jobs (
                job_id TEXT PRIMARY KEY,
                source_session_id TEXT NOT NULL REFERENCES replay_sources(source_session_id),
                asset_id TEXT NOT NULL UNIQUE REFERENCES assist_audio_assets(asset_id),
                current_attempt_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN
                    ('queued','running','needs-review','completed','failed','cancelled')),
                provider TEXT,
                model TEXT,
                version TEXT,
                config_version TEXT,
                language TEXT,
                started_utc TEXT,
                finished_utc TEXT,
                error_json TEXT,
                created_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS transcription_jobs_source_idx
                ON transcription_jobs(source_session_id, created_utc, job_id);
            CREATE TABLE IF NOT EXISTS transcription_attempts (
                attempt_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL REFERENCES transcription_jobs(job_id),
                status TEXT NOT NULL CHECK(status IN
                    ('queued','running','needs-review','completed','failed','cancelled')),
                started_utc TEXT,
                finished_utc TEXT,
                error_json TEXT,
                created_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS transcription_attempts_job_idx
                ON transcription_attempts(job_id, created_utc, attempt_id);
            """
        )
        self._db.commit()

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "attempt_id": row["attempt_id"],
            "status": row["status"],
            "started_utc": row["started_utc"],
            "finished_utc": row["finished_utc"],
            "error": json.loads(row["error_json"]) if row["error_json"] else None,
            "created_utc": row["created_utc"],
        }

    def commit_asset_job(
        self,
        *,
        asset: Mapping[str, Any],
        job: Mapping[str, Any],
        attempt: Mapping[str, Any],
    ) -> None:
        """Commit the asset, queued job, and first attempt in one transaction."""
        with self._db:
            self._db.execute(
                "INSERT INTO assist_audio_assets VALUES (?, ?, ?, ?, ?, ?)",
                (
                    asset["id"],
                    asset["session_id"],
                    asset["hash"],
                    asset["duration_ms"],
                    _json(asset),
                    asset["created_utc"],
                ),
            )
            self._db.execute(
                """INSERT INTO transcription_jobs (
                    job_id, source_session_id, asset_id, current_attempt_id, status,
                    provider, model, version, config_version, language,
                    started_utc, finished_utc, error_json, created_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job["id"],
                    job["source_session_id"],
                    job["asset_id"],
                    job["attempt_id"],
                    job["status"],
                    job["provider"],
                    job["model"],
                    job["version"],
                    job["config_version"],
                    job["language"],
                    job["started_utc"],
                    job["finished_utc"],
                    _json(job["error"]) if job["error"] is not None else None,
                    job["created_utc"],
                ),
            )
            self._db.execute(
                "INSERT INTO transcription_attempts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt["attempt_id"],
                    job["id"],
                    attempt["status"],
                    attempt["started_utc"],
                    attempt["finished_utc"],
                    _json(attempt["error"]) if attempt["error"] is not None else None,
                    attempt["created_utc"],
                ),
            )

    def get_asset(self, source_session_id: str, asset_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT metadata_json FROM assist_audio_assets WHERE source_session_id=? AND asset_id=?",
            (source_session_id, asset_id),
        ).fetchone()
        return json.loads(row["metadata_json"]) if row else None

    def get_job(self, source_session_id: str, job_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT * FROM transcription_jobs WHERE source_session_id=? AND job_id=?",
            (source_session_id, job_id),
        ).fetchone()
        if row is None:
            return None
        attempts = self._db.execute(
            "SELECT * FROM transcription_attempts WHERE job_id=? ORDER BY rowid",
            (job_id,),
        ).fetchall()
        return {
            "id": row["job_id"],
            "source_session_id": row["source_session_id"],
            "asset_id": row["asset_id"],
            "attempt_id": row["current_attempt_id"],
            "status": row["status"],
            "provider": row["provider"],
            "model": row["model"],
            "version": row["version"],
            "config_version": row["config_version"],
            "language": row["language"],
            "started_utc": row["started_utc"],
            "finished_utc": row["finished_utc"],
            "error": json.loads(row["error_json"]) if row["error_json"] else None,
            "chunk_progress": None,
            "created_utc": row["created_utc"],
            "attempts": [self._attempt_from_row(item) for item in attempts],
        }

    def mark_running(
        self,
        job_id: str,
        attempt_id: str,
        *,
        provider: str,
        model: str,
        version: str,
        config_version: str,
        started_utc: str,
    ) -> bool:
        with self._db:
            attempt = self._db.execute(
                "UPDATE transcription_attempts SET status='running', started_utc=? "
                "WHERE job_id=? AND attempt_id=? AND status='queued'",
                (started_utc, job_id, attempt_id),
            )
            if attempt.rowcount != 1:
                return False
            job = self._db.execute(
                """UPDATE transcription_jobs SET status='running', provider=?, model=?, version=?,
                    config_version=?, started_utc=?, finished_utc=NULL, error_json=NULL
                    WHERE job_id=? AND current_attempt_id=? AND status='queued'""",
                (provider, model, version, config_version, started_utc, job_id, attempt_id),
            )
            if job.rowcount != 1:
                raise sqlite3.IntegrityError("queued attempt is no longer the active job attempt")
            return True

    def finish_attempt(
        self,
        job_id: str,
        attempt_id: str,
        *,
        status: str,
        finished_utc: str,
        error: Mapping[str, str] | None = None,
    ) -> bool:
        if status not in {"needs-review", "completed", "failed", "cancelled"}:
            raise ValueError("attempt terminal status is invalid")
        error_json = _json(dict(error)) if error is not None else None
        with self._db:
            job = self._db.execute(
                """UPDATE transcription_jobs SET status=?, finished_utc=?, error_json=?
                    WHERE job_id=? AND current_attempt_id=? AND status IN ('queued','running')""",
                (status, finished_utc, error_json, job_id, attempt_id),
            )
            if job.rowcount != 1:
                return False
            attempt = self._db.execute(
                """UPDATE transcription_attempts SET status=?, finished_utc=?, error_json=?
                    WHERE job_id=? AND attempt_id=? AND status IN ('queued','running')""",
                (status, finished_utc, error_json, job_id, attempt_id),
            )
            if attempt.rowcount != 1:
                raise sqlite3.IntegrityError("active job attempt receipt is missing")
            return True

    def retry_job(
        self,
        source_session_id: str,
        job_id: str,
        *,
        attempt: Mapping[str, Any],
        provider: str | None,
        model: str | None,
        version: str | None,
        config_version: str | None,
        language: str | None,
    ) -> dict[str, Any] | None:
        with self._db:
            row = self._db.execute(
                "SELECT status FROM transcription_jobs WHERE source_session_id=? AND job_id=?",
                (source_session_id, job_id),
            ).fetchone()
            if row is None:
                return None
            if row["status"] not in {"failed", "cancelled"}:
                raise ValueError("only failed or cancelled jobs can be retried")
            self._db.execute(
                "INSERT INTO transcription_attempts VALUES (?, ?, 'queued', NULL, NULL, NULL, ?)",
                (attempt["attempt_id"], job_id, attempt["created_utc"]),
            )
            self._db.execute(
                """UPDATE transcription_jobs SET current_attempt_id=?, status='queued',
                    provider=?, model=?, version=?, config_version=?, language=?,
                    started_utc=NULL, finished_utc=NULL, error_json=NULL
                    WHERE source_session_id=? AND job_id=?""",
                (
                    attempt["attempt_id"], provider, model, version, config_version, language,
                    source_session_id, job_id,
                ),
            )
        return self.get_job(source_session_id, job_id)


__all__ = ["AssistStorage"]
