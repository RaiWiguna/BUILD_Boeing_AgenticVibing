"""A04.1 untrusted upload staging; synthetic audio and disposable storage only."""

import hashlib
import io
import json
import os
from pathlib import Path

import pytest
import soundfile
from flowlens.auth.accounts import Accounts
from flowlens.auth.sessions import Sessions
from flowlens.storage.sqlite.database import Database
from pydantic import SecretStr


@pytest.fixture
def importer(tmp_path):
    from flowlens.imports.staging import ImportLimits, Imports

    with Database(tmp_path / "data.db") as db:
        accounts = Accounts(db)
        admin = accounts.bootstrap("admin", SecretStr("synthetic-import-initial"))
        accounts.change_password(
            admin.id, SecretStr("synthetic-import-initial"), SecretStr("synthetic-import-changed")
        )
        now = [1000]
        sessions = Sessions(db, accounts, clock=lambda: now[0])
        auth = sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
        service = Imports(
            db,
            sessions,
            tmp_path / "staging",
            limits=ImportLimits(max_file_bytes=1024 * 1024, max_total_bytes=2 * 1024 * 1024),
        )
        try:
            yield service, auth, now
        finally:
            service.close()


def upload(
    data=None, *, role="audio", filename="sample.wav", media_type="audio/wav", expected=None
):
    from flowlens.imports.staging import Upload

    body = data if data is not None else Path("tests/fixtures/audio/hold-short.wav").read_bytes()
    return Upload(
        role,
        filename,
        media_type,
        (body[index : index + 4096] for index in range(0, len(body), 4096)),
        expected,
    )


def stage(p, files=None, *, key="synthetic-key"):
    service, auth, _ = p
    return service.stage(auth.token.get_secret_value(), key, files or [upload()])


def assert_no_domain(service):
    with service.database.begin() as uow:
        for table in (
            "platform_sessions",
            "platform_sources",
            "platform_assets",
            "platform_jobs",
            "platform_runs",
        ):
            assert uow.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_wav_preview_is_private_hashed_and_never_committed(importer):
    service, auth, _ = importer
    body = Path("tests/fixtures/audio/hold-short.wav").read_bytes()
    preview = stage(importer)
    assert preview.status == "NEEDS_REMEDIATION"
    assert preview.files[0].sha256 == hashlib.sha256(body).hexdigest()
    assert preview.files[0].channels == 1
    assert preview.files[0].sample_rate_hz == 16000
    assert preview.files[0].duration_ms == 8021
    assert preview.clock_alignment == "UNKNOWN"
    assert preview.layout_status == "UNKNOWN"
    assert preview.rights_status == "UNDECLARED"
    assert not preview.tracks_present
    assert {issue.code for issue in preview.issues} >= {"RIGHTS_REQUIRED", "CLOCK_REQUIRED"}
    assert str(service.root) not in preview.model_dump_json()
    assert "storage_key" not in preview.model_dump_json()
    assert service.get(auth.token.get_secret_value(), preview.id) == preview
    assert service.root.stat().st_mode & 0o077 == 0
    for path in service.root.rglob("*.upload"):
        assert path.stat().st_mode & 0o077 == 0
        assert path.read_bytes() == body
    assert_no_domain(service)


@pytest.mark.parametrize(
    "filename",
    [
        "../outside.wav",
        "/private/sample.wav",
        "..\\sample.wav",
        "a\x00.wav",
        "<script>.wav",
        "sample.wav:stream",
    ],
)
def test_filename_traversal_and_unsafe_names_rejected(importer, filename):
    from flowlens.imports.staging import ImportFailure

    with pytest.raises(ImportFailure) as error:
        stage(importer, [upload(filename=filename)])
    assert error.value.issues[0].code == "INVALID_FILENAME"
    assert not list(importer[0].root.rglob("*.upload"))
    assert_no_domain(importer[0])


@pytest.mark.parametrize(
    "body,expected_code",
    [
        (b"<html>bad</html>", "CONTENT_MISMATCH"),
        (b"RIFF\x10\x00\x00\x00WAVE", "INVALID_AUDIO"),
        (b"", "EMPTY_FILE"),
    ],
)
def test_malformed_audio_is_rejected_and_cleaned(importer, body, expected_code):
    from flowlens.imports.staging import ImportFailure

    with pytest.raises(ImportFailure) as error:
        stage(importer, [upload(body)])
    assert error.value.issues[0].code == expected_code
    assert not list(importer[0].root.rglob("*.upload"))
    assert_no_domain(importer[0])


