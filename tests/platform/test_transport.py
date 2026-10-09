"""A03.2 host policies on disposable SQLite and synthetic principals."""

import json
from uuid import UUID, uuid4

import pytest
from fastapi import APIRouter, Request, WebSocket
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import ModuleRegistration
from pydantic import SecretStr
from starlette.websockets import WebSocketDisconnect

ORIGIN = "http://127.0.0.1:8000"
PASSWORD = "synthetic-transport-password"


@pytest.fixture
def transport(tmp_path):
    touched = []
    router = APIRouter()

    @router.api_route("/api/v1/probe", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def probe():
        touched.append("probe")
        return {"ok": True}

    @router.api_route("/api/v1/sessions/{session_id}/probe", methods=["GET", "POST"])
    def scoped(request: Request, session_id: UUID, run_id: UUID | None = None):
        from flowlens.auth.transport import http_context

        ctx = http_context(
            request,
            session_id,
            run_id=run_id,
            required="review" if request.method == "POST" else "read",
        )
        touched.append(ctx)
        return {"actor": str(ctx.actor_id), "mode": ctx.mode, "as_of_ms": ctx.as_of_ms}

    @router.get("/internal/probe")
    def worker_probe(request: Request):
        touched.append("worker")
        return {"actor": str(request.state.principal_id)}

    @router.get("/internal/scopes/{scope_id}")
    def worker_scope(request: Request, scope_id: UUID):
        from flowlens.auth.transport import worker_context

        ctx = worker_context(request, scope_id)
        touched.append(ctx)
        return {"actor": str(ctx.actor_id), "session": str(ctx.session_id)}

    @router.websocket("/api/v1/sessions/{session_id}/transport-probe")
    async def stream(websocket: WebSocket, session_id: UUID):
        from flowlens.auth.transport import websocket_context

        ctx = await websocket_context(websocket, session_id)
        await websocket.accept()
        touched.append(ctx)
        await websocket.send_json({"actor": str(ctx.actor_id)})
        # Policy recheck probe; durable replay/stream lifecycle remains A07.3.
        await websocket.receive_text()
        ctx = await websocket_context(websocket, session_id)
        await websocket.send_json({"actor": str(ctx.actor_id)})
        await websocket.close()

    @router.websocket("/api/v1/errors/{kind}")
    async def ws_error(websocket: WebSocket, kind: str):
        from fastapi import HTTPException
        from flowlens.core.errors import ContractError

        if kind == "http":
            raise HTTPException(403, detail="private-password /private/audio.wav")
        if kind == "contract":
            raise ContractError("ACCESS_DENIED")
        raise RuntimeError("private-password SELECT /private/audio.wav")

    app = create_host(
        HostSettings(profile="test", database_path=tmp_path / "transport.db"),
        modules=(ModuleRegistration("transport-probes", mock=True, routes=(router,)),),
    )
    with TestClient(app, base_url=ORIGIN) as client:
        now = [1000]
        app.state.sessions.clock = lambda: now[0]
        account = app.state.accounts.bootstrap("admin", SecretStr(PASSWORD))
        app.state.accounts.change_password(
            account.id, SecretStr(PASSWORD), SecretStr(PASSWORD + "2")
        )
        auth = app.state.sessions.login("admin", SecretStr(PASSWORD + "2"), "local")
        sid, other, run = uuid4(), uuid4(), uuid4()
        with app.state.transactions.begin() as uow:
            for identifier in (sid, other):
                uow.connection.execute(
                    "INSERT INTO platform_sessions VALUES (?)", (str(identifier),)
                )
                uow.connection.execute(
                    "INSERT INTO platform_revisions VALUES (?,1,?)", (str(identifier), "a" * 64)
                )
                uow.connection.execute(
                    "INSERT INTO platform_context_state VALUES (?,500,'AS_KNOWN')",
                    (str(identifier),),
                )
            uow.connection.execute("INSERT INTO platform_runs VALUES (?,?,1)", (str(sid), str(run)))
            uow.commit()
        for capability in ("read", "review", "analysis"):
            app.state.permissions.grant(
                auth.token.get_secret_value(),
                account.id,
                sid,
                capability,
                role="evaluator",
                expires_ms=10000,
            )
        yield app, client, auth, sid, other, run, now, touched


def browser_login(t):
    _, client, auth, *_ = t
    client.cookies.set("flowlens_session", auth.token.get_secret_value())
    return {"Origin": ORIGIN, "X-CSRF-Token": auth.csrf_token}


def test_registered_http_route_cannot_skip_principal_guard(transport):
    _, client, _, _, _, _, _, touched = transport
    response = client.get("/api/v1/probe")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"
    assert touched == []
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("bad", ["csrf", "origin", "missing_origin", "cross_site"])
def test_generic_mutation_denial_has_no_effect(transport, method, bad):
    _, client, _, _, _, _, _, touched = transport
    headers = browser_login(transport)
    if bad == "csrf":
        headers["X-CSRF-Token"] = "0" * 64
    elif bad == "origin":
        headers["Origin"] = "https://attacker.example"
    elif bad == "missing_origin":
        del headers["Origin"]
    else:
        headers["Sec-Fetch-Site"] = "cross-site"
    response = client.request(method, "/api/v1/probe", headers=headers)
    assert response.status_code == 403
    assert touched == []


def test_generic_mutation_and_safe_read_succeed_with_live_cookie(transport):
    _, client, *_ = transport
    headers = browser_login(transport)
    assert client.get("/api/v1/probe").status_code == 200
    assert client.post("/api/v1/probe", headers=headers).status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "null"},
        {"Origin": "https://attacker.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"Authorization": "Bearer synthetic-secret"},
    ],
)
def test_browser_reads_reject_foreign_origin_and_bearer(transport, headers):
    _, client, *_ = transport
    browser_login(transport)
    assert client.get("/api/v1/probe", headers=headers).status_code == 403
    assert client.get("/api/v1/auth/session", headers=headers).status_code == 403


