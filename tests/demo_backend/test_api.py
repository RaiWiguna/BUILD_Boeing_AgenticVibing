"""API tests against a disposable PostgreSQL database (DEMO_TEST_DATABASE_URL).

Run inside Compose: docker compose -f deploy/compose/local/compose.demo.yml --profile test run --rm api-test
"""

import json
import os
import time
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
from fastapi.testclient import TestClient  # noqa: E402
from flowlens_demo.app import create_app  # noqa: E402

DB_URL = os.environ.get("DEMO_TEST_DATABASE_URL")
ROOT = Path(os.environ.get("DEMO_SCENARIO_ROOT", "/scenarios"))
SCENARIO = ROOT / "kagc-2022-09-10-88"
AUDIO = SCENARIO / "88.wav"
ADSB = SCENARIO / "kagc_adsb_2022-09-10_88.csv"
AUDIO_87 = SCENARIO / "87.wav"
ADSB_87 = SCENARIO / "kagc_adsb_2022-09-10_87.csv"
OFFSET_88 = 168_007

pytestmark = pytest.mark.skipif(
    not DB_URL or not AUDIO.exists(),
    reason="needs DEMO_TEST_DATABASE_URL and prepared scenario assets",
)


def reset_db():
    assert DB_URL and DB_URL.rsplit("/", 1)[-1].endswith("_test"), (
        "refusing to reset a non-test database"
    )
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute(
            "DROP TABLE IF EXISTS playback_state, findings, transcript_segments, workspace_files, workspaces CASCADE"
        )


@pytest.fixture()
def client():
    reset_db()
    with TestClient(create_app(DB_URL, str(ROOT), processing_scale=0.002)) as c:
        yield c


def part(path, kind="audio/wav"):
    return ("files", (path.name, path.read_bytes(), kind))


def upload(client, name="KAGC demo", files=None, positions=None):
    files = files or [part(AUDIO), part(ADSB, "text/csv")]
    data = {"name": name}
    if positions:
        data["positions"] = json.dumps(positions)
    return client.post("/api/demo/workspaces", data=data, files=files)


def wait_ready(client, wid):
    for _ in range(50):
        body = client.get(f"/api/demo/workspaces/{wid}").json()
        if body["status"] == "READY":
            return body
        time.sleep(0.02)
    raise AssertionError("workspace did not become READY")


def test_health(client):
    body = client.get("/api/demo/health").json()
    assert (
        body["database"] is True
        and body["scenarios"] == 6
        and body["profile"] == "demo"
    )


def test_upload_processes_and_stores_workspace(client):
    res = upload(client)
    assert res.status_code == 201, res.text
    ws = res.json()
    assert ws["status"] == "PROCESSING"
    assert [s["key"] for s in ws["steps"]][:5] == [
        "upload",
        "checksum",
        "audio",
        "vad",
        "adsb",
    ]
    assert "mock" not in ws["steps"][0]
    adsb = next(f for f in ws["files"] if f["role"] == "adsb")
    assert adsb["detected"]["icao_ids"] == 3 and adsb["detected"]["label"] == "ADS-B"
    audio = next(f for f in ws["files"] if f["role"] == "audio")
    assert (
        audio["detected"]["sample_rate_hz"] == 44100
        and audio["detected"]["format"] == "IEEE float"
    )

    ready = wait_ready(client, ws["id"])
    assert all(s["status"] == "DONE" for s in ready["steps"])
    analysis = client.get(f"/api/demo/workspaces/{ws['id']}/analysis").json()
    assert analysis["spec"]["title"] == "KAGC demo"
    assert (
        len(analysis["spec"]["segments"]) == 7
        and len(analysis["spec"]["findings"]) == 8
    )
    assert "loops" not in analysis["spec"]
    assert "MOCK" not in analysis["labels"]
    assert [r["part"] for r in analysis["recordings"]] == ["88"]
    assert analysis["recordings"][0]["audio_url"].endswith("/audio/88")

    # Finalisation happens once even when read repeatedly.
    client.get(f"/api/demo/workspaces/{ws['id']}")
    with psycopg.connect(DB_URL) as conn:
        assert conn.execute("SELECT count(*) FROM findings").fetchone()[0] == 8
        assert (
            conn.execute("SELECT count(*) FROM transcript_segments").fetchone()[0] == 7
        )
    assert [w["id"] for w in client.get("/api/demo/workspaces").json()] == [ws["id"]]


