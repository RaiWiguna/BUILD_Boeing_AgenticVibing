"""Composition-owned domain adapter; actual B reducers behind actual A authority."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid5

from fastapi import FastAPI
from pydantic import Field

from flowlens.advisory.findings import assemble
from flowlens.advisory.models import Document, Inputs
from flowlens.analysis.repository import scope
from flowlens.contracts.models import (
    Brief,
    CommitReceipt,
    Contract,
    CriticalSlot,
    Evidence,
    Finding,
    Intent,
    JobLease,
    JobResult,
    MemoryEvent,
    RequestContext,
    Snapshot,
    Timed,
    TranscriptSegment,
)
from flowlens.contracts.ports import EvidenceService
from flowlens.contracts.ports import UnitOfWork as TransactionPort
from flowlens.core.errors import ContractError
from flowlens.integration.catalog import PUBLIC
from flowlens.intent.models import Candidate, Provenance, QuoteSlot
from flowlens.intent.validation import validate, visible
from flowlens.jobs.coordinator import Jobs, RunConfig, Stage, StagePolicy, digest
from flowlens.memory.models import AcceptedEvent, Invalidation
from flowlens.memory.reducer import reconstruct
from flowlens.memory.service import AcceptedInputs, MemoryService, repo
from flowlens.storage.sqlite.database import Database, ScopedInventory, UnitOfWork

CONFIG = RunConfig(
    model_version="MOCK",
    api_version="integration-1",
    sdk_version="locked",
    prompt_version="intent-1",
    reducer_version="memory-1",
    rule_version="findings-1",
)


class IntentSubmission(Contract):
    """Private HTTP payload, versioned separately from frozen JobResult DTOs."""

    codec: str = Field(default="intent-submission-1", pattern=r"^intent-submission-1$")
    result: JobResult
    candidates: tuple[Candidate, ...] = Field(min_length=1, max_length=64)
    provenance: Provenance


def intent_projection(
    ctx: RequestContext, candidate: Candidate, segment: TranscriptSegment
) -> Intent:
    def slot(value: QuoteSlot) -> CriticalSlot:
        return CriticalSlot.model_validate(value.model_dump(mode="json"))

    return Intent(
        id=candidate.id,
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=ctx.input_revision,
        event_time_ms=segment.event_time_ms,
        available_time_ms=segment.available_time_ms,
        recorded_at=segment.recorded_at,
        segment_ids=[candidate.segment_id],
        speech_act=candidate.speech_act,
        role_candidate=candidate.role,
        entity_candidates=list(candidate.entity_candidates),
        actions=list(candidate.actions),
        callsign=slot(candidate.callsign),
        runway=slot(candidate.runway),
        condition=candidate.condition.value,
        negation=None
        if candidate.negation.value is None
        else True
        if candidate.negation.value.casefold() in ("not", "no", "negative")
        else None,
        quality="AMBIGUOUS" if candidate.unknowns or candidate.role == "UNKNOWN" else "SUPPORTED",
        alternatives=[],
        unknowns=list(candidate.unknowns),
        evidence=list(candidate.evidence),
    )


class TransactionalEvidence:
    def __init__(self, registry: object, uow: UnitOfWork) -> None:
        from flowlens.evidence.registry import EvidenceRegistry

        self.registry = cast(EvidenceRegistry, registry)
        self.uow = uow

    def resolve(self, context: RequestContext, evidence: Evidence) -> Evidence:
        return self.registry.resolve_in_uow(context, evidence, self.uow)

    def register(self, context: RequestContext, evidence: Evidence, uow: TransactionPort) -> UUID:
        if uow is not self.uow:
            raise ContractError("ACCESS_DENIED")
        return self.registry.register(context, evidence, uow)


class Engine:
    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.memory = MemoryService(self, self)

    @property
    def database(self) -> Database:
        return cast(Database, self.app.state.transactions)

    @property
    def jobs(self) -> Jobs:
        return cast(Jobs, self.app.state.jobs)

    def status(self) -> dict[str, object]:
        return {
            "composition": "A_B_LOCAL",
            "profile": "MOCK" if self.app.state.settings.profile == "test" else "PROVIDERS_PENDING",
            "analysis_execution": "MOCK_TEST_ONLY"
            if self.app.state.settings.profile == "test"
            else "PROVIDER_CONFIGURATION_REQUIRED",
            "providers": {"GOOGLE_STT": "NOT_CONFIGURED", "GEMINI": "NOT_CONFIGURED"},
            "provider_verified": False,
            "G_BE": "not_started",
            "domain": "NOT_DOMAIN_VALIDATED",
        }

    def policies(self) -> tuple[StagePolicy, ...]:
        from flowlens.integration.audio import AUDIO_CONFIG

        audio = StagePolicy(
            stage="AUDIO",
            version="integration-audio-1",
            rights=("local",),
            outputs={},
            handler=self.accept,
            ready=lambda: True,
            reservation=0,
            config=AUDIO_CONFIG,
            execution_mode="DEBRIEF",
        )
        return (
            audio,
            *tuple(
                StagePolicy(
                    stage=cast(Stage, stage),
                    execution_mode="DEBRIEF",
                    version="integration-1",
                    rights=("cloud_audio",) if stage == "STT" else ("cloud_context",),
                    outputs={name: PUBLIC for name in names},
                    handler=self.accept,
                    ready=lambda: self.app.state.settings.profile == "test",
                    reservation=1000,
                    config=CONFIG,
                    lease_ms=30000,
                )
                for stage, names in (
                    ("STT", ("TranscriptSegment",)),
                    ("INTENT", ("Intent",)),
                    ("FINDINGS", ("Finding",)),
                    ("BRIEF", ("Brief",)),
                )
            ),
        )

    def records(self, ctx: RequestContext, uow: TransactionPort) -> tuple[Contract, ...]:
        result = []
        for record in cast(ScopedInventory, uow.repository(PUBLIC)).inventory(ctx):
            try:
                visible(ctx, cast(Timed, record))
            except ContractError:
                continue
            for ref in getattr(record, "evidence", ()):
                if isinstance(record, TranscriptSegment) and ref.kind == "AUDIO":
                    self.app.state.evidence._audio(
                        ctx, ref, cast(UnitOfWork, uow), require_access=False
                    )
                else:
                    TransactionalEvidence(self.app.state.evidence, cast(UnitOfWork, uow)).resolve(
                        ctx, ref
                    )
            result.append(record)
        return tuple(result)

    def resolve(self, context: RequestContext, evidence: Evidence) -> Evidence:
        return cast(EvidenceService, self.app.state.evidence).resolve(context, evidence)

    def register(self, context: RequestContext, evidence: Evidence, uow: TransactionPort) -> UUID:
        return cast(EvidenceService, self.app.state.evidence).register(context, evidence, uow)

    def authoritative(
        self,
        context: RequestContext,
        candidate: Candidate,
        config_hash: str,
        uow: TransactionPort,
        *,
        provenance: Provenance,
    ) -> AcceptedInputs:
        actual = cast(UnitOfWork, uow)
        actual.authorize(context)
        self.jobs.guard(actual, context)
        if (
            "worker" not in context.capabilities
            or self.app.state.settings.profile != "test"
            or provenance.profile != "MOCK"
        ):
            raise ContractError("ACCESS_DENIED")
        row = actual.connection.execute(
            "SELECT payload FROM analysis_intent_submissions WHERE session_id=? AND run_id=? "
            "AND revision=? "
            "AND result_hash=?",
            (*scope(context), digest({"config": config_hash, "candidate": str(candidate.id)})),
        ).fetchone()
        if row is None:
            raise ContractError("ACCESS_DENIED")
        submission = IntentSubmission.model_validate_json(row[0])
        if (
            submission.provenance != provenance
            or candidate not in submission.candidates
            or submission.result.config_hash != config_hash
        ):
            raise ContractError("INVALID_AI_OUTPUT")
        segments = {r.id: r for r in self.records(context, uow) if isinstance(r, TranscriptSegment)}
        # Neither diarization nor model role establishes controller/pilot authority.
        # Imported speaker mapping is not yet representable; keep role UNKNOWN.
        return AcceptedInputs(segments, self.identities(context, actual), {}, False)

    def identities(self, ctx: RequestContext, uow: UnitOfWork) -> dict[UUID, tuple[str, ...]]:
        from flowlens.imports.metadata import PreparedImport

        identities: dict[UUID, tuple[str, ...]] = {}
        for row in uow.connection.execute(
            "SELECT payload FROM platform_source_packages WHERE session_id=? AND revision=?",
            (str(ctx.session_id), ctx.input_revision),
        ):
            p = PreparedImport.model_validate_json(row[0])
            if p.manifest is None:
                raise ContractError("NOT_EVALUABLE")
            self.app.state.permissions.require_source_rights(uow, ctx, p.manifest.id)
            for entity in p.identities:
                identities[entity.entity_id] = (entity.callsign,)
        return identities

    def submit(self, token: str, submission: IntentSubmission) -> CommitReceipt:
        """Seal private candidate/provenance before coordinator result transaction.

        Candidate bytes are immutable per attempt. They never grant lease authority;
        the normal coordinator rechecks cancellation/rights/revision before accept.
        """
        result = submission.result
        with self.database.begin() as uow:
            attempt, _, _, policy = self.jobs._attempt(uow, token, result, active=False)
            if policy.stage != "INTENT" or len(submission.candidates) != 1:
                raise ContractError("INVALID_INPUT")
            scope_id = UUID(attempt["scope_id"])
            completed = bool(
                uow.connection.execute(
                    "SELECT 1 FROM platform_receipts WHERE attempt_id=?", (str(result.attempt_id),)
                ).fetchone()
            )
        if completed:
            with self.database.begin() as uow:
                old = uow.connection.execute(
                    "SELECT payload FROM analysis_intent_submissions WHERE attempt_id=?",
                    (str(result.attempt_id),),
                ).fetchone()
                if old is None or old[0] != submission.model_dump_json():
                    raise ContractError("IDEMPOTENCY_CONFLICT")
            return self.jobs.result(token, result)
        ctx = self.app.state.permissions.worker_context(token, scope_id)
        with self.database.begin() as uow:
            self.jobs._attempt(uow, token, result)
            uow.authorize(ctx)
            candidate = submission.candidates[0]
            key = digest({"config": result.config_hash, "candidate": str(candidate.id)})
            old = uow.connection.execute(
                "SELECT payload FROM analysis_intent_submissions WHERE attempt_id=?",
                (str(result.attempt_id),),
            ).fetchone()
            if old and old[0] != submission.model_dump_json():
                raise ContractError("IDEMPOTENCY_CONFLICT")
            if not old:
                uow.connection.execute(
                    "INSERT INTO analysis_intent_submissions VALUES (?,?,?,?,?,?)",
                    (str(result.attempt_id), *scope(ctx), key, submission.model_dump_json()),
                )
            uow.commit()
        return self.jobs.result(token, result)

    def validate(
        self, context: RequestContext, candidate: JobResult, evidence: EvidenceService
    ) -> JobResult:
        with self.database.begin() as uow:
            uow.authorize(context)
            job = uow.connection.execute(
                "SELECT stage FROM platform_job_state WHERE id=?", (str(candidate.job_id),)
            ).fetchone()
            if (
                candidate.status != "FAILED"
                and job[0] in ("STT", "INTENT")
                and not candidate.outputs
            ):
                raise ContractError("INVALID_AI_OUTPUT")
            for output in candidate.outputs:
                for ref in output.evidence:
                    # AUDIO and transcript quote/scope validation stays A-owned.
                    TransactionalEvidence(evidence, uow).resolve(context, ref)
            if any(isinstance(o, Intent) for o in candidate.outputs):
                rows = uow.connection.execute(
                    "SELECT payload FROM analysis_intent_submissions WHERE attempt_id=?",
                    (str(candidate.attempt_id),),
                ).fetchall()
                if len(rows) != 1:
                    raise ContractError("INVALID_AI_OUTPUT")
                packet = IntentSubmission.model_validate_json(rows[0][0])
                if packet.result != candidate:
                    raise ContractError("INVALID_AI_OUTPUT")
                segments = {
                    r.id: r for r in self.records(context, uow) if isinstance(r, TranscriptSegment)
                }
                expected = []
                for c in packet.candidates:
                    checked = validate(
                        context,
                        c,
                        segments,
                        self.identities(context, uow),
                        TransactionalEvidence(evidence, uow),
                    )
                    expected.append(
                        intent_projection(context, checked, segments[checked.segment_id])
                    )
                if expected != candidate.outputs:
                    raise ContractError("INVALID_AI_OUTPUT")
        return candidate

    def accept(self, context: RequestContext, result: JobResult, uow: TransactionPort) -> None:
        actual = cast(UnitOfWork, uow)
        job = actual.connection.execute(
            "SELECT stage FROM platform_job_state WHERE id=?", (str(result.job_id),)
        ).fetchone()
        if job[0] == "AUDIO":
            from flowlens.integration.audio import validate_artifacts

            validate_artifacts(context, result, actual, self.app.state.assets)
        if any(isinstance(o, Intent) for o in result.outputs):
            row = actual.connection.execute(
                "SELECT payload FROM analysis_intent_submissions WHERE attempt_id=?",
                (str(result.attempt_id),),
            ).fetchone()
            if row is None:
                raise ContractError("INVALID_AI_OUTPUT")
            packet = IntentSubmission.model_validate_json(row[0])
            for candidate in packet.candidates:
                MemoryService(self, TransactionalEvidence(self.app.state.evidence, actual)).accept(
                    context,
                    candidate,
                    config_hash=result.config_hash,
                    provenance=packet.provenance,
                    recorded_at=datetime.now(UTC),
                    uow=uow,
                )
        # Only transcript and explicitly projected intent candidates are accepted
        # from workers. Findings/brief are compared to server-derived B output.
        expected = self.findings(context, uow)
        if job[0] == "FINDINGS" and result.outputs != list(expected):
            raise ContractError("INVALID_AI_OUTPUT")
        if job[0] == "BRIEF":
            if result.outputs != [self.brief(context, result.config_hash, uow)]:
                raise ContractError("INVALID_AI_OUTPUT")
            from flowlens.advisory.models import Entry
            from flowlens.advisory.service import repo as advisory_repo

            document = self.document(context, result.config_hash, uow)
            entry = Entry(
                id=uuid5(result.attempt_id, "document"),
                session_id=context.session_id,
                analysis_run_id=context.analysis_run_id,
                revision=context.input_revision,
                input_hash=context.input_hash,
                stream_id=uuid5(result.attempt_id, "brief-stream"),
                version=1,
                body=document,
                event_time_ms=context.as_of_ms,
                available_time_ms=None,
                recorded_at=result.outputs[0].recorded_at,
            )
            advisory_repo(uow).append(context, entry)
            uow.audit(context, "ADVISORY_ACCEPTED", entry.id)
        for record in result.outputs:
            uow.repository(PUBLIC).append(context, record)

    def memory_rows(
        self, ctx: RequestContext, uow: TransactionPort
    ) -> tuple[AcceptedEvent | Invalidation, ...]:
        return repo(uow).inventory(ctx)

    def findings(self, ctx: RequestContext, uow: TransactionPort) -> tuple[Finding, ...]:
        rows = self.memory_rows(ctx, uow)
        events = {e.id: e for e in rows if isinstance(e, AcceptedEvent)}
        result = []
        for f in assemble(ctx, Inputs(events=rows, facts=(), signals=())):
            anchors = [
                e
                for e in events.values()
                if any(r.id in {ref.id for ref in f.evidence} for r in e.candidate.evidence)
            ]
            if not anchors:
                continue
            anchor = max(anchors, key=lambda e: e.event_time_ms)
            result.append(
                Finding(
                    id=f.id,
                    session_id=ctx.session_id,
                    analysis_run_id=ctx.analysis_run_id,
                    revision=ctx.input_revision,
                    event_time_ms=anchor.event_time_ms,
                    available_time_ms=anchor.available_time_ms,
                    recorded_at=anchor.recorded_at,
                    evidence=list(f.evidence),
                    category=f.category,
                    statement=f.statement,
                    priority=f.priority,
                    status="OPEN" if f.status == "SUPPORTED" else "UNRESOLVED",
                    entity_ids=list(f.entity_ids),
                    rule_version=f.rule_version,
                    model_version=None,
                    quality=f.quality,
                    applicability=f.applicability,
                    unknowns=list(f.unknowns),
                    stale=False,
                )
            )
        return tuple(result)

    def snapshot(self, context: RequestContext) -> Snapshot:
        with self.database.begin() as uow:
            uow.authorize(context)
            if context.analysis_run_id is None:
                return Snapshot(
                    session_id=context.session_id,
                    analysis_run_id=None,
                    revision=context.input_revision,
                    as_of_ms=context.as_of_ms,
                    mode=context.mode,
                    sequence=0,
                    events=[],
                    memory=[],
                    findings=[],
                    quality="MISSING",
                )
            rows = self.memory_rows(context, uow)
            accepted = {e.id: e for e in rows if isinstance(e, AcceptedEvent)}
            memory = []
            for p in reconstruct(context, rows):
                anchor = accepted[p.originating_id]
                try:
                    visible(context, anchor)
                except ContractError:
                    continue
                memory.append(
                    MemoryEvent(
                        id=uuid5(p.originating_id, "public-memory"),
                        session_id=context.session_id,
                        analysis_run_id=context.analysis_run_id,
                        revision=context.input_revision,
                        event_time_ms=anchor.event_time_ms,
                        available_time_ms=anchor.available_time_ms,
                        recorded_at=anchor.recorded_at,
                        evidence=list(anchor.candidate.evidence),
                        entity_id=p.entity_id,
                        intent_id=p.originating_id,
                        interpretation=p.interpretation,
                        instruction=p.instruction,
                        readback=p.readback,
                        movement=p.movement,
                        reviewer=p.reviewer,
                        dependency_hashes=list(anchor.dependency_hashes),
                        reducer_version="memory-1",
                    )
                )
            return Snapshot(
                session_id=context.session_id,
                analysis_run_id=context.analysis_run_id,
                revision=context.input_revision,
                as_of_ms=context.as_of_ms,
                mode=context.mode,
                sequence=0,
                events=[],
                memory=memory,
                findings=list(self.findings(context, uow)),
                quality="AMBIGUOUS" if rows else "MISSING",
            )

    def purge(self, context: RequestContext, uow: TransactionPort) -> None:
        # The retention coordinator performs session-wide SQL erasure using the
        # exact catalog after callback isolation checks; private B APIs are run-scoped.
        context.require("admin", context.session_id)
        uow.audit(context, "ANALYSIS_PURGE_REGISTERED", context.session_id)

    def inputs(self, context: RequestContext, uow: TransactionPort) -> Inputs:
        actual = cast(UnitOfWork, uow)
        actual.authorize(context)
        events = self.memory_rows(context, uow)
        included = []
        for event in events:
            try:
                visible(context, event)
            except ContractError:
                continue
            if isinstance(event, AcceptedEvent):
                for ref in event.candidate.evidence:
                    TransactionalEvidence(self.app.state.evidence, actual).resolve(context, ref)
            included.append(event)
        return Inputs(events=tuple(included), facts=(), signals=())

    def provenance(self, ctx: RequestContext, config_hash: str) -> Provenance:
        return Provenance(
            profile="MOCK",
            model="MOCK",
            api_version=CONFIG.api_version,
            sdk_version=CONFIG.sdk_version,
            prompt_version=CONFIG.prompt_version,
            schema_hash=digest(Candidate.model_json_schema()),
            config_hash=config_hash,
            input_hash=ctx.input_hash,
            request_hashes=(),
            response_hashes=(),
            calls=0,
            total_tokens=0,
        )

    def document(self, context: RequestContext, config_hash: str, uow: TransactionPort) -> Document:
        from flowlens.advisory.findings import catalog
        from flowlens.advisory.models import Selection
        from flowlens.advisory.service import render_document

        inputs = self.inputs(context, uow)
        facts = catalog(context, inputs)
        selection = Selection(
            status="COMPLETE" if facts else "INSUFFICIENT_CONTEXT",
            fact_ids=tuple(f.id for f in facts),
            option_kinds=(),
        )
        return render_document(
            context, "BRIEF", inputs, selection, self.provenance(context, config_hash)
        )

    def brief(self, context: RequestContext, config_hash: str, uow: TransactionPort) -> Brief:
        from flowlens.contracts.models import Brief, FactualItem

        document = self.document(context, config_hash, uow)
        rows = [e for e in self.inputs(context, uow).events if isinstance(e, AcceptedEvent)]
        references = {r.id: r for f in document.facts for r in f.evidence}
        return Brief(
            id=uuid5(cast(UUID, context.analysis_run_id), "brief:" + str(context.as_of_ms)),
            session_id=context.session_id,
            analysis_run_id=context.analysis_run_id,
            revision=context.input_revision,
            event_time_ms=context.as_of_ms,
            available_time_ms=None,
            recorded_at=max(
                (e.recorded_at for e in rows), default=datetime(2026, 10, 10, tzinfo=UTC)
            ),
            evidence=list(references.values()),
            as_of_ms=context.as_of_ms,
            items=[
                FactualItem(
                    statement=f.statement, evidence_ids=[r.id for r in f.evidence], unknowns=[]
                )
                for f in document.facts
            ],
            labels=list(document.limitations),
            model_version="MOCK",
            prompt_version="advisory-select-1",
        )

    def prepare(self, token: str, lease: JobLease) -> dict[str, object]:
        context = self.jobs.context(token, lease)
        outputs: tuple[Contract, ...]
        with self.database.begin() as uow:
            _, _, _, policy = self.jobs._attempt(uow, token, lease)
            if policy.stage == "FINDINGS":
                outputs = self.findings(context, uow)
            elif policy.stage == "BRIEF":
                outputs = (self.brief(context, lease.config_hash, uow),)
            else:
                raise ContractError("INVALID_INPUT")
        return {
            "profile": "MOCK",
            "provider_verified": False,
            "outputs": [r.model_dump(mode="json") for r in outputs],
        }
