"""BE-08 committed-state recovery, compatible branches, backup, and runtime manifest."""

from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from test_be_06 import (
    OPERATOR_KEY,
    FakeClock,
    FixedWorker,
    _import_source,
    _operator,
)
from test_be_07 import _client as _be07_client
from test_be_07 import _prepare_assist

from backend.app import create_app
from backend.models import Role
from backend.ports import CompositionOverrides
from backend.session import SessionError


class FaultWriter:
    def __init__(self, archive: Any) -> None:
        self.archive = archive
        self.fail_next: str | None = None

    def create(self, session_id: str, metadata: dict[str, Any]) -> None:
        self.archive.create(session_id, metadata)

    def save(self, session_id, status, events, public, private, command=None) -> None:
        failure, self.fail_next = self.fail_next, None
        if failure == "before":
            raise sqlite3.OperationalError("injected pre-commit failure")
        self.archive.save(session_id, status, events, public, private, command)
        if failure == "after":
            raise sqlite3.OperationalError("injected post-commit response failure")

    def command(self, session_id: str, command_id: str):
        return self.archive.command(session_id, command_id)


def _fault_client(tmp_path: Path, clock: FakeClock | None = None) -> tuple[TestClient, dict[str, Any]]:
    fake_clock = clock or FakeClock()
    state: dict[str, Any] = {}

    def writer_factory(archive):
        state["writer"] = FaultWriter(archive)
        return state["writer"]

    app = create_app(
        db_path=tmp_path / "be08.sqlite3",
        operator_key=OPERATOR_KEY,
        run_clock=False,
        ports=CompositionOverrides(session_writer_factory=writer_factory),
        wall_clock=fake_clock.wall_time,
        monotonic_clock=fake_clock.monotonic_time,
        audio_root=tmp_path / "private-audio",
    )
    return TestClient(app), state


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _new_synthetic_session(client: TestClient, token: str, name: str = "overlap") -> str:
    created = client.post("/api/v1/sessions", headers=_headers(token),
                          json={"scenario_id": name, "seed": 19})
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_precommit_rollback_receipt_conflicts_and_stale_revision(tmp_path: Path) -> None:
    client, state = _fault_client(tmp_path)
    with client:
        token = _operator(client)
        session_id = _new_synthetic_session(client, token)
        manager = client.app.state.manager
        session = manager.sessions[session_id]
        archive = manager.archive
        writer: FaultWriter = state["writer"]
        command = {"command_id": "be08-start-once", "expected_revision": 0, "type": "START"}
        before_frame = copy.deepcopy(archive.frame(session_id))
        before_events = archive.all_events(session_id)
        before_receipts = archive.db.execute(
            "SELECT COUNT(*) FROM commands WHERE session_id=?", (session_id,),
        ).fetchone()[0]

        writer.fail_next = "before"
        failed = client.post(f"/api/v1/sessions/{session_id}/commands", headers=_headers(token), json=command)
        assert failed.status_code == 503
        assert archive.frame(session_id) == before_frame
        assert archive.all_events(session_id) == before_events
        assert archive.db.execute(
            "SELECT COUNT(*) FROM commands WHERE session_id=?", (session_id,),
        ).fetchone()[0] == before_receipts
        assert session.revision == before_frame[0]["revision"]
        assert session.sequence == before_frame[0]["sequence"]
        assert session.event_ordinal == before_frame[1]["event_ordinal"]
        assert session.pending_events == []
        assert session.status == "PAUSED" and session.error
        assert archive.command(session_id, command["command_id"]) is None

        accepted = client.post(f"/api/v1/sessions/{session_id}/commands", headers=_headers(token), json=command)
        assert accepted.status_code == 200, accepted.text
        receipt = accepted.json()
        assert client.post(
            f"/api/v1/sessions/{session_id}/commands", headers=_headers(token), json=command,
        ).json() == receipt
        assert sum(event.get("command", {}).get("command_id") == command["command_id"]
                   for event in archive.all_events(session_id)) == 1

        changed_body = command | {"expected_revision": 1, "type": "PAUSE"}
        assert client.post(
            f"/api/v1/sessions/{session_id}/commands", headers=_headers(token), json=changed_body,
        ).status_code == 409
        other_actor = manager.mint(Role.INSTRUCTOR, "Lab operator", None)
        assert client.post(
            f"/api/v1/sessions/{session_id}/commands", headers=_headers(other_actor), json=command,
        ).status_code == 409
        before_stale = copy.deepcopy(archive.frame(session_id))
        stale = command | {"command_id": "be08-stale", "type": "PAUSE"}
        assert client.post(
            f"/api/v1/sessions/{session_id}/commands", headers=_headers(token), json=stale,
        ).status_code == 409
        assert archive.frame(session_id) == before_stale
        assert archive.command(session_id, stale["command_id"]) is None


