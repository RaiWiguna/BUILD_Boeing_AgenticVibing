"""Audited legacy history metadata only; quarantine payload stays unavailable."""

import importlib
from uuid import uuid5

import pytest
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.legacy import NAMESPACE, import_archive
from test_imports import importer as importer
from test_legacy import archive


def test_legacy_alias_history_metadata_no_seed_truth_or_commands(importer, tmp_path):
    imports, auth, clock = importer
    path = tmp_path / "legacy.db"
    archive(path)
    import_archive(path, imports.database)
    from flowlens.auth.permissions import Permissions

    p = Permissions(imports.database, imports.sessions)
    sid = uuid5(NAMESPACE, "abcdef123456")
    p.grant(
        auth.token.get_secret_value(),
        auth.account.id,
        sid,
        "read",
        role="observer",
        expires_ms=clock[0] + 10000,
    )
    reader = importlib.import_module("flowlens.replay.compatibility").LegacyHistory(p)
    result = reader.read(auth.token.get_secret_value(), "abcdef123456")
    assert result.session_id == sid and result.legacy_id == "abcdef123456"
    assert result.runtime_status == "INTERRUPTED" and result.available_time_ms is None
    assert result.frames[0].sim_ms == 0 and result.frames[0].sequence == 1
    assert result.source_status == "NOT_EVALUABLE"
    assert not any(
        k in result.model_dump_json()
        for k in ("seed", "private", "assessment", "request", "response")
    )
    assert reader.read(auth.token.get_secret_value(), sid) == result
    p.revoke(auth.token.get_secret_value(), auth.account.id, sid, "read")
    with pytest.raises(ContractError):
        reader.read(auth.token.get_secret_value(), "abcdef123456")


def test_historical_casing_and_training_routes_explicitly_rejected(tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    app = create_host(HostSettings(profile="test"))
    with TestClient(app) as client:
        for route in (
            "/api/v1/auth/operator",
            "/api/v1/seats",
            "/api/v1/sessions/abcdef123456/commands",
        ):
            assert client.post(
                route, json={"simMs": 10, "sessionId": "abcdef123456"}
            ).status_code in (401, 403)
        assert all(
            "commands" not in r and "operator" not in r and "seats" not in r
            for r in app.openapi()["paths"]
        )
