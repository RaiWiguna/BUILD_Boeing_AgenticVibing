"""Standalone MOCK SDK acceptance. No credentials, cloud calls, DB or evaluator truth."""

import asyncio
import hashlib
import io
import json
import time
import wave
from typing import Any
from uuid import UUID, uuid4

from google.cloud.speech_v2 import types
from google.protobuf.duration_pb2 import Duration

from flowlens.audio.models import (
    AudioLimits,
    ChunkMetadata,
    FrameRange,
    PreparationMetadata,
    ProbeInfo,
)
from flowlens.audio.planning import plan_chunks
from flowlens.contracts.models import ClockMapping, JobLease, RequestContext
from flowlens.providers.stt.adapter import STTExecutor
from flowlens.providers.stt.models import AuthorizedChunk, ProviderApproval, STTConfig


def mock_config(**changes: Any) -> STTConfig:
    return STTConfig(
        **(
            {
                "project": "mock-project",
                "region": "us",
                "endpoint": "us-speech.googleapis.com",
                "recognizer": "projects/mock-project/locations/us/recognizers/_",
                "model": "chirp_3",
                "language": "en-US",
            }
            | changes
        )
    )


def mock_binding(
    config: STTConfig,
    *,
    offset_ms: int | None = 2000,
    frames: int = 64000,
    channels: int = 1,
    chunk_index: int = 0,
    gaps: tuple[FrameRange, ...] = (),
) -> tuple[AuthorizedChunk, bytes]:
    """Generated zero PCM, explicitly MOCK metadata. Not an audio quality fixture."""
    limits = AudioLimits(chunk_ms=3000, overlap_ms=1000)
    clock = ClockMapping(
        offset_ms=offset_ms, uncertainty_ms=None if offset_ms is None else 5, timezone="UTC"
    )
    plans = plan_chunks(
        decoded_frames=frames,
        source_rate=16000,
        channels=channels,
        clock=clock,
        limits=limits,
        source_gaps=gaps,
    )
    chunks: list[ChunkMetadata] = []
    buffers: list[bytes] = []
    for index, plan in enumerate(plans):
        count = plan.derivative_frames.end - plan.derivative_frames.start
        stream = io.BytesIO()
        with wave.open(stream, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * count)
        audio = stream.getvalue()
        buffers.append(audio)
        chunks.append(
            ChunkMetadata(
                filename=f"chunk-{index}.wav",
                plan=plan,
                sha256=hashlib.sha256(audio).hexdigest(),
                byte_count=len(audio),
                local_frames=FrameRange(start=0, end=count),
            )
        )
    prep = PreparationMetadata(
        source_id=UUID(int=5),
        asset_id=UUID(int=6),
        source_sha256="b" * 64,
        source_after_sha256="b" * 64,
        probe=ProbeInfo(
            sample_rate=16000,
            channels=channels,
            duration_seconds=frames / 16000,
            codec="pcm_s16le",
            container="wav",
        ),
        decoded_frames=frames,
        output_rate=16000,
        decoded_sha256="c" * 64,
        clock=clock,
        source_gaps=gaps,
        config=limits,
        config_sha256=limits.digest(),
        ffmpeg_version="MOCK",
        ffprobe_version="MOCK",
        chunks=tuple(chunks),
    )
    ctx = RequestContext(
        actor_id=UUID(int=3),
        capabilities=["worker", "audio"],
        session_id=UUID(int=1),
        analysis_run_id=UUID(int=2),
        input_revision=1,
        input_hash="a" * 64,
        as_of_ms=0,
        mode="DEBRIEF",
        request_id=uuid4(),
    )
    chunk_id = uuid4()
    now = time.time_ns() // 1_000_000
    lease = JobLease(
        session_id=ctx.session_id,
        analysis_run_id=ctx.analysis_run_id,
        revision=1,
        job_id=uuid4(),
        attempt_id=uuid4(),
        lease_id=uuid4(),
        owner_id=ctx.actor_id,
        stage="STT",
        input_hash=ctx.input_hash,
        config_hash=config.digest(),
        expires_ms=now + 60000,
        deadline_ms=now + 120000,
        budget_microunits=1,
        asset_ids=[chunk_id],
    )
    return AuthorizedChunk(
        context=ctx,
        lease=lease,
        chunk_id=chunk_id,
        preparation=prep,
        chunk_index=chunk_index,
        local_permission="ALLOWED",
        cloud_permission="ALLOWED",
        approval=ProviderApproval(
            config_hash=config.digest(),
            compatibility="VERIFIED",
            api_enabled=True,
            identity_authorized=True,
            billing_authorized=True,
            data_logging="DISABLED",
        ),
    ), buffers[chunk_index]


def mock_response(
    *, word: str = "hold", start_ns: int = 100_000_000, end_ns: int = 500_000_000
) -> types.RecognizeResponse:
    return types.RecognizeResponse(
        results=[
            types.SpeechRecognitionResult(
                channel_tag=1,
                language_code="en-US",
                result_end_offset=Duration(nanos=end_ns),
                alternatives=[
                    types.SpeechRecognitionAlternative(
                        transcript=word,
                        confidence=0.8,
                        words=[
                            types.WordInfo(
                                word=word,
                                start_offset=Duration(nanos=start_ns),
                                end_offset=Duration(nanos=end_ns),
                                confidence=0.7,
                            )
                        ],
                    )
                ],
            )
        ],
        metadata=types.RecognitionResponseMetadata(total_billed_duration=Duration(seconds=3)),
    )


class MockClient:
    profile = "MOCK"

    def __init__(
        self,
        response: types.RecognizeResponse | None = None,
        *,
        errors: list[Exception] | None = None,
        delay: float = 0.0,
    ) -> None:
        self.response = response if response is not None else mock_response()
        self.errors = errors or []
        self.delay = delay
        self.requests: list[types.RecognizeRequest] = []
        self.cancelled = self.active = self.peak = 0
        self.closed = False

    async def recognize(
        self, request: types.RecognizeRequest, *, retry: None, timeout: float
    ) -> types.RecognizeResponse:
        if retry is not None or timeout <= 0:
            raise RuntimeError("Invalid transport control")
        self.requests.append(request)
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.delay)
            if self.errors:
                raise self.errors.pop(0)
            return self.response
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        finally:
            self.active -= 1

    async def close(self) -> None:
        self.closed = True


async def smoke() -> None:
    config = mock_config()
    binding, audio = mock_binding(config)
    client = MockClient()
    executor = STTExecutor(config, client)
    try:
        raw, usage = await executor.transcribe(
            binding, audio, lambda: binding.lease, reserve=lambda lease, ms: None
        )  # MOCK budget
        if raw.status != "COMPLETE" or usage.audio_ms != 3000 or executor.calls != 1:
            raise RuntimeError("MOCK STT acceptance failed")
    finally:
        await executor.close()
    print(
        json.dumps(
            {
                "unit": "B03",
                "profile": "MOCK",
                "provider_calls": 0,
                "sdk_mock_calls": executor.calls,
                "status": "passed",
                "pipeline_ready": False,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(smoke())
