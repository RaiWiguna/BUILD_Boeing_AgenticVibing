"""Real A source/evidence/alert lifecycle. B absent; no provider or source mutation."""

import importlib
import json

import pytest
from flowlens.core.errors import ContractError
from test_geometry_kernel import layout
from test_import_commit import commit, context
from test_import_commit import committed as committed
from test_import_metadata import prepare, request
from test_imports import importer as importer
from test_imports import stage, upload
from test_observed_rules import event, pose
from test_occupancy import at, reader


def source(importer, committed, *, tracks=None, events=None, modify=None, key="upload-key"):
    tracks = tracks if tracks is not None else [pose(0, time=1000), pose(0, time=2000)]
    events = events if events is not None else [event("HOLD_SHORT", time=500, line_id="H1")]
    tracks = [t.model_copy(update={"source_event_id": f"t{i}"}) for i, t in enumerate(tracks)]
    preview = stage(
        importer,
        [
            upload(),
            upload(
                json.dumps([t.model_dump(mode="json") for t in tracks]).encode(),
                role="tracks",
                filename="tracks.json",
                media_type="application/json",
            ),
            upload(
                json.dumps([e.model_dump(mode="json") for e in events]).encode(),
                role="events",
                filename="events.json",
                media_type="application/json",
            ),
        ],
        key=key,
    )

    def declaration(d):
        for file in d["files"]:
            file["clock"] = {
                "timezone": "UTC",
                "method": "DECLARED_OFFSET",
                "offset_ms": 0,
                "uncertainty_ms": 0,
                "basis": "synthetic rules oracle",
                "reviewer": "fixture",
            }
        d["layout"] = layout().model_dump(mode="json")
        d["coverage"] = {
            "vehicles": True,
            "speaker_identity": None,
            "gaps": [],
            "basis": "synthetic observed tracks",
        }
        d["identities"] = []
        for index, entity in enumerate(sorted({str(t.entity_id) for t in tracks})):
            first = next(t for t in tracks if str(t.entity_id) == entity)
            d["identities"].append(
                {
                    "source_entity_id": entity,
                    "callsign": f"fixture{index}23",
                    "aliases": [],
                    "validity": {"start_ms": 0, "end_ms": 100000},
                    "evidence_file_id": str(preview.files[1].id),
                    "evidence_record_ids": [first.source_event_id],
                }
            )
        if modify:
            modify(d)

    prepared = prepare(importer, preview, request(preview, modify=declaration))
    receipt = commit(committed, preview, prepared)
    context(committed, receipt)
    return receipt, prepared


def service(committed, tmp_path, **kwargs):
    occupancy, files, evidence = reader(committed, tmp_path)
    return (
        importlib.import_module("flowlens.geometry.service").Rules(occupancy, evidence, **kwargs),
        files,
        evidence,
    )


def test_real_source_rules_resolvable_evidence_and_current_revocation(
    importer, committed, tmp_path
):
    receipt, prepared = source(
        importer, committed, tracks=[pose(-50, time=1000), pose(-10, time=2000)]
    )
    s, files, evidence = service(committed, tmp_path)
    try:
        c = at(committed, receipt, 2000, "AS_KNOWN")
        result = s.evaluate(c)
        hold = next(r for r in result.signals if r.rule_id == "HOLD_SHORT_MOVEMENT")
        assert hold.status == "ACTIVE" and len(hold.evidence) == 3
        for e in hold.evidence:
            assert evidence.get(c, e.id) == e
        committed[2].revoke(committed[3].token.get_secret_value(), c.actor_id, c.session_id, "read")
        with pytest.raises(ContractError):
            s.evaluate(c)
    finally:
        files.close()


