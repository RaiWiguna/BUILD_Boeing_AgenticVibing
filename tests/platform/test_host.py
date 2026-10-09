"""A01.1: exercise the real host boundary, without persistence or cloud calls."""

import importlib
import subprocess
import sys
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistration
from flowlens.testing.harness import build_harness
from pydantic import BaseModel, ConfigDict, ValidationError

ROOT = Path(__file__).resolve().parents[2]


def settings(**kwargs):
    return importlib.import_module("flowlens.core.host_config").HostSettings(**kwargs)


def host(config=None, modules=()):
    return importlib.import_module("flowlens.api.host").create_host(config, modules=modules)


@pytest.mark.parametrize(
    "values",
    [
        {"api_workers": 2},
        {"api_workers": True},
        {"api_workers": "1"},
        {"port": True},
        {"port": 0},
        {"port": 65536},
        {"host": "0.0.0.0"},
        {"host": "example.org"},
        {"profile": "production"},
        {"profile": "unknown"},
        {"contract_version": "2.0.0"},
        {"unknown": "private-password"},
    ],
)
def test_invalid_settings_are_rejected(values):
    with pytest.raises(ValidationError):
        settings(**values)


def test_environment_is_explicit_and_settings_are_immutable():
    config_type = importlib.import_module("flowlens.core.host_config").HostSettings
    config = config_type.from_environment(
        {"FLOWLENS_PROFILE": "test", "FLOWLENS_PORT": "8101", "UNRELATED": "secret"}
    )
    assert config.profile == "test"
    assert config.port == 8101
    assert config.api_workers == 1
    with pytest.raises(ValidationError):
        config.port = 9000


@pytest.mark.parametrize(
    "env",
    [
        {"WEB_CONCURRENCY": "2"},
        {"UVICORN_WORKERS": "2"},
        {"FLOWLENS_API_WORKERS": "2"},
        {"FLOWLENS_PORT": "private-password"},
        {"FLOWLENS_API_WORKER": "1"},
    ],
)
def test_environment_cannot_override_single_process_or_hide_typos(env):
    config_type = importlib.import_module("flowlens.core.host_config").HostSettings
    with pytest.raises(ValueError):
        config_type.from_environment(env)


def test_default_host_is_separate_from_contract_harness():
    with TestClient(host(settings())) as client:
        assert client.get("/health").json()["status"] == "alive"
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["ready"] is False
        assert response.json()["implementation"] == "HOST_ONLY"
        assert response.json()["profile"] == "development"
        release = client.get("/release.json").json()
        assert release["contract_version"] == "1.0.0"
        assert release["implementation"] == "HOST_ONLY"
        assert client.post("/_harness/validate/intent", json={}).status_code == 404
        assert "/api/v1/sessions" not in client.get("/openapi.json").json()["paths"]


def test_fake_b_registration_is_explicit_and_only_allowed_in_test():
    registration = build_harness("A").registry.modules[0]
    with pytest.raises(ValueError, match="MOCK"):
        host(settings(), modules=(registration,))
    app = host(settings(profile="test"), modules=(registration,))
    with TestClient(app) as client:
        assert client.get("/ready").json()["profile"] == "MOCK"
        assert client.get("/_harness/module").status_code == 200
    assert app.state.registry.modules[0].snapshot_reader is registration.snapshot_reader
    assert app.state.registry.modules[0].job_handlers == registration.job_handlers


def test_incompatible_and_duplicate_modules_fail_before_serving():
    with pytest.raises(ValueError, match="incompatible"):
        host(settings(), modules=(ModuleRegistration("bad", contract_version="2.0.0"),))
    with pytest.raises(ValueError, match="duplicate module"):
        host(settings(), modules=(ModuleRegistration("a"), ModuleRegistration("a")))


@pytest.mark.parametrize("path", ["/health", "/ready", "/release.json", "/docs"])
def test_modules_cannot_shadow_host_routes(path):
    router = APIRouter()
    router.get(path)(lambda: {"ready": True})
    with pytest.raises(ValueError, match="route"):
        host(settings(), modules=(ModuleRegistration("collision", routes=(router,)),))


