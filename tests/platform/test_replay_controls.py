"""A07.2 real durable controls; no provider and immutable observations."""

import importlib
from uuid import uuid4

import pytest
from flowlens.core.errors import ContractError
from pydantic import SecretStr
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer


def controls(media, committed):
    module = importlib.import_module("flowlens.replay.controls")
    from flowlens.replay.snapshots import Replay

    token = committed[3].token.get_secret_value()
    c = media[2]
    committed[2].grant(
        token, c.actor_id, c.session_id, "review", role="controller", expires_ms=1000000
    )
    service = module.Controls(Replay(committed[1]))
    return service, token, c.session_id


def act(s, token, sid, action, version, key=None, view="LEADER", value=None):
    return s.command(
        token,
        sid,
        action,
        expected_version=version,
        key=key or str(uuid4()),
        view=view,
        value=value,
    )


def observer(committed, sid):
    sessions = committed[2].sessions
    admin = committed[3]
    accounts = sessions.accounts
    user = accounts.create(admin.account.id, "observer", SecretStr("synthetic-view-initial"))
    accounts.change_password(
        user.id, SecretStr("synthetic-view-initial"), SecretStr("synthetic-view-changed")
    )
    auth = sessions.login("observer", SecretStr("synthetic-view-changed"), "synthetic-view-peer")
    committed[2].grant(
        admin.token.get_secret_value(), user.id, sid, "read", role="observer", expires_ms=1000000
    )
    return auth.token.get_secret_value(), user.id


def test_play_pause_speed_seek_time_oracle(media, committed):
    s, token, sid = controls(media, committed)
    lead = act(s, token, sid, "LEAD", 0)
    assert lead.state.cursor_ms == 0 and lead.version == 1
    speed = act(s, token, sid, "SPEED", 1, value=2.0)
    playing = act(s, token, sid, "PLAY", speed.version)
    committed[4][0] += 1250
    assert s.get(token, sid).state.cursor_ms == 2500
    paused = act(s, token, sid, "PAUSE", playing.version)
    committed[4][0] += 300
    assert s.get(token, sid).state.cursor_ms == paused.state.cursor_ms == 2500
    seek = act(s, token, sid, "SEEK", paused.version, value=200)
    assert seek.state.cursor_ms == 200
    c = s.context(token, sid, mode="AS_KNOWN")
    assert c.as_of_ms == 200 and c.mode == "AS_KNOWN"
    assert [r.source_event_id for r in s.replay.snapshot(c).events] == ["instruction-1"]


def test_leader_conflict_follow_and_local_view_independent(media, committed):
    s, token, sid = controls(media, committed)
    lead = act(s, token, sid, "LEAD", 0)
    other, actor = observer(committed, sid)
    with pytest.raises(ContractError):
        act(s, other, sid, "SEEK", lead.version, value=200)
    local = act(s, other, sid, "SEEK", 0, view="LOCAL", value=500)
    shared = act(s, token, sid, "SEEK", lead.version, value=200)
    assert s.get(other, sid, view="LOCAL").state.cursor_ms == 500
    assert s.get(other, sid).state.cursor_ms == shared.state.cursor_ms == 200
    assert s.context(other, sid, view="LOCAL").as_of_ms == 500
    assert s.context(other, sid, view="FOLLOW").as_of_ms == 200
    assert local.state.view == "LOCAL" and local.state.leader_id is None
    assert local.state.session_id == sid and actor != lead.state.leader_id


def test_durable_idempotency_version_conflicts_and_atomic_audit(media, committed, importer):
    s, token, sid = controls(media, committed)
    with importer[0].database.begin() as uow:
        before_sequence = uow.connection.execute("SELECT COUNT(*) FROM platform_events").fetchone()[
            0
        ]
    lead = act(s, token, sid, "LEAD", 0, key="lead")
    assert act(s, token, sid, "LEAD", 0, key="lead") == lead
    seek = act(s, token, sid, "SEEK", 1, key="seek", value=200)
    assert act(s, token, sid, "SEEK", 1, key="seek", value=200) == seek
    with pytest.raises(ContractError, match="IDEMPOTENCY_CONFLICT"):
        act(s, token, sid, "SEEK", 1, key="seek", value=300)
    with pytest.raises(ContractError, match="VERSION_CONFLICT"):
        act(s, token, sid, "SEEK", 1, value=300)
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_control_receipts").fetchone()[0]
            == 2
        )
        assert (
            uow.connection.execute(
                "SELECT COUNT(*) FROM platform_audit WHERE action='REPLAY_CONTROL'"
            ).fetchone()[0]
            == 2
        )
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_events").fetchone()[0]
            == before_sequence + 2
        )


