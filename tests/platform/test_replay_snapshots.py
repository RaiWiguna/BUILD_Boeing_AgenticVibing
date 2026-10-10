"""A07.1 deterministic replay with independent availability expectations."""

import importlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from flowlens.contracts.models import RequestContext, Snapshot, SourceEvent, Track
from flowlens.core.errors import ContractError
from flowlens.testing.harness import FakeAnalysis
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer


def engine():
    return importlib.import_module("flowlens.replay.snapshots")


def ctx():
    return RequestContext(
        actor_id=uuid4(),
        capabilities=["read"],
        session_id=uuid4(),
        analysis_run_id=None,
        input_revision=1,
        input_hash="a" * 64,
        as_of_ms=300,
        mode="AS_KNOWN",
        request_id=uuid4(),
    )


def event(c, identifier, time, available, quality="SUPPORTED"):
    return SourceEvent(
        id=UUID(int=identifier),
        session_id=c.session_id,
        analysis_run_id=None,
        revision=1,
        event_time_ms=time,
        available_time_ms=available,
        recorded_at=datetime(2026, 1, 1, tzinfo=UTC),
        source_id=UUID(int=99),
        source_event_id=str(identifier),
        kind="REPORT",
        entity_id=None,
        source_hash=c.input_hash,
        quality=quality,
        statement="Synthetic observed report",
    )


@pytest.mark.parametrize(
    "asof,mode,ids",
    [
        (99, "AS_KNOWN", []),
        (100, "AS_KNOWN", []),
        (199, "AS_KNOWN", []),
        (200, "AS_KNOWN", [1]),
        (300, "AS_KNOWN", [1, 4]),
        (40000, "AS_KNOWN", [1, 4, 2]),
        (300, "DEBRIEF", [1, 4, 2]),
        (500, "DEBRIEF", [1, 4, 2, 3]),
    ],
)
def test_independent_time_oracle(asof, mode, ids):
    c = ctx().model_copy(update={"as_of_ms": asof, "mode": mode})
    rows = [
        event(c, 3, 500, None),
        event(c, 2, 300, 40000),
        event(c, 4, 100, 300),
        event(c, 1, 100, 200),
    ]
    result = engine().reduce(c, rows, None, sequence=7)
    assert [r.id.int for r in result.events] == ids
    assert result.sequence == 7 and result.mode == mode and result.as_of_ms == asof
    assert result.quality == ("SUPPORTED" if ids else "MISSING")
    assert engine().reduce(c, list(reversed(rows)), None, sequence=7) == result


def test_dedup_conflict_scope_and_revalidation():
    c = ctx()
    row = event(c, 1, 100, 200)
    assert len(engine().reduce(c, [row, row], None, sequence=0).events) == 1
    for bad in (
        row.model_copy(update={"statement": "different"}),
        row.model_copy(update={"session_id": uuid4()}),
        row.model_copy(update={"revision": 2}),
        row.model_copy(update={"event_time_ms": -1}),
    ):
        with pytest.raises(ContractError):
            engine().reduce(c, [row, bad], None, sequence=0)


def test_track_fields_preserved_and_quality_not_fabricated():
    c = ctx()
    base = event(c, 1, 100, 200, quality="AMBIGUOUS").model_dump()
    base.update(
        kind="TRACK",
        x_m=2.0,
        y_m=3.0,
        heading_deg=90.0,
        speed_mps=0.0,
        length_m=20.0,
        width_m=4.0,
        age_ms=9,
        layout_version="synthetic-1",
    )
    track = Track(**base)
    result = engine().reduce(c, [track], None, sequence=0)
    assert result.events[0].kind == "TRACK" and track.x_m == 2.0
    assert result.quality == "AMBIGUOUS"


def fresh_at(committed, media, asof, mode="AS_KNOWN", run=None):
    db = committed[0].imports.database
    with db.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_context_state SET mode=?,as_of_ms=? WHERE session_id=?",
            (mode, asof, str(media[2].session_id)),
        )
        uow.commit()
    return committed[2].human_context(
        committed[3].token.get_secret_value(), media[2].session_id, run_id=run
    )


def test_real_source_checkpoints_rebuild_and_restart(media, committed, importer):
    service = engine().Replay(committed[1], snapshot_reader=FakeAnalysis().snapshot)
    for mode in ("AS_KNOWN", "DEBRIEF"):
        for time in (99, 200, 500, 40000, 200, 500):
            c = fresh_at(committed, media, time, mode)
            cached = service.snapshot(c)
            assert cached == service.snapshot(c, checkpoints=False)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_replay_snapshots").fetchone()[0]
            == 8
        )
        assert uow.connection.execute("PRAGMA foreign_key_check").fetchall() == []
        before = uow.connection.execute(
            "SELECT payload FROM platform_records ORDER BY id"
        ).fetchall()
    again = engine().Replay(committed[1], snapshot_reader=FakeAnalysis().snapshot)
    c = fresh_at(committed, media, 500, "DEBRIEF")
    assert again.snapshot(c) == service.snapshot(c, checkpoints=False)
    with importer[0].database.begin() as uow:
        assert (
            before
            == uow.connection.execute("SELECT payload FROM platform_records ORDER BY id").fetchall()
        )
    # Actual new Database owner with the persisted checkpoint, same authority services.
    from flowlens.storage.sqlite.database import Database

    db = importer[0].database
    db.close()
    reopened = Database(db.path)
    importer[0].database = reopened
    committed[1].database = reopened
    committed[2].database = reopened
    committed[2].sessions.database = reopened
    reopened.context_guard = committed[2].enforce
    try:
        assert again.snapshot(c) == cached.model_copy(update={"mode": "DEBRIEF", "as_of_ms": 500})
    finally:
        reopened.close()


