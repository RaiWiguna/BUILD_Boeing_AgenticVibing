"""Private audio registration and bounded worker-attempt lifecycle for BE-05."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import os
import re
import uuid
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, StrictInt, StrictStr, ValidationError, model_validator

from .assist_storage import AssistStorage
from .models import Contract
from .ports import WorkerPort
from .replay_contracts import (
    ReplayPermissionProfile,
    ReplaySourceManifest,
    ReplaySourceProvenance,
    ReplayTimebase,
)

MAX_AUDIO_BYTES = 64 * 1024 * 1024
_ASSET_ID_PATTERN = re.compile(r"^aud_[0-9a-f]{32}$")


class AssistValidationError(ValueError):
    """An uploaded audio asset or its source metadata violates the BE-05 profile."""


class AssistConflict(ValueError):
    """A job lifecycle transition is not valid for the current job state."""


class AssistAssetUnavailable(RuntimeError):
    """A committed private asset is missing or no longer matches its hash."""


class AudioAssetInput(Contract):
    """Client-owned SC-04 fields; identity, duration, hash, and path are server-owned."""

    source_kind: Literal["synthetic", "authorized_simulator_replay"]
    source_ref: StrictStr = Field(min_length=1, max_length=200)
    channel_id: StrictStr = Field(min_length=1, max_length=200)
    audio_start: StrictInt | None
    timebase: ReplayTimebase
    provenance: ReplaySourceProvenance
    permission_profile: ReplayPermissionProfile
    retention_until: datetime | None

    @model_validator(mode="after")
    def audio_start_matches_alignment(self) -> AudioAssetInput:
        if self.timebase.alignment_status == "aligned" and self.audio_start is None:
            raise ValueError("aligned audio requires audio_start in session milliseconds")
        if self.timebase.alignment_status == "unknown" and self.audio_start is not None:
            raise ValueError("unknown audio alignment cannot claim audio_start")
        if self.audio_start is not None and self.audio_start < 0:
            raise ValueError("audio_start must be nonnegative")
        if self.retention_until is not None and (
            self.retention_until.tzinfo is None or self.retention_until.utcoffset() is None
        ):
            raise ValueError("retention_until must include a timezone")
        return self


@dataclass(frozen=True)
class AssistJobConfig:
    """Explicit server-side worker identity and wall-clock deadline."""

    provider: str
    model: str
    version: str
    config_version: str
    timeout_s: float
    language: str | None = None

    def __post_init__(self) -> None:
        if not all((self.provider.strip(), self.model.strip(), self.version.strip(), self.config_version.strip())):
            raise ValueError("provider, model, and version fields must be nonempty")
        if not math.isfinite(self.timeout_s) or self.timeout_s <= 0:
            raise ValueError("timeout_s must be a finite positive wall-clock duration")


@dataclass(frozen=True)
class PrivateWorkerRequest:
    """Read-only worker input; it carries no archive, DB, actor, or simulator capability."""

    job_id: str
    attempt_id: str
    asset_id: str
    local_asset_ref: str
    asset_hash: str
    provider: str
    model_version: str
    config_version: str
    language: str | None
    audio_start: int | None
    timebase: dict[str, Any]
    duration_ms: int
    public_evidence: tuple[dict[str, Any], ...] = ()


def _utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _validate_wav(data: bytes, filename: str, content_type: str) -> tuple[int, str]:
    if not filename.lower().endswith(".wav"):
        raise AssistValidationError("Only WAV audio is supported by the synthetic BE-05 profile")
    if content_type.split(";", 1)[0].strip().lower() not in {
        "audio/wav",
        "audio/x-wav",
        "application/octet-stream",
    }:
        raise AssistValidationError("Audio content type must identify a WAV file")
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise AssistValidationError("WAV payload is empty or exceeds the private upload limit")
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            if wav.getcomptype() != "NONE":
                raise AssistValidationError("Only uncompressed PCM WAV audio is supported")
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            frames = wav.getnframes()
            if channels not in {1, 2} or sample_width not in {1, 2, 3, 4} or sample_rate <= 0 or frames <= 0:
                raise AssistValidationError("WAV channel, sample width, sample rate, or duration is invalid")
            duration_ms = (frames * 1000 + sample_rate - 1) // sample_rate
    except (wave.Error, EOFError, OSError) as error:
        raise AssistValidationError("Audio file is not a valid PCM WAV payload") from error
    if duration_ms <= 0:
        raise AssistValidationError("WAV duration must be positive")
    return duration_ms, hashlib.sha256(data).hexdigest()


class AssistService:
    """Own private audio files and job state while reusing the server Archive writer."""

    def __init__(
        self,
        archive_db: Any,
        audio_root: str | Path,
        *,
        worker: WorkerPort[Any, Any] | None,
        job_config: AssistJobConfig | None,
        wall_clock,
        monotonic_clock,
    ) -> None:
        private_root = Path(audio_root).resolve()
        frontend_root = (Path(__file__).resolve().parents[1] / "frontend").resolve()
        if private_root == frontend_root or private_root.is_relative_to(frontend_root):
            raise ValueError("private audio storage must be outside the frontend/static tree")
        private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(private_root, 0o700)
        except OSError:
            # Windows ACLs govern privacy there; the path still remains outside static content.
            pass
        self._root = private_root
        self._storage = AssistStorage(archive_db)
        self._worker = worker
        self._config = job_config
        self._wall_clock = wall_clock
        self._monotonic_clock = monotonic_clock
        self._deadlines: dict[str, float] = {}
        self._attempt_jobs: dict[str, tuple[str, str]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def _private_path(self, asset_id: str) -> Path:
        if not _ASSET_ID_PATTERN.fullmatch(asset_id):
            raise AssistAssetUnavailable("Private audio asset is unavailable")
        path = (self._root / f"{asset_id}.wav").resolve()
        if path.parent != self._root:
            raise AssistAssetUnavailable("Private audio asset is unavailable")
        return path

    @staticmethod
    def _validate_source_metadata(
        metadata: AudioAssetInput,
        manifest: ReplaySourceManifest,
        duration_ms: int,
    ) -> None:
        if metadata.source_kind != manifest.source_kind:
            raise AssistValidationError("Audio source kind does not match the replay source")
        # source_ref is a source identity, never a client-selected path or locator.
        if metadata.source_ref != manifest.source_id:
            raise AssistValidationError("Audio source_ref must identify the bound replay source")
        if metadata.provenance != manifest.provenance:
            raise AssistValidationError("Audio provenance must match the imported replay source")
        if metadata.permission_profile != manifest.permission_profile:
            raise AssistValidationError("Audio usage/permission profile must match the replay source")
        if metadata.retention_until != manifest.retention_until:
            raise AssistValidationError("Audio retention must match the replay source")
        if metadata.timebase != manifest.timebase:
            raise AssistValidationError("Audio timebase must match the supported replay timebase")
        channels = manifest.coverage.channel_ids
        if channels is not None and metadata.channel_id not in channels:
            raise AssistValidationError("Audio channel is outside the replay source coverage")
        if metadata.audio_start is not None and manifest.coverage.intervals is not None:
            start = metadata.audio_start
            end = start + duration_ms
            intervals = manifest.coverage.intervals
            missing = manifest.coverage.missing_intervals or []
            contained = any(start >= item.start_ms and end <= item.end_ms for item in intervals)
            overlaps_missing = any(start < item.end_ms and end > item.start_ms for item in missing)
            if not contained or overlaps_missing:
                raise AssistValidationError("Audio time range is outside known replay coverage")

    def register_asset(
        self,
        *,
        source_session_id: str,
        source_manifest: ReplaySourceManifest,
        metadata_json: str,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> dict[str, Any]:
        try:
            metadata = AudioAssetInput.model_validate_json(metadata_json)
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            raise AssistValidationError("Audio asset metadata must be a valid SC-04 JSON object") from error
        duration_ms, content_hash = _validate_wav(audio_bytes, filename, content_type)
        self._validate_source_metadata(metadata, source_manifest, duration_ms)

        now = _utc(self._wall_clock())
        asset_id = f"aud_{uuid.uuid4().hex}"
        job_id = f"job_{uuid.uuid4().hex}"
        attempt_id = f"att_{uuid.uuid4().hex}"
        asset: dict[str, Any] = {
            "id": asset_id,
            "session_id": source_session_id,
            "source_kind": metadata.source_kind,
            "source_ref": source_manifest.source_id,
            "channel_id": metadata.channel_id,
            "audio_start": metadata.audio_start,
            "timebase": metadata.timebase.model_dump(mode="json"),
            "duration_ms": duration_ms,
            "hash": content_hash,
            "provenance": metadata.provenance.model_dump(mode="json"),
            "permission_profile": metadata.permission_profile.model_dump(mode="json"),
            "retention_until": metadata.retention_until.isoformat() if metadata.retention_until else None,
            "created_utc": now,
            "format": "wav-pcm",
        }
        config = self._config
        provider = config.provider if config else None
        model = config.model if config else None
        version = config.version if config else None
        config_version = config.config_version if config else None
        language = config.language if config else None
        job: dict[str, Any] = {
            "id": job_id,
            "source_session_id": source_session_id,
            "asset_id": asset_id,
            "attempt_id": attempt_id,
            "status": "queued",
            "provider": provider,
            "model": model,
            "version": version,
            "config_version": config_version,
            "language": language,
            "started_utc": None,
            "finished_utc": None,
            "error": None,
            "created_utc": now,
        }
        attempt = {
            "attempt_id": attempt_id,
            "status": "queued",
            "started_utc": None,
            "finished_utc": None,
            "error": None,
            "created_utc": now,
        }

        temp_path = self._root / f".{asset_id}.part"
        final_path = self._private_path(asset_id)
        try:
            with temp_path.open("xb") as staged:
                staged.write(audio_bytes)
                staged.flush()
                os.fsync(staged.fileno())
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            os.replace(temp_path, final_path)
            self._storage.commit_asset_job(asset=asset, job=job, attempt=attempt)
        except Exception:
            temp_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise

        if self._config is None:
            self._storage.finish_attempt(
                job_id,
                attempt_id,
                status="failed",
                finished_utc=_utc(self._wall_clock()),
                error={"code": "job_configuration_unavailable", "message": "No worker job configuration is installed."},
            )
        elif self._worker is None:
            self._storage.finish_attempt(
                job_id,
                attempt_id,
                status="failed",
                finished_utc=_utc(self._wall_clock()),
                error={"code": "worker_unavailable", "message": "No replay worker is configured."},
            )
        else:
            self._schedule(source_session_id, job_id, attempt_id)

        committed_job = self._storage.get_job(source_session_id, job_id)
        if committed_job is None:
            raise RuntimeError("committed audio job could not be read")
        return {"asset": asset, "job": committed_job}

    def _schedule(self, source_session_id: str, job_id: str, attempt_id: str) -> None:
        self._attempt_jobs[attempt_id] = (source_session_id, job_id)
        self._tasks[attempt_id] = asyncio.create_task(
            self._execute(source_session_id, job_id, attempt_id)
        )

    def _now_utc(self) -> str:
        return _utc(self._wall_clock())

    async def _wait_for_deadline(self, attempt_id: str) -> None:
        while True:
            deadline = self._deadlines.get(attempt_id)
            if deadline is None:
                return
            remaining = deadline - self._monotonic_clock()
            if remaining <= 0:
                return
            await asyncio.sleep(min(0.05, remaining))

    async def _execute(self, source_session_id: str, job_id: str, attempt_id: str) -> None:
        worker_task: asyncio.Task[Any] | None = None
        timer_task: asyncio.Task[None] | None = None
        try:
            job = self._storage.get_job(source_session_id, job_id)
            asset = self._storage.get_asset(source_session_id, job["asset_id"]) if job else None
            config = self._config
            worker = self._worker
            if job is None or asset is None or config is None or worker is None:
                self._finish(job_id, attempt_id, "failed", "worker_unavailable", "No replay worker is configured.")
                return
            path = self._private_path(asset["id"])
            if path.is_symlink() or not path.is_file():
                self._finish(job_id, attempt_id, "failed", "asset_unavailable", "Private audio asset is unavailable.")
                return
            file_hash = await asyncio.to_thread(self._hash_file, path)
            if file_hash != asset["hash"]:
                self._finish(job_id, attempt_id, "failed", "asset_integrity_failed", "Private audio hash verification failed.")
                return

            started_utc = self._now_utc()
            if not self._storage.mark_running(
                job_id,
                attempt_id,
                provider=config.provider,
                model=config.model,
                version=config.version,
                config_version=config.config_version,
                started_utc=started_utc,
            ):
                return
            self._deadlines[attempt_id] = self._monotonic_clock() + config.timeout_s
            request = PrivateWorkerRequest(
                job_id=job_id,
                attempt_id=attempt_id,
                asset_id=asset["id"],
                local_asset_ref=str(path),
                asset_hash=asset["hash"],
                provider=config.provider,
                model_version=config.version,
                config_version=config.config_version,
                language=config.language,
                audio_start=asset["audio_start"],
                timebase=asset["timebase"],
                duration_ms=asset["duration_ms"],
            )
            worker_task = asyncio.create_task(asyncio.to_thread(worker.process, request))
            timer_task = asyncio.create_task(self._wait_for_deadline(attempt_id))
            done, _ = await asyncio.wait((worker_task, timer_task), return_when=asyncio.FIRST_COMPLETED)
            if timer_task in done and worker_task not in done:
                self._finish(job_id, attempt_id, "failed", "timeout", "Worker attempt exceeded its configured wall-clock deadline.")
                return
            result = worker_task.result()
            status = self._accept_result(result, request)
            if status == "failed":
                self._finish(job_id, attempt_id, status, "worker_failed", "Worker could not process this asset.")
            elif status is None:
                self._finish(job_id, attempt_id, "failed", "worker_result_invalid", "Worker result did not match the active attempt.")
            else:
                self._finish(job_id, attempt_id, status, None, None)
        except asyncio.CancelledError:
            # Cancelling the coroutine cannot stop an already-running worker thread;
            # its result is detached and cannot reach storage.
            raise
        except Exception:  # noqa: BLE001 - worker boundary must fail closed for arbitrary provider errors.
            self._finish(job_id, attempt_id, "failed", "worker_failed", "Worker could not process this asset.")
        finally:
            for task in (worker_task, timer_task):
                if task is not None and not task.done():
                    task.cancel()
            self._deadlines.pop(attempt_id, None)
            self._attempt_jobs.pop(attempt_id, None)
            self._tasks.pop(attempt_id, None)

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _accept_result(
        result: Any, request: PrivateWorkerRequest
    ) -> Literal["completed", "needs-review", "failed"] | None:
        try:
            matches = (
                result.job_id == request.job_id
                and result.attempt_id == request.attempt_id
                and result.asset_id == request.asset_id
                and result.model_version == request.model_version
                and result.config_version == request.config_version
            )
            status = result.status
        except Exception:  # noqa: BLE001 - malformed objects from an external worker are rejected safely.
            return None
        if not matches or status not in {"completed", "needs-review", "failed"}:
            return None
        return status

    def _finish(
        self,
        job_id: str,
        attempt_id: str,
        status: Literal["needs-review", "completed", "failed", "cancelled"],
        error_code: str | None,
        error_message: str | None,
    ) -> bool:
        error = {"code": error_code, "message": error_message} if error_code and error_message else None
        committed = self._storage.finish_attempt(
            job_id,
            attempt_id,
            status=status,
            finished_utc=self._now_utc(),
            error=error,
        )
        if committed:
            self._deadlines.pop(attempt_id, None)
        return committed

    def expire_due(self) -> None:
        now = self._monotonic_clock()
        for attempt_id, deadline in list(self._deadlines.items()):
            if now < deadline:
                continue
            identity = self._attempt_jobs.get(attempt_id)
            if identity is None:
                continue
            _, job_id = identity
            if self._finish(
                job_id,
                attempt_id,
                "failed",
                "timeout",
                "Worker attempt exceeded its configured wall-clock deadline.",
            ):
                task = self._tasks.get(attempt_id)
                if task is not None:
                    task.cancel()

    def get_job(self, source_session_id: str, job_id: str) -> dict[str, Any] | None:
        self.expire_due()
        return self._storage.get_job(source_session_id, job_id)

    def cancel_job(self, source_session_id: str, job_id: str) -> dict[str, Any] | None:
        self.expire_due()
        job = self._storage.get_job(source_session_id, job_id)
        if job is None:
            return None
        if job["status"] == "cancelled":
            return job
        if job["status"] not in {"queued", "running"}:
            raise AssistConflict("Only queued or running jobs can be cancelled")
        if not self._finish(job_id, job["attempt_id"], "cancelled", None, None):
            current = self._storage.get_job(source_session_id, job_id)
            if current is None or current["status"] != "cancelled":
                raise AssistConflict("Job attempt is no longer active")
            return current
        task = self._tasks.get(job["attempt_id"])
        if task is not None:
            task.cancel()
        return self._storage.get_job(source_session_id, job_id)

    def retry_job(self, source_session_id: str, job_id: str) -> dict[str, Any] | None:
        self.expire_due()
        now = self._now_utc()
        attempt_id = f"att_{uuid.uuid4().hex}"
        config = self._config
        try:
            job = self._storage.retry_job(
                source_session_id,
                job_id,
                attempt={"attempt_id": attempt_id, "created_utc": now},
                provider=config.provider if config else None,
                model=config.model if config else None,
                version=config.version if config else None,
                config_version=config.config_version if config else None,
                language=config.language if config else None,
            )
        except ValueError as error:
            raise AssistConflict(str(error)) from error
        if job is None:
            return None
        if config is None:
            self._finish(job_id, attempt_id, "failed", "job_configuration_unavailable", "No worker job configuration is installed.")
        elif self._worker is None:
            self._finish(job_id, attempt_id, "failed", "worker_unavailable", "No replay worker is configured.")
        else:
            self._schedule(source_session_id, job_id, attempt_id)
        return self._storage.get_job(source_session_id, job_id)

    def content_asset(self, source_session_id: str, asset_id: str) -> dict[str, Any] | None:
        asset = self._storage.get_asset(source_session_id, asset_id)
        if asset is None:
            return None
        return asset

    def verified_content_path(self, asset_id: str, expected_hash: str) -> Path:
        path = self._private_path(asset_id)
        if path.is_symlink() or not path.is_file() or self._hash_file(path) != expected_hash:
            raise AssistAssetUnavailable("Private audio integrity check failed")
        return path

    async def close(self) -> None:
        """Fail active attempts safely before the owning Archive connection closes."""
        tasks = list(self._tasks.items())
        for attempt_id, task in tasks:
            identity = self._attempt_jobs.get(attempt_id)
            if identity is not None:
                _, job_id = identity
                self._finish(
                    job_id,
                    attempt_id,
                    "failed",
                    "server_shutdown",
                    "Worker attempt stopped because the local server is shutting down.",
                )
            task.cancel()
        if tasks:
            await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)
        self._tasks.clear()
        self._deadlines.clear()
        self._attempt_jobs.clear()


__all__ = [
    "MAX_AUDIO_BYTES",
    "AssistAssetUnavailable",
    "AssistConflict",
    "AssistJobConfig",
    "AssistService",
    "AssistValidationError",
    "AudioAssetInput",
    "PrivateWorkerRequest",
]
