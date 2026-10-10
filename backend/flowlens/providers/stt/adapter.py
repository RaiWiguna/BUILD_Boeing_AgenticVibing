"""Bounded cancellable Google V2 calls; SDK DTOs stay within this module.

Caller provides an authoritative lease/permission checkpoint. No database, artifact
promotion, scheduler, implicit ADC lookup, logging, or accepted-state writes.
"""

import asyncio
import base64
import hashlib
import io
import math
import time
import wave
from collections.abc import Callable, Coroutine
from fractions import Fraction
from importlib.metadata import version
from typing import Any, Protocol, TypeVar
from uuid import uuid5

from flowlens.analysis.transcript_records import Hypothesis, Offset, RawTranscript, Word
from flowlens.audio.planning import plan_chunks
from flowlens.contracts.models import JobLease, Usage
from flowlens.providers.stt.models import AuthorizedChunk, STTConfig, STTFailure
from google.api_core import exceptions as google_errors
from google.auth.credentials import Credentials
from google.cloud.speech_v2 import SpeechAsyncClient, types
from google.cloud.speech_v2.services.speech.transports.grpc_asyncio import (
    SpeechGrpcAsyncIOTransport,
)
from google.protobuf.duration_pb2 import Duration
from google.protobuf.field_mask_pb2 import FieldMask

T = TypeVar("T")


class Client(Protocol):
    def recognize(
        self, request: types.RecognizeRequest, *, retry: None, timeout: float
    ) -> Coroutine[Any, Any, types.RecognizeResponse]: ...
    async def close(self) -> None: ...


class GoogleClient:
    """Explicit credentials only. One bounded grpc.aio channel per executor lifetime."""

    def __init__(self, config: STTConfig, credentials: Credentials) -> None:
        config = STTConfig.model_validate_json(config.model_dump_json())
        channel = SpeechGrpcAsyncIOTransport.create_channel(
            host=config.endpoint,
            credentials=credentials,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
            options=[
                ("grpc.max_receive_message_length", config.max_response_bytes),
                ("grpc.max_send_message_length", 10_010_000),
            ],
        )
        self.channel = channel
        self.client = SpeechAsyncClient(
            transport=SpeechGrpcAsyncIOTransport(
                host=config.endpoint, channel=channel, credentials=credentials
            )
        )

    async def recognize(
        self, request: types.RecognizeRequest, *, retry: None, timeout: float
    ) -> types.RecognizeResponse:
        return await self.client.recognize(request=request, retry=retry, timeout=timeout)

    async def close(self) -> None:
        await self.channel.close()


def duration_ns(value: Duration) -> int:
    if value.seconds < 0 or value.nanos < 0 or value.nanos >= 1_000_000_000:
        raise STTFailure("STT_OUTPUT_INVALID")
    return value.seconds * 1_000_000_000 + value.nanos


def confidence(value: float, *, enabled: bool = True) -> float | None:
    if not math.isfinite(value) or value < 0 or value > 1:
        raise STTFailure("STT_OUTPUT_INVALID")
    # Proto3 default zero is documented as the unset sentinel, not certainty=0.
    return value if enabled and value != 0 else None


def enclosing(start: Fraction, end: Fraction) -> Offset:
    return Offset(start_ns=math.floor(start), end_ns=math.ceil(end))