def test_duplicate_module_routes_fail_before_serving():
    first, second = APIRouter(), APIRouter()
    first.get("/api/v1/example")(lambda: {})
    second.get("/api/v1/example")(lambda: {})
    with pytest.raises(ValueError, match="route"):
        host(settings(), modules=(ModuleRegistration("a", routes=(first, second)),))


class Input(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    count: int


def error_module():
    router = APIRouter()

    @router.post("/api/v1/test/input")
    def validate(payload: Input):
        return payload

    @router.get("/api/v1/test/denied")
    def denied():
        raise ContractError("ACCESS_DENIED")

    @router.get("/api/v1/test/broken")
    def broken():
        raise RuntimeError("private-password SELECT /private/audio.wav")

    @router.get("/api/v1/test/http")
    def http_error():
        raise HTTPException(403, detail="private-password", headers={"X-Secret": "secret"})

    return ModuleRegistration("error-test", routes=(router,))


@pytest.mark.parametrize(
    "path,status,code",
    [
        ("denied", 403, "ACCESS_DENIED"),
        ("broken", 500, "INTERNAL_ERROR"),
        ("http", 403, "ACCESS_DENIED"),
    ],
)
def test_errors_never_echo_private_exception_or_request_details(tmp_path, path, status, code):
    app = host(
        settings(profile="test", database_path=tmp_path / "errors.db"), modules=(error_module(),)
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        authenticate_error_client(app, client)
        response = client.get(f"/api/v1/test/{path}", headers={"X-Request-ID": "private-password"})
        assert response.status_code == status
        assert response.json()["code"] == code
        UUID(response.json()["request_id"])
        assert "private-password" not in response.text
        assert "SELECT" not in response.text
        assert "x-secret" not in response.headers


def authenticate_error_client(app, client):
    from pydantic import SecretStr

    initial = SecretStr("synthetic-error-initial")
    changed = SecretStr("synthetic-error-changed")
    account = app.state.accounts.bootstrap("admin", initial)
    app.state.accounts.change_password(account.id, initial, changed)
    auth = app.state.sessions.login("admin", changed, "local")
    client.cookies.set("flowlens_session", auth.token.get_secret_value())
    return {"Origin": app.state.settings.origin, "X-CSRF-Token": auth.csrf_token}


def test_validation_error_omits_input_and_uses_server_request_id(tmp_path):
    app = host(settings(database_path=tmp_path / "validation.db"), modules=(error_module(),))
    with TestClient(app) as client:
        headers = authenticate_error_client(app, client)
        response = client.post(
            "/api/v1/test/input", json={"count": "private-password"}, headers=headers
        )
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_INPUT"
        assert response.json()["field_issues"] == ["body.count"]
        UUID(response.json()["request_id"])
        assert "private-password" not in response.text


def test_launcher_uses_one_process_and_no_reload(monkeypatch):
    launcher = importlib.import_module("flowlens.api.serve")
    captured = {}

    def run(app, **kwargs):
        captured.update(kwargs)
        captured["app"] = app

    monkeypatch.setattr(launcher.uvicorn, "run", run)
    monkeypatch.setattr(launcher, "environ", {})
    launcher.main()
    assert captured["workers"] == 1
    assert captured["reload"] is False
    assert captured["host"] == "127.0.0.1"
    assert captured["access_log"] is False
    assert captured["proxy_headers"] is False


def test_launcher_rejects_config_without_printing_values():
    import os

    env = {k: v for k, v in os.environ.items() if not k.startswith("FLOWLENS_")}
    env["FLOWLENS_PORT"] = "private-password"
    proc = subprocess.run(
        [sys.executable, "-m", "flowlens.api.serve"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert proc.returncode != 0
    assert "Invalid host configuration" in proc.stderr
    assert "private-password" not in proc.stderr + proc.stdout
