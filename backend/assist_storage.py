"""Additive audio/job persistence on the server-owned Archive connection.

This adapter deliberately receives the existing connection and never opens a
second SQLite writer. Files live beside this metadata in a separate private
store managed by :mod:`backend.assist_service`.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Mapping
from typing import Any


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class AssistStorage:
    """Persist audio assets, jobs, results, and stream events via Archive.db."""

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
            CREATE TABLE IF NOT EXISTS assist_analyses (
                analysis_id TEXT PRIMARY KEY,
                source_session_id TEXT NOT NULL REFERENCES replay_sources(source_session_id),
                source_id TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind = 'assist'),
                job_id TEXT NOT NULL REFERENCES transcription_jobs(job_id),
                attempt_id TEXT NOT NULL REFERENCES transcription_attempts(attempt_id),
                input_hash TEXT NOT NULL,
                versions_json TEXT NOT NULL,
                window_start_ms INTEGER NOT NULL CHECK(window_start_ms >= 0),
                window_end_ms INTEGER NOT NULL CHECK(window_end_ms >= window_start_ms),
                status TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS assist_analyses_source_idx
                ON assist_analyses(source_session_id, created_utc, analysis_id);
            CREATE TABLE IF NOT EXISTS assist_transcript_segments (
                source_session_id TEXT NOT NULL,
                analysis_id TEXT NOT NULL REFERENCES assist_analyses(analysis_id),
                segment_id TEXT NOT NULL,
                available_ms INTEGER,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(source_session_id, segment_id)
            );
            CREATE TABLE IF NOT EXISTS assist_candidate_entities (
                source_session_id TEXT NOT NULL,
                analysis_id TEXT NOT NULL REFERENCES assist_analyses(analysis_id),
                ordinal INTEGER NOT NULL,
                segment_id TEXT NOT NULL,
                available_ms INTEGER,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(analysis_id, ordinal),
                FOREIGN KEY(source_session_id, segment_id)
                    REFERENCES assist_transcript_segments(source_session_id, segment_id)
            );
            CREATE TABLE IF NOT EXISTS assist_highlights (
                source_session_id TEXT NOT NULL,
                analysis_id TEXT NOT NULL REFERENCES assist_analyses(analysis_id),
                highlight_id TEXT NOT NULL,
                available_ms INTEGER,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(source_session_id, highlight_id)
            );
            CREATE TABLE IF NOT EXISTS assist_options (
                source_session_id TEXT NOT NULL,
                analysis_id TEXT NOT NULL REFERENCES assist_analyses(analysis_id),
                option_id TEXT NOT NULL,
                available_ms INTEGER,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(source_session_id, option_id)
            );
            CREATE TABLE IF NOT EXISTS assist_result_receipts (
                job_id TEXT NOT NULL REFERENCES transcription_jobs(job_id),
                attempt_id TEXT NOT NULL REFERENCES transcription_attempts(attempt_id),
                payload_hash TEXT NOT NULL,
                receipt_json TEXT NOT NULL,
                PRIMARY KEY(job_id, attempt_id)
            );
            CREATE TABLE IF NOT EXISTS assist_stream_state (
                source_session_id TEXT PRIMARY KEY REFERENCES replay_sources(source_session_id),
                sequence INTEGER NOT NULL CHECK(sequence >= 0)
            );
            CREATE TABLE IF NOT EXISTS assist_stream_events (
                source_session_id TEXT NOT NULL REFERENCES replay_sources(source_session_id),
                sequence INTEGER NOT NULL CHECK(sequence > 0),
                event_type TEXT NOT NULL CHECK(event_type IN
                    ('job_progress','segment','highlight','option')),
                analysis_id TEXT NOT NULL REFERENCES assist_analyses(analysis_id),
                job_id TEXT NOT NULL REFERENCES transcription_jobs(job_id),
                available_ms INTEGER,
                evaluator_only INTEGER NOT NULL DEFAULT 0 CHECK(evaluator_only IN (0,1)),
                payload_json TEXT NOT NULL,
                created_utc TEXT NOT NULL,
                PRIMARY KEY(source_session_id, sequence)
            );
            CREATE INDEX IF NOT EXISTS assist_stream_events_time_idx
                ON assist_stream_events(source_session_id, sequence, available_ms);
            CREATE TRIGGER IF NOT EXISTS assist_analyses_no_update
                BEFORE UPDATE ON assist_analyses BEGIN
                    SELECT RAISE(ABORT, 'assist analyses are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_analyses_no_delete
                BEFORE DELETE ON assist_analyses BEGIN
                    SELECT RAISE(ABORT, 'assist analyses are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_segments_no_update
                BEFORE UPDATE ON assist_transcript_segments BEGIN
                    SELECT RAISE(ABORT, 'assist transcript segments are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_segments_no_delete
                BEFORE DELETE ON assist_transcript_segments BEGIN
                    SELECT RAISE(ABORT, 'assist transcript segments are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_entities_no_update
                BEFORE UPDATE ON assist_candidate_entities BEGIN
                    SELECT RAISE(ABORT, 'assist entities are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_entities_no_delete
                BEFORE DELETE ON assist_candidate_entities BEGIN
                    SELECT RAISE(ABORT, 'assist entities are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_highlights_no_update
                BEFORE UPDATE ON assist_highlights BEGIN
                    SELECT RAISE(ABORT, 'assist highlights are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_highlights_no_delete
                BEFORE DELETE ON assist_highlights BEGIN
                    SELECT RAISE(ABORT, 'assist highlights are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_options_no_update
                BEFORE UPDATE ON assist_options BEGIN
                    SELECT RAISE(ABORT, 'assist options are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_options_no_delete
                BEFORE DELETE ON assist_options BEGIN
                    SELECT RAISE(ABORT, 'assist options are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_receipts_no_update
                BEFORE UPDATE ON assist_result_receipts BEGIN
                    SELECT RAISE(ABORT, 'assist result receipts are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_receipts_no_delete
                BEFORE DELETE ON assist_result_receipts BEGIN
                    SELECT RAISE(ABORT, 'assist result receipts are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_stream_events_no_update
                BEFORE UPDATE ON assist_stream_events BEGIN
                    SELECT RAISE(ABORT, 'assist stream events are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS assist_stream_events_no_delete
                BEFORE DELETE ON assist_stream_events BEGIN
                    SELECT RAISE(ABORT, 'assist stream events are immutable'); END;
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

    def get_source_binding(self, source_session_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT source_id, content_hash, manifest_json FROM replay_sources WHERE source_session_id=?",
            (source_session_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "source_id": row["source_id"],
            "content_hash": row["content_hash"],
            "manifest": json.loads(row["manifest_json"]),
        }

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
            "result_receipt": self.get_result_receipt(row["job_id"], row["current_attempt_id"]),
        }

    def get_result_receipt(self, job_id: str, attempt_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT receipt_json FROM assist_result_receipts WHERE job_id=? AND attempt_id=?",
            (job_id, attempt_id),
        ).fetchone()
        return json.loads(row["receipt_json"]) if row else None

    def commit_result_batch(
        self,
        *,
        source_session_id: str,
        source_id: str,
        job_id: str,
        attempt_id: str,
        result_payload: Mapping[str, Any],
        payload_hash: str,
        analysis: Mapping[str, Any],
        segments: list[Mapping[str, Any]],
        entities: list[Mapping[str, Any]],
        highlights: list[Mapping[str, Any]],
        options: list[Mapping[str, Any]],
        available_times: Mapping[str, int | None],
        final_status: str,
        finished_utc: str,
    ) -> dict[str, Any]:
        """Commit immutable result rows, terminal attempt, receipt, and stream sequence atomically."""
        if final_status not in {"completed", "needs-review"}:
            raise ValueError("assist result status must be completed or needs-review")
        with self._db:
            existing = self._db.execute(
                "SELECT payload_hash, receipt_json FROM assist_result_receipts WHERE job_id=? AND attempt_id=?",
                (job_id, attempt_id),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] != payload_hash:
                    raise ValueError("job attempt already has a different committed result")
                return json.loads(existing["receipt_json"])

            job = self._db.execute(
                """SELECT j.status, j.current_attempt_id, j.asset_id, j.source_session_id,
                          a.status AS attempt_status
                   FROM transcription_jobs j JOIN transcription_attempts a
                     ON a.job_id=j.job_id AND a.attempt_id=?
                   WHERE j.job_id=?""",
                (attempt_id, job_id),
            ).fetchone()
            if (job is None or job["source_session_id"] != source_session_id
                    or job["current_attempt_id"] != attempt_id or job["status"] != "running"
                    or job["attempt_status"] != "running"):
                raise ValueError("worker result is not for the active running attempt")
            source = self._db.execute(
                "SELECT source_id FROM replay_sources WHERE source_session_id=?", (source_session_id,)
            ).fetchone()
            if source is None or source["source_id"] != source_id:
                raise ValueError("worker result source binding no longer matches the archive")

            self._db.execute(
                """INSERT INTO assist_analyses
                   (analysis_id, source_session_id, source_id, kind, job_id, attempt_id, input_hash,
                    versions_json, window_start_ms, window_end_ms, status, result_json, created_utc)
                   VALUES (?, ?, ?, 'assist', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (analysis["id"], source_session_id, source_id, job_id, attempt_id,
                 analysis["input_hash"], _json(analysis["versions"]), analysis["window_start_ms"],
                 analysis["window_end_ms"], final_status, _json(result_payload), analysis["created_utc"]),
            )
            self._db.executemany(
                """INSERT INTO assist_transcript_segments
                   (source_session_id, analysis_id, segment_id, available_ms, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                [(source_session_id, analysis["id"], row["id"], available_times.get(f"transcript_segment:{row['id']}"), _json(row))
                 for row in segments],
            )
            self._db.executemany(
                """INSERT INTO assist_candidate_entities
                   (source_session_id, analysis_id, ordinal, segment_id, available_ms, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [(source_session_id, analysis["id"], index, row["segment_id"],
                  available_times.get(f"transcript_segment:{row['segment_id']}"), _json(row))
                 for index, row in enumerate(entities)],
            )
            self._db.executemany(
                """INSERT INTO assist_highlights
                   (source_session_id, analysis_id, highlight_id, available_ms, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                [(source_session_id, analysis["id"], row["id"], available_times.get(f"highlight:{row['id']}"), _json(row))
                 for row in highlights],
            )
            self._db.executemany(
                """INSERT INTO assist_options
                   (source_session_id, analysis_id, option_id, available_ms, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                [(source_session_id, analysis["id"], row["id"], available_times.get(f"option:{row['id']}"), _json(row))
                 for row in options],
            )

            job_update = self._db.execute(
                """UPDATE transcription_jobs SET status=?, finished_utc=?, error_json=NULL
                   WHERE job_id=? AND source_session_id=? AND current_attempt_id=? AND status='running'""",
                (final_status, finished_utc, job_id, source_session_id, attempt_id),
            )
            attempt_update = self._db.execute(
                """UPDATE transcription_attempts SET status=?, finished_utc=?, error_json=NULL
                   WHERE job_id=? AND attempt_id=? AND status='running'""",
                (final_status, finished_utc, job_id, attempt_id),
            )
            if job_update.rowcount != 1 or attempt_update.rowcount != 1:
                raise ValueError("worker attempt became terminal before result commit")

            self._db.execute(
                "INSERT OR IGNORE INTO assist_stream_state(source_session_id, sequence) VALUES (?, 0)",
                (source_session_id,),
            )
            sequence_row = self._db.execute(
                "SELECT sequence FROM assist_stream_state WHERE source_session_id=?", (source_session_id,)
            ).fetchone()
            sequence = int(sequence_row["sequence"])
            stream_rows: list[tuple[str, str | None, int | None, int, Mapping[str, Any]]] = []
            for segment in segments:
                segment_entities = [entity for entity in entities if entity["segment_id"] == segment["id"]]
                stream_rows.append(("segment", analysis["id"], available_times.get(f"transcript_segment:{segment['id']}"),
                                    0, {
                                        "segment": segment,
                                        "entities": segment_entities,
                                        "time_alignment": analysis["versions"]["time_alignment"],
                                        "alignment_uncertainty": (
                                            "Audio-to-session time mapping is unknown; do not place this segment on historical replay time."
                                            if analysis["versions"]["time_alignment"] == "unknown" else None
                                        ),
                                    }))
            for highlight in highlights:
                stream_rows.append(("highlight", analysis["id"], available_times.get(f"highlight:{highlight['id']}"), 0, highlight))
            for option in options:
                stream_rows.append(("option", analysis["id"], available_times.get(f"option:{option['id']}"), 1, option))
            stream_rows.append(("job_progress", analysis["id"], analysis["window_end_ms"], 0, {
                "id": job_id, "source_session_id": source_session_id, "asset_id": job["asset_id"],
                "attempt_id": attempt_id, "status": final_status, "analysis_id": analysis["id"],
            }))
            receipt = {
                "receipt_id": f"assist-receipt-{uuid.uuid4().hex}",
                "source_session_id": source_session_id,
                "source_id": source_id,
                "job_id": job_id,
                "attempt_id": attempt_id,
                "analysis_id": analysis["id"],
                "status": final_status,
                "payload_hash": payload_hash,
                "sequence": sequence + len(stream_rows),
            }
            self._db.execute(
                "INSERT INTO assist_result_receipts(job_id, attempt_id, payload_hash, receipt_json) VALUES (?, ?, ?, ?)",
                (job_id, attempt_id, payload_hash, _json(receipt)),
            )
            for event_type, analysis_id, available_ms, evaluator_only, payload in stream_rows:
                sequence += 1
                self._db.execute(
                    """INSERT INTO assist_stream_events
                       (source_session_id, sequence, event_type, analysis_id, job_id, available_ms,
                        evaluator_only, payload_json, created_utc)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source_session_id, sequence, event_type, analysis_id, job_id, available_ms,
                     evaluator_only, _json(payload), finished_utc),
                )
            self._db.execute(
                "UPDATE assist_stream_state SET sequence=? WHERE source_session_id=?",
                (sequence, source_session_id),
            )
            return receipt

    def list_segments(
        self, source_session_id: str, *, analysis_id: str | None, until_ms: int | None,
        limit: int, after_ordinal: int = 0,
    ) -> list[dict[str, Any]]:
        sql = """SELECT s.rowid AS ordinal, s.segment_id, s.payload_json, s.analysis_id,
                        a.versions_json
                 FROM assist_transcript_segments s JOIN assist_analyses a USING(analysis_id)
                 WHERE s.source_session_id=?"""
        params: list[Any] = [source_session_id]
        if analysis_id is not None:
            sql += " AND s.analysis_id=?"
            params.append(analysis_id)
        if until_ms is not None:
            sql += " AND s.available_ms IS NOT NULL AND s.available_ms<=?"
            params.append(until_ms)
            sql += " AND a.window_end_ms<=?"
            params.append(until_ms)
        sql += " AND s.rowid>?"
        params.append(after_ordinal)
        sql += " ORDER BY s.rowid LIMIT ?"
        params.append(limit)
        rows = self._db.execute(sql, params).fetchall()
        result = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            entity_rows = self._db.execute(
                "SELECT payload_json FROM assist_candidate_entities WHERE analysis_id=? AND segment_id=? ORDER BY ordinal",
                (row["analysis_id"], row["segment_id"]),
            ).fetchall()
            time_alignment = json.loads(row["versions_json"]).get("time_alignment", "unknown")
            result.append({
                "ordinal": row["ordinal"], "segment": payload,
                "entities": [json.loads(item["payload_json"]) for item in entity_rows],
                "time_alignment": time_alignment,
                "alignment_uncertainty": (
                    "Audio-to-session time mapping is unknown; do not place this segment on historical replay time."
                    if time_alignment == "unknown" else None
                ),
            })
        return result

    def list_highlights(
        self, source_session_id: str, *, analysis_id: str | None, until_ms: int | None,
        limit: int, after_ordinal: int = 0,
    ) -> list[dict[str, Any]]:
        sql = """SELECT h.rowid AS ordinal, h.payload_json, h.highlight_id
                 FROM assist_highlights h JOIN assist_analyses a USING(analysis_id)
                 WHERE h.source_session_id=?"""
        params: list[Any] = [source_session_id]
        if analysis_id is not None:
            sql += " AND h.analysis_id=?"
            params.append(analysis_id)
        if until_ms is not None:
            sql += " AND h.available_ms IS NOT NULL AND h.available_ms<=? AND a.window_end_ms<=?"
            params.append(until_ms)
            params.append(until_ms)
        sql += " AND h.rowid>?"
        params.append(after_ordinal)
        sql += " ORDER BY h.rowid LIMIT ?"
        params.append(limit)
        return [{"ordinal": row["ordinal"], "item": json.loads(row["payload_json"])}
                for row in self._db.execute(sql, params).fetchall()]

    def list_options(
        self, source_session_id: str, *, analysis_id: str, until_ms: int | None,
        limit: int, after_ordinal: int = 0,
    ) -> list[dict[str, Any]]:
        sql = """SELECT o.rowid AS ordinal, o.payload_json, o.option_id FROM assist_options o
                 JOIN assist_analyses a USING(analysis_id)
                 WHERE o.source_session_id=? AND o.analysis_id=?"""
        params: list[Any] = [source_session_id, analysis_id]
        if until_ms is not None:
            sql += " AND o.available_ms IS NOT NULL AND o.available_ms<=? AND a.window_end_ms<=?"
            params.append(until_ms)
            params.append(until_ms)
        sql += " AND o.rowid>?"
        params.append(after_ordinal)
        sql += " ORDER BY o.rowid LIMIT ?"
        params.append(limit)
        return [{"ordinal": row["ordinal"], "item": json.loads(row["payload_json"])}
                for row in self._db.execute(sql, params).fetchall()]

    def list_jobs(self, source_session_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT job_id FROM transcription_jobs WHERE source_session_id=? ORDER BY created_utc, rowid",
            (source_session_id,),
        ).fetchall()
        return [job for row in rows if (job := self.get_job(source_session_id, row["job_id"])) is not None]

    def segment_available_ms(self, source_session_id: str, segment_id: str) -> int | None:
        row = self._db.execute(
            "SELECT available_ms FROM assist_transcript_segments WHERE source_session_id=? AND segment_id=?",
            (source_session_id, segment_id),
        ).fetchone()
        return int(row["available_ms"]) if row is not None and row["available_ms"] is not None else None

    def analysis(self, source_session_id: str, analysis_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT * FROM assist_analyses WHERE source_session_id=? AND analysis_id=?",
            (source_session_id, analysis_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["analysis_id"], "source_session_id": row["source_session_id"],
            "source_id": row["source_id"], "job_id": row["job_id"], "attempt_id": row["attempt_id"],
            "kind": row["kind"], "input_hash": row["input_hash"], "versions": json.loads(row["versions_json"]),
            "window_start_ms": row["window_start_ms"], "window_end_ms": row["window_end_ms"],
            "status": row["status"], "created_utc": row["created_utc"],
        }

    def analysis_ids(self, source_session_id: str) -> list[str]:
        rows = self._db.execute(
            "SELECT analysis_id FROM assist_analyses WHERE source_session_id=? ORDER BY created_utc, rowid",
            (source_session_id,),
        ).fetchall()
        return [row["analysis_id"] for row in rows]

    def transcript_segment_at(self, source_session_id: str, segment_id: str, until_ms: int) -> dict[str, Any] | None:
        row = self._db.execute(
            """SELECT s.payload_json, s.analysis_id, a.versions_json FROM assist_transcript_segments s
               JOIN assist_analyses a USING(analysis_id)
               WHERE s.source_session_id=? AND s.segment_id=? AND s.available_ms IS NOT NULL
                 AND s.available_ms<=? AND a.window_end_ms<=?""",
            (source_session_id, segment_id, until_ms, until_ms),
        ).fetchone()
        if row is None:
            return None
        entity_rows = self._db.execute(
            "SELECT payload_json FROM assist_candidate_entities WHERE analysis_id=? AND segment_id=? ORDER BY ordinal",
            (row["analysis_id"], segment_id),
        ).fetchall()
        time_alignment = json.loads(row["versions_json"]).get("time_alignment", "unknown")
        return {
            "segment": json.loads(row["payload_json"]),
            "entities": [json.loads(item["payload_json"]) for item in entity_rows],
            "time_alignment": time_alignment,
            "alignment_uncertainty": (
                "Audio-to-session time mapping is unknown; do not place this segment on historical replay time."
                if time_alignment == "unknown" else None
            ),
        }

    def entity_segment(self, source_session_id: str, segment_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT payload_json, available_ms FROM assist_transcript_segments WHERE source_session_id=? AND segment_id=?",
            (source_session_id, segment_id),
        ).fetchone()
        if row is None:
            return None
        return {"payload": json.loads(row["payload_json"]), "available_ms": row["available_ms"]}

    def detector_alert_available_ms(
        self, source_session_id: str, analysis_id: str, alert_id: str
    ) -> int | None:
        analysis = self._db.execute(
            "SELECT kind, window_start_ms, window_end_ms FROM replay_analyses "
            "WHERE source_session_id=? AND analysis_id=?", (source_session_id, analysis_id),
        ).fetchone()
        if analysis is None or analysis["kind"] != "detector":
            return None
        rows = self._db.execute(
            "SELECT at_ms, frame_json FROM replay_analysis_frames WHERE analysis_id=? ORDER BY at_ms",
            (analysis_id,),
        ).fetchall()
        for row in rows:
            frame = json.loads(row["frame_json"])
            state = frame.get("state", frame)
            alerts = state.get("alerts", {}) if isinstance(state, dict) else {}
            if isinstance(alerts, dict) and (alert_id in alerts or any(
                isinstance(alert, dict) and alert.get("id") == alert_id for alert in alerts.values()
            )):
                return int(row["at_ms"])
        return None

    def find_detector_alert_available_ms(
        self, source_session_id: str, alert_id: str, start_ms: int, end_ms: int
    ) -> int | None:
        rows = self._db.execute(
            """SELECT a.analysis_id FROM replay_analyses a
               WHERE a.source_session_id=? AND a.kind='detector'
                 AND a.window_start_ms<=? AND a.window_end_ms>=?""",
            (source_session_id, end_ms, start_ms),
        ).fetchall()
        for row in rows:
            available = self.detector_alert_available_ms(source_session_id, row["analysis_id"], alert_id)
            if available is not None and start_ms <= available <= end_ms:
                return available
        return None

    def source_event_available_ms(self, source_session_id: str, source_event_id: str) -> int | None:
        row = self._db.execute(
            """SELECT e.sim_ms FROM replay_source_events e JOIN replay_sources s USING(source_id)
               WHERE s.source_session_id=? AND e.source_event_id=?""",
            (source_session_id, source_event_id),
        ).fetchone()
        return int(row["sim_ms"]) if row is not None and row["sim_ms"] is not None else None

    def stream_sequence(self, source_session_id: str) -> int:
        row = self._db.execute(
            "SELECT sequence FROM assist_stream_state WHERE source_session_id=?", (source_session_id,)
        ).fetchone()
        return int(row["sequence"]) if row is not None else 0

    def stream_events(self, source_session_id: str, after_sequence: int) -> list[dict[str, Any]]:
        rows = self._db.execute(
            """SELECT sequence, event_type, analysis_id, job_id, available_ms,
                      evaluator_only, payload_json FROM assist_stream_events
               WHERE source_session_id=? AND sequence>? ORDER BY sequence""",
            (source_session_id, after_sequence),
        ).fetchall()
        return [{
            "sequence": row["sequence"], "type": row["event_type"], "analysis_id": row["analysis_id"],
            "job_id": row["job_id"], "available_ms": row["available_ms"],
            "evaluator_only": bool(row["evaluator_only"]), "payload": json.loads(row["payload_json"]),
        } for row in rows]

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
