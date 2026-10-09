"""Standalone MOCK worker acceptance. No SQLite, Package A or provider calls.

python -m flowlens.testing.audio_worker [--real]
The harness process runs the executor with fake platform ports. --real uses local
FFmpeg; the default uses an actual Python subprocess and synthetic PCM copying.
Neither mode proves internal API authentication or real A/B integration.
"""

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
import wave
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from flowlens.audio import AudioError, AudioLimits, AudioTools
from flowlens.audio.models import ProbeInfo
from flowlens.audio.process import run_bounded
from flowlens.contracts.models import (
    ArtifactSubmission,
    CommitReceipt,
    JobLease,
    JobResult,
    RequestContext,
    SourceManifest,
)
from flowlens.core.errors import ContractError
from flowlens.workers.audio import AudioInput, AudioWorker, WorkerConfig
from flowlens.workers.audio.worker import epoch_ms

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class MockTools(AudioTools):
    """MOCK PCM only, with a real interruptible Python child process."""

    processing: threading.Event = field(default_factory=threading.Event)
    delay: float = 0.25
    broken: bool = False

    def probe(self, source: Path, limits: AudioLimits) -> ProbeInfo:
        with wave.open(str(source), "rb") as reader:
            return ProbeInfo(
                sample_rate=reader.getframerate(),
                channels=reader.getnchannels(),
                duration_seconds=reader.getnframes() / reader.getframerate(),
                codec="pcm_s16le",
                container="wav",
            )

    def decode(self, source: Path, target: Path, info: ProbeInfo, limits: AudioLimits) -> None:
        self.processing.set()
        try:
            run_bounded(
                [sys.executable, "-c", f"import time; time.sleep({self.delay!r})"],
                timeout=limits.process_timeout_seconds,
                max_bytes=1,
                cancel=self.cancel,
            )
            if self.broken:
                raise AudioError("AUDIO_PROCESS_FAILED")
            if limits.output_rate != info.sample_rate:
                raise AudioError("MOCK_RESAMPLE_UNSUPPORTED")
            with wave.open(str(source), "rb") as reader:
                target.write_bytes(reader.readframes(reader.getnframes()))
        finally:
            self.processing.clear()


