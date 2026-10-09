"""B02.2 MOCK ports / actual subprocess / real FFmpeg acceptance kept distinct."""

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from flowlens.audio import AudioError, AudioLimits, AudioTools
from flowlens.audio.process import run_bounded
from flowlens.contracts.models import CommitReceipt, JobResult
from flowlens.core.errors import ContractError
from flowlens.testing.audio_worker import MockPlatform, MockTools
from flowlens.workers.audio import AudioWorker, WorkerConfig
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def setup_worker(tmp_path):
    scratch = tmp_path / "worker-scratch"
    scratch.mkdir()
    limits = AudioLimits(chunk_ms=3000, overlap_ms=500)
    platform = MockPlatform(limits)
    config = WorkerConfig(
        worker_id=platform.leased.owner_id,
        scratch_root=scratch,
        heartbeat_seconds=0.05,
        block_bytes=1024,
        audio=limits,
    )
    tools = MockTools(Path("MOCK"), Path("MOCK"), "MOCK", "MOCK", processing=platform.processing)
    worker = AudioWorker(config, platform, platform, platform, tools)
    yield worker, platform
    assert not list(scratch.iterdir())
    assert not any(t.name == "audio-heartbeat" for t in threading.enumerate())


def test_success_scoped_download_provenance_and_receipt(setup_worker):
    worker, platform = setup_worker
    outcome = worker.run_once()
    assert outcome.status == "RECEIPT"
    assert platform.processing_heartbeats >= 1
    assert len(platform.accepted) == 1
    candidate = JobResult.model_validate_json(platform.accepted[0].model_dump_json())
    assert candidate.outputs == [] and candidate.evidence == []
    assert candidate.status == "COMPLETE" and candidate.failure_code is None
    assert candidate.usage.cost_microunits is None
    assert all(identifier == platform.binding.asset.id for identifier, _, _ in platform.downloads)
    assert all(end - start <= 1024 for _, start, end in platform.downloads)
    assert sum(end - start for _, start, end in platform.downloads) == len(platform.payload)
    report = platform.staged[candidate.artifacts[-1].id][1]
    metadata = json.loads(report)["preparation"]
    assert metadata["source_sha256"] == metadata["source_after_sha256"]
    assert metadata["source_sha256"] == platform.binding.asset.sha256
    assert metadata["probe"]["sample_rate"] == 16000
    assert metadata["clock"] == platform.binding.clock.model_dump(mode="json")
    assert len(metadata["chunks"]) == len(candidate.artifacts) - 1
    for artifact in candidate.artifacts:
        submitted, data = platform.staged[artifact.id]
        assert submitted == artifact
        assert len(data) == artifact.size_bytes
        assert hashlib.sha256(data).hexdigest() == artifact.sha256
        assert artifact.required_capability == "audio"
    assert worker.run_once().status == "IDLE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", uuid4()),
        ("analysis_run_id", uuid4()),
        ("input_revision", 2),
        ("input_hash", "b" * 64),
        ("actor_id", uuid4()),
        ("capabilities", ["worker", "audio", "truth"]),
    ],
)
def test_binding_context_negative(setup_worker, field, value):
    worker, platform = setup_worker
    platform.binding = platform.binding.model_copy(
        update={"context": platform.binding.context.model_copy(update={field: value})}
    )
    assert worker.run_once().code == "WORKER_BINDING_INVALID"
    assert not platform.downloads and not platform.results and not platform.accepted


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", uuid4()),
        ("attempt_id", uuid4()),
        ("lease_id", uuid4()),
        ("config_hash", "b" * 64),
    ],
)
def test_binding_identity_negative(setup_worker, field, value):
    worker, platform = setup_worker
    platform.binding = platform.binding.model_copy(update={field: value})
    assert worker.run_once().code == "WORKER_BINDING_INVALID"
    assert not platform.downloads and not platform.accepted


@pytest.mark.parametrize(
    "field,value",
    [
        ("stage", "STT"),
        ("owner_id", uuid4()),
        ("asset_ids", [uuid4()]),
        ("config_hash", "b" * 64),
        ("asset_ids", [uuid4(), uuid4()]),
    ],
)
def test_lease_negative(setup_worker, field, value):
    worker, platform = setup_worker
    platform.leased = platform.leased.model_copy(update={field: value})
    platform.lease = lambda *_: platform.leased
    # Resolve normally checks platform scope; these fields are server-bound here.
    assert worker.run_once().code == "WORKER_BINDING_INVALID"
    assert not platform.downloads and not platform.accepted