def test_postcommit_ambiguity_uses_durable_receipt_once(tmp_path: Path) -> None:
    client, state = _fault_client(tmp_path)
    with client:
        token = _operator(client)
        session_id = _new_synthetic_session(client, token)
        archive = client.app.state.manager.archive
        state["writer"].fail_next = "after"
        command = {"command_id": "be08-ambiguous-commit", "expected_revision": 0, "type": "START"}
        accepted = client.post(f"/api/v1/sessions/{session_id}/commands", headers=_headers(token), json=command)
        assert accepted.status_code == 200, accepted.text
        response = accepted.json()
        durable = archive.command(session_id, command["command_id"])
        assert durable is not None and durable[1] == response
        retry = client.post(f"/api/v1/sessions/{session_id}/commands", headers=_headers(token), json=command)
        assert retry.status_code == 200 and retry.json() == response
        assert sum(event.get("command", {}).get("command_id") == command["command_id"]
                   for event in archive.all_events(session_id)) == 1
        assert archive.db.execute(
            "SELECT COUNT(*) FROM commands WHERE session_id=? AND command_id=?",
            (session_id, command["command_id"]),
        ).fetchone()[0] == 1


def test_ack_assessment_and_tick_failures_restore_committed_state(tmp_path: Path) -> None:
    client, state = _fault_client(tmp_path)
    with client:
        token = _operator(client)
        session_id = _new_synthetic_session(client, token)
        manager = client.app.state.manager
        archive = manager.archive
        session = manager.sessions[session_id]
        # An authored synthetic alert lets this test exercise acknowledgement persistence.
        session.alerts = {"fixture-alert": {
            "id": "fixture-alert", "key": "fixture-alert", "status": "RESOLVED",
        }}
        session.save()
        writer: FaultWriter = state["writer"]

        before = copy.deepcopy(archive.frame(session_id))
        before_events = archive.all_events(session_id)
        writer.fail_next = "before"
        ack = client.post(f"/api/v1/sessions/{session_id}/acknowledgements", headers=_headers(token),
                          json={"alert_id": "fixture-alert"})
        assert ack.status_code == 503
        assert archive.frame(session_id) == before
        assert archive.all_events(session_id) == before_events
        assert session.acknowledgements == before[0]["acknowledgements"]

        before = copy.deepcopy(archive.frame(session_id))
        before_events = archive.all_events(session_id)
        writer.fail_next = "before"
        assessment = client.post(
            f"/api/v1/sessions/{session_id}/assessments", headers=_headers(token),
            json={"type": "bookmark", "text": "synthetic test note", "values": {}},
        )
        assert assessment.status_code == 503
        assert archive.frame(session_id) == before
        assert archive.all_events(session_id) == before_events
        assert session.assessments == before[0]["assessments"]

        started = client.post(
            f"/api/v1/sessions/{session_id}/commands", headers=_headers(token),
            json={"command_id": "be08-tick-start", "expected_revision": 0, "type": "START"},
        )
        assert started.status_code == 200
        before = copy.deepcopy(archive.frame(session_id))
        before_events = archive.all_events(session_id)
        before_simulator = copy.deepcopy(before[1]["simulator"])
        writer.fail_next = "before"
        try:
            session.advance(ticks=2)
        except SessionError as error:
            assert error.status == 503
        else:
            raise AssertionError("injected tick failure was not surfaced")
        assert archive.frame(session_id) == before
        assert archive.all_events(session_id) == before_events
        assert session.sequence == before[0]["sequence"]
        assert session.revision == before[0]["revision"]
        assert json.dumps(session.simulator.checkpoint()) == json.dumps(before_simulator)
        assert session.pending_events == []
        assert session.status == "PAUSED" and session.error


