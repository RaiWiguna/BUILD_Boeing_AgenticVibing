"""Playback over frozen public frames. Review controls never alter the source session."""
import copy
import uuid
from collections.abc import Mapping
from typing import Any

from .models import Command, Role
from .replay_import import ArchiveReplayEventSource, SQLiteReplayArchiveReader
from .replay_source import ObservedStateReducer, ReplaySourceReader
from .session import SessionError
from .storage import Archive


def imported_replay_frame(
    archive: Archive,
    source_session_id: str,
    at_ms: int,
    analysis_id: str | None = None,
) -> dict[str, Any] | None:
    """Build a public source projection and optionally join one explicit analysis frame."""
    if at_ms < 0:
        raise ValueError("at_ms must be nonnegative")
    reader = SQLiteReplayArchiveReader(archive)
    metadata = reader.metadata(source_session_id)
    if metadata is None:
        return None

    source = ArchiveReplayEventSource(archive, source_session_id)
    manifest = source.manifest()
    records = tuple(
        record for record in source.read(-1, at_ms)
        if record.event.sim_ms is not None
        and record.event.sim_ms <= at_ms
        and (record.event.received_ms is None or record.event.received_ms <= at_ms)
    )
    observed = ObservedStateReducer(ReplaySourceReader(source)).build_state(at_ms, records=records)
    source_state = observed.public_projection()
    # source_ref can be a local locator. It remains internal to the reader/reducer.
    source_state.pop("source_ref", None)
    frame_ms = max((record.event.sim_ms for record in records if record.event.sim_ms is not None), default=None)

    analysis_exists = analysis_id is not None and any(
        item.get("id") == analysis_id for item in metadata.get("analyses", ())
    )
    derived_read = reader.frame(source_session_id, at_ms, analysis_id) if analysis_exists else None
    derived_frame: Mapping[str, Any] | None = None
    if isinstance(derived_read, Mapping):
        stored_frame = derived_read.get("state")
        derived_frame = stored_frame if isinstance(stored_frame, Mapping) else None
    if isinstance(derived_frame, Mapping) and isinstance(derived_read, Mapping):
        derived_state = derived_frame.get("state")
        if isinstance(derived_state, Mapping):
            source_state.update(derived_state)
        frame_ms = derived_read.get("frame_ms", frame_ms)

    source_state["layout"] = manifest.layout.model_dump(mode="json")
    source_state["analysis_id"] = analysis_id if analysis_exists else None
    source_state["analysis_status"] = (
        derived_frame.get("status", "unavailable") if isinstance(derived_frame, Mapping) else "unavailable"
    )
    derived_available = (
        isinstance(derived_frame, Mapping)
        and derived_frame.get("status") == "evaluated"
        and isinstance(derived_frame.get("detector_result"), Mapping)
    )
    result = derived_frame.get("detector_result") if derived_available and isinstance(derived_frame, Mapping) else None
    source_state["predictions"] = result.get("predictions") if isinstance(result, Mapping) else None
    source_state["alerts"] = (
        derived_frame.get("alerts") if derived_available and isinstance(derived_frame, Mapping) else None
    )
    source_state["lifecycle_events"] = (
        derived_frame.get("lifecycle_events") if derived_available and isinstance(derived_frame, Mapping) else None
    )
    source_state["complexity"] = None

    return {
        "source_session_id": source_session_id,
        "requested_ms": at_ms,
        "frame_ms": frame_ms,
        "analysis_id": analysis_id if analysis_exists else None,
        "analysis_status": source_state["analysis_status"],
        "state": source_state,
    }


