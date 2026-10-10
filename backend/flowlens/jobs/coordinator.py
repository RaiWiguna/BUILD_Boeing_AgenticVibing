"""API-owned scheduler. Workers carry candidates; only registered handlers write domains."""

import hashlib
import json
import re
import secrets
import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID, uuid4

from flowlens.assets.access import Assets
from flowlens.auth.permissions import Permissions, context_digest, worker_hash
from flowlens.contracts.models import (
    AnalysisRun,
    CommitReceipt,
    Contract,
    Evidence,
    JobLease,
    JobProgress,
    JobResult,
    Mode,
    RequestContext,
    TranscriptSegment,
    Usage,
)
from flowlens.contracts.ports import AnalysisModule
from flowlens.contracts.ports import UnitOfWork as TransactionPort
from flowlens.contracts.results import result_hash as result_hash
from flowlens.core.errors import ContractError
from flowlens.imports.metadata import PreparedImport
from flowlens.ops.logs import emit
from flowlens.sources.metadata import Action
from flowlens.sources.policy import policy
from flowlens.storage.sqlite.database import Database, UnitOfWork
from pydantic import Field, ValidationError

Stage = Literal[
    "AUDIO", "STT", "INTENT", "ASSOCIATION", "MEMORY", "FINDINGS", "BRIEF", "QUERY", "EXPORT"
]


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class RunConfig(Contract):
    model_version: str = Field(min_length=1, max_length=128)
    api_version: str = Field(min_length=1, max_length=128)
    sdk_version: str = Field(min_length=1, max_length=128)
    prompt_version: str = Field(min_length=1, max_length=128)
    reducer_version: str = Field(min_length=1, max_length=128)
    rule_version: str = Field(min_length=1, max_length=128)


class StageInput(Contract):
    stage: Stage
    source_ids: list[UUID] = Field(min_length=1, max_length=100)
    asset_ids: list[UUID] = Field(default_factory=list, max_length=100)


@dataclass(frozen=True)
class StagePolicy:
    stage: Stage
    version: str
    rights: tuple[Action, ...]
    outputs: dict[str, str]
    handler: Callable[[RequestContext, JobResult, TransactionPort], None]
    ready: Callable[[], bool]
    reservation: int
    config: RunConfig
    concurrency: int = 1
    lease_ms: int = 30000
    max_attempts: int = 3
    execution_mode: Mode = "AS_KNOWN"

    def __post_init__(self) -> None:
        if (
            not re.fullmatch(r"[a-zA-Z0-9_.-]{1,64}", self.version)
            or not 0 <= self.reservation <= 10**12
            or not 1 <= self.concurrency <= 16
            or not 100 <= self.lease_ms <= 120000
            or not 1 <= self.max_attempts <= 3
            or self.execution_mode not in ("AS_KNOWN", "DEBRIEF")
            or not self.rights
            or any(r not in ("local", "cloud_audio", "cloud_context") for r in self.rights)
            or any(not ns.startswith("analysis.") for ns in self.outputs.values())
        ):
            raise ValueError("Invalid registered job policy")
        if (
            (self.stage == "STT" and "cloud_audio" not in self.rights)
            or (self.stage == "AUDIO" and not {"local", "cloud_audio"}.intersection(self.rights))
            or self.stage not in ("AUDIO", "STT")
            and "cloud_context" not in self.rights
        ):
            raise ValueError("Stage transfer policy is incomplete")

    @property
    def fingerprint(self) -> str:
        return digest(
            {
                "stage": self.stage,
                "config": self.config.model_dump(mode="json"),
                "version": self.version,
                "rights": self.rights,
                "outputs": self.outputs,
                "reservation": self.reservation,
                "concurrency": self.concurrency,
                "lease_ms": self.lease_ms,
                "max_attempts": self.max_attempts,
                **(
                    {"execution_mode": self.execution_mode}
                    if self.execution_mode != "AS_KNOWN"
                    else {}
                ),
            }
        )


