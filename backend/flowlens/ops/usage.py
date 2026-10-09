"""Scoped attempt totals. Unknown provider usage never becomes zero or actual billing."""

from uuid import UUID

from flowlens.auth.permissions import Permissions
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import RequestContext, Usage
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import UnitOfWork


class UsageSummary(MetadataModel):
    scope: str
    runs: int
    attempts: int
    active_attempts: int
    unreported_attempts: int
    budget_microunits: int
    used_microunits: int
    reserved_microunits: int
    remaining_microunits: int
    reported_usage: Usage
    provider_billing_verified: bool = False
    channel_attribution: str = "NOT_REPORTED_BY_FROZEN_USAGE"
    stages: dict[str, int]
    job_states: dict[str, int]
    maximum_eligible_queue_wait_ms: int | None
    maximum_lease_age_ms: int | None


def invariant(uow: UnitOfWork) -> None:
    mismatch = uow.connection.execute(
        "SELECT 1 FROM platform_run_state r WHERE "
        "r.reserved!=(SELECT COALESCE(SUM(a.reservation),0) FROM platform_attempt_state a "
        "JOIN platform_job_state j ON j.id=a.job_id WHERE j.run_id=r.id AND a.state='ACTIVE') "
        "OR r.used!=(SELECT COALESCE(SUM(a.charged),0) FROM platform_attempt_state a "
        "JOIN platform_job_state j ON j.id=a.job_id WHERE j.run_id=r.id) LIMIT 1"
    ).fetchone()
    if mismatch:
        raise ContractError("NOT_EVALUABLE")


class UsageReader:
    def __init__(self, permissions: Permissions) -> None:
        self.permissions = permissions
        self.database = permissions.database

    def _aggregate(
        self,
        uow: UnitOfWork,
        *,
        session: UUID | None,
        run: UUID | None,
        revision: int | None,
        scope: str,
    ) -> UsageSummary:
        invariant(uow)
        runs = list(
            uow.connection.execute(
                "SELECT * FROM platform_run_state WHERE (? IS NULL OR session_id=?) "
                "AND (? IS NULL OR id=?) AND (? IS NULL OR revision=?)",
                (
                    str(session) if session else None,
                    str(session) if session else None,
                    str(run) if run else None,
                    str(run) if run else None,
                    revision,
                    revision,
                ),
            )
        )
        ids = {r["id"] for r in runs}
        attempts = [
            r
            for r in uow.connection.execute(
                "SELECT a.*,j.run_id,j.stage,t.leased_ms FROM platform_attempt_state a "
                "LEFT JOIN platform_attempt_timing t ON t.attempt_id=a.id AND "
                "t.session_id=a.session_id "
                "JOIN platform_job_state j "
                "ON j.id=a.job_id WHERE (? IS NULL OR a.session_id=?)",
                (str(session) if session else None, str(session) if session else None),
            )
            if r["run_id"] in ids
        ]
        jobs = [
            r
            for r in uow.connection.execute(
                "SELECT run_id,state,ready_ms FROM platform_job_state WHERE (? "
                "IS NULL OR session_id=?)",
                (str(session) if session else None, str(session) if session else None),
            )
            if r["run_id"] in ids
        ]
        values = [Usage.model_validate_json(r["usage"]) if r["usage"] else None for r in attempts]

        def total(field: str) -> int | None:
            numbers = [getattr(v, field) if v is not None else None for v in values]
            return (
                sum(n for n in numbers if n is not None)
                if numbers and all(n is not None for n in numbers)
                else None
            )

        stages: dict[str, int] = {}
        states: dict[str, int] = {}
        for r in attempts:
            stages[r["stage"]] = stages.get(r["stage"], 0) + 1
        for r in jobs:
            states[r["state"]] = states.get(r["state"], 0) + 1
        now = self.permissions.sessions.clock()
        queue = [
            max(0, now - r["ready_ms"])
            for r in jobs
            if r["state"] in ("QUEUED", "RETRY_WAIT") and r["ready_ms"] <= now
        ]
        leases = []
        for r in attempts:
            if r["state"] == "ACTIVE":
                if r["leased_ms"] is not None:
                    leases.append(max(0, now - r["leased_ms"]))
        return UsageSummary(
            scope=scope,
            runs=len(runs),
            attempts=len(attempts),
            active_attempts=sum(r["state"] == "ACTIVE" for r in attempts),
            unreported_attempts=sum(v is None for v in values),
            budget_microunits=sum(r["budget"] for r in runs),
            used_microunits=sum(r["used"] for r in runs),
            reserved_microunits=sum(r["reserved"] for r in runs),
            remaining_microunits=sum(max(0, r["budget"] - r["used"] - r["reserved"]) for r in runs),
            reported_usage=Usage(
                audio_ms=total("audio_ms"),
                input_tokens=total("input_tokens"),
                output_tokens=total("output_tokens"),
                cost_microunits=total("cost_microunits"),
                latency_ms=sum(v.latency_ms for v in values if v),
            ),
            stages=stages,
            job_states=states,
            maximum_eligible_queue_wait_ms=max(queue) if queue else None,
            maximum_lease_age_ms=max(leases)
            if leases
            and all(r["leased_ms"] is not None for r in attempts if r["state"] == "ACTIVE")
            else None,
        )

    def read(self, context: RequestContext) -> UsageSummary:
        with self.database.begin() as uow:
            self.permissions.enforce(uow, context)
            context.require("analysis", context.session_id, context.analysis_run_id)
            return self._aggregate(
                uow,
                session=context.session_id,
                run=context.analysis_run_id,
                revision=context.input_revision,
                scope="AUTHORIZED_REVISION",
            )

    def admin(self, token: str) -> UsageSummary:
        with self.database.begin() as uow:
            self.permissions._admin(uow, token)
            return self._aggregate(
                uow, session=None, run=None, revision=None, scope="RETAINED_LOCAL_RUNS"
            )
