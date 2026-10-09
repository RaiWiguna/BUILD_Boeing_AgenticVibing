"""Deterministic observed replay; analysis projections are supplied through frozen ports."""

import hashlib
import json
from collections.abc import Callable, Sequence
from uuid import UUID

from flowlens.api.serializers import check_projection
from flowlens.contracts.models import (
    Finding,
    MemoryEvent,
    Quality,
    RequestContext,
    Snapshot,
    SourceEvent,
    Track,
)
from flowlens.core.errors import ContractError
from flowlens.sources.store import Sources
from flowlens.storage.sqlite.database import UnitOfWork
from pydantic import ValidationError

REDUCER_VERSION = "observed-replay-1"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ordered[T: (SourceEvent, MemoryEvent, Finding)](
    context: RequestContext, rows: Sequence[T]
) -> list[T]:
    """Stable event-time/UUID order, with exact duplicate retry and conflicting ID denial."""
    unique: dict[object, T] = {}
    for original in rows:
        try:
            row = type(original).model_validate_json(original.model_dump_json())
        except (ValidationError, ValueError):
            raise ContractError("INVALID_INPUT") from None
        if (row.session_id, row.revision) != (context.session_id, context.input_revision) or (
            row.analysis_run_id != context.analysis_run_id
            and not (isinstance(row, SourceEvent) and row.analysis_run_id is None)
        ):
            raise ContractError("ACCESS_DENIED")
        identifier = row.id
        if identifier in unique and unique[identifier] != row:
            raise ContractError("VERSION_CONFLICT")
        unique[identifier] = row
    return sorted(
        [
            r
            for r in unique.values()
            if r.event_time_ms <= context.as_of_ms
            and (
                context.mode == "DEBRIEF"
                or (r.available_time_ms is not None and r.available_time_ms <= context.as_of_ms)
            )
        ],
        key=lambda r: (r.event_time_ms, str(r.id)),
    )


def reduce(
    context: RequestContext,
    events: Sequence[SourceEvent],
    analysis: Snapshot | None,
    *,
    sequence: int,
    checkpoint: Snapshot | None = None,
) -> Snapshot:
    """A projects source events; B remains owner of memory/finding semantics."""
    if analysis is not None:
        try:
            analysis = Snapshot.model_validate_json(analysis.model_dump_json())
            check_projection(analysis, context)
        except (ValidationError, ValueError):
            raise ContractError("ACCESS_DENIED") from None
    source = ordered(context, [*events, *(analysis.events if analysis else [])])
    source_fields = SourceEvent.model_fields
    source = [
        SourceEvent.model_validate({k: v for k, v in r.model_dump().items() if k in source_fields})
        for r in source
    ]
    memory = ordered(context, analysis.memory if analysis else [])
    findings = ordered(context, analysis.findings if analysis else [])
    if checkpoint is not None:
        # Caller verifies version, immutable-input fingerprint, mode/run and checksum.
        source = ordered(context, [*checkpoint.events, *source])
        memory = ordered(context, [*checkpoint.memory, *memory])
        findings = ordered(context, [*checkpoint.findings, *findings])
    qualities: list[Quality] = [r.quality for r in source]
    if analysis and (analysis.memory or analysis.findings):
        qualities.append(analysis.quality)
    quality: Quality = next(
        (q for q in ("CONFLICTING", "MISSING", "AMBIGUOUS") if q in qualities),
        "SUPPORTED" if qualities else "MISSING",
    )
    return Snapshot(
        session_id=context.session_id,
        analysis_run_id=context.analysis_run_id,
        revision=context.input_revision,
        as_of_ms=context.as_of_ms,
        mode=context.mode,
        sequence=sequence,
        events=source,
        memory=memory,
        findings=findings,
        quality=quality,
    )


