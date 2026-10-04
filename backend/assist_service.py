"""Private audio registration and bounded worker-attempt lifecycle for BE-05."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import io
import json
import math
import os
import re
import uuid
import wave
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    model_validator,
)

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


class AssistResultConflict(AssistConflict):
    """A result attempt is stale or its immutable ID was reused with other output."""


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


class AssistEvidenceRef(Contract):
    kind: Literal["session_event", "transcript_segment", "detector_alert"]
    id: StrictStr = Field(min_length=1, max_length=300)


class TranscriptSegment(Contract):
    id: StrictStr = Field(min_length=1, max_length=200)
    asset_id: StrictStr = Field(min_length=1, max_length=200)
    start_ms: StrictInt = Field(ge=0)
    end_ms: StrictInt = Field(ge=0)
    channel_id: StrictStr = Field(min_length=1, max_length=200)
    speaker_label: StrictStr | None
    speaker_source: StrictStr = Field(min_length=1, max_length=80)
    speaker_confidence: StrictFloat | None = Field(ge=0, le=1)
    text: StrictStr = Field(max_length=4000)
    language: StrictStr | None
    asr_confidence: StrictFloat | None = Field(ge=0, le=1)
    model_version: StrictStr = Field(min_length=1, max_length=100)
    correction_status: StrictStr = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def ordered_segment(self) -> TranscriptSegment:
        if self.end_ms <= self.start_ms:
            raise ValueError("transcript segment end_ms must be after start_ms")
        return self


class CandidateEntity(Contract):
    segment_id: StrictStr = Field(min_length=1, max_length=200)
    entity_type: Literal["callsign", "runway", "instruction", "number", "negation", "time", "actor", "channel"]
    candidate_value: StrictStr = Field(min_length=1, max_length=500)
    normalized_value: StrictStr | None = Field(default=None, max_length=500)
    confidence: StrictFloat | None = Field(default=None, ge=0, le=1)
    alternatives: list[StrictStr] = Field(default_factory=list, max_length=20)


class AssistHighlight(Contract):
    id: StrictStr = Field(min_length=1, max_length=200)
    category: StrictStr = Field(min_length=1, max_length=100)
    review_priority: StrictStr = Field(min_length=1, max_length=40)
    statement: StrictStr = Field(min_length=1, max_length=4000)
    transcript_segment_ids: list[StrictStr] = Field(default_factory=list, max_length=100)
    session_event_ids: list[StrictStr] = Field(default_factory=list, max_length=100)
    uncertainty: StrictStr = Field(min_length=1, max_length=1000)
    provider_version: StrictStr | None
    rule_version: StrictStr | None
    status: StrictStr = Field(min_length=1, max_length=80)
    linked_alert_id: StrictStr | None = None
    link_status: StrictStr | None = None


class AdvisoryOptionCandidate(Contract):
    id: StrictStr = Field(min_length=1, max_length=200)
    replay_analysis_id: StrictStr = Field(min_length=1, max_length=200)
    option_statement: StrictStr = Field(min_length=1, max_length=4000)
    rationale: StrictStr = Field(min_length=1, max_length=4000)
    supporting_evidence_ids: list[AssistEvidenceRef] = Field(min_length=1, max_length=100)
    preconditions: list[StrictStr] = Field(default_factory=list, max_length=100)
    unknowns: list[StrictStr] = Field(default_factory=list, max_length=100)
    source_version: StrictStr = Field(min_length=1, max_length=200)
    model_version: StrictStr = Field(min_length=1, max_length=100)
    rule_version: StrictStr | None
    review_status: StrictStr = Field(min_length=1, max_length=80)


class WorkerSafeError(Contract):
    code: StrictStr = Field(min_length=1, max_length=100)
    message: StrictStr = Field(min_length=1, max_length=500)


class WorkerResultDTO(Contract):
    """BE-local SC-04/05 result adapter until the AI-owned DTO package exists."""

    job_id: StrictStr = Field(min_length=1)
    attempt_id: StrictStr = Field(min_length=1)
    asset_id: StrictStr = Field(min_length=1)
    model_version: StrictStr = Field(min_length=1)
    config_version: StrictStr = Field(min_length=1)
    status: Literal["completed", "needs-review", "failed"]
    source_session_id: StrictStr | None = None
    source_content_hash: StrictStr | None = None
    asset_hash: StrictStr | None = None
    input_hash: StrictStr | None = None
    analysis_id: StrictStr | None = None
    segments: list[TranscriptSegment] = Field(default_factory=list, max_length=10000)
    entities: list[CandidateEntity] = Field(default_factory=list, max_length=20000)
    highlights: list[AssistHighlight] = Field(default_factory=list, max_length=10000)
    options: list[AdvisoryOptionCandidate] = Field(default_factory=list, max_length=1000)
    error: WorkerSafeError | None = None

    @model_validator(mode="after")
    def result_status_matches_payload(self) -> WorkerResultDTO:
        if self.status == "failed" and (self.segments or self.entities or self.highlights or self.options):
            raise ValueError("failed worker result cannot include assist output")
        if self.status != "failed" and self.error is not None:
            raise ValueError("only failed results may carry a safe worker error")
        return self


class TranscriptReadItem(Contract):
    segment: TranscriptSegment
    entities: list[CandidateEntity]
    time_alignment: Literal["aligned", "unknown"]
    alignment_uncertainty: StrictStr | None


class AssistJobView(Contract):
    id: StrictStr
    source_session_id: StrictStr
    asset_id: StrictStr
    attempt_id: StrictStr
    status: Literal["queued", "running", "needs-review", "completed", "failed", "cancelled"]
    provider: StrictStr | None
    model: StrictStr | None
    version: StrictStr | None
    config_version: StrictStr | None
    language: StrictStr | None
    started_utc: StrictStr | None
    finished_utc: StrictStr | None
    error: dict[str, StrictStr] | None
    chunk_progress: dict[str, Any] | None
    analysis_id: StrictStr | None


class ReviewAnnotationView(Contract):
    target_id: StrictStr
    decision: Literal["corrected", "confirmed", "dismissed", "unresolved"]
    reviewer: StrictStr
    timestamp: StrictStr
    correction: StrictStr | None = None
    reason: StrictStr | None = None


class AssistSnapshotPayload(Contract):
    jobs: list[AssistJobView]
    segments: list[TranscriptReadItem]
    highlights: list[AssistHighlight]
    options: list[AdvisoryOptionCandidate]
    review_annotations: list[ReviewAnnotationView]


class AssistJobProgressPayload(Contract):
    job: AssistJobView


class AssistErrorPayload(Contract):
    code: StrictStr
    message: StrictStr


class _AssistMessage(Contract):
    schema_version: Literal["assist-1"] = "assist-1"
    source_session_id: StrictStr
    sequence: StrictInt = Field(ge=0)
    type: StrictStr


class AssistSnapshotMessage(_AssistMessage):
    type: Literal["snapshot"]
    payload: AssistSnapshotPayload


class AssistJobProgressMessage(_AssistMessage):
    type: Literal["job_progress"]
    payload: AssistJobProgressPayload


class AssistSegmentMessage(_AssistMessage):
    type: Literal["segment"]
    payload: TranscriptReadItem


class AssistHighlightMessage(_AssistMessage):
    type: Literal["highlight"]
    payload: AssistHighlight


class AssistOptionMessage(_AssistMessage):
    type: Literal["option"]
    payload: AdvisoryOptionCandidate


class AssistAnnotationMessage(_AssistMessage):
    type: Literal["review_annotation"]
    payload: ReviewAnnotationView


class AssistStreamErrorMessage(_AssistMessage):
    type: Literal["error"]
    payload: AssistErrorPayload


AssistStreamMessage = (
    AssistSnapshotMessage | AssistJobProgressMessage | AssistSegmentMessage |
    AssistHighlightMessage | AssistOptionMessage | AssistAnnotationMessage | AssistStreamErrorMessage
)


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
    source_session_id: str
    source_id: str
    source_content_hash: str
    layout_version: str
    analysis_id: str
    input_hash: str
    window_start_ms: int
    window_end_ms: int
    time_alignment: Literal["aligned", "unknown"]
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

            binding = self._storage.get_source_binding(source_session_id)
            manifest_hash = binding["manifest"].get("content_hash") if binding is not None else None
            if (binding is None or asset["session_id"] != source_session_id
                    or not isinstance(manifest_hash, str)
                    or binding["content_hash"].casefold() != manifest_hash.casefold()):
                self._finish(job_id, attempt_id, "failed", "source_integrity_failed", "Replay source binding verification failed.")
                return
            window_start_ms, window_end_ms, time_alignment = self._analysis_window(asset, binding["manifest"])
            analysis_id = f"assist_{uuid.uuid4().hex}"
            input_hash = self._input_hash(
                source_session_id=source_session_id, source_content_hash=binding["content_hash"],
                asset=asset, job=job, layout_version=binding["manifest"]["layout"]["version"],
                source_manifest=binding["manifest"],
                window_start_ms=window_start_ms, window_end_ms=window_end_ms,
            )

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
                source_session_id=source_session_id,
                source_id=binding["source_id"],
                source_content_hash=binding["content_hash"],
                layout_version=binding["manifest"]["layout"]["version"],
                analysis_id=analysis_id,
                input_hash=input_hash,
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
                time_alignment=time_alignment,
            )
            worker_task = asyncio.create_task(asyncio.to_thread(worker.process, request))
            timer_task = asyncio.create_task(self._wait_for_deadline(attempt_id))
            done, _ = await asyncio.wait((worker_task, timer_task), return_when=asyncio.FIRST_COMPLETED)
            if timer_task in done and worker_task not in done:
                self._finish(job_id, attempt_id, "failed", "timeout", "Worker attempt exceeded its configured wall-clock deadline.")
                return
            result = worker_task.result()
            validated = self._validate_worker_result(result, request)
            if validated.status == "failed":
                self._finish(job_id, attempt_id, "failed", "worker_failed", "Worker could not process this asset.")
            else:
                self.commit_result(validated, request)
        except asyncio.CancelledError:
            # Cancelling the coroutine cannot stop an already-running worker thread;
            # its result is detached and cannot reach storage.
            raise
        except (AssistValidationError, AssistResultConflict):
            self._finish(
                job_id, attempt_id, "failed", "worker_result_invalid",
                "Worker result did not match the active attempt or evidence scope.",
            )
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
    def _analysis_window(
        asset: Mapping[str, Any], manifest: Mapping[str, Any]
    ) -> tuple[int, int, Literal["aligned", "unknown"]]:
        audio_start = asset["audio_start"]
        if audio_start is not None:
            return audio_start, audio_start + asset["duration_ms"], "aligned"
        intervals = manifest.get("coverage", {}).get("intervals") or []
        if intervals:
            return min(item["start_ms"] for item in intervals), max(item["end_ms"] for item in intervals), "unknown"
        # C-05 requires integer bounds; the unknown alignment is recorded in versions
        # and no segment from this analysis receives a historical availability time.
        return 0, 0, "unknown"

    @staticmethod
    def _input_hash(
        *, source_session_id: str, source_content_hash: str, asset: Mapping[str, Any],
        job: Mapping[str, Any], layout_version: str, source_manifest: Mapping[str, Any],
        window_start_ms: int, window_end_ms: int,
    ) -> str:
        manifest_json = json.dumps(
            source_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        )
        selected_inputs = {
            "source_session_id": source_session_id,
            "source_content_hash": source_content_hash,
            "source_manifest_hash": hashlib.sha256(manifest_json.encode("utf-8")).hexdigest(),
            "layout_version": layout_version,
            "asset_id": asset["id"],
            "asset_hash": asset["hash"],
            "source_kind": asset["source_kind"],
            "channel_id": asset["channel_id"],
            "asset_timebase": asset["timebase"],
            "audio_start": asset["audio_start"],
            "duration_ms": asset["duration_ms"],
            "provenance": asset["provenance"],
            "permission_profile": asset["permission_profile"],
            "retention_until": asset["retention_until"],
            "model_version": job["version"],
            "config_version": job["config_version"],
            "provider": job["provider"],
            "model": job["model"],
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
        }
        encoded = json.dumps(selected_inputs, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _as_mapping(result: Any) -> dict[str, Any]:
        if isinstance(result, Mapping):
            return dict(result)
        model_dump = getattr(result, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(mode="json")
            if isinstance(dumped, dict):
                return dumped
        try:
            value = vars(result)
        except TypeError as error:
            raise AssistValidationError("Worker result must be a typed JSON object") from error
        if not isinstance(value, dict):
            raise AssistValidationError("Worker result must be a typed JSON object")
        return dict(value)

    @classmethod
    def _validate_worker_result(cls, result: Any, request: PrivateWorkerRequest) -> WorkerResultDTO:
        payload = cls._as_mapping(result)
        base_fields = {"job_id", "attempt_id", "asset_id", "model_version", "config_version", "status"}
        # BE-05's status-only WorkerResult remains readable during migration. This
        # adapter supplies only server-known bindings and empty output collections;
        # it never fabricates transcript, highlight, or option content.
        if set(payload) == base_fields:
            payload.update({
                "source_session_id": request.source_session_id,
                "source_content_hash": request.source_content_hash,
                "asset_hash": request.asset_hash,
                "input_hash": request.input_hash,
                "analysis_id": request.analysis_id,
                "segments": [], "entities": [], "highlights": [], "options": [],
            })
        try:
            dto = WorkerResultDTO.model_validate(payload)
        except ValidationError as error:
            raise AssistValidationError("Worker result does not match the strict SC-04/05 profile") from error
        matches = (
            dto.job_id == request.job_id
            and dto.attempt_id == request.attempt_id
            and dto.asset_id == request.asset_id
            and dto.model_version == request.model_version
            and dto.config_version == request.config_version
        )
        if not matches:
            raise AssistValidationError("Worker result job, attempt, asset, or version does not match the active request")
        contains_output = bool(dto.segments or dto.entities or dto.highlights or dto.options)
        bindings = {
            "source_session_id": (dto.source_session_id, request.source_session_id),
            "source_content_hash": (dto.source_content_hash, request.source_content_hash),
            "asset_hash": (dto.asset_hash, request.asset_hash),
            "input_hash": (dto.input_hash, request.input_hash),
            "analysis_id": (dto.analysis_id, request.analysis_id),
        }
        for name, (actual, expected) in bindings.items():
            if actual is not None and actual != expected:
                raise AssistValidationError(f"Worker result {name} does not match the server-bound request")
            if contains_output and actual is None:
                raise AssistValidationError(f"Worker result output must identify its {name}")
        return dto

    def _resolve_ref(
        self, ref: AssistEvidenceRef, request: PrivateWorkerRequest,
        segment_times: Mapping[str, int | None],
    ) -> int:
        if ref.kind == "session_event":
            event_id = ref.id
            if ":" in event_id:
                prefix, event_id = event_id.split(":", 1)
                if prefix != request.source_id:
                    raise AssistValidationError("Evidence reference belongs to another replay source")
            available_ms = self._storage.source_event_available_ms(request.source_session_id, event_id)
        elif ref.kind == "transcript_segment":
            if ref.id in segment_times:
                available_ms = segment_times[ref.id]
            else:
                existing = self._storage.entity_segment(request.source_session_id, ref.id)
                available_ms = existing["available_ms"] if existing else None
        else:
            available_ms = self._storage.find_detector_alert_available_ms(
                request.source_session_id, ref.id, request.window_start_ms, request.window_end_ms
            )
        if available_ms is None:
            raise AssistValidationError("Evidence reference is dangling, foreign, or time-unresolved")
        if not request.window_start_ms <= available_ms <= request.window_end_ms:
            raise AssistValidationError("Evidence reference is outside the bound analysis window")
        return available_ms

    def commit_result(self, result: WorkerResultDTO, request: PrivateWorkerRequest) -> dict[str, Any]:
        """Validate a complete immutable result before committing any row."""
        asset = self._storage.get_asset(request.source_session_id, request.asset_id)
        binding = self._storage.get_source_binding(request.source_session_id)
        job = self._storage.get_job(request.source_session_id, request.job_id)
        if asset is None or binding is None or job is None:
            raise AssistResultConflict("Worker result source, asset, or job no longer exists")
        if (asset["hash"] != request.asset_hash or asset["session_id"] != request.source_session_id
                or binding["source_id"] != request.source_id
                or binding["content_hash"] != request.source_content_hash
                or job["asset_id"] != request.asset_id
                or job["version"] != request.model_version
                or job["config_version"] != request.config_version):
            raise AssistResultConflict("Worker result source, asset hash, job, or version binding changed")
        private_path = self._private_path(request.asset_id)
        if private_path.is_symlink() or not private_path.is_file() or self._hash_file(private_path) != request.asset_hash:
            raise AssistResultConflict("Worker result audio asset hash no longer matches the committed asset")

        content = result.model_dump(mode="json")
        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if result.status not in {"completed", "needs-review"}:
            raise AssistValidationError("Only successful typed worker results can be committed")
        if (result.job_id != request.job_id or result.attempt_id != request.attempt_id
                or result.asset_id != request.asset_id or result.model_version != request.model_version
                or result.config_version != request.config_version):
            raise AssistValidationError("Worker result identity does not match its server request")
        contains_output = bool(result.segments or result.entities or result.highlights or result.options)
        for actual, expected in (
            (result.source_session_id, request.source_session_id),
            (result.source_content_hash, request.source_content_hash),
            (result.asset_hash, request.asset_hash),
            (result.input_hash, request.input_hash),
            (result.analysis_id, request.analysis_id),
        ):
            if actual is not None and actual != expected:
                raise AssistValidationError("Worker result binding differs from the established input")
            if contains_output and actual is None:
                raise AssistValidationError("Worker result output is missing a fixed input binding")

        segment_ids = [segment.id for segment in result.segments]
        highlight_ids = [highlight.id for highlight in result.highlights]
        option_ids = [option.id for option in result.options]
        if (len(segment_ids) != len(set(segment_ids)) or len(highlight_ids) != len(set(highlight_ids))
                or len(option_ids) != len(set(option_ids))):
            raise AssistValidationError("Worker result contains duplicate entity IDs")
        segments = [segment.model_dump(mode="json") for segment in result.segments]
        entities = [entity.model_dump(mode="json") for entity in result.entities]
        highlights = [highlight.model_dump(mode="json") for highlight in result.highlights]
        options = [option.model_dump(mode="json") for option in result.options]
        segment_times: dict[str, int | None] = {}
        for segment in result.segments:
            if segment.asset_id != request.asset_id or segment.model_version != request.model_version:
                raise AssistValidationError("Transcript segment is not bound to the selected audio asset/version")
            if segment.end_ms > asset["duration_ms"]:
                raise AssistValidationError("Transcript segment exceeds the audio asset duration")
            if request.time_alignment == "aligned":
                audio_start = asset["audio_start"]
                if audio_start is None:
                    raise AssistValidationError("Aligned audio is missing its server-validated start time")
                segment_available_ms = audio_start + segment.end_ms
                start_ms = audio_start + segment.start_ms
                if start_ms < request.window_start_ms or segment_available_ms > request.window_end_ms:
                    raise AssistValidationError("Transcript segment is outside the selected analysis window")
                available_ms: int | None = segment_available_ms
            else:
                available_ms = None
            segment_times[segment.id] = available_ms
        for entity in result.entities:
            if entity.segment_id not in segment_times:
                raise AssistValidationError("Candidate entity references a segment outside this result batch")

        available_times: dict[str, int | None] = {
            f"transcript_segment:{key}": value for key, value in segment_times.items()
        }
        for highlight in result.highlights:
            times: list[int] = []
            for segment_id in highlight.transcript_segment_ids:
                times.append(self._resolve_ref(
                    AssistEvidenceRef(kind="transcript_segment", id=segment_id), request, segment_times
                ))
            for event_id in highlight.session_event_ids:
                times.append(self._resolve_ref(
                    AssistEvidenceRef(kind="session_event", id=event_id), request, segment_times
                ))
            if highlight.linked_alert_id is not None:
                times.append(self._resolve_ref(
                    AssistEvidenceRef(kind="detector_alert", id=highlight.linked_alert_id), request, segment_times
                ))
            available_times[f"highlight:{highlight.id}"] = max(times) if times else request.window_end_ms
        for option in result.options:
            if option.replay_analysis_id != request.analysis_id:
                raise AssistValidationError("Advisory option refers to a different replay analysis")
            if option.source_version != request.source_content_hash or option.model_version != request.model_version:
                raise AssistValidationError("Advisory option source/model version differs from its analysis")
            times = [self._resolve_ref(ref, request, segment_times) for ref in option.supporting_evidence_ids]
            available_times[f"option:{option.id}"] = max(times)

        analysis = {
            "id": request.analysis_id,
            "kind": "assist",
            "input_hash": request.input_hash,
            "versions": {
                "schema_version": "assist-1",
                "source_version": request.source_content_hash,
                "layout_version": request.layout_version,
                "model": job["model"],
                "model_version": request.model_version,
                "config_version": request.config_version,
                "provider": job["provider"],
                "time_alignment": request.time_alignment,
                "transcript_revision_basis": "raw",
                "rule_versions": sorted({
                    version for version in [*(h.rule_version for h in result.highlights),
                                            *(o.rule_version for o in result.options)] if version is not None
                }),
            },
            "window_start_ms": request.window_start_ms,
            "window_end_ms": request.window_end_ms,
            "created_utc": self._now_utc(),
        }
        try:
            return self._storage.commit_result_batch(
                source_session_id=request.source_session_id,
                source_id=request.source_id,
                job_id=request.job_id,
                attempt_id=request.attempt_id,
                result_payload=content,
                payload_hash=payload_hash,
                analysis=analysis,
                segments=segments,
                entities=entities,
                highlights=highlights,
                options=options,
                available_times=available_times,
                final_status=result.status,
                finished_utc=self._now_utc(),
            )
        except ValueError as error:
            raise AssistResultConflict(str(error)) from error

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

    @staticmethod
    def _encode_cursor(kind: str, source_session_id: str, analysis_id: str | None,
                       until_ms: int | None, after_ordinal: int) -> str:
        raw = json.dumps({
            "v": 1, "kind": kind, "source": source_session_id,
            "analysis": analysis_id, "until_ms": until_ms, "after": after_ordinal,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str | None, *, kind: str, source_session_id: str,
                       analysis_id: str | None, until_ms: int | None) -> int:
        if cursor is None:
            return 0
        if len(cursor) > 1000:
            raise AssistValidationError("Assist cursor is invalid")
        try:
            encoded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")))
        except (ValueError, UnicodeError, binascii.Error, json.JSONDecodeError) as error:
            raise AssistValidationError("Assist cursor is invalid") from error
        if (not isinstance(value, dict) or set(value) != {"v", "kind", "source", "analysis", "until_ms", "after"}
                or value["v"] != 1 or value["kind"] != kind or value["source"] != source_session_id
                or value["analysis"] != analysis_id or value["until_ms"] != until_ms
                or isinstance(value["after"], bool) or not isinstance(value["after"], int) or value["after"] < 0):
            raise AssistValidationError("Assist cursor does not match this source, analysis, or replay time")
        return value["after"]

    def list_transcripts(
        self, source_session_id: str, *, analysis_id: str | None, until_ms: int | None,
        cursor: str | None, limit: int,
    ) -> dict[str, Any]:
        if analysis_id is not None and self._storage.analysis(source_session_id, analysis_id) is None:
            raise KeyError("Replay analysis not found")
        after = self._decode_cursor(cursor, kind="transcripts", source_session_id=source_session_id,
                                    analysis_id=analysis_id, until_ms=until_ms)
        rows = self._storage.list_segments(
            source_session_id, analysis_id=analysis_id, until_ms=until_ms, limit=limit + 1,
            after_ordinal=after,
        )
        has_more = len(rows) > limit
        visible = rows[:limit]
        items = [TranscriptReadItem.model_validate({
            "segment": row["segment"], "entities": row["entities"],
            "time_alignment": row["time_alignment"],
            "alignment_uncertainty": row["alignment_uncertainty"],
        })
                 for row in visible]
        next_cursor = None
        if has_more and visible:
            next_cursor = self._encode_cursor(
                "transcripts", source_session_id, analysis_id, until_ms, int(visible[-1]["ordinal"])
            )
        return {"items": [item.model_dump(mode="json") for item in items], "next_cursor": next_cursor}

    def list_highlights(
        self, source_session_id: str, *, analysis_id: str | None, until_ms: int | None,
        cursor: str | None, limit: int,
    ) -> dict[str, Any]:
        if analysis_id is not None and self._storage.analysis(source_session_id, analysis_id) is None:
            raise KeyError("Replay analysis not found")
        after = self._decode_cursor(cursor, kind="highlights", source_session_id=source_session_id,
                                    analysis_id=analysis_id, until_ms=until_ms)
        rows = self._storage.list_highlights(
            source_session_id, analysis_id=analysis_id, until_ms=until_ms, limit=limit + 1,
            after_ordinal=after,
        )
        has_more = len(rows) > limit
        visible = rows[:limit]
        items = [AssistHighlight.model_validate(row["item"]) for row in visible]
        next_cursor = None
        if has_more and visible:
            next_cursor = self._encode_cursor(
                "highlights", source_session_id, analysis_id, until_ms, int(visible[-1]["ordinal"])
            )
        return {"items": [item.model_dump(mode="json") for item in items], "next_cursor": next_cursor}

    def list_options(
        self, source_session_id: str, *, analysis_id: str, until_ms: int | None,
        cursor: str | None, limit: int,
    ) -> dict[str, Any]:
        if self._storage.analysis(source_session_id, analysis_id) is None:
            raise KeyError("Replay analysis not found")
        after = self._decode_cursor(cursor, kind="options", source_session_id=source_session_id,
                                    analysis_id=analysis_id, until_ms=until_ms)
        rows = self._storage.list_options(
            source_session_id, analysis_id=analysis_id, until_ms=until_ms, limit=limit + 1,
            after_ordinal=after,
        )
        has_more = len(rows) > limit
        visible = rows[:limit]
        items = [AdvisoryOptionCandidate.model_validate(row["item"]) for row in visible]
        next_cursor = None
        if has_more and visible:
            next_cursor = self._encode_cursor(
                "options", source_session_id, analysis_id, until_ms, int(visible[-1]["ordinal"])
            )
        return {"items": [item.model_dump(mode="json") for item in items], "next_cursor": next_cursor}

    def get_segment_at(self, source_session_id: str, segment_id: str, until_ms: int) -> dict[str, Any] | None:
        return self._storage.transcript_segment_at(source_session_id, segment_id, until_ms)

    def assist_snapshot(
        self, source_session_id: str, *, analysis_id: str | None = None,
        until_ms: int | None = None, evaluator: bool = False,
    ) -> dict[str, Any]:
        jobs: list[AssistJobView] = []
        for job in self._storage.list_jobs(source_session_id):
            receipt = job.get("result_receipt")
            selected_analysis = receipt.get("analysis_id") if receipt else None
            if until_ms is not None:
                analysis = self._storage.analysis(source_session_id, selected_analysis) if selected_analysis else None
                # Job state is wall-clock state; hide results that extend beyond a historical view.
                if analysis is None or analysis["window_end_ms"] > until_ms:
                    continue
            if analysis_id is not None and selected_analysis != analysis_id:
                continue
            jobs.append(AssistJobView.model_validate({key: job.get(key) for key in (
                "id", "source_session_id", "asset_id", "attempt_id", "status", "provider", "model",
                "version", "config_version", "language", "started_utc", "finished_utc", "error",
                "chunk_progress",
            )} | {"analysis_id": selected_analysis}))
        segments_response = self.list_transcripts(
            source_session_id, analysis_id=analysis_id, until_ms=until_ms, cursor=None, limit=10000
        )
        highlights_response = self.list_highlights(
            source_session_id, analysis_id=analysis_id, until_ms=until_ms, cursor=None, limit=10000
        )
        options_response: dict[str, Any] = {"items": [], "next_cursor": None}
        if evaluator:
            analyses = ([self._storage.analysis(source_session_id, analysis_id)] if analysis_id else
                        [self._storage.analysis(source_session_id, item_id)
                         for item_id in self._storage.analysis_ids(source_session_id)])
            for analysis in analyses:
                if analysis is None or (until_ms is not None and analysis["window_end_ms"] > until_ms):
                    continue
                if analysis["status"] not in {"completed", "needs-review"}:
                    continue
                rows = self._storage.list_options(
                    source_session_id, analysis_id=analysis["id"], until_ms=until_ms,
                    limit=10000, after_ordinal=0,
                )
                options_response["items"].extend(row["item"] for row in rows)
        payload = AssistSnapshotPayload(
            jobs=jobs,
            segments=[TranscriptReadItem.model_validate(item) for item in segments_response["items"]],
            highlights=[AssistHighlight.model_validate(item) for item in highlights_response["items"]],
            options=[AdvisoryOptionCandidate.model_validate(item) for item in options_response["items"]],
            review_annotations=[],
        )
        return AssistSnapshotMessage(
            source_session_id=source_session_id,
            sequence=self._storage.stream_sequence(source_session_id),
            type="snapshot",
            payload=payload,
        ).model_dump(mode="json")

    def stream_events(self, source_session_id: str, after_sequence: int) -> list[dict[str, Any]]:
        return self._storage.stream_events(source_session_id, after_sequence)

    def stream_sequence(self, source_session_id: str) -> int:
        return self._storage.stream_sequence(source_session_id)

    def list_analyses(self, source_session_id: str) -> list[dict[str, Any]]:
        analyses = []
        for analysis_id in self._storage.analysis_ids(source_session_id):
            analysis = self._storage.analysis(source_session_id, analysis_id)
            if analysis is None:
                continue
            analyses.append({key: analysis[key] for key in (
                "id", "source_session_id", "source_id", "kind", "input_hash", "versions",
                "window_start_ms", "window_end_ms", "status",
            )})
        return analyses

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