@pytest.mark.parametrize(
    "action,value",
    [
        ("SEEK", -1),
        ("SEEK", 40001),
        ("SPEED", 0.0),
        ("SPEED", float("inf")),
        ("SPEED", 17.0),
        ("SEEK", True),
        ("PAUSE", 1),
        ("CLEARANCE", None),
    ],
)
def test_invalid_controls_do_not_mutate(media, committed, action, value):
    s, token, sid = controls(media, committed)
    lead = act(s, token, sid, "LEAD", 0)
    with pytest.raises(ContractError):
        act(s, token, sid, action, lead.version, value=value)
    assert s.get(token, sid).version == lead.version


def test_step_uses_available_time_and_unknown_remains_unknown(media, committed):
    s, token, sid = controls(media, committed)
    act(s, token, sid, "LEAD", 0)
    assert (
        s.command(
            token, sid, "STEP", expected_version=1, key="step1", mode="AS_KNOWN"
        ).state.cursor_ms
        == 200
    )
    assert (
        s.command(
            token, sid, "STEP", expected_version=2, key="step2", mode="AS_KNOWN"
        ).state.cursor_ms
        == 40000
    )
    act(s, token, sid, "SEEK", 3, value=0)
    assert (
        s.command(
            token, sid, "STEP", expected_version=4, key="step3", mode="DEBRIEF"
        ).state.cursor_ms
        == 100
    )


def test_archive_and_recover_no_auto_resume_and_source_immutable(media, committed, importer):
    s, token, sid = controls(media, committed)
    with importer[0].database.begin() as uow:
        before = list(uow.connection.execute("SELECT payload FROM platform_records ORDER BY id"))
    act(s, token, sid, "LEAD", 0)
    act(s, token, sid, "SEEK", 1, value=200)
    act(s, token, sid, "PLAY", 2)
    committed[4][0] += 1000
    s.recover()
    assert s.get(token, sid).state.status == "PAUSED"
    assert s.get(token, sid).state.cursor_ms == 200
    version = s.get(token, sid).version
    archived = act(s, token, sid, "ARCHIVE", version)
    assert archived.archived and archived.state.status == "PAUSED"
    with pytest.raises(ContractError):
        act(s, token, sid, "PLAY", archived.version)
    local = act(s, token, sid, "SEEK", 0, view="LOCAL", value=500)
    assert local.state.cursor_ms == 500
    with importer[0].database.begin() as uow:
        assert before == list(
            uow.connection.execute("SELECT payload FROM platform_records ORDER BY id")
        )


def test_live_revoke_rejects_existing_controls_and_cross_session(media, committed):
    s, token, sid = controls(media, committed)
    lead = act(s, token, sid, "LEAD", 0)
    with pytest.raises(ContractError):
        s.get(token, uuid4())
    committed[2].revoke(token, media[2].actor_id, sid, "read")
    for call in (
        lambda: s.get(token, sid),
        lambda: act(s, token, sid, "PAUSE", lead.version),
        lambda: s.context(token, sid),
    ):
        with pytest.raises(ContractError):
            call()


def test_two_claimants_release_and_revoked_leader_takeover(media, committed):
    from concurrent.futures import ThreadPoolExecutor

    s, token, sid = controls(media, committed)
    other, actor = observer(committed, sid)
    committed[2].grant(token, actor, sid, "review", role="controller", expires_ms=1000000)

    def claim(t):
        try:
            return act(s, t, sid, "LEAD", 0)
        except ContractError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, [token, other]))
    winners = [r for r in results if not isinstance(r, str)]
    assert len(winners) == 1 and "VERSION_CONFLICT" in results
    winner = winners[0].state.leader_id
    winner_token, next_token = (token, other) if winner == media[2].actor_id else (other, token)
    committed[2].revoke(token, winner, sid, "review")
    takeover = act(s, next_token, sid, "LEAD", 1)
    assert takeover.state.leader_id != winner
    released = act(s, next_token, sid, "RELEASE", takeover.version)
    assert released.state.leader_id is None and released.state.status == "PAUSED"


