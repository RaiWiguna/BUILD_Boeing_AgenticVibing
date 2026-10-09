"""A-owned source geometry rules coordinator; never a semantic analysis implementation."""

import re
from collections.abc import Callable
from typing import Literal
from uuid import UUID, uuid5

from flowlens.contracts.models import (
    Evidence,
    OpenLoop,
    RequestContext,
    Scoped,
    SourceEvent,
    ToolRequest,
    Track,
)
from flowlens.contracts.ports import ContextReader
from flowlens.core.errors import ContractError
from flowlens.evidence.registry import EvidenceRegistry
from flowlens.geometry.alerts import (
    Acknowledgement,
    AlertRevision,
    reduce_signal,
    reduce_source_group,
    seen,
)
from flowlens.geometry.indicators import (
    Indicators,
    active_duration,
    activity_records,
    validate_loop,
)
from flowlens.geometry.kernel import Geometry
from flowlens.geometry.occupancy import Occupancy, overlap
from flowlens.geometry.rules import (
    Instruction,
    RuleProfile,
    RuleSignal,
    SourceAlert,
    decode,
    evaluate,
)
from flowlens.imports.metadata import PreparedImport, hashed
from flowlens.storage.sqlite.database import UnitOfWork


class RuleEvaluation(Scoped):
    as_of_ms: int
    mode: Literal["AS_KNOWN", "DEBRIEF"]
    evaluation_version: int
    last_published_as_of_ms: int | None
    signals: list[RuleSignal]
    source_alerts: list[SourceEvent]
    evidence: list[Evidence]
    rule_version: str
    status: Literal["EVALUATED", "NOT_EVALUABLE"]
    reason: str | None
    indicators: Indicators


class RuleReceipt(Scoped):
    id: UUID
    version: int
    sequence: int
    mode: Literal["AS_KNOWN", "DEBRIEF"]
    as_of_ms: int
    alerts: list[AlertRevision]
    indicators: Indicators


class RulePublished(Scoped):
    evaluation_version: int
    as_of_ms: int
    mode: Literal["AS_KNOWN", "DEBRIEF"]
    alert_revision_ids: list[UUID]
    indicators: Indicators


