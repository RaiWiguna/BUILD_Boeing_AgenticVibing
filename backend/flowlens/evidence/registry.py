"""Scope/hash/time/range/quote verification; semantic interpretation belongs to B."""

from uuid import UUID, uuid5

from flowlens.assets.access import Assets
from flowlens.contracts.models import (
    Contract,
    Evidence,
    RequestContext,
    SourceEvent,
    Track,
    TranscriptSegment,
)
from flowlens.contracts.ports import UnitOfWork as TransactionPort
from flowlens.core.errors import ContractError
from flowlens.imports.metadata import PreparedImport
from flowlens.sources.store import Sources
from flowlens.storage.sqlite.database import UnitOfWork
from pydantic import ValidationError


class EvidenceRegistry:
    def index_track(self, context: RequestContext, track: Track, uow: UnitOfWork) -> Evidence:
        """Cache only a server-derived canonical source anchor, under current read authority."""
        checked = self.resolve_in_uow(
            context,
            Evidence(
                id=uuid5(
                    track.id,
                    f"geometry:{context.session_id}:{context.analysis_run_id}:{context.input_revision}",
                ),
                session_id=context.session_id,
                analysis_run_id=context.analysis_run_id,
                revision=context.input_revision,
                kind="TRACK",
                source_id=track.source_id,
                source_hash=track.source_hash,
                segment_id=track.id,
                start_ms=track.event_time_ms,
                end_ms=track.event_time_ms + 1,
                quote=None,
                span_start=None,
                span_end=None,
            ),
            uow,
        )
        old = uow.connection.execute(
            "SELECT payload FROM platform_evidence WHERE namespace='evidence' AND id=?",
            (str(checked.id),),
        ).fetchone()
        if old and old[0] != checked.model_dump_json():
            raise ContractError("IDEMPOTENCY_CONFLICT")
        if not old:
            uow.connection.execute(
                "INSERT INTO platform_evidence VALUES ('evidence',?,?,?,?,?,?,?)",
                (
                    str(checked.id),
                    str(checked.session_id),
                    str(checked.analysis_run_id) if checked.analysis_run_id else None,
                    checked.revision,
                    "Evidence",
                    checked.model_dump_json(),
                    str(checked.source_id),
                ),
            )
        return checked

    def __init__(
        self,
        sources: Sources,
        assets: Assets,
        *,
        transcript_namespace: str = "analysis.transcripts",
    ) -> None:
        self.sources, self.assets, self.transcript_namespace = sources, assets, transcript_namespace

    def _audio(
        self, ctx: RequestContext, e: Evidence, uow: UnitOfWork, *, require_access: bool = True
    ) -> Evidence:
        if (e.session_id, e.analysis_run_id, e.revision) != (
            ctx.session_id,
            ctx.analysis_run_id,
            ctx.input_revision,
        ):
            raise ContractError("ACCESS_DENIED")
        manifest = self.sources.permissions.require_source_rights(uow, ctx, e.source_id)
        if manifest.source_hash != e.source_hash:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        selected = next((a for a in manifest.assets if a.id == e.segment_id), None)
        if e.segment_id is None and len(manifest.assets) == 1:
            selected = manifest.assets[0]
        if selected is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if require_access:
            self.assets.locate(uow, ctx, selected.id)
        row = uow.connection.execute(
            "SELECT package_id,payload FROM platform_source_packages "
            "WHERE session_id=? AND source_id=?",
            (str(ctx.session_id), str(e.source_id)),
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        prepared = PreparedImport.model_validate_json(row["payload"])
        file = next((f for f in prepared.files if f.id == selected.id), None)
        if file is None or file.sha256 != selected.sha256:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        with self.sources.files.open(UUID(row["package_id"]), file):
            pass
        clock = next(f.clock for f in prepared.declaration.files if f.file_id == selected.id)
        low, high = clock.to_session_ms(0), clock.to_session_ms(selected.duration_ms)
        if low is None or high is None:
            raise ContractError("ALIGNMENT_REQUIRED")
        if (
            e.start_ms is None
            or e.end_ms is None
            or not low <= e.start_ms < e.end_ms <= high
            or e.end_ms > ctx.as_of_ms
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if e.quote is not None or e.span_start is not None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        return e

    def resolve(self, context: RequestContext, evidence: Evidence) -> Evidence:
        with self.sources.database.begin() as uow:
            return self.resolve_in_uow(context, evidence, uow)

    def resolve_in_uow(
        self,
        ctx: RequestContext,
        evidence: Evidence,
        uow: UnitOfWork,
        *,
        candidates: dict[UUID, Contract] | None = None,
    ) -> Evidence:
        try:
            e = Evidence.model_validate_json(evidence.model_dump_json())
        except ValidationError:
            raise ContractError("INVALID_INPUT") from None
        self.sources.permissions.enforce(uow, ctx)
        if (e.session_id, e.analysis_run_id, e.revision) != (
            ctx.session_id,
            ctx.analysis_run_id,
            ctx.input_revision,
        ):
            raise ContractError("ACCESS_DENIED")
        self.sources.require_right(
            uow,
            ctx,
            e.source_id,
            (
                "cloud_audio"
                if e.kind == "TRANSCRIPT" and candidates and e.segment_id in candidates
                else "cloud_context"
            )
            if "worker" in ctx.capabilities and e.kind != "AUDIO"
            else "local",
        )
        manifest = self.sources.permissions.require_source_rights(uow, ctx, e.source_id)
        if manifest.source_hash != e.source_hash:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if e.kind == "AUDIO":
            return self._audio(ctx, e, uow)
        if e.segment_id is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        pending = candidates.get(e.segment_id) if candidates else None
        if e.kind == "TRANSCRIPT":
            if pending is not None:
                record = pending
            else:
                try:
                    record = uow.repository(self.transcript_namespace).get(ctx, e.segment_id)
                except (KeyError, ValueError):
                    raise ContractError("EVIDENCE_UNAVAILABLE") from None
            if not isinstance(record, TranscriptSegment) or record.source_id != e.source_id:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if (record.session_id, record.analysis_run_id, record.revision) != (
                ctx.session_id,
                ctx.analysis_run_id,
                ctx.input_revision,
            ):
                raise ContractError("ACCESS_DENIED")
            if e.start_ms != record.start_ms or e.end_ms != record.end_ms:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            anchors = [
                anchor
                for anchor in record.evidence
                if anchor.kind == "AUDIO" and anchor.source_id == e.source_id
            ]
            if not anchors:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            for anchor in anchors:
                self._audio(ctx, anchor, uow, require_access=False)
            if not any(
                anchor.start_ms is not None
                and anchor.end_ms is not None
                and anchor.start_ms <= record.start_ms < record.end_ms <= anchor.end_ms
                for anchor in anchors
            ):
                raise ContractError("EVIDENCE_UNAVAILABLE")
            text = record.text
        elif e.kind in ("EVENT", "TRACK"):
            row = uow.connection.execute(
                "SELECT kind,payload FROM platform_records WHERE session_id=? AND revision=? "
                "AND run_id IS NULL AND id=? AND namespace IN ('source_events','tracks')",
                (str(ctx.session_id), ctx.input_revision, str(e.segment_id)),
            ).fetchone()
            if row is None:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            record = (Track if row["kind"] == "Track" else SourceEvent).model_validate_json(
                row["payload"]
            )
            if e.kind == "TRACK" and not isinstance(record, Track):
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if record.source_id != e.source_id or record.source_hash != e.source_hash:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            if e.start_ms is not None and (
                e.start_ms != record.event_time_ms or e.end_ms != record.event_time_ms + 1
            ):
                raise ContractError("EVIDENCE_UNAVAILABLE")
            text = record.statement
        else:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if record.event_time_ms > ctx.as_of_ms:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (
            pending is None
            and ctx.mode == "AS_KNOWN"
            and (record.available_time_ms is None or record.available_time_ms > ctx.as_of_ms)
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if e.quote is not None:
            if (
                e.span_start is None
                or e.span_end is None
                or not 0 <= e.span_start < e.span_end <= len(text)
                or text[e.span_start : e.span_end] != e.quote
            ):
                raise ContractError("EVIDENCE_UNAVAILABLE")
        elif e.span_start is not None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        return e

    def register(self, context: RequestContext, evidence: Evidence, uow: TransactionPort) -> UUID:
        if not isinstance(uow, UnitOfWork):
            raise ContractError("ACCESS_DENIED")
        if not ({"analysis", "review"} & set(context.capabilities)):
            raise ContractError("ACCESS_DENIED")
        return self.register_candidate(context, evidence, uow, {})

    def register_candidate(
        self,
        context: RequestContext,
        evidence: Evidence,
        uow: UnitOfWork,
        candidates: dict[UUID, Contract],
    ) -> UUID:
        if not ({"analysis", "review"} & set(context.capabilities)):
            raise ContractError("ACCESS_DENIED")
        checked = self.resolve_in_uow(context, evidence, uow, candidates=candidates)
        old = uow.connection.execute(
            "SELECT payload FROM platform_evidence WHERE namespace='evidence' AND id=?",
            (str(checked.id),),
        ).fetchone()
        if old:
            if old[0] != checked.model_dump_json():
                raise ContractError("IDEMPOTENCY_CONFLICT")
            return checked.id
        uow.connection.execute(
            "INSERT INTO platform_evidence VALUES ('evidence',?,?,?,?,?,?,?)",
            (
                str(checked.id),
                str(checked.session_id),
                str(checked.analysis_run_id) if checked.analysis_run_id else None,
                checked.revision,
                "Evidence",
                checked.model_dump_json(),
                str(checked.source_id),
            ),
        )
        return checked.id

    def get(self, context: RequestContext, identifier: UUID) -> Evidence:
        with self.sources.database.begin() as uow:
            self.sources.permissions.enforce(uow, context)
            row = uow.connection.execute(
                "SELECT payload FROM platform_evidence WHERE namespace='evidence' AND id=?",
                (str(identifier),),
            ).fetchone()
            if row is None:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            return self.resolve_in_uow(context, Evidence.model_validate_json(row[0]), uow)