def test_control_atomic_fault_no_effect_and_receipts_immutable(
    media, committed, importer, monkeypatch
):
    import sqlite3

    from flowlens.storage.sqlite.database import UnitOfWork

    s, token, sid = controls(media, committed)
    lead = act(s, token, sid, "LEAD", 0)
    original = UnitOfWork.audit

    def failure(*args):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(UnitOfWork, "audit", failure)
    with pytest.raises(RuntimeError):
        act(s, token, sid, "SEEK", 1, value=200, key="fault")
    monkeypatch.setattr(UnitOfWork, "audit", original)
    assert s.get(token, sid).version == lead.version
    assert s.get(token, sid).state.cursor_ms == 0
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_control_receipts").fetchone()[0]
            == 1
        )
        for sql in (
            "UPDATE platform_control_receipts SET version=999",
            "DELETE FROM platform_control_receipts",
        ):
            with pytest.raises(sqlite3.DatabaseError):
                uow.connection.execute(sql)
    assert act(s, token, sid, "SEEK", 1, value=200, key="fault").state.cursor_ms == 200


def test_recovery_persists_pause_across_real_owner_restart_and_no_provider(
    media, committed, importer
):
    from flowlens.storage.sqlite.database import Database

    s, token, sid = controls(media, committed)

    def forbidden(_):
        pytest.fail("Control or seek called B/provider snapshot")

    s.replay.snapshot_reader = forbidden
    act(s, token, sid, "LEAD", 0)
    act(s, token, sid, "SEEK", 1, value=200)
    act(s, token, sid, "PLAY", 2)
    db = importer[0].database
    db.close()
    reopened = Database(db.path)
    importer[0].database = reopened
    committed[1].database = reopened
    committed[2].database = reopened
    committed[2].sessions.database = reopened
    reopened.context_guard = committed[2].enforce
    s.database = reopened
    try:
        committed[4][0] += 9000
        s.recover()
        assert s.get(token, sid).state.cursor_ms == 200
        assert s.get(token, sid).state.status == "PAUSED"
        assert s.get(token, sid).version == 4
        assert act(s, token, sid, "SEEK", 4, value=500).state.cursor_ms == 500
    finally:
        reopened.close()


def test_host_controls_startup_recovery_and_cleanup(tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    settings = HostSettings(
        profile="test",
        database_path=tmp_path / "db" / "host.db",
        import_staging_path=tmp_path / "staging",
        raw_assets_path=tmp_path / "raw",
        artifact_staging_path=tmp_path / "derivatives",
    )
    app = create_host(settings)
    with TestClient(app):
        assert app.state.controls is not None
        assert app.state.legacy_history is not None
    assert app.state.controls is None and app.state.legacy_history is None


def test_revoked_leader_freezes_playback_for_followers(media, committed):
    s, token, sid = controls(media, committed)
    act(s, token, sid, "LEAD", 0)
    act(s, token, sid, "PLAY", 1)
    committed[4][0] += 100
    committed[2].revoke(token, media[2].actor_id, sid, "review")
    frozen = s.get(token, sid)
    assert frozen.state.status == "PAUSED" and frozen.state.leader_id is None
    committed[4][0] += 1000
    assert s.get(token, sid).state.cursor_ms == frozen.state.cursor_ms


def test_observer_cannot_label_self_as_leader_or_use_legacy_casing(media, committed):
    from flowlens.contracts.models import PlaybackState
    from pydantic import ValidationError

    s, token, sid = controls(media, committed)
    lead = act(s, token, sid, "LEAD", 0)
    other, _ = observer(committed, sid)
    with pytest.raises(ContractError):
        s.get(other, sid, view="LEADER")
    with pytest.raises(ContractError):
        s.context(other, sid, view="LEADER")
    payload = lead.state.model_dump()
    payload["simMs"] = payload.pop("cursor_ms")
    with pytest.raises(ValidationError):
        PlaybackState.model_validate(payload)