@pytest.mark.parametrize("point", ["before", "during", "submitted"])
@pytest.mark.parametrize("reason", ["cancel", "deadline", "expiry", "shutdown"])
def test_interrupt_before_during_and_after_processing(setup_worker, point, reason):
    worker, platform = setup_worker
    clock = [platform.now()]
    worker.now = lambda: clock[0]
    platform.now = lambda: clock[0]

    def interrupt():
        if reason == "cancel":
            platform.cancelled_flag = True
        elif reason == "deadline":
            clock[0] = platform.leased.deadline_ms
        elif reason == "expiry":
            clock[0] = platform.leased.expires_ms
        else:
            worker.shutdown.set()

    def hook(event):
        if point == "during" and platform.processing.is_set() or point == event:
            interrupt()

    platform.hook = hook
    if point == "before":
        interrupt()
    started = time.monotonic()
    outcome = worker.run_once()
    assert outcome.status == "ABORTED"
    assert time.monotonic() - started < 2
    assert not platform.accepted
    assert not platform.results
    if point == "before":
        assert not platform.downloads


@pytest.mark.parametrize(
    "change", ["exception", "lease_id", "owner_id", "deadline_ms", "expires_ms"]
)
def test_heartbeat_failure_or_lost_lease_interrupts_tool(setup_worker, change):
    worker, platform = setup_worker
    original = platform.heartbeat

    def heartbeat(lease):
        if not platform.processing.is_set():
            return original(lease)
        if change == "exception":
            raise OSError("SECRET private-path raw stderr")
        value = (
            lease.expires_ms - 1
            if change == "expires_ms"
            else lease.deadline_ms + 1
            if change == "deadline_ms"
            else uuid4()
        )
        return lease.model_copy(update={change: value})

    platform.heartbeat = heartbeat
    outcome = worker.run_once()
    assert outcome.code in {"WORKER_LOST_LEASE", "WORKER_CONTROL_UNAVAILABLE"}
    assert not platform.results and not platform.accepted
    assert "SECRET" not in repr(outcome)


@pytest.mark.parametrize("mode", ["checksum", "short", "long", "decode", "timeout"])
def test_failure_has_no_partial_success(setup_worker, mode):
    worker, platform = setup_worker
    original = platform.download
    if mode in {"checksum", "short", "long"}:

        def download(*args):
            data = original(*args)
            return (
                bytes([data[0] ^ 1]) + data[1:]
                if mode == "checksum"
                else data[:-1]
                if mode == "short"
                else data + b"x"
            )

        platform.download = download
    elif mode == "decode":
        worker.tools = replace(worker.tools, broken=True)
    else:
        worker.config = worker.config.model_copy(
            update={
                "audio": worker.config.audio.model_copy(update={"process_timeout_seconds": 0.05})
            }
        )
        platform.leased = platform.leased.model_copy(
            update={"config_hash": worker.config.audio.digest()}
        )
        platform.binding = platform.binding.model_copy(
            update={"config_hash": worker.config.audio.digest()}
        )
    outcome = worker.run_once()
    assert outcome.status == "FAILED" and outcome.receipt is not None
    assert not platform.accepted and not platform.staged
    assert platform.results[-1].status == "FAILED"
    assert platform.results[-1].failure_code == "INVALID_AI_OUTPUT"
    assert not platform.results[-1].artifacts and not platform.results[-1].outputs


def test_ambiguous_response_resends_identical_result_once(setup_worker):
    worker, platform = setup_worker
    platform.lose_result_response = True
    outcome = worker.run_once()
    assert outcome.status == "RECEIPT"
    assert len(platform.results) == 2 and platform.results[0] == platform.results[1]
    assert len(platform.accepted) == 1 and len(platform.receipts) == 1
    assert platform.result(platform.results[0]) == outcome.receipt
    with pytest.raises(ContractError, match="IDEMPOTENCY_CONFLICT"):
        platform.result(platform.results[0].model_copy(update={"output_hash": "b" * 64}))


@pytest.mark.parametrize("change", ["cancel", "late", "stale", "receipt", "client"])
def test_result_races_and_client_failure_do_not_claim_success(setup_worker, change):
    worker, platform = setup_worker
    original = platform.result

    def result(candidate):
        if change == "cancel":
            platform.cancelled_flag = True
        elif change == "late":
            platform.now = lambda: platform.leased.deadline_ms
        elif change == "stale":
            platform.leased = platform.leased.model_copy(update={"revision": 2})
        elif change == "client":
            raise OSError("SECRET audio payload")
        if change == "receipt":
            return CommitReceipt(
                id=uuid4(),
                session_id=uuid4(),
                analysis_run_id=candidate.analysis_run_id,
                revision=1,
                job_id=candidate.job_id,
                attempt_id=candidate.attempt_id,
                output_hash=candidate.output_hash,
                sequence=1,
            )
        return original(candidate)

    platform.result = result
    outcome = worker.run_once()
    assert outcome.status in {"ABORTED", "UNCONFIRMED"}
    assert not platform.accepted
    assert "SECRET" not in repr(outcome)