def audio_bytes(*, format="WAV", samples=None, channels=1, rate=16000, subtype="PCM_16"):
    output = io.BytesIO()
    frames = samples if samples is not None else [[0.0] * channels for _ in range(160)]
    soundfile.write(output, frames, rate, format=format, subtype=subtype)
    return output.getvalue()


def test_flac_is_fully_decoded_without_transforming_source(importer):
    body = audio_bytes(format="FLAC", channels=2)
    preview = stage(importer, [upload(body, filename="sample.flac", media_type="audio/flac")])
    assert (preview.files[0].channels, preview.files[0].duration_ms) == (2, 10)
    assert preview.files[0].sha256 == hashlib.sha256(body).hexdigest()
    assert next(importer[0].root.rglob("*.upload")).read_bytes() == body


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_float_audio_nonfinite_samples_rejected(importer, value):
    from flowlens.imports.staging import ImportFailure

    body = audio_bytes(samples=[value] * 160, subtype="FLOAT")
    with pytest.raises(ImportFailure) as error:
        stage(importer, [upload(body)])
    assert error.value.issues[0].code == "NONFINITE_AUDIO"


def test_size_duration_channels_and_hash_limits_rejected(importer):
    from flowlens.imports.staging import ImportFailure, ImportLimits

    service, *_ = importer
    service.limits = ImportLimits(
        max_file_bytes=1024 * 1024, max_total_bytes=2 * 1024 * 1024, max_duration_ms=5
    )
    with pytest.raises(ImportFailure) as error:
        stage(importer)
    assert error.value.issues[0].code == "DURATION_LIMIT"
    with pytest.raises(ImportFailure) as error:
        stage(importer, [upload(audio_bytes(channels=3))])
    assert error.value.issues[0].code == "CHANNEL_LIMIT"
    with pytest.raises(ImportFailure) as error:
        stage(importer, [upload(expected="0" * 64)])
    assert error.value.issues[0].code == "HASH_MISMATCH"
    with pytest.raises(ImportFailure) as error:
        stage(importer, [upload(b"x" * (1024 * 1024 + 1))])
    assert error.value.issues[0].code == "FILE_SIZE_LIMIT"
    assert not list(service.root.rglob("*.upload"))


def test_identical_retry_returns_same_preview_changed_payload_conflicts(importer):
    from flowlens.core.errors import ContractError

    first = stage(importer)
    assert stage(importer) == first
    with pytest.raises(ContractError, match="IDEMPOTENCY_CONFLICT"):
        stage(importer, [upload(audio_bytes())])
    assert len(list(importer[0].root.rglob("*.upload"))) == 1
    assert_no_domain(importer[0])


def test_typed_events_and_tracks_preview_contains_counts_not_payload(importer):
    files = [
        upload(),
        upload(
            Path("tests/fixtures/events/availability.json").read_bytes(),
            role="events",
            filename="events.json",
            media_type="application/json",
        ),
        upload(
            Path("tests/fixtures/events/track.json").read_bytes(),
            role="tracks",
            filename="tracks.json",
            media_type="application/json",
        ),
    ]
    preview = stage(importer, files)
    assert [item.row_count for item in preview.files] == [None, 3, 1]
    assert preview.tracks_present
    assert "Synthetic source instruction" not in preview.model_dump_json()
    assert_no_domain(importer[0])


@pytest.mark.parametrize(
    "body,code",
    [
        (b'[{"x":NaN}]', "NONFINITE_NUMBER"),
        (b'[{"x":1e999}]', "NONFINITE_NUMBER"),
        (b'[{"x":1,"x":2}]', "DUPLICATE_FIELD"),
        (b'[{"truth":"private"}]', "SCHEMA_MISMATCH"),
    ],
)
def test_json_sidecar_malformed_nonfinite_duplicate_and_truth_rejected(importer, body, code):
    from flowlens.imports.staging import ImportFailure

    with pytest.raises(ImportFailure) as error:
        stage(
            importer,
            [
                upload(),
                upload(body, role="events", filename="events.json", media_type="application/json"),
            ],
        )
    assert error.value.issues[0].code == code
    assert not list(importer[0].root.rglob("*.upload"))