@pytest.mark.parametrize(
    "query", ["token=synthetic-secret", "access_token=synthetic-secret", "context={}"]
)
def test_browser_does_not_accept_query_credentials_or_context(transport, query):
    _, client, _, _, _, _, _, touched = transport
    browser_login(transport)
    assert client.get("/api/v1/probe?" + query).status_code == 403
    assert touched == []


def test_http_context_uses_server_scope_and_requires_capability(transport):
    app, client, auth, sid, other, _, _, touched = transport
    headers = browser_login(transport)
    path = f"/api/v1/sessions/{sid}/probe"
    response = client.get(path)
    assert response.json() == {"actor": str(auth.account.id), "mode": "AS_KNOWN", "as_of_ms": 500}
    assert client.get(f"/api/v1/sessions/{other}/probe").status_code == 403
    app.state.permissions.revoke(auth.token.get_secret_value(), auth.account.id, sid, "review")
    assert client.post(path, headers=headers).status_code == 403
    assert len(touched) == 1


def test_worker_only_route_rejects_browser_and_human_bearer(transport):
    app, client, auth, *_ = transport
    assert client.get("/internal/probe").status_code == 401
    browser_login(transport)
    assert client.get("/internal/probe").status_code == 403
    client.cookies.clear()
    assert (
        client.get(
            "/internal/probe", headers={"Authorization": "Bearer " + auth.token.get_secret_value()}
        ).status_code
        == 401
    )
    credential = app.state.permissions.provision_worker(
        auth.token.get_secret_value(), expires_ms=10000
    )
    headers = {"Authorization": "Bearer " + credential.token.get_secret_value()}
    assert client.get("/internal/probe", headers=headers).json() == {"actor": str(credential.id)}
    assert client.get("/api/v1/probe", headers=headers).status_code == 403
    for browser_header in ("Origin", "Sec-Fetch-Site", "X-CSRF-Token"):
        assert (
            client.get("/internal/probe", headers={**headers, browser_header: ORIGIN}).status_code
            == 403
        )
    app.state.permissions.revoke_worker(auth.token.get_secret_value(), credential.id)
    assert client.get("/internal/probe", headers=headers).status_code == 401


def test_worker_http_context_rechecks_bound_scope(transport):
    app, client, auth, sid, _, run, _, touched = transport
    credential = app.state.permissions.provision_worker(
        auth.token.get_secret_value(), expires_ms=10000
    )
    scope = app.state.permissions.bind_worker(
        auth.token.get_secret_value(), credential.id, sid, run, expires_ms=9000
    )
    headers = {"Authorization": "Bearer " + credential.token.get_secret_value()}
    assert client.get(f"/internal/scopes/{scope}", headers=headers).json()["session"] == str(sid)
    assert client.get(f"/internal/scopes/{uuid4()}", headers=headers).status_code == 401
    app.state.permissions.revoke_scope(auth.token.get_secret_value(), scope)
    assert client.get(f"/internal/scopes/{scope}", headers=headers).status_code == 401
    assert len(touched) == 1