@pytest.mark.parametrize("failure", ["download", "submit", "consumer", "unconsumed"])
def test_port_failure_cleanup(setup_worker, failure):
    worker, platform = setup_worker

    def fail(*args):
        if failure == "consumer":
            next(args[-1])
        if failure == "unconsumed":
            return args[1].id
        raise RuntimeError("SECRET C:/private/audio.wav credentials stderr")

    if failure == "download":
        platform.download = fail
    else:
        platform.submit = fail
    outcome = worker.run_once()
    assert outcome.status != "RECEIPT" and not platform.accepted
    assert "SECRET" not in repr(outcome) and "private" not in repr(outcome)


def test_retry_restart_uses_new_attempt_and_private_scratch(setup_worker):
    worker, platform = setup_worker
    worker.tools = replace(worker.tools, broken=True)
    assert worker.run_once().status == "FAILED"
    old_attempt = platform.leased.attempt_id
    platform.delivered = False
    assert worker.run_once().code == "WORKER_ATTEMPT_REUSED"
    platform.delivered = False
    platform.leased = platform.leased.model_copy(
        update={"attempt_id": uuid4(), "lease_id": uuid4()}
    )
    platform.binding = platform.binding.model_copy(
        update={
            "attempt_id": platform.leased.attempt_id,
            "lease_id": platform.leased.lease_id,
        }
    )
    restarted = AudioWorker(
        worker.config, platform, platform, platform, replace(worker.tools, broken=False)
    )
    assert restarted.run_once().status == "RECEIPT"
    assert platform.accepted[0].attempt_id != old_attempt


@pytest.mark.parametrize(
    "field,value",
    [
        ("heartbeat_seconds", 0.01),
        ("heartbeat_seconds", float("inf")),
        ("block_bytes", 10**9),
        ("max_attempts", 10001),
        ("max_metadata_bytes", 10**9),
        ("extra_field", True),
    ],
)
def test_config_strict_bounded(setup_worker, field, value):
    worker, _ = setup_worker
    with pytest.raises(ValidationError):
        WorkerConfig.model_validate({**worker.config.model_dump(), field: value})


@pytest.mark.parametrize("limit", ["input", "chunks", "output", "metadata", "attempts"])
def test_resource_limits(setup_worker, limit):
    worker, platform = setup_worker
    changes = (
        {"max_input_bytes": 100}
        if limit == "input"
        else (
            {"max_chunks": 1}
            if limit == "chunks"
            else {"max_output_bytes": 1000}
            if limit == "output"
            else {}
        )
    )
    audio = worker.config.audio.model_copy(update=changes)
    worker.config = worker.config.model_copy(
        update={
            "audio": audio,
            "max_metadata_bytes": 1024 if limit == "metadata" else 2 * 1024**2,
            "max_attempts": 1 if limit == "attempts" else 100,
        }
    )
    platform.leased = platform.leased.model_copy(update={"config_hash": audio.digest()})
    platform.binding = platform.binding.model_copy(update={"config_hash": audio.digest()})
    outcome = worker.run_once()
    if limit == "attempts":
        assert outcome.status == "RECEIPT"
        assert worker.run_once().code == "WORKER_RESTART_REQUIRED"
    else:
        assert outcome.status in {"ABORTED", "FAILED"} and not platform.accepted


def test_subprocess_cancel_reaps_child(tmp_path):
    cancel = threading.Event()
    timer = threading.Timer(0.2, cancel.set)
    timer.start()
    started = time.monotonic()
    pidfile = tmp_path / "pid"
    try:
        with pytest.raises(AudioError, match="AUDIO_CANCELLED"):
            run_bounded(
                [
                    sys.executable,
                    "-c",
                    "import os,sys,time;"
                    "open(sys.argv[1],'w').write(str(os.getpid()));time.sleep(30)",
                    str(pidfile),
                ],
                timeout=10.0,
                max_bytes=1,
                cancel=cancel,
            )
        assert time.monotonic() - started < 2
        pid = int(pidfile.read_text())
        if os.name == "nt":
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                code = ctypes.c_ulong()
                ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
                ctypes.windll.kernel32.CloseHandle(handle)
                assert code.value != 259
        else:
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)
    finally:
        timer.join()
        pidfile.unlink(missing_ok=True)