def test_checkpoint_cannot_bypass_revoked_grant_or_source_rights(media, committed):
    service = engine().Replay(committed[1])
    c = fresh_at(committed, media, 500)
    service.snapshot(c)
    committed[2].revoke(committed[3].token.get_secret_value(), c.actor_id, c.session_id, "read")
    with pytest.raises(ContractError):
        service.snapshot(c)


def test_fake_snapshot_scope_and_future_rejected(media, committed):
    c = fresh_at(committed, media, 500)
    valid = FakeAnalysis().snapshot(c)
    for invalid in (
        valid.model_copy(update={"session_id": uuid4()}),
        valid.model_copy(update={"revision": 2}),
        valid.model_copy(update={"as_of_ms": 501}),
        valid.model_copy(update={"events": [event(c, 88, 900, 900)]}),
    ):
        with pytest.raises(ContractError):
            engine().Replay(
                committed[1], snapshot_reader=lambda _, invalid=invalid: invalid
            ).snapshot(c)


def test_corrupt_checkpoint_rebuilds_and_callback_sequence_race_denied(media, committed, importer):
    c = fresh_at(committed, media, 500)
    service = engine().Replay(committed[1])
    expected = service.snapshot(c)
    with importer[0].database.begin() as uow:
        uow.connection.execute("UPDATE platform_replay_snapshots SET payload='{}'")
        uow.commit()
    assert service.snapshot(c) == expected

    def racing(context):
        with importer[0].database.begin() as uow:
            uow.enqueue_event(context, event(context, 98, 100, 200))
            uow.commit()
        return FakeAnalysis().snapshot(context)

    with pytest.raises(ContractError, match="VERSION_CONFLICT"):
        engine().Replay(committed[1], snapshot_reader=racing).snapshot(c)


def test_track_snapshot_wire_is_stable_event_header_and_source_track_keeps_geometry():
    c = ctx()
    base = event(c, 1, 100, 200).model_dump()
    base.update(
        kind="TRACK",
        x_m=2.0,
        y_m=3.0,
        heading_deg=90.0,
        speed_mps=0.0,
        length_m=20.0,
        width_m=4.0,
        age_ms=9,
        layout_version="synthetic-1",
    )
    track = Track(**base)
    result = engine().reduce(c, [track], None, sequence=0)
    assert type(result.events[0]) is SourceEvent
    assert Snapshot.model_validate_json(result.model_dump_json()) == result
    assert track.x_m == 2.0


def test_host_composes_replay_from_committed_sources(tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings
    from flowlens.core.modules import ModuleRegistration

    module = ModuleRegistration(
        name="fake-analysis", mock=True, snapshot_reader=FakeAnalysis().snapshot
    )
    settings = HostSettings(
        profile="test",
        database_path=tmp_path / "db" / "host.db",
        import_staging_path=tmp_path / "staging",
        raw_assets_path=tmp_path / "raw",
        artifact_staging_path=tmp_path / "derivatives",
    )
    app = create_host(settings, modules=[module])
    with TestClient(app):
        assert app.state.replay is not None
        assert app.state.replay.snapshot_reader is not None
    assert app.state.replay is None


def test_cache_separates_reducer_versions_and_live_rights(media, committed, importer):
    c = fresh_at(committed, media, 500)
    a = engine().Replay(committed[1], reducer_version="synthetic-1")
    b = engine().Replay(committed[1], reducer_version="synthetic-2")
    assert a.snapshot(c) == b.snapshot(c)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_replay_snapshots").fetchone()[0]
            == 2
        )
    rights = media[4].declaration.rights.model_copy(update={"reviewer": "DENIED"})
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        c.session_id,
        media[3].source_id,
        rights,
        expected_version=1,
    )
    with pytest.raises(ContractError):
        a.snapshot(c)


def test_nested_fake_finding_future_evidence_denied():
    import json
    from pathlib import Path

    from flowlens.contracts.models import Finding

    c = ctx().model_copy(update={"analysis_run_id": uuid4()})
    data = json.loads(Path("contracts/examples/finding.json").read_text())
    data.update(
        session_id=str(c.session_id),
        analysis_run_id=str(c.analysis_run_id),
        revision=1,
        event_time_ms=100,
        available_time_ms=200,
    )
    for e in data["evidence"]:
        e.update(session_id=str(c.session_id), analysis_run_id=str(c.analysis_run_id), revision=1)
    finding = Finding.model_validate_json(json.dumps(data))
    analysis = (
        FakeAnalysis()
        .snapshot(c)
        .model_copy(update={"findings": [finding], "quality": "AMBIGUOUS"})
    )
    result = engine().reduce(c, [], analysis, sequence=0)
    assert result.findings == [finding] and result.quality == "AMBIGUOUS"
    bad = finding.model_copy(update={"available_time_ms": 301})
    with pytest.raises(ContractError):
        engine().reduce(c, [], analysis.model_copy(update={"findings": [bad]}), sequence=0)


def test_analysis_cannot_fabricate_source_events(media, committed):
    c = fresh_at(committed, media, 500)
    bad = FakeAnalysis().snapshot(c).model_copy(update={"events": [event(c, 88, 100, 200)]})
    with pytest.raises(ContractError):
        engine().Replay(committed[1], snapshot_reader=lambda _: bad).snapshot(c)
