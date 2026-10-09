"""Opt-in measured A10 platform capacity, real host/SQLite, frozen fake analysis.

FLOWLENS_RUN_CAPACITY=1 enables the disposable large fixture, never cloud calls.
The report contains measurements, not private files or credentials.
"""

import hashlib
import json
import math
import os
import platform
import sqlite3
import subprocess
import sys
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import ModuleRegistration
from flowlens.imports.metadata import ImportMetadata
from flowlens.imports.staging import ImportLimits, Upload
from flowlens.testing.harness import FakeAnalysis
from pydantic import SecretStr
from test_import_metadata import request

ORIGIN = "http://127.0.0.1:8000"


def distribution(values):
    ordered = sorted(values)
    return {
        "count": len(values),
        "p50_ms": ordered[math.ceil(len(values) * 0.5) - 1],
        "p95_ms": ordered[math.ceil(len(values) * 0.95) - 1],
        "max_ms": max(values),
        "samples_ms": values,
    }


def file_upload(path, role="audio"):
    def chunks():
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                yield block

    return Upload(role, path.name, "audio/wav" if role == "audio" else "application/json", chunks())


def audio(path, seconds):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        block = b"\0" * 32000
        for _ in range(seconds):
            stream.writeframesraw(block)


@pytest.mark.skipif(os.getenv("FLOWLENS_RUN_CAPACITY") != "1", reason="opt-in full capacity run")
def test_measured_platform_capacity(tmp_path):
    fake = FakeAnalysis()
    app = create_host(
        HostSettings(
            profile="test",
            database_path=tmp_path / "db" / "data.db",
            import_staging_path=tmp_path / "imports",
            raw_assets_path=tmp_path / "raw",
            artifact_staging_path=tmp_path / "artifacts",
            retention_journal_path=tmp_path / "journal" / "current.db",
        ),
        modules=[
            ModuleRegistration(name="acceptance-fake-b", mock=True, snapshot_reader=fake.snapshot)
        ],
    )
    report = {
        "fixture": "a10-capacity-1",
        "date_local": datetime.now(ZoneInfo("Asia/Jakarta")).isoformat(),
        "measured_source_sha256": {
            p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in [
                "backend/flowlens/api/host.py",
                "backend/flowlens/replay/snapshots.py",
                "backend/flowlens/replay/views.py",
                "backend/flowlens/replay/controls.py",
                "backend/flowlens/imports/staging.py",
                "uv.lock",
                "tests/platform/test_acceptance_capacity.py",
            ]
        },
        "input_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "environment": {
            "os": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version,
            "sqlite": sqlite3.sqlite_version,
            "cpu_count": os.cpu_count(),
            "cpu": subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip(),
            "memory_bytes": int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)),
        },
        "method": (
            "real host lifespan/SQLite WAL; 5 concurrent ASGI clients, "
            "nearest-rank percentiles; no network/browser/provider"
        ),
        "thresholds_ms": {
            "list_p95": 500,
            "snapshot_p95": 500,
            "seek_p95": 1000,
            "resync_max": 3000,
        },
        "workload": {
            "sessions": 100,
            "objects": 20,
            "replay_ms": 3600000,
            "track_cadence_ms": 60000,
            "track_rows": 1220,
            "audio_channels": 2,
            "seconds_per_channel": 3600,
            "aggregate_channel_seconds": 7200,
            "sample_rate_hz": 16000,
            "pcm_bits": 16,
        },
        "limits": [
            "Synthetic silence is not speech/domain evidence",
            "60-second observed samples do not prove 1Hz or higher throughput",
            "ASGI timings exclude LAN/browser/TLS",
            "5 logical clients share one authorized account",
            "No provider calls; no B semantics; no VM/off-host RPO/RTO measurement",
        ],
    }
    with TestClient(app, base_url=ORIGIN) as client:
        admin = app.state.accounts.bootstrap("capacity", SecretStr("synthetic-capacity-initial"))
        app.state.accounts.change_password(
            admin.id,
            SecretStr("synthetic-capacity-initial"),
            SecretStr("synthetic-capacity-changed"),
        )
        auth = app.state.sessions.login(
            "capacity", SecretStr("synthetic-capacity-changed"), "local"
        )
        token = auth.token.get_secret_value()
        client.cookies.set("flowlens_session", token)
        headers = {"Origin": ORIGIN, "X-CSRF-Token": auth.csrf_token}
        # Import retention allows 100 archived sessions independently of draft quota.
        app.state.imports.limits = ImportLimits(max_owner_drafts=100)
        report["import_limits"] = app.state.imports.limits.model_dump()
        tiny = tmp_path / "tiny.wav"
        audio(tiny, 1)
        channels = [tmp_path / f"channel{n}.wav" for n in range(2)]
        generation = perf_counter()
        for path in channels:
            audio(path, 3600)
        report["audio_generation_ms"] = (perf_counter() - generation) * 1000
        template = json.loads(Path("tests/fixtures/events/track.json").read_text())
        tracks = []
        for time_ms in range(0, 3600001, 60000):
            for entity in range(1, 21):
                index = len(tracks) + 100
                tracks.append(
                    {
                        **template,
                        "id": str(UUID(int=index)),
                        "source_event_id": f"track-{index}",
                        "entity_id": str(UUID(int=entity)),
                        "event_time_ms": time_ms,
                        "available_time_ms": time_ms,
                        "x_m": float(entity * 10),
                        "statement": "Synthetic capacity observation",
                    }
                )
        trackfile = tmp_path / "tracks.json"
        trackfile.write_text(json.dumps(tracks))
        import_times = []
        for n in range(100):
            started = perf_counter()
            files = (
                [file_upload(p) for p in channels] + [file_upload(trackfile, "tracks")]
                if n == 0
                else [file_upload(tiny)]
            )
            preview = app.state.imports.stage(token, f"capacity-{n}", files)

            def modify(data, n=n, preview=preview):
                data["source_identifier"] = f"capacity-{n}"
                for index, f in enumerate(data["files"]):
                    f["clock"] = {
                        "timezone": "UTC",
                        "method": "DECLARED_OFFSET",
                        "offset_ms": 0,
                        "uncertainty_ms": 0,
                        "basis": "synthetic clock",
                        "reviewer": "fixture",
                    }
                    f["channels"] = (
                        [f"radio-{index}"] if preview.files[index].role == "audio" else []
                    )
                if n == 0:
                    data["identities"] = [
                        {
                            "source_entity_id": str(UUID(int=e)),
                            "callsign": f"CAP{e}",
                            "evidence_file_id": str(preview.files[2].id),
                            "evidence_record_ids": [f"track-{99 + e}"],
                            "aliases": [],
                            "validity": {"start_ms": 0, "end_ms": 3600001},
                        }
                        for e in range(1, 21)
                    ]

            prepared = ImportMetadata(app.state.imports).prepare(
                token, preview.id, f"metadata-{n}", request(preview, modify=modify)
            )
            receipt = app.state.import_commits.commit(
                token, preview.id, prepared.revision, f"commit-{n}"
            )
            assert not receipt.deduplicated
            app.state.permissions.grant(
                token,
                admin.id,
                receipt.session_id,
                "read",
                role="evaluator",
                expires_ms=app.state.sessions.clock() + 86400000,
            )
            if n == 0:
                sid = receipt.session_id
                assets = prepared.manifest.assets
                assert [f.duration_ms for f in prepared.files if f.role == "audio"] == [
                    3600000,
                    3600000,
                ]
                app.state.permissions.grant(
                    token,
                    admin.id,
                    sid,
                    "audio",
                    role="evaluator",
                    expires_ms=app.state.sessions.clock() + 86400000,
                )
                report["audio_bytes"] = [p.stat().st_size for p in channels]
                report["audio_hashes"] = [
                    hashlib.sha256(p.read_bytes()).hexdigest() for p in channels
                ]
            import_times.append((perf_counter() - started) * 1000)
        report["imports"] = distribution(import_times)
        assert len(client.get("/api/v1/sessions?limit=100").json()["items"]) == 100
        for item, path in zip(assets[:2], channels, strict=True):
            reply = client.get(
                f"/api/v1/assets/{item.id}/audio",
                headers={"Range": f"bytes={path.stat().st_size - 64}-"},
            )
            assert reply.status_code == 206 and reply.content == path.read_bytes()[-64:]
        assert client.get(f"/api/v1/sessions/{UUID(int=999999)}/snapshot").status_code == 403
        version = 0
        seek_times = []
        for index in range(30):
            position = (index * 137173) % 3600001 if index < 29 else 3600000
            started = perf_counter()
            reply = client.post(
                f"/api/v1/sessions/{sid}/playback",
                json={
                    "action": "SEEK",
                    "view": "LOCAL",
                    "value": position,
                    "expected_version": version,
                    "key": f"seek-{index}",
                },
                headers=headers,
            )
            assert reply.status_code == 200
            version = reply.json()["version"]
            reply = client.get(f"/api/v1/sessions/{sid}/snapshot?view=LOCAL&mode=AS_KNOWN")
            assert reply.status_code == 200
            assert all(e["event_time_ms"] <= position for e in reply.json()["events"])
            seek_times.append((perf_counter() - started) * 1000)
        assert len(reply.json()["events"]) == 1220
        assert len({e["entity_id"] for e in reply.json()["events"]}) == 20
        report["seek"] = distribution(seek_times)
        if os.getenv("FLOWLENS_PROFILE_CAPACITY") == "1":
            import cProfile

            profile = cProfile.Profile()
            from flowlens.replay.views import Views

            profile.runcall(Views(app.state.controls).snapshot, token, sid, "LOCAL", "AS_KNOWN")
            profile.dump_stats("artifacts/reports/a101-replay.prof")

        def requests(kind):
            url = (
                "/api/v1/sessions?limit=100"
                if kind == "list"
                else f"/api/v1/sessions/{sid}/snapshot?view=LOCAL&mode=AS_KNOWN"
            )
            values = []
            for _ in range(10):
                started = perf_counter()
                response = client.get(url)
                assert response.status_code == 200
                assert len(response.json()["items" if kind == "list" else "events"]) == (
                    100 if kind == "list" else 1220
                )
                values.append((perf_counter() - started) * 1000)
            return values

        for kind in ("list", "snapshot"):
            with ThreadPoolExecutor(max_workers=5) as pool:
                samples = list(pool.map(requests, [kind] * 5))
            report[kind] = distribution([value for group in samples for value in group])
        started = perf_counter()
        with client.websocket_connect(
            f"/api/v1/sessions/{sid}/stream?view=LOCAL&after_sequence=99999",
            headers={"Origin": ORIGIN},
        ) as ws:
            assert ws.receive_json()["type"] == "RESYNC_REQUIRED"
            restored = ws.receive_json()
            assert restored["type"] == "SNAPSHOT" and len(restored["payload"]["events"]) == 1220
        report["resync_ms"] = (perf_counter() - started) * 1000
        report["provider_calls"] = 0
        report["passed"] = all(
            [
                report["list"]["p95_ms"] <= 500,
                report["snapshot"]["p95_ms"] <= 500,
                report["seek"]["p95_ms"] <= 1000,
                report["resync_ms"] <= 3000,
            ]
        )
        target = Path(
            os.getenv("FLOWLENS_CAPACITY_REPORT", "artifacts/reports/a101-benchmark.json")
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n")
        assert report["passed"], {
            k: v for k, v in report.items() if k in ("list", "snapshot", "seek", "resync_ms")
        }