def test_unknown_file_name_is_rejected(client):
    files = [
        ("files", ("tower.wav", b"RIFF", "audio/wav")),
        ("files", (ADSB.name, ADSB.read_bytes(), "text/csv")),
    ]
    res = upload(client, files=files)
    assert res.status_code == 422 and res.json()["details"]["code"] == "UNKNOWN_FILE"


def test_known_name_with_different_content_is_rejected(client):
    files = [
        ("files", ("88.wav", AUDIO.read_bytes()[:-10], "audio/wav")),
        ("files", (ADSB.name, ADSB.read_bytes(), "text/csv")),
    ]
    res = upload(client, files=files)
    assert (
        res.status_code == 422 and res.json()["details"]["code"] == "CHECKSUM_MISMATCH"
    )


def test_main_recording_needs_its_adsb_file(client):
    res = upload(client, files=[("files", ("88.wav", AUDIO.read_bytes(), "audio/wav"))])
    assert res.status_code == 422 and res.json()["details"]["code"] == "MISSING_ROLE"


def test_duplicate_name_case_insensitive(client):
    assert upload(client, "Demo One").status_code == 201
    res = upload(client, "demo one")
    assert res.status_code == 409 and res.json()["code"] == "NAME_TAKEN"


def test_analysis_before_ready_is_409():
    reset_db()
    with TestClient(create_app(DB_URL, str(ROOT), processing_scale=50.0)) as slow:
        wid = upload(slow).json()["id"]
        res = slow.get(f"/api/demo/workspaces/{wid}/analysis")
        assert res.status_code == 409 and res.json()["code"] == "NOT_READY"
        assert slow.get(f"/api/demo/workspaces/{wid}/audio").status_code == 409


def test_processing_survives_api_restart():
    reset_db()
    with TestClient(create_app(DB_URL, str(ROOT), processing_scale=0.002)) as first:
        wid = upload(first).json()["id"]
    time.sleep(0.1)
    with TestClient(create_app(DB_URL, str(ROOT), processing_scale=0.002)) as second:
        assert second.get(f"/api/demo/workspaces/{wid}").json()["status"] == "READY"


def test_audio_supports_ranges(client):
    wid = wait_ready(client, upload(client).json()["id"])["id"]
    size = (SCENARIO / "derived" / "88.pcm16.wav").stat().st_size
    full = client.get(f"/api/demo/workspaces/{wid}/audio")
    assert (
        full.status_code == 200
        and len(full.content) == size
        and full.headers["accept-ranges"] == "bytes"
    )
    part = client.get(
        f"/api/demo/workspaces/{wid}/audio", headers={"Range": "bytes=100-199"}
    )
    assert part.status_code == 206 and len(part.content) == 100
    assert part.headers["content-range"] == f"bytes 100-199/{size}"
    assert part.content == full.content[100:200]
    tail = client.get(
        f"/api/demo/workspaces/{wid}/audio", headers={"Range": "bytes=-44"}
    )
    assert tail.status_code == 206 and tail.content == full.content[-44:]
    assert (
        client.get(
            f"/api/demo/workspaces/{wid}/audio", headers={"Range": f"bytes={size}-"}
        ).status_code
        == 416
    )


def test_playback_position_is_saved_and_clamped(client):
    ws = wait_ready(client, upload(client).json()["id"])
    assert client.put(
        f"/api/demo/workspaces/{ws['id']}/playback", json={"cursor_ms": 41_500}
    ).json() == {"cursor_ms": 41_500}
    assert (
        client.get(f"/api/demo/workspaces/{ws['id']}").json()["playback_cursor_ms"]
        == 41_500
    )
    assert (
        client.put(
            f"/api/demo/workspaces/{ws['id']}/playback", json={"cursor_ms": 10_000_000}
        ).json()["cursor_ms"]
        == ws["duration_ms"]
    )
    assert (
        client.put(
            f"/api/demo/workspaces/{ws['id']}/playback", json={"cursor_ms": -1}
        ).status_code
        == 422
    )


