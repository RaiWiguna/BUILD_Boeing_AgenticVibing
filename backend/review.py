"""Playback over frozen public frames. Review controls never alter the source session."""
import copy
import uuid

from .models import Command, Role
from .session import SessionError
from .storage import Archive


class Review:
    def __init__(self, archive: Archive, source_id: str):
        self.id = uuid.uuid4().hex[:12]
        self.archive = archive
        self.source_id = source_id
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
