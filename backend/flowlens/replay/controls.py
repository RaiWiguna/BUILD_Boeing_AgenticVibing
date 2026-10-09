"""Durable training replay controls, independent local views and shared leadership."""

import math
import re
import sqlite3
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID, uuid4

from flowlens.auth.sessions import token_hash
from flowlens.contracts.models import Mode, PlaybackState, RequestContext, SourceManifest
from flowlens.core.errors import ContractError
from flowlens.replay.snapshots import Replay, digest
from flowlens.storage.sqlite.database import UnitOfWork

View = Literal["LEADER", "FOLLOW", "LOCAL"]


@dataclass(frozen=True)
class ControlResult:
    state: PlaybackState
    version: int
    archived: bool


class Controls:
    def __init__(self, replay: Replay) -> None:
        self.replay = replay
        self.permissions = replay.sources.permissions
        self.database = replay.sources.database

    def _context(
        self,
        uow: UnitOfWork,
        token: str,
        sid: UUID,
        mode: Mode,
        run: UUID | None = None,
    ) -> RequestContext:
        if type(sid) is not UUID or mode not in ("AS_KNOWN", "DEBRIEF"):
            raise ContractError("INVALID_INPUT")
        actor = self.permissions.sessions.authenticate(uow, token_hash(token))
        capabilities = self.permissions._capabilities(uow, actor.id, sid, mode)
        revision = self.permissions._input(uow, sid, run)
        ctx = RequestContext(
            actor_id=actor.id,
            capabilities=capabilities,
            session_id=sid,
            analysis_run_id=run,
            input_revision=revision["revision"],
            input_hash=revision["input_hash"],
            as_of_ms=0,
            mode=mode,
            request_id=uuid4(),
        )
        self.permissions._receipt(uow, ctx, "HUMAN", token_hash(token))
        self.replay._inputs(uow, ctx)
        return ctx

    def _duration(self, uow: UnitOfWork, c: RequestContext) -> tuple[int, list[int]]:
        events, _ = self.replay._inputs(uow, c)
        steps = sorted(
            {
                max(e.event_time_ms, e.available_time_ms)
                if c.mode == "AS_KNOWN" and e.available_time_ms is not None
                else e.event_time_ms
                for e in events
                if c.mode == "DEBRIEF" or e.available_time_ms is not None
            }
        )
        times = [
            0,
            *steps,
            *(e.event_time_ms for e in events),
            *(e.available_time_ms for e in events if e.available_time_ms is not None),
        ]
        for row in uow.connection.execute(
            "SELECT payload FROM platform_sources WHERE session_id=? AND revision=?",
            (str(c.session_id), c.input_revision),
        ):
            times.extend(a.duration_ms for a in SourceManifest.model_validate_json(row[0]).assets)
        return max(times), steps

    def _row(self, uow: UnitOfWork, c: RequestContext, viewer: str) -> sqlite3.Row:
        row = uow.connection.execute(
            "SELECT * FROM platform_playback WHERE session_id=? AND viewer=?",
            (str(c.session_id), viewer),
        ).fetchone()
        if row is None:
            cursor = 0
            if viewer:
                shared = self._row(uow, c, "")
                cursor = self._effective(uow, c, shared).cursor_ms
            state = PlaybackState(
                session_id=c.session_id,
                analysis_run_id=None,
                revision=c.input_revision,
                status="PAUSED",
                cursor_ms=cursor,
                speed=1.0,
                leader_id=None,
                view="LOCAL" if viewer else "LEADER",
            )
            uow.connection.execute(
                "INSERT INTO platform_playback VALUES (?,?,?,0,?,NULL,0)",
                (
                    str(c.session_id),
                    viewer,
                    state.model_dump_json(),
                    self.permissions.sessions.clock(),
                ),
            )
            return self._row(uow, c, viewer)
        return cast(sqlite3.Row, row)

    def _effective(self, uow: UnitOfWork, c: RequestContext, row: sqlite3.Row) -> PlaybackState:
        state = PlaybackState.model_validate_json(row["payload"])
        duration, _ = self._duration(uow, c)
        cursor = state.cursor_ms
        if state.status == "PLAYING":
            cursor = min(
                duration,
                cursor
                + int(max(0, self.permissions.sessions.clock() - row["anchor_ms"]) * state.speed),
            )
        status = "ENDED" if state.status == "PLAYING" and cursor >= duration else state.status
        leader = state.leader_id
        if leader is not None:
            try:
                actor = self.permissions.sessions.authenticate(uow, row["leader_digest"])
                caps = self.permissions._capabilities(uow, actor.id, c.session_id, c.mode)
                if actor.id != leader or "review" not in caps:
                    raise ContractError("ACCESS_DENIED")
            except ContractError:
                # Lost leader authority cannot justify elapsed playback. Keep the
                # last durable cursor, as on crash recovery, until a new leader acts.
                leader, status, cursor = None, "PAUSED", state.cursor_ms
        return PlaybackState.model_validate_json(
            state.model_copy(
                update={"cursor_ms": cursor, "status": status, "leader_id": leader}
            ).model_dump_json()
        )

    def get(self, token: str, session_id: UUID, *, view: View = "FOLLOW") -> ControlResult:
        if view not in ("LEADER", "FOLLOW", "LOCAL"):
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            c = self._context(uow, token, session_id, "DEBRIEF")
            shared = self._row(uow, c, "")
            row = self._row(uow, c, str(c.actor_id)) if view == "LOCAL" else shared
            state = self._effective(uow, c, row)
            if view == "LEADER" and state.leader_id != c.actor_id:
                raise ContractError("ACCESS_DENIED")
            state = state.model_copy(update={"view": view})
            result = ControlResult(state, row["version"], bool(shared["archived"]))
            uow.commit()
            return result

    def context(
        self,
        token: str,
        session_id: UUID,
        *,
        view: View = "FOLLOW",
        mode: Mode = "DEBRIEF",
        run_id: UUID | None = None,
    ) -> RequestContext:
        if view not in ("LEADER", "FOLLOW", "LOCAL"):
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            c = self._context(uow, token, session_id, mode, run_id)
            row = self._row(uow, c, str(c.actor_id) if view == "LOCAL" else "")
            state = self._effective(uow, c, row)
            if view == "LEADER" and state.leader_id != c.actor_id:
                raise ContractError("ACCESS_DENIED")
            c = c.model_copy(update={"as_of_ms": state.cursor_ms})
            self.permissions._receipt(uow, c, "HUMAN", token_hash(token))
            uow.commit()
            return c

    def command(
        self,
        token: str,
        session_id: UUID,
        action: str,
        *,
        expected_version: int,
        key: str,
        view: View = "LEADER",
        value: int | float | None = None,
        mode: Mode = "DEBRIEF",
    ) -> ControlResult:
        if (
            view not in ("LEADER", "LOCAL")
            or action
            not in ("LEAD", "RELEASE", "PLAY", "PAUSE", "SEEK", "STEP", "SPEED", "ARCHIVE")
            or type(expected_version) is not int
            or not 0 <= expected_version < 2**63 - 1
            or type(key) is not str
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key)
            or (action == "SEEK" and (type(value) is not int or value < 0))
            or (
                action == "SPEED"
                and (
                    type(value) not in (int, float)
                    or value is None
                    or not math.isfinite(value)
                    or not 0 < value <= 16
                )
            )
            or (action not in ("SEEK", "SPEED") and value is not None)
            or (view == "LOCAL" and action in ("LEAD", "RELEASE", "ARCHIVE"))
        ):
            raise ContractError("INVALID_INPUT")
        fingerprint = digest(
            {
                "action": action,
                "version": expected_version,
                "view": view,
                "value": value,
                "mode": mode,
            }
        )
        with self.database.begin() as uow:
            c = self._context(uow, token, session_id, mode)
            if view == "LEADER":
                c.require("review", session_id)
            old = uow.connection.execute(
                "SELECT * FROM platform_control_receipts "
                "WHERE session_id=? AND actor_id=? AND key=?",
                (str(session_id), str(c.actor_id), key),
            ).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return ControlResult(
                    PlaybackState.model_validate_json(old["payload"]),
                    old["version"],
                    bool(old["archived"]),
                )
            shared = self._row(uow, c, "")
            viewer = str(c.actor_id) if view == "LOCAL" else ""
            row = self._row(uow, c, viewer)
            if row["version"] != expected_version:
                raise ContractError("VERSION_CONFLICT")
            if view == "LEADER" and shared["archived"]:
                raise ContractError("ACCESS_DENIED")
            state = self._effective(uow, c, row)
            if view == "LEADER" and (
                (action == "LEAD" and state.leader_id not in (None, c.actor_id))
                or (action != "LEAD" and state.leader_id != c.actor_id)
            ):
                raise ContractError("ACCESS_DENIED")
            duration, steps = self._duration(uow, c)
            updates: dict[str, object] = {"view": view}
            leader_digest = row["leader_digest"]
            archived = bool(shared["archived"])
            if action == "LEAD":
                updates["leader_id"], leader_digest = c.actor_id, token_hash(token)
            elif action in ("RELEASE", "ARCHIVE"):
                updates.update(status="PAUSED")
                if action == "RELEASE":
                    updates["leader_id"], leader_digest = None, None
                else:
                    archived = True
            elif action == "PLAY":
                updates["status"] = "PLAYING" if state.cursor_ms < duration else "ENDED"
            elif action == "PAUSE":
                updates["status"] = "PAUSED"
            elif action == "SEEK":
                if value is None or value > duration:
                    raise ContractError("INVALID_INPUT")
                updates.update(cursor_ms=value, status="PAUSED")
            elif action == "STEP":
                updates.update(
                    cursor_ms=next((t for t in steps if t > state.cursor_ms), duration),
                    status="PAUSED",
                )
            elif action == "SPEED":
                updates["speed"] = float(value) if value is not None else state.speed
            state = PlaybackState.model_validate_json(
                state.model_copy(update=updates).model_dump_json()
            )
            version = row["version"] + 1
            uow.connection.execute(
                "UPDATE platform_playback SET payload=?,version=?,anchor_ms=?,"
                "leader_digest=?,archived=? "
                "WHERE session_id=? AND viewer=?",
                (
                    state.model_dump_json(),
                    version,
                    self.permissions.sessions.clock(),
                    leader_digest,
                    int(archived) if view == "LEADER" else 0,
                    str(session_id),
                    viewer,
                ),
            )
            if view == "LEADER":
                uow.enqueue_event(c, state)
            uow.audit(c, "REPLAY_CONTROL", session_id)
            uow.connection.execute(
                "INSERT INTO platform_control_receipts VALUES (?,?,?,?,?,?,?,?)",
                (
                    str(session_id),
                    str(c.actor_id),
                    key,
                    fingerprint,
                    state.model_dump_json(),
                    version,
                    int(archived),
                    viewer,
                ),
            )
            uow.commit()
            return ControlResult(state, version, archived)

    def recover(self) -> None:
        """Startup does not resume playback or infer elapsed downtime after a crash."""
        with self.database.begin() as uow:
            for row in uow.connection.execute("SELECT * FROM platform_playback").fetchall():
                state = PlaybackState.model_validate_json(row["payload"])
                if state.status == "PLAYING":
                    state = state.model_copy(update={"status": "PAUSED"})
                    uow.connection.execute(
                        "UPDATE platform_playback SET payload=?,version=version+1,anchor_ms=? "
                        "WHERE session_id=? AND viewer=?",
                        (
                            state.model_dump_json(),
                            self.permissions.sessions.clock(),
                            row["session_id"],
                            row["viewer"],
                        ),
                    )
            uow.commit()
