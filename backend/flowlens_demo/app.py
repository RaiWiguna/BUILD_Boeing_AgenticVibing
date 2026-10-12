"""FastAPI app for demo workspaces (prepared analysis, PostgreSQL persistence).

Routes live under /api/demo. Uploaded files are hashed and inspected, then discarded: a
workspace references the canonical scenario assets on the server. A session can grow by
adding recordings before or after the main one; the file set selects a prepared analysis.
Nothing here calls a cloud provider, and transcript/audio content is never logged.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from . import DEMO_VERSION
from .adsb import parse as parse_adsb
from .db import Database
from .media import inspect_wav
from .processing import step_details, step_states, total_ms
from .scenarios import FileRef, Registry, Scenario, variant_key

MAX_AUDIO_BYTES = 64 * 1024 * 1024
MAX_ADSB_BYTES = 8 * 1024 * 1024
MAX_FILES = 20
NAME_RE = re.compile(r"^[^\x00-\x1f]{1,80}$")


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        recovery: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.status, self.code, self.message, self.recovery, self.details = (
            status,
            code,
            message,
            recovery,
            details or {},
        )


class PlaybackIn(BaseModel):
    cursor_ms: int = Field(ge=0, le=24 * 3_600_000)


def _iso(v: datetime | None) -> str | None:
    return v.astimezone(UTC).isoformat().replace("+00:00", "Z") if v else None


def create_app(
    database_url: str | None = None,
    scenario_root: str | None = None,
    processing_scale: float | None = None,
) -> FastAPI:
    db = Database(database_url or os.environ["DEMO_DATABASE_URL"])
    registry = Registry(Path(scenario_root or os.environ.get("DEMO_SCENARIO_ROOT") or "/scenarios"))
    scale = (
        processing_scale
        if processing_scale is not None
        else float(os.environ.get("DEMO_PROCESSING_SCALE", "1.0"))
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        db.migrate()
        yield

    app = FastAPI(title="FlowLens demo workspaces", version=DEMO_VERSION, lifespan=lifespan)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={
                "code": exc.code,
                "message": exc.message,
                "recovery": exc.recovery,
                "details": exc.details,
            },
        )

    # ── helpers ────────────────────────────────────────────────────────
    def finalize_if_due(cur: Any, row: dict[str, Any]) -> dict[str, Any]:
        """Turn a finished schedule into a stored workspace exactly once."""
        if row["status"] != "PROCESSING":
            return row
        elapsed = (datetime.now(UTC) - row["processing_started_at"]).total_seconds() * 1000
        if elapsed < total_ms(row["processing_scale"]):
            return row
        sc = registry.get(row["scenario_id"])
        if sc is None:
            cur.execute(
                "UPDATE workspaces SET status='FAILED' WHERE id=%s AND status='PROCESSING' RETURNING *",
                (row["id"],),
            )
            return cur.fetchone() or row
        variant = sc.data["variants"].get(row["variant"])
        if variant is None:
            cur.execute(
                "UPDATE workspaces SET status='FAILED' WHERE id=%s AND status='PROCESSING' RETURNING *",
                (row["id"],),
            )
            return cur.fetchone() or row
        ready_at = datetime.now(UTC)
        analysis = build_analysis(sc.data, variant, row, ready_at)
        cur.execute(
            "UPDATE workspaces SET status='READY', ready_at=%s, analysis=%s WHERE id=%s AND status='PROCESSING' RETURNING *",
            (ready_at, psycopg_json(analysis), row["id"]),
        )
        updated = cur.fetchone()
        if updated is None:  # another request finalized first
            cur.execute("SELECT * FROM workspaces WHERE id=%s", (row["id"],))
            return cur.fetchone()  # type: ignore[no-any-return]
        spec = analysis["spec"]
        for seg, live in zip(spec["segments"], analysis["live"]["segments"], strict=True):
            words = live["words"]
            cur.execute(
                "INSERT INTO transcript_segments (workspace_id, seg_key, start_ms, end_ms, text, confidence, words) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    seg["key"],
                    words[0]["start_ms"],
                    words[-1]["end_ms"],
                    seg["text"],
                    live["confidence"],
                    psycopg_json(words),
                ),
            )
        for f in spec["findings"]:
            cur.execute(
                "INSERT INTO findings (workspace_id, finding_key, category, priority, title, statement, pending_ms, available_ms, body) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    f["key"],
                    f["category"],
                    f["priority"],
                    f["title"],
                    f["statement"],
                    clock_ms(f["pending"]),
                    clock_ms(f["available"]),
                    psycopg_json(f),
                ),
            )
        return updated  # type: ignore[no-any-return]

    def view(cur: Any, row: dict[str, Any]) -> dict[str, Any]:
        sc = registry.get(row["scenario_id"])
        order = {"before": 0, "main": 1, "after": 2}
        files = sorted(
            (
                {**f, "position": sc.position(f["part"]) if sc else "main"}
                for f in file_rows(cur, row["id"])
            ),
            key=lambda f: (order.get(f["position"], 1), f["part"], f["role"] != "audio"),
        )
        cur.execute("SELECT cursor_ms FROM playback_state WHERE workspace_id=%s", (row["id"],))
        pb = cur.fetchone()
        elapsed = (datetime.now(UTC) - row["processing_started_at"]).total_seconds() * 1000
        total = total_ms(row["processing_scale"])
        steps = step_states(
            elapsed if row["status"] == "PROCESSING" else total + 1,
            row["processing_scale"],
            row["step_details"],
        )
        variant = sc.data["variants"].get(row["variant"]) if sc else None
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "scenario_id": row["scenario_id"],
            "status": row["status"],
            "duration_ms": row["duration_ms"],
            "created_at": _iso(row["created_at"]),
            "ready_at": _iso(row["ready_at"]),
            "progress": 1.0
            if row["status"] == "READY"
            else round(min(0.99, elapsed / total) if total else 0.99, 3),
            "eta_ms": 0 if row["status"] != "PROCESSING" else max(0, int(total - elapsed)),
            "steps": steps,
            "files": files,
            "labels": sc.data["labels"] if sc else [],
            "recordings": variant["recordings"] if variant else [],
            "playback_cursor_ms": pb["cursor_ms"] if pb else 0,
        }

    def load(cur: Any, workspace_id: str) -> dict[str, Any]:
        try:
            wid = uuid.UUID(workspace_id)
        except ValueError as exc:
            raise ApiError(404, "NOT_FOUND", "Workspace not found.") from exc
        cur.execute("SELECT * FROM workspaces WHERE id=%s", (wid,))
        row = cur.fetchone()
        if row is None:
            raise ApiError(404, "NOT_FOUND", "Workspace not found.", "Return to the session list.")
        return finalize_if_due(cur, row)

    # ── routes ─────────────────────────────────────────────────────────
    @app.get("/api/demo/health")
    def health() -> dict[str, Any]:
        return {
            "status": "alive",
            "profile": "demo",
            "database": db.ping(),
            "scenarios": len(registry),
            "version": DEMO_VERSION,
        }

    @app.get("/api/demo/scenarios")
    def scenarios() -> dict[str, Any]:
        """File names the demo recognises, with role and position (no hashes or paths)."""
        files = registry.expected()
        return {"expected_files": [f["name"] for f in files], "files": files}

    @app.get("/api/demo/workspaces")
    def list_workspaces() -> list[dict[str, Any]]:
        with db.tx() as cur:
            cur.execute("SELECT * FROM workspaces ORDER BY created_at DESC")
            rows = [finalize_if_due(cur, r) for r in cur.fetchall()]
            return [view(cur, r) for r in rows]

    @app.get("/api/demo/workspaces/{workspace_id}")
    def get_workspace(workspace_id: str) -> dict[str, Any]:
        with db.tx() as cur:
            return view(cur, load(cur, workspace_id))

    async def read_upload(
        up: UploadFile, positions: dict[str, str]
    ) -> tuple[Scenario, FileRef, dict[str, Any]]:
        fname = Path(up.filename or "").name
        match = registry.by_file_name(fname)
        if match is None:
            raise ApiError(
                422,
                "INVALID_IMPORT",
                f"“{fname}” is not a recording of this scenario.",
                "Use a recording from the scenario folder.",
                {"file": fname, "code": "UNKNOWN_FILE"},
            )
        sc, ref = match
        want = positions.get(fname)
        have = sc.position(ref.part)
        if want and want != have:
            main = sc.parts[sc.main_part]["audio"]["name"]
            raise ApiError(
                422,
                "INVALID_IMPORT",
                f"“{fname}” was recorded {have} {main}. Add it under {have.capitalize()}.",
                details={"file": fname, "code": "WRONG_POSITION", "position": have},
            )
        limit = MAX_AUDIO_BYTES if ref.role == "audio" else MAX_ADSB_BYTES
        h, size, head, body = hashlib.sha256(), 0, b"", bytearray()
        while chunk := await up.read(1 << 20):
            size += len(chunk)
            if size > limit:
                raise ApiError(
                    413,
                    "INVALID_IMPORT",
                    f"“{fname}” is larger than {limit // (1024 * 1024)} MiB.",
                    details={"file": fname, "code": "TOO_LARGE"},
                )
            h.update(chunk)
            if len(head) < 65536:
                head += chunk[: 65536 - len(head)]
            if ref.role == "adsb":
                body += chunk
        digest = h.hexdigest()
        if digest != ref.meta["sha256"] or size != ref.meta["size_bytes"]:
            raise ApiError(
                422,
                "INVALID_IMPORT",
                f"“{fname}” has the expected name but different content.",
                "Use the unmodified file.",
                {"file": fname, "code": "CHECKSUM_MISMATCH"},
            )
        if ref.role == "audio":
            info = inspect_wav(head, size)
            if info is None:
                raise ApiError(
                    422,
                    "INVALID_IMPORT",
                    f"“{fname}” is not a readable WAV file.",
                    details={"file": fname, "code": "NOT_WAV"},
                )
            detected: dict[str, Any] = {**info.__dict__, "describe": info.describe()}
        else:
            detected = parse_adsb(bytes(body)).summary()
            detected["label"] = ref.meta.get("label", "ADS-B")
        return (
            sc,
            ref,
            {
                "part": ref.part,
                "role": ref.role,
                "position": have,
                "name": fname,
                "size_bytes": size,
                "sha256": digest,
                "detected": detected,
            },
        )

    def check_set(sc: Scenario, keys: set[tuple[str, str]]) -> dict[str, Any]:
        main = sc.main_part
        if (main, "audio") not in keys or (main, "adsb") not in keys:
            raise ApiError(
                422,
                "INVALID_IMPORT",
                "Add the main recording and its ADS-B file.",
                details={"code": "MISSING_ROLE"},
            )
        for part, role in keys:
            if role == "adsb" and (part, "audio") not in keys:
                audio = sc.parts[part]["audio"]["name"]
                raise ApiError(
                    422,
                    "INVALID_IMPORT",
                    f"Add {audio} with its ADS-B file.",
                    details={"code": "MISSING_AUDIO", "file": audio},
                )
        variant = sc.variant(keys)
        if variant is None:
            raise ApiError(
                422,
                "INVALID_IMPORT",
                "This combination of files is not supported.",
                details={"code": "UNSUPPORTED_COMBINATION"},
            )
        return variant

    async def accept(
        files: list[UploadFile], positions_json: str | None, existing: list[dict[str, Any]]
    ) -> tuple[Scenario, list[dict[str, Any]], dict[str, Any]]:
        if not files or len(files) > MAX_FILES:
            raise ApiError(
                422,
                "INVALID_IMPORT",
                f"Upload 1–{MAX_FILES} files.",
                details={"received": len(files), "code": "FILE_COUNT"},
            )
        try:
            positions = json.loads(positions_json) if positions_json else {}
            assert isinstance(positions, dict)
        except (ValueError, AssertionError) as exc:
            raise ApiError(422, "INVALID_INPUT", "Invalid file positions.") from exc
        scenario = registry.get(existing[0]["scenario_id"]) if existing else None
        keys = {(f["part"], f["role"]) for f in existing}
        uploads: list[dict[str, Any]] = []
        for up in files:
            sc, ref, u = await read_upload(up, positions)
            if scenario is not None and sc.id != scenario.id:
                raise ApiError(
                    422,
                    "INVALID_IMPORT",
                    "These files belong to a different scenario.",
                    details={"code": "SCENARIO_MISMATCH"},
                )
            if (ref.part, ref.role) in keys:
                raise ApiError(
                    422,
                    "INVALID_IMPORT",
                    f"“{u['name']}” is already in this session.",
                    details={"code": "DUPLICATE_FILE", "file": u["name"]},
                )
            scenario = sc
            keys.add((ref.part, ref.role))
            uploads.append(u)
        assert scenario is not None
        return scenario, uploads, check_set(scenario, keys)

    def store_files(cur: Any, wid: uuid.UUID, uploads: list[dict[str, Any]]) -> None:
        for u in uploads:
            cur.execute(
                "INSERT INTO workspace_files (workspace_id, part, role, original_name, size_bytes, sha256, detected) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    wid,
                    u["part"],
                    u["role"],
                    u["name"],
                    u["size_bytes"],
                    u["sha256"],
                    psycopg_json(u["detected"]),
                ),
            )

    def file_rows(cur: Any, wid: uuid.UUID) -> list[dict[str, Any]]:
        cur.execute(
            "SELECT part, role, original_name AS name, size_bytes, sha256, detected FROM workspace_files WHERE workspace_id=%s",
            (wid,),
        )
        return list(cur.fetchall())

    def schedule_scale(n_files: int) -> float:
        return scale * (1 + 0.3 * max(0, n_files - 2))

    @app.post("/api/demo/workspaces", status_code=201)
    async def create_workspace(
        name: str = Form(...),
        files: list[UploadFile] = File(...),
        positions: str | None = Form(None),
    ) -> dict[str, Any]:
        name = name.strip()
        if not NAME_RE.match(name):
            raise ApiError(422, "INVALID_INPUT", "Session name must be 1–80 printable characters.")
        scenario, uploads, variant = await accept(files, positions, [])
        details = step_details(scenario, variant, uploads, uploads)
        wid = uuid.uuid4()
        with db.tx() as cur:
            cur.execute("SELECT 1 FROM workspaces WHERE lower(name)=lower(%s)", (name,))
            if cur.fetchone():
                raise ApiError(
                    409,
                    "NAME_TAKEN",
                    "A session with this name already exists.",
                    "Choose a different name.",
                )
            cur.execute(
                "INSERT INTO workspaces (id, name, scenario_id, status, duration_ms, processing_scale, step_details, variant) VALUES (%s,%s,%s,'PROCESSING',%s,%s,%s,%s) RETURNING *",
                (
                    wid,
                    name,
                    scenario.id,
                    variant["duration_ms"],
                    schedule_scale(len(uploads)),
                    psycopg_json(details),
                    variant_key((u["part"], u["role"]) for u in uploads),
                ),
            )
            row = cur.fetchone()
            assert row is not None
            store_files(cur, wid, uploads)
            return view(cur, row)

    @app.post("/api/demo/workspaces/{workspace_id}/files")
    async def add_files(
        workspace_id: str,
        files: list[UploadFile] = File(...),
        positions: str | None = Form(None),
    ) -> dict[str, Any]:
        with db.tx() as cur:
            row = load(cur, workspace_id)
            if row["status"] == "PROCESSING":
                raise ApiError(
                    409,
                    "NOT_READY",
                    "This session is still processing.",
                    "Try again when it is ready.",
                )
            existing = [{**f, "scenario_id": row["scenario_id"]} for f in file_rows(cur, row["id"])]
        scenario, uploads, variant = await accept(files, positions, existing)
        all_files = existing + uploads
        details = step_details(scenario, variant, all_files, uploads)
        old = scenario.variant((f["part"], f["role"]) for f in existing)
        shift = offset_of(variant, scenario.main_part) - (
            offset_of(old, scenario.main_part) if old else 0
        )
        with db.tx() as cur:
            cur.execute("SELECT status FROM workspaces WHERE id=%s FOR UPDATE", (row["id"],))
            locked = cur.fetchone()
            if locked is None or locked["status"] == "PROCESSING":
                raise ApiError(409, "NOT_READY", "This session is already being updated.")
            cur.execute("DELETE FROM transcript_segments WHERE workspace_id=%s", (row["id"],))
            cur.execute("DELETE FROM findings WHERE workspace_id=%s", (row["id"],))
            store_files(cur, row["id"], uploads)
            cur.execute(
                "UPDATE workspaces SET status='PROCESSING', processing_started_at=now(), ready_at=NULL, analysis=NULL, duration_ms=%s, processing_scale=%s, step_details=%s, variant=%s WHERE id=%s RETURNING *",
                (
                    variant["duration_ms"],
                    schedule_scale(len(uploads) + 1),
                    psycopg_json(details),
                    variant_key((f["part"], f["role"]) for f in all_files),
                    row["id"],
                ),
            )
            updated = cur.fetchone()
            assert updated is not None
            cur.execute(
                "UPDATE playback_state SET cursor_ms=LEAST(%s, GREATEST(0, cursor_ms + %s)), updated_at=now() WHERE workspace_id=%s",
                (variant["duration_ms"], shift, row["id"]),
            )
            return view(cur, updated)

    @app.get("/api/demo/workspaces/{workspace_id}/analysis")
    def analysis(workspace_id: str) -> dict[str, Any]:
        with db.tx() as cur:
            row = load(cur, workspace_id)
            if row["status"] != "READY":
                raise ApiError(
                    409,
                    "NOT_READY",
                    "Processing has not finished yet.",
                    "Wait for processing to complete.",
                )
            analysis = row["analysis"]
            sc = registry.get(row["scenario_id"])
            if sc is None or analysis.get("build") != sc.data["build"]:
                variant = sc.data["variants"].get(row["variant"]) if sc else None
                if sc is None or variant is None:
                    raise ApiError(409, "NOT_READY", "This session needs to be imported again.")
                analysis = build_analysis(sc.data, variant, row, row["ready_at"])
                cur.execute(
                    "UPDATE workspaces SET analysis=%s WHERE id=%s",
                    (psycopg_json(analysis), row["id"]),
                )
            base = f"/api/demo/workspaces/{row['id']}/audio"
            return {
                "workspace": view(cur, row),
                **analysis,
                "recordings": [
                    {**r, "audio_url": f"{base}/{r['part']}"} for r in analysis["recordings"]
                ],
                "audio_url": f"{base}/{analysis['recordings'][0]['part']}",
            }

    @app.put("/api/demo/workspaces/{workspace_id}/playback")
    def playback(workspace_id: str, body: PlaybackIn) -> dict[str, Any]:
        with db.tx() as cur:
            row = load(cur, workspace_id)
            cursor = min(body.cursor_ms, row["duration_ms"])
            cur.execute(
                "INSERT INTO playback_state (workspace_id, cursor_ms) VALUES (%s,%s) ON CONFLICT (workspace_id) DO UPDATE SET cursor_ms=EXCLUDED.cursor_ms, updated_at=now()",
                (row["id"], cursor),
            )
            return {"cursor_ms": cursor}

    @app.get("/api/demo/workspaces/{workspace_id}/audio")
    def audio_main(workspace_id: str, request: Request) -> Response:
        return audio(workspace_id, "", request)

    @app.get("/api/demo/workspaces/{workspace_id}/audio/{part}")
    def audio(workspace_id: str, part: str, request: Request) -> Response:
        with db.tx() as cur:
            row = load(cur, workspace_id)
        sc = registry.get(row["scenario_id"])
        if row["status"] != "READY" or sc is None:
            raise ApiError(409, "NOT_READY", "Audio is available after processing.")
        parts = [k.split(":")[0] for k in (row["variant"] or "").split(",") if k.endswith(":audio")]
        part = part or sc.main_part
        if part not in parts:
            raise ApiError(404, "NOT_FOUND", "This recording is not part of the session.")
        path = sc.audio_path(part)
        size = path.stat().st_size
        headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=3600"}
        rng = request.headers.get("range")
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng or "")
        if not m or (not m.group(1) and not m.group(2)):
            return FileResponse(path, media_type="audio/wav", headers=headers)
        if m.group(1):
            start = int(m.group(1))
            end = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
        else:
            start, end = max(0, size - int(m.group(2))), size - 1
        if start > end or start >= size:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        with path.open("rb") as fh:
            fh.seek(start)
            data = fh.read(end - start + 1)
        return Response(
            data,
            status_code=206,
            media_type="audio/wav",
            headers={**headers, "Content-Range": f"bytes {start}-{end}/{size}"},
        )

    return app


def clock_ms(clock: str) -> int:
    m, rest = clock.split(":")
    s, t = rest.split(".")
    return (int(m) * 60 + int(s)) * 1000 + int(t) * 100


def psycopg_json(value: Any) -> Any:
    from psycopg.types.json import Jsonb

    return Jsonb(value)


def offset_of(variant: dict[str, Any], part: str) -> int:
    return next((int(r["offset_ms"]) for r in variant["recordings"] if r["part"] == part), 0)


def build_analysis(
    scenario: dict[str, Any], variant: dict[str, Any], row: dict[str, Any], ready_at: datetime
) -> dict[str, Any]:
    spec = copy.deepcopy(variant["spec"])
    stamp = _iso(ready_at)
    spec["title"] = row["name"]
    spec["updatedAt"] = stamp
    for run in spec["runs"]:
        run["createdAt"] = stamp
    return {
        "spec": spec,
        "live": variant["live"],
        "layout": variant["layout"],
        "peaks": variant["peaks"],
        "labels": scenario["labels"],
        "attribution": scenario["attribution"],
        "stt": variant["stt"],
        "adsb": variant["adsb"],
        "recordings": variant["recordings"],
        "build": scenario["build"],
    }
