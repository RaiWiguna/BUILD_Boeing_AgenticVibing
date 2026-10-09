"""Local audio preparation records; these are not frozen wire DTOs."""

import hashlib
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from flowlens.contracts.models import ClockMapping


class AudioRecord(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", allow_inf_nan=False)


class AudioLimits(AudioRecord):
    """Engineering limits, not a claim about verified provider quotas."""

    max_input_bytes: int = Field(default=512 * 1024**2, gt=0, le=512 * 1024**2)
    max_duration_seconds: int = Field(default=3600, gt=0, le=3600)
    max_channels: int = Field(default=2, ge=1, le=2)
    max_input_rate: int = Field(default=192000, ge=8000, le=192000)
    output_rate: int = Field(default=16000, ge=8000, le=192000)
    chunk_ms: int = Field(default=50000, gt=0, le=50000)
    overlap_ms: int = Field(default=1000, ge=0)
    max_chunk_bytes: int = Field(default=9_999_999, gt=44, lt=10_000_000)
    max_chunks: int = Field(default=512, gt=0, le=4096)
    max_output_bytes: int = Field(default=512 * 1024**2, gt=44, le=1024**3)
    process_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    probe_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    config_version: Literal["audio-1"] = "audio-1"

    @model_validator(mode="after")
    def valid_overlap(self) -> Self:
        capacity = min(self.chunk_ms * self.output_rate // 1000, (self.max_chunk_bytes - 44) // 2)
        if capacity <= self.overlap_ms * self.output_rate // 1000:
            raise ValueError("Overlap must be smaller than effective chunk capacity.")
        return self

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class FrameRange(AudioRecord):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("Frame range must have positive length.")
        return self


class ProbeInfo(AudioRecord):
    sample_rate: int
    channels: int
    duration_seconds: float
    codec: str
    container: str


class ChunkPlan(AudioRecord):
    channel: int
    derivative_frames: FrameRange
    source_frames: FrameRange
    source_start_ms: float
    source_end_ms: float
    session_start_ms: float | None
    session_end_ms: float | None
    overlap_frames: int
    coverage_segment: int
    gap_before_source_frames: int
    expected_bytes: int


class ChunkMetadata(AudioRecord):
    filename: str
    plan: ChunkPlan
    sha256: str
    byte_count: int
    # Each WAV is mono PCM16, starting at local frame zero.
    local_frames: FrameRange


class PreparationMetadata(AudioRecord):
    transform_version: Literal["pcm16-channel-chunks-1"] = "pcm16-channel-chunks-1"
    source_id: UUID
    asset_id: UUID
    source_sha256: str
    source_after_sha256: str
    probe: ProbeInfo
    decoded_frames: int
    output_rate: int
    output_channels: Literal[1] = 1
    sample_width_bytes: Literal[2] = 2
    decoded_sha256: str
    clock: ClockMapping
    source_gaps: tuple[FrameRange, ...]
    config: AudioLimits
    config_sha256: str
    ffmpeg_version: str
    ffprobe_version: str
    chunks: tuple[ChunkMetadata, ...]