class Review:
    def __init__(self, archive: Archive, source_id: str):
        self.id = uuid.uuid4().hex[:12]
        self.archive = archive
        self.source_id = source_id
        imported_source = archive.replay_source(source_id)
        self.imported = imported_source is not None
        if self.imported:
            event_source = ArchiveReplayEventSource(archive, source_id)
            manifest = event_source.manifest()
            event_times = [
                record.event.sim_ms for record in event_source.read(-1)
                if record.event.sim_ms is not None
            ]
            coverage_times = [interval.end_ms for interval in (manifest.coverage.intervals or [])]
            available_times = event_times or coverage_times
            if not available_times:
                raise SessionError(404, "Replay source has no aligned time range")
            self.end_ms = max(available_times)
        else:
            latest = archive.frame(source_id)
            if not latest:
                raise SessionError(404, "Source session has no recorded frame")
            self.end_ms = latest[0]["sim_ms"]
        self.now_ms = 0
        self.status = "PAUSED"
        self.speed = 1.0
        self.revision = 0
        self.sequence = 0
        self.commands: dict[str, tuple[dict, dict]] = {}
        self.annotations: list[dict] = []

    def snapshot(self) -> dict:
        if self.imported:
            frame = imported_replay_frame(self.archive, self.source_id, self.now_ms)
            if frame is None:
                raise SessionError(404, "Replay source not available")
            state = frame["state"]
            replay_metadata = SQLiteReplayArchiveReader(self.archive).metadata(self.source_id) or {}
            tracks = state.get("tracks", {})
            if isinstance(tracks, Mapping):
                track_items = [
                    {**track, "stale": state.get("track_freshness", {}).get(object_id) == "stale"}
                    for object_id, track in tracks.items()
                ]
            else:
                track_items = []
            return {
                "session_id": self.id,
                "source_session_id": self.source_id,
                "kind": "review",
                "sequence": self.sequence,
                "sim_ms": frame["frame_ms"],
                "revision": self.revision,
                "status": self.status,
                "speed": self.speed,
                "metadata": {
                    "id": self.source_id,
                    "kind": "replay_source",
                    "source_id": replay_metadata.get("source_id"),
                    "manifest": replay_metadata.get("manifest"),
                    "analyses": replay_metadata.get("analyses", []),
                },
                "layout": state.get("layout"),
                "tracks": track_items,
                "clearances": state.get("clearances", []),
                "requests": state.get("requests", []),
                "predictions": state.get("predictions"),
                "runway": state.get("runway"),
                "alerts": state.get("alerts"),
                "native_source_alerts": state.get("native_source_alerts", []),
                "events": [],
                "acknowledgements": [],
                "assessments": [],
                "complexity": None,
                "error": None,
                "review_end_ms": self.end_ms,
                "playback_ms": self.now_ms,
                "review_annotations": self.annotations,
                "analysis_id": state.get("analysis_id"),
                "analysis_status": state.get("analysis_status"),
            }
        frame = self.archive.frame(self.source_id, self.now_ms)
        if frame is None:
            raise SessionError(404, "Review frame not available")
        public = copy.deepcopy(frame[0])
        public.update(session_id=self.id, kind="review", source_session_id=self.source_id,
                      sequence=self.sequence, revision=self.revision, status=self.status,
                      speed=self.speed, review_end_ms=self.end_ms, playback_ms=self.now_ms,
                      review_annotations=self.annotations)
        return public

    def execute(self, command: Command, role: Role, actor: str) -> dict:
        if role != Role.INSTRUCTOR:
            raise SessionError(403, "Only instructors control the shared review")
        request = {"command": command.model_dump(mode="json"), "actor": actor}
        prior = self.commands.get(command.command_id)
        if prior:
            if prior[0] != request:
                raise SessionError(409, "Command ID reused")
            return prior[1]
        if command.expected_revision != self.revision:
            raise SessionError(409, "Review revision changed")
        if command.type == "SEEK":
            if not 0 <= float(command.value or 0)*1000 <= self.end_ms:
                raise SessionError(422, "Seek must be inside the recorded session")
            self.now_ms = int(float(command.value or 0)*1000)
        elif command.type == "START":
            self.status = "RUNNING"
        elif command.type in {"PAUSE", "END"}:
            self.status = "PAUSED"
        elif command.type == "SET_SPEED":
            self.speed = float(command.value or 1)
        else:
            raise SessionError(409, "Review is read-only; create a training branch for alternative instructions")
        self.revision += 1
        self.sequence += 1
        response = {"session_id": self.id, "revision": self.revision, "status": self.status}
        self.commands[command.command_id] = (request, response)
        return response

    def advance(self, ticks: int = 1, persist: bool = True):
        if self.status == "RUNNING":
            self.now_ms = min(self.end_ms, self.now_ms+ticks*100)
            self.sequence += 1
            if self.now_ms >= self.end_ms:
                self.status = "PAUSED"