def map_response(
    config: STTConfig, binding: AuthorizedChunk, response: types.RecognizeResponse
) -> RawTranscript:
    """Reject malformed responses; preserve exact bytes before any derived interpretation."""
    if binding.lease.analysis_run_id is None:
        raise STTFailure("STT_BINDING_INVALID")
    pb = types.RecognizeResponse.pb(response)
    if pb.ByteSize() > config.max_response_bytes:
        raise STTFailure("STT_OUTPUT_LIMIT")
    serialized = pb.SerializeToString(deterministic=True)
    prep = binding.preparation
    chunk = prep.chunks[binding.chunk_index]
    plan = chunk.plan
    start = Fraction(plan.derivative_frames.start * 1_000_000_000, prep.output_rate)
    end = Fraction(plan.derivative_frames.end * 1_000_000_000, prep.output_rate)
    duration = end - start
    offset = prep.clock.offset_ms
    source_range = enclosing(start, end)
    session_range = (
        None if offset is None else enclosing(start + offset * 1_000_000, end + offset * 1_000_000)
    )
    hypotheses: list[Hypothesis] = []
    word_count = text_count = 0
    incomplete = False
    previous_end = 0
    for index, result in enumerate(pb.results):
        if result.channel_tag not in (0, 1) or result.language_code not in ("", config.language):
            raise STTFailure("STT_OUTPUT_INVALID")
        result_end = (
            duration_ns(result.result_end_offset) if result.HasField("result_end_offset") else None
        )
        if result_end is not None and (result_end > duration or result_end < previous_end):
            raise STTFailure("STT_OUTPUT_INVALID")
        prior_result_end = previous_end
        previous_end = result_end if result_end is not None else previous_end
        if not result.alternatives:
            incomplete = True
        for alt_index, alt in enumerate(result.alternatives):
            text_count += len(alt.transcript)
            word_count += len(alt.words)
            if (
                len(hypotheses) >= config.max_hypotheses
                or word_count > config.max_words
                or text_count > config.max_text_characters
            ):
                raise STTFailure("STT_OUTPUT_LIMIT")
            if alt.words and not alt.transcript.strip():
                raise STTFailure("STT_OUTPUT_INVALID")
            words: list[Word] = []
            last = prior_result_end
            for word in alt.words:
                has_start, has_end = word.HasField("start_offset"), word.HasField("end_offset")
                if has_start != has_end or not word.word.strip():
                    raise STTFailure("STT_OUTPUT_INVALID")
                local = source = session = None
                if has_start:
                    a, b = duration_ns(word.start_offset), duration_ns(word.end_offset)
                    if (
                        a < last
                        or b <= a
                        or b > duration
                        or (result_end is not None and b > result_end)
                    ):
                        raise STTFailure("STT_OUTPUT_INVALID")
                    last = b
                    local = Offset(start_ns=a, end_ns=b)
                    source = enclosing(start + a, start + b)
                    if offset is not None:
                        session = enclosing(
                            start + a + offset * 1_000_000, start + b + offset * 1_000_000
                        )
                words.append(
                    Word(
                        text=word.word,
                        local=local,
                        source=source,
                        session=session,
                        confidence=confidence(word.confidence, enabled=config.word_confidence),
                    )
                )
            if alt.transcript.strip() and (not words or any(w.local is None for w in words)):
                incomplete = True
            hypotheses.append(
                Hypothesis(
                    result_index=index,
                    alternative_index=alt_index,
                    text=alt.transcript,
                    language=result.language_code,
                    confidence=confidence(alt.confidence),
                    end_ns=result_end,
                    words=tuple(words),
                )
            )
    billed = (
        duration_ns(pb.metadata.total_billed_duration)
        if pb.HasField("metadata") and (pb.metadata.HasField("total_billed_duration"))
        else None
    )
    # Billing may round up, but a mono <=60s inline request cannot plausibly bill hours.
    if billed is not None and billed > 61_000_000_000:
        raise STTFailure("STT_OUTPUT_INVALID")
    spoken = any(h.text.strip() for h in hypotheses)
    return RawTranscript(
        id=uuid5(binding.lease.attempt_id, str(binding.chunk_id)),
        session_id=binding.context.session_id,
        analysis_run_id=binding.lease.analysis_run_id,
        revision=binding.context.input_revision,
        input_hash=binding.context.input_hash,
        config_hash=config.digest(),
        job_id=binding.lease.job_id,
        attempt_id=binding.lease.attempt_id,
        lease_id=binding.lease.lease_id,
        source_id=prep.source_id,
        source_hash=prep.source_sha256,
        chunk_id=binding.chunk_id,
        chunk_hash=chunk.sha256,
        channel=plan.channel,
        coverage_segment=plan.coverage_segment,
        source_range=source_range,
        session_range=session_range,
        uncertainty_ms=prep.clock.uncertainty_ms,
        sdk_version=version("google-cloud-speech"),
        config_json=config.model_dump_json(),
        preparation_json=prep.model_dump_json(),
        response_base64=base64.b64encode(serialized).decode(),
        response_hash=hashlib.sha256(serialized).hexdigest(),
        hypotheses=tuple(hypotheses),
        status="PARTIAL" if incomplete else ("COMPLETE" if spoken else "NO_SPEECH"),
        billed_ns=billed,
    )