class MockPlatform:
    """Explicit MOCK scoped asset access and receipt coordinator reference.

    Artifacts are staging only until a COMPLETE eligible result. Rejections never
    promote artifacts. This is not durable platform storage/authentication.
    """

    profile = "MOCK"

    def __init__(self, limits: AudioLimits, *, fixture: str = "hold-short.wav") -> None:
        manifest = SourceManifest.model_validate_json(
            (ROOT / "tests/fixtures/manifests/synthetic-audio.json").read_bytes()
        )
        self.payload = (ROOT / "tests/fixtures/audio" / fixture).read_bytes()
        asset = manifest.assets[0].model_copy(update={"fixture_path": None})
        self.now: Callable[[], int] = epoch_ms
        owner = uuid4()
        self.leased = JobLease(
            session_id=manifest.session_id,
            analysis_run_id=uuid4(),
            revision=manifest.revision,
            job_id=uuid4(),
            attempt_id=uuid4(),
            lease_id=uuid4(),
            owner_id=owner,
            stage="AUDIO",
            input_hash=manifest.source_hash,
            config_hash=limits.digest(),
            expires_ms=self.now() + 30000,
            deadline_ms=self.now() + 60000,
            budget_microunits=0,
            asset_ids=[asset.id],
        )
        self.binding = AudioInput(
            context=RequestContext(
                actor_id=owner,
                capabilities=["worker", "audio"],
                session_id=manifest.session_id,
                analysis_run_id=self.leased.analysis_run_id,
                input_revision=manifest.revision,
                input_hash=manifest.source_hash,
                as_of_ms=0,
                mode="DEBRIEF",
                request_id=uuid4(),
            ),
            job_id=self.leased.job_id,
            attempt_id=self.leased.attempt_id,
            lease_id=self.leased.lease_id,
            config_hash=limits.digest(),
            source_id=manifest.id,
            asset=asset,
            size_bytes=len(self.payload),
            clock=manifest.clock,
            local_allowed=True,
        )
        self.delivered = False
        self.cancelled_flag = False
        self.heartbeats = 0
        self.processing_heartbeats = 0
        self.processing = threading.Event()
        self.hook: Callable[[str], None] = lambda point: None
        self.staged: dict[UUID, tuple[ArtifactSubmission, bytes]] = {}
        self.results: list[JobResult] = []
        self.receipts: dict[UUID, CommitReceipt] = {}
        self.candidates: dict[UUID, JobResult] = {}
        self.accepted: list[JobResult] = []
        self.downloads: list[tuple[UUID, int, int]] = []
        self.lose_result_response = False

    def check(self, lease: JobLease) -> None:
        if self.cancelled_flag:
            raise ContractError("JOB_CANCELLED")
        if self.now() >= min(self.leased.expires_ms, self.leased.deadline_ms):
            raise ContractError("LEASE_EXPIRED")
        if lease.model_dump(exclude={"expires_ms"}) != self.leased.model_dump(
            exclude={"expires_ms"}
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")

    def lease(self, worker_id: UUID, stage: str) -> JobLease | None:
        if worker_id != self.leased.owner_id or stage != "AUDIO":
            raise ContractError("ACCESS_DENIED")
        if self.delivered:
            return None
        self.delivered = True
        return self.leased

    def resolve(self, lease: JobLease) -> AudioInput:
        self.check(lease)
        return self.binding

    def heartbeat(self, lease: JobLease) -> JobLease:
        self.hook("heartbeat")
        self.check(lease)
        self.heartbeats += 1
        if self.processing.is_set():
            self.processing_heartbeats += 1
        self.leased = self.leased.model_copy(
            update={
                "expires_ms": min(
                    self.leased.deadline_ms, max(self.leased.expires_ms, self.now() + 30000)
                )
            }
        )
        return self.leased

    def cancelled(self, lease: JobLease) -> bool:
        self.hook("cancelled")
        return self.cancelled_flag

    def check_context(self, context: RequestContext) -> None:
        if context != self.binding.context:
            raise ContractError("ACCESS_DENIED")
        self.check(self.leased)

    def download(self, context: RequestContext, asset_id: UUID, start: int, end: int) -> bytes:
        self.hook("download")
        self.check_context(context)
        if asset_id != self.binding.asset.id or not 0 <= start < end <= len(self.payload):
            raise ContractError("ACCESS_DENIED")
        self.downloads.append((asset_id, start, end))
        return self.payload[start:end]

    def submit(
        self,
        context: RequestContext,
        artifact: ArtifactSubmission,
        chunks: Iterator[bytes],
    ) -> UUID:
        self.hook("submit")
        self.check_context(context)
        data = bytearray()
        for chunk in chunks:
            if len(data) + len(chunk) > artifact.size_bytes:
                raise ContractError("INVALID_INPUT")
            data.extend(chunk)
        self.check_context(context)
        if (
            len(data) != artifact.size_bytes
            or hashlib.sha256(data).hexdigest() != artifact.sha256
            or (artifact.session_id, artifact.analysis_run_id, artifact.revision)
            != (context.session_id, context.analysis_run_id, context.input_revision)
            or artifact.source_asset_id != self.binding.asset.id
        ):
            raise ContractError("INVALID_INPUT")
        if artifact.id in self.staged and self.staged[artifact.id] != (artifact, bytes(data)):
            raise ContractError("IDEMPOTENCY_CONFLICT")
        self.staged[artifact.id] = (artifact, bytes(data))
        self.hook("submitted")
        return artifact.id

    def result(self, result: JobResult) -> CommitReceipt:
        self.hook("result")
        result = JobResult.model_validate_json(result.model_dump_json())
        self.results.append(result)
        existing = self.receipts.get(result.attempt_id)
        if existing:
            if result != self.candidates[result.attempt_id]:
                raise ContractError("IDEMPOTENCY_CONFLICT")
            return existing
        self.check(self.leased)
        if (
            result.session_id,
            result.analysis_run_id,
            result.revision,
            result.job_id,
            result.attempt_id,
            result.lease_id,
            result.input_hash,
            result.config_hash,
        ) != (
            self.leased.session_id,
            self.leased.analysis_run_id,
            self.leased.revision,
            self.leased.job_id,
            self.leased.attempt_id,
            self.leased.lease_id,
            self.leased.input_hash,
            self.leased.config_hash,
        ):
            raise ContractError("SOURCE_REVISION_CHANGED")
        expected_hash = hashlib.sha256(result.model_dump_json(exclude={"output_hash"}).encode())
        if result.output_hash != expected_hash.hexdigest():
            raise ContractError("INVALID_INPUT")
        if any(
            item.id not in self.staged or self.staged[item.id][0] != item
            for item in result.artifacts
        ):
            raise ContractError("EVIDENCE_UNAVAILABLE")
        receipt = CommitReceipt(
            id=uuid4(),
            session_id=result.session_id,
            analysis_run_id=result.analysis_run_id,
            revision=result.revision,
            job_id=result.job_id,
            attempt_id=result.attempt_id,
            output_hash=result.output_hash,
            sequence=1,
        )
        self.receipts[result.attempt_id] = receipt
        self.candidates[result.attempt_id] = result
        if result.status == "COMPLETE":
            self.accepted.append(result)
        else:
            self.staged.clear()
        if self.lose_result_response:
            self.lose_result_response = False
            raise OSError("MOCK response lost after commit")
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="MOCK isolated audio worker acceptance")
    parser.add_argument("--real", action="store_true", help="Use actual local FFmpeg/ffprobe")
    parser.add_argument(
        "--scenario",
        choices=("success", "cancel", "deadline", "shutdown", "heartbeat-failure", "timeout"),
        default="success",
    )
    args = parser.parse_args()
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    with TemporaryDirectory(prefix="flowlens-worker-harness-") as name:
        limits = AudioLimits(chunk_ms=3000, overlap_ms=500)
        platform = MockPlatform(limits)
        tools = (
            AudioTools.discover()
            if args.real
            else MockTools(
                Path("MOCK"),
                Path("MOCK"),
                "MOCK",
                "MOCK",
                processing=platform.processing,
            )
        )
        worker = AudioWorker(
            WorkerConfig(
                worker_id=platform.leased.owner_id,
                scratch_root=Path(name),
                heartbeat_seconds=0.05,
                audio=limits,
            ),
            platform,
            platform,
            platform,
            tools,
            shutdown=stop,
            now=lambda: platform.now(),
        )
        timer = None
        if args.scenario != "success":
            if args.real:
                print("WORKER_HARNESS_INVALID_CONFIG")
                return 2
            if args.scenario == "timeout":
                audio = limits.model_copy(update={"process_timeout_seconds": 0.05})
                worker.config = worker.config.model_copy(update={"audio": audio})
                platform.leased = platform.leased.model_copy(update={"config_hash": audio.digest()})
                platform.binding = platform.binding.model_copy(
                    update={"config_hash": audio.digest()}
                )
            else:

                def hook(point: str) -> None:
                    if not platform.processing.is_set():
                        return
                    if args.scenario == "cancel":
                        platform.cancelled_flag = True
                    elif args.scenario == "deadline":
                        platform.now = lambda: platform.leased.deadline_ms
                    elif args.scenario == "heartbeat-failure" and point == "heartbeat":
                        raise OSError("MOCK control failure")

                platform.hook = hook
                if args.scenario == "shutdown":
                    # Exercise the executable's signal handler in this process.
                    timer = threading.Timer(0.1, lambda: signal.raise_signal(signal.SIGTERM))
                    timer.start()
        outcome = worker.run_once()
        if timer is not None:
            timer.join()
        clean = not list(Path(name).iterdir())
        print(
            json.dumps(
                {
                    "profile": "MOCK",
                    "pid": os.getpid(),
                    "parent_pid": os.getppid(),
                    "status": outcome.status,
                    "code": outcome.code,
                    "accepted": len(platform.accepted),
                    "heartbeats": platform.heartbeats,
                    "processing_heartbeats": platform.processing_heartbeats,
                    "provider_calls": 0,
                    "pipeline_ready": False,
                    "cleaned": clean,
                    "audio_execution": "REAL_FFMPEG"
                    if args.real
                    else "MOCK_PCM_REAL_PYTHON_PROCESS",
                    "runtime_forbidden_imports": [
                        name
                        for name in sys.modules
                        if name == "sqlite3" or name.startswith(("flowlens.storage", "evaluation"))
                    ],
                }
            )
        )
        expected = (
            "RECEIPT"
            if args.scenario == "success"
            else ("FAILED" if args.scenario == "timeout" else "ABORTED")
        )
        return 0 if outcome.status == expected and clean else 1


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception:
        print("WORKER_HARNESS_FAILED")
        exit_code = 1
    raise SystemExit(exit_code)