def test_http_upload_preview_and_denials(tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings

    app = create_host(
        HostSettings(
            profile="test",
            database_path=tmp_path / "http.db",
            import_staging_path=tmp_path / "private-staging",
        )
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        initial, changed = (
            SecretStr("synthetic-import-initial"),
            SecretStr("synthetic-import-changed"),
        )
        account = app.state.accounts.bootstrap("admin", initial)
        app.state.accounts.change_password(account.id, initial, changed)
        auth = app.state.sessions.login("admin", changed, "local")
        client.cookies.set("flowlens_session", auth.token.get_secret_value())
        headers = {
            "Origin": app.state.settings.origin,
            "X-CSRF-Token": auth.csrf_token,
            "Idempotency-Key": "http-key",
        }
        body = Path("tests/fixtures/audio/hold-short.wav").read_bytes()
        first = client.post(
            "/api/v1/imports", files={"audio": ("sample.wav", body, "audio/wav")}, headers=headers
        )
        assert first.status_code == 201
        assert first.json()["status"] == "NEEDS_REMEDIATION"
        assert client.get("/api/v1/imports/" + first.json()["id"]).json() == first.json()
        assert (
            client.post(
                "/api/v1/imports",
                files={"audio": ("sample.wav", body, "audio/wav")},
                headers=headers,
            ).json()
            == first.json()
        )
        assert (
            client.post(
                "/api/v1/imports",
                files={"audio": ("other.wav", body, "audio/wav")},
                headers=headers,
            ).status_code
            == 409
        )
        missing_csrf = {key: value for key, value in headers.items() if key != "X-CSRF-Token"}
        assert (
            client.post(
                "/api/v1/imports",
                files={"audio": ("sample.wav", body, "audio/wav")},
                headers=missing_csrf,
            ).status_code
            == 403
        )
        invalid = client.post(
            "/api/v1/imports",
            files={"audio": ("../../private.wav", body, "audio/wav")},
            headers={**headers, "Idempotency-Key": "invalid"},
        )
        assert invalid.status_code == 422
        assert invalid.json()["code"] == "INVALID_IMPORT"
        assert "INVALID_FILENAME" in str(invalid.json()["field_issues"])
        assert "../../private" not in invalid.text
        assert first.headers["cache-control"] == "no-store"
        assert_no_domain(app.state.imports)
    assert app.state.imports is None


def test_jsonl_and_explicit_track_csv_profiles(importer):
    import csv

    events = json.loads(Path("tests/fixtures/events/availability.json").read_text())
    track = json.loads(Path("tests/fixtures/events/track.json").read_text())
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=[*track, "units"])
    writer.writeheader()
    writer.writerow({**track, "units": "m"})
    preview = stage(
        importer,
        [
            upload(),
            upload(
                ("\n".join(json.dumps(item) for item in events)).encode(),
                role="events",
                filename="events.jsonl",
                media_type="application/x-ndjson",
            ),
            upload(
                output.getvalue().encode(),
                role="tracks",
                filename="tracks.csv",
                media_type="text/csv",
            ),
        ],
    )
    assert [file.row_count for file in preview.files] == [None, 3, 1]


def test_csv_unknown_units_are_not_guessed(importer):
    import csv

    from flowlens.imports.staging import ImportFailure

    track = json.loads(Path("tests/fixtures/events/track.json").read_text())
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=[*track, "units"])
    writer.writeheader()
    writer.writerow({**track, "units": "feet"})
    with pytest.raises(ImportFailure) as error:
        stage(
            importer,
            [
                upload(),
                upload(
                    output.getvalue().encode(),
                    role="tracks",
                    filename="tracks.csv",
                    media_type="text/csv",
                ),
            ],
        )
    assert error.value.issues[0].code == "UNKNOWN_UNITS"


