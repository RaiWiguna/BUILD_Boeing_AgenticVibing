"""Authorized replay views and deterministic pagination over immutable source observations."""

import base64
import binascii
from typing import Annotated, Any, Literal
from uuid import UUID

from flowlens.api.serializers import public_dto
from flowlens.auth.sessions import token_hash
from flowlens.contracts.models import (
    Mode,
    PlaybackState,
    RequestContext,
    SourceEvent,
    SourceManifest,
    Track,
)
from flowlens.core.errors import ContractError
from flowlens.replay.controls import Controls, View
from flowlens.replay.snapshots import digest
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Cursor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    scope: str
    time_ms: Annotated[int, Field(ge=0)]
    id: UUID


def cursor_read(raw: str, scope: str) -> Cursor:
    if len(raw) > 1024:
        raise ContractError("INVALID_INPUT")
    try:
        payload = base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_", validate=True)
        c = Cursor.model_validate_json(payload)
    except (binascii.Error, ValidationError, ValueError):
        raise ContractError("INVALID_INPUT") from None
    if c.scope != scope:
        raise ContractError("VERSION_CONFLICT")
    return c


def cursor_write(scope: str, time: int, identifier: UUID) -> str:
    c = Cursor(scope=scope, time_ms=time, id=identifier)
    return base64.urlsafe_b64encode(c.model_dump_json().encode()).decode().rstrip("=")