@pytest.mark.parametrize(
    "bad", ["missing_origin", "foreign_origin", "no_cookie", "cross_session", "bearer", "query"]
)
def test_websocket_denied_before_accept(transport, bad):
    _, client, _, sid, other, _, _, touched = transport
    browser_login(transport)
    headers = {"Origin": ORIGIN}
    path = f"/api/v1/sessions/{sid}/transport-probe"
    if bad == "missing_origin":
        headers.clear()
    elif bad == "foreign_origin":
        headers["Origin"] = "https://attacker.example"
    elif bad == "no_cookie":
        client.cookies.clear()
    elif bad == "cross_session":
        path = f"/api/v1/sessions/{other}/transport-probe"
    elif bad == "bearer":
        headers["Authorization"] = "Bearer synthetic-secret"
    else:
        path += "?token=synthetic-secret"
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(path, headers=headers):
            pytest.fail("unauthorized socket accepted")
    assert error.value.code == 1008
    assert touched == []


@pytest.mark.parametrize("cause", ["logout", "grant", "expired", "reset"])
def test_websocket_policy_recheck_rejects_revoked_principal_or_grant(transport, cause):
    app, client, auth, sid, _, _, now, _ = transport
    browser_login(transport)
    with client.websocket_connect(
        f"/api/v1/sessions/{sid}/transport-probe", headers={"Origin": ORIGIN}
    ) as ws:
        assert ws.receive_json()["actor"] == str(auth.account.id)
        if cause == "logout":
            app.state.sessions.logout(auth.token.get_secret_value())
        elif cause == "grant":
            app.state.permissions.revoke(
                auth.token.get_secret_value(), auth.account.id, sid, "read"
            )
        elif cause == "expired":
            now[0] = 10000
        else:
            app.state.accounts.reset_password(
                auth.account.id, auth.account.id, SecretStr(PASSWORD + "3")
            )
        ws.send_text("recheck")
        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()
        assert error.value.code == 1008


def manifest_source(t):
    from pathlib import Path

    from flowlens.contracts.models import SourceManifest

    app, _, _, sid, *_ = t
    source = SourceManifest.model_validate_json(
        Path("contracts/examples/manifest.json").read_text()
    )
    source = source.model_copy(update={"session_id": sid})
    with app.state.transactions.begin() as uow:
        uow.connection.execute(
            "INSERT INTO platform_sources VALUES (?,?,?,?,?)",
            (str(sid), str(source.id), 1, source.source_hash, source.model_dump_json()),
        )
        asset = source.assets[0]
        uow.connection.execute(
            "INSERT INTO platform_assets VALUES (?,?,?,?,?,?)",
            (str(sid), str(asset.id), str(source.id), 1, "private/synthetic.wav", asset.sha256),
        )
        uow.commit()
    return source


def serialize(t, value, **kwargs):
    from flowlens.api.serializers import public_dto

    app, _, auth, sid, *_ = t
    ctx = app.state.permissions.human_context(auth.token.get_secret_value(), sid)
    with app.state.transactions.begin() as uow:
        return public_dto(app.state.permissions, uow, ctx, value, **kwargs)


def test_observer_manifest_has_no_asset_inventory_or_fixture_path(transport):
    source = manifest_source(transport)
    result = serialize(transport, source)
    assert result["assets"] == []
    assert "tests/fixtures" not in str(result) and "private/" not in str(result)
    assert result["coverage"]["audio"] is True


def test_explicit_audio_grant_exposes_only_authorized_safe_asset_metadata(transport):
    app, _, auth, sid, *_ = transport
    source = manifest_source(transport)
    app.state.permissions.grant(
        auth.token.get_secret_value(),
        auth.account.id,
        sid,
        "audio",
        role="observer",
        expires_ms=10000,
    )
    result = serialize(transport, source)
    assert result["assets"][0]["id"] == str(source.assets[0].id)
    assert result["assets"][0]["fixture_path"] is None
    assert "private/" not in str(result) and "tests/fixtures" not in str(result)


@pytest.mark.parametrize("kind", ["raw", "context", "result", "truth", "private", "subclass"])
def test_public_serializer_denies_internal_raw_truth_and_subclass_payloads(transport, kind):
    from pathlib import Path

    from flowlens.contracts.models import JobResult, RequestContext, SourceManifest
    from flowlens.core.errors import ContractError

    source = manifest_source(transport)
    values = {
        "raw": {"truth": "hidden", "password": "synthetic-secret", "storage_key": "private/a"},
        "context": RequestContext.model_validate_json(
            Path("contracts/examples/context.json").read_text()
        ),
        "result": JobResult.model_validate_json(
            Path("contracts/examples/job_result.json").read_text()
        ),
        "truth": source,
        "private": source,
    }

    class ExtendedManifest(SourceManifest):
        secret: str = "synthetic-secret"

    values["subclass"] = ExtendedManifest(**source.model_dump())
    kwargs = {"classification": kind.upper()} if kind in ("truth", "private") else {}
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        serialize(transport, values[kind], **kwargs)