class Jobs:
    def __init__(
        self,
        database: Database,
        permissions: Permissions,
        assets: Assets,
        evidence: object,
        module: AnalysisModule,
        policies: Sequence[StagePolicy],
        *,
        allow_mock: bool = False,
    ) -> None:
        from flowlens.evidence.registry import EvidenceRegistry

        if not isinstance(evidence, EvidenceRegistry):
            raise ValueError("A-owned evidence registry required")
        self.allow_mock = allow_mock
        self.database, self.permissions, self.assets = database, permissions, assets
        self.evidence, self.module = evidence, module
        self.policies = {p.stage: p for p in policies}
        if not policies or len(self.policies) != len(policies):
            raise ValueError("Unique registered stage policies required")
        if any(
            namespace not in database.repositories
            for p in policies
            for namespace in p.outputs.values()
        ):
            raise ValueError("Registered output repository factory required")
        self.publish: Callable[[UUID, int], None] | None = None
        self.fault: Callable[[str], None] | None = None
        permissions.worker_guard = self.guard
        permissions.worker_mode = self.worker_mode
        self.recover()

    def now(self) -> int:
        return self.permissions.sessions.clock()

    def client(self, token: str) -> "WorkerJobs":
        self.permissions.authenticate_worker(token)
        return WorkerJobs(self, token)

    def _principal(self, uow: UnitOfWork, token: str) -> sqlite3.Row:
        row = uow.connection.execute(
            "SELECT * FROM platform_workers WHERE token_hash=?", (worker_hash(token),)
        ).fetchone()
        if row is None or row["revoked"] or self.now() >= row["expires_ms"]:
            raise ContractError("AUTH_REQUIRED")
        return cast(sqlite3.Row, row)

    def _creator(self, uow: UnitOfWork, run: sqlite3.Row) -> None:
        account = uow.connection.execute(
            "SELECT * FROM platform_accounts WHERE id=?", (run["creator_id"],)
        ).fetchone()
        if (
            account is None
            or not account["active"]
            or account["must_change_password"]
            or account["credential_version"] != run["credential_version"]
        ):
            raise ContractError("ACCESS_DENIED")
        caps = self.permissions._capabilities(
            uow, UUID(run["creator_id"]), UUID(run["session_id"]), "AS_KNOWN"
        )
        if "analysis" not in caps:
            raise ContractError("ACCESS_DENIED")
        latest = self.permissions._input(uow, UUID(run["session_id"]), UUID(run["id"]))
        if (latest["revision"], latest["input_hash"]) != (run["revision"], run["input_hash"]):
            raise ContractError("SOURCE_REVISION_CHANGED")

    def _eligible(
        self, uow: UnitOfWork, run: sqlite3.Row, job: sqlite3.Row, *, active: bool = True
    ) -> StagePolicy:
        self._creator(uow, run)
        p = self.policies.get(job["stage"])
        if p is None or p.fingerprint != job["policy_hash"]:
            raise ContractError("VERSION_CONFLICT")
        inputs = uow.connection.execute(
            "SELECT stage,policy_hash FROM platform_job_state WHERE run_id=? ORDER BY id",
            (run["id"],),
        ).fetchall()
        confighash = digest(
            {
                "config": json.loads(run["config"]),
                "policies": sorted((r["stage"], r["policy_hash"]) for r in inputs),
            }
        )
        if confighash != run["config_hash"]:
            raise ContractError("VERSION_CONFLICT")
        state = AnalysisRun.model_validate_json(run["payload"]).status
        if active and state in ("CANCELLED", "FAILED", "COMPLETED", "PARTIAL"):
            raise ContractError("JOB_CANCELLED")
        if active and self.now() >= run["deadline_ms"]:
            raise ContractError("LEASE_EXPIRED")
        for source in json.loads(job["sources"]):
            current = policy(uow.connection, UUID(run["session_id"]), UUID(source))
            row = uow.connection.execute(
                "SELECT 1 FROM platform_sources WHERE session_id=? AND id=? AND revision=?",
                (run["session_id"], source, run["revision"]),
            ).fetchone()
            if current is None or row is None or current.expires_ms <= self.now():
                raise ContractError("SOURCE_PERMISSION_REQUIRED")
            current.rights.require("local")
            for right in p.rights:
                current.rights.require(right)
        return p

    def create(
        self,
        ctx: RequestContext,
        config: RunConfig,
        inputs: list[StageInput],
        *,
        budget: int,
        deadline_ms: int,
        expected_revision: int,
        key: str,
    ) -> AnalysisRun:
        config = RunConfig.model_validate_json(config.model_dump_json())
        inputs = [StageInput.model_validate_json(i.model_dump_json()) for i in inputs]
        if (
            "worker" in ctx.capabilities
            or "analysis" not in ctx.capabilities
            or type(budget) is not int
            or not 0 <= budget <= 10**12
            or type(deadline_ms) is not int
            or not self.now() < deadline_ms <= self.now() + 86400000
            or not 1 <= len(inputs) <= 64
            or expected_revision != ctx.input_revision
            or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", key)
        ):
            raise ContractError("INVALID_INPUT")
        for item in inputs:
            if len(set(item.source_ids)) != len(item.source_ids) or len(set(item.asset_ids)) != len(
                item.asset_ids
            ):
                raise ContractError("INVALID_INPUT")
            p = self.policies.get(item.stage)
            if p is None or not p.ready():
                raise ContractError("PROVIDER_UNAVAILABLE")
            if config != p.config:
                raise ContractError("VERSION_CONFLICT")
            if budget < p.reservation:
                raise ContractError("BUDGET_EXCEEDED")
            if "cloud_audio" in p.rights and not item.asset_ids:
                raise ContractError("INVALID_INPUT")
        requesthash = digest(
            {
                "config": config.model_dump(mode="json"),
                "inputs": [i.model_dump(mode="json") for i in inputs],
                "budget": budget,
                "deadline": deadline_ms,
                "revision": expected_revision,
                "policies": [self.policies[i.stage].fingerprint for i in inputs],
            }
        )
        with self.database.begin() as uow:
            self.permissions.enforce(uow, ctx)
            for item in inputs:
                if item.asset_ids:
                    ctx.require("audio", ctx.session_id)
                for source in item.source_ids:
                    self.permissions.require_source_rights(uow, ctx, source)
                    current = policy(uow.connection, ctx.session_id, source)
                    if current is None or current.expires_ms <= self.now():
                        raise ContractError("SOURCE_PERMISSION_REQUIRED")
                    for right in self.policies[item.stage].rights:
                        current.rights.require(right)
                for aid in item.asset_ids:
                    asset = uow.connection.execute(
                        "SELECT source_id,revision FROM platform_assets WHERE "
                        "session_id=? AND id=?",
                        (str(ctx.session_id), str(aid)),
                    ).fetchone()
                    if (
                        asset is None
                        or asset["revision"] != ctx.input_revision
                        or UUID(asset["source_id"]) not in item.source_ids
                    ):
                        raise ContractError("ACCESS_DENIED")
            old = uow.connection.execute(
                "SELECT * FROM platform_run_requests WHERE actor_id=? AND session_id=? AND key=?",
                (str(ctx.actor_id), str(ctx.session_id), key),
            ).fetchone()
            if old:
                if old["request_hash"] != requesthash:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return AnalysisRun.model_validate_json(old["payload"])
            config_hash = digest(
                {
                    "config": config.model_dump(mode="json"),
                    "policies": sorted(
                        (i.stage, self.policies[i.stage].fingerprint) for i in inputs
                    ),
                }
            )
            run = AnalysisRun(
                id=uuid4(),
                session_id=ctx.session_id,
                analysis_run_id=None,
                revision=ctx.input_revision,
                status="QUEUED",
                input_hash=ctx.input_hash,
                config_hash=config_hash,
                usage=None,
                **config.model_dump(exclude={"schema_version"}),
            )
            run = run.model_copy(update={"analysis_run_id": run.id})
            account = uow.connection.execute(
                "SELECT credential_version FROM platform_accounts WHERE id=?", (str(ctx.actor_id),)
            ).fetchone()
            uow.connection.execute(
                "INSERT INTO platform_runs VALUES (?,?,?)",
                (str(ctx.session_id), str(run.id), ctx.input_revision),
            )
            uow.connection.execute(
                "INSERT INTO "
                "platform_run_state(id,session_id,revision,creator_id,"
                "credential_version,as_of_ms,input_hash,config_hash,config,payload,"
                "deadline_ms,budget) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(run.id),
                    str(ctx.session_id),
                    ctx.input_revision,
                    str(ctx.actor_id),
                    account[0],
                    ctx.as_of_ms,
                    ctx.input_hash,
                    config_hash,
                    config.model_dump_json(),
                    run.model_dump_json(),
                    deadline_ms,
                    budget,
                ),
            )
            for item in inputs:
                jid = uuid4()
                uow.connection.execute(
                    "INSERT INTO platform_jobs VALUES (?,?,?,?)",
                    (str(ctx.session_id), str(jid), str(run.id), ctx.input_revision),
                )
                uow.connection.execute(
                    "INSERT INTO "
                    "platform_job_state(id,session_id,run_id,stage,policy_hash,"
                    "sources,assets,state,ready_ms) VALUES (?,?,?,?,?,?,?,'QUEUED',?)",
                    (
                        str(jid),
                        str(ctx.session_id),
                        str(run.id),
                        item.stage,
                        self.policies[item.stage].fingerprint,
                        json.dumps(sorted(map(str, item.source_ids))),
                        json.dumps(sorted(map(str, item.asset_ids))),
                        self.now(),
                    ),
                )
            uow.connection.execute(
                "INSERT INTO platform_run_requests VALUES (?,?,?,?,?,?)",
                (
                    str(ctx.actor_id),
                    str(ctx.session_id),
                    key,
                    requesthash,
                    str(run.id),
                    run.model_dump_json(),
                ),
            )
            uow.audit(ctx, "RUN_CREATED", run.id)
            uow.commit()
            return run

    def _run(self, uow: UnitOfWork, run_id: UUID | str) -> sqlite3.Row:
        row = uow.connection.execute(
            "SELECT * FROM platform_run_state WHERE id=?", (str(run_id),)
        ).fetchone()
        if row is None:
            raise ContractError("ACCESS_DENIED")
        return cast(sqlite3.Row, row)

    def _finish(
        self,
        uow: UnitOfWork,
        attempt: sqlite3.Row,
        state: str,
        *,
        charge: int | None = None,
        usage: Usage | None = None,
        failure: str | None = None,
    ) -> None:
        if attempt["state"] != "ACTIVE":
            raise ContractError("LEASE_EXPIRED")
        cost = attempt["reservation"] if charge is None else charge
        uow.connection.execute(
            "UPDATE platform_attempt_state SET state=?,charged=?,usage=?,failure_code=? WHERE id=?",
            (state, cost, usage.model_dump_json() if usage else None, failure, attempt["id"]),
        )
        uow.connection.execute(
            "UPDATE platform_run_state SET "
            "reserved=reserved-?,used=used+?,version=version+1 WHERE id=(SELECT "
            "run_id FROM platform_job_state WHERE id=?)",
            (attempt["reservation"], cost, attempt["job_id"]),
        )
        uow.connection.execute(
            "UPDATE platform_worker_scopes SET revoked=1 WHERE id=?", (attempt["scope_id"],)
        )
        logged_lease = JobLease.model_validate_json(attempt["lease"])
        uow.after_commit(
            lambda: emit(
                event="JOB_ATTEMPT_FINISHED",
                session_id=UUID(attempt["session_id"]),
                run_id=logged_lease.analysis_run_id,
                stage=logged_lease.stage,
                config_hash=logged_lease.config_hash,
                input_hash=logged_lease.input_hash,
                job_id=UUID(attempt["job_id"]),
                attempt_id=UUID(attempt["id"]),
                charged_microunits=cost,
                measurement="COMMITTED_ATTEMPT",
            )
        )

    def _sync_run(self, uow: UnitOfWork, run_id: str, forced: str | None = None) -> None:
        run = self._run(uow, run_id)
        rows = uow.connection.execute(
            "SELECT state FROM platform_job_state WHERE run_id=?", (run_id,)
        ).fetchall()
        states = {r[0] for r in rows}
        status = forced or (
            "RUNNING"
            if "RUNNING" in states
            else "QUEUED"
            if states.intersection({"QUEUED", "RETRY_WAIT"})
            else "PARTIAL"
            if "FAILED" in states and states.intersection({"SUCCEEDED", "PARTIAL"})
            else "FAILED"
            if "FAILED" in states
            else "CANCELLED"
            if "CANCELLED" in states
            else "PARTIAL"
            if "PARTIAL" in states
            else "COMPLETED"
        )
        usages = [
            Usage.model_validate_json(r[0])
            if r[0]
            else Usage(
                audio_ms=None,
                input_tokens=None,
                output_tokens=None,
                cost_microunits=None,
                latency_ms=0,
            )
            for r in uow.connection.execute(
                "SELECT a.usage FROM platform_attempt_state a JOIN platform_job_state "
                "j ON j.id=a.job_id WHERE j.run_id=? AND a.state!='ACTIVE'",
                (run_id,),
            )
        ]
        usage = None
        if usages:

            def total(field: str) -> int | None:
                values = [getattr(v, field) for v in usages]
                return None if any(v is None for v in values) else sum(values)

            usage = Usage(
                audio_ms=total("audio_ms"),
                input_tokens=total("input_tokens"),
                output_tokens=total("output_tokens"),
                cost_microunits=total("cost_microunits"),
                latency_ms=sum(v.latency_ms for v in usages),
            )
        payload = AnalysisRun.model_validate_json(run["payload"]).model_copy(
            update={"status": status, "usage": usage}
        )
        uow.connection.execute(
            "UPDATE platform_run_state SET payload=? WHERE id=?",
            (payload.model_dump_json(), run_id),
        )

    def _retry(
        self,
        uow: UnitOfWork,
        job: sqlite3.Row,
        p: StagePolicy | None,
        failure: str,
        *,
        retry: bool = True,
    ) -> None:
        run = self._run(uow, job["run_id"])
        eligible = bool(
            retry
            and p
            and job["attempt_count"] < p.max_attempts
            and self.now() + 1000 < run["deadline_ms"]
            and run["budget"] - run["used"] - run["reserved"] >= p.reservation
        )
        uow.connection.execute(
            "UPDATE platform_job_state SET state=?,ready_ms=?,failure_code=? WHERE id=?",
            (
                "RETRY_WAIT" if eligible else "FAILED",
                self.now() + 1000 * max(1, job["attempt_count"]) + secrets.randbelow(501),
                failure,
                job["id"],
            ),
        )

    def _recover(self, uow: UnitOfWork) -> None:
        jobs = uow.connection.execute(
            "SELECT * FROM platform_job_state WHERE state IN "
            "('QUEUED','RETRY_WAIT','RUNNING') ORDER BY id"
        ).fetchall()
        for job in jobs:
            run = self._run(uow, job["run_id"])
            p = self.policies.get(job["stage"])
            invalid = None
            try:
                self._eligible(uow, run, job)
            except ContractError as exc:
                invalid = exc.code
            attempt = uow.connection.execute(
                "SELECT * FROM platform_attempt_state WHERE job_id=? AND state='ACTIVE'",
                (job["id"],),
            ).fetchone()
            if attempt:
                lease = JobLease.model_validate_json(attempt["lease"])
                scope = uow.connection.execute(
                    "SELECT s.revoked,w.revoked AS wr,w.expires_ms FROM "
                    "platform_worker_scopes s JOIN platform_workers w ON "
                    "w.id=s.worker_id WHERE s.id=?",
                    (attempt["scope_id"],),
                ).fetchone()
                if (
                    invalid
                    or scope["revoked"]
                    or scope["wr"]
                    or self.now() >= min(scope["expires_ms"], lease.expires_ms)
                ):
                    self._finish(uow, attempt, "EXPIRED", failure=invalid or "LEASE_EXPIRED")
                    self._retry(uow, job, p, invalid or "LEASE_EXPIRED", retry=invalid is None)
            elif invalid:
                self._retry(uow, job, p, invalid, retry=False)
            elif p and run["budget"] - run["used"] - run["reserved"] < p.reservation:
                # Other active reservations may complete and release unused budget.
                if run["reserved"] == 0:
                    self._retry(uow, job, p, "BUDGET_EXCEEDED", retry=False)
            self._sync_run(uow, job["run_id"])

    def recover(self) -> None:
        with self.database.begin() as uow:
            self._recover(uow)
            uow.commit()

    def lease(self, token: str, worker_id: UUID, stage: str) -> JobLease | None:
        if stage not in self.policies:
            raise ContractError("INVALID_INPUT")
        with self.database.begin() as uow:
            worker = self._principal(uow, token)
            if str(worker_id) != worker["id"]:
                raise ContractError("ACCESS_DENIED")
            self._recover(uow)
            p = self.policies[stage]
            if not p.ready():
                raise ContractError("PROVIDER_UNAVAILABLE")
            active = uow.connection.execute(
                "SELECT COUNT(*) FROM platform_job_state WHERE stage=? AND state='RUNNING'",
                (stage,),
            ).fetchone()[0]
            if active >= p.concurrency:
                uow.commit()
                return None
            rows = uow.connection.execute(
                "SELECT * FROM platform_job_state WHERE stage=? AND state IN "
                "('QUEUED','RETRY_WAIT') AND ready_ms<=? ORDER BY ready_ms,id",
                (stage, self.now()),
            ).fetchall()
            for job in rows:
                run = self._run(uow, job["run_id"])
                self._eligible(uow, run, job)
                if run["budget"] - run["reserved"] - run["used"] < p.reservation:
                    continue
                scope = uuid4()
                lease = JobLease(
                    session_id=UUID(run["session_id"]),
                    analysis_run_id=UUID(run["id"]),
                    revision=run["revision"],
                    job_id=UUID(job["id"]),
                    attempt_id=uuid4(),
                    lease_id=uuid4(),
                    owner_id=worker_id,
                    stage=p.stage,
                    input_hash=run["input_hash"],
                    config_hash=run["config_hash"],
                    expires_ms=min(
                        self.now() + p.lease_ms, run["deadline_ms"], worker["expires_ms"]
                    ),
                    deadline_ms=run["deadline_ms"],
                    budget_microunits=p.reservation,
                    asset_ids=[UUID(v) for v in json.loads(job["assets"])],
                )
                uow.connection.execute(
                    "INSERT INTO platform_worker_scopes VALUES (?,?,?,?,?,?,?,0)",
                    (
                        str(scope),
                        str(worker_id),
                        run["session_id"],
                        run["id"],
                        run["revision"],
                        run["as_of_ms"],
                        lease.expires_ms,
                    ),
                )
                for source in json.loads(job["sources"]):
                    uow.connection.execute(
                        "INSERT INTO platform_worker_sources VALUES (?,?,?,?)",
                        (str(scope), run["session_id"], source, run["revision"]),
                    )
                for aid in json.loads(job["assets"]):
                    uow.connection.execute(
                        "INSERT INTO platform_worker_assets VALUES (?,?,?)",
                        (str(scope), run["session_id"], aid),
                    )
                uow.connection.execute(
                    "INSERT INTO platform_attempts VALUES (?,?,?,?)",
                    (run["session_id"], str(lease.attempt_id), job["id"], str(lease.lease_id)),
                )
                uow.connection.execute(
                    "INSERT INTO platform_attempt_timing VALUES (?,?,?)",
                    (run["session_id"], str(lease.attempt_id), self.now()),
                )
                uow.connection.execute(
                    "INSERT INTO "
                    "platform_attempt_state(id,session_id,job_id,worker_id,scope_id,"
                    "lease,state,reservation) VALUES (?,?,?,?,?,?,'ACTIVE',?)",
                    (
                        str(lease.attempt_id),
                        run["session_id"],
                        job["id"],
                        str(worker_id),
                        str(scope),
                        lease.model_dump_json(),
                        p.reservation,
                    ),
                )
                uow.connection.execute(
                    "UPDATE platform_job_state SET "
                    "state='RUNNING',attempt_count=attempt_count+1 WHERE id=?",
                    (job["id"],),
                )
                uow.connection.execute(
                    "UPDATE platform_run_state SET "
                    "reserved=reserved+?,version=version+1 WHERE id=?",
                    (p.reservation, run["id"]),
                )
                self._sync_run(uow, run["id"])
                uow.commit()
                return lease
            uow.commit()
            return None

    def _attempt(
        self, uow: UnitOfWork, token: str, lease: JobLease | JobResult, *, active: bool = True
    ) -> tuple[sqlite3.Row, sqlite3.Row, sqlite3.Row, StagePolicy]:
        worker = self._principal(uow, token)
        attempt = uow.connection.execute(
            "SELECT * FROM platform_attempt_state WHERE id=?", (str(lease.attempt_id),)
        ).fetchone()
        if attempt is None or worker["id"] != attempt["worker_id"]:
            raise ContractError("ACCESS_DENIED")
        original = JobLease.model_validate_json(attempt["lease"])
        if any(
            getattr(original, k) != getattr(lease, k)
            for k in (
                "session_id",
                "analysis_run_id",
                "revision",
                "job_id",
                "attempt_id",
                "lease_id",
                "input_hash",
                "config_hash",
            )
        ):
            raise ContractError("VERSION_CONFLICT")
        if isinstance(lease, JobLease) and any(
            getattr(original, k) != getattr(lease, k)
            for k in ("owner_id", "stage", "deadline_ms", "budget_microunits", "asset_ids")
        ):
            raise ContractError("ACCESS_DENIED")
        job = uow.connection.execute(
            "SELECT * FROM platform_job_state WHERE id=?", (attempt["job_id"],)
        ).fetchone()
        run = self._run(uow, job["run_id"])
        p = self._eligible(uow, run, job, active=active)
        scope = uow.connection.execute(
            "SELECT * FROM platform_worker_scopes WHERE id=?", (attempt["scope_id"],)
        ).fetchone()
        if active and (
            attempt["state"] != "ACTIVE"
            or job["state"] != "RUNNING"
            or scope["revoked"]
            or self.now() >= min(original.expires_ms, scope["expires_ms"])
        ):
            raise ContractError("LEASE_EXPIRED")
        if (
            not active
            and uow.connection.execute(
                "SELECT 1 FROM platform_permission_audit WHERE target_id=? "
                "AND action='REVOKE_WORKER_SCOPE'",
                (attempt["scope_id"],),
            ).fetchone()
        ):
            raise ContractError("ACCESS_DENIED")
        # Completed attempt scope is server-revoked; explicit later revocation is handled
        # by current principal/source/creator checks rather than reactivating the scope.
        return cast(sqlite3.Row, attempt), cast(sqlite3.Row, job), run, p

    def scope(self, token: str, lease: JobLease) -> UUID:
        with self.database.begin() as uow:
            attempt, *_ = self._attempt(uow, token, lease)
            return UUID(attempt["scope_id"])

    def context(self, token: str, lease: JobLease) -> RequestContext:
        return self.permissions.worker_context(token, self.scope(token, lease))

    def worker_mode(self, uow: UnitOfWork, scope_id: str) -> Mode:
        row = uow.connection.execute(
            "SELECT j.stage FROM platform_attempt_state a "
            "JOIN platform_job_state j ON j.id=a.job_id WHERE a.scope_id=?",
            (scope_id,),
        ).fetchone()
        policy = self.policies.get(row[0]) if row else None
        return policy.execution_mode if policy else "AS_KNOWN"

    def guard(self, uow: UnitOfWork, ctx: RequestContext) -> None:
        if "worker" not in ctx.capabilities:
            return
        proof = uow.connection.execute(
            "SELECT scope_id FROM platform_context_receipts WHERE digest=?", (context_digest(ctx),)
        ).fetchone()
        attempt = (
            uow.connection.execute(
                "SELECT * FROM platform_attempt_state WHERE scope_id=?", (proof[0],)
            ).fetchone()
            if proof
            else None
        )
        if attempt is None:
            raise ContractError("ACCESS_DENIED")
        job = uow.connection.execute(
            "SELECT * FROM platform_job_state WHERE id=?", (attempt["job_id"],)
        ).fetchone()
        self._eligible(uow, self._run(uow, job["run_id"]), job)
        if (
            attempt["state"] != "ACTIVE"
            or self.now() >= JobLease.model_validate_json(attempt["lease"]).expires_ms
        ):
            raise ContractError("LEASE_EXPIRED")

    def heartbeat(self, token: str, lease: JobLease) -> JobLease:
        lease = JobLease.model_validate_json(lease.model_dump_json())
        with self.database.begin() as uow:
            attempt, _, run, p = self._attempt(uow, token, lease)
            worker = self._principal(uow, token)
            current = JobLease.model_validate_json(attempt["lease"])
            updated = current.model_copy(
                update={
                    "expires_ms": min(
                        self.now() + p.lease_ms, run["deadline_ms"], worker["expires_ms"]
                    )
                }
            )
            uow.connection.execute(
                "UPDATE platform_attempt_state SET lease=? WHERE id=?",
                (updated.model_dump_json(), attempt["id"]),
            )
            uow.connection.execute(
                "UPDATE platform_worker_scopes SET expires_ms=? WHERE id=?",
                (updated.expires_ms, attempt["scope_id"]),
            )
            uow.commit()
            return updated

    def cancelled(self, token: str, lease: JobLease) -> bool:
        # Authenticate first; an invalid credential cannot probe job state.
        self.permissions.authenticate_worker(token)
        try:
            with self.database.begin() as uow:
                self._attempt(uow, token, lease)
            return False
        except ContractError as error:
            if error.code in (
                "JOB_CANCELLED",
                "LEASE_EXPIRED",
                "SOURCE_REVISION_CHANGED",
                "VERSION_CONFLICT",
                "SOURCE_PERMISSION_REQUIRED",
                "CLOUD_TRANSFER_BLOCKED",
            ):
                return True
            raise

    def inspect(self, ctx: RequestContext, run_id: UUID) -> dict[str, object]:
        if "worker" in ctx.capabilities:
            raise ContractError("ACCESS_DENIED")
        with self.database.begin() as uow:
            self.permissions.enforce(uow, ctx)
            ctx.require("analysis", ctx.session_id)
            run = self._run(uow, run_id)
            if run["session_id"] != str(ctx.session_id):
                raise ContractError("ACCESS_DENIED")
            self._recover(uow)
            run = self._run(uow, run_id)
            jobs = [
                dict(r)
                for r in uow.connection.execute(
                    "SELECT id,stage,state,attempt_count,failure_code FROM "
                    "platform_job_state WHERE run_id=? ORDER BY id",
                    (str(run_id),),
                )
            ]
            result: dict[str, object] = {
                "run": AnalysisRun.model_validate_json(run["payload"]).model_dump(mode="json"),
                "budget": run["budget"],
                "reserved": run["reserved"],
                "used": run["used"],
                "version": run["version"],
                "jobs": jobs,
            }
            uow.commit()
            return result

    def cancel(self, ctx: RequestContext, run_id: UUID, *, key: str, expected_version: int) -> None:
        if (
            "worker" in ctx.capabilities
            or type(expected_version) is not int
            or expected_version < 1
            or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", key)
        ):
            raise ContractError("ACCESS_DENIED")
        with self.database.begin() as uow:
            self.permissions.enforce(uow, ctx)
            ctx.require("analysis", ctx.session_id)
            run = self._run(uow, run_id)
            if run["session_id"] != str(ctx.session_id):
                raise ContractError("ACCESS_DENIED")
            old = uow.connection.execute(
                "SELECT expected_version FROM platform_run_cancels "
                "WHERE actor_id=? AND run_id=? AND key=?",
                (str(ctx.actor_id), str(run_id), key),
            ).fetchone()
            if old:
                if old[0] != expected_version:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return
            if run["version"] != expected_version:
                raise ContractError("VERSION_CONFLICT")
            for attempt in uow.connection.execute(
                "SELECT a.* FROM platform_attempt_state a JOIN platform_job_state j "
                "ON j.id=a.job_id WHERE j.run_id=? AND a.state='ACTIVE'",
                (str(run_id),),
            ).fetchall():
                self._finish(uow, attempt, "CANCELLED", failure="JOB_CANCELLED")
            uow.connection.execute(
                "UPDATE platform_job_state SET "
                "state='CANCELLED',failure_code='JOB_CANCELLED' WHERE run_id=? AND "
                "state IN ('QUEUED','RETRY_WAIT','RUNNING')",
                (str(run_id),),
            )
            if AnalysisRun.model_validate_json(run["payload"]).status not in (
                "COMPLETED",
                "PARTIAL",
                "FAILED",
            ):
                self._sync_run(uow, str(run_id), "CANCELLED")
            uow.connection.execute(
                "INSERT INTO platform_run_cancels VALUES (?,?,?,?)",
                (str(ctx.actor_id), str(run_id), key, expected_version),
            )
            uow.connection.execute(
                "UPDATE platform_run_state SET version=version+1 WHERE id=?", (str(run_id),)
            )
            uow.audit(ctx, "RUN_CANCELLED", run_id)
            uow.commit()

    def input(self, token: str, lease: JobLease) -> dict[str, object]:
        ctx = self.context(token, lease)
        audio: list[dict[str, object]] = []
        with self.database.begin() as uow:
            _, job, run, p = self._attempt(uow, token, lease)
            self.permissions.enforce(uow, ctx)
            config = RunConfig.model_validate_json(run["config"])
            for aid in lease.asset_ids:
                located = self.assets.locate(uow, ctx, aid)
                row = uow.connection.execute(
                    "SELECT p.payload,p.source_id,s.source_hash FROM platform_source_packages p "
                    "JOIN platform_sources s ON s.session_id=p.session_id AND s.id=p.source_id "
                    "AND s.revision=p.revision WHERE p.package_id=?",
                    (str(located.package_id),),
                ).fetchone()
                prepared = PreparedImport.model_validate_json(row["payload"])
                clock = next(f.clock for f in prepared.declaration.files if f.file_id == aid)
                audio.append(
                    {
                        "asset": located.asset.model_dump(mode="json"),
                        "source_id": row["source_id"],
                        "source_hash": row["source_hash"],
                        "clock": clock.model_dump(mode="json"),
                    }
                )
            # AS_KNOWN records only; no labels, source inventory, private path or secret.
            context_records: list[dict[str, object]] = []
            if "cloud_context" in p.rights:
                sources = set(json.loads(job["sources"]))
                records = uow.connection.execute(
                    "SELECT kind,payload FROM platform_records WHERE session_id=? "
                    "AND revision=? AND run_id IS NULL AND namespace='source_events' "
                    "AND json_extract(payload,'$.source_id') IN "
                    "(SELECT source_id FROM platform_worker_sources WHERE scope_id="
                    "(SELECT scope_id FROM platform_attempt_state WHERE id=?)) "
                    "AND json_extract(payload,'$.event_time_ms')<=? "
                    "AND json_extract(payload,'$.available_time_ms')<=? LIMIT 513",
                    (
                        str(ctx.session_id),
                        ctx.input_revision,
                        str(lease.attempt_id),
                        ctx.as_of_ms,
                        ctx.as_of_ms,
                    ),
                )
                for record in records:
                    data = json.loads(record["payload"])
                    if (
                        data.get("source_id") in sources
                        and data["event_time_ms"] <= ctx.as_of_ms
                        and data.get("available_time_ms") is not None
                        and data["available_time_ms"] <= ctx.as_of_ms
                    ):
                        context_records.append(data)
                if len(context_records) > 512:
                    raise ContractError("NOT_EVALUABLE")
            result: dict[str, object] = {
                "context": ctx.model_dump(mode="json"),
                "config": config.model_dump(mode="json"),
                "audio": audio,
                "records": context_records,
            }
            if len(json.dumps(result).encode()) > 1024**2:
                raise ContractError("NOT_EVALUABLE")
            return result

    def _fault(self, point: str) -> None:
        if self.fault is not None:
            self.fault(point)

    def _candidate(
        self, uow: UnitOfWork, ctx: RequestContext, r: JobResult, p: StagePolicy
    ) -> dict[UUID, Evidence]:
        if (
            len(r.model_dump_json().encode()) > 1024**2
            or len(r.outputs) > 256
            or len(r.evidence) > 2048
            or len(r.artifacts) > 32
            or result_hash(r) != r.output_hash
        ):
            raise ContractError("INVALID_AI_OUTPUT")
        if r.status == "FAILED" and r.evidence:
            raise ContractError("INVALID_AI_OUTPUT")
        if r.usage.cost_microunits is not None and r.usage.cost_microunits > p.reservation:
            raise ContractError("BUDGET_EXCEEDED")
        if len({o.id for o in r.outputs}) != len(r.outputs) or len(
            {a.id for a in r.artifacts}
        ) != len(r.artifacts):
            raise ContractError("INVALID_AI_OUTPUT")
        candidates: dict[UUID, Contract] = {o.id: o for o in r.outputs}
        references: dict[UUID, Evidence] = {}

        def collect(value: object) -> None:
            if isinstance(value, Evidence):
                old = references.get(value.id)
                if old is not None and old != value:
                    raise ContractError("INVALID_AI_OUTPUT")
                references[value.id] = value
            elif isinstance(value, Contract):
                for name in type(value).model_fields:
                    collect(getattr(value, name))
            elif isinstance(value, list):
                for item in value:
                    collect(item)

        for output in r.outputs:
            if type(output).__name__ not in p.outputs or output.event_time_ms > ctx.as_of_ms:
                raise ContractError("INVALID_AI_OUTPUT")
            if isinstance(output, TranscriptSegment):
                if (
                    output.origin == "HUMAN_CORRECTION"
                    or output.available_time_ms is not None
                    or output.event_time_ms != output.end_ms
                    or output.end_ms > ctx.as_of_ms
                ):
                    raise ContractError("INVALID_AI_OUTPUT")
                if output.origin == "MOCK" and not self.allow_mock:
                    raise ContractError("INVALID_AI_OUTPUT")
                anchors = [
                    a
                    for a in output.evidence
                    if a.kind == "AUDIO" and a.source_id == output.source_id
                ]
                if not anchors or not any(
                    a.start_ms is not None
                    and a.end_ms is not None
                    and a.start_ms <= output.start_ms < output.end_ms <= a.end_ms
                    for a in anchors
                ):
                    raise ContractError("EVIDENCE_UNAVAILABLE")
                for anchor in anchors:
                    if anchor.segment_id is None:
                        raise ContractError("EVIDENCE_UNAVAILABLE")
                    parent = self.assets.locate(uow, ctx, anchor.segment_id)
                    if output.channel >= parent.asset.channels:
                        raise ContractError("INVALID_AI_OUTPUT")
            collect(output)
        collect(r.evidence)
        for e in references.values():
            self.evidence.resolve_in_uow(ctx, e, uow, candidates=candidates)
        for artifact in r.artifacts:
            spec, _, _ = self.assets.staged_in_uow(ctx, artifact.id, uow)
            if artifact != spec:
                raise ContractError("INVALID_AI_OUTPUT")
        return references

    def result(self, token: str, candidate: JobResult) -> CommitReceipt:
        try:
            candidate = JobResult.model_validate_json(candidate.model_dump_json())
        except ValidationError:
            raise ContractError("INVALID_AI_OUTPUT") from None
        request_hash = digest(candidate.model_dump(mode="json"))
        with self.database.begin() as uow:
            attempt, _, _, _ = self._attempt(uow, token, candidate, active=False)
            previous = uow.connection.execute(
                "SELECT * FROM platform_receipts WHERE session_id=? AND attempt_id=?",
                (str(candidate.session_id), str(candidate.attempt_id)),
            ).fetchone()
            if previous:
                if previous["request_hash"] != request_hash:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return CommitReceipt.model_validate_json(previous["payload"])
            self._attempt(uow, token, candidate)
            scope = UUID(attempt["scope_id"])
        # The module may read through EvidenceService; no provider/domain validation
        # runs under the writer lock. Authority is checked again before any write.
        try:
            ctx = self.permissions.worker_context(token, scope)
            with self.database.begin() as uow:
                _, _, _, p = self._attempt(uow, token, candidate)
                self._candidate(uow, ctx, candidate, p)
            validated = self.module.validate(ctx, candidate, self.evidence)
        except ContractError:
            # Another identical request may have committed and revoked this
            # attempt while validation was outside the lock. Recheck current
            # authority and the immutable receipt before returning that outcome.
            with self.database.begin() as uow:
                self._attempt(uow, token, candidate, active=False)
                previous = uow.connection.execute(
                    "SELECT * FROM platform_receipts WHERE session_id=? AND attempt_id=?",
                    (str(candidate.session_id), str(candidate.attempt_id)),
                ).fetchone()
                if previous:
                    if previous["request_hash"] != request_hash:
                        raise ContractError("IDEMPOTENCY_CONFLICT") from None
                    return CommitReceipt.model_validate_json(previous["payload"])
            raise
        try:
            validated = JobResult.model_validate_json(validated.model_dump_json())
        except (AttributeError, ValidationError):
            raise ContractError("INVALID_AI_OUTPUT") from None
        # Validation can reject/abstain, but cannot silently rewrite a worker's
        # idempotent request or routing/config/usage authority.
        if validated != candidate:
            raise ContractError("INVALID_AI_OUTPUT")
        with self.database.begin() as uow:
            attempt, job, run, p = self._attempt(uow, token, validated, active=False)
            previous = uow.connection.execute(
                "SELECT * FROM platform_receipts WHERE session_id=? AND attempt_id=?",
                (str(validated.session_id), str(validated.attempt_id)),
            ).fetchone()
            if previous:
                if previous["request_hash"] != request_hash:
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return CommitReceipt.model_validate_json(previous["payload"])
            self._attempt(uow, token, validated)
            self.permissions.enforce(uow, ctx)
            references = self._candidate(uow, ctx, validated, p)
            if validated.status != "FAILED":
                for output in validated.outputs:
                    try:
                        uow.repository(p.outputs[type(output).__name__]).get(ctx, output.id)
                    except KeyError:
                        pass
                    else:
                        raise ContractError("IDEMPOTENCY_CONFLICT")
                with uow.domain_writes():
                    p.handler(ctx, validated, uow)
                for output in validated.outputs:
                    persisted = uow.repository(p.outputs[type(output).__name__]).get(ctx, output.id)
                    if type(persisted) is not type(output) or persisted != output:
                        raise ContractError("INVALID_AI_OUTPUT")
            self._fault("domain")
            candidates: dict[UUID, Contract] = {o.id: o for o in validated.outputs}
            for reference in references.values():
                self.evidence.register_candidate(ctx, reference, uow, candidates)
            self._fault("evidence")
            for artifact in validated.artifacts:
                spec, _, package = self.assets.staged_in_uow(ctx, artifact.id, uow)
                uow.connection.execute(
                    "INSERT INTO platform_artifacts VALUES (?,?,?,?,?,?)",
                    (
                        str(ctx.session_id),
                        str(spec.id),
                        str(ctx.analysis_run_id),
                        ctx.input_revision,
                        str(package),
                        spec.model_dump_json(),
                    ),
                )
                uow.connection.execute(
                    "UPDATE platform_artifact_staging SET accepted=1 WHERE id=?", (str(spec.id),)
                )
            self._fault("artifact")
            uow.audit(ctx, "JOB_RESULT_COMMITTED", validated.job_id)
            self._fault("audit")
            event = JobProgress(
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                job_id=validated.job_id,
                stage=job["stage"],
                status="FAILED"
                if validated.status == "FAILED"
                else "PARTIAL"
                if validated.status == "PARTIAL"
                else "COMPLETED",
                completed_units=len(validated.outputs),
                total_units=None,
            )
            sequence = uow.enqueue_event(ctx, event)
            self._fault("event")
            receipt = CommitReceipt(
                id=uuid4(),
                session_id=ctx.session_id,
                analysis_run_id=ctx.analysis_run_id,
                revision=ctx.input_revision,
                job_id=validated.job_id,
                attempt_id=validated.attempt_id,
                output_hash=validated.output_hash,
                sequence=sequence,
            )
            uow.connection.execute(
                "INSERT INTO platform_receipts VALUES (?,?,?,?)",
                (
                    str(ctx.session_id),
                    str(validated.attempt_id),
                    request_hash,
                    receipt.model_dump_json(),
                ),
            )
            self._fault("receipt")
            self._finish(
                uow,
                attempt,
                "COMMITTED",
                charge=validated.usage.cost_microunits,
                usage=validated.usage,
                failure=validated.failure_code,
            )
            if validated.status == "FAILED":
                self._retry(
                    uow,
                    job,
                    p,
                    validated.failure_code or "INVALID_AI_OUTPUT",
                    retry=validated.failure_code
                    in ("PROVIDER_UNAVAILABLE", "PROVIDER_QUOTA_EXCEEDED"),
                )
            else:
                uow.connection.execute(
                    "UPDATE platform_job_state SET state=?,failure_code=NULL WHERE id=?",
                    ("PARTIAL" if validated.status == "PARTIAL" else "SUCCEEDED", job["id"]),
                )
            self._sync_run(uow, run["id"])
            if self.publish:
                callback = self.publish
                uow.after_commit(lambda: callback(ctx.session_id, sequence))
            self._fault("before_commit")
            uow.commit()
            return receipt


class WorkerJobs:
    """Bound JobClient; worker identity always comes from its live credential."""

    def __init__(self, jobs: Jobs, token: str) -> None:
        self.jobs, self._token = jobs, token

    def lease(self, worker_id: UUID, stage: str) -> JobLease | None:
        return self.jobs.lease(self._token, worker_id, stage)

    def heartbeat(self, lease: JobLease) -> JobLease:
        return self.jobs.heartbeat(self._token, lease)

    def cancelled(self, lease: JobLease) -> bool:
        return self.jobs.cancelled(self._token, lease)

    def result(self, result: JobResult) -> CommitReceipt:
        return self.jobs.result(self._token, result)