class Rules:
    def __init__(
        self,
        occupancy: Occupancy,
        evidence: EvidenceRegistry,
        *,
        profile: RuleProfile | None = None,
        context_reader: ContextReader | None = None,
    ) -> None:
        self.occupancy, self.evidence = occupancy, evidence
        self.sources = occupancy.sources
        self.database = self.sources.database
        self.profile = profile or RuleProfile()
        self.context_reader = context_reader
        self.fault: Callable[[str], None] = lambda phase: None

    def _packages(self, ctx: RequestContext) -> list[PreparedImport]:
        with self.database.begin() as uow:
            self.sources.permissions.enforce(uow, ctx)
            rows = list(
                uow.connection.execute(
                    "SELECT source_id,payload FROM platform_source_packages WHERE session_id=?",
                    (str(ctx.session_id),),
                )
            )
            for row in rows:
                self.sources.require_right(
                    uow,
                    ctx,
                    UUID(row["source_id"]),
                    "cloud_context" if "worker" in ctx.capabilities else "reviewer",
                )
            return [PreparedImport.model_validate_json(row["payload"]) for row in rows]

    def evaluate(self, ctx: RequestContext) -> RuleEvaluation:
        packages = self._packages(ctx)
        records = self.sources.read_events(ctx)
        tracks = [r for r in records if isinstance(r, Track)]
        events = [r for r in records if not isinstance(r, Track)]
        prepared = packages[0] if len(packages) == 1 else None
        reason = None
        if prepared is None:
            reason = "SOURCE_RESOURCE_ALIGNMENT_UNKNOWN"
        elif prepared.declaration.source_kind not in ("SYNTHETIC", "ROLEPLAY"):
            reason = "RULE_PROFILE_NOT_APPLICABLE"
        elif prepared.layout is None:
            reason = "LAYOUT_MISSING"
        elif prepared.alignment_status != "KNOWN":
            reason = "CLOCK_UNKNOWN"
        elif not tracks:
            reason = "TRACK_MISSING"
        elif any(track.entity_id is None for track in tracks):
            reason = "IDENTITY_UNKNOWN"
        reports = {
            entity: self.occupancy.report(ctx, entity)
            for entity in sorted({t.entity_id for t in tracks if t.entity_id is not None}, key=str)
        }
        # Canonical source refs are a read cache; publication has a separate atomic boundary.
        # Track refs are already checked by Occupancy; event refs use the same exact record bounds.
        with self.database.begin() as uow:
            self.sources.permissions.enforce(uow, ctx)
            anchors = {r.id: self.evidence.index_source(ctx, r, uow) for r in records}
            uow.commit()
        signals = []
        if prepared is not None and prepared.layout is not None:
            g = Geometry(
                prepared.layout, protection_margin_m=self.profile.occupancy.protection_margin_m
            )
            signals = evaluate(ctx, g, tracks, events, anchors, profile=self.profile)
            changed = []
            for signal in signals:
                causes = [
                    reports[e].result.reason
                    for e in signal.entity_ids
                    if e in reports and reports[e].result.status == "NOT_EVALUABLE"
                ]
                cause = reason or (causes[0] if causes else None)
                if (
                    cause is None
                    and signal.rule_id == "HOLD_SHORT_MOVEMENT"
                    and signal.status == "ACTIVE"
                ):
                    timed_files = {
                        file.id for file in prepared.files if file.role in ("tracks", "events")
                    }
                    bound = max(
                        (
                            file.clock.uncertainty_ms or 0
                            for file in prepared.declaration.files
                            if file.file_id in timed_files
                        ),
                        default=0,
                    )
                    history = [t for t in tracks if t.entity_id in signal.entity_ids]
                    proof_ids = {anchor.segment_id for anchor in signal.evidence}
                    issued = [
                        event
                        for event in events
                        if event.id in proof_ids and isinstance(decode(event), Instruction)
                    ]
                    if (
                        bound
                        and len(history) >= 2
                        and any(
                            event.event_time_ms + bound > history[-2].event_time_ms - bound
                            for event in issued
                        )
                    ):
                        cause = "INSTRUCTION_TIME_UNCERTAIN"
                if (
                    cause is None
                    and signal.rule_id == "RUNWAY_SHARED_RESOURCE"
                    and len(signal.entity_ids) == 2
                ):
                    a, b = [reports[entity] for entity in signal.entity_ids]
                    duration = overlap(a.predicted, b.predicted)
                    occupied = a.result.occupied is True and b.result.occupied is True
                    unknown = (
                        a.prediction_unknown
                        or b.prediction_unknown
                        or a.exit_unknown
                        or b.exit_unknown
                    )
                    state = (
                        "ACTIVE"
                        if occupied or duration and not unknown
                        else "UNKNOWN"
                        if unknown
                        else "INACTIVE"
                    )
                    why = (
                        "OBSERVED_RESOURCE_OVERLAP"
                        if occupied
                        else "PREDICTION_UNKNOWN"
                        if unknown
                        else "PREDICTED_MODEL_OVERLAP"
                        if duration
                        else "NO_MODELED_OVERLAP"
                    )
                    signal = signal.model_copy(
                        update={
                            "status": state,
                            "reason": why,
                            "priority": "ATTENTION"
                            if state == "ACTIVE"
                            else "NOTICE"
                            if state == "UNKNOWN"
                            else "INFO",
                            "overlap_ms": duration,
                            "exit_unknown": unknown,
                        }
                    )
                signal = signal.model_copy(
                    update={
                        "config_hash": hashed(
                            {
                                "rule": signal.config_hash,
                                "source": prepared.declaration_hash,
                                "geometry": [
                                    reports[e].config_hash
                                    for e in signal.entity_ids
                                    if e in reports
                                ],
                            }
                        )
                    }
                )
                if cause:
                    signal = signal.model_copy(
                        update={
                            "status": "UNKNOWN",
                            "reason": cause,
                            "priority": "NOTICE",
                            "overlap_ms": None,
                            "exit_unknown": True,
                        }
                    )
                changed.append(signal)
            signals = changed
        activity = activity_records(ctx, events)
        loops: list[OpenLoop] = []
        loop_status: Literal["UNAVAILABLE", "EVALUATED", "PARTIAL"] = "UNAVAILABLE"
        if self.context_reader is not None:
            try:
                candidates = self.context_reader.lookup(
                    ctx,
                    ToolRequest(
                        name="get_active_rule_context",
                        entity_id=None,
                        evidence_id=None,
                        window=None,
                        limit=100,
                    ),
                )
            except Exception:
                candidates = None
            if isinstance(candidates, list) and all(
                isinstance(c, OpenLoop) for c in candidates[:100]
            ):
                selected = [
                    validate_loop(ctx, c) for c in candidates[:100] if isinstance(c, OpenLoop)
                ]
                unique: dict[UUID, OpenLoop] = {}
                conflicts: set[UUID] = set()
                for loop in selected:
                    if loop.id in unique and loop != unique[loop.id]:
                        conflicts.add(loop.id)
                    unique[loop.id] = loop
                loops = [loop for identifier, loop in unique.items() if identifier not in conflicts]
                loop_status = (
                    "PARTIAL"
                    if len(candidates) >= 100
                    or conflicts
                    or any(c.status == "UNKNOWN" for c in loops)
                    else "EVALUATED"
                )
        with self.database.begin() as uow:
            self.sources.permissions.enforce(uow, ctx)
            for p in packages:
                if p.manifest is None:
                    raise ContractError("NOT_EVALUABLE")
                self.sources.require_right(
                    uow,
                    ctx,
                    p.manifest.id,
                    "cloud_context" if "worker" in ctx.capabilities else "reviewer",
                )
            for anchor in [*anchors.values(), *(e for loop in loops for e in loop.evidence)]:
                self.evidence.resolve_in_uow(ctx, anchor, uow)
            jobs = list(
                uow.connection.execute(
                    "SELECT j.state FROM platform_job_state j "
                    "JOIN platform_run_state r ON r.id=j.run_id "
                    "WHERE j.session_id=? AND r.revision=? AND (? IS NULL OR j.run_id=?)",
                    (
                        str(ctx.session_id),
                        ctx.input_revision,
                        str(ctx.analysis_run_id) if ctx.analysis_run_id else None,
                        str(ctx.analysis_run_id) if ctx.analysis_run_id else None,
                    ),
                )
            )
            head = uow.connection.execute(
                "SELECT version,as_of_ms FROM platform_rule_heads "
                "WHERE session_id=? AND revision=? AND run_scope=? AND mode=?",
                self._scope(ctx),
            ).fetchone()
            indicator = Indicators(
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                as_of_ms=ctx.as_of_ms,
                window_start_ms=max(0, ctx.as_of_ms - 60000),
                reported_active_audio_ms=active_duration(ctx, activity),
                activity_status="SOURCE_REPORTED_NOT_VAD_VERIFIED" if activity else "UNAVAILABLE",
                open_loop_count=sum(c.status in ("OPEN", "PARTIAL") for c in loops)
                if loop_status != "UNAVAILABLE"
                else None,
                open_loop_status=loop_status,
                active_entity_count=sum(r.result.status == "EVALUATED" for r in reports.values()),
                unknown_entity_count=sum(r.result.status != "EVALUATED" for r in reports.values()),
                queued_job_count=sum(row[0] in ("QUEUED", "RETRY_WAIT") for row in jobs),
                running_job_count=sum(row[0] == "RUNNING" for row in jobs),
                evidence=list(
                    {
                        e.id: e
                        for e in [
                            *(anchors[e.id] for e, _ in activity),
                            *(e for loop in loops for e in loop.evidence),
                        ]
                    }.values()
                ),
            )
        return RuleEvaluation(
            session_id=ctx.session_id,
            analysis_run_id=ctx.analysis_run_id,
            revision=ctx.input_revision,
            as_of_ms=ctx.as_of_ms,
            mode=ctx.mode,
            evaluation_version=head[0] if head else 0,
            last_published_as_of_ms=head[1] if head else None,
            signals=signals,
            source_alerts=[e for e in events if isinstance(decode(e), SourceAlert)],
            evidence=list(anchors.values()),
            rule_version=self.profile.version,
            status="NOT_EVALUABLE" if reason else "EVALUATED",
            reason=reason,
            indicators=indicator,
        )

    @staticmethod
    def _scope(ctx: RequestContext) -> tuple[str, int, str, str]:
        return str(ctx.session_id), ctx.input_revision, str(ctx.analysis_run_id or ""), ctx.mode

    def _guard(self, uow: UnitOfWork, ctx: RequestContext, *, write: bool = False) -> None:
        self.sources.permissions.enforce(uow, ctx)
        ctx.require("read", ctx.session_id, ctx.analysis_run_id)
        if write and (
            "worker" in ctx.capabilities
            or not {"analysis", "review"}.intersection(ctx.capabilities)
        ):
            raise ContractError("ACCESS_DENIED")
        for row in uow.connection.execute(
            "SELECT id FROM platform_sources WHERE session_id=? AND revision=?",
            (str(ctx.session_id), ctx.input_revision),
        ):
            self.sources.require_right(
                uow,
                ctx,
                UUID(row[0]),
                "cloud_context" if "worker" in ctx.capabilities else "reviewer",
            )

    @staticmethod
    def _key(key: str, version: int) -> str:
        if (
            type(key) is not str
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key)
            or type(version) is not int
            or not 0 <= version < 2**63 - 1
        ):
            raise ContractError("INVALID_INPUT")
        return hashed(key)

    def _checked(self, uow: UnitOfWork, ctx: RequestContext, alert: AlertRevision) -> AlertRevision:
        if (alert.session_id, alert.analysis_run_id, alert.revision) != (
            ctx.session_id,
            ctx.analysis_run_id,
            ctx.input_revision,
        ) or alert.as_of_ms > ctx.as_of_ms:
            raise ContractError("ACCESS_DENIED")
        for evidence in alert.evidence:
            self.evidence.resolve_in_uow(ctx, evidence, uow)
        return alert

    def _inventory(self, uow: UnitOfWork, ctx: RequestContext) -> list[AlertRevision]:
        rows = uow.connection.execute(
            "SELECT r.payload FROM platform_alert_revisions r WHERE "
            "r.session_id=? AND r.revision=? AND r.run_scope=? AND r.mode=? AND "
            "r.as_of_ms<=? AND r.version=(SELECT MAX(s.version) FROM "
            "platform_alert_revisions s WHERE s.session_id=r.session_id AND "
            "s.revision=r.revision AND s.run_scope=r.run_scope AND s.mode=r.mode "
            "AND s.alert_id=r.alert_id AND s.as_of_ms<=?) ORDER BY r.alert_id",
            (*self._scope(ctx), ctx.as_of_ms, ctx.as_of_ms),
        )
        return [self._checked(uow, ctx, AlertRevision.model_validate_json(row[0])) for row in rows]

    def inventory(self, ctx: RequestContext) -> list[AlertRevision]:
        with self.database.begin() as uow:
            self._guard(uow, ctx)
            return self._inventory(uow, ctx)

    def history(self, ctx: RequestContext, alert_id: UUID) -> list[AlertRevision]:
        if type(alert_id) is not UUID:
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            self._guard(uow, ctx)
            rows = uow.connection.execute(
                "SELECT payload FROM platform_alert_revisions WHERE session_id=? "
                "AND revision=? AND run_scope=? AND mode=? AND alert_id=? AND "
                "as_of_ms<=? ORDER BY version",
                (*self._scope(ctx), str(alert_id), ctx.as_of_ms),
            )
            return [
                self._checked(uow, ctx, AlertRevision.model_validate_json(row[0])) for row in rows
            ]

    def publish(self, ctx: RequestContext, *, key: str, expected_version: int) -> RuleReceipt:
        key_hash = self._key(key, expected_version)
        fingerprint = hashed(
            {
                "scope": self._scope(ctx),
                "input": ctx.input_hash,
                "as_of_ms": ctx.as_of_ms,
                "version": expected_version,
                "profile": self.profile.__dict__ | {"occupancy": self.profile.occupancy.__dict__},
            }
        )
        with self.database.begin() as uow:
            self._guard(uow, ctx, write=True)
            old = uow.connection.execute(
                "SELECT fingerprint,payload FROM platform_rule_receipts WHERE "
                "session_id=? AND actor_id=? AND key_hash=?",
                (str(ctx.session_id), str(ctx.actor_id), key_hash),
            ).fetchone()
            if old:
                if old[0] != fingerprint:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                receipt = RuleReceipt.model_validate_json(old[1])
                for alert in receipt.alerts:
                    self._checked(uow, ctx, alert)
                for anchor in receipt.indicators.evidence:
                    self.evidence.resolve_in_uow(ctx, anchor, uow)
                return receipt
        evaluated = self.evaluate(ctx)
        self.fault("after_evaluate")
        with self.database.begin() as uow:
            self._guard(uow, ctx, write=True)
            # A concurrent duplicate may have committed while calculation ran outside the lock.
            old = uow.connection.execute(
                "SELECT fingerprint,payload FROM platform_rule_receipts WHERE "
                "session_id=? AND actor_id=? AND key_hash=?",
                (str(ctx.session_id), str(ctx.actor_id), key_hash),
            ).fetchone()
            if old:
                if old[0] != fingerprint:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                receipt = RuleReceipt.model_validate_json(old[1])
                for alert in receipt.alerts:
                    self._checked(uow, ctx, alert)
                for anchor in receipt.indicators.evidence:
                    self.evidence.resolve_in_uow(ctx, anchor, uow)
                return receipt
            head = uow.connection.execute(
                "SELECT version,as_of_ms FROM platform_rule_heads WHERE "
                "session_id=? AND revision=? AND run_scope=? AND mode=?",
                self._scope(ctx),
            ).fetchone()
            if (head[0] if head else 0) != expected_version or head and ctx.as_of_ms < head[1]:
                raise ContractError("VERSION_CONFLICT")
            for anchor in [*evaluated.evidence, *evaluated.indicators.evidence]:
                self.evidence.resolve_in_uow(ctx, anchor, uow)
            previous = {a.id: a for a in self._inventory(uow, ctx)}
            if head is None:
                uow.connection.execute(
                    "INSERT INTO platform_rule_heads VALUES (?,?,?,?,?,?,?)",
                    (
                        str(ctx.session_id),
                        ctx.input_revision,
                        str(ctx.analysis_run_id or ""),
                        str(ctx.analysis_run_id) if ctx.analysis_run_id else None,
                        ctx.mode,
                        0,
                        0,
                    ),
                )
            proposed = [reduce_signal(previous.get(s.id), s) for s in evaluated.signals]
            by_segment = {e.segment_id: e for e in evaluated.evidence if e.segment_id is not None}
            # Latest visible event for each source-owned key; never apply a deterministic reducer.
            source_latest: dict[tuple[UUID, str], list[SourceEvent]] = {}
            for event in evaluated.source_alerts:
                source_body = decode(event)
                if not isinstance(source_body, SourceAlert):
                    raise ContractError("INVALID_INPUT")
                group = source_latest.setdefault((event.source_id, source_body.alert_key), [])
                if not group or event.event_time_ms == group[-1].event_time_ms:
                    group.append(event)
                elif event.event_time_ms > group[-1].event_time_ms:
                    group[:] = [event]
            for (source_id, source_key), group in source_latest.items():
                identifier = uuid5(
                    source_id,
                    f"source-alert:{ctx.analysis_run_id}:{ctx.input_revision}:{source_key}",
                )
                proposed.append(
                    reduce_source_group(previous.get(identifier), ctx, group, by_segment)
                )
            for alert in proposed:
                self._checked(uow, ctx, alert)
                if alert.id not in previous or alert.revision_id != previous[alert.id].revision_id:
                    uow.connection.execute(
                        "INSERT INTO platform_alert_revisions VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            *self._scope(ctx),
                            str(alert.id),
                            alert.version,
                            alert.as_of_ms,
                            str(alert.revision_id),
                            alert.model_dump_json(),
                        ),
                    )
            self.fault("after_alerts")
            uow.connection.execute(
                "UPDATE platform_rule_heads SET version=?,as_of_ms=? WHERE "
                "session_id=? AND revision=? AND run_scope=? AND mode=?",
                (expected_version + 1, ctx.as_of_ms, *self._scope(ctx)),
            )
            marker = RulePublished(
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                evaluation_version=expected_version + 1,
                as_of_ms=ctx.as_of_ms,
                mode=ctx.mode,
                alert_revision_ids=[a.revision_id for a in proposed],
                indicators=evaluated.indicators,
            )
            sequence = uow.enqueue_event(ctx, marker)
            uow.audit(ctx, "RULES_PUBLISHED", ctx.session_id)
            self.fault("after_event")
            receipt = RuleReceipt(
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                id=uuid5(ctx.session_id, f"rules:{ctx.actor_id}:{key_hash}"),
                version=expected_version + 1,
                sequence=sequence,
                mode=ctx.mode,
                as_of_ms=ctx.as_of_ms,
                alerts=proposed,
                indicators=evaluated.indicators,
            )
            uow.connection.execute(
                "INSERT INTO platform_rule_receipts VALUES (?,?,?,?,?)",
                (
                    str(ctx.session_id),
                    str(ctx.actor_id),
                    key_hash,
                    fingerprint,
                    receipt.model_dump_json(),
                ),
            )
            self.fault("before_commit")
            uow.commit()
            return receipt

    def acknowledge(
        self, ctx: RequestContext, alert_id: UUID, *, key: str, expected_version: int
    ) -> Acknowledgement:
        key_hash = self._key(key, expected_version)
        if type(alert_id) is not UUID:
            raise ContractError("INVALID_INPUT")
        fingerprint = hashed(
            {
                "scope": self._scope(ctx),
                "input": ctx.input_hash,
                "alert": str(alert_id),
                "version": expected_version,
            }
        )
        with self.database.begin() as uow:
            self._guard(uow, ctx, write=True)
            old = uow.connection.execute(
                "SELECT fingerprint,payload FROM platform_alert_seen WHERE "
                "session_id=? AND actor_id=? AND key_hash=?",
                (str(ctx.session_id), str(ctx.actor_id), key_hash),
            ).fetchone()
            if old:
                if old[0] != fingerprint:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                ack = Acknowledgement.model_validate_json(old[1])
                row = uow.connection.execute(
                    "SELECT payload FROM platform_alert_revisions WHERE "
                    "session_id=? AND revision=? AND run_scope=? AND mode=? AND "
                    "revision_id=?",
                    (*self._scope(ctx), str(ack.alert_revision_id)),
                ).fetchone()
                if row is None:
                    raise ContractError("EVIDENCE_UNAVAILABLE")
                self._checked(uow, ctx, AlertRevision.model_validate_json(row[0]))
                return ack
            row = uow.connection.execute(
                "SELECT payload FROM platform_alert_revisions WHERE session_id=? "
                "AND revision=? AND run_scope=? AND mode=? AND alert_id=? AND "
                "as_of_ms<=? ORDER BY version DESC LIMIT 1",
                (*self._scope(ctx), str(alert_id), ctx.as_of_ms),
            ).fetchone()
            if row is None:
                raise ContractError("EVIDENCE_UNAVAILABLE")
            alert = self._checked(uow, ctx, AlertRevision.model_validate_json(row[0]))
            if alert.version != expected_version:
                raise ContractError("VERSION_CONFLICT")
            ack = seen(ctx, alert)
            uow.connection.execute(
                "INSERT INTO platform_alert_seen VALUES (?,?,?,?,?)",
                (
                    str(ctx.session_id),
                    str(ctx.actor_id),
                    key_hash,
                    fingerprint,
                    ack.model_dump_json(),
                ),
            )
            uow.audit(ctx, "ALERT_SEEN", alert_id)
            uow.enqueue_event(ctx, ack)
            self.fault("before_seen_commit")
            uow.commit()
            return ack
