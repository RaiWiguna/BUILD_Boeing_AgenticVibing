"""A07.3 real A REST/ASGI WebSocket tests, frozen fake B, disposable source/SQLite."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.contracts.models import StreamEvent
from flowlens.core.host_config import HostSettings
from flowlens.testing.harness import FakeAnalysis
from starlette.websockets import WebSocketDisconnect
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer

ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def wire(media, committed, importer):
    from flowlens.replay.controls import Controls
    from flowlens.replay.snapshots import Replay

    app = create_host(HostSettings(profile="test"))
    app.state.sessions = committed[2].sessions
    app.state.permissions = committed[2]
    app.state.transactions = importer[0].database
    app.state.sources = committed[1]
    app.state.replay = Replay(committed[1], snapshot_reader=FakeAnalysis().snapshot)
    app.state.controls = Controls(app.state.replay)
    token = committed[3].token.get_secret_value()
    sid = media[2].session_id
    app.state.controls.command(
        token, sid, "SEEK", view="LOCAL", value=500, key="local", expected_version=0
    )
    with TestClient(app, base_url=ORIGIN) as client:
        client.cookies.set("flowlens_session", token)
        yield app, client, sid, token, {"Origin": ORIGIN, "X-CSRF-Token": committed[3].csrf_token}


def test_catalogue_sources_snapshot_and_safe_metadata(wire, media):
    app, client, sid, _, headers = wire
    listing = client.get("/api/v1/sessions")
    assert listing.status_code == 200
    assert [s["session_id"] for s in listing.json()["items"]] == [str(sid)]
    sources = client.get(f"/api/v1/sessions/{sid}/sources")
    assert sources.status_code == 200 and len(sources.json()["items"]) == 1
    source_id = media[3].source_id
    item = client.get(f"/api/v1/sessions/{sid}/sources/{source_id}")
    assert item.status_code == 200 and item.json()["id"] == str(source_id)
    snapshot = client.get(f"/api/v1/sessions/{sid}/snapshot?view=LOCAL&mode=AS_KNOWN")
    assert snapshot.status_code == 200 and len(snapshot.json()["events"]) == 1
    assert snapshot.json()["as_of_ms"] == 500
    assert item.headers["Cache-Control"] == "no-store"
    assert str(app.state.sources.files.root) not in item.text
    assert all(k not in snapshot.text for k in ("private", "truth", "seed"))


def test_same_time_pages_no_duplicate_skip_or_future(wire, committed, importer, media):
    from test_replay_snapshots import event

    app, client, sid, _, _ = wire
    c = media[2]
    original = committed[1].read_events(c)[0]
    with importer[0].database.begin() as uow:
        for number in (88, 89):
            e = event(c, number, 100, 200).model_copy(
                update={"source_id": original.source_id, "source_hash": original.source_hash}
            )
            uow.connection.execute(
                "INSERT INTO platform_records VALUES ('source_events',?,?,NULL,1,'SourceEvent',?)",
                (str(e.id), str(sid), e.model_dump_json()),
            )
        uow.commit()
    params = {"view": "LOCAL", "mode": "DEBRIEF", "limit": 1}
    all_rows = []
    pages = []
    for _ in range(8):
        response = client.get(f"/api/v1/sessions/{sid}/history", params=params)
        assert response.status_code == 200
        pages.append(response.json())
        all_rows.extend(response.json()["items"])
        cursor = response.json()["next_cursor"]
        if not cursor:
            break
        params["cursor"] = cursor
    assert len(all_rows) == len({r["id"] for r in all_rows}) == 5
    assert [(r["event_time_ms"], r["id"]) for r in all_rows] == sorted(
        (r["event_time_ms"], r["id"]) for r in all_rows
    )
    assert sum(r["event_time_ms"] == 100 for r in all_rows) == 3
    assert client.get(
        f"/api/v1/sessions/{sid}/history", params={"view": "LOCAL", "mode": "AS_KNOWN"}
    ).json()["items"] == [
        r for r in all_rows if r["available_time_ms"] is not None and r["available_time_ms"] <= 500
    ]
    retry = client.get(
        f"/api/v1/sessions/{sid}/history",
        params={"view": "LOCAL", "mode": "DEBRIEF", "limit": 1, "cursor": pages[0]["next_cursor"]},
    )
    assert retry.json() == pages[1]


def test_cursor_scope_and_changed_view_denial(wire):
    app, client, sid, token, _ = wire
    prefix = f"/api/v1/sessions/{sid}/history"
    first = client.get(prefix, params={"view": "LOCAL", "limit": 1}).json()
    assert first["next_cursor"]
    cursor = first["next_cursor"]
    assert (
        client.get(
            prefix, params={"view": "LOCAL", "mode": "AS_KNOWN", "cursor": cursor}
        ).status_code
        == 409
    )
    assert (
        client.get(prefix, params={"view": "LOCAL", "cursor": "invalid-private-path"}).status_code
        == 422
    )
    app.state.controls.command(
        token, sid, "SEEK", view="LOCAL", value=200, expected_version=1, key="seek"
    )
    assert client.get(prefix, params={"view": "LOCAL", "cursor": cursor}).status_code == 409
    assert (
        client.get(f"/api/v1/sessions/{uuid4()}/history", params={"cursor": cursor}).status_code
        == 403
    )


def test_http_control_body_csrf_conflicts_and_no_ai_command(wire):
    app, client, sid, _, headers = wire
    path = f"/api/v1/sessions/{sid}/playback"
    data = {"action": "SEEK", "view": "LOCAL", "value": 200, "expected_version": 1, "key": "seek"}
    assert client.post(path, json=data).status_code == 403
    response = client.post(path, json=data, headers=headers)
    assert response.status_code == 200 and response.json()["state"]["cursor_ms"] == 200
    assert client.post(path, json=data, headers=headers).json() == response.json()
    assert client.post(path, json={**data, "value": 300}, headers=headers).status_code == 409
    assert client.post(path, json={**data, "role": "admin"}, headers=headers).status_code == 422
    assert (
        client.post(path, json={**data, "action": "CLEARANCE"}, headers=headers).status_code == 422
    )
    assert (
        client.post(
            path, content=b"x" * 8192, headers={**headers, "Content-Type": "application/json"}
        ).status_code
        == 422
    )
    assert client.get(path, params={"view": "LOCAL"}).json()["state"]["cursor_ms"] == 200


@pytest.mark.parametrize("route", ["snapshot", "history", "sources", "playback"])
def test_rest_cross_scope_origin_and_grant_denial(wire, committed, route):
    app, client, sid, token, _ = wire
    path = f"/api/v1/sessions/{sid}/{route}"
    assert client.get(path, headers={"Origin": "https://foreign.example"}).status_code == 403
    assert client.get(f"/api/v1/sessions/{uuid4()}/{route}").status_code == 403
    committed[2].revoke(token, committed[3].account.id, sid, "read")
    assert client.get(path).status_code == 403
    assert client.get("/api/v1/sessions").json()["items"] == []


def connect(client, sid, **params):
    from urllib.parse import urlencode

    return client.websocket_connect(
        f"/api/v1/sessions/{sid}/stream?" + urlencode({"view": "LOCAL", **params}),
        headers={"Origin": ORIGIN},
    )


def message(ws):
    raw = ws.receive_json()
    return StreamEvent.model_validate_json(__import__("json").dumps(raw))


def test_ws_snapshot_reconnect_resync_retry_no_duplicate_state(wire):
    app, client, sid, _, _ = wire
    with connect(client, sid) as ws:
        first = message(ws)
        assert first.type == "SNAPSHOT" and len(first.payload.events) == 3
        sequence = first.payload.sequence
        ws.send_json({"type": "RESYNC", "after_sequence": sequence})
        retry = message(ws)
        assert retry.type == "SNAPSHOT" and retry.payload == first.payload
    with connect(client, sid, after_sequence=sequence) as ws:
        assert message(ws).payload == first.payload
    with connect(client, sid, after_sequence=sequence + 10) as ws:
        gap = message(ws)
        assert gap.type == "RESYNC_REQUIRED" and gap.payload.snapshot_sequence == sequence
        rebuilt = message(ws)
        assert rebuilt.type == "SNAPSHOT" and rebuilt.payload == first.payload


@pytest.mark.parametrize("cause", ["grant_revoke", "grant_expiry", "logout", "rights", "reset"])
def test_idle_ws_access_loss_disconnects_without_client_message(wire, committed, cause, media):
    app, client, sid, token, _ = wire
    with connect(client, sid) as ws:
        assert message(ws).type == "SNAPSHOT"
        if cause == "grant_revoke":
            committed[2].revoke(token, committed[3].account.id, sid, "read")
        elif cause == "grant_expiry":
            committed[4][0] += 1000001
        elif cause == "logout":
            committed[2].sessions.logout(token)
        elif cause == "reset":
            from pydantic import SecretStr

            app.state.sessions.accounts.reset_password(
                committed[3].account.id, committed[3].account.id, SecretStr("synthetic-new-reset")
            )
        else:
            rights = media[4].declaration.rights.model_copy(update={"reviewer": "DENIED"})
            committed[1].set_rights(token, sid, media[3].source_id, rights, expected_version=1)
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 1008 and closed.value.reason == ""


def test_ws_cross_session_origin_and_untrusted_messages_denied(wire):
    _, client, sid, _, _ = wire
    for other, origin in ((uuid4(), ORIGIN), (sid, "https://foreign.example")):
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect(
                f"/api/v1/sessions/{other}/stream", headers={"Origin": origin}
            ):
                pass
        assert closed.value.code == 1008
    for payload in (
        {"type": "RESYNC", "after_sequence": 0, "context": {"role": "admin"}},
        {"type": "SEEK", "cursor_ms": 40000},
        {"type": "RESYNC", "after_sequence": True},
    ):
        with connect(client, sid) as ws:
            message(ws)
            ws.send_json(payload)
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1008


def test_ws_publication_gap_snapshot_stays_unique(wire, committed):
    app, client, sid, token, _ = wire
    committed[2].grant(
        token, committed[3].account.id, sid, "review", role="controller", expires_ms=1000000
    )
    with connect(client, sid) as ws:
        before = message(ws)
        app.state.controls.command(token, sid, "LEAD", expected_version=0, key="claim")
        app.state.controls.command(
            token, sid, "SEEK", value=200, expected_version=1, key="shared-seek"
        )
        # LOCAL view remains500 while shared control advances the durable session sequence.
        messages = [message(ws), message(ws)]
        assert [m.type for m in messages] == ["RESYNC_REQUIRED", "SNAPSHOT"]
        after = messages[-1].payload
        assert after.sequence == before.payload.sequence + 2
        assert after.as_of_ms == 500
        assert after.events == before.payload.events
        assert len({e.id for e in after.events}) == len(after.events)


def test_zero_cursor_context_proof_is_unique_and_authoritative(wire):
    app, client, sid, token, _ = wire
    from flowlens.auth.permissions import context_digest

    for view in ("FOLLOW", "LOCAL"):
        if view == "LOCAL":
            app.state.controls.command(
                token, sid, "SEEK", value=0, view="LOCAL", key="zero", expected_version=1
            )
        c = app.state.controls.context(token, sid, view=view)
        assert c.as_of_ms == 0
        with app.state.transactions.begin() as uow:
            app.state.permissions.enforce(uow, c)
            assert (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_context_receipts WHERE digest=?",
                    (context_digest(c),),
                ).fetchone()[0]
                == 1
            )
        response = client.get(f"/api/v1/sessions/{sid}/snapshot", params={"view": view})
        assert response.status_code == 200 and response.json()["events"] == []


def test_follow_stream_delivers_typed_playback_then_authoritative_snapshot(wire, committed):
    app, client, sid, token, _ = wire
    committed[2].grant(
        token, committed[3].account.id, sid, "review", role="controller", expires_ms=1000000
    )
    with connect(client, sid, view="FOLLOW") as ws:
        before = message(ws)
        app.state.controls.command(token, sid, "LEAD", expected_version=0, key="leader")
        typed = message(ws)
        assert typed.type == "PLAYBACK_CHANGED" and typed.sequence == before.sequence + 1
        assert typed.payload.view == "FOLLOW" and typed.payload.leader_id == committed[3].account.id
        assert message(ws).type == "SNAPSHOT"


def test_unknown_or_future_publication_resync_does_not_leak_payload(wire, importer):
    import json

    app, client, sid, _, _ = wire
    with connect(client, sid) as ws:
        first = message(ws)
        with importer[0].database.begin() as uow:
            uow.connection.execute(
                "INSERT INTO platform_events VALUES (?,?,NULL,1,?)",
                (
                    str(sid),
                    first.sequence + 1,
                    json.dumps({"private_schedule": "must stay hidden", "session_id": str(sid)}),
                ),
            )
            uow.commit()
        gap = message(ws)
        assert gap.type == "RESYNC_REQUIRED" and "must stay hidden" not in gap.model_dump_json()
        snap = message(ws)
        assert snap.type == "SNAPSHOT" and "private_schedule" not in snap.model_dump_json()


def test_ws_binary_oversized_and_duplicate_json_messages_close_safely(wire):
    _, client, sid, _, _ = wire
    for value in (b"binary", "x" * 1025, '{"type":"RESYNC","type":"RESYNC","after_sequence":0}'):
        with connect(client, sid) as ws:
            message(ws)
            ws.send_bytes(value) if isinstance(value, bytes) else ws.send_text(value)
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1008 and closed.value.reason == ""


@pytest.mark.parametrize("termination", ["revoke", "oversize"])
def test_real_loopback_http_websocket_resync_and_idle_revocation(wire, committed, termination):
    import asyncio
    import json
    import socket
    import threading
    import time

    import httpx
    import uvicorn
    from wsproto import ConnectionType, WSConnection, events

    app, _, sid, token, _ = wire
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    previous_settings = app.state.settings
    app.state.settings = HostSettings(profile="test", port=port)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            ws="wsproto",
            log_config=None,
            access_log=False,
            proxy_headers=False,
            timeout_graceful_shutdown=2,
            ws_max_size=1024,
        )
    )
    task = threading.Thread(
        target=lambda: asyncio.run(server.serve(sockets=[listener])), daemon=True
    )
    task.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and task.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        with httpx.Client(base_url=origin, headers={"Cookie": f"flowlens_session={token}"}) as http:
            response = http.get(
                f"/api/v1/sessions/{sid}/snapshot", params={"view": "LOCAL", "mode": "AS_KNOWN"}
            )
            assert response.status_code == 200 and len(response.json()["events"]) == 1
        with socket.create_connection(("127.0.0.1", port), timeout=3) as sock:
            sock.settimeout(3)
            ws = WSConnection(ConnectionType.CLIENT)
            sock.sendall(
                ws.send(
                    events.Request(
                        host=f"127.0.0.1:{port}",
                        target=f"/api/v1/sessions/{sid}/stream?view=LOCAL",
                        extra_headers=[
                            (b"origin", origin.encode()),
                            (b"cookie", f"flowlens_session={token}".encode()),
                        ],
                    )
                )
            )
            text = ""

            def receive():
                nonlocal text
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    for e in ws.events():
                        if isinstance(e, events.CloseConnection):
                            return e
                        if isinstance(e, events.TextMessage):
                            text += e.data
                            if e.message_finished:
                                result = json.loads(text)
                                text = ""
                                return result
                    data = sock.recv(65536)
                    assert data
                    ws.receive_data(data)
                pytest.fail("Native WebSocket event deadline exceeded")

            first = receive()
            assert first["type"] == "SNAPSHOT"
            sock.sendall(
                ws.send(
                    events.TextMessage(
                        data=json.dumps(
                            {"type": "RESYNC", "after_sequence": first["payload"]["sequence"]}
                        )
                    )
                )
            )
            assert receive()["payload"] == first["payload"]
            if termination == "revoke":
                committed[2].revoke(token, committed[3].account.id, sid, "read")
            else:
                sock.sendall(ws.send(events.TextMessage(data="private-text" * 150)))
            close = receive()
            assert isinstance(close, events.CloseConnection)
            assert close.code == (1008 if termination == "revoke" else 1009)
            assert "private-text" not in close.reason
    finally:
        server.should_exit = True
        task.join(timeout=5)
        listener.close()
        app.state.settings = previous_settings
        assert not task.is_alive()


def test_actual_launcher_configures_bounded_native_ws_protocol(monkeypatch):
    from flowlens.api import serve

    observed = {}
    monkeypatch.setattr(serve.uvicorn, "run", lambda app, **kwargs: observed.update(kwargs))
    monkeypatch.setattr(serve, "environ", {})
    serve.main()
    assert observed["ws"] == "wsproto" and observed["ws_max_size"] == 1024


def test_catalogue_and_source_pages_are_grant_scoped_and_stable(wire, media, importer):
    app, client, sid, token, _ = wire
    # A second actual independent source import, not a fabricated catalogue placeholder.
    from flowlens.imports.commit import ImportCommit
    from test_import_commit import commit, context

    real_commits = ImportCommit(importer[0], app.state.sources.files)
    c = (real_commits, app.state.sources, app.state.permissions, importer[1], importer[2])
    from pathlib import Path

    from test_import_metadata import prepare, request
    from test_imports import stage, upload

    preview = stage(
        importer,
        [upload(Path("tests/fixtures/audio/silence.wav").read_bytes(), filename="silence.wav")],
        key="second-stage",
    )
    prepared = prepare(
        importer,
        preview,
        request(preview, modify=lambda d: d.update(source_identifier="laboratory-session-2")),
    )
    result = commit(c, preview, prepared, key="second-session")
    context(c, result)
    first = client.get("/api/v1/sessions", params={"limit": 1}).json()
    second = client.get(
        "/api/v1/sessions", params={"limit": 1, "cursor": first["next_cursor"]}
    ).json()
    assert len(first["items"]) == len(second["items"]) == 1
    assert {first["items"][0]["session_id"], second["items"][0]["session_id"]} == {
        str(sid),
        str(result.session_id),
    }
    assert second["next_cursor"] is None
    # The committed import model is one immutable source package per session;
    # channels/files live inside its manifest. Do not fabricate an invalid second package.
    page = client.get(f"/api/v1/sessions/{sid}/sources", params={"limit": 1}).json()
    assert [item["id"] for item in page["items"]] == [str(media[3].source_id)]
    assert page["next_cursor"] is None
    history_cursor = client.get(
        f"/api/v1/sessions/{sid}/history", params={"view": "LOCAL", "limit": 1}
    ).json()["next_cursor"]
    assert (
        client.get(f"/api/v1/sessions/{sid}/sources", params={"cursor": history_cursor}).status_code
        == 409
    )
    for limit in (0, 101):
        assert (
            client.get(f"/api/v1/sessions/{sid}/sources", params={"limit": limit}).status_code
            == 422
        )
    app.state.permissions.revoke(token, media[2].actor_id, result.session_id, "read")
    assert [item["session_id"] for item in client.get("/api/v1/sessions").json()["items"]] == [
        str(sid)
    ]


def test_selected_run_scope_and_future_fake_b_denial(wire, importer):
    app, client, sid, _, _ = wire
    run = uuid4()
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_runs(session_id,id,revision) VALUES (?,?,1)", (str(sid), str(run))
        )
        uow.commit()
    path = f"/api/v1/sessions/{sid}/snapshot"
    assert client.get(path, params={"view": "LOCAL", "run_id": run}).json()[
        "analysis_run_id"
    ] == str(run)
    assert client.get(path, params={"run_id": uuid4()}).status_code == 403
    with connect(client, sid, run_id=str(run)) as ws:
        value = message(ws)
        assert value.analysis_run_id == run and value.payload.analysis_run_id == run
    from test_replay_snapshots import event

    def invalid(c):
        return (
            FakeAnalysis().snapshot(c).model_copy(update={"events": [event(c, 999, 100, 100000)]})
        )

    app.state.replay.snapshot_reader = invalid
    assert client.get(path, params={"view": "LOCAL", "mode": "AS_KNOWN"}).status_code == 403
    with pytest.raises(WebSocketDisconnect) as closed:
        with connect(client, sid, mode="AS_KNOWN"):
            pass
    assert closed.value.code == 1008


def test_revoke_between_snapshot_and_publication_never_emits(wire, committed):
    app, client, sid, token, _ = wire
    original = app.state.replay.snapshot

    def racing(c):
        result = original(c)
        committed[2].revoke(token, c.actor_id, sid, "read")
        return result

    app.state.replay.snapshot = racing
    with pytest.raises(WebSocketDisconnect) as closed:
        with connect(client, sid) as ws:
            ws.receive_json()
    assert closed.value.code == 1008


def test_transient_publication_race_retries_snapshot_and_busy_is_retryable(wire):
    from flowlens.core.errors import ContractError

    app, client, sid, _, _ = wire
    original = app.state.replay.snapshot
    seen = []

    def once(c):
        seen.append(c)
        if len(seen) == 1:
            raise ContractError("VERSION_CONFLICT")
        return original(c)

    app.state.replay.snapshot = once
    with connect(client, sid) as ws:
        assert message(ws).type == "SNAPSHOT"
    assert len(seen) == 2
    seen.clear()

    def busy(c):
        seen.append(c)
        raise ContractError("VERSION_CONFLICT")

    app.state.replay.snapshot = busy
    with pytest.raises(WebSocketDisconnect) as closed:
        with connect(client, sid):
            pass
    assert closed.value.code == 1013 and len(seen) == 3


def test_replay_http_openapi_uses_frozen_public_dtos(wire):
    _, client, _, _, _ = wire
    schema = client.get("/openapi.json").json()
    for path, model in (
        ("/api/v1/sessions/{session_id}/snapshot", "Snapshot"),
        ("/api/v1/sessions/{session_id}/sources/{source_id}", "SourceManifest"),
    ):
        response = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        assert response["$ref"].endswith("/" + model)
    body = schema["paths"]["/api/v1/sessions/{session_id}/playback"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert body["additionalProperties"] is False and "context" not in body["properties"]


def test_stream_connection_limit_and_slot_release(wire):
    from contextlib import ExitStack

    _, client, sid, _, _ = wire
    with ExitStack() as stack:
        for _ in range(4):
            ws = stack.enter_context(connect(client, sid))
            assert message(ws).type == "SNAPSHOT"
        with pytest.raises(WebSocketDisconnect) as denied:
            with connect(client, sid):
                pass
        assert denied.value.code == 1008
    with connect(client, sid) as ws:
        assert message(ws).type == "SNAPSHOT"


def test_legacy_http_alias_and_canonical_history_metadata(wire, tmp_path):
    from uuid import uuid5

    from flowlens.replay.compatibility import LegacyHistory
    from flowlens.storage.sqlite.legacy import NAMESPACE, import_archive
    from test_legacy import archive

    app, client, _, token, _ = wire
    import_archive(archive(tmp_path / "archive.db"), app.state.transactions)
    sid = uuid5(NAMESPACE, "abcdef123456")
    app.state.legacy_history = LegacyHistory(app.state.permissions)
    app.state.permissions.grant(
        token,
        app.state.sessions.resolve(token).account.id,
        sid,
        "read",
        role="observer",
        expires_ms=10000,
    )
    alias = client.get("/api/v1/legacy/sessions/abcdef123456/history")
    canonical = client.get(f"/api/v1/sessions/{sid}/legacy-history")
    assert alias.status_code == canonical.status_code == 200 and alias.json() == canonical.json()
    assert (
        alias.json()["available_time_ms"] is None
        and alias.json()["source_status"] == "NOT_EVALUABLE"
    )
    assert "seed" not in alias.text and "private" not in alias.text
    assert (
        client.get("/api/v1/legacy/sessions/abcdef123456/history?mode=AS_KNOWN").status_code == 422
    )
    assert client.get("/api/v1/legacy/sessions/fedcba654321/history").status_code == 403
