"""B05 lifecycle. Trusted source/authority, transactions and publication stay injected."""

from collections.abc import Callable
from datetime import datetime
from typing import Literal, Protocol, cast
from uuid import UUID, uuid5

from flowlens.advisory.findings import assemble, catalog, digest, validate_inputs
from flowlens.advisory.models import (
    NAMESPACE,
    Document,
    Entry,
    Inputs,
    Invalidate,
    Option,
    Proposal,
    QueryResult,
    Review,
    Selection,
)
from flowlens.advisory.provider import AdvisoryExecutor
from flowlens.advisory.store import MIGRATIONS, AdvisoryRepository, SQLiteAdvisoryRepository
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import EvidenceService, TransactionFactory, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistration
from flowlens.intent.models import Provenance
from flowlens.intent.validation import visible
from flowlens.memory.reducer import reconstruct


class AcceptanceAccess(Protocol):
    def authoritative(
        self, context: RequestContext, operation: str, candidate: Contract | None, uow: UnitOfWork
    ) -> Inputs:
        """Attest scoped source facts/comparisons/coverage and current accepted memory.

        Check rights, authoritative scope/revision/hash, active attempt/lease/deadline,
        cancellation, bound config/provenance and authenticated proposal, including
        duplicates. Review identity must be server-authenticated. Read operations
        check current source rights too. No permissive implementation is provided.
        """
        ...


def repo(uow: UnitOfWork) -> AdvisoryRepository:
    return cast(AdvisoryRepository, uow.repository(NAMESPACE))


def render_document(
    ctx: RequestContext,
    kind: Literal["FINDINGS", "BRIEF", "OPTIONS"],
    inputs: Inputs,
    selection: Selection,
    provenance: Provenance,
) -> Document:
    facts = {f.id: f for f in catalog(ctx, inputs)}
    if not set(selection.fact_ids) <= facts.keys() or len(set(selection.fact_ids)) != len(
        selection.fact_ids
    ):
        raise ContractError("INVALID_AI_OUTPUT")
    if len(set(selection.option_kinds)) != len(selection.option_kinds):
        raise ContractError("INVALID_AI_OUTPUT")
    if kind != "OPTIONS" and selection.option_kinds:
        raise ContractError("INVALID_AI_OUTPUT")
    if selection.status == "INSUFFICIENT_CONTEXT" and (
        selection.fact_ids or selection.option_kinds
    ):
        raise ContractError("INVALID_AI_OUTPUT")
    # Source alerts and unresolved context cannot be dropped to make a brief look clean.
    projection = reconstruct(ctx, inputs.events)
    mandatory = {f.id for f in facts.values() if f.label == "SOURCE_ALERT"}
    mandatory.update(p.originating_id for p in projection if not p.stale)
    selected_ids = tuple(dict.fromkeys((*selection.fact_ids, *sorted(mandatory, key=str))))
    selected = tuple(facts[i] for i in selected_ids if i in facts)
    options = []
    for option in selection.option_kinds:
        if not selected:
            raise ContractError("INVALID_AI_OUTPUT")
        options.append(
            Option(
                statement=(
                    "Hypothetically review the referenced evidence before assessing alternatives."
                    if option == "REVIEW_EVIDENCE"
                    else "Hypothetically compare alternatives in a separate "
                    "evaluator-controlled offline study."
                ),
                rationale_evidence=tuple(e.id for f in selected for e in f.evidence),
                preconditions=(
                    "Human evaluator review",
                    "Evidence and rule applicability verified",
                ),
                unknowns=(
                    "Operational suitability unvalidated",
                    "Missing context may change assessment",
                ),
                consequences=("Tradeoffs require explicit assumptions and independent evaluation",),
            )
        )
    return Document(
        kind=kind,
        as_of_ms=ctx.as_of_ms,
        mode=ctx.mode,
        input_digest=digest(inputs),
        findings=assemble(ctx, inputs),
        facts=selected,
        options=tuple(options),
        status=selection.status,
        provenance=provenance,
        active_instruction_ids=tuple(
            p.originating_id for p in projection if p.instruction == "ACTIVE" and not p.stale
        ),
        open_loop_ids=tuple(
            p.originating_id for p in projection if p.loop in ("OPEN", "UNKNOWN") and not p.stale
        ),
        unknowns=tuple(sorted({u for f in assemble(ctx, inputs) for u in f.unknowns})),
    )


