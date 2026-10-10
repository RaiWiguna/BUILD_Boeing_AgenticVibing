"""Single-attempt executor. Run in a dedicated process, with bounded port adapters.

No DB, raw inventory, provider, accepted-state writer or automatic job retry.
All platform calls must have a transport timeout <= heartbeat interval; the
frozen synchronous ports cannot interrupt an implementation that hangs forever.
"""

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable, Generator
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid5

from flowlens.audio import AudioError, AudioTools, prepare_audio
from flowlens.audio.preparation import digest, local_path
from flowlens.contracts.models import (
    ArtifactSubmission,
    CommitReceipt,
    JobLease,
    JobResult,
    TimeRange,
    Usage,
)
from flowlens.contracts.ports import AssetAccess, JobClient
from flowlens.contracts.results import result_hash
from flowlens.workers.audio.models import AudioInput, InputAccess, WorkerConfig, WorkerOutcome


class WorkerStop(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def epoch_ms() -> int:
    """Lease clocks use server-compatible Unix epoch ms, never replay/as-of ms."""
    return time.time_ns() // 1_000_000


class LeaseGuard:
    def __init__(
        self,
        jobs: JobClient,
        lease: JobLease,
        config: WorkerConfig,
        shutdown: threading.Event,
        now: Callable[[], int],
    ) -> None:
        self.jobs, self.lease, self.config = jobs, lease, config
        self.shutdown, self.now = shutdown, now
        self.cancel = threading.Event()
        self.done = threading.Event()
        self.lock = threading.RLock()
        self.code: str | None = None
        self.initial_ms, self.initial_tick = now(), time.monotonic()
        self.thread = threading.Thread(target=self.monitor, name="audio-heartbeat")

    def stop(self, code: str) -> None:
        if self.code is None:
            self.code = code
        self.cancel.set()

    def checkpoint(self) -> None:
        with self.lock:
            # A backwards wall-clock adjustment cannot extend a leased attempt.
            current = max(
                self.now(), self.initial_ms + int((time.monotonic() - self.initial_tick) * 1000)
            )
            if self.shutdown.is_set():
                self.stop("WORKER_SHUTDOWN")
            if current >= self.lease.deadline_ms:
                self.stop("WORKER_DEADLINE")
            elif current >= self.lease.expires_ms:
                self.stop("WORKER_LEASE_EXPIRED")
            if self.code is not None:
                raise WorkerStop(self.code)

    def poll(self, *, heartbeat: bool) -> None:
        with self.lock:
            self.checkpoint()
            if self.jobs.cancelled(self.lease):
                self.stop("WORKER_CANCELLED")
                self.checkpoint()
            if heartbeat:
                old = self.lease
                renewed = JobLease.model_validate_json(self.jobs.heartbeat(old).model_dump_json())
                if (
                    renewed.model_dump(exclude={"expires_ms"})
                    != old.model_dump(exclude={"expires_ms"})
                    or renewed.expires_ms < old.expires_ms
                ):
                    self.stop("WORKER_LOST_LEASE")
                else:
                    self.lease = renewed
            self.checkpoint()

    def monitor(self) -> None:
        # Poll often enough to interrupt a tool near lease/deadline expiry, even
        # when heartbeat scheduling itself is less frequent.
        next_heartbeat = time.monotonic() + self.config.heartbeat_seconds
        while not self.done.wait(min(0.05, self.config.heartbeat_seconds)):
            try:
                due = time.monotonic() >= next_heartbeat
                self.poll(heartbeat=due)
                if due:
                    next_heartbeat = time.monotonic() + self.config.heartbeat_seconds
            except WorkerStop:
                return
            except Exception:
                with self.lock:
                    self.stop("WORKER_CONTROL_UNAVAILABLE")
                return

    def close(self) -> None:
        self.done.set()
        if self.thread.is_alive():
            self.thread.join()


class AudioWorker:
    def __init__(
        self,
        config: WorkerConfig,
        jobs: JobClient,
        assets: AssetAccess,
        inputs: InputAccess,
        tools: AudioTools,
        *,
        shutdown: threading.Event | None = None,
        now: Callable[[], int] = epoch_ms,
    ) -> None:
        self.config = WorkerConfig.model_validate(config.model_dump())
        self.jobs, self.assets, self.inputs, self.tools = jobs, assets, inputs, tools
        self.shutdown = shutdown if shutdown is not None else threading.Event()
        self.now = now
        self.attempts: set[UUID] = set()
        local_path(config.scratch_root, config.scratch_root, directory=True)

    def validate(self, lease: JobLease, binding: AudioInput) -> None:
        ctx = binding.context
        if (
            lease.stage != "AUDIO"
            or lease.owner_id != self.config.worker_id
            or (ctx.session_id, ctx.analysis_run_id, ctx.input_revision, ctx.input_hash)
            != (lease.session_id, lease.analysis_run_id, lease.revision, lease.input_hash)
            or (binding.job_id, binding.attempt_id, binding.lease_id)
            != (lease.job_id, lease.attempt_id, lease.lease_id)
            or binding.config_hash != lease.config_hash
            or (binding.audio_config_hash or binding.config_hash) != self.config.audio.digest()
            or lease.asset_ids != [binding.asset.id]
            or ctx.actor_id != lease.owner_id
            or set(ctx.capabilities) not in ({"worker", "audio"}, {"worker", "read", "analysis"})
            or binding.asset.fixture_path is not None
            or binding.size_bytes > self.config.audio.max_input_bytes
        ):
            raise WorkerStop("WORKER_BINDING_INVALID")

    def download(self, binding: AudioInput, target: Path, guard: LeaseGuard) -> None:
        checksum = hashlib.sha256()
        with target.open("xb") as sink:
            for start in range(0, binding.size_bytes, self.config.block_bytes):
                guard.checkpoint()
                end = min(start + self.config.block_bytes, binding.size_bytes)
                block = self.assets.download(binding.context, binding.asset.id, start, end)
                guard.checkpoint()
                if type(block) is not bytes or len(block) != end - start:
                    raise WorkerStop("WORKER_DOWNLOAD_INVALID")
                sink.write(block)
                checksum.update(block)
        if checksum.hexdigest() != binding.asset.sha256:
            raise WorkerStop("WORKER_CHECKSUM_INVALID")

    def submit_file(
        self,
        binding: AudioInput,
        path: Path,
        artifact: ArtifactSubmission,
        guard: LeaseGuard,
    ) -> None:
        consumed = 0
        checksum = hashlib.sha256()

        def chunks() -> Generator[bytes, None, None]:
            nonlocal consumed
            with path.open("rb") as stream:
                while block := stream.read(self.config.block_bytes):
                    guard.checkpoint()
                    consumed += len(block)
                    if consumed > artifact.size_bytes:
                        raise WorkerStop("WORKER_UPLOAD_INVALID")
                    checksum.update(block)
                    yield block

        guard.poll(heartbeat=False)
        stream = chunks()
        try:
            identifier = self.assets.submit(binding.context, artifact, stream)
        finally:
            # A failing/partial consumer may retain the generator in its traceback.
            # Close its open file before the surrounding private directory is removed.
            stream.close()
        guard.poll(heartbeat=False)
        if (
            identifier != artifact.id
            or consumed != artifact.size_bytes
            or checksum.hexdigest() != artifact.sha256
        ):
            raise WorkerStop("WORKER_UPLOAD_INVALID")

    def process(self, binding: AudioInput, guard: LeaseGuard) -> list[ArtifactSubmission]:
        with TemporaryDirectory(prefix="flowlens-worker-", dir=self.config.scratch_root) as name:
            work = Path(name)
            if os.name != "nt":
                work.chmod(0o700)
            raw, scratch = work / "download", work / "prepare"
            raw.mkdir(mode=0o700)
            scratch.mkdir(mode=0o700)
            source = raw / "asset.audio"
            self.download(binding, source, guard)
            with prepare_audio(
                source=source,
                raw_root=raw,
                scratch_root=scratch,
                source_id=binding.source_id,
                asset=binding.asset,
                clock=binding.clock,
                tools=replace(self.tools, cancel=guard.cancel),
                limits=self.config.audio,
                source_gaps=binding.source_gaps,
                checkpoint=guard.checkpoint,
            ) as prepared:
                metadata = prepared.metadata
                artifacts: list[ArtifactSubmission] = []
                for index, chunk in enumerate(metadata.chunks):
                    start = chunk.plan.source_frames.start * 1000 // metadata.probe.sample_rate
                    end = (
                        chunk.plan.source_frames.end * 1000 + metadata.probe.sample_rate - 1
                    ) // metadata.probe.sample_rate
                    end = min(end, binding.asset.duration_ms)
                    artifact = ArtifactSubmission(
                        id=uuid5(binding.attempt_id, f"audio-{index}"),
                        session_id=binding.context.session_id,
                        analysis_run_id=guard.lease.analysis_run_id,
                        revision=binding.context.input_revision,
                        kind="AUDIO_DERIVATIVE",
                        sha256=chunk.sha256,
                        size_bytes=chunk.byte_count,
                        source_asset_id=binding.asset.id,
                        transform_version=metadata.transform_version,
                        source_range=TimeRange(start_ms=start, end_ms=end),
                        derivative_range=TimeRange(
                            start_ms=0,
                            end_ms=(chunk.local_frames.end * 1000 + metadata.output_rate - 1)
                            // metadata.output_rate,
                        ),
                        expires_at=None,
                        required_capability="audio",
                    )
                    self.submit_file(binding, prepared.directory / chunk.filename, artifact, guard)
                    artifacts.append(artifact)
                # Full exact frame/rate/channel/clock/hash provenance is a private
                # JSON artifact, never smuggled into lease/output/text fields.
                payload = json.dumps(
                    {
                        "version": "audio-worker-1",
                        "job_id": str(binding.job_id),
                        "attempt_id": str(binding.attempt_id),
                        "input_hash": guard.lease.input_hash,
                        "config_hash": binding.config_hash,
                        "artifact_ids": [str(item.id) for item in artifacts],
                        "preparation": metadata.model_dump(mode="json"),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                if len(payload) > self.config.max_metadata_bytes:
                    raise WorkerStop("WORKER_METADATA_LIMIT")
                report = work / "provenance.json"
                report.write_bytes(payload)
                manifest = ArtifactSubmission(
                    id=uuid5(binding.attempt_id, "provenance"),
                    session_id=binding.context.session_id,
                    analysis_run_id=guard.lease.analysis_run_id,
                    revision=binding.context.input_revision,
                    kind="JSON_REPORT",
                    sha256=digest(report),
                    size_bytes=len(payload),
                    source_asset_id=binding.asset.id,
                    transform_version="audio-worker-provenance-1",
                    source_range=None,
                    derivative_range=None,
                    expires_at=None,
                    required_capability="audio",
                )
                self.submit_file(binding, report, manifest, guard)
                artifacts.append(manifest)
                return artifacts

    def deliver(self, result: JobResult, guard: LeaseGuard) -> CommitReceipt:
        # Only resend the exact same in-memory candidate after an ambiguous response.
        # Never repeat preparation, artifact upload or provider calls here.
        for attempt in range(2):
            guard.poll(heartbeat=False)
            try:
                receipt = CommitReceipt.model_validate_json(
                    self.jobs.result(result).model_dump_json()
                )
            except Exception:
                if attempt == 0:
                    continue
                raise WorkerStop("WORKER_RESULT_UNCONFIRMED") from None
            if (
                receipt.session_id,
                receipt.analysis_run_id,
                receipt.revision,
                receipt.job_id,
                receipt.attempt_id,
                receipt.output_hash,
            ) != (
                result.session_id,
                result.analysis_run_id,
                result.revision,
                result.job_id,
                result.attempt_id,
                result.output_hash,
            ):
                raise WorkerStop("WORKER_RECEIPT_INVALID")
            return receipt
        raise WorkerStop("WORKER_RESULT_UNCONFIRMED")

    def run_once(self) -> WorkerOutcome:
        if self.shutdown.is_set():
            return WorkerOutcome("ABORTED", "WORKER_SHUTDOWN")
        if len(self.attempts) >= self.config.max_attempts:
            return WorkerOutcome("ABORTED", "WORKER_RESTART_REQUIRED")
        try:
            leased = self.jobs.lease(self.config.worker_id, "AUDIO")
            if leased is None:
                return WorkerOutcome("IDLE", "WORKER_IDLE")
            lease = JobLease.model_validate_json(leased.model_dump_json())
            if (
                lease.stage != "AUDIO"
                or lease.owner_id != self.config.worker_id
                or len(lease.asset_ids) != 1
            ):
                raise WorkerStop("WORKER_BINDING_INVALID")
            if lease.attempt_id in self.attempts:
                raise WorkerStop("WORKER_ATTEMPT_REUSED")
            self.attempts.add(lease.attempt_id)
            guard = LeaseGuard(self.jobs, lease, self.config, self.shutdown, self.now)
            try:
                guard.poll(heartbeat=True)
                guard.thread.start()
                input_json = self.inputs.resolve(lease).model_dump_json()
                if len(input_json.encode()) > 512 * 1024:
                    raise WorkerStop("WORKER_BINDING_INVALID")
                binding = AudioInput.model_validate_json(input_json)
                self.validate(lease, binding)
                started = time.monotonic()
                failure = False
                code = "WORKER_COMPLETE"
                artifacts: list[ArtifactSubmission] = []
                try:
                    artifacts = self.process(binding, guard)
                except (AudioError, OSError):
                    guard.checkpoint()
                    failure, code = True, "WORKER_AUDIO_FAILED"
                except WorkerStop as exc:
                    guard.checkpoint()
                    if exc.code not in {
                        "WORKER_DOWNLOAD_INVALID",
                        "WORKER_CHECKSUM_INVALID",
                        "WORKER_UPLOAD_INVALID",
                        "WORKER_METADATA_LIMIT",
                    }:
                        raise
                    failure, code = True, exc.code
                guard.poll(heartbeat=False)
                candidate = JobResult(
                    session_id=lease.session_id,
                    analysis_run_id=lease.analysis_run_id,
                    revision=lease.revision,
                    job_id=lease.job_id,
                    attempt_id=lease.attempt_id,
                    lease_id=lease.lease_id,
                    input_hash=lease.input_hash,
                    config_hash=lease.config_hash,
                    output_hash="0" * 64,
                    status="FAILED" if failure else "COMPLETE",
                    outputs=[],
                    evidence=[],
                    artifacts=[] if failure else artifacts,
                    usage=Usage(
                        audio_ms=None,
                        input_tokens=None,
                        output_tokens=None,
                        cost_microunits=None,
                        latency_ms=max(0, int((time.monotonic() - started) * 1000)),
                    ),
                    failure_code="INVALID_AI_OUTPUT" if failure else None,
                )
                candidate = candidate.model_copy(update={"output_hash": result_hash(candidate)})
                receipt = self.deliver(candidate, guard)
                return WorkerOutcome("FAILED" if failure else "RECEIPT", code, receipt)
            finally:
                guard.close()
        except WorkerStop as exc:
            return WorkerOutcome(
                "UNCONFIRMED"
                if exc.code in {"WORKER_RESULT_UNCONFIRMED", "WORKER_RECEIPT_INVALID"}
                else "ABORTED",
                exc.code,
            )
        except Exception:
            return WorkerOutcome("ABORTED", "WORKER_CLIENT_FAILED")

    def serve(self) -> WorkerOutcome:
        """Bounded process lifetime; coordinator alone decides retry/new attempt."""
        while not self.shutdown.is_set():
            outcome = self.run_once()
            if outcome.status == "IDLE":
                self.shutdown.wait(self.config.heartbeat_seconds)
            elif outcome.status != "RECEIPT":
                return outcome
        return WorkerOutcome("ABORTED", "WORKER_SHUTDOWN")
