"""A04 final commit and recovery acceptance, synthetic files/disposable DB only."""

from pathlib import Path

import pytest
from test_import_metadata import prepare, request
from test_imports import importer as importer
from test_imports import stage, upload


@pytest.fixture
def committed(importer, tmp_path):
    from flowlens.assets.storage import PrivateFiles
    from flowlens.auth.permissions import Permissions
    from flowlens.imports.commit import ImportCommit
    from flowlens.sources.store import Sources

    imports, auth, clock = importer
    permissions = Permissions(imports.database, imports.sessions)
    imports.database.context_guard = permissions.enforce
    files = PrivateFiles(tmp_path / "raw")
    sources = Sources(imports.database, permissions, files)
    commits = ImportCommit(imports, files)
    try:
        yield commits, sources, permissions, auth, clock
    finally:
        files.close()


def ready(importer, files=None):
    preview = stage(importer, files)

    def clocks(d):
        for f in d["files"]:
            f["clock"] = {
                "timezone": "UTC",
                "method": "DECLARED_OFFSET",
                "offset_ms": 0,
                "uncertainty_ms": 10,
                "basis": "synthetic calibration",
                "reviewer": "fixture",
            }

    prepared = prepare(importer, preview, request(preview, modify=clocks))
    return preview, prepared


def commit(c, preview, prepared, *, key="commit-key"):
    return c[0].commit(c[3].token.get_secret_value(), preview.id, prepared.revision, key)


def context(c, result, *, run=None, capabilities=("read", "audio", "analysis", "export")):
    _, _, permissions, auth, clock = c
    for capability in capabilities:
        permissions.grant(
            auth.token.get_secret_value(),
            auth.account.id,
            result.session_id,
            capability,
            role="evaluator",
            expires_ms=clock[0] + 1000000,
        )
    return permissions.human_context(auth.token.get_secret_value(), result.session_id, run_id=run)


def test_audio_commit_roundtrip_private_raw_and_explicit_grants(importer, committed):
    preview, prepared = ready(importer)
    result = commit(committed, preview, prepared)
    assert result.session_id == prepared.manifest.session_id
    ctx = context(committed, result)
    manifest = committed[1].manifest(ctx, result.source_id)
    assert manifest.assets[0].sha256 == preview.files[0].sha256
    assert committed[1].read_events(ctx) == []
    assert str(committed[0].files.root) not in result.model_dump_json()
    raw = list(committed[0].files.root.rglob("*.raw"))
    assert (
        len(raw) == 1
        and raw[0].read_bytes() == Path("tests/fixtures/audio/hold-short.wav").read_bytes()
    )
    assert raw[0].stat().st_mode & 0o222 == 0
    assert commit(committed, preview, prepared) == result
    with importer[0].database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_sessions").fetchone()[0] == 1
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_grants").fetchone()[0] == 4


@pytest.mark.parametrize("boundary", ["after_copy", "after_promotion", "before_db_commit"])
def test_precommit_fault_leaves_no_readable_session_or_orphan(importer, committed, boundary):
    preview, prepared = ready(importer)

    def fail(phase):
        if phase == boundary:
            raise RuntimeError("synthetic crash boundary")

    committed[0].fault = fail
    with pytest.raises(RuntimeError):
        commit(committed, preview, prepared)
    with importer[0].database.begin() as uow:
        for table in (
            "platform_sessions",
            "platform_sources",
            "platform_assets",
            "platform_import_commits",
        ):
            assert uow.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert not list(committed[0].files.root.rglob("*.raw"))


def test_postcommit_failure_retry_and_recovery_preserve_committed_files(importer, committed):
    preview, prepared = ready(importer)

    def fail(phase):
        if phase == "after_db_commit":
            raise RuntimeError("synthetic lost response")

    committed[0].fault = fail
    with pytest.raises(RuntimeError):
        commit(committed, preview, prepared)
    committed[0].fault = lambda _: None
    result = commit(committed, preview, prepared)
    orphan = committed[0].files.root / "00000000-0000-0000-0000-000000000123"
    orphan.mkdir(mode=0o700)
    (orphan / "discard.raw").write_bytes(b"synthetic orphan")
    committed[0].recover()
    assert not orphan.exists()
    assert (
        committed[1].manifest(context(committed, result), result.source_id).source_hash
        == prepared.content_hash
    )


def test_paired_observed_records_are_normalized_and_as_of_filtered(importer, committed):
    preview, prepared = ready(
        importer,
        [
            upload(),
            upload(
                Path("tests/fixtures/events/availability.json").read_bytes(),
                role="events",
                filename="events.json",
                media_type="application/json",
            ),
        ],
    )
    result = commit(committed, preview, prepared)
    ctx = context(committed, result)
    events = committed[1].read_events(ctx)
    assert len(events) == 3
    assert all(
        row.session_id == result.session_id and row.source_id == result.source_id for row in events
    )
    assert all(row.analysis_run_id is None for row in events)
    with importer[0].database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_context_state SET mode='AS_KNOWN',as_of_ms=150 WHERE session_id=?",
            (str(result.session_id),),
        )
        uow.commit()
    fresh = committed[2].human_context(committed[3].token.get_secret_value(), result.session_id)
    assert all(
        row.available_time_ms is not None and row.available_time_ms <= 150
        for row in committed[1].read_events(fresh)
    )


