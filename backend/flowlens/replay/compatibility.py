"""Explicit audited legacy alias/history metadata; quarantined content is not replay input."""

from typing import Literal
from uuid import UUID

from flowlens.auth.permissions import Permissions
from flowlens.auth.sessions import token_hash
from flowlens.core.errors import ContractError
from pydantic import BaseModel, ConfigDict


class LegacyFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    sim_ms: int
    sequence: int


class LegacySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    session_id: UUID
    legacy_id: str
    runtime_status: str
    source_status: Literal["NOT_EVALUABLE"] = "NOT_EVALUABLE"
    available_time_ms: None = None
    frames: list[LegacyFrame]
    events_count: int
    commands_count: int


class LegacyHistory:
    def __init__(self, permissions: Permissions) -> None:
        self.permissions = permissions

    def read(self, token: str, alias: str | UUID, *, limit: int = 100) -> LegacySummary:
        if (
            type(alias) not in (str, UUID)
            or type(limit) is not int
            or not 1 <= limit <= 100
            or (isinstance(alias, str) and not 1 <= len(alias) <= 128)
        ):
            raise ContractError("INVALID_INPUT")
        with self.permissions.database.begin() as uow:
            actor = self.permissions.sessions.authenticate(uow, token_hash(token))
            column = "session_id" if isinstance(alias, UUID) else "legacy_id"
            # Fixed column alternatives, never arbitrary client SQL or implicit UUID coercion.
            query = (
                "SELECT * FROM platform_legacy_sessions WHERE session_id=?"
                if column == "session_id"
                else "SELECT * FROM platform_legacy_sessions WHERE legacy_id=?"
            )
            row = uow.connection.execute(query, (str(alias),)).fetchone()
            if row is None:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            session = UUID(row["session_id"])
            self.permissions._capabilities(uow, actor.id, session, "DEBRIEF")
            frames = [
                LegacyFrame(sim_ms=r[0], sequence=r[1])
                for r in uow.connection.execute(
                    "SELECT sim_ms,sequence FROM platform_legacy_frames WHERE session_id=? "
                    "ORDER BY sim_ms,sequence LIMIT ?",
                    (row["legacy_id"], limit),
                )
            ]
            events = uow.connection.execute(
                "SELECT COUNT(*) FROM platform_legacy_events WHERE session_id=?",
                (row["legacy_id"],),
            ).fetchone()[0]
            commands = uow.connection.execute(
                "SELECT COUNT(*) FROM platform_legacy_commands WHERE session_id=?",
                (row["legacy_id"],),
            ).fetchone()[0]
            return LegacySummary(
                session_id=session,
                legacy_id=row["legacy_id"],
                runtime_status=row["runtime_status"],
                frames=frames,
                events_count=events,
                commands_count=commands,
            )
