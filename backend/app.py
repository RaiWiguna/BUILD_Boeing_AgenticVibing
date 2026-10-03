"""Local single-process FastAPI application. WebSockets authenticate in the first message."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import logging
import os
import secrets
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from .models import (
    Acknowledgement,
    Assessment,
    Command,
    Contract,
    CreateSession,
    Role,
    SeatRequest,
    SimulationConfig,
)
from .ports import CompositionOverrides, SessionWriter, WorkerRequest, WorkerResult
from .replay_contracts import ReplayEventRecord, ReplaySourceManifest
from .reporting import report_csv, report_html, session_report
from .review import Review
from .scenarios import CATALOGUE
from .session import Session, SessionError
from .storage import Archive

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("flowlens")


class OperatorLogin(Contract):
    key: str = Field(min_length=16, max_length=200)


class BranchRequest(Contract):
    at_ms: int = Field(ge=0)


class _ArchivePublicReader:
    """Project current archive rows to the public reader capability."""

    def __init__(self, archive: Archive):
        self._archive = archive

    def metadata(self, source_session_id: str) -> dict | None:
        return self._archive.metadata(source_session_id)

    def frame(self, source_session_id: str, at_ms: int | None = None) -> dict | None:
        stored = self._archive.frame(source_session_id, at_ms)
        return copy.deepcopy(stored[0]) if stored else None

    def events(self, source_session_id: str, after_ordinal: int = 0,
               until_ms: int | None = None) -> list[dict]:
        stored = self._archive.all_events(source_session_id)
        return [event for event in stored if event["ordinal"] > after_ordinal
                and (until_ms is None or event["sim_ms"] <= until_ms)]


class Manager:
    def __init__(self, archive: Archive, operator_key: str, *, ports: CompositionOverrides | None = None,
                 wall_clock: Callable[[], float] = time.time,
                 monotonic_clock: Callable[[], float] = time.perf_counter):
        self.archive = archive
        self.operator_key = operator_key
        self.ports = ports or CompositionOverrides()
        self.session_writer: SessionWriter = (
            self.ports.session_writer_factory(archive)
            if self.ports.session_writer_factory else archive
        )
        self.replay_event_source = self.ports.replay_event_source
        self.replay_archive_reader = self.ports.replay_archive_reader or _ArchivePublicReader(archive)
        self.worker_port = self.ports.worker
        self.wall_clock = wall_clock
        self.monotonic_clock = monotonic_clock
        self.sessions: dict[str, Session | Review] = {}
        self.tokens: dict[str, dict] = {}
        self.lock = asyncio.Lock()
        self.last: dict[str, float] = {}
        self.accumulators: dict[str, float] = {}

    def mint(self, role: Role, label: str, session_id: str | None) -> str:
        token = secrets.token_urlsafe(32)
        self.tokens[hashlib.sha256(token.encode()).hexdigest()] = {
            "role": role, "label": label, "session_id": session_id, "expires": self.wall_clock()+8*3600}
        return token

    def identity(self, token: str) -> dict:
        actor = self.tokens.get(hashlib.sha256(token.encode()).hexdigest())
        if not actor or actor["expires"] < self.wall_clock():
            raise HTTPException(401, "Seat token missing or expired")
        return actor

    def access(self, id: str, actor: dict):
        if actor["session_id"] is not None and actor["session_id"] != id:
            raise HTTPException(403, "Token belongs to a different session")
        if id not in self.sessions and not self.archive.metadata(id):
            raise HTTPException(404, "Session not found")

    def instructor(self, actor: dict):
        if actor["role"] != Role.INSTRUCTOR:
            raise HTTPException(403, "Instructor access required")

    def snapshot(self, id: str, actor: dict) -> dict:
        self.access(id, actor)
        if id in self.sessions:
            result = copy.deepcopy(self.sessions[id].snapshot())
        else:
            frame = self.replay_archive_reader.frame(id)
            if not frame:
                raise HTTPException(404, "No recorded snapshot")
            result = copy.deepcopy(dict(frame))
            metadata = self.replay_archive_reader.metadata(id)
            if metadata is None:
                raise HTTPException(404, "Session not found")
            result["status"] = metadata["status"]
        # Assessment and response timings are personal evaluation data.
        if actor["role"] != Role.INSTRUCTOR:
            result["assessments"] = [e for e in result["assessments"] if e.get("actor") == actor["label"]]
            result["events"] = [e for e in result["events"] if e["type"] != "ASSESSMENT" or e.get("actor") == actor["label"]]
            result["review_annotations"] = []
        if result["metadata"]["condition"] == "baseline":
            result["predictions"] = []
            for alert in result["alerts"]:
                alert["reason"] = "Runway attention required."
                alert["metrics"] = {}
                alert["evidence_event_ids"] = []
                alert["assumptions"] = ""
            result["events"] = [e | {"message": "Runway alert", "evidence_event_ids": []}
                                if e["type"].startswith("ALERT") else e for e in result["events"]]
        result["seat"] = {"role": actor["role"].value, "label": actor["label"]}
        result["server_sent_utc_ms"] = int(self.wall_clock()*1000)
        return result

    def new_session(self, scenario_id: str, seed: int = 42, config: SimulationConfig | None = None,
                    condition: str = "flowlens", parent: dict | None = None,
                    initialize: bool = True) -> Session:
        return Session(
            self.archive, scenario_id, seed, config, condition, parent,
            detector=self.ports.detector,
            lifecycle=self.ports.alert_lifecycle,
            writer=self.session_writer,
            audit_clock=self.wall_clock,
            initialize=initialize,
        )

    def read_replay_source(
        self, after_ordinal: int = 0, until_ms: int | None = None
    ) -> tuple[ReplaySourceManifest, list[ReplayEventRecord]]:
        """Read one injected source page without reducing or mutating session state."""
        if self.replay_event_source is None:
            raise RuntimeError("No replay event source is configured")
        manifest = self.replay_event_source.manifest()
        records = list(self.replay_event_source.read(after_ordinal, until_ms))
        previous_ordinal = after_ordinal
        for record in records:
            if record.source_id != manifest.source_id or record.event.ordinal <= previous_ordinal:
                raise ValueError("Replay source returned mismatched identity or nonordered event ordinals")
            previous_ordinal = record.event.ordinal
        return manifest, records

    def read_public_frame(self, source_session_id: str, at_ms: int | None = None) -> Mapping[str, Any] | None:
        return self.replay_archive_reader.frame(source_session_id, at_ms)

    def read_public_events(self, source_session_id: str, after_ordinal: int = 0,
                           until_ms: int | None = None) -> Sequence[Mapping[str, Any]]:
        return self.replay_archive_reader.events(source_session_id, after_ordinal, until_ms)

    def run_worker(self, request: WorkerRequest) -> WorkerResult:
        if self.worker_port is None:
            raise RuntimeError("No replay worker is configured")
        return self.worker_port.process(request)

    async def clock(self):
        while True:
            async with self.lock:
                wall = self.monotonic_clock()
                for id, session in list(self.sessions.items()):
                    elapsed = wall-self.last.get(id, wall)
                    self.last[id] = wall
                    if session.status != "RUNNING":
                        self.accumulators[id] = 0
                        continue
                    budget = self.accumulators.get(id, 0)+elapsed*session.speed
                    ticks = min(50, int(budget/.1))
                    self.accumulators[id] = budget-ticks*.1
                    try:
                        session.advance(ticks)
                    except Exception:
                        session.status = "PAUSED"
                        LOGGER.exception("Session paused after runtime/persistence failure")
            await asyncio.sleep(.05)


def create_app(db_path: str | Path | None = None, operator_key: str | None = None,
               run_clock: bool = True, *, ports: CompositionOverrides | None = None,
               wall_clock: Callable[[], float] = time.time,
               monotonic_clock: Callable[[], float] = time.perf_counter) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = ROOT / "runtime"
        runtime.mkdir(exist_ok=True)
        key = operator_key or os.environ.get("FLOWLENS_OPERATOR_KEY")
        if not key:
            key_file = runtime / "operator-key.txt"
            if not key_file.exists():
                key_file.write_text(secrets.token_urlsafe(32), encoding="utf-8")
            key = key_file.read_text(encoding="utf-8").strip()
            LOGGER.warning("Local operator key is stored at %s (paste into the operator login)", key_file)
        archive = Archive(db_path or runtime / "flowlens.sqlite3")
        app.state.manager = Manager(archive, key, ports=ports, wall_clock=wall_clock,
                                    monotonic_clock=monotonic_clock)
        task = asyncio.create_task(app.state.manager.clock()) if run_clock else None
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        archive.close()

    app = FastAPI(title="ATC FlowLens Training API", version="0.1.0", lifespan=lifespan)

    def manager() -> Manager:
        return app.state.manager

    def identity(authorization: str = Header(default="")) -> dict:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "A seat or operator token is required")
        return manager().identity(authorization[7:])

    @app.exception_handler(SessionError)
    async def session_error(request, error: SessionError):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=error.status, content={"detail": error.message})

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "mode": "synthetic-training", "single_writer": True}

    @app.post("/api/v1/auth/operator")
    async def login(payload: OperatorLogin):
        async with manager().lock:
            if not secrets.compare_digest(payload.key, manager().operator_key):
                raise HTTPException(401, "Invalid operator key")
            return {"token": manager().mint(Role.INSTRUCTOR, "Lab operator", None), "expires_in_s": 28800}

    @app.get("/api/v1/scenarios")
    def scenarios():
        return {"items": [s.public() for s in CATALOGUE.values()]}

    @app.get("/api/v1/scenarios/{id}")
    def scenario(id: str):
        if id not in CATALOGUE:
            raise HTTPException(404, "Scenario not found")
        return CATALOGUE[id].public()

    @app.get("/api/v1/sessions")
    def sessions(actor=Depends(identity)):
        manager().instructor(actor)
        return {"items": [s for s in manager().archive.list_sessions()
                          if actor["session_id"] is None or s["id"] == actor["session_id"]]}

    @app.post("/api/v1/sessions", status_code=201)
    async def create(payload: CreateSession, actor=Depends(identity)):
        manager().instructor(actor)
        if actor["session_id"] is not None:
            raise HTTPException(403, "Only the lab operator creates independent sessions")
        if payload.scenario_id not in CATALOGUE:
            raise HTTPException(422, "Unknown scenario ID")
        async with manager().lock:
            if sum(s.status == "RUNNING" for s in manager().sessions.values()) >= 8:
                raise HTTPException(409, "Pause another session before creating more lab sessions")
            session = manager().new_session(payload.scenario_id, payload.seed, payload.config, payload.condition)
            manager().sessions[session.id] = session
            return session.metadata

    @app.get("/api/v1/sessions/{id}")
    def session_metadata(id: str, actor=Depends(identity)):
        manager().access(id, actor)
        item = manager().sessions.get(id)
        if isinstance(item, Review):
            return {"id": id, "kind": "review", "source_id": item.source_id, "status": item.status}
        return manager().archive.metadata(id)

    @app.post("/api/v1/sessions/{id}/seats", status_code=201)
    async def seats(id: str, payload: SeatRequest, actor=Depends(identity)):
        manager().access(id, actor)
        manager().instructor(actor)
        async with manager().lock:
            return {"token": manager().mint(payload.role, payload.label, id),
                    "session_id": id, "role": payload.role.value, "label": payload.label, "expires_in_s": 28800}

    @app.get("/api/v1/sessions/{id}/snapshot")
    def snapshot(id: str, actor=Depends(identity)):
        return manager().snapshot(id, actor)

    @app.post("/api/v1/sessions/{id}/commands")
    async def command(id: str, payload: Command, actor=Depends(identity)):
        manager().access(id, actor)
        async with manager().lock:
            session = manager().sessions.get(id)
            if not session:
                raise HTTPException(409, "Archived session cannot receive commands")
            return session.execute(payload, actor["role"], actor["label"])

    @app.get("/api/v1/sessions/{id}/events")
    def events(id: str, cursor: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), actor=Depends(identity)):
        manager().access(id, actor)
        session = manager().sessions.get(id)
        source = session.source_id if isinstance(session, Review) else id
        items = manager().archive.events(source, cursor, limit,
                                         session.now_ms if isinstance(session, Review) else None)
        # Cursor advances through unfiltered rows so personal-data filtering cannot stall pagination.
        next_cursor = items[-1]["ordinal"] if items else cursor
        if actor["role"] != Role.INSTRUCTOR:
            items = [e for e in items if e["type"] != "ASSESSMENT" or e.get("actor") == actor["label"]]
        metadata = manager().archive.metadata(source)
        if metadata and metadata["condition"] == "baseline":
            items = [e | {"message": "Runway alert", "evidence_event_ids": []}
                     if e["type"].startswith("ALERT") else e for e in items]
        return {"items": items, "next_cursor": next_cursor}

    @app.post("/api/v1/sessions/{id}/acknowledgements")
    async def ack(id: str, payload: Acknowledgement, actor=Depends(identity)):
        manager().access(id, actor)
        if actor["role"] == Role.OBSERVER:
            raise HTTPException(403, "Observer records notes, not operational acknowledgements")
        async with manager().lock:
            session = manager().sessions.get(id)
            if not isinstance(session, Session) or session.status in {"ENDED", "INTERRUPTED"}:
                raise HTTPException(409, "Use review annotations for frozen sessions")
            return session.acknowledge(payload.alert_id, actor["label"])

    @app.post("/api/v1/sessions/{id}/assessments", status_code=201)
    async def assess(id: str, payload: Assessment, actor=Depends(identity)):
        manager().access(id, actor)
        if payload.type == "trainer_review" and actor["role"] != Role.INSTRUCTOR:
            raise HTTPException(403, "Instructor access required")
        async with manager().lock:
            session = manager().sessions.get(id)
            if isinstance(session, Review):
                item = {"sim_ms": session.now_ms, "actor": actor["label"], **payload.model_dump()}
                session.annotations.append(item)
                session.sequence += 1
                return item
            if not isinstance(session, Session):
                raise HTTPException(409, "Open a review to annotate an archived session")
            return session.assess(payload.model_dump(), actor["label"], actor["role"])

    @app.post("/api/v1/sessions/{id}/reviews", status_code=201)
    async def reviews(id: str, actor=Depends(identity)):
        manager().access(id, actor)
        manager().instructor(actor)
        async with manager().lock:
            source = manager().sessions.get(id)
            if isinstance(source, Review):
                raise HTTPException(422, "Create a review from a training session")
            if source and source.status not in {"ENDED", "INTERRUPTED"}:
                raise HTTPException(409, "End the training session before freezing a review")
            review = Review(manager().archive, id)
            manager().sessions[review.id] = review
            # Session-bound instructor may control the newly created review only through a new token.
            return {"id": review.id, "source_id": id,
                    "token": manager().mint(Role.INSTRUCTOR, actor["label"], review.id)}

    @app.post("/api/v1/sessions/{id}/branches", status_code=201)
    async def branch(id: str, payload: BranchRequest, actor=Depends(identity)):
        manager().access(id, actor)
        manager().instructor(actor)
        async with manager().lock:
            current = manager().sessions.get(id)
            source_id = current.source_id if isinstance(current, Review) else id
            source = manager().sessions.get(source_id)
            if source and source.status not in {"ENDED", "INTERRUPTED"}:
                raise HTTPException(409, "End the source training session before branching")
            latest = manager().archive.frame(source_id)
            if not latest or payload.at_ms > latest[0]["sim_ms"]:
                raise HTTPException(422, "Branch time is outside the archive")
            frame = manager().archive.frame(source_id, payload.at_ms)
            if not frame:
                raise HTTPException(422, "No checkpoint at this time")
            metadata = frame[0]["metadata"]
            child = manager().new_session(
                metadata["scenario"]["id"], metadata["seed"],
                SimulationConfig.model_validate(metadata["config"]), metadata["condition"],
                {"session_id": source_id, "requested_ms": payload.at_ms, "frame_ms": frame[0]["sim_ms"]},
                initialize=False,
            )
            child.restore(frame[0], frame[1], [e for e in manager().archive.all_events(source_id)
                                              if e["ordinal"] <= frame[1]["event_ordinal"]])
            manager().sessions[child.id] = child
            return {"id": child.id, "parent": child.metadata["parent"],
                    "token": manager().mint(Role.INSTRUCTOR, actor["label"], child.id)}

    @app.get("/api/v1/sessions/{id}/report")
    def report(id: str, format: str = Query("json", pattern="^(json|csv|html)$"), actor=Depends(identity)):
        manager().access(id, actor)
        manager().instructor(actor)
        session = manager().sessions.get(id)
        source = session.source_id if isinstance(session, Review) else id
        result = session_report(manager().archive, source)
        if isinstance(session, Review):
            result["review_annotations"] = session.annotations
        if format == "csv":
            return Response(report_csv(result), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="flowlens-{source}.csv"'})
        if format == "html":
            return HTMLResponse(report_html(result))
        return result

    @app.websocket("/api/v1/sessions/{id}/stream")
    async def stream(socket: WebSocket, id: str):
        await socket.accept()
        try:
            credentials = await asyncio.wait_for(socket.receive_json(), timeout=5)
            actor = manager().identity(credentials.get("token", ""))
            manager().access(id, actor)
            while True:
                if actor["expires"] < manager().wall_clock():
                    await socket.close(code=4401)
                    return
                await socket.send_json(manager().snapshot(id, actor))
                await asyncio.sleep(.2)
        except HTTPException as error:
            await socket.close(code=4403 if error.status_code == 403 else 4401)
        except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
            return

    dist = ROOT / "frontend" / "dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend():
        if not (dist / "index.html").exists():
            return HTMLResponse("<h1>ATC FlowLens</h1><p>Build the frontend with npm run build in frontend/.</p>", status_code=503)
        return FileResponse(dist / "index.html")

    return app


app = create_app()