def test_durable_publish_idempotency_history_and_ack_seen_only(importer, committed, tmp_path):
    receipt, prepared = source(
        importer, committed, tracks=[pose(0, time=1000), pose(130, time=2000)]
    )
    s, files, _ = service(committed, tmp_path)
    try:
        c = at(committed, receipt, 1000)
        first = s.publish(c, key="rules-1", expected_version=0)
        assert first.version == 1 and first == s.publish(c, key="rules-1", expected_version=0)
        alert = next(r for r in first.alerts if r.rule_id == "STOPPED_IN_PROTECTION")
        assert alert.status == "ACTIVE"
        ack = s.acknowledge(c, alert.id, key="seen-1", expected_version=alert.version)
        assert (
            ack.meaning == "SEEN_ONLY"
            and s.acknowledge(c, alert.id, key="seen-1", expected_version=alert.version) == ack
        )
        assert s.history(c, alert.id)[-1].status == "ACTIVE"
        with pytest.raises(ContractError):
            s.acknowledge(c, alert.id, key="wrong-version", expected_version=0)
        c = at(committed, receipt, 2000)
        second = s.publish(c, key="rules-2", expected_version=1)
        assert second.version == 2
        history = s.history(c, alert.id)
        assert [r.status for r in history] == ["ACTIVE", "CLEARED"]
        assert history[1].previous_revision_id == history[0].revision_id
        with pytest.raises(ContractError):
            s.publish(at(committed, receipt, 999), key="backwards", expected_version=2)
    finally:
        files.close()


def test_publish_requires_analysis_or_review_but_read_evaluation_remains(
    importer, committed, tmp_path
):
    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    try:
        c = at(committed, receipt, 1000)
        committed[2].revoke(
            committed[3].token.get_secret_value(), c.actor_id, c.session_id, "analysis"
        )
        c = at(committed, receipt, 1000)
        assert s.evaluate(c).signals
        with pytest.raises(ContractError):
            s.publish(c, key="forbidden", expected_version=0)
        assert s.inventory(c) == []
    finally:
        files.close()


def test_source_alert_survives_rules_and_ack_severity_independent(importer, committed, tmp_path):
    from test_alert_reducer import source as source_alert

    _, alert, _ = source_alert()
    receipt, _ = source(importer, committed, events=[alert])
    s, files, _ = service(committed, tmp_path)
    try:
        c = at(committed, receipt, 1000)
        result = s.publish(c, key="external", expected_version=0)
        source_item = next(a for a in result.alerts if a.origin == "SOURCE")
        assert source_item.source_severity == "CRITICAL" and source_item.priority is None
        s.acknowledge(c, source_item.id, key="seen", expected_version=1)
        assert s.history(c, source_item.id)[-1].source_severity == "CRITICAL"
        assert s.history(c, source_item.id)[-1].status == "ACTIVE"
    finally:
        files.close()


def test_active_dropout_transition_is_unknown_and_never_auto_clear(importer, committed, tmp_path):
    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    try:
        first = s.publish(at(committed, receipt, 2000), key="active", expected_version=0)
        alert = next(a for a in first.alerts if a.rule_id == "STOPPED_IN_PROTECTION")
        s.publish(at(committed, receipt, 8000), key="stale", expected_version=1)
        history = s.history(at(committed, receipt, 8000), alert.id)
        assert [a.status for a in history] == ["ACTIVE", "UNKNOWN"]
    finally:
        files.close()


@pytest.mark.parametrize("boundary", ["after_alerts", "after_event", "before_commit"])
def test_publish_fault_rolls_back_alerts_head_event_audit_receipt(
    importer, committed, tmp_path, boundary
):
    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    c = at(committed, receipt, 1000)
    tables = [
        "platform_alert_revisions",
        "platform_rule_heads",
        "platform_rule_receipts",
        "platform_events",
        "platform_audit",
    ]
    with s.database.begin() as uow:
        before = {
            table: uow.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in tables
        }

    def failed(phase):
        if phase == boundary:
            raise RuntimeError("synthetic publication fault")

    s.fault = failed
    try:
        with pytest.raises(RuntimeError):
            s.publish(c, key="fault", expected_version=0)
        with s.database.begin() as uow:
            assert before == {
                table: uow.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }
        s.fault = lambda phase: None
        assert s.publish(c, key="fault", expected_version=0).version == 1
    finally:
        files.close()


def test_permission_loss_between_calculation_and_publish_denied(importer, committed, tmp_path):
    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    c = at(committed, receipt, 1000)

    def revoked(phase):
        if phase == "after_evaluate":
            committed[2].revoke(
                committed[3].token.get_secret_value(), c.actor_id, c.session_id, "analysis"
            )

    s.fault = revoked
    try:
        with pytest.raises(ContractError):
            s.publish(c, key="revoked", expected_version=0)
        with s.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_alert_revisions").fetchone()[
                    0
                ]
                == 0
            )
    finally:
        files.close()