def test_unknown_workspace_is_404(client):
    assert client.get("/api/demo/workspaces/not-a-uuid").status_code == 404
    assert (
        client.get(
            "/api/demo/workspaces/00000000-0000-4000-8000-000000000000"
        ).status_code
        == 404
    )


def test_before_recording_extends_the_timeline(client):
    res = upload(
        client,
        files=[part(AUDIO_87), part(AUDIO), part(ADSB, "text/csv")],
        positions={"87.wav": "before", "88.wav": "main"},
    )
    assert res.status_code == 201, res.text
    ws = wait_ready(client, res.json()["id"])
    assert [(f["part"], f["position"]) for f in ws["files"]][0] == ("87", "before")
    analysis = client.get(f"/api/demo/workspaces/{ws['id']}/analysis").json()
    recs = analysis["recordings"]
    assert [(r["part"], r["offset_ms"]) for r in recs] == [("87", 0), ("88", OFFSET_88)]
    assert ws["duration_ms"] == OFFSET_88 + recs[1]["duration_ms"]
    titles = [f["title"] for f in analysis["spec"]["findings"]]
    assert "Readback matches the taxi clearance" in titles
    assert "Hold short changed off the recording" in titles
    assert "Response identity is a suffix only" not in titles
    assert analysis["spec"]["gaps"] == [
        {"start_ms": recs[0]["duration_ms"], "end_ms": OFFSET_88}
    ]
    size = (SCENARIO / "derived" / "87.pcm16.wav").stat().st_size
    audio = client.get(
        f"/api/demo/workspaces/{ws['id']}/audio/87", headers={"Range": "bytes=0-9"}
    )
    assert (
        audio.status_code == 206
        and audio.headers["content-range"] == f"bytes 0-9/{size}"
    )
    assert client.get(f"/api/demo/workspaces/{ws['id']}/audio/89").status_code == 404


def test_recording_in_the_wrong_slot_is_rejected(client):
    res = upload(
        client,
        files=[part(AUDIO_87), part(AUDIO), part(ADSB, "text/csv")],
        positions={"87.wav": "after"},
    )
    body = res.json()
    assert res.status_code == 422 and body["details"]["code"] == "WRONG_POSITION"
    assert body["details"]["position"] == "before"


def test_adsb_without_its_recording_is_rejected(client):
    res = upload(
        client, files=[part(ADSB_87, "text/csv"), part(AUDIO), part(ADSB, "text/csv")]
    )
    assert res.status_code == 422 and res.json()["details"]["code"] == "MISSING_AUDIO"