def journal(ctx: RequestContext, entries: tuple[Entry, ...]) -> tuple[Entry, ...]:
    """Append-only recorded changes, deterministic and permission/as-of scoped."""
    ctx.require("read", ctx.session_id, ctx.analysis_run_id)
    result = []
    for e in entries:
        if e.input_hash != ctx.input_hash:
            raise ContractError("SOURCE_REVISION_CHANGED")
        try:
            visible(ctx, e)
        except ContractError:
            if (e.session_id, e.analysis_run_id, e.revision) != (
                ctx.session_id,
                ctx.analysis_run_id,
                ctx.input_revision,
            ):
                raise
            continue
        result.append(e)
    return tuple(sorted(result, key=lambda e: (e.event_time_ms, e.version, str(e.id))))


def stale_ids(entries: tuple[Entry, ...]) -> set[UUID]:
    return {i for e in entries if isinstance(e.body, Invalidate) for i in e.body.document_ids}


class AdvisoryService:
    def __init__(self, access: AcceptanceAccess, evidence: EvidenceService) -> None:
        self.access, self.evidence = access, evidence

    def inputs(self, ctx: RequestContext, uow: UnitOfWork) -> Inputs:
        inputs = self.access.authoritative(ctx, "READ", None, uow)
        validate_inputs(ctx, inputs, self.evidence)
        return inputs

    async def propose(
        self,
        ctx: RequestContext,
        kind: Literal["FINDINGS", "BRIEF", "OPTIONS"],
        inputs: Inputs,
        executor: AdvisoryExecutor,
        *,
        checkpoint: Callable[[], None],
        reserve: Callable[[int], None],
        local_provenance: Provenance | None = None,
    ) -> Proposal:
        validate_inputs(ctx, inputs, self.evidence)
        if kind == "FINDINGS":
            if local_provenance is None:
                raise ContractError("INVALID_INPUT")
            selection = Selection(
                status="COMPLETE",
                fact_ids=tuple(f.id for f in catalog(ctx, inputs)),
                option_kinds=(),
            )
            provenance = local_provenance
        else:
            selection, provenance = await executor.select(
                ctx, catalog(ctx, inputs), kind, checkpoint=checkpoint, reserve=reserve
            )
        checkpoint()
        return Proposal(
            document=render_document(ctx, kind, inputs, selection, provenance), selection=selection
        )

    def _append(self, ctx: RequestContext, entry: Entry, uow: UnitOfWork) -> UUID:
        visible(ctx, entry)
        try:
            old = repo(uow).get(ctx, entry.id)
        except ContractError as exc:
            if exc.code != "EVIDENCE_UNAVAILABLE":
                raise
        else:
            if (old.stream_id, old.version, old.body, old.input_hash) != (
                entry.stream_id,
                entry.version,
                entry.body,
                entry.input_hash,
            ):
                raise ContractError("IDEMPOTENCY_CONFLICT")
            return old.id
        repo(uow).append(ctx, entry)
        uow.audit(ctx, "ADVISORY_" + entry.body.kind, entry.id)
        # Safe internal metadata notice: private report/review contents are not a public event.
        uow.enqueue_event(
            ctx,
            Notice(
                id=entry.id,
                kind=entry.body.kind,
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
            ),
        )
        return entry.id

    def accept(
        self,
        ctx: RequestContext,
        proposal: Proposal,
        *,
        identifier: UUID,
        stream_id: UUID,
        expected_version: int,
        recorded_at: datetime,
        event_time_ms: int,
        available_time_ms: int | None,
        uow: UnitOfWork,
    ) -> UUID:
        ctx.require("analysis", ctx.session_id, ctx.analysis_run_id)
        proposal = Proposal.model_validate_json(proposal.model_dump_json())
        current = self.access.authoritative(ctx, "ACCEPT", proposal, uow)
        validate_inputs(ctx, current, self.evidence)
        doc = proposal.document
        if (
            doc.provenance.input_hash != ctx.input_hash
            or doc.as_of_ms != ctx.as_of_ms
            or doc.mode != ctx.mode
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        expected = render_document(ctx, doc.kind, current, proposal.selection, doc.provenance)
        if expected != doc:
            raise ContractError("SOURCE_REVISION_CHANGED")
        entry = Entry(
            id=identifier,
            session_id=ctx.session_id,
            analysis_run_id=ctx.analysis_run_id,
            revision=ctx.input_revision,
            input_hash=ctx.input_hash,
            stream_id=stream_id,
            version=expected_version + 1,
            body=doc,
            event_time_ms=event_time_ms,
            available_time_ms=available_time_ms,
            recorded_at=recorded_at,
        )
        # These are references to already resolvable accepted/source evidence.
        # Re-registering it would duplicate platform-owned registry rows.
        return self._append(ctx, entry, uow)

    def review(
        self,
        ctx: RequestContext,
        entry: Entry,
        uow: UnitOfWork,
    ) -> UUID:
        ctx.require("review", ctx.session_id, ctx.analysis_run_id)
        # Repository writes need analysis permission; a platform grant must explicitly
        # authorize both rather than escalating a caller's capabilities here.
        entry = Entry.model_validate_json(entry.model_dump_json())
        self.access.authoritative(ctx, "REVIEW", entry, uow)
        review = entry.body
        if not isinstance(review, Review) or review.actor_id != ctx.actor_id:
            raise ContractError("ACCESS_DENIED")
        rows = journal(ctx, repo(uow).inventory(ctx))
        target = repo(uow).get(ctx, review.document_id)
        visible(ctx, target)
        if not isinstance(target.body, Document) or target.id in stale_ids(rows):
            raise ContractError("SOURCE_REVISION_CHANGED")
        if target.body.input_digest != digest(self.inputs(ctx, uow)):
            raise ContractError("SOURCE_REVISION_CHANGED")
        subjects = {target.id, *(f.id for f in target.body.findings)}
        if review.subject_id not in subjects:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        if (
            review.decision in ("RELEVANT", "NOT_RELEVANT", "UNSUPPORTED")
            and target.body.kind != "OPTIONS"
        ):
            raise ContractError("INVALID_INPUT")
        if (
            review.subject_id in {f.id for f in target.body.findings}
            and review.decision == "CONFIRMED"
        ):
            finding = next(f for f in target.body.findings if f.id == review.subject_id)
            if finding.status != "SUPPORTED":
                raise ContractError("NOT_EVALUABLE")
        expected_stream = uuid5(target.id, str(review.subject_id))
        if entry.stream_id != expected_stream or entry.version != review.expected_version:
            raise ContractError("VERSION_CONFLICT")
        return self._append(ctx, entry, uow)

    def invalidate(self, ctx: RequestContext, entry: Entry, uow: UnitOfWork) -> UUID:
        ctx.require("review", ctx.session_id, ctx.analysis_run_id)
        entry = Entry.model_validate_json(entry.model_dump_json())
        self.access.authoritative(ctx, "INVALIDATE", entry, uow)
        if not isinstance(entry.body, Invalidate):
            raise ContractError("INVALID_INPUT")
        for identifier in entry.body.document_ids:
            row = repo(uow).get(ctx, identifier)
            visible(ctx, row)
            if not isinstance(row.body, Document):
                raise ContractError("INVALID_INPUT")
        return self._append(ctx, entry, uow)

    def reanalyze(
        self,
        ctx: RequestContext,
        previous_id: UUID,
        proposal: Proposal,
        *,
        identifier: UUID,
        invalidation_id: UUID,
        recorded_at: datetime,
        event_time_ms: int,
        available_time_ms: int | None,
        uow: UnitOfWork,
    ) -> UUID:
        old = repo(uow).get(ctx, previous_id)
        visible(ctx, old)
        if not isinstance(old.body, Document) or old.body.kind != proposal.document.kind:
            raise ContractError("INVALID_INPUT")
        self.invalidate(
            ctx,
            Entry(
                id=invalidation_id,
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                input_hash=ctx.input_hash,
                stream_id=invalidation_id,
                version=1,
                body=Invalidate(document_ids=(old.id,), reason="REANALYSIS"),
                recorded_at=recorded_at,
                event_time_ms=event_time_ms,
                available_time_ms=available_time_ms,
            ),
            uow,
        )
        return self.accept(
            ctx,
            proposal,
            identifier=identifier,
            stream_id=old.stream_id,
            expected_version=old.version,
            recorded_at=recorded_at,
            event_time_ms=event_time_ms,
            available_time_ms=available_time_ms,
            uow=uow,
        )

    async def query(
        self,
        ctx: RequestContext,
        question: str,
        inputs: Inputs,
        executor: AdvisoryExecutor,
        *,
        checkpoint: Callable[[], None],
        reserve: Callable[[int], None],
    ) -> QueryResult:
        validate_inputs(ctx, inputs, self.evidence)
        facts = catalog(ctx, inputs)
        try:
            selection, provenance = await executor.select(
                ctx, facts, "QUERY", question=question, checkpoint=checkpoint, reserve=reserve
            )
        except Exception as exc:
            from flowlens.providers.gemini.models import GeminiFailure

            if not isinstance(exc, GeminiFailure) or exc.code not in (
                "UNAVAILABLE",
                "TIMEOUT",
                "REFUSED",
            ):
                raise
            return QueryResult(
                status="UNAVAILABLE",
                items=(),
                context_start_ms=None,
                context_end_ms=ctx.as_of_ms,
                mode=ctx.mode,
                provenance=None,
            )
        selected = tuple(
            f for identifier in selection.fact_ids for f in facts if f.id == identifier
        )
        checkpoint()
        validate_inputs(ctx, inputs, self.evidence)
        return QueryResult(
            status=selection.status,
            items=selected,
            context_start_ms=min((f.event_time_ms for f in facts), default=None),
            context_end_ms=ctx.as_of_ms,
            mode=ctx.mode,
            provenance=provenance,
        )

    def purge(self, ctx: RequestContext, uow: UnitOfWork) -> None:
        ctx.require("admin", ctx.session_id, ctx.analysis_run_id)
        self.access.authoritative(ctx, "PURGE", None, uow)
        repo(uow).purge(ctx)
        uow.audit(ctx, "ADVISORY_PURGED", ctx.session_id)


class Notice(Contract):
    id: UUID
    kind: str
    session_id: UUID
    analysis_run_id: UUID | None
    revision: int


def register_advisory(
    transactions: TransactionFactory,
    access: AcceptanceAccess,
    evidence: EvidenceService,
) -> ModuleRegistration:
    service = AdvisoryService(access, evidence)

    def inventory(ctx: RequestContext) -> tuple[Entry, ...]:
        with transactions.begin() as uow:
            service.inputs(ctx, uow)
            return repo(uow).inventory(ctx)

    return ModuleRegistration(
        name="advisory",
        mock=getattr(transactions, "profile", None) == "MOCK",
        services={
            "advisory": service,
            "advisory_inventory": inventory,
            "advisory_journal": journal,
        },
        repositories={NAMESPACE: SQLiteAdvisoryRepository},
        migrations=MIGRATIONS,
        purge_handler=service.purge,
        inventory_namespaces=(NAMESPACE,),
        readiness=lambda: False,
    )
