"""Typed durable event delivery with authoritative snapshots and fail-closed live resync."""

from datetime import UTC, datetime
from typing import Any

from flowlens.api.serializers import check_projection, public_dto
from flowlens.contracts.models import (
    Finding,
    JobProgress,
    MemoryEvent,
    Option,
    PlaybackState,
    RequestContext,
    ResyncRequired,
    Review,
    Snapshot,
    SourceQualityChanged,
    StreamEvent,
    TranscriptSegment,
)
from flowlens.core.errors import ContractError
from flowlens.replay.controls import View
from flowlens.replay.views import Views
from pydantic import ValidationError

TYPES: tuple[
    tuple[
        type[PlaybackState]
        | type[JobProgress]
        | type[TranscriptSegment]
        | type[MemoryEvent]
        | type[Finding]
        | type[Option]
        | type[Review]
        | type[SourceQualityChanged],
        str,
    ],
    ...,
] = (
    (PlaybackState, "PLAYBACK_CHANGED"),
    (JobProgress, "JOB_PROGRESS"),
    (TranscriptSegment, "TRANSCRIPT_REVISION"),
    (MemoryEvent, "MEMORY_CHANGED"),
    (Finding, "FINDING_CHANGED"),
    (Option, "OPTION_READY"),
    (Review, "REVIEW_ADDED"),
    (SourceQualityChanged, "SOURCE_QUALITY_CHANGED"),
)


def envelope(c: RequestContext, sequence: int, kind: str, payload: object) -> StreamEvent:
    # Revalidate dynamic payload/type mapping through the frozen model, never SDK/raw JSON output.
    return StreamEvent.model_validate(
        {
            "session_id": c.session_id,
            "analysis_run_id": c.analysis_run_id,
            "sequence": sequence,
            "type": kind,
            "recorded_at": datetime.now(UTC),
            "payload": payload,
        }
    )


class Stream:
    def __init__(self, views: Views, *, view: View = "FOLLOW") -> None:
        self.views, self.view = views, view

    def frame(
        self, c: RequestContext, snapshot: Snapshot, after: int, *, incremental: bool
    ) -> list[dict[str, Any]]:
        if snapshot.sequence < 1:
            # Committed source sessions start with a durable SOURCE_QUALITY_CHANGED event.
            raise ContractError("NOT_EVALUABLE")
        sequence = snapshot.sequence
        pending: list[StreamEvent] = []
        gap = after != 0 and after != sequence and not incremental
        with self.views.database.begin() as uow:
            _, current = self.views.replay._inputs(uow, c)
            if current != sequence:
                raise ContractError("VERSION_CONFLICT")
            if incremental and after != sequence:
                rows = uow.connection.execute(
                    "SELECT * FROM platform_events WHERE session_id=? "
                    "AND sequence>? AND sequence<=? "
                    "ORDER BY sequence LIMIT 101",
                    (str(c.session_id), after, sequence),
                ).fetchall()
                gap = after > sequence or sequence - after > 100 or len(rows) != sequence - after
                for row in rows:
                    if row["revision"] != c.input_revision or row["run_id"] not in (
                        None,
                        str(c.analysis_run_id),
                    ):
                        gap = True
                        continue
                    parsed = False
                    for model, kind in TYPES:
                        try:
                            value = model.model_validate_json(row["payload"])
                        except ValidationError:
                            continue
                        parsed = True
                        if isinstance(value, PlaybackState):
                            if c.analysis_run_id is not None:
                                value = value.model_copy(
                                    update={"analysis_run_id": c.analysis_run_id}
                                )
                            # A LOCAL viewer must never be moved by another user's shared playback.
                            # A local snapshot replaces state across this sequence hole.
                            if self.view == "LOCAL":
                                gap = True
                                break
                            value = value.model_copy(update={"view": self.view})
                        elif (
                            isinstance(value, SourceQualityChanged)
                            and c.analysis_run_id is not None
                        ):
                            value = value.model_copy(update={"analysis_run_id": c.analysis_run_id})
                        try:
                            check_projection(value, c)
                        except ContractError:
                            gap = True
                            break
                        pending.append(envelope(c, row["sequence"], kind, value))
                        break
                    if not parsed:
                        gap = True
            if gap:
                pending = [
                    envelope(
                        c,
                        sequence,
                        "RESYNC_REQUIRED",
                        ResyncRequired(
                            session_id=c.session_id,
                            analysis_run_id=c.analysis_run_id,
                            revision=c.input_revision,
                            reason="SEQUENCE_GAP",
                            snapshot_sequence=sequence,
                        ),
                    )
                ]
            pending.append(envelope(c, sequence, "SNAPSHOT", snapshot))
            return [public_dto(self.views.permissions, uow, c, event) for event in pending]