def test_public_serializer_revalidates_scope_and_current_source_rights(transport):
    from flowlens.core.errors import ContractError

    app, _, _, _, other, *_ = transport
    source = manifest_source(transport)
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        serialize(transport, source.model_copy(update={"session_id": other}))
    with app.state.transactions.begin() as uow:
        changed = source.model_copy(
            update={"permissions": source.permissions.model_copy(update={"local": False})}
        )
        uow.connection.execute(
            "UPDATE platform_sources SET payload=?", (changed.model_dump_json(),)
        )
        uow.commit()
    with pytest.raises(ContractError, match="SOURCE_PERMISSION_REQUIRED"):
        serialize(transport, source)


def test_public_serializer_rejects_forged_revoked_and_worker_contexts(transport):
    from flowlens.api.serializers import public_dto
    from flowlens.core.errors import ContractError

    app, _, auth, sid, _, run, *_ = transport
    source = manifest_source(transport)
    service = app.state.permissions
    ctx = service.human_context(auth.token.get_secret_value(), sid)
    forged = ctx.model_copy(update={"capabilities": ["read", "truth"]})
    with app.state.transactions.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        public_dto(service, uow, forged, source)
    worker = service.provision_worker(auth.token.get_secret_value(), expires_ms=10000)
    scope = service.bind_worker(auth.token.get_secret_value(), worker.id, sid, run, expires_ms=9000)
    worker_ctx = service.worker_context(worker.token.get_secret_value(), scope)
    with app.state.transactions.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        public_dto(service, uow, worker_ctx, source)
    service.revoke(auth.token.get_secret_value(), auth.account.id, sid, "read")
    with app.state.transactions.begin() as uow, pytest.raises(ContractError, match="ACCESS_DENIED"):
        public_dto(service, uow, ctx, source)


def public_event(t):
    from datetime import UTC, datetime

    from flowlens.contracts.models import SourceEvent

    _, _, _, sid, *_ = t
    return SourceEvent(
        id=uuid4(),
        session_id=sid,
        analysis_run_id=None,
        revision=1,
        event_time_ms=100,
        available_time_ms=150,
        recorded_at=datetime(2026, 10, 9, tzinfo=UTC),
        source_id=uuid4(),
        source_event_id="synthetic-observation",
        kind="REPORT",
        entity_id=None,
        source_hash="a" * 64,
        quality="SUPPORTED",
        statement="Observed synthetic report",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"event_time_ms": 501},
        {"available_time_ms": None},
        {"available_time_ms": 501},
        {"revision": 2},
        {"analysis_run_id": uuid4()},
    ],
)
def test_public_serializer_denies_future_unavailable_or_wrong_scope(transport, changes):
    from flowlens.core.errors import ContractError

    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        serialize(transport, public_event(transport).model_copy(update=changes))


def test_public_serializer_preserves_typed_observed_dto_and_does_not_mutate_input(transport):
    from flowlens.contracts.models import SourceEvent

    event = public_event(transport)
    output = serialize(transport, event)
    assert SourceEvent.model_validate_json(json.dumps(output)) == event


def test_public_snapshot_checks_nested_revision_and_mode(transport):
    from flowlens.contracts.models import Snapshot
    from flowlens.core.errors import ContractError

    _, _, _, sid, *_ = transport
    event = public_event(transport)
    snapshot = Snapshot(
        session_id=sid,
        analysis_run_id=None,
        revision=1,
        as_of_ms=500,
        mode="AS_KNOWN",
        sequence=1,
        events=[event],
        memory=[],
        findings=[],
        quality="SUPPORTED",
    )
    assert serialize(transport, snapshot)["events"][0]["statement"] == event.statement
    for changed in (
        snapshot.model_copy(update={"mode": "DEBRIEF"}),
        snapshot.model_copy(update={"events": [event.model_copy(update={"revision": 2})]}),
    ):
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            serialize(transport, changed)