def test_seen_fault_rolls_back_receipt_event_audit_and_retry(importer, committed, tmp_path):
    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    c = at(committed, receipt, 1000)
    result = s.publish(c, key="active", expected_version=0)
    alert = next(a for a in result.alerts if a.status == "ACTIVE")
    with s.database.begin() as uow:
        before = (
            uow.connection.execute("SELECT COUNT(*) FROM platform_audit").fetchone()[0],
            uow.connection.execute("SELECT COUNT(*) FROM platform_events").fetchone()[0],
        )

    def failed(phase):
        if phase == "before_seen_commit":
            raise RuntimeError("synthetic seen failure")

    s.fault = failed
    try:
        with pytest.raises(RuntimeError):
            s.acknowledge(c, alert.id, key="seen", expected_version=1)
        with s.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_alert_seen").fetchone()[0]
                == 0
            )
            assert before == (
                uow.connection.execute("SELECT COUNT(*) FROM platform_audit").fetchone()[0],
                uow.connection.execute("SELECT COUNT(*) FROM platform_events").fetchone()[0],
            )
        s.fault = lambda phase: None
        assert s.acknowledge(c, alert.id, key="seen", expected_version=1).meaning == "SEEN_ONLY"
    finally:
        files.close()


def test_receipts_conflicts_modes_and_historical_visibility(importer, committed, tmp_path):
    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    try:
        c = at(committed, receipt, 1000, "AS_KNOWN")
        first = s.publish(c, key="same", expected_version=0)
        with pytest.raises(ContractError):
            s.publish(c, key="same", expected_version=1)
        c = at(committed, receipt, 2000, "AS_KNOWN")
        s.publish(c, key="later", expected_version=1)
        c = at(committed, receipt, 1000, "AS_KNOWN")
        assert all(a.as_of_ms <= 1000 for a in s.inventory(c))
        c = at(committed, receipt, 1000, "DEBRIEF")
        assert s.inventory(c) == []
        with pytest.raises(ContractError):
            s.publish(c, key="same", expected_version=0)
        assert s.publish(c, key="debrief", expected_version=0).version == 1
        assert first.sequence > 0
    finally:
        files.close()


def test_reopen_preserves_history_receipt_ack_and_append_only(importer, committed, tmp_path):
    import sqlite3

    from flowlens.storage.sqlite.database import Database

    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    c = at(committed, receipt, 1000)
    first = s.publish(c, key="first", expected_version=0)
    alert = next(a for a in first.alerts if a.status == "ACTIVE")
    ack = s.acknowledge(c, alert.id, key="ack", expected_version=1)
    # Release the API owner, then reopen all live guards against the same durable database.
    original = s.database
    original.close()
    reopened = Database(original.path)
    importer[0].database = reopened
    committed[1].database = reopened
    committed[2].database = reopened
    committed[2].sessions.database = reopened
    reopened.context_guard = committed[2].enforce
    s.database = reopened
    try:
        assert s.publish(c, key="first", expected_version=0) == first
        assert s.acknowledge(c, alert.id, key="ack", expected_version=1) == ack
        assert s.history(c, alert.id)[-1] == alert
        with reopened.begin() as uow:
            with pytest.raises(sqlite3.IntegrityError):
                uow.connection.execute("UPDATE platform_alert_revisions SET payload='{}'")
            with pytest.raises(sqlite3.IntegrityError):
                uow.connection.execute("DELETE FROM platform_rule_receipts")
    finally:
        reopened.close()
        files.close()


def test_shared_rule_uses_real_clock_margin(importer, committed, tmp_path):
    from uuid import uuid4

    crossing = pose(0, -30, 90, time=1000, speed=10)
    arrival = pose(-150, 0, time=1000, speed=20, entity=uuid4())

    def uncertain(d):
        for file in d["files"]:
            file["clock"]["uncertainty_ms"] = 500

    receipt, _ = source(importer, committed, tracks=[crossing, arrival], modify=uncertain)
    s, files, _ = service(committed, tmp_path)
    try:
        result = s.evaluate(at(committed, receipt, 1000))
        shared = next(x for x in result.signals if x.rule_id == "RUNWAY_SHARED_RESOURCE")
        # crossing [1500,6501], arrival [2500,14501] after declared500ms margins.
        assert shared.overlap_ms == 4001 and shared.status == "ACTIVE"
    finally:
        files.close()