def test_truncated_wav_and_flac_fail_even_when_magic_is_correct(importer):
    from flowlens.imports.staging import ImportFailure

    for fmt, filename, mime in (
        ("WAV", "sample.wav", "audio/wav"),
        ("FLAC", "sample.flac", "audio/flac"),
    ):
        body = audio_bytes(format=fmt)
        with pytest.raises(ImportFailure):
            stage(importer, [upload(body[:-4], filename=filename, media_type=mime)], key=fmt)
    assert not list(importer[0].root.rglob("*.upload"))


def test_tamper_and_file_symlink_never_return_a_valid_preview(importer, tmp_path):
    from flowlens.imports.staging import ImportFailure

    service, auth, _ = importer
    preview = stage(importer)
    path = next(service.root.rglob("*.upload"))
    original = path.read_bytes()
    path.write_bytes(original[:-1] + b"x")
    with pytest.raises(ImportFailure, match="INVALID_IMPORT"):
        service.get(auth.token.get_secret_value(), preview.id)
    outside = tmp_path / "outside"
    outside.write_bytes(original)
    outside.chmod(0o600)
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ImportFailure):
        service.get(auth.token.get_secret_value(), preview.id)
    assert outside.read_bytes() == original


def test_owner_admin_expiry_and_revocation_are_rechecked(importer):
    from flowlens.core.errors import ContractError

    service, auth, now = importer
    preview = stage(importer)
    other = service.sessions.accounts.create(
        auth.account.id, "other", SecretStr("synthetic-other-initial"), is_admin=True
    )
    service.sessions.accounts.change_password(
        other.id, SecretStr("synthetic-other-initial"), SecretStr("synthetic-other-changed")
    )
    token = service.sessions.login(
        "other", SecretStr("synthetic-other-changed"), "local"
    ).token.get_secret_value()
    with pytest.raises(ContractError, match="ACCESS_DENIED"):
        service.get(token, preview.id)
    pending = service.start(auth.token.get_secret_value(), "revoked-key")
    sink = pending.add("audio", "sample.wav", "audio/wav")
    sink.write(audio_bytes())
    sink.seal()
    service.sessions.logout(auth.token.get_secret_value())
    try:
        with pytest.raises(ContractError, match="AUTH_REQUIRED"):
            pending.finish()
    finally:
        pending.abort()
    assert len(list(service.root.rglob("*.upload"))) == 1


def test_restart_recovers_partial_and_orphan_and_preserves_valid_preview(importer):
    from uuid import uuid4

    from flowlens.imports.staging import Imports

    service, auth, _ = importer
    first = stage(importer)
    pending = service.start(auth.token.get_secret_value(), "partial")
    sink = pending.add("audio", "partial.wav", "audio/wav")
    sink.write(b"partial")
    # Simulate process death: release fds/slots without executing abort cleanup.
    sink.close()
    os.close(pending.directory)
    pending.closed = True
    orphan = service.root / str(uuid4())
    orphan.mkdir(mode=0o700)
    (orphan / "opaque.upload").write_bytes(b"partial")
    service.close()
    reopened = Imports(service.database, service.sessions, service.root)
    try:
        assert reopened.get(auth.token.get_secret_value(), first.id) == first
        assert not orphan.exists()
        assert not (service.root / str(pending.id)).exists()
        assert len(list(service.root.rglob("*.upload"))) == 1
    finally:
        reopened.close()
    assert_no_domain(service)


def test_quota_bounded_and_existing_key_retry_still_works(importer):
    from flowlens.imports.staging import ImportFailure, ImportLimits

    service, *_ = importer
    service.limits = ImportLimits(max_owner_drafts=1)
    first = stage(importer)
    assert stage(importer) == first
    with pytest.raises(ImportFailure) as error:
        stage(importer, key="new-key")
    assert error.value.issues[0].code == "DRAFT_LIMIT"


def test_input_iteration_failure_and_unsealed_upload_are_cleaned(importer):
    from flowlens.imports.staging import ImportFailure, Upload

    def broken():
        yield b"RIFF"
        raise RuntimeError("synthetic interrupted upload")

    with pytest.raises(RuntimeError):
        stage(importer, [Upload("audio", "sample.wav", "audio/wav", broken())])
    service, auth, _ = importer
    pending = service.start(auth.token.get_secret_value(), "partial")
    pending.add("audio", "sample.wav", "audio/wav").write(audio_bytes())
    try:
        with pytest.raises(ImportFailure) as error:
            pending.finish()
        assert error.value.issues[0].code == "INCOMPLETE_UPLOAD"
    finally:
        pending.abort()
    assert not list(service.root.rglob("*.upload"))