def test_compatible_branch_restores_private_checkpoint_and_ancestry(tmp_path: Path) -> None:
    client, _ = _fault_client(tmp_path)
    with client:
        token = _operator(client)
        source_id = _new_synthetic_session(client, token)
        ended = client.post(
            f"/api/v1/sessions/{source_id}/commands", headers=_headers(token),
            json={"command_id": "be08-end-source", "expected_revision": 0, "type": "END"},
        )
        assert ended.status_code == 200
        archive = client.app.state.manager.archive
        parent_frame = copy.deepcopy(archive.frame(source_id))
        parent_events = archive.all_events(source_id)
        branch = client.post(f"/api/v1/sessions/{source_id}/branches", headers=_headers(token), json={"at_ms": 0})
        assert branch.status_code == 201, branch.text
        child_id = branch.json()["id"]
        child_frame = archive.frame(child_id)
        assert child_frame is not None
        assert child_frame[1]["simulator"] == parent_frame[1]["simulator"]
        assert child_frame[1]["tracks"] == parent_frame[1]["tracks"]
        assert child_frame[1]["previous_tracks"] == parent_frame[1]["previous_tracks"]
        child_events = archive.all_events(child_id)
        assert child_events[:len(parent_events)] == parent_events
        assert child_events[-1]["type"] == "BRANCH_CREATED"
        assert archive.frame(source_id) == parent_frame
        assert archive.all_events(source_id) == parent_events

        second_parent = _new_synthetic_session(client, token, name="hold_line")
        assert client.post(
            f"/api/v1/sessions/{second_parent}/commands", headers=_headers(token),
            json={"command_id": "be08-end-incompatible", "expected_revision": 0, "type": "END"},
        ).status_code == 200
        incompatible = archive.frame(second_parent)
        assert incompatible is not None
        private = incompatible[1]
        private.pop("schema_version")
        with archive.db:
            archive.db.execute(
                "UPDATE frames SET private=? WHERE session_id=? AND sim_ms=?",
                (json.dumps(private, allow_nan=False), second_parent, incompatible[0]["sim_ms"]),
            )
        count_before = archive.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        rejected = client.post(
            f"/api/v1/sessions/{second_parent}/branches", headers=_headers(token), json={"at_ms": 0},
        )
        assert rejected.status_code == 409
        assert "Checkpoint" in rejected.json()["detail"]
        assert archive.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == count_before