@pytest.mark.parametrize(
    "headers",
    [
        [("Origin", ORIGIN), ("Origin", "https://attacker.example")],
        [("X-CSRF-Token", "0" * 64), ("X-CSRF-Token", "1" * 64)],
        [("Cookie", "flowlens_session=first; flowlens_session=second")],
        [("X-Request-Context", "synthetic-secret")],
    ],
)
def test_ambiguous_headers_and_context_headers_fail_closed(transport, headers):
    _, client, _, _, _, _, _, touched = transport
    browser_login(transport)
    response = client.get("/api/v1/probe", headers=headers)
    assert response.status_code == 403
    assert touched == []
    assert "synthetic-secret" not in response.text


@pytest.mark.parametrize("cause", ["logout", "expired", "reset", "forced_change"])
def test_http_principal_revocation_and_expiry_prevent_route_execution(transport, cause):
    app, client, auth, _, _, _, now, touched = transport
    browser_login(transport)
    if cause == "logout":
        app.state.sessions.logout(auth.token.get_secret_value())
    elif cause == "expired":
        now[0] += 8 * 60 * 60 * 1000
    elif cause == "reset":
        app.state.accounts.reset_password(
            auth.account.id, auth.account.id, SecretStr(PASSWORD + "3")
        )
    else:
        with app.state.transactions.begin() as uow:
            uow.connection.execute("UPDATE platform_accounts SET must_change_password=1")
            uow.commit()
    response = client.get("/api/v1/probe")
    assert response.status_code == (403 if cause == "forced_change" else 401)
    assert touched == []


def test_public_projection_remains_observed_even_with_truth_grant(transport):
    from flowlens.core.errors import ContractError

    app, _, auth, sid, *_ = transport
    source = manifest_source(transport)
    with app.state.transactions.begin() as uow:
        uow.connection.execute("UPDATE platform_context_state SET mode='DEBRIEF'")
        uow.commit()
    app.state.permissions.grant(
        auth.token.get_secret_value(),
        auth.account.id,
        sid,
        "truth",
        role="evaluator",
        expires_ms=10000,
    )
    assert serialize(transport, source)["assets"] == []
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        serialize(transport, source, classification="TRUTH")


def test_websocket_validation_errors_have_no_private_input_in_close_reason(transport):
    _, client, *_ = transport
    browser_login(transport)
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            "/api/v1/sessions/private-password/stream", headers={"Origin": ORIGIN}
        ):
            pytest.fail("invalid path accepted")
    assert error.value.code == 1008
    assert error.value.reason == ""


@pytest.mark.parametrize("kind,code", [("http", 1008), ("contract", 1008), ("unexpected", 1011)])
def test_websocket_error_boundary_never_echoes_exception_text(transport, kind, code):
    _, client, *_ = transport
    browser_login(transport)
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/api/v1/errors/{kind}", headers={"Origin": ORIGIN}):
            pytest.fail("failing socket accepted")
    assert error.value.code == code
    assert error.value.reason == ""


def test_http_context_checks_run_selector_and_ignores_client_clock_claims(transport):
    _, client, auth, sid, _, run, _, touched = transport
    browser_login(transport)
    path = f"/api/v1/sessions/{sid}/probe"
    assert client.get(
        path, params={"run_id": str(run), "mode": "DEBRIEF", "as_of_ms": 99999}
    ).json() == {
        "actor": str(auth.account.id),
        "mode": "AS_KNOWN",
        "as_of_ms": 500,
    }
    assert client.get(path, params={"run_id": str(uuid4())}).status_code == 403
    assert len(touched) == 1


def test_worker_principal_expiry_and_cross_principal_scope_denied(transport):
    app, client, auth, sid, _, run, now, _ = transport
    service = app.state.permissions
    first = service.provision_worker(auth.token.get_secret_value(), expires_ms=10000)
    second = service.provision_worker(auth.token.get_secret_value(), expires_ms=10000)
    scope = service.bind_worker(auth.token.get_secret_value(), first.id, sid, run, expires_ms=9000)
    headers = {"Authorization": "Bearer " + second.token.get_secret_value()}
    assert client.get(f"/internal/scopes/{scope}", headers=headers).status_code == 401
    now[0] = 10000
    assert client.get("/internal/probe", headers=headers).status_code == 401


def test_serializer_revalidates_invalid_model_copy_and_keeps_input_immutable(transport):
    from flowlens.core.errors import ContractError

    source = manifest_source(transport)
    before = source.model_dump_json()
    serialize(transport, source)
    assert source.model_dump_json() == before
    broken = source.model_copy(
        update={"clock": source.clock.model_copy(update={"offset_ms": None})}
    )
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        serialize(transport, broken)