def validate_authorization(config: STTConfig, binding: AuthorizedChunk) -> None:
    ctx, lease, prep = binding.context, binding.lease, binding.preparation
    if binding.local_permission != "ALLOWED" or binding.cloud_permission != "ALLOWED":
        raise STTFailure("STT_PERMISSION_DENIED")
    if (
        binding.approval.compatibility != "VERIFIED"
        or not binding.approval.api_enabled
        or not binding.approval.identity_authorized
        or not binding.approval.billing_authorized
        or binding.approval.data_logging != "DISABLED"
    ):
        raise STTFailure("STT_PROFILE_UNVERIFIED")
    if (
        lease.stage != "STT"
        or lease.analysis_run_id is None
        or (ctx.session_id, ctx.analysis_run_id, ctx.input_revision, ctx.input_hash)
        != (lease.session_id, lease.analysis_run_id, lease.revision, lease.input_hash)
        or ctx.actor_id != lease.owner_id
        or set(ctx.capabilities) != {"worker", "audio"}
        or lease.config_hash != config.digest()
        or binding.approval.config_hash != config.digest()
        or lease.asset_ids != [binding.chunk_id]
        or lease.budget_microunits <= 0
        or binding.chunk_index >= len(prep.chunks)
    ):
        raise STTFailure("STT_BINDING_INVALID")


def validate_binding(config: STTConfig, binding: AuthorizedChunk, audio: bytes) -> None:
    validate_authorization(config, binding)
    prep = binding.preparation
    if (
        prep.config_sha256 != prep.config.digest()
        or prep.source_after_sha256 != prep.source_sha256
        or prep.output_rate != prep.config.output_rate
        or prep.output_channels != 1
        or prep.sample_width_bytes != 2
    ):
        raise STTFailure("STT_BINDING_INVALID")
    plans = plan_chunks(
        decoded_frames=prep.decoded_frames,
        source_rate=prep.probe.sample_rate,
        channels=prep.probe.channels,
        limits=prep.config,
        clock=prep.clock,
        source_gaps=prep.source_gaps,
    )
    if tuple(c.plan for c in prep.chunks) != plans:
        raise STTFailure("STT_BINDING_INVALID")
    chunk = prep.chunks[binding.chunk_index]
    frames = chunk.plan.derivative_frames.end - chunk.plan.derivative_frames.start
    if (
        type(audio) is not bytes
        or len(audio) != chunk.byte_count
        or len(audio) > 9_999_999
        or len(audio) != chunk.plan.expected_bytes
        or len(audio) != 44 + frames * 2
        or hashlib.sha256(audio).hexdigest() != chunk.sha256
        or chunk.local_frames.start != 0
        or chunk.local_frames.end != frames
        or frames > 60 * prep.output_rate
    ):
        raise STTFailure("STT_AUDIO_INVALID")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if (
                wav.getnchannels(),
                wav.getsampwidth(),
                wav.getframerate(),
                wav.getnframes(),
                wav.getcomptype(),
            ) != (1, 2, prep.output_rate, frames, "NONE"):
                raise STTFailure("STT_AUDIO_INVALID")
    except (wave.Error, EOFError):
        raise STTFailure("STT_AUDIO_INVALID") from None