def test_staging_root_symlink_and_insecure_permissions_rejected(importer, tmp_path):
    from flowlens.imports.staging import Imports

    service, *_ = importer
    alias = tmp_path / "alias"
    alias.symlink_to(service.root, target_is_directory=True)
    with pytest.raises(ValueError):
        Imports(service.database, service.sessions, alias)
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(ValueError):
        Imports(service.database, service.sessions, public)


def test_multipart_does_not_silently_strip_windows_paths(importer):
    from flowlens.imports.routes import MultipartUpload
    from flowlens.imports.staging import ImportFailure

    service, auth, _ = importer
    pending = service.start(auth.token.get_secret_value(), "windows-path")
    parser = MultipartUpload(pending, b"boundary")
    body = (
        b'--boundary\r\nContent-Disposition: form-data; name="audio"; '
        b'filename="C:\\private\\sample.wav"\r\nContent-Type: audio/wav\r\n'
        b"\r\nRIFF\r\n--boundary--\r\n"
    )
    try:
        with pytest.raises(ImportFailure) as error:
            parser.feed(body)
        assert error.value.issues[0].code == "INVALID_FILENAME"
    finally:
        pending.abort()


def test_decoder_does_not_inherit_host_secrets(importer, monkeypatch):
    from flowlens.imports import inspection

    real_run = inspection.subprocess.run
    monkeypatch.setenv("FLOWLENS_WORKER_TOKEN", "synthetic-private-token")

    def checked_run(*args, **kwargs):
        assert "FLOWLENS_WORKER_TOKEN" not in kwargs["env"]
        assert "PYTHONPATH" not in kwargs["env"]
        return real_run(*args, **kwargs)

    monkeypatch.setattr(inspection.subprocess, "run", checked_run)
    assert stage(importer).files[0].frames == 128343


def test_incomplete_multipart_and_decoder_timeout_clean_staging(importer, monkeypatch):
    from flowlens.imports import inspection
    from flowlens.imports.routes import MultipartUpload
    from flowlens.imports.staging import ImportFailure

    service, auth, _ = importer
    pending = service.start(auth.token.get_secret_value(), "unfinished-http")
    parser = MultipartUpload(pending, b"boundary")
    try:
        parser.feed(
            b'--boundary\r\nContent-Disposition: form-data; name="audio"; '
            b'filename="sample.wav"\r\nContent-Type: audio/wav\r\n\r\nRIFF'
        )
        with pytest.raises(ImportFailure) as error:
            parser.finish()
        assert error.value.issues[0].code == "INCOMPLETE_UPLOAD"
    finally:
        pending.abort()

    def timeout_run(*args, **kwargs):
        raise inspection.subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(inspection.subprocess, "run", timeout_run)
    with pytest.raises(ImportFailure) as error:
        stage(importer)
    assert error.value.issues[0].code == "DECODER_TIMEOUT"
    assert not list(service.root.rglob("*.upload"))
    assert_no_domain(service)


def test_expired_draft_is_unavailable_and_removed_on_restart(importer):
    from flowlens.core.errors import ContractError
    from flowlens.imports.staging import Imports

    service, auth, clock = importer
    preview = stage(importer)
    clock[0] = preview.expires_ms
    auth = service.sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
    with pytest.raises(ContractError) as error:
        service.get(auth.token.get_secret_value(), preview.id)
    assert error.value.code == "EVIDENCE_UNAVAILABLE"
    with pytest.raises(ContractError) as error:
        service.stage(auth.token.get_secret_value(), "synthetic-key", [upload()])
    assert error.value.code == "EVIDENCE_UNAVAILABLE"
    service.close()
    restarted = Imports(service.database, service.sessions, service.root)
    try:
        assert not list(restarted.root.rglob("*.upload"))
        with service.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_import_drafts").fetchone()[0]
                == 0
            )
    finally:
        restarted.close()
