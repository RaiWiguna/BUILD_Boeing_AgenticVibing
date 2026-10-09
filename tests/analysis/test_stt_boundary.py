"""Worker/private provenance acceptance with explicit MOCK authority and disposable UOW."""

import asyncio
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import timedelta
from uuid import uuid4

import pytest
from flowlens.analysis.transcript_records import RawTranscript
from flowlens.bindings.stt import PrivateTranscriptIngest
from flowlens.core.errors import ContractError
from flowlens.providers.stt.adapter import STTExecutor
from flowlens.providers.stt.execution import execute_attempt
from flowlens.providers.stt.models import STTFailure
from flowlens.providers.stt.provenance import decode, encode, manifest
from flowlens.testing.stt import MockClient, mock_binding, mock_config
from flowlens.testing.stt_worker import RECORDED, MockBridge, produce, setup_bridge
from flowlens.testing.transcripts import TranscriptReferenceTransactions


@pytest.fixture
def boundary(tmp_path):
    bridge, context, evidence = setup_bridge()
    artifact = asyncio.run(produce(bridge))
    transactions = TranscriptReferenceTransactions(tmp_path / "boundary.db")
    transactions.seed(context)
    service = PrivateTranscriptIngest(mock_config(), bridge, evidence)
    return bridge, context, artifact, transactions, service


def counts(transactions):
    with closing(sqlite3.connect(transactions.path)) as conn:
        return tuple(
            conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in (
                "analysis_transcript_raw",
                "analysis_transcript_revisions",
                "reference_records",
                "reference_audit",
                "reference_events",
            )
        )


def accept(boundary, recorded=RECORDED):
    bridge, context, artifact, transactions, service = boundary
    with transactions.begin() as uow:
        result = service.accept(context, artifact.id, recorded, "MOCK", uow)
        uow.commit()
    return result


def test_roundtrip_duplicate_restart_preserves_receipt_time(boundary):
    identifier = accept(boundary)
    bridge, context, artifact, transactions, service = boundary
    before = counts(transactions)
    assert before == (1, 1, 1, 2, 2)
    assert bridge.downloads == 2 and bridge.reserved_ms == 3000
    assert accept(boundary, RECORDED + timedelta(hours=1)) == identifier
    assert counts(transactions) == before
    fresh = TranscriptReferenceTransactions(transactions.path)
    with fresh.begin() as uow:
        segment = service.lifecycle.current_segments(context, uow)[0]
        assert segment.recorded_at == RECORDED and segment.text == "hold"
        assert (segment.start_ms, segment.end_ms) == (2100, 2500)


@pytest.mark.parametrize(
    "change",
    [
        "hypothesis",
        "words",
        "source_time",
        "config",
        "preparation",
        "response_hash",
        "sdk_version",
        "status",
        "chunk_hash",
        "manifest_scope",
        "manifest_hash",
        "manifest_capability",
        "manifest_transform",
        "noncanonical_json",
        "oversize",
    ],
)
def test_tampered_candidate_rejected_before_domain_write(boundary, change):
    bridge, context, artifact, transactions, service = boundary
    raw = RawTranscript.model_validate_json(bridge.artifacts[artifact.id][1])
    if change == "hypothesis":
        raw = raw.model_copy(
            update={"hypotheses": (raw.hypotheses[0].model_copy(update={"text": "cross runway"}),)}
        )
    elif change == "words":
        word = raw.hypotheses[0].words[0].model_copy(update={"confidence": 0.99})
        raw = raw.model_copy(
            update={"hypotheses": (raw.hypotheses[0].model_copy(update={"words": (word,)}),)}
        )
    elif change == "source_time":
        raw = raw.model_copy(
            update={"source_range": raw.source_range.model_copy(update={"start_ns": 1})}
        )
    elif change == "config":
        raw = raw.model_copy(update={"config_json": mock_config(model="short").model_dump_json()})
    elif change == "preparation":
        raw = raw.model_copy(update={"preparation_json": "{}"})
    elif change in {"response_hash", "chunk_hash"}:
        raw = raw.model_copy(update={change: "0" * 64})
    elif change == "sdk_version":
        raw = raw.model_copy(update={"sdk_version": "unverified"})
    elif change == "status":
        raw = raw.model_copy(update={"status": "NO_SPEECH"})
    payload = encode(raw)
    artifact = manifest(bridge.binding, payload)
    if change == "manifest_scope":
        artifact = artifact.model_copy(update={"revision": 2})
    elif change == "manifest_hash":
        artifact = artifact.model_copy(update={"sha256": "0" * 64})
    elif change == "manifest_capability":
        artifact = artifact.model_copy(update={"required_capability": "export"})
    elif change == "manifest_transform":
        artifact = artifact.model_copy(update={"transform_version": "unrelated"})
    elif change == "noncanonical_json":
        payload += b" "
        artifact = manifest(bridge.binding, payload)
    elif change == "oversize":
        payload = b" " * (8 * 1024 * 1024 + 1)
    bridge.artifacts[artifact.id] = artifact, payload
    before = counts(transactions)
    with pytest.raises(ContractError):
        accept(boundary)
    assert counts(transactions) == before