@pytest.mark.parametrize("real", [False, True])
def test_standalone_worker_is_separate_process(real):
    if real and not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("REAL FFMPEG BLOCKER")
    with subprocess.Popen(
        [sys.executable, "-m", "flowlens.testing.audio_worker", *(["--real"] if real else [])],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        assert process.returncode == 0, stderr
        report = json.loads(stdout)
        # Windows venv redirector may remain as an intermediate launcher process.
        assert report["pid"] != os.getpid()
        assert process.pid in {report["pid"], report["parent_pid"]}
    assert report["profile"] == "MOCK" and report["accepted"] == 1
    assert report["provider_calls"] == 0 and report["pipeline_ready"] is False
    assert report["cleaned"] is True and report["status"] == "RECEIPT"
    assert report["runtime_forbidden_imports"] == []
    if not real:
        assert report["processing_heartbeats"] >= 1


def test_worker_runtime_boundary():
    for file in (ROOT / "backend/flowlens/workers").rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            modules = (
                [item.name for item in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            for module in modules:
                assert not module.startswith(("sqlite3", "evaluation", "flowlens.testing"))
                if module.startswith("flowlens."):
                    assert module.startswith(
                        ("flowlens.workers.audio", "flowlens.audio", "flowlens.contracts")
                    )


def test_real_worker_fixture_immutability(setup_worker):
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("REAL FFMPEG BLOCKER")
    worker, platform = setup_worker
    worker.tools = AudioTools.discover()
    raw_hash = hashlib.sha256(platform.payload).hexdigest()
    assert worker.run_once().status == "RECEIPT"
    assert hashlib.sha256(platform.payload).hexdigest() == raw_hash


@pytest.mark.parametrize(
    "scenario", ["cancel", "deadline", "shutdown", "heartbeat-failure", "timeout"]
)
def test_separate_process_failure_cleanup(scenario):
    result = subprocess.run(
        [sys.executable, "-m", "flowlens.testing.audio_worker", "--scenario", scenario],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["pid"] != os.getpid() and report["accepted"] == 0
    assert report["status"] == ("FAILED" if scenario == "timeout" else "ABORTED")
    assert report["cleaned"] is True and report["runtime_forbidden_imports"] == []
    assert report["provider_calls"] == 0


def test_backwards_clock_does_not_extend_lease(setup_worker):
    worker, platform = setup_worker
    clock = [platform.now()]
    platform.leased = platform.leased.model_copy(update={"expires_ms": clock[0] + 100})
    worker.now = lambda: clock[0]
    # Keep the MOCK server expiry fixed; simulate only the worker wall-clock rollback.
    original = platform.heartbeat

    def heartbeat(lease):
        if platform.processing.is_set():
            clock[0] -= 100000
            return lease  # no extension
        return lease

    platform.heartbeat = heartbeat
    assert worker.run_once().code == "WORKER_LEASE_EXPIRED"
    assert not platform.accepted
    platform.heartbeat = original


def test_real_ffmpeg_cancel_cleanup(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("REAL FFMPEG BLOCKER")
    cancel = threading.Event()
    timer = threading.Timer(0.2, cancel.set)
    timer.start()
    output = tmp_path / "partial.pcm"
    try:
        with pytest.raises(AudioError, match="AUDIO_CANCELLED"):
            run_bounded(
                [
                    shutil.which("ffmpeg"),
                    "-nostdin",
                    "-v",
                    "error",
                    "-re",
                    "-i",
                    str(ROOT / "tests/fixtures/audio/hold-short.wav"),
                    "-f",
                    "s16le",
                    "pipe:1",
                ],
                timeout=10.0,
                max_bytes=1000000,
                output=output,
                cancel=cancel,
            )
    finally:
        timer.join()
        output.unlink(missing_ok=True)


def test_retry_does_not_reuse_cancelled_staging(setup_worker):
    worker, platform = setup_worker
    platform.hook = lambda point: (
        setattr(platform, "cancelled_flag", True) if point == "submitted" else None
    )
    assert worker.run_once().status == "ABORTED"
    old_ids = set(platform.staged)
    assert old_ids and not platform.accepted
    platform.hook = lambda _: None
    platform.cancelled_flag = False
    platform.delivered = False
    platform.leased = platform.leased.model_copy(
        update={"attempt_id": uuid4(), "lease_id": uuid4()}
    )
    platform.binding = platform.binding.model_copy(
        update={
            "attempt_id": platform.leased.attempt_id,
            "lease_id": platform.leased.lease_id,
        }
    )
    restarted = AudioWorker(worker.config, platform, platform, platform, worker.tools)
    assert restarted.run_once().status == "RECEIPT"
    assert not old_ids.intersection(item.id for item in platform.accepted[0].artifacts)


def test_preparation_checksum_is_interruptible(tmp_path):
    from flowlens.audio.preparation import digest

    source = tmp_path / "private-input"
    source.write_bytes(b"x" * 200000)
    calls = [0]

    def checkpoint():
        calls[0] += 1
        if calls[0] == 2:
            raise RuntimeError("stop")

    try:
        with pytest.raises(RuntimeError, match="stop"):
            digest(source, checkpoint=checkpoint)
        with pytest.raises(AudioError, match="AUDIO_INPUT_LIMIT"):
            digest(source, max_bytes=100)
    finally:
        source.unlink()
