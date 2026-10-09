"""Standalone MOCK worker -> private artifact -> API UOW acceptance, never Package A."""

import asyncio
import json
from collections.abc import Generator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from flowlens.analysis.transcript_projection import project
from flowlens.analysis.transcript_records import RawTranscript
from flowlens.bindings.stt import PrivateTranscriptIngest
from flowlens.contracts.models import ArtifactSubmission, JobLease, RequestContext
from flowlens.contracts.ports import UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.providers.stt.adapter import STTExecutor, map_response
from flowlens.providers.stt.execution import execute_attempt
from flowlens.providers.stt.models import AuthorizedChunk
from flowlens.testing.harness import FakePlatform
from flowlens.testing.stt import MockClient, mock_binding, mock_config, mock_response
from flowlens.testing.transcripts import TranscriptReferenceTransactions

RECORDED = datetime(2026, 10, 9, tzinfo=UTC)


class MockBridge:
    """In-memory transport/authority double; not authenticated or durable platform evidence."""

    profile = "MOCK"

    def __init__(self, binding: AuthorizedChunk, audio: bytes) -> None:
        self.binding, self.audio = binding, audio
        self.artifacts: dict[UUID, tuple[ArtifactSubmission, bytes]] = {}
        self.active = True
        self.upload_mode = "complete"
        self.downloads = 0
        self.reserved_ms = 0

    def resolve(self, lease: JobLease) -> AuthorizedChunk:
        if lease != self.checkpoint():
            raise ContractError("LEASE_EXPIRED")
        return self.binding

    def checkpoint(self) -> JobLease:
        if not self.active:
            raise ContractError("LEASE_EXPIRED")
        return self.binding.lease

    def reserve(self, lease: JobLease, audio_ms: int) -> None:
        if lease != self.checkpoint():
            raise ContractError("LEASE_EXPIRED")
        self.reserved_ms += audio_ms

    def download(self, context: RequestContext, asset_id: UUID, start: int, end: int) -> bytes:
        if context != self.binding.context or asset_id != self.binding.chunk_id:
            raise ContractError("ACCESS_DENIED")
        self.checkpoint()
        self.downloads += 1
        return self.audio[start:end]

    def submit(
        self, context: RequestContext, artifact: ArtifactSubmission, chunks: Iterator[bytes]
    ) -> UUID:
        if context != self.binding.context:
            raise ContractError("ACCESS_DENIED")
        self.stream = chunks
        if self.upload_mode == "partial":
            next(chunks)
            raise RuntimeError("private consumer error")
        if self.upload_mode == "early":
            return artifact.id
        if self.upload_mode == "closed_early":
            next(chunks)
            if not isinstance(chunks, Generator):
                raise RuntimeError("Expected upload generator")
            chunks.close()
            return artifact.id
        payload = b"".join(chunks)
        self.artifacts[artifact.id] = (artifact, payload)
        if self.upload_mode == "cancel_after":
            self.active = False
        return artifact.id

    def staged(
        self, context: RequestContext, artifact_id: UUID, uow: UnitOfWork
    ) -> tuple[ArtifactSubmission, bytes]:
        self.checkpoint()
        artifact, payload = self.artifacts[artifact_id]
        context.require("audio", artifact.session_id, artifact.analysis_run_id)
        return artifact, payload

    def authoritative(
        self, context: RequestContext, raw: RawTranscript, uow: UnitOfWork
    ) -> tuple[AuthorizedChunk, bytes]:
        lease = self.checkpoint()
        if (raw.job_id, raw.attempt_id, raw.lease_id) != (
            lease.job_id,
            lease.attempt_id,
            lease.lease_id,
        ):
            raise ContractError("LEASE_EXPIRED")
        if (context.input_revision, context.input_hash) != (lease.revision, lease.input_hash):
            raise ContractError("SOURCE_REVISION_CHANGED")
        return self.binding, self.audio


async def produce(bridge: MockBridge) -> ArtifactSubmission:
    executor = STTExecutor(mock_config(), MockClient())
    try:
        artifact, _ = await execute_attempt(
            bridge.binding.lease, bridge, bridge, executor, bridge.checkpoint, bridge.reserve
        )
        return artifact
    finally:
        await executor.close()


def setup_bridge() -> tuple[MockBridge, RequestContext, FakePlatform]:
    config = mock_config()
    binding, audio = mock_binding(config)
    bridge = MockBridge(binding, audio)
    context = binding.context.model_copy(
        update={"capabilities": ["read", "audio", "analysis"], "as_of_ms": 100000}
    )
    raw = map_response(config, binding, mock_response())
    evidence = FakePlatform([], list(project(raw, recorded_at=RECORDED, origin="MOCK")))
    return bridge, context, evidence


def main() -> None:
    bridge, context, evidence = setup_bridge()
    artifact = asyncio.run(produce(bridge))
    with TemporaryDirectory(prefix="flowlens-stt-boundary-") as temporary:
        path = Path(temporary) / "transcripts.db"
        transactions = TranscriptReferenceTransactions(path)
        transactions.seed(context)
        service = PrivateTranscriptIngest(mock_config(), bridge, evidence)
        with transactions.begin() as uow:
            identifier = service.accept(context, artifact.id, RECORDED, "MOCK", uow)
            uow.commit()
        restarted = TranscriptReferenceTransactions(path)
        with restarted.begin() as uow:
            if (
                service.accept(context, artifact.id, RECORDED + timedelta(seconds=1), "MOCK", uow)
                != identifier
                or len(service.lifecycle.current_segments(context, uow)) != 1
            ):
                raise RuntimeError("Private boundary recovery invariant failed")
            uow.commit()
    # Only the MOCK platform can delete its staged artifacts; worker owns no files.
    bridge.artifacts.clear()
    print(
        json.dumps(
            {
                "unit": "B03_PRIVATE_BOUNDARY",
                "profile": "MOCK",
                "status": "passed",
                "provider_calls": 0,
                "sdk_mock_calls": 1,
                "pipeline_ready": False,
                "database": "disposable-cleaned",
                "staging": "mock-platform-cleaned",
            }
        )
    )


if __name__ == "__main__":
    main()
