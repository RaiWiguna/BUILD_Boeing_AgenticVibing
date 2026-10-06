"""BE-07 append-only review and debrief checks over authored synthetic fixtures."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from test_be_06 import (
    FakeClock,
    FixedWorker,
    _asset_metadata,
    _client,
    _import_source,
    _operator,
    _result,
    _upload,
    _wait_job,
    _wav,
)


def _prepare_assist(
    client: TestClient, token: str, source_name: str,
) -> tuple[dict[str, Any], str, dict[str, Any], str]:
    manifest, source_id = _import_source(client, token, source_name)
    uploaded = _upload(client, token, source_id, manifest)
    assert uploaded.status_code == 201, uploaded.text
    job = _wait_job(client, token, source_id, uploaded.json()["job"]["id"])
    assert job["status"] == "completed"
    return manifest, source_id, job, uploaded.json()["job"]


def test_append_only_corrections_reviews_and_restart_preserve_raw_rows(tmp_path: Path) -> None:
    clock = FakeClock()
    first_receipt: dict[str, Any]
    source_id = "be07-synthetic-persistence"
    analysis_id = ""
    with _client(tmp_path, worker=FixedWorker(), clock=clock) as client:
        token = _operator(client)
        _, source_id, job, _ = _prepare_assist(client, token, source_id)
        analysis_id = job["result_receipt"]["analysis_id"]
        headers = {"Authorization": f"Bearer {token}"}
        database = client.app.state.manager.archive.db
        source_before = database.execute(
            "SELECT event_bytes, content_hash FROM replay_sources WHERE source_session_id=?", (source_id,),
        ).fetchone()
        raw_result_before = database.execute(
            "SELECT result_json FROM assist_analyses WHERE analysis_id=?", (analysis_id,),
        ).fetchone()["result_json"]
        raw_segment_before = database.execute(
            "SELECT payload_json FROM assist_transcript_segments WHERE source_session_id=? AND segment_id=?",
            (source_id, "seg-synthetic-1"),
        ).fetchone()["payload_json"]

        correction = {
            "request_id": "be07-correction-1",
            "expected_revision": 0,
            "text": "Synthetic corrected transcript text.",
            "reason": "Authored fixture correction for append-only review coverage.",
        }
        corrected = client.post(
            f"/api/v1/sessions/{source_id}/transcripts/seg-synthetic-1/corrections",
            headers=headers,
            json=correction,
        )
        assert corrected.status_code == 200, corrected.text
        first_receipt = corrected.json()
        assert first_receipt["reviewer"] == "Lab operator"
        assert first_receipt["timestamp_utc"] == datetime.fromtimestamp(clock.wall, tz=UTC).isoformat()
        assert first_receipt["expected_revision"] == first_receipt["basis_revision"] == 0
        assert first_receipt["revision"] == 1
        assert client.post(
            f"/api/v1/sessions/{source_id}/transcripts/seg-synthetic-1/corrections",
            headers=headers,
            json=correction,
        ).json() == first_receipt

        highlight_review = client.post(
            f"/api/v1/sessions/{source_id}/highlights/highlight-synthetic-1/review",
            headers=headers,
            json={
                "request_id": "be07-highlight-review-1", "expected_revision": 0,
                "decision": "confirmed", "reason": "Synthetic fixture decision only.",
            },
        )
        corrected_candidate = client.post(
            f"/api/v1/sessions/{source_id}/highlights/highlight-synthetic-1/review",
            headers=headers,
            json={
                "request_id": "be07-highlight-correction-1", "expected_revision": 1,
                "decision": "corrected", "correction": "Synthetic corrected candidate wording.",
                "reason": "Candidate text remains an immutable worker result.",
            },
        )
        option_review = client.post(
            f"/api/v1/sessions/{source_id}/replay-analyses/{analysis_id}/options/option-synthetic-1/review",
            headers=headers,
            json={
                "request_id": "be07-option-review-1", "expected_revision": 0,
                "decision": "unresolved", "reason": "Synthetic fixture has unresolved support.",
            },
        )
        assert highlight_review.status_code == corrected_candidate.status_code == option_review.status_code == 200
        assert highlight_review.json()["sequence"] == first_receipt["sequence"] + 1
        assert corrected_candidate.json()["sequence"] == first_receipt["sequence"] + 2
        assert option_review.json()["sequence"] == first_receipt["sequence"] + 3

        transcripts = client.get(f"/api/v1/sessions/{source_id}/transcripts", headers=headers).json()["items"]
        first_segment = next(item for item in transcripts if item["segment"]["id"] == "seg-synthetic-1")
        assert first_segment["segment"]["text"] == "Synthetic fixture segment one; not audio transcription."
        assert first_segment["corrected_view"] == {
            "text": correction["text"], "revision": 1, "is_corrected": True,
        }
        assert len(first_segment["revision_history"]) == 1
        assert first_segment["revision_history"][0]["basis_revision"] == 0
        assert first_segment["review_history"][0]["decision"] == "corrected"
        highlights = client.get(f"/api/v1/sessions/{source_id}/highlights", headers=headers).json()["items"]
        assert highlights[0]["statement"].startswith("Synthetic review highlight")
        assert highlights[0]["current_decision"]["decision"] == "corrected"
        assert [item["decision"] for item in highlights[0]["review_history"]] == ["confirmed", "corrected"]
        assert highlights[0]["statement"].startswith("Synthetic review highlight")
        options = client.get(
            f"/api/v1/sessions/{source_id}/replay-analyses/{analysis_id}/options", headers=headers,
        ).json()["items"]
        assert options[0]["current_decision"]["decision"] == "unresolved"

        assert database.execute(
            "SELECT payload_json FROM assist_transcript_segments WHERE source_session_id=? AND segment_id=?",
            (source_id, "seg-synthetic-1"),
        ).fetchone()["payload_json"] == raw_segment_before
        assert database.execute(
            "SELECT result_json FROM assist_analyses WHERE analysis_id=?", (analysis_id,),
        ).fetchone()["result_json"] == raw_result_before
        source_after = database.execute(
            "SELECT event_bytes, content_hash FROM replay_sources WHERE source_session_id=?", (source_id,),
        ).fetchone()
        assert tuple(source_after) == tuple(source_before)
        assert database.execute(
            "SELECT COUNT(*) FROM assist_review_receipts",
        ).fetchone()[0] == 4
        assert database.execute(
            "SELECT COUNT(*) FROM assist_stream_events WHERE event_type='review_annotation'",
        ).fetchone()[0] == 4

    # The app and Archive connection are closed; a fresh app reconstructs the reads from SQLite.
    with _client(tmp_path, worker=None, clock=clock) as reopened:
        token = _operator(reopened)
        headers = {"Authorization": f"Bearer {token}"}
        snapshot = reopened.get(
            f"/api/v1/sessions/{source_id}/assist-snapshot?analysis_id={analysis_id}", headers=headers,
        )
        assert snapshot.status_code == 200
        assert snapshot.json()["sequence"] == option_review.json()["sequence"]
        assert len(snapshot.json()["payload"]["review_annotations"]) == 4
        assert snapshot.json()["payload"]["segments"][0]["corrected_view"]["text"] == correction["text"]
        rows = reopened.app.state.manager.assist_service.stream_events(source_id, first_receipt["sequence"])
        assert [row["type"] for row in rows] == [
            "review_annotation", "review_annotation", "review_annotation",
        ]


def test_request_collisions_stale_revision_and_untrusted_authority_are_atomic(tmp_path: Path) -> None:
    with _client(tmp_path, worker=FixedWorker()) as client:
        token = _operator(client)
        _, source_id, job, _ = _prepare_assist(client, token, "be07-synthetic-idempotency")
        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/sessions/{source_id}/transcripts/seg-synthetic-1/corrections"
        body = {
            "request_id": "be07-idempotency-1", "expected_revision": 0,
            "text": "Accepted synthetic correction.", "reason": "Fixture reason.",
        }
        accepted = client.post(url, headers=headers, json=body)
        assert accepted.status_code == 200
        sequence = client.app.state.manager.assist_service.stream_sequence(source_id)
        assert client.post(url, headers=headers, json=body).json() == accepted.json()

        changed_body = body | {"text": "Different content for a reused ID."}
        assert client.post(url, headers=headers, json=changed_body).status_code == 409
        second_actor_token = _operator(client)
        second_actor_headers = {"Authorization": f"Bearer {second_actor_token}"}
        assert client.post(url, headers=second_actor_headers, json=body).status_code == 409
        stale = body | {"request_id": "be07-stale-1", "expected_revision": 0}
        assert client.post(url, headers=headers, json=stale).status_code == 409
        assert client.post(
            f"/api/v1/sessions/{source_id}/replay-analyses/not-the-analysis/options/option-synthetic-1/review",
            headers=headers,
            json={"request_id": "be07-cross-analysis-1", "expected_revision": 0,
                  "decision": "confirmed", "reason": "Synthetic test."},
        ).status_code == 404
        assert client.post(
            url, headers=headers,
            json=body | {"reviewer": "forged", "actor_id": "forged", "evaluator_replay": True},
        ).status_code == 422
        assert client.post(
            f"/api/v1/sessions/{source_id}/highlights/highlight-synthetic-1/review",
            headers=headers,
            json={"request_id": "be07-invalid-review-1", "expected_revision": 0,
                  "decision": "confirmed"},
        ).status_code == 422
        database = client.app.state.manager.archive.db
        assert database.execute("SELECT COUNT(*) FROM assist_transcript_revisions").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM assist_review_annotations").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM assist_review_receipts").fetchone()[0] == 1
        assert database.execute(
            "SELECT COUNT(*) FROM assist_stream_events WHERE event_type='review_annotation'",
        ).fetchone()[0] == 1
        assert client.app.state.manager.assist_service.stream_sequence(source_id) == sequence
        assert database.execute(
            "SELECT COUNT(*) FROM assist_result_receipts WHERE attempt_id=?", (job["attempt_id"],),
        ).fetchone()[0] == 1


def test_source_read_capability_can_read_but_cannot_write_or_cross_source(tmp_path: Path) -> None:
    with _client(tmp_path, worker=FixedWorker()) as client:
        token = _operator(client)
        manifest, source_id, job, _ = _prepare_assist(client, token, "be07-synthetic-scope-a")
        _, other_source = _import_source(client, token, "be07-synthetic-scope-b")
        analysis_id = job["result_receipt"]["analysis_id"]
        headers = {"Authorization": f"Bearer {token}"}
        created_review = client.post(f"/api/v1/sessions/{source_id}/reviews", headers=headers)
        assert created_review.status_code == 201
        read_token = created_review.json()["source_read_token"]
        read_headers = {"Authorization": f"Bearer {read_token}"}
        assert client.get(f"/api/v1/sessions/{source_id}/transcripts", headers=read_headers).status_code == 200
        assert client.get(f"/api/v1/sessions/{source_id}/assist-snapshot", headers=read_headers).status_code == 200
        assert client.get(
            f"/api/v1/sessions/{source_id}/replay-analyses/{analysis_id}/options", headers=read_headers,
        ).status_code == 403
        assert client.get(
            f"/api/v1/sessions/{other_source}/transcripts", headers=read_headers,
        ).status_code == 403
        assert client.post(
            f"/api/v1/sessions/{source_id}/transcripts/seg-synthetic-1/corrections",
            headers=read_headers,
            json={"request_id": "be07-read-token-correction", "expected_revision": 0,
                  "text": "Not authorized.", "reason": "Read-only test."},
        ).status_code == 403
        assert client.post(
            f"/api/v1/sessions/{source_id}/highlights/highlight-synthetic-1/review",
            headers=read_headers,
            json={"request_id": "be07-read-token-highlight", "expected_revision": 0,
                  "decision": "dismissed", "reason": "Read-only test."},
        ).status_code == 403
        assert client.post(
            f"/api/v1/sessions/{source_id}/replay-analyses/{analysis_id}/options/option-synthetic-1/review",
            headers=read_headers,
            json={"request_id": "be07-read-token-option", "expected_revision": 0,
                  "decision": "dismissed", "reason": "Read-only test."},
        ).status_code == 403
        assert client.post(f"/api/v1/sessions/{source_id}/reviews", headers=read_headers).status_code == 403
        assert _upload(client, read_token, source_id, manifest).status_code == 403
        assert client.app.state.manager.assist_service.stream_sequence(source_id) == job["result_receipt"]["sequence"]


def test_review_annotation_stream_and_reconnect_snapshot_are_typed_and_consistent(tmp_path: Path) -> None:
    with _client(tmp_path, worker=FixedWorker()) as client:
        token = _operator(client)
        _, source_id, job, _ = _prepare_assist(client, token, "be07-synthetic-stream")
        analysis_id = job["result_receipt"]["analysis_id"]
        headers = {"Authorization": f"Bearer {token}"}
        with client.websocket_connect(f"/api/v1/sessions/{source_id}/assist-stream") as socket:
            socket.send_json({"token": token, "after_sequence": job["result_receipt"]["sequence"]})
            initial = socket.receive_json()
            assert initial["type"] == "snapshot"
            assert initial["sequence"] == job["result_receipt"]["sequence"]
            response = client.post(
                f"/api/v1/sessions/{source_id}/highlights/highlight-synthetic-1/review",
                headers=headers,
                json={"request_id": "be07-stream-review-1", "expected_revision": 0,
                      "decision": "dismissed", "reason": "Synthetic stream test."},
            )
            assert response.status_code == 200
            message = socket.receive_json()
            assert message["schema_version"] == "assist-1"
            assert message["type"] == "review_annotation"
            assert message["sequence"] == response.json()["sequence"]
            assert message["payload"]["analysis_id"] == analysis_id
            assert message["payload"]["target_id"] == "highlight-synthetic-1"
            assert message["payload"]["reviewer"] == "Lab operator"

        with client.websocket_connect(f"/api/v1/sessions/{source_id}/assist-stream") as reconnect:
            reconnect.send_json({"token": token, "after_sequence": 0, "analysis_id": analysis_id})
            snapshot = reconnect.receive_json()
            assert snapshot["type"] == "snapshot"
            assert snapshot["sequence"] == response.json()["sequence"]
            assert snapshot["payload"]["review_annotations"][0]["decision"] == "dismissed"
            assert snapshot["payload"]["highlights"][0]["current_decision"]["decision"] == "dismissed"


def test_imported_debrief_exports_preserve_uncertainty_and_escape_untrusted_text(tmp_path: Path) -> None:
    clock = FakeClock()

    def hostile_synthetic_result(request: Any) -> dict[str, Any]:
        result = _result(request)
        result["highlights"] = []
        result["options"] = []
        result["segments"][0]["text"] = "<script>alert('fixture')</script>"
        return result

    with _client(tmp_path, worker=FixedWorker(hostile_synthetic_result), clock=clock) as client:
        token = _operator(client)
        manifest, source_id = _import_source(client, token, "be07-synthetic-debrief", aligned=False)
        metadata = _asset_metadata(manifest)
        metadata["audio_start"] = None
        uploaded = client.post(
            f"/api/v1/sessions/{source_id}/audio-assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"audio": ("fixture.wav", _wav(), "audio/wav")},
            data={"metadata": json.dumps(metadata)},
        )
        assert uploaded.status_code == 201, uploaded.text
        job = _wait_job(client, token, source_id, uploaded.json()["job"]["id"])
        analysis_id = job["result_receipt"]["analysis_id"]
        formula_text = " \t=HYPERLINK(\"https://example.invalid\",\"x\") <script>alert(1)</script>"
        correction = client.post(
            f"/api/v1/sessions/{source_id}/transcripts/seg-synthetic-1/corrections",
            headers={"Authorization": f"Bearer {token}"},
            json={"request_id": "be07-html-correction", "expected_revision": 0,
                  "text": formula_text, "reason": "<img src=x onerror=alert(1)>"},
        )
        assert correction.status_code == 200
        json_response = client.get(f"/api/v1/sessions/{source_id}/debrief", headers={"Authorization": f"Bearer {token}"})
        assert json_response.status_code == 200
        report = json_response.json()
        serialized = json.dumps(report, ensure_ascii=False)
        assert report["source"]["data_label"] == "synthetic_fixture_not_operationally_validated"
        assert report["source"]["source_kind"] == "synthetic"
        assert report["analyses"][0]["id"] == analysis_id
        assert report["source_event_refs"][0]["kind"] == "session_event"
        assert report["transcripts"][0]["segment"]["text"] == "<script>alert('fixture')</script>"
        assert report["transcripts"][0]["corrected_view"]["text"] == formula_text
        assert any(ref["status"] == "alignment_unknown" for ref in report["unresolved_refs"])
        assert any(item["target_kind"] == "transcript_segment" for item in report["uncertainty"])
        assert token not in serialized
        assert str(tmp_path / "private-audio") not in serialized
        assert "restricted_truth" not in serialized and "ground_truth_samples" not in serialized

        html_response = client.get(
            f"/api/v1/sessions/{source_id}/debrief?format=html", headers={"Authorization": f"Bearer {token}"},
        )
        assert html_response.status_code == 200
        assert "&lt;script&gt;" in html_response.text
        assert "<script>" not in html_response.text
        assert "&lt;img src=x onerror=alert(1)&gt;" in html_response.text

        csv_response = client.get(
            f"/api/v1/sessions/{source_id}/debrief?format=csv", headers={"Authorization": f"Bearer {token}"},
        )
        assert csv_response.status_code == 200
        rows = list(csv.DictReader(csv_response.text.splitlines()))
        annotation_row = next(row for row in rows if row["record_type"] == "review_annotation")
        assert annotation_row["text"].startswith("'")
        assert token not in csv_response.text
        assert str(tmp_path / "private-audio") not in csv_response.text

        # Existing synthetic /report remains instructor-only and retains restricted truth separation.
        synthetic_session = client.post(
            "/api/v1/sessions", headers={"Authorization": f"Bearer {token}"},
            json={"scenario_id": "overlap", "seed": 42},
        )
        assert synthetic_session.status_code == 201
        synthetic_report = client.get(
            f"/api/v1/sessions/{synthetic_session.json()['id']}/report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert synthetic_report.status_code == 200
        assert "ground_truth_samples" in synthetic_report.json()
        assert client.get(
            f"/api/v1/sessions/{source_id}/report", headers={"Authorization": f"Bearer {token}"},
        ).status_code == 409


def test_be06_stream_schema_migration_preserves_old_rows_before_review_append(tmp_path: Path) -> None:
    source_name = "be07-synthetic-legacy-stream"
    with _client(tmp_path, worker=FixedWorker()) as client:
        token = _operator(client)
        _, source_id, job, _ = _prepare_assist(client, token, source_name)
        original_rows = [tuple(row) for row in client.app.state.manager.archive.db.execute(
            "SELECT source_session_id, sequence, event_type, analysis_id, job_id, available_ms, "
            "evaluator_only, payload_json, created_utc FROM assist_stream_events ORDER BY sequence"
        ).fetchall()]
        assert len(original_rows) == 5

    database_path = tmp_path / "be06.sqlite3"
    database = sqlite3.connect(database_path)
    database.execute("PRAGMA foreign_keys=OFF")
    database.execute("DROP TRIGGER assist_stream_events_no_update")
    database.execute("DROP TRIGGER assist_stream_events_no_delete")
    database.execute("DROP INDEX assist_stream_events_time_idx")
    database.execute("ALTER TABLE assist_stream_events RENAME TO assist_stream_events_for_test")
    database.execute(
        """CREATE TABLE assist_stream_events (
            source_session_id TEXT NOT NULL REFERENCES replay_sources(source_session_id),
            sequence INTEGER NOT NULL CHECK(sequence > 0),
            event_type TEXT NOT NULL CHECK(event_type IN ('job_progress','segment','highlight','option')),
            analysis_id TEXT NOT NULL REFERENCES assist_analyses(analysis_id),
            job_id TEXT NOT NULL REFERENCES transcription_jobs(job_id),
            available_ms INTEGER,
            evaluator_only INTEGER NOT NULL DEFAULT 0 CHECK(evaluator_only IN (0,1)),
            payload_json TEXT NOT NULL,
            created_utc TEXT NOT NULL,
            PRIMARY KEY(source_session_id, sequence)
        )"""
    )
    database.execute(
        """INSERT INTO assist_stream_events
           SELECT source_session_id, sequence, event_type, analysis_id, job_id, available_ms,
                  evaluator_only, payload_json, created_utc
           FROM assist_stream_events_for_test ORDER BY sequence"""
    )
    database.execute("DROP TABLE assist_stream_events_for_test")
    database.execute(
        "CREATE INDEX assist_stream_events_time_idx "
        "ON assist_stream_events(source_session_id, sequence, available_ms)"
    )
    database.execute(
        """CREATE TRIGGER assist_stream_events_no_update BEFORE UPDATE ON assist_stream_events
           BEGIN SELECT RAISE(ABORT, 'assist stream events are immutable'); END"""
    )
    database.execute(
        """CREATE TRIGGER assist_stream_events_no_delete BEFORE DELETE ON assist_stream_events
           BEGIN SELECT RAISE(ABORT, 'assist stream events are immutable'); END"""
    )
    database.commit()
    database.close()

    with _client(tmp_path, worker=None) as reopened:
        token = _operator(reopened)
        headers = {"Authorization": f"Bearer {token}"}
        legacy_rows = [tuple(row) for row in reopened.app.state.manager.archive.db.execute(
            "SELECT source_session_id, sequence, event_type, analysis_id, job_id, available_ms, "
            "evaluator_only, payload_json, created_utc FROM assist_stream_events ORDER BY sequence"
        ).fetchall()]
        assert legacy_rows == original_rows
        assert reopened.app.state.manager.assist_service.stream_sequence(source_id) == 5
        response = reopened.post(
            f"/api/v1/sessions/{source_id}/transcripts/seg-synthetic-1/corrections",
            headers=headers,
            json={"request_id": "be07-post-migration-review", "expected_revision": 0,
                  "text": "Synthetic post-migration correction.", "reason": "Compatibility test."},
        )
        assert response.status_code == 200, response.text
        assert response.json()["sequence"] == 6
        schema_sql = reopened.app.state.manager.archive.db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='assist_stream_events'",
        ).fetchone()["sql"]
        assert "review_annotation" in schema_sql
        assert reopened.app.state.manager.archive.db.execute(
            "SELECT COUNT(*) FROM assist_stream_events",
        ).fetchone()[0] == len(original_rows) + 1
        assert reopened.app.state.manager.archive.db.execute(
            "SELECT COUNT(*) FROM assist_result_receipts WHERE attempt_id=?", (job["attempt_id"],),
        ).fetchone()[0] == 1
