"""Internal configuration/binding, never additions to the frozen wire envelope."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol
from uuid import UUID

from pydantic import Field

from flowlens.audio.models import AudioLimits, AudioRecord, FrameRange
from flowlens.contracts.models import Asset, ClockMapping, CommitReceipt, JobLease, RequestContext


class WorkerConfig(AudioRecord):
    worker_id: UUID
    scratch_root: Path
    heartbeat_seconds: float = Field(default=1.0, ge=0.05, le=10.0)
    block_bytes: int = Field(default=65536, ge=1024, le=1024 * 1024)
    max_metadata_bytes: int = Field(default=2 * 1024**2, ge=1024, le=8 * 1024**2)
    max_attempts: int = Field(default=100, ge=1, le=10000)
    audio: AudioLimits = AudioLimits()


class AudioInput(AudioRecord):
    """Trusted adapter resolves one leased asset; no inventory or source labels."""

    context: RequestContext
    job_id: UUID
    attempt_id: UUID
    lease_id: UUID
    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    audio_config_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_id: UUID
    asset: Asset
    size_bytes: int = Field(gt=0, le=512 * 1024**2)
    clock: ClockMapping
    source_gaps: tuple[FrameRange, ...] = Field(default=(), max_length=4096)
    local_allowed: Literal[True]


class InputAccess(Protocol):
    def resolve(self, lease: JobLease) -> AudioInput: ...


@dataclass(frozen=True)
class WorkerOutcome:
    status: Literal["IDLE", "RECEIPT", "FAILED", "ABORTED", "UNCONFIRMED"]
    code: str
    receipt: CommitReceipt | None = None