@pytest.mark.parametrize("negative", ["cancel", "late", "stale", "attempt", "rights", "stage"])
@pytest.mark.parametrize("already_accepted", [False, True])
def test_authority_rejects_invalid_and_duplicate_replays(boundary, negative, already_accepted):
    bridge, context, artifact, transactions, service = boundary
    if already_accepted:
        accept(boundary)
    before = counts(transactions)
    binding = bridge.binding
    if negative == "cancel":
        bridge.active = False
    elif negative == "late":
        bridge.binding = binding.model_copy(
            update={"lease": binding.lease.model_copy(update={"expires_ms": 0})}
        )
    elif negative == "stale":
        bridge.binding = binding.model_copy(
            update={"lease": binding.lease.model_copy(update={"revision": 2})}
        )
    elif negative == "attempt":
        bridge.binding = binding.model_copy(
            update={"lease": binding.lease.model_copy(update={"attempt_id": uuid4()})}
        )
    elif negative == "rights":
        bridge.binding = binding.model_copy(update={"cloud_permission": "DENIED"})
    elif negative == "stage":
        bridge.binding = binding.model_copy(
            update={"lease": binding.lease.model_copy(update={"stage": "AUDIO"})}
        )
    with pytest.raises(ContractError):
        accept(boundary)
    assert counts(transactions) == before


@pytest.mark.parametrize("failure", ["evidence", "audit", "event", "no_commit"])
def test_caller_uow_rollback_keeps_staging_for_platform_cleanup(boundary, monkeypatch, failure):
    bridge, context, artifact, transactions, service = boundary
    before = counts(transactions)

    def fail(*args):
        raise RuntimeError("synthetic injected failure")

    def write():
        with transactions.begin() as uow:
            if failure in {"audit", "event"}:
                monkeypatch.setattr(uow, "audit" if failure == "audit" else "enqueue_event", fail)
            if failure == "evidence":
                monkeypatch.setattr(service.lifecycle.evidence, "register", fail)
            service.accept(context, artifact.id, RECORDED, "MOCK", uow)
            if failure != "no_commit":
                uow.commit()

    if failure == "no_commit":
        write()
    else:
        with pytest.raises(RuntimeError):
            write()
    assert counts(transactions) == before and artifact.id in bridge.artifacts


@pytest.mark.parametrize("mode", ["partial", "early", "closed_early", "cancel_after"])
def test_consumer_failure_closes_stream_and_never_reports_success(mode):
    bridge, _, _ = setup_bridge()
    bridge.upload_mode = mode
    with pytest.raises(STTFailure):
        asyncio.run(produce(bridge))
    assert next(bridge.stream, None) is None
    # Uploaded/partial remote data belongs to platform TTL, never worker deletion.
    assert bool(bridge.artifacts) == (mode == "cancel_after")


def test_fresh_attempt_cannot_reuse_previous_artifact(boundary):
    bridge, context, artifact, transactions, service = boundary
    old_raw = RawTranscript.model_validate_json(bridge.artifacts[artifact.id][1])
    bridge.binding = bridge.binding.model_copy(
        update={
            "lease": bridge.binding.lease.model_copy(
                update={"attempt_id": uuid4(), "lease_id": uuid4()}
            )
        }
    )
    new = asyncio.run(produce(bridge))
    new_raw = RawTranscript.model_validate_json(bridge.artifacts[new.id][1])
    from flowlens.analysis.transcript_projection import project

    service.lifecycle.evidence.segments.extend(
        project(new_raw, recorded_at=RECORDED, origin="MOCK")
    )
    assert old_raw.id != new_raw.id and new.id != artifact.id
    with pytest.raises(ContractError):
        accept(boundary)
    with transactions.begin() as uow:
        service.accept(context, new.id, RECORDED, "MOCK", uow)
        uow.commit()
    assert counts(transactions)[0:2] == (1, 1)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cloud_permission", "DENIED"),
        ("local_permission", "UNDETERMINED"),
    ],
)
def test_rights_preflight_prevents_download(field, value):
    bridge, _, _ = setup_bridge()
    bridge.binding = bridge.binding.model_copy(update={field: value})
    with pytest.raises(STTFailure):
        asyncio.run(produce(bridge))
    assert bridge.downloads == 0


def test_bounded_download_hash_and_safe_diagnostic():
    bridge, _, _ = setup_bridge()
    bridge.audio = bridge.audio[:-1] + b"x"
    with pytest.raises(STTFailure, match="STT_AUDIO_INVALID"):
        asyncio.run(produce(bridge))