class Replay:
    def __init__(
        self,
        sources: Sources,
        *,
        snapshot_reader: Callable[[RequestContext], Snapshot] | None = None,
        reducer_version: str = REDUCER_VERSION,
    ) -> None:
        if not reducer_version or len(reducer_version) > 100:
            raise ValueError("Invalid reducer version")
        self.sources, self.snapshot_reader, self.reducer_version = (
            sources,
            snapshot_reader,
            reducer_version,
        )

    def _inputs(self, uow: UnitOfWork, context: RequestContext) -> tuple[list[SourceEvent], int]:
        self.sources.permissions.enforce(uow, context)
        context.require("read", context.session_id)
        if "worker" in context.capabilities:
            raise ContractError("ACCESS_DENIED")
        for row in uow.connection.execute(
            "SELECT id FROM platform_sources WHERE session_id=? AND revision=?",
            (str(context.session_id), context.input_revision),
        ):
            self.sources.require_right(uow, context, UUID(row[0]), "reviewer")
        rows = uow.connection.execute(
            "SELECT kind,payload FROM platform_records WHERE session_id=? AND revision=? "
            "AND run_id IS NULL AND namespace IN ('source_events','tracks')",
            (str(context.session_id), context.input_revision),
        )
        events = [
            (Track if r[0] == "Track" else SourceEvent).model_validate_json(r[1]) for r in rows
        ]
        events.sort(key=lambda r: (r.event_time_ms, str(r.id)))
        sequence = int(
            uow.connection.execute(
                "SELECT COALESCE(MAX(sequence),0) FROM platform_events WHERE session_id=?",
                (str(context.session_id),),
            ).fetchone()[0]
        )
        return events, sequence

    def snapshot(self, context: RequestContext, *, checkpoints: bool = True) -> Snapshot:
        database = self.sources.database
        with database.begin() as uow:
            events, sequence = self._inputs(uow, context)
        # B may read repositories through ports. Never hold a replay/DB lock here.
        analysis = self.snapshot_reader(context) if self.snapshot_reader else None
        result = reduce(context, events, analysis, sequence=sequence)
        if analysis is not None and analysis.events:
            observed = {r.id: r for r in reduce(context, events, None, sequence=sequence).events}
            if any(observed.get(r.id) != r for r in analysis.events):
                raise ContractError("ACCESS_DENIED")
        fingerprint = digest(
            {
                "input": context.input_hash,
                "sequence": sequence,
                "events": [r.model_dump(mode="json") for r in events],
                "analysis": (
                    {
                        k: v
                        for k, v in analysis.model_dump(mode="json").items()
                        if k not in ("as_of_ms", "mode", "sequence")
                    }
                    if analysis
                    else None
                ),
            }
        )
        key = digest(
            {
                "version": self.reducer_version,
                "input": fingerprint,
                "run": str(context.analysis_run_id),
                "mode": context.mode,
            }
        )
        with database.begin() as uow:
            current, current_sequence = self._inputs(uow, context)
            if current != events or current_sequence != sequence:
                raise ContractError("VERSION_CONFLICT")
            if checkpoints:
                row = uow.connection.execute(
                    "SELECT * FROM platform_replay_snapshots WHERE session_id=? AND revision=? "
                    "AND cache_key=? AND checkpoint_ms<=? ORDER BY checkpoint_ms DESC LIMIT 1",
                    (str(context.session_id), context.input_revision, key, context.as_of_ms),
                ).fetchone()
                if row:
                    try:
                        base = Snapshot.model_validate_json(row["payload"])
                        if digest(base.model_dump(mode="json")) != row["payload_hash"] or (
                            base.session_id,
                            base.revision,
                            base.analysis_run_id,
                            base.mode,
                            base.as_of_ms,
                            base.sequence,
                        ) != (
                            context.session_id,
                            context.input_revision,
                            context.analysis_run_id,
                            context.mode,
                            row["checkpoint_ms"],
                            sequence,
                        ):
                            raise ValueError("Invalid checkpoint")
                        # Exact checkpoints already reconstructed and compared against the
                        # current inputs need no second full dedup/validation pass. Older
                        # checkpoints still follow the original merge path.
                        if base != result:
                            result = reduce(
                                context, events, analysis, sequence=sequence, checkpoint=base
                            )
                    except (ValidationError, ValueError):
                        # Derived cache can be rebuilt; it is never an authoritative source.
                        pass
                uow.connection.execute(
                    "INSERT INTO platform_replay_snapshots VALUES (?,?,?,?,?,?,?) "
                    "ON CONFLICT(session_id,revision,cache_key,checkpoint_ms) DO UPDATE SET "
                    "payload=excluded.payload,payload_hash=excluded.payload_hash",
                    (
                        str(context.session_id),
                        context.input_revision,
                        key,
                        context.as_of_ms,
                        self.reducer_version,
                        result.model_dump_json(),
                        digest(result.model_dump(mode="json")),
                    ),
                )
                uow.commit()
        return result
