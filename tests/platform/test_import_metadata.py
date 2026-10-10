"""A04.2 metadata revisions; disposable storage and independent conversion oracles."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_imports import assert_no_domain, stage, upload
from test_imports import importer as importer


def declaration(preview):
    return {
        "source_kind": "SYNTHETIC",
        "source_label": "Synthetic laboratory recording",
        "source_owner": "research-fixture-owner",
        "source_identifier": "laboratory-session-1",
        "dataset": "synthetic-fixtures",
        "dataset_version": "1",
        "subset": None,
        "rights": {
            "local": "ALLOWED",
            "cloud_audio": "DENIED",
            "cloud_context": "UNDETERMINED",
            "reviewer": "ALLOWED",
            "export": "DENIED",
            "audio_export": "DENIED",
            "basis": "Synthetic inputs owned by this test; no cloud consent.",
        },
        "retention": {"policy": "FIXED_DAYS", "days": 30, "basis": "Synthetic test policy"},
        "files": [
            {
                "file_id": str(item.id),
                "sha256": item.sha256,
                "channels": ["radio"] if item.role == "audio" else [],
                "clock": {"timezone": "UTC", "method": "UNKNOWN"},
            }
            for item in preview.files
        ],
        "coverage": {"vehicles": None, "speaker_identity": None, "gaps": []},
        "identities": [],
        "layout": None,
    }


def request(preview, *, expected=0, modify=None):
    from flowlens.imports.metadata import MetadataRequest

    data = declaration(preview)
    if modify:
        modify(data)
    return MetadataRequest.model_validate_json(
        json.dumps({"expected_revision": expected, "declaration": data})
    )


def prepare(importer, preview, payload=None, *, key="metadata-key"):
    from flowlens.imports.metadata import ImportMetadata

    service, auth, _ = importer
    metadata = ImportMetadata(service)
    return metadata.prepare(
        auth.token.get_secret_value(), preview.id, key, payload or request(preview)
    )


def test_audio_only_manifest_hash_roundtrip_and_unknowns(importer):
    from flowlens.imports.metadata import ImportMetadata, PreparedImport

    preview = stage(importer)
    result = prepare(importer, preview)
    assert result.revision == 1
    assert result.locally_eligible
    assert result.status == "PREPARED"
    assert not result.cloud_audio_eligible and not result.cloud_context_eligible
    assert result.manifest.permissions.local
    assert not result.manifest.permissions.cloud
    assert result.manifest.permissions.retention_days == 30
    assert result.manifest.coverage.vehicles is None
    assert result.manifest.coverage.speaker_identity is None
    assert not result.manifest.coverage.tracks
    assert result.manifest.clock.offset_ms is None
    assert result.alignment_status == "UNKNOWN"
    assert result.manifest.assets[0].sha256 == preview.files[0].sha256
    assert result.manifest.assets[0].fixture_path is None
    assert PreparedImport.model_validate_json(result.model_dump_json()) == result
    service, auth, _ = importer
    assert ImportMetadata(service).get(auth.token.get_secret_value(), preview.id) == result
    assert_no_domain(service)
    assert str(service.root) not in result.model_dump_json()


def test_receipt_revision_conflicts_preserve_previous_declaration(importer):
    from flowlens.core.errors import ContractError
    from flowlens.imports.metadata import ImportMetadata

    preview = stage(importer)
    first = prepare(importer, preview)
    assert prepare(importer, preview) == first
    changed = request(preview, modify=lambda d: d.update(source_label="Changed label"))
    with pytest.raises(ContractError) as error:
        prepare(importer, preview, changed)
    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    with pytest.raises(ContractError) as error:
        prepare(importer, preview, changed, key="stale-version")
    assert error.value.code == "VERSION_CONFLICT"
    second = prepare(
        importer,
        preview,
        request(preview, expected=1, modify=lambda d: d.update(source_label="Changed label")),
        key="second-revision",
    )
    assert second.revision == 2 and second.content_hash == first.content_hash
    assert second.manifest.id == first.manifest.id
    assert second.manifest_hash != first.manifest_hash
    assert prepare(importer, preview) == first
    service, auth, _ = importer
    metadata = ImportMetadata(service)
    assert metadata.get(auth.token.get_secret_value(), preview.id, revision=1) == first
    assert metadata.get(auth.token.get_secret_value(), preview.id) == second
    assert first.declaration.source_label != second.declaration.source_label
    assert_no_domain(service)


@pytest.mark.parametrize("right", ["DENIED", "UNDETERMINED"])
def test_unknown_local_or_retention_blocks_local_eligibility(importer, right):
    preview = stage(importer)
    result = prepare(
        importer,
        preview,
        request(preview, modify=lambda d: d["rights"].update(local=right)),
    )
    assert not result.locally_eligible and result.manifest is None
    assert result.status == "NEEDS_REMEDIATION"
    assert any(issue.code == "LOCAL_RIGHT_REQUIRED" and issue.blocking for issue in result.issues)


def test_declared_cloud_categories_and_export_gate_are_separate(importer):
    from flowlens.core.errors import ContractError

    preview = stage(importer)
    result = prepare(
        importer,
        preview,
        request(preview, modify=lambda d: d["rights"].update(cloud_audio="ALLOWED")),
    )
    result.require_right("cloud_audio")
    assert result.cloud_audio_eligible and not result.cloud_context_eligible
    assert not result.manifest.permissions.cloud
    for action in ("cloud_context", "export", "audio_export"):
        with pytest.raises(ContractError):
            result.require_right(action)


def test_clock_oracles_timezone_dst_drift_and_unknown():
    from flowlens.clocks.normalization import ClockSpec, source_timestamp_ms
    from flowlens.imports.staging import ImportFailure

    clock = ClockSpec(
        timezone="UTC",
        method="DECLARED_LINEAR",
        offset_ms=2000,
        uncertainty_ms=50,
        drift_ppm=100.0,
        basis="synthetic oracle",
        reviewer="fixture-reviewer",
    )
    assert clock.to_session_ms(1000000) == 1002100
    assert clock.to_session_ms(0) == 2000
    assert ClockSpec(timezone="UNKNOWN").to_session_ms(1234) is None
    origin = datetime(2026, 10, 9, tzinfo=UTC)
    assert source_timestamp_ms("2026-10-09T07:00:01.250", "Asia/Jakarta", origin) == 1250
    assert source_timestamp_ms("2026-10-09T00:00:01.250Z", "UTC", origin) == 1250
    fall_origin = datetime(2026, 11, 1, 4, tzinfo=UTC)
    with pytest.raises(ImportFailure) as error:
        source_timestamp_ms("2026-11-01T01:30:00", "America/New_York", fall_origin)
    assert error.value.issues[0].code == "AMBIGUOUS_TIME"
    assert (
        source_timestamp_ms("2026-11-01T01:30:00", "America/New_York", fall_origin, fold=0)
        == 5400000
    )
    assert (
        source_timestamp_ms("2026-11-01T01:30:00", "America/New_York", fall_origin, fold=1)
        == 9000000
    )
    with pytest.raises(ImportFailure) as error:
        source_timestamp_ms(
            "2026-03-08T02:30:00", "America/New_York", datetime(2026, 3, 8, tzinfo=UTC)
        )
    assert error.value.issues[0].code == "NONEXISTENT_TIME"


def test_layout_feet_oracle_does_not_change_raw_declaration(importer):
    preview = stage(importer)
    payload = request(
        preview,
        modify=lambda d: d.update(
            layout={
                "version": "fictional-ft-1",
                "coordinate_system": "LOCAL_CARTESIAN",
                "units": "ft",
                "validity": {"start_ms": 0, "end_ms": 10000},
                "uncertainty": 1.0,
                "runway_polygon": [[0.0, 0.0], [100.0, 0.0], [100.0, 10.0], [0.0, 10.0]],
                "hold_lines": [{"id": "H1", "points": [[-10.0, 0.0], [-10.0, 10.0]]}],
            }
        ),
    )
    result = prepare(importer, preview, payload)
    assert result.layout.units == "m"
    assert result.layout.runway_polygon[1][0] == pytest.approx(30.48)
    assert result.layout.runway_polygon[2][1] == pytest.approx(3.048)
    assert result.layout.uncertainty == pytest.approx(0.3048)
    assert result.declaration.layout.units == "ft"
    assert result.declaration.layout.runway_polygon[1][0] == 100.0
    assert result.manifest.layout_version == "fictional-ft-1"


def paired(importer):

    return stage(
        importer,
        [
            upload(),
            upload(
                Path("tests/fixtures/events/track.json").read_bytes(),
                role="tracks",
                filename="tracks.json",
                media_type="application/json",
            ),
        ],
    )


def test_sidecar_normalization_maps_time_and_scoped_identity_without_raw_changes(importer):

    preview = paired(importer)
    record = json.loads(Path("tests/fixtures/events/track.json").read_text())
    data = declaration(preview)
    for file in data["files"]:
        file["clock"] = {
            "timezone": "UTC",
            "method": "DECLARED_OFFSET",
            "offset_ms": 1000,
            "uncertainty_ms": 20,
            "basis": "independent fixture clock",
            "reviewer": "fixture-reviewer",
        }
    data["layout"] = {
        "version": "fictional-1",
        "coordinate_system": "LOCAL_CARTESIAN",
        "units": "m",
        "validity": {"start_ms": 0, "end_ms": 10000},
        "uncertainty": 0.5,
        "runway_polygon": [[-100.0, -10.0], [100.0, -10.0], [100.0, 10.0], [-100.0, 10.0]],
        "hold_lines": [{"id": "H1", "points": [[-30.0, -20.0], [-30.0, 20.0]]}],
    }
    data["identities"] = [
        {
            "source_entity_id": record["entity_id"],
            "callsign": "test123",
            "aliases": ["test23"],
            "validity": {"start_ms": 1000, "end_ms": 10000},
            "evidence_file_id": str(preview.files[1].id),
            "evidence_record_ids": ["track-1"],
        }
    ]
    from flowlens.imports.metadata import MetadataRequest

    payload = MetadataRequest.model_validate_json(
        json.dumps({"expected_revision": 0, "declaration": data})
    )
    result = prepare(importer, preview, payload)
    summary = result.normalizations[0]
    assert summary.rows == 1 and summary.min_event_ms == summary.max_event_ms == 1100
    assert summary.available_unknown == 0 and summary.min_available_ms == 1200
    assert result.identities[0].callsign == "TEST123"
    assert result.identities[0].source_entity_id == record["entity_id"]
    assert str(result.identities[0].entity_id) != record["entity_id"]
    assert result.identities[0].entity_id != result.manifest.session_id
    assert result.alignment_status == "KNOWN"
    assert result.paired_status == "METADATA_COMPLETE"
    raw = next(importer[0].root.rglob(str(preview.files[1].id) + ".upload"))
    assert raw.read_bytes() == Path("tests/fixtures/events/track.json").read_bytes()
    assert_no_domain(importer[0])


def test_unknown_clock_preserves_unknown_sidecar_available_and_identity(importer):
    preview = paired(importer)
    result = prepare(importer, preview)
    assert result.normalizations[0].min_event_ms is None
    assert result.normalizations[0].min_available_ms is None
    assert result.paired_status == "NOT_EVALUABLE"
    assert result.identities == []
    assert result.manifest.coverage.vehicles is None


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["files"][0].update(sha256="0" * 64),
        lambda d: d.update(files=[]),
        lambda d: d["files"][0].update(channels=[]),
        lambda d: d["coverage"].update(vehicles=True, basis="declared vehicles"),
    ],
)
def test_inconsistent_file_and_coverage_declarations_rejected(importer, change):
    from flowlens.imports.staging import ImportFailure
    from pydantic import ValidationError

    preview = stage(importer)
    with pytest.raises((ImportFailure, ValidationError)):
        prepare(importer, preview, request(preview, modify=change))
    with importer[0].database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_import_metadata").fetchone()[0]
            == 0
        )


def test_retention_unknown_is_not_projected_to_a_default(importer):
    preview = stage(importer)
    result = prepare(
        importer,
        preview,
        request(
            preview,
            modify=lambda d: d.update(
                retention={"policy": "UNDETERMINED", "basis": "awaiting source owner"}
            ),
        ),
    )
    assert not result.locally_eligible and result.manifest is None
    assert any(x.code == "RETENTION_REQUIRED" and x.blocking for x in result.issues)


def test_hash_tampering_is_detected_on_roundtrip(importer):
    from flowlens.imports.metadata import PreparedImport
    from pydantic import ValidationError

    result = prepare(importer, stage(importer))
    data = json.loads(result.model_dump_json())
    data["declaration"]["rights"]["cloud_context"] = "ALLOWED"
    with pytest.raises(ValidationError):
        PreparedImport.model_validate_json(json.dumps(data))


def test_metadata_sql_immutable_and_ttl_cascade_cleanup(importer):
    import sqlite3

    from flowlens.imports.staging import Imports

    service, _, clock = importer
    result = prepare(importer, stage(importer))
    for query in (
        "UPDATE platform_import_metadata SET revision=2",
        "DELETE FROM platform_import_metadata",
        "INSERT OR REPLACE INTO platform_import_metadata SELECT * FROM platform_import_metadata",
    ):
        with service.database.begin() as uow:
            with pytest.raises(sqlite3.DatabaseError):
                uow.connection.execute(query)
    service.close()
    clock[0] = 86401000
    restarted = Imports(service.database, service.sessions, service.root)
    try:
        with service.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_import_metadata").fetchone()[
                    0
                ]
                == 0
            )
        assert not (service.root / str(result.id)).exists()
    finally:
        restarted.close()


def test_self_intersecting_layout_rejected(importer):
    from pydantic import ValidationError

    preview = stage(importer)
    with pytest.raises(ValidationError):
        request(
            preview,
            modify=lambda d: d.update(
                layout={
                    "version": "invalid-crossing",
                    "coordinate_system": "LOCAL_CARTESIAN",
                    "units": "m",
                    "validity": {"start_ms": 0, "end_ms": 10000},
                    "uncertainty": 0.0,
                    "runway_polygon": [[0.0, 0.0], [4.0, 4.0], [0.0, 4.0], [4.0, 0.0], [5.0, -1.0]],
                    "hold_lines": [{"id": "H1", "points": [[-1.0, 0.0], [-1.0, 1.0]]}],
                }
            ),
        )


def test_reviewer_permission_is_not_granted_by_frozen_local_projection(importer):
    preview = stage(importer)
    result = prepare(
        importer, preview, request(preview, modify=lambda d: d["rights"].update(reviewer="DENIED"))
    )
    assert result.locally_eligible
    assert not result.manifest.permissions.local
    from flowlens.core.errors import ContractError

    with pytest.raises(ContractError):
        result.require_right("reviewer")


def test_http_metadata_routes_have_origin_csrf_revision_and_safe_errors(tmp_path):
    from pathlib import Path

    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings
    from pydantic import SecretStr

    app = create_host(
        HostSettings(
            profile="test",
            database_path=tmp_path / "http.db",
            import_staging_path=tmp_path / "staging",
        )
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        account = app.state.accounts.bootstrap("admin", SecretStr("synthetic-import-initial"))
        app.state.accounts.change_password(
            account.id, SecretStr("synthetic-import-initial"), SecretStr("synthetic-import-changed")
        )
        auth = app.state.sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
        client.cookies.set("flowlens_session", auth.token.get_secret_value())
        headers = {
            "Origin": app.state.settings.origin,
            "X-CSRF-Token": auth.csrf_token,
            "Idempotency-Key": "upload-http",
        }
        response = client.post(
            "/api/v1/imports",
            headers=headers,
            files={
                "audio": (
                    "sample.wav",
                    Path("tests/fixtures/audio/hold-short.wav").read_bytes(),
                    "audio/wav",
                )
            },
        )
        from flowlens.imports.staging import ImportPreview

        preview = ImportPreview.model_validate_json(response.text)
        endpoint = f"/api/v1/imports/{preview.id}/metadata"
        payload = {"expected_revision": 0, "declaration": declaration(preview)}
        headers["Idempotency-Key"] = "metadata-http"
        result = client.post(endpoint, headers=headers, json=payload)
        assert result.status_code == 201
        assert result.json()["status"] == "PREPARED"
        current_preview = client.get(f"/api/v1/imports/{preview.id}").json()
        assert current_preview["metadata_revision"] == 1
        assert current_preview["rights_status"] == "DECLARED"
        assert current_preview["status"] == "PREPARED"
        assert result.headers["Cache-Control"] == "no-store"
        schema = app.openapi()
        assert "Declaration" in schema["components"]["schemas"]
        assert (
            schema["paths"]["/api/v1/imports/{import_id}/metadata"]["post"]["requestBody"][
                "content"
            ]["application/json"]["schema"]["properties"]["declaration"]["$ref"]
            == "#/components/schemas/Declaration"
        )
        assert client.get(endpoint).json() == result.json()
        assert client.get(endpoint + "?revision=1").json() == result.json()
        assert client.post(endpoint, headers=headers, json=payload).json() == result.json()
        no_csrf = {k: v for k, v in headers.items() if k != "X-CSRF-Token"}
        assert client.post(endpoint, headers=no_csrf, json=payload).status_code == 403
        payload["declaration"]["source_label"] = "Changed"
        assert client.post(endpoint, headers=headers, json=payload).status_code == 409
        payload["declaration"]["layout"] = {"private_path": "/private/not-a-layout"}
        error = client.post(endpoint, headers=headers, json=payload)
        assert error.status_code == 422
        assert "/private/not-a-layout" not in error.text
        payload["declaration"]["layout"] = {
            "version": "fictional-1",
            "coordinate_system": "LOCAL_CARTESIAN",
            "units": "yards",
            "validity": {"start_ms": 0, "end_ms": 10000},
            "uncertainty": 0.0,
            "runway_polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]],
            "hold_lines": [{"id": "H1", "points": [[-1.0, 0.0], [-1.0, 1.0]]}],
        }
        issue = client.post(endpoint, headers=headers, json=payload)
        assert issue.status_code == 422
        assert any("UNKNOWN_UNITS" in field for field in issue.json()["field_issues"])
        assert "yards" not in issue.text
        assert (
            client.post(endpoint, headers=headers, content=b"x" * (1024**2 + 1)).status_code == 422
        )
        assert_no_domain(app.state.imports)
    assert app.state.imports is None


def test_live_metadata_preflight_uses_latest_rights_after_revision(importer):
    from flowlens.core.errors import ContractError
    from flowlens.imports.metadata import ImportMetadata

    preview = stage(importer)
    original = prepare(
        importer,
        preview,
        request(preview, modify=lambda d: d["rights"].update(cloud_audio="ALLOWED")),
    )
    service, auth, _ = importer
    metadata = ImportMetadata(service)
    assert (
        metadata.require_right(auth.token.get_secret_value(), preview.id, "cloud_audio") == original
    )
    prepare(importer, preview, request(preview, expected=1), key="revoked-cloud")
    with pytest.raises(ContractError) as error:
        metadata.require_right(auth.token.get_secret_value(), preview.id, "cloud_audio")
    assert error.value.code == "CLOUD_TRANSFER_BLOCKED"
    assert metadata.get(auth.token.get_secret_value(), preview.id, revision=1) == original


def test_linear_clock_is_not_silently_projected_as_offset_only(importer):
    preview = stage(importer)

    def linear(d):
        d["files"][0]["clock"] = {
            "timezone": "UTC",
            "method": "DECLARED_LINEAR",
            "offset_ms": 2000,
            "uncertainty_ms": 50,
            "drift_ppm": 100.0,
            "basis": "fixture calibration",
            "reviewer": "fixture-reviewer",
        }

    result = prepare(importer, preview, request(preview, modify=linear))
    assert result.declaration.files[0].clock.to_session_ms(1000000) == 1002100
    assert result.manifest.clock.offset_ms is None
    assert result.manifest.coverage.quality == "MISSING"


@pytest.mark.parametrize(
    "clock",
    [
        {"timezone": "invented/no-such-zone"},
        {"timezone": "UTC", "offset_ms": 0},
        {"timezone": "UTC", "method": "DECLARED_OFFSET", "offset_ms": 0, "uncertainty_ms": None},
        {
            "timezone": "UTC",
            "method": "DECLARED_LINEAR",
            "offset_ms": 0,
            "uncertainty_ms": 0,
            "drift_ppm": float("nan"),
            "basis": "x",
            "reviewer": "x",
        },
    ],
)
def test_clock_metadata_rejects_inconsistent_or_nonfinite_fields(clock):
    from flowlens.clocks.normalization import ClockSpec
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ClockSpec.model_validate(clock)


def test_missing_available_time_is_never_fabricated_and_recorded_time_retained():
    from pathlib import Path
    from uuid import UUID

    from flowlens.clocks.normalization import ClockSpec
    from flowlens.contracts.models import Track
    from flowlens.imports.normalization import normalize_record

    data = json.loads(Path("tests/fixtures/events/track.json").read_text())
    data["available_time_ms"] = None
    track = Track.model_validate_json(json.dumps(data))
    normalized = normalize_record(
        track,
        ClockSpec(
            timezone="UTC",
            method="DECLARED_OFFSET",
            offset_ms=1000,
            uncertainty_ms=10,
            basis="fixture",
            reviewer="fixture",
        ),
        UUID(int=123),
        UUID(int=456),
        [],
    )
    assert normalized.event_time_ms == 1100 and normalized.available_time_ms is None
    assert normalized.raw_available_time_ms is None
    assert normalized.raw_event_time_ms == 100
    assert normalized.recorded_at == datetime(2026, 10, 8, tzinfo=UTC)
    assert normalized.raw_entity_id == track.entity_id and normalized.entity_id is None


def test_metadata_owner_revocation_and_tamper_fail_closed(importer):
    from flowlens.core.errors import ContractError
    from flowlens.imports.metadata import ImportMetadata
    from flowlens.imports.staging import ImportFailure
    from pydantic import SecretStr

    service, auth, _ = importer
    preview = stage(importer)
    prepare(importer, preview)
    second = service.sessions.accounts.create(
        auth.account.id, "second-admin", SecretStr("synthetic-second-admin"), is_admin=True
    )
    service.sessions.accounts.change_password(
        second.id, SecretStr("synthetic-second-admin"), SecretStr("synthetic-second-changed")
    )
    other = service.sessions.login("second-admin", SecretStr("synthetic-second-changed"), "local")
    metadata = ImportMetadata(service)
    with pytest.raises(ContractError) as error:
        metadata.get(other.token.get_secret_value(), preview.id)
    assert error.value.code == "ACCESS_DENIED"
    service.sessions.logout(auth.token.get_secret_value())
    with pytest.raises(ContractError) as error:
        metadata.prepare(
            auth.token.get_secret_value(), preview.id, "metadata-key", request(preview)
        )
    assert error.value.code == "AUTH_REQUIRED"
    fresh = service.sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
    next(service.root.rglob("*.upload")).write_bytes(b"synthetic tamper")
    with pytest.raises(ImportFailure):
        metadata.get(fresh.token.get_secret_value(), preview.id)


def test_metadata_same_key_concurrency_and_commit_fault_are_atomic(importer, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from flowlens.imports.metadata import ImportMetadata
    from flowlens.storage.sqlite.database import UnitOfWork

    service, auth, _ = importer
    preview = stage(importer)
    metadata = ImportMetadata(service)

    def run():
        return metadata.prepare(
            auth.token.get_secret_value(), preview.id, "concurrent", request(preview)
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: run(), range(3)))
    assert all(result == results[0] for result in results)
    with service.database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_import_metadata").fetchone()[0]
            == 1
        )

    def fail_commit(self):
        raise RuntimeError("synthetic commit fault")

    monkeypatch.setattr(UnitOfWork, "commit", fail_commit)
    with pytest.raises(RuntimeError):
        metadata.prepare(
            auth.token.get_secret_value(), preview.id, "fault", request(preview, expected=1)
        )
    with service.database.begin() as uow:
        assert (
            uow.connection.execute("SELECT COUNT(*) FROM platform_import_metadata").fetchone()[0]
            == 1
        )
    assert_no_domain(service)


def test_upgrade_from_a041_preserves_staged_preview_and_adds_metadata(tmp_path):
    from flowlens.auth.accounts import Accounts
    from flowlens.auth.sessions import Sessions
    from flowlens.imports.metadata import ImportMetadata
    from flowlens.imports.staging import Imports
    from flowlens.storage.sqlite.database import Database
    from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS
    from pydantic import SecretStr
    from test_imports import upload

    path, root = tmp_path / "upgrade.db", tmp_path / "staging"
    with Database(path, migrations=PLATFORM_MIGRATIONS[:8]) as database:
        accounts = Accounts(database)
        admin = accounts.bootstrap("admin", SecretStr("synthetic-import-initial"))
        accounts.change_password(
            admin.id, SecretStr("synthetic-import-initial"), SecretStr("synthetic-import-changed")
        )
        sessions = Sessions(database, accounts, clock=lambda: 1000)
        auth = sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
        imports = Imports(database, sessions, root)
        try:
            preview = imports.stage(auth.token.get_secret_value(), "upgrade", [upload()])
        finally:
            imports.close()
    with Database(path, migrations=PLATFORM_MIGRATIONS[:9]) as database:
        imports = Imports(
            database, Sessions(database, Accounts(database), clock=lambda: 1000), root
        )
        try:
            assert imports.get(auth.token.get_secret_value(), preview.id) == preview
            prepared = ImportMetadata(imports).prepare(
                auth.token.get_secret_value(), preview.id, "upgraded-metadata", request(preview)
            )
            assert prepared.files == preview.files
            with database.begin() as uow:
                assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()
                assert (
                    uow.connection.execute(
                        "SELECT COUNT(*) FROM platform_schema_migrations"
                    ).fetchone()[0]
                    == 9
                )
            assert_no_domain(imports)
        finally:
            imports.close()
