"""Standalone STT acquisition/submission binding through injected ports.

This is a single-attempt operation, not a scheduler or accepted-result transport.
Checkpoints own heartbeat/cancellation/rights; synchronous ports must be bounded.
No local files are created. Platform owns partial/staged upload TTL and promotion.
"""

import time
from collections.abc import Callable, Generator
from typing import Protocol
from uuid import UUID

from flowlens.contracts.models import ArtifactSubmission, JobLease, Usage
from flowlens.contracts.ports import AssetAccess
from flowlens.providers.stt.adapter import STTExecutor, validate_authorization
from flowlens.providers.stt.models import AuthorizedChunk, STTFailure
from flowlens.providers.stt.provenance import encode, manifest


class ChunkAccess(Protocol):
    def resolve(self, lease: JobLease) -> AuthorizedChunk:
        """Return only this worker's authorized B02 chunk, never evaluator labels."""
        ...


async def execute_attempt(
    lease: JobLease,
    inputs: ChunkAccess,
    assets: AssetAccess,
    executor: STTExecutor,
    checkpoint: Callable[[], JobLease],
    reserve: Callable[[JobLease, int], None],
) -> tuple[ArtifactSubmission, Usage]:
    started = time.monotonic()
    initial_ms = executor.now_ms()
    last_expiry = lease.expires_ms

    def check() -> JobLease:
        nonlocal last_expiry
        current = JobLease.model_validate_json(checkpoint().model_dump_json())
        if (
            current.model_dump(exclude={"expires_ms"}) != lease.model_dump(exclude={"expires_ms"})
            or current.expires_ms < last_expiry
        ):
            raise STTFailure("STT_LOST_LEASE")
        last_expiry = current.expires_ms
        now = max(executor.now_ms(), initial_ms + int((time.monotonic() - started) * 1000))
        if now >= min(current.expires_ms, current.deadline_ms):
            raise STTFailure("STT_LEASE_EXPIRED")
        if time.monotonic() - started >= executor.config.timeout_seconds:
            raise STTFailure("STT_TIMEOUT")
        return current

    try:
        check()
        serialized = inputs.resolve(lease).model_dump_json()
        if len(serialized.encode()) > 524288:
            raise STTFailure("STT_BINDING_INVALID")
        binding = AuthorizedChunk.model_validate_json(serialized)
        if binding.lease != lease:
            raise STTFailure("STT_BINDING_INVALID")
        validate_authorization(executor.config, binding)
        # Reject invalid index/declared size before any range request/allocation.
        if binding.chunk_index >= len(binding.preparation.chunks):
            raise STTFailure("STT_BINDING_INVALID")
        size = binding.preparation.chunks[binding.chunk_index].byte_count
        if not 44 <= size <= 9_999_999:
            raise STTFailure("STT_AUDIO_INVALID")
        data = bytearray()
        for start in range(0, size, 65536):
            check()
            end = min(start + 65536, size)
            block = assets.download(binding.context, binding.chunk_id, start, end)
            if type(block) is not bytes or len(block) != end - start:
                raise STTFailure("STT_AUDIO_INVALID")
            data.extend(block)
        raw, usage = await executor.transcribe(binding, bytes(data), check, reserve=reserve)
        payload = encode(raw)
        artifact = manifest(binding, payload)
        fully_consumed = False

        def blocks() -> Generator[bytes, None, None]:
            nonlocal fully_consumed
            for offset in range(0, len(payload), 65536):
                check()
                yield payload[offset : offset + 65536]
            fully_consumed = True

        stream = blocks()
        try:
            identifier: UUID = assets.submit(binding.context, artifact, stream)
            # A consumer returning early must never be considered a complete upload.
            if not fully_consumed or identifier != artifact.id:
                raise STTFailure("STT_OUTPUT_INVALID")
        finally:
            stream.close()
        check()
        return artifact, usage
    except STTFailure:
        raise
    except Exception:
        raise STTFailure("STT_CONTROL_FAILED") from None