class Views:
    def __init__(self, controls: Controls) -> None:
        self.controls, self.replay = controls, controls.replay
        self.database, self.permissions = controls.database, controls.permissions

    def context(
        self, token: str, sid: UUID, view: View, mode: Mode, run: UUID | None = None
    ) -> RequestContext:
        return self.controls.context(token, sid, view=view, mode=mode, run_id=run)

    def project(self, context: RequestContext, value: object) -> dict[str, Any]:
        with self.database.begin() as uow:
            self.replay.authorize_inputs(uow, context)
            return public_dto(self.permissions, uow, context, value)

    def snapshot(
        self, token: str, sid: UUID, view: View, mode: Mode, run: UUID | None = None
    ) -> dict[str, Any]:
        c = self.context(token, sid, view, mode, run)
        return self.project(c, self.replay.snapshot(c))

    def catalogue(self, token: str, limit: int, after: UUID | None) -> dict[str, object]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            actor = self.permissions.sessions.authenticate(uow, token_hash(token))
            ids = [
                UUID(r[0])
                for r in uow.connection.execute(
                    "SELECT session_id FROM platform_grants WHERE account_id=? "
                    "AND capability='read' "
                    "AND revoked=0 AND expires_ms>? AND session_id>? ORDER BY session_id",
                    (str(actor.id), self.permissions.sessions.clock(), str(after) if after else ""),
                )
            ]
            items: list[dict[str, object]] = []
            for sid in ids:
                try:
                    self.permissions._capabilities(uow, actor.id, sid, "DEBRIEF")
                    legacy = uow.connection.execute(
                        "SELECT runtime_status FROM platform_legacy_sessions WHERE session_id=?",
                        (str(sid),),
                    ).fetchone()
                    if legacy:
                        items.append(
                            {
                                "session_id": str(sid),
                                "source_status": "NOT_EVALUABLE",
                                "archive_status": legacy[0],
                            }
                        )
                    else:
                        c = self.controls._context(uow, token, sid, "DEBRIEF")
                        source_count = uow.connection.execute(
                            "SELECT COUNT(*) FROM platform_sources "
                            "WHERE session_id=? AND revision=?",
                            (str(sid), c.input_revision),
                        ).fetchone()[0]
                        if not source_count:
                            continue
                        state = uow.connection.execute(
                            "SELECT archived FROM platform_playback "
                            "WHERE session_id=? AND viewer=''",
                            (str(sid),),
                        ).fetchone()
                        items.append(
                            {
                                "session_id": str(sid),
                                "source_status": "SOURCE_READY",
                                "archive_status": "ARCHIVED" if state and state[0] else "OPEN",
                            }
                        )
                except ContractError:
                    # Catalogue never advertises resources without a currently readable source.
                    continue
                if len(items) > limit:
                    break
            uow.commit()
            return {
                "items": items[:limit],
                "next_cursor": items[limit - 1]["session_id"] if len(items) > limit else None,
            }

    def sources(self, c: RequestContext, limit: int, cursor: str | None) -> dict[str, object]:
        scope = digest(
            {
                "kind": "sources",
                "actor": str(c.actor_id),
                "session": str(c.session_id),
                "revision": c.input_revision,
                "hash": c.input_hash,
            }
        )
        after = cursor_read(cursor, scope).id if cursor else None
        with self.database.begin() as uow:
            self.replay._inputs(uow, c)
            rows = uow.connection.execute(
                "SELECT payload FROM platform_sources "
                "WHERE session_id=? AND revision=? AND id>? ORDER BY id LIMIT ?",
                (str(c.session_id), c.input_revision, str(after) if after else "", limit + 1),
            ).fetchall()
            manifests = [SourceManifest.model_validate_json(r[0]) for r in rows]
            items = [public_dto(self.permissions, uow, c, m) for m in manifests[:limit]]
            return {
                "items": items,
                "next_cursor": cursor_write(scope, 0, manifests[limit - 1].id)
                if len(manifests) > limit
                else None,
            }

    def history(
        self, c: RequestContext, view: View, limit: int, cursor: str | None
    ) -> dict[str, object]:
        scope = digest(
            {
                "kind": "history",
                "actor": str(c.actor_id),
                "session": str(c.session_id),
                "run": str(c.analysis_run_id),
                "revision": c.input_revision,
                "hash": c.input_hash,
                "as_of_ms": c.as_of_ms,
                "mode": c.mode,
                "view": view,
            }
        )
        after = cursor_read(cursor, scope) if cursor else None
        events = self.replay.sources.read_events(c)
        page = [
            e
            for e in events
            if after is None or (e.event_time_ms, str(e.id)) > (after.time_ms, str(after.id))
        ]
        with self.database.begin() as uow:
            self.replay._inputs(uow, c)
            items = [public_dto(self.permissions, uow, c, e) for e in page[:limit]]
        return {
            "items": items,
            "as_of_ms": c.as_of_ms,
            "mode": c.mode,
            "next_cursor": cursor_write(scope, page[limit - 1].event_time_ms, page[limit - 1].id)
            if len(page) > limit
            else None,
        }

    def source(self, c: RequestContext, identifier: UUID) -> dict[str, Any]:
        return self.project(c, self.replay.sources.manifest(c, identifier))


class ControlBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    action: Literal["LEAD", "RELEASE", "PLAY", "PAUSE", "SEEK", "STEP", "SPEED", "ARCHIVE"]
    expected_version: Annotated[int, Field(ge=0, lt=2**63 - 1)]
    key: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")]
    view: Literal["LEADER", "LOCAL"] = "LEADER"
    value: int | float | None = None
    mode: Mode = "DEBRIEF"


class CatalogueItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    session_id: UUID
    source_status: Literal["SOURCE_READY", "NOT_EVALUABLE"]
    archive_status: Literal["OPEN", "ARCHIVED", "INTERRUPTED", "ENDED"]


class CataloguePage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    items: list[CatalogueItem]
    next_cursor: UUID | None


class SourcesPage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    items: list[SourceManifest]
    next_cursor: str | None


class HistoryPage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    items: list[Track | SourceEvent]
    next_cursor: str | None
    as_of_ms: Annotated[int, Field(ge=0)]
    mode: Mode


class ControlReply(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    state: PlaybackState
    version: Annotated[int, Field(ge=0)]
    archived: bool