def test_unknown_alignment_is_archived_without_fabricated_timed_rows(importer, committed):
    preview = stage(
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
    prepared = prepare(importer, preview)
    result = commit(committed, preview, prepared)
    assert committed[1].read_events(context(committed, result)) == []
    assert (
        committed[1].manifest(context(committed, result), result.source_id).clock.offset_ms is None
    )


def test_duplicate_identical_dedup_and_changed_source_conflict(importer, committed):
    from flowlens.imports.staging import ImportFailure

    first, p1 = ready(importer)
    r1 = commit(committed, first, p1)
    service, auth, _ = importer
    second = service.stage(auth.token.get_secret_value(), "second-upload", [upload()])

    def clocks(d):
        d["files"][0]["clock"] = p1.declaration.files[0].clock.model_dump(mode="json")

    p2 = prepare(importer, second, request(second, modify=clocks), key="second-metadata")
    r2 = commit(committed, second, p2, key="second-commit")
    assert r2.session_id == r1.session_id and r2.deduplicated
    third = service.stage(auth.token.get_secret_value(), "third-upload", [upload()])
    p3 = prepare(
        importer,
        third,
        request(third, modify=lambda d: d.update(source_label="Changed declaration")),
        key="third-metadata",
    )
    with pytest.raises(ImportFailure) as error:
        commit(committed, third, p3, key="third-commit")
    assert error.value.issues[0].code == "DUPLICATE_SOURCE_CONFLICT"


def test_source_rights_revision_is_live_and_no_automatic_grants(importer, committed):
    from flowlens.core.errors import ContractError

    preview, prepared = ready(importer)
    result = commit(committed, preview, prepared)
    with pytest.raises(ContractError):
        committed[2].human_context(committed[3].token.get_secret_value(), result.session_id)
    ctx = context(committed, result)
    rights = prepared.declaration.rights.model_copy(update={"local": "DENIED"})
    committed[1].set_rights(
        committed[3].token.get_secret_value(),
        result.session_id,
        result.source_id,
        rights,
        expected_version=1,
    )
    with pytest.raises(ContractError):
        committed[1].manifest(ctx, result.source_id)


def test_http_commit_is_configured_authenticated_and_stable(tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings
    from flowlens.imports.staging import ImportPreview
    from pydantic import SecretStr
    from test_import_metadata import declaration

    app = create_host(
        HostSettings(
            profile="test",
            database_path=tmp_path / "db" / "http.db",
            import_staging_path=tmp_path / "staging",
            raw_assets_path=tmp_path / "raw",
        )
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        initial, changed = (
            SecretStr("synthetic-import-initial"),
            SecretStr("synthetic-import-changed"),
        )
        admin = app.state.accounts.bootstrap("admin", initial)
        app.state.accounts.change_password(admin.id, initial, changed)
        auth = app.state.sessions.login("admin", changed, "local")
        client.cookies.set("flowlens_session", auth.token.get_secret_value())
        headers = {
            "Origin": app.state.settings.origin,
            "X-CSRF-Token": auth.csrf_token,
            "Idempotency-Key": "upload",
        }
        p = client.post(
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
        preview = ImportPreview.model_validate_json(p.text)
        base = f"/api/v1/imports/{preview.id}"
        headers["Idempotency-Key"] = "metadata"
        assert (
            client.post(
                base + "/metadata",
                headers=headers,
                json={"expected_revision": 0, "declaration": declaration(preview)},
            ).status_code
            == 201
        )
        headers["Idempotency-Key"] = "commit"
        result = client.post(base + "/commit", headers=headers, json={"expected_revision": 1})
        assert result.status_code == 201
        assert (
            result.json()
            == client.post(base + "/commit", headers=headers, json={"expected_revision": 1}).json()
        )
        assert result.headers["Cache-Control"] == "no-store"
        assert (
            client.post(
                base + "/commit",
                headers={"Origin": app.state.settings.origin},
                json={"expected_revision": 1},
            ).status_code
            == 403
        )
        oversized = client.post(
            base + "/commit",
            headers={**headers, "Content-Type": "application/json"},
            content=b'{"expected_revision":1}' + b" " * 4096,
        )
        assert oversized.status_code == 422
        assert app.state.sources is not None
    assert app.state.raw_files is None


def test_committed_observation_and_assets_sql_replacement_rejected(importer, committed):
    import sqlite3

    preview, prepared = ready(
        importer,
        [
            upload(),
            upload(
                Path("tests/fixtures/events/availability.json").read_bytes(),
                role="events",
                filename="events.json",
                media_type="application/json",
            ),
        ],
    )
    result = commit(committed, preview, prepared)
    for sql in (
        "UPDATE platform_assets SET storage_key='unsafe'",
        "INSERT OR REPLACE INTO platform_sources SELECT * FROM platform_sources",
        "INSERT OR REPLACE INTO platform_records SELECT * FROM platform_records",
    ):
        with importer[0].database.begin() as uow:
            with pytest.raises(sqlite3.DatabaseError):
                uow.connection.execute(sql)
    assert (
        committed[1].manifest(context(committed, result), result.source_id).source_hash
        == prepared.content_hash
    )


@pytest.mark.parametrize(
    "boundary,expected", [("after_copy", 0), ("after_promotion", 0), ("after_db_commit", 1)]
)
def test_process_exit_at_durability_boundary_recovers(tmp_path, boundary, expected):
    import subprocess
    import sys

    from flowlens.assets.storage import PrivateFiles
    from flowlens.auth.accounts import Accounts
    from flowlens.auth.sessions import Sessions
    from flowlens.imports.commit import ImportCommit
    from flowlens.imports.staging import Imports
    from flowlens.storage.sqlite.database import Database

    script = tmp_path / "crash.py"
    script.write_text("""import os,sys
from pathlib import Path
from pydantic import SecretStr
from flowlens.auth.accounts import Accounts
from flowlens.auth.sessions import Sessions
from flowlens.storage.sqlite.database import Database
from flowlens.imports.staging import Imports,Upload
from flowlens.imports.metadata import ImportMetadata,MetadataRequest
from flowlens.imports.commit import ImportCommit
from flowlens.assets.storage import PrivateFiles
import json
root=Path(sys.argv[1]);phase=sys.argv[2]
db=Database(root/"db"/"data.db");accounts=Accounts(db)
a=accounts.bootstrap("admin",SecretStr("synthetic-import-initial"))
accounts.change_password(a.id,SecretStr("synthetic-import-initial"),SecretStr("synthetic-import-changed"))
sessions=Sessions(db,accounts,clock=lambda:1000)
auth=sessions.login("admin",SecretStr("synthetic-import-changed"),"local")
imports=Imports(db,sessions,root/"staging");raw=PrivateFiles(root/"raw")
body=Path("tests/fixtures/audio/hold-short.wav").read_bytes()
p=imports.stage(auth.token.get_secret_value(),"upload",[Upload("audio","sample.wav","audio/wav",[body])])
d={"source_kind":"SYNTHETIC","source_label":"synthetic crash fixture",
"source_owner":"fixture","source_identifier":"crash",
"rights":{"local":"ALLOWED","cloud_audio":"DENIED","cloud_context":"DENIED",
"reviewer":"ALLOWED","export":"DENIED","audio_export":"DENIED","basis":"synthetic"},
"retention":{"policy":"FIXED_DAYS","days":30,"basis":"synthetic"},
"files":[{"file_id":str(p.files[0].id),"sha256":p.files[0].sha256,
"channels":["radio"],"clock":{"timezone":"UTC"}}],
"coverage":{},"identities":[],"layout":None}
metadata=ImportMetadata(imports).prepare(auth.token.get_secret_value(),p.id,"metadata",MetadataRequest.model_validate_json(json.dumps({"expected_revision":0,"declaration":d})))
commits=ImportCommit(imports,raw)
commits.fault=lambda current:os._exit(91) if current==phase else None
commits.commit(auth.token.get_secret_value(),p.id,1,"commit")
""")
    assert (
        subprocess.run(
            [sys.executable, str(script), str(tmp_path / "state"), boundary],
            capture_output=True,
            timeout=30,
        ).returncode
        == 91
    )
    with Database(tmp_path / "state" / "db" / "data.db") as db:
        imports = Imports(
            db, Sessions(db, Accounts(db), clock=lambda: 1000), tmp_path / "state" / "staging"
        )
        raw = PrivateFiles(tmp_path / "state" / "raw")
        try:
            ImportCommit(imports, raw)
            with db.begin() as uow:
                assert (
                    uow.connection.execute("SELECT COUNT(*) FROM platform_sessions").fetchone()[0]
                    == expected
                )
                assert not uow.connection.execute("PRAGMA foreign_key_check").fetchall()
            assert len(list(raw.root.rglob("*.raw"))) == expected
        finally:
            raw.close()
            imports.close()


def test_metadata_changed_during_copy_cannot_publish_stale_declaration(importer, committed):
    from flowlens.core.errors import ContractError

    preview, prepared = ready(importer)

    def race(phase):
        if phase == "after_promotion":
            prepare(importer, preview, request(preview, expected=1), key="new-metadata")

    committed[0].fault = race
    with pytest.raises(ContractError) as error:
        commit(committed, preview, prepared)
    assert error.value.code == "VERSION_CONFLICT"
    assert not list(committed[0].files.root.rglob("*.raw"))
    with importer[0].database.begin() as uow:
        assert uow.connection.execute("SELECT COUNT(*) FROM platform_sessions").fetchone()[0] == 0