class STTExecutor:
    def __init__(
        self,
        config: STTConfig,
        client: Client,
        *,
        now_ms: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
    ) -> None:
        self.config = STTConfig.model_validate_json(config.model_dump_json())
        self.client, self.now_ms = client, now_ms
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        self.calls = 0
        self.attempted_audio_ms = 0
        self.seen: set[tuple[object, object]] = set()
        self.closed = False

    def validate(self, binding: AuthorizedChunk, audio: bytes) -> None:
        if self.closed:
            raise STTFailure("STT_BINDING_INVALID")
        validate_binding(self.config, binding, audio)

    async def controlled(
        self,
        operation: Coroutine[Any, Any, T],
        check: Callable[[], None],
        deadline: float,
        discard: Callable[[T], None] | None = None,
    ) -> T:
        task = asyncio.create_task(operation)
        try:
            while not task.done():
                check()
                if time.monotonic() >= deadline:
                    raise STTFailure("STT_TIMEOUT")
                await asyncio.wait({task}, timeout=min(0.05, max(0, deadline - time.monotonic())))
            if time.monotonic() >= deadline:
                raise STTFailure("STT_TIMEOUT")
            check()
            return await task
        except BaseException:
            if (
                discard is not None
                and task.done()
                and not task.cancelled()
                and task.exception() is None
            ):
                discard(task.result())
            raise
        finally:
            if not task.done():
                task.cancel()
            # grpc.aio cancellation propagates to the RPC. Injected clients must cooperate.
            await asyncio.gather(task, return_exceptions=True)

    async def transcribe(
        self,
        binding: AuthorizedChunk,
        audio: bytes,
        checkpoint: Callable[[], JobLease],
        *,
        reserve: Callable[[JobLease, int], None],
    ) -> tuple[RawTranscript, Usage]:
        """Checkpoint must be bounded, authoritative and check permission revocation as well."""
        started = time.monotonic()
        try:
            serialized_binding = binding.model_dump_json()
            if len(serialized_binding.encode()) > 524288:
                raise STTFailure("STT_BINDING_INVALID")
            binding = AuthorizedChunk.model_validate_json(serialized_binding)
            self.validate(binding, audio)
            initial_epoch = self.now_ms()
            initial_tick = time.monotonic()
            lease = binding.lease
            last_expiry = lease.expires_ms

            def check() -> None:
                nonlocal last_expiry
                if self.closed:
                    raise STTFailure("STT_SHUTDOWN")
                current = JobLease.model_validate_json(checkpoint().model_dump_json())
                if (
                    current.model_dump(exclude={"expires_ms"})
                    != lease.model_dump(exclude={"expires_ms"})
                    or current.expires_ms < last_expiry
                ):
                    raise STTFailure("STT_LOST_LEASE")
                last_expiry = current.expires_ms
                now = max(
                    self.now_ms(), initial_epoch + int((time.monotonic() - initial_tick) * 1000)
                )
                if now >= current.deadline_ms:
                    raise STTFailure("STT_DEADLINE")
                if now >= current.expires_ms:
                    raise STTFailure("STT_LEASE_EXPIRED")

            check()
            key = (lease.attempt_id, binding.chunk_id)
            if key in self.seen or len(self.seen) >= self.config.max_calls:
                raise STTFailure("STT_DUPLICATE_OR_LIMIT")
            self.seen.add(key)
            deadline = started + self.config.timeout_seconds
            acquired = False
            try:
                await self.controlled(
                    self.semaphore.acquire(),
                    check,
                    deadline,
                    discard=lambda _: self.semaphore.release(),
                )
                acquired = True
                request = types.RecognizeRequest(
                    recognizer=self.config.recognizer,
                    config=types.RecognitionConfig(
                        auto_decoding_config=types.AutoDetectDecodingConfig(),
                        model=self.config.model,
                        language_codes=[self.config.language],
                        features=types.RecognitionFeatures(
                            enable_word_time_offsets=True,
                            enable_word_confidence=self.config.word_confidence,
                        ),
                    ),
                    config_mask=FieldMask(paths=["*"]),
                    content=audio,
                )
                response: types.RecognizeResponse | None = None
                for attempt in range(self.config.max_attempts):
                    check()
                    if self.calls >= self.config.max_calls:
                        raise STTFailure("STT_CALL_LIMIT")
                    chunk = binding.preparation.chunks[binding.chunk_index]
                    audio_ms = math.ceil(
                        (chunk.local_frames.end * 1000) / binding.preparation.output_rate
                    )
                    # Caller/platform owns pricing and durable budget reservation for every retry.
                    reserve(lease, audio_ms)
                    check()
                    self.calls += 1
                    self.attempted_audio_ms += audio_ms
                    try:
                        response = await self.controlled(
                            self.client.recognize(
                                request, retry=None, timeout=max(0.001, deadline - time.monotonic())
                            ),
                            check,
                            deadline,
                        )
                        break
                    except google_errors.ResourceExhausted:
                        raise STTFailure("STT_QUOTA") from None
                    except (
                        google_errors.ServiceUnavailable,
                        google_errors.DeadlineExceeded,
                    ) as exc:
                        if attempt + 1 >= self.config.max_attempts:
                            raise STTFailure(
                                "STT_TIMEOUT"
                                if isinstance(exc, google_errors.DeadlineExceeded)
                                else "STT_UNAVAILABLE"
                            ) from None
                        await self.controlled(
                            asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1)),
                            check,
                            deadline,
                        )
                    except (google_errors.PermissionDenied, google_errors.Unauthenticated):
                        raise STTFailure("STT_PROVIDER_DENIED") from None
                check()
                if response is None:
                    raise STTFailure("STT_UNAVAILABLE")
                raw = map_response(self.config, binding, response)
                check()
                return raw, Usage(
                    audio_ms=None
                    if raw.billed_ns is None
                    else math.ceil(raw.billed_ns / 1_000_000),
                    input_tokens=None,
                    output_tokens=None,
                    cost_microunits=None,
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
            finally:
                if acquired:
                    self.semaphore.release()
        except STTFailure:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            raise STTFailure("STT_INVALID_OR_UNAVAILABLE") from None

    async def close(self) -> None:
        self.closed = True
        try:
            await asyncio.wait_for(self.client.close(), timeout=self.config.timeout_seconds)
        except Exception:
            raise STTFailure("STT_CLIENT_CLOSE_FAILED") from None
