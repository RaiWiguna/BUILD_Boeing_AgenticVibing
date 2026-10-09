"""Smoke fail-closed tests. Injected SDK double never establishes real provider success."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
from flowlens.providers.stt import smoke
from flowlens.testing.stt import MockClient, mock_binding, mock_config
from google.auth.credentials import AnonymousCredentials

ROOT = Path(__file__).resolve().parents[2]


def profile():
    config = mock_config(max_calls=1)
    binding, _ = mock_binding(config)
    return smoke.SmokeProfile(
        config=config,
        approval=binding.approval,
        quota_verified=True,
        synthetic_cloud_rights_verified=True,
        budget_microunits=90,
        price_microunits_per_second=10,
    )


@pytest.mark.parametrize(
    "negative,code",
    [
        ("credentials", "CREDENTIALS_UNAVAILABLE"),
        ("quota", "QUOTA_UNVERIFIED"),
        ("rights", "RIGHTS_UNVERIFIED"),
        ("budget", "BUDGET_INSUFFICIENT"),
        ("retry", "SMOKE_LIMITS_INVALID"),
        ("logging", "PROFILE_UNVERIFIED"),
        ("hash", "PROFILE_UNVERIFIED"),
    ],
)
def test_preflight_blocks_before_client_creation(negative, code):
    candidate = profile()
    if negative == "quota":
        candidate = candidate.model_copy(update={"quota_verified": False})
    elif negative == "rights":
        candidate = candidate.model_copy(update={"synthetic_cloud_rights_verified": False})
    elif negative == "budget":
        candidate = candidate.model_copy(update={"budget_microunits": 1})
    elif negative == "retry":
        candidate = candidate.model_copy(update={"config": mock_config(max_attempts=2)})
    elif negative in {"logging", "hash"}:
        candidate = candidate.model_copy(
            update={
                "approval": candidate.approval.model_copy(
                    update={"data_logging": "UNKNOWN"}
                    if negative == "logging"
                    else {"config_hash": "0" * 64}
                )
            }
        )
    assert code in smoke.preflight(candidate, negative != "credentials")


def test_default_real_smoke_entrypoint_no_lookup_no_rpc():
    result = subprocess.run(
        [sys.executable, "-m", "flowlens.providers.stt.smoke"],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "BLOCKED" and report["provider_calls"] == 0
    assert report["sdk_version"] == "2.41.0" and result.stderr == ""


def test_profile_dry_run_does_not_read_credentials_or_open_channel(tmp_path, monkeypatch, capsys):
    path = tmp_path / "approved.json"
    path.write_text(profile().model_dump_json())
    credentials = tmp_path / "credentials.json"
    credentials.write_text("sensitive-invalid-credential")
    monkeypatch.setattr(
        sys, "argv", ["smoke", "--profile", str(path), "--credentials", str(credentials)]
    )

    def fail(*args, **kwargs):
        pytest.fail("dry run must not load credentials/create client")

    monkeypatch.setattr(smoke, "load_credentials_from_file", fail)
    monkeypatch.setattr(smoke, "GoogleClient", fail)
    smoke.main()
    output = capsys.readouterr()
    assert json.loads(output.out)["status"] == "PREFLIGHT_ONLY"
    assert "sensitive" not in output.out and str(tmp_path) not in output.out


def test_bad_profile_diagnostics_omit_private_paths(tmp_path, monkeypatch, capsys):
    path = tmp_path / "private-account.json"
    path.write_text("secret malformed profile")
    monkeypatch.setattr(sys, "argv", ["smoke", "--profile", str(path), "--execute"])
    smoke.main()
    output = capsys.readouterr()
    assert json.loads(output.out)["status"] == "BLOCKED"
    assert "private-account" not in output.out and "secret" not in output.out


def test_actual_ffmpeg_smoke_plumbing_with_mock_sdk_only(monkeypatch):
    client = MockClient()
    monkeypatch.setattr(smoke, "GoogleClient", lambda config, credentials: client)
    report = asyncio.run(smoke.run_smoke(profile(), AnonymousCredentials(), ROOT))
    # This assertion validates plumbing ONLY: injected SDK is MOCK, no cloud RPC.
    assert client.closed and len(client.requests) == 1
    assert report["attempted_audio_ms"] == 8022 and report["reserved_microunits"] == 90
    assert report["actual_cost_microunits"] is None
    assert report["label_status"] == "NOT_GOLD/NOT_DOMAIN_VALIDATED"


def test_changed_waveform_never_creates_client(tmp_path, monkeypatch):
    source = tmp_path / "tests/fixtures/audio/hold-short.wav"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"unauthorized audio")
    created = []
    monkeypatch.setattr(smoke, "GoogleClient", lambda *args: created.append(True))
    with pytest.raises(smoke.STTFailure, match="STT_PERMISSION_DENIED"):
        asyncio.run(smoke.run_smoke(profile(), AnonymousCredentials(), tmp_path))
    assert created == []