def test_concurrent_duplicate_publish_commits_one_effect(importer, committed, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    c = at(committed, receipt, 1000)
    barrier = Barrier(2)

    def paused(phase):
        if phase == "after_evaluate":
            barrier.wait(timeout=10)

    s.fault = paused
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(s.publish, c, key="concurrent", expected_version=0) for _ in range(2)
            ]
            a, b = [f.result(timeout=20) for f in futures]
        assert a == b
        with s.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_rule_receipts").fetchone()[0]
                == 1
            )
            assert (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_audit WHERE action='RULES_PUBLISHED'"
                ).fetchone()[0]
                == 1
            )
    finally:
        files.close()


def test_session_and_run_scopes_do_not_share_alert_history(importer, committed, tmp_path):
    from uuid import uuid4

    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    c = at(committed, receipt, 1000)
    first = s.publish(c, key="source-view", expected_version=0)
    run_id = uuid4()
    with s.database.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_runs VALUES (?,?,?)",
            (str(c.session_id), str(run_id), c.input_revision),
        )
        uow.commit()
    try:
        run_ctx = at(committed, receipt, 1000, run=run_id)
        assert s.inventory(run_ctx) == [] and s.history(run_ctx, first.alerts[0].id) == []
        second = s.publish(run_ctx, key="run-view", expected_version=0)
        assert all(a.analysis_run_id == run_id for a in second.alerts)
        other, _ = source(
            importer,
            committed,
            key="other-upload",
            modify=lambda d: d.update(source_identifier="fixture-other"),
        )
        other_ctx = at(committed, other, 1000)
        assert s.history(other_ctx, first.alerts[0].id) == []
        with pytest.raises(ContractError):
            s.acknowledge(other_ctx, first.alerts[0].id, key="cross-scope", expected_version=1)
    finally:
        files.close()


def test_conflicting_source_alert_updates_at_same_time_never_choose_clear_by_uuid(
    importer, committed, tmp_path
):
    from test_alert_reducer import source as source_alert

    _, active, _ = source_alert(status="ACTIVE", severity="CRITICAL", time=1000)
    _, clear, _ = source_alert(status="CLEARED", severity="WARNING", time=1000)
    receipt, _ = source(importer, committed, events=[active, clear])
    s, files, _ = service(committed, tmp_path)
    try:
        result = s.publish(at(committed, receipt, 1000), key="conflict", expected_version=0)
        alert = next(a for a in result.alerts if a.origin == "SOURCE")
        assert alert.status == "UNKNOWN" and alert.reason == "SOURCE_ALERT_CONFLICT"
        assert len(alert.source_variants) == 2 and len(alert.evidence) == 2
        assert {json.loads(e.statement)["severity"] for e in alert.source_variants} == {
            "CRITICAL",
            "WARNING",
        }
        assert alert.priority is None
    finally:
        files.close()


@pytest.mark.parametrize(
    "cause,reason",
    [("identity", "IDENTITY_UNKNOWN"), ("layout", "LAYOUT_MISSING"), ("clock", "CLOCK_UNKNOWN")],
)
def test_frame_eligibility_never_reports_empty_evaluated_geometry(
    importer, committed, tmp_path, cause, reason
):
    def modify(d):
        if cause == "identity":
            d["identities"] = []
        elif cause == "layout":
            d["layout"] = None
        elif cause == "clock":
            for f in d["files"]:
                f["clock"] = {"timezone": "UTC", "method": "UNKNOWN"}

    receipt, _ = source(importer, committed, modify=modify)
    s, files, _ = service(committed, tmp_path)
    try:
        result = s.evaluate(at(committed, receipt, 1000))
        assert result.status == "NOT_EVALUABLE" and result.reason == reason
    finally:
        files.close()


def test_overlapping_clock_bounds_do_not_prove_hold_instruction_precedes_movement(
    importer, committed, tmp_path
):
    def modify(d):
        for file in d["files"]:
            file["clock"]["uncertainty_ms"] = 500

    receipt, _ = source(
        importer, committed, tracks=[pose(-50, time=1000), pose(-10, time=2000)], modify=modify
    )
    s, files, _ = service(committed, tmp_path)
    try:
        signal = next(
            r
            for r in s.evaluate(at(committed, receipt, 2000)).signals
            if r.rule_id == "HOLD_SHORT_MOVEMENT"
        )
        assert signal.status == "UNKNOWN" and signal.reason == "INSTRUCTION_TIME_UNCERTAIN"
    finally:
        files.close()