def test_restart_keeps_interrupted_replay_be07_review_and_safe_backup(tmp_path: Path) -> None:
    clock = FakeClock()
    synthetic_id = ""
    source_id = "be08-synthetic-review-source"
    analysis_id = ""
    corrected_text = "BE-08 synthetic corrected transcript text."
    annotation_response: dict[str, Any] = {}

    with _be07_client(tmp_path, worker=FixedWorker(), clock=clock) as client:
        token = _operator(client)
        synthetic_id = _new_synthetic_session(client, token)
        assert client.post(
            f"/api/v1/sessions/{synthetic_id}/commands", headers=_headers(token),
            json={"command_id": "be08-running-before-restart", "expected_revision": 0, "type": "START"},
        ).status_code == 200

        _, source_id, job, _ = _prepare_assist(client, token, source_id)
        analysis_id = job["result_receipt"]["analysis_id"]
        result_receipt = job["result_receipt"]
        correction = client.post(
            f"/api/v1/sessions/{source_id}/transcripts/seg-synthetic-1/corrections",
            headers=_headers(token),
            json={"request_id": "be08-correction", "expected_revision": 0,
                  "text": corrected_text, "reason": "synthetic restart persistence fixture"},
        )
        assert correction.status_code == 200, correction.text
        annotation = client.post(
            f"/api/v1/sessions/{source_id}/highlights/highlight-synthetic-1/review",
            headers=_headers(token),
            json={"request_id": "be08-review-annotation", "expected_revision": 0,
                  "decision": "confirmed", "reason": "synthetic restart persistence fixture"},
        )
        assert annotation.status_code == 200, annotation.text
        annotation_response = annotation.json()
        snapshot = client.get(
            f"/api/v1/sessions/{source_id}/assist-snapshot?analysis_id={analysis_id}", headers=_headers(token),
        )
        assert snapshot.status_code == 200
        assert snapshot.json()["sequence"] == annotation_response["sequence"]
        debrief = client.get(f"/api/v1/sessions/{source_id}/debrief", headers=_headers(token))
        assert debrief.status_code == 200
        assert debrief.json()["transcripts"][0]["corrected_view"]["text"] == corrected_text
        assert any(item["target_id"] == "highlight-synthetic-1" and item["decision"] == "confirmed"
                   for item in debrief.json()["review_annotations"])
        durable_receipt = client.app.state.manager.archive.db.execute(
            "SELECT receipt_json FROM assist_review_receipts WHERE request_id=?",
            ("be08-review-annotation",),
        ).fetchone()
        assert json.loads(durable_receipt["receipt_json"]) == annotation_response

        manifest_response = client.get("/api/v1/runtime-manifest", headers=_headers(token))
        assert manifest_response.status_code == 200
        runtime = manifest_response.json()
        assert runtime["schema_version"] == "flowlens-runtime-1"
        assert runtime["runtime"]["python_version"]
        assert runtime["runtime"]["architecture"]
        assert runtime["configuration"]["python_requirement_declared"] == ">=3.11"
        assert runtime["configuration"]["journal_mode"] == "wal"
        assert runtime["optional_providers"]["assist_worker"]["available"] is True
        assert runtime["optional_providers"]["assist_worker"]["inference_verified"] is False
        assert runtime["optional_providers"]["local_model"]["available"] is False
        assert all("requirement" in item and "available" in item for item in runtime["dependencies"])
        fastapi_dependency = next(item for item in runtime["dependencies"] if item["distribution"] == "fastapi")
        assert fastapi_dependency["available"] is True and fastapi_dependency["installed_version"]
        serialized_runtime = json.dumps(runtime)
        for private_value in (token, str(tmp_path / "private-audio"), "source_ref", "rng_state",
                              "restricted_truth", "ground_truth_samples"):
            assert private_value not in serialized_runtime

        backup_path = client.app.state.manager.archive.backup_to(tmp_path / "be08-backup.sqlite3")
        backup = sqlite3.connect(backup_path)
        try:
            assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert backup.execute("SELECT COUNT(*) FROM events WHERE session_id=?", (synthetic_id,)).fetchone()[0] > 0
            assert backup.execute("SELECT COUNT(*) FROM commands WHERE session_id=?", (synthetic_id,)).fetchone()[0] == 1
            assert backup.execute("SELECT COUNT(*) FROM replay_import_receipts").fetchone()[0] == 1
            assert backup.execute("SELECT COUNT(*) FROM assist_result_receipts").fetchone()[0] == 1
            assert backup.execute("SELECT COUNT(*) FROM assist_review_receipts").fetchone()[0] == 2
            assert backup.execute("SELECT COUNT(*) FROM assist_transcript_revisions").fetchone()[0] == 1
            assert backup.execute("SELECT COUNT(*) FROM assist_review_annotations").fetchone()[0] == 2
            assert backup.execute("SELECT sequence FROM assist_stream_state").fetchone()[0] == snapshot.json()["sequence"]
        finally:
            backup.close()

    with _be07_client(tmp_path, worker=None, clock=clock) as reopened:
        token = _operator(reopened)
        headers = _headers(token)
        metadata = reopened.get(f"/api/v1/sessions/{synthetic_id}", headers=headers)
        assert metadata.status_code == 200 and metadata.json()["status"] == "INTERRUPTED"
        assert synthetic_id not in reopened.app.state.manager.sessions
        replay_snapshot = reopened.get(f"/api/v1/sessions/{synthetic_id}/snapshot", headers=headers)
        assert replay_snapshot.status_code == 200 and replay_snapshot.json()["status"] == "INTERRUPTED"
        assert reopened.post(
            f"/api/v1/sessions/{synthetic_id}/commands", headers=headers,
            json={"command_id": "be08-no-auto-resume", "expected_revision": 1, "type": "START"},
        ).status_code == 409

        transcripts = reopened.get(f"/api/v1/sessions/{source_id}/transcripts", headers=headers)
        assert transcripts.status_code == 200
        assert transcripts.json()["items"][0]["corrected_view"]["text"] == corrected_text
        source_events = reopened.get(f"/api/v1/sessions/{source_id}/events", headers=headers)
        assert source_events.status_code == 200 and source_events.json()["items"]
        assist_snapshot = reopened.get(
            f"/api/v1/sessions/{source_id}/assist-snapshot?analysis_id={analysis_id}", headers=headers,
        )
        assert assist_snapshot.status_code == 200
        assert assist_snapshot.json()["sequence"] == annotation_response["sequence"]
        assert any(item["target_id"] == "highlight-synthetic-1" and item["decision"] == "confirmed"
                   for item in assist_snapshot.json()["payload"]["review_annotations"])
        debrief = reopened.get(f"/api/v1/sessions/{source_id}/debrief", headers=headers)
        assert debrief.status_code == 200
        assert any(item["target_id"] == "highlight-synthetic-1" and item["decision"] == "confirmed"
                   for item in debrief.json()["review_annotations"])
        durable_receipt = reopened.app.state.manager.archive.db.execute(
            "SELECT receipt_json FROM assist_review_receipts WHERE request_id=?",
            ("be08-review-annotation",),
        ).fetchone()
        assert json.loads(durable_receipt["receipt_json"]) == annotation_response
        durable_result = reopened.app.state.manager.archive.db.execute(
            "SELECT receipt_json FROM assist_result_receipts WHERE job_id=? AND attempt_id=?",
            (job["id"], job["attempt_id"]),
        ).fetchone()
        assert json.loads(durable_result["receipt_json"]) == result_receipt

        runtime = reopened.get("/api/v1/runtime-manifest", headers=headers).json()
        assert runtime["optional_providers"]["assist_worker"]["available"] is False
        assert runtime["optional_providers"]["local_model"]["available"] is False


def test_imported_replay_stays_reviewable_but_cannot_be_branched(tmp_path: Path) -> None:
    with _be07_client(tmp_path, worker=None) as client:
        token = _operator(client)
        _, source_id = _import_source(client, token, "be08-imported-synthetic")
        headers = _headers(token)
        review = client.post(f"/api/v1/sessions/{source_id}/reviews", headers=headers)
        assert review.status_code == 201, review.text
        snapshot = client.get(f"/api/v1/sessions/{review.json()['id']}/snapshot", headers=headers)
        assert snapshot.status_code == 200
        assert snapshot.json()["kind"] == "review"
        branch = client.post(
            f"/api/v1/sessions/{review.json()['id']}/branches", headers=headers, json={"at_ms": 100},
        )
        assert branch.status_code == 409
        source_events = client.get(f"/api/v1/sessions/{source_id}/events", headers=headers)
        assert source_events.status_code == 200 and source_events.json()["items"]