def test_add_recording_before_reprocesses_and_shifts_playback(client):
    ws = wait_ready(client, upload(client).json()["id"])
    client.put(f"/api/demo/workspaces/{ws['id']}/playback", json={"cursor_ms": 10_000})
    res = client.post(
        f"/api/demo/workspaces/{ws['id']}/files",
        data={"positions": json.dumps({"87.wav": "before", ADSB_87.name: "before"})},
        files=[part(AUDIO_87), part(ADSB_87, "text/csv")],
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "PROCESSING"
    ready = wait_ready(client, ws["id"])
    assert ready["name"] == "KAGC demo" and len(ready["files"]) == 4
    assert ready["playback_cursor_ms"] == 10_000 + OFFSET_88
    analysis = client.get(f"/api/demo/workspaces/{ws['id']}/analysis").json()
    assert len(analysis["spec"]["findings"]) == 11
    assert "Taxi follows the clearance" in [
        f["title"] for f in analysis["spec"]["findings"]
    ]
    with psycopg.connect(DB_URL) as conn:
        assert conn.execute("SELECT count(*) FROM findings").fetchone()[0] == 11
        assert (
            conn.execute("SELECT count(*) FROM transcript_segments").fetchone()[0] == 11
        )
    dup = client.post(f"/api/demo/workspaces/{ws['id']}/files", files=[part(AUDIO_87)])
    assert dup.status_code == 422 and dup.json()["details"]["code"] == "DUPLICATE_FILE"


def test_stored_analysis_from_an_older_scenario_is_rebuilt(client):
    wid = upload(client).json()["id"]
    wait_ready(client, wid)
    first = client.get(f"/api/demo/workspaces/{wid}/analysis").json()
    assert first["spec"]["findings"][0]["live"]["title"]
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute(
            "UPDATE workspaces SET analysis = jsonb_set(analysis, '{build}', '\"old\"') WHERE id=%s",
            (wid,),
        )
    again = client.get(f"/api/demo/workspaces/{wid}/analysis").json()
    assert again["build"] == first["build"] != "old"
    assert again["spec"]["findings"] == first["spec"]["findings"]


@pytest.mark.parametrize(
    "main,date",
    [
        (50, "2022-09-10"),
        (51, "2022-09-10"),
        (47, "2022-09-10"),
        (156, "2022-09-11"),
        (123, "2022-09-10"),
    ],
)
def test_additional_standalone_case(client, main, date):
    case_id = f"kagc-{date}-{main}"
    root = ROOT / case_id
    response = client.post(
        "/api/demo/workspaces",
        data={"name": f"Additional {main}", "scenario_id": case_id},
        files=[
            part(root / f"{main}.wav"),
            part(root / f"kagc_adsb_{date}_{main}.csv", "text/csv"),
        ],
    )
    assert response.status_code == 201, response.text
    wid = response.json()["id"]
    ws = wait_ready(client, wid)
    assert len(ws["recordings"]) == 1 and ws["recordings"][0]["part"] == str(main)
    analysis = client.get(f"/api/demo/workspaces/{wid}/analysis").json()
    assert analysis["spec"]["findings"] and analysis["spec"]["reminders"]
    assert all(f["movement"] == "NOT_EVALUABLE" for f in analysis["spec"]["findings"])
    assert all(r["part"] not in ("87", "88") for r in analysis["recordings"])


def test_additional_context_and_identity_scoping(client):
    root = ROOT / "kagc-2022-09-10-51"
    files = [
        part(root / "51.wav"),
        part(root / "kagc_adsb_2022-09-10_51.csv", "text/csv"),
        part(root / "50.wav"),
    ]
    res = client.post(
        "/api/demo/workspaces",
        data={"name": "Context 51", "scenario_id": root.name},
        files=files,
    )
    assert res.status_code == 201, res.text
    ws = wait_ready(client, res.json()["id"])
    assert [r["part"] for r in ws["recordings"]] == ["50", "51"]
    assert ws["recordings"][1]["offset_ms"] == 120003
    analysis = client.get(f"/api/demo/workspaces/{ws['id']}/analysis").json()
    assert analysis["spec"]["gaps"] == [{"start_ms": 64932, "end_ms": 120003}]
    # Same immutable 50 source is valid as main in a different case, but never as
    # a file belonging to a completely unrelated clearance case.
    bad = client.post(
        "/api/demo/workspaces",
        data={"name": "Wrong case", "scenario_id": "kagc-2022-09-11-156"},
        files=files,
    )
    assert bad.status_code == 422


def test_additional_catalogue(client):
    choices = client.get("/api/demo/scenarios").json()["scenarios"]
    assert len(choices) == 6
    case50 = next(c for c in choices if c["id"] == "kagc-2022-09-10-50")
    case51 = next(c for c in choices if c["id"] == "kagc-2022-09-10-51")
    assert (
        next(f for f in case50["files"] if f["name"] == "50.wav")["position"] == "main"
    )
    assert (
        next(f for f in case51["files"] if f["name"] == "50.wav")["position"]
        == "before"
    )
    assert next(c for c in choices if c["id"] == "kagc-2022-09-10-88")["limits"] is None