def test_same_executor_attempt_cannot_trigger_duplicate_rpc():
    bridge, _, _ = setup_bridge()
    client = MockClient()
    executor = STTExecutor(mock_config(), client)

    async def run():
        try:
            await execute_attempt(
                bridge.binding.lease, bridge, bridge, executor, bridge.checkpoint, bridge.reserve
            )
            with pytest.raises(STTFailure, match="STT_DUPLICATE_OR_LIMIT"):
                await execute_attempt(
                    bridge.binding.lease,
                    bridge,
                    bridge,
                    executor,
                    bridge.checkpoint,
                    bridge.reserve,
                )
        finally:
            await executor.close()

    asyncio.run(run())
    assert len(client.requests) == 1 and client.closed


def test_worker_actual_process_import_isolation():
    script = (
        "import sys,json; import flowlens.providers.stt.execution; "
        "print(json.dumps([m for m in sys.modules if m == 'sqlite3' "
        "or m.startswith(('flowlens.storage','flowlens.testing','evaluation'))]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []


def test_private_codec_response_corruption_and_limit(boundary):
    bridge, _, artifact, _, _ = boundary
    raw = RawTranscript.model_validate_json(bridge.artifacts[artifact.id][1])
    raw = raw.model_copy(update={"response_base64": "%%%%"})
    payload = encode(raw)
    with pytest.raises(STTFailure):
        decode(
            mock_config(), bridge.binding, bridge.audio, manifest(bridge.binding, payload), payload
        )


def test_unknown_clock_preserves_raw_without_invented_public_segment(tmp_path):
    binding, audio = mock_binding(mock_config(), offset_ms=None)
    bridge = MockBridge(binding, audio)
    artifact = asyncio.run(produce(bridge))
    context = binding.context.model_copy(update={"capabilities": ["read", "analysis", "audio"]})
    from flowlens.testing.harness import FakePlatform

    service = PrivateTranscriptIngest(mock_config(), bridge, FakePlatform([], []))
    transactions = TranscriptReferenceTransactions(tmp_path / "unknown.db")
    transactions.seed(context)
    with transactions.begin() as uow:
        service.accept(context, artifact.id, RECORDED, "MOCK", uow)
        assert service.lifecycle.current_segments(context, uow) == ()
        uow.commit()
    assert counts(transactions)[0:2] == (1, 0)


@pytest.mark.parametrize(
    "negative",
    [
        "owner",
        "session",
        "run",
        "input_hash",
        "revision",
        "config",
        "asset",
        "stage",
        "approval",
        "index",
        "size",
        "expired",
    ],
)
def test_acquisition_binding_negatives_prevent_download_and_rpc(negative):
    bridge, _, _ = setup_bridge()
    binding = bridge.binding
    lease_changes = {
        "owner": {"owner_id": uuid4()},
        "session": {"session_id": uuid4()},
        "run": {"analysis_run_id": uuid4()},
        "input_hash": {"input_hash": "0" * 64},
        "revision": {"revision": 2},
        "config": {"config_hash": "0" * 64},
        "asset": {"asset_ids": [uuid4()]},
        "stage": {"stage": "AUDIO"},
        "expired": {"expires_ms": 0},
    }
    if negative in lease_changes:
        binding = binding.model_copy(
            update={"lease": binding.lease.model_copy(update=lease_changes[negative])}
        )
    elif negative == "approval":
        binding = binding.model_copy(
            update={"approval": binding.approval.model_copy(update={"data_logging": "UNKNOWN"})}
        )
    elif negative == "index":
        binding = binding.model_copy(update={"chunk_index": 999})
    elif negative == "size":
        chunks = list(binding.preparation.chunks)
        chunks[0] = chunks[0].model_copy(update={"byte_count": 10_000_000})
        binding = binding.model_copy(
            update={"preparation": binding.preparation.model_copy(update={"chunks": tuple(chunks)})}
        )
    bridge.binding = binding
    with pytest.raises(STTFailure):
        asyncio.run(produce(bridge))
    assert bridge.downloads == 0 and bridge.reserved_ms == 0 and not bridge.artifacts


def test_whole_attempt_timeout_covers_download_before_rpc(monkeypatch):
    bridge, _, _ = setup_bridge()
    tick = [0.0]
    import flowlens.providers.stt.execution as worker

    monkeypatch.setattr(worker.time, "monotonic", lambda: tick[0])
    original = bridge.download

    def delayed(*args):
        result = original(*args)
        tick[0] += 31
        return result

    bridge.download = delayed
    with pytest.raises(STTFailure, match="STT_TIMEOUT"):
        asyncio.run(produce(bridge))
    assert bridge.reserved_ms == 0 and not bridge.artifacts


def test_restart_after_accepted_chunk_cannot_duplicate_state(boundary):
    accept(boundary)
    bridge, context, artifact, transactions, service = boundary
    before = counts(transactions)
    bridge.binding = bridge.binding.model_copy(
        update={
            "lease": bridge.binding.lease.model_copy(
                update={"attempt_id": uuid4(), "lease_id": uuid4()}
            )
        }
    )
    new = asyncio.run(produce(bridge))
    with transactions.begin() as uow:
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            service.accept(context, new.id, RECORDED, "MOCK", uow)
    assert counts(transactions) == before
