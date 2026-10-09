"""MOCK SDK/transport acceptance, plus separate actual B02 FFmpeg -> MOCK STT test."""

import ast
import asyncio
import base64
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from flowlens.analysis.transcript_projection import deduplicate, project
from flowlens.audio import AudioTools, prepare_audio
from flowlens.audio.models import AudioLimits, FrameRange
from flowlens.contracts.models import SourceManifest
from flowlens.providers.stt.adapter import STTExecutor, map_response
from flowlens.providers.stt.models import STTFailure
from flowlens.testing.stt import MockClient, mock_binding, mock_config, mock_response
from google.api_core import exceptions as errors
from google.cloud.speech_v2 import types
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def execute(config=None, binding=None, audio=None, client=None, checkpoint=None):
    config = config or mock_config()
    if binding is None:
        binding, audio = mock_binding(config)
    client = client or MockClient()
    executor = STTExecutor(config, client)

    async def run():
        try:
            return await executor.transcribe(
                binding,
                audio,
                checkpoint or (lambda: binding.lease),
                reserve=lambda lease, ms: None,
            )  # MOCK budget
        finally:
            await executor.close()

    return asyncio.run(run()), client, executor


@pytest.mark.parametrize(
    "change",
    [
        {"project": ""},
        {"region": "elsewhere"},
        {"endpoint": "evil.example"},
        {"recognizer": "projects/other/locations/global/recognizers/_"},
        {"recognizer": "projects/mock-project/locations/global/recognizers/../../secret"},
        {"model": ""},
        {"language": "English"},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": 121.0},
        {"max_concurrency": 3},
        {"max_attempts": 4},
        {"max_response_bytes": 1048577},
        {"max_words": 8193},
        {"max_calls": 4097},
        {"store": False},
        {"credential": "secret"},
        {"max_attempts": "1"},
    ],
)
def test_strict_config(change):
    with pytest.raises(ValidationError):
        mock_config(**change)


def test_config_no_effective_default_and_immutable():
    config = mock_config()
    with pytest.raises(ValidationError):
        config.model = "short"
    assert config.digest() != mock_config(model="short").digest()
    assert (
        mock_config(
            region="us",
            endpoint="us-speech.googleapis.com",
            recognizer="projects/mock-project/locations/us/recognizers/_",
        ).region
        == "us"
    )


def test_sdk_request_response_provenance_mapping():
    (raw, usage), client, executor = execute()
    request = client.requests[0]
    assert request.recognizer == "projects/mock-project/locations/us/recognizers/_"
    assert request.config.model == "chirp_3"  # MOCK selection only
    assert list(request.config.language_codes) == ["en-US"]
    assert request.config.features.enable_word_time_offsets is True
    assert request.config.features.enable_word_confidence is False
    assert list(request.config_mask.paths) == ["*"]
    assert request.uri == "" and request.content.startswith(b"RIFF")
    word = raw.hypotheses[0].words[0]
    assert (word.local.start_ns, word.local.end_ns) == (100000000, 500000000)
    assert (word.source.start_ns, word.source.end_ns) == (100000000, 500000000)
    assert (word.session.start_ns, word.session.end_ns) == (2100000000, 2500000000)
    assert word.confidence is None and raw.uncertainty_ms == 5
    binary = base64.b64decode(raw.response_base64)
    assert hashlib.sha256(binary).hexdigest() == raw.response_hash
    assert types.RecognizeResponse.deserialize(binary) == client.response
    assert raw.sdk_version == "2.41.0"
    assert usage.audio_ms == 3000 and usage.cost_microunits is None
    assert executor.attempted_audio_ms == 3000 and client.closed and client.active == 0
    assert "hold" not in repr(raw) and "hold" not in repr(word)
    with pytest.raises(ValidationError):
        raw.hypotheses = ()


@pytest.mark.parametrize("permission", ["DENIED", "UNDETERMINED"])
@pytest.mark.parametrize("field", ["local_permission", "cloud_permission"])
def test_permission_prevents_cloud(field, permission):
    config = mock_config()
    binding, audio = mock_binding(config)
    client = MockClient()
    with pytest.raises(STTFailure, match="STT_PERMISSION_DENIED"):
        execute(config, binding.model_copy(update={field: permission}), audio, client)
    assert client.requests == [] and client.closed


@pytest.mark.parametrize(
    "field,value",
    [
        ("compatibility", "UNVERIFIED"),
        ("api_enabled", False),
        ("identity_authorized", False),
        ("billing_authorized", False),
        ("data_logging", "UNKNOWN"),
        ("data_logging", "ENABLED"),
    ],
)
def test_profile_prevents_cloud(field, value):
    config = mock_config()
    binding, audio = mock_binding(config)
    binding = binding.model_copy(
        update={"approval": binding.approval.model_copy(update={field: value})}
    )
    client = MockClient()
    with pytest.raises(STTFailure):
        execute(config, binding, audio, client)
    assert client.requests == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", uuid4()),
        ("analysis_run_id", uuid4()),
        ("analysis_run_id", None),
        ("revision", 2),
        ("input_hash", "f" * 64),
        ("config_hash", "f" * 64),
        ("owner_id", uuid4()),
        ("asset_ids", []),
        ("stage", "AUDIO"),
        ("budget_microunits", 0),
    ],
)
def test_lease_binding_negatives(field, value):
    config = mock_config()
    binding, audio = mock_binding(config)
    binding = binding.model_copy(update={"lease": binding.lease.model_copy(update={field: value})})
    client = MockClient()
    with pytest.raises(STTFailure):
        execute(config, binding, audio, client)
    assert client.requests == []


@pytest.mark.parametrize(
    "change",
    [
        {"capabilities": ["worker", "audio", "truth"]},
        {"capabilities": ["read", "audio"]},
        {"actor_id": uuid4()},
        {"input_hash": "e" * 64},
    ],
)
def test_context_negatives(change):
    config = mock_config()
    binding, audio = mock_binding(config)
    client = MockClient()
    with pytest.raises(STTFailure):
        execute(
            config,
            binding.model_copy(update={"context": binding.context.model_copy(update=change)}),
            audio,
            client,
        )
    assert not client.requests


@pytest.mark.parametrize(
    "change",
    [
        {"source_after_sha256": "f" * 64},
        {"output_rate": 8000},
        {"config_sha256": "f" * 64},
        {"decoded_frames": 64001},
    ],
)
def test_preparation_binding_negatives(change):
    config = mock_config()
    binding, audio = mock_binding(config)
    client = MockClient()
    with pytest.raises(STTFailure):
        execute(
            config,
            binding.model_copy(
                update={"preparation": binding.preparation.model_copy(update=change)}
            ),
            audio,
            client,
        )
    assert not client.requests


def test_audio_checksum_and_length_prevent_call():
    config = mock_config()
    binding, audio = mock_binding(config)
    for wrong in (audio[:-1], audio + b"x", b"X" + audio[1:]):
        client = MockClient()
        with pytest.raises(STTFailure, match="STT_AUDIO_INVALID"):
            execute(config, binding, wrong, client)
        assert not client.requests


@pytest.mark.parametrize("value", [-1, 1_000_000_000])
def test_bad_duration_nanos(value):
    response = mock_response()
    types.RecognizeResponse.pb(response).results[0].alternatives[0].words[
        0
    ].end_offset.nanos = value
    with pytest.raises(STTFailure, match="STT_OUTPUT_INVALID"):
        execute(client=MockClient(response))


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
@pytest.mark.parametrize("word", [False, True])
def test_bad_confidence(value, word):
    response = mock_response()
    target = (
        response.results[0].alternatives[0].words[0]
        if word
        else response.results[0].alternatives[0]
    )
    target.confidence = value
    with pytest.raises(STTFailure, match="STT_OUTPUT_INVALID"):
        execute(client=MockClient(response))


@pytest.mark.parametrize(
    "case", ["beyond", "reverse", "negative", "unpaired", "channel", "language", "billed"]
)
def test_malformed_outputs(case):
    response = mock_response()
    pb = types.RecognizeResponse.pb(response)
    word = pb.results[0].alternatives[0].words[0]
    if case == "beyond":
        word.end_offset.seconds = 60
    elif case == "reverse":
        word.start_offset.nanos = 600000000
    elif case == "negative":
        word.start_offset.seconds = -1
    elif case == "unpaired":
        word.ClearField("end_offset")
    elif case == "channel":
        pb.results[0].channel_tag = 2
    elif case == "language":
        pb.results[0].language_code = "id-ID"
    else:
        pb.metadata.total_billed_duration.seconds = 3600
    with pytest.raises(STTFailure, match="STT_OUTPUT_INVALID"):
        execute(client=MockClient(response))


def test_unknown_clock_silence_partial_and_zero_sentinel():
    config = mock_config()
    binding, audio = mock_binding(config, offset_ms=None)
    (raw, _), _, _ = execute(config, binding, audio)
    assert raw.session_range is None and raw.hypotheses[0].words[0].session is None
    assert project(raw, recorded_at=datetime.now(UTC), origin="MOCK") == ()
    response = types.RecognizeResponse()
    (silence, usage), _, _ = execute(client=MockClient(response))
    assert silence.status == "NO_SPEECH" and silence.hypotheses == () and usage.audio_ms is None
    response = mock_response()
    response.results[0].alternatives[0].words.clear()
    response.results[0].alternatives[0].confidence = 0
    (partial, _), _, _ = execute(client=MockClient(response))
    assert partial.status == "PARTIAL" and partial.hypotheses[0].confidence is None
    segment = project(partial, recorded_at=datetime.now(UTC), origin="MOCK")[0]
    assert (segment.start_ms, segment.end_ms) == (2000, 5000)
    assert segment.reason == "CHUNK_RANGE_ALIGNMENT_UNKNOWN" and segment.available_time_ms is None


def test_final_short_gap_channels_independent_mapping():
    config = mock_config()
    binding, audio = mock_binding(
        config, frames=96000, channels=2, chunk_index=3, gaps=(FrameRange(start=32000, end=48000),)
    )
    (raw, _), _, _ = execute(config, binding, audio)
    assert raw.channel == 1 and raw.coverage_segment == 1
    assert (raw.source_range.start_ns, raw.source_range.end_ns) == (3000000000, 6000000000)
    assert raw.hypotheses[0].words[0].source.start_ns == 3100000000
    assert raw.hypotheses[0].words[0].session.start_ns == 5100000000
    binding, audio = mock_binding(config, chunk_index=1)
    (short, _), _, _ = execute(config, binding, audio)
    assert (short.source_range.start_ns, short.source_range.end_ns) == (2000000000, 4000000000)


def overlap_records(delta=0, different=False, unknown=False):
    config = mock_config()
    first, _ = mock_binding(config)
    second, _ = mock_binding(config, chunk_index=1)
    # 2.1..2.5s source in both chunks (second starts at source2s).
    response = mock_response()
    pb = types.RecognizeResponse.pb(response)
    pb.results[0].result_end_offset.seconds = 2
    pb.results[0].alternatives[0].words[0].start_offset.seconds = 2
    pb.results[0].alternatives[0].words[0].end_offset.seconds = 2
    other = mock_response(word="short" if different else "hold", start_ns=100000000 + delta)
    if unknown:
        pb.results[0].alternatives[0].words[0].ClearField("start_offset")
        pb.results[0].alternatives[0].words[0].ClearField("end_offset")
    return map_response(config, first, response), map_response(config, second, other)


def test_exact_overlap_preserves_both_provenances():
    records = overlap_records()
    words = deduplicate(records)
    assert len(words) == 1 and len(words[0].references) == 2
    assert words[0].boundary_quality == "EXACT_OVERLAP"
    assert [r.hypotheses[0].text for r in records] == ["hold", "hold"]
    with pytest.raises(ValueError, match="Duplicate"):
        deduplicate((records[0], records[0]))


@pytest.mark.parametrize("fields", [{"delta": 1000}, {"different": True}, {"unknown": True}])
def test_ambiguous_boundary_retained(fields):
    words = deduplicate(overlap_records(**fields))
    assert len(words) == 2 and all(w.boundary_quality == "AMBIGUOUS" for w in words)


def test_genuine_repetition_and_channel_scope_retained():
    config = mock_config()
    first, _ = mock_binding(config)
    second, _ = mock_binding(config, chunk_index=1)
    raws = (
        map_response(config, first, mock_response()),
        map_response(config, second, mock_response()),
    )
    assert len(deduplicate(raws)) == 2  # same utterance at source0.1s and2.1s
    a, b = overlap_records()
    assert len(deduplicate((a, b.model_copy(update={"channel": 1})))) == 2


@pytest.mark.parametrize(
    "error,expected",
    [
        (errors.ResourceExhausted("private audio secret"), "STT_QUOTA"),
        (errors.PermissionDenied("private credential"), "STT_PROVIDER_DENIED"),
        (errors.Unauthenticated("private credential"), "STT_PROVIDER_DENIED"),
        (errors.ServiceUnavailable("private transcript"), "STT_UNAVAILABLE"),
        (RuntimeError("D:/private key audio hold"), "STT_INVALID_OR_UNAVAILABLE"),
    ],
)
def test_failures_safe_and_no_hidden_retry(error, expected):
    client = MockClient(errors=[error])
    with pytest.raises(STTFailure) as caught:
        execute(client=client)
    assert str(caught.value) == expected and len(client.requests) == 1
    assert client.closed and client.active == 0
    assert str(STTFailure("transcript-secret")) == "STT_CONTROL_FAILED"


def test_bounded_retry_and_request_accounting():
    config = mock_config(max_attempts=3, retry_delay_seconds=0.0)
    (_, _), client, executor = execute(
        config,
        client=MockClient(
            errors=[errors.ServiceUnavailable("private"), errors.DeadlineExceeded("private")]
        ),
    )
    assert len(client.requests) == 3 and executor.attempted_audio_ms == 9000
    assert all(r == client.requests[0] for r in client.requests)


@pytest.mark.parametrize(
    "case", ["timeout", "cancel", "deadline", "lease", "lost", "permission", "control"]
)
def test_interrupt_during_rpc(case):
    config = mock_config(timeout_seconds=0.08 if case == "timeout" else 1.0)
    binding, audio = mock_binding(config)
    client = MockClient(delay=0.5)
    started = time.monotonic()

    def checkpoint():
        if client.requests:
            if case == "cancel":
                raise STTFailure("STT_CANCELLED")
            if case == "deadline":
                return binding.lease.model_copy(update={"deadline_ms": 0})
            if case == "lease":
                return binding.lease.model_copy(update={"expires_ms": 0})
            if case == "lost":
                return binding.lease.model_copy(update={"lease_id": uuid4()})
            if case == "permission":
                raise STTFailure("STT_PERMISSION_DENIED")
            if case == "control":
                raise RuntimeError("private key")
        return binding.lease

    with pytest.raises(STTFailure):
        execute(config, binding, audio, client, checkpoint)
    assert client.active == 0 and client.cancelled == 1 and client.closed
    assert time.monotonic() - started < 0.4


def test_concurrency_duplicate_fresh_attempt_and_async_cancellation():
    async def run():
        config = mock_config()
        client = MockClient(delay=0.06)
        executor = STTExecutor(config, client)
        bindings = [mock_binding(config) for _ in range(5)]
        try:
            await asyncio.gather(
                *(
                    executor.transcribe(b, a, lambda b=b: b.lease, reserve=lambda lease, ms: None)
                    for b, a in bindings
                )
            )
            assert client.peak == 2 and executor.calls == 5
            b, a = bindings[0]
            with pytest.raises(STTFailure, match="STT_DUPLICATE_OR_LIMIT"):
                await executor.transcribe(b, a, lambda: b.lease, reserve=lambda lease, ms: None)
            b = b.model_copy(
                update={
                    "lease": b.lease.model_copy(update={"attempt_id": uuid4(), "lease_id": uuid4()})
                }
            )
            task = asyncio.create_task(
                executor.transcribe(b, a, lambda: b.lease, reserve=lambda lease, ms: None)
            )
            await asyncio.sleep(0.02)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert client.active == 0 and client.cancelled == 1
            assert executor.semaphore._value == 2
        finally:
            await executor.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "changes", [{"max_response_bytes": 1}, {"max_text_characters": 1}, {"max_words": 1}]
)
def test_output_caps(changes):
    response = mock_response()
    response.results[0].alternatives[0].words.append(response.results[0].alternatives[0].words[0])
    with pytest.raises(STTFailure, match="STT_OUTPUT_LIMIT"):
        execute(mock_config(**changes), client=MockClient(response))


def test_real_ffmpeg_into_mock_sdk_cleanup(tmp_path):
    config = mock_config()
    template, _ = mock_binding(config)
    source = ROOT / "tests/fixtures/audio/hold-short.wav"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash == "cf3baa73bc59e37ddbd16e99e8a5f7493c22057d01c02b4030585b88486ba044"
    with prepare_audio(
        source=source,
        raw_root=source.parent,
        scratch_root=tmp_path,
        source_id=template.preparation.source_id,
        asset=SourceManifest.model_validate_json(
            (ROOT / "contracts/examples/manifest.json").read_text()
        ).assets[0],
        limits=AudioLimits(),
        clock=template.preparation.clock,
        tools=AudioTools.discover(),
    ) as prepared:
        binding = template.model_copy(update={"preparation": prepared.metadata})
        audio = (prepared.directory / prepared.metadata.chunks[0].filename).read_bytes()
        (raw, _), _, _ = execute(config, binding, audio)
        assert raw.source_hash == source_hash and raw.source_range.end_ns == 8021437500
        directory = prepared.directory
    assert not directory.exists()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash


def test_provider_runtime_boundary_and_standalone():
    forbidden = (
        "sqlite3",
        "flowlens.platform",
        "flowlens.storage",
        "evaluation",
        "flowlens.analysis.transcript_store",
        "flowlens.analysis.repository",
        "flowlens.analysis.transcripts",
    )
    for path in (ROOT / "backend/flowlens/providers/stt").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else ([n.name for n in node.names] if isinstance(node, ast.Import) else [])
            )
            assert all(not n.startswith(forbidden) for n in names)
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy,sys; runpy.run_module('flowlens.testing.stt',run_name='__main__'); "
            "assert not any(n.startswith(('sqlite3','flowlens.platform','evaluation',"
            "'flowlens.analysis.transcript_store','flowlens.analysis.transcripts')) "
            "for n in sys.modules)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["profile"] == "MOCK" and result["provider_calls"] == 0
    assert result["sdk_mock_calls"] == 1 and result["pipeline_ready"] is False


def test_budget_reservation_before_every_attempt():
    async def run():
        config = mock_config(max_attempts=3, retry_delay_seconds=0.0)
        binding, audio = mock_binding(config)
        client = MockClient(errors=[errors.ServiceUnavailable("secret")])
        executor = STTExecutor(config, client)
        reservations = []

        def reserve(lease, ms):
            assert lease == binding.lease and ms == 3000
            reservations.append(ms)
            if len(reservations) == 2:
                raise STTFailure("STT_BUDGET_EXCEEDED")

        try:
            with pytest.raises(STTFailure, match="STT_BUDGET_EXCEEDED"):
                await executor.transcribe(binding, audio, lambda: binding.lease, reserve=reserve)
            assert reservations == [3000, 3000] and executor.calls == 1
            assert executor.attempted_audio_ms == 3000 and len(client.requests) == 1
        finally:
            await executor.close()

    asyncio.run(run())


@pytest.mark.parametrize("kind", ["lease", "deadline"])
def test_initial_expiry_prevents_call(kind):
    config = mock_config()
    binding, audio = mock_binding(config)
    now = time.time_ns() // 1000000
    lease = binding.lease.model_copy(
        update={
            "expires_ms": now - 1,
            "deadline_ms": now - 1 if kind == "deadline" else now + 60000,
        }
    )
    binding = binding.model_copy(update={"lease": lease})
    client = MockClient()
    with pytest.raises(
        STTFailure, match="STT_DEADLINE" if kind == "deadline" else "STT_LEASE_EXPIRED"
    ):
        execute(config, binding, audio, client)
    assert not client.requests


def test_response_alternatives_unknown_word_alignment_and_limits():
    response = mock_response()
    alt = response.results[0].alternatives[0]
    alt.words[0].start_offset = None
    alt.words[0].end_offset = None
    response.results[0].alternatives.append(types.SpeechRecognitionAlternative(transcript="short"))
    (raw, _), _, _ = execute(client=MockClient(response))
    assert raw.status == "PARTIAL" and len(raw.hypotheses) == 2
    assert raw.hypotheses[0].words[0].local is None
    assert raw.hypotheses[1].confidence is None
    with pytest.raises(STTFailure, match="STT_OUTPUT_LIMIT"):
        execute(mock_config(max_hypotheses=1), client=MockClient(response))


def test_request_cap_cleanup_and_restart_does_not_reuse_result():
    async def run():
        config = mock_config(max_calls=1)
        a, bytes_a = mock_binding(config)
        b, bytes_b = mock_binding(config)
        client = MockClient()
        executor = STTExecutor(config, client)
        try:
            await executor.transcribe(a, bytes_a, lambda: a.lease, reserve=lambda lease, ms: None)
            with pytest.raises(STTFailure, match="STT_DUPLICATE_OR_LIMIT"):
                await executor.transcribe(
                    b, bytes_b, lambda: b.lease, reserve=lambda lease, ms: None
                )
            assert executor.calls == 1
        finally:
            await executor.close()
        # Fresh coordinator attempt and executor performs a fresh request, no local spool.
        fresh = a.model_copy(
            update={
                "lease": a.lease.model_copy(update={"attempt_id": uuid4(), "lease_id": uuid4()})
            }
        )
        second = STTExecutor(config, MockClient())
        try:
            raw, _ = await second.transcribe(
                fresh, bytes_a, lambda: fresh.lease, reserve=lambda lease, ms: None
            )
            assert second.calls == 1 and raw.attempt_id != a.lease.attempt_id
        finally:
            await second.close()

    asyncio.run(run())


def test_real_sdk_client_uses_explicit_bounded_channel(monkeypatch):
    from flowlens.providers.stt.adapter import GoogleClient
    from google.auth.credentials import AnonymousCredentials
    from google.cloud.speech_v2.services.speech.transports.grpc_asyncio import (
        SpeechGrpcAsyncIOTransport,
    )

    create = SpeechGrpcAsyncIOTransport.create_channel
    settings = []

    def channel(**kwargs):
        settings.append(kwargs)
        return create(**kwargs)

    monkeypatch.setattr(SpeechGrpcAsyncIOTransport, "create_channel", channel)

    async def run():
        client = GoogleClient(mock_config(), AnonymousCredentials())
        await client.close()

    asyncio.run(run())
    assert settings[0]["host"] == "us-speech.googleapis.com"
    assert settings[0]["options"] == [
        ("grpc.max_receive_message_length", 1048576),
        ("grpc.max_send_message_length", 10010000),
    ]


def test_client_close_failure_diagnostic_safe():
    class FailedClose(MockClient):
        async def close(self):
            raise RuntimeError("D:/private credential hold short")

    with pytest.raises(STTFailure, match="STT_CLIENT_CLOSE_FAILED") as caught:
        execute(client=FailedClose())
    assert str(caught.value) == "STT_CLIENT_CLOSE_FAILED"


def test_semaphore_permit_returned_on_post_acquire_rejection():
    async def run():
        executor = STTExecutor(mock_config(), MockClient())
        count = 0

        def checkpoint():
            nonlocal count
            count += 1
            if count == 2:
                raise STTFailure("STT_CANCELLED")

        try:
            with pytest.raises(STTFailure, match="STT_CANCELLED"):
                await executor.controlled(
                    executor.semaphore.acquire(),
                    checkpoint,
                    time.monotonic() + 1,
                    discard=lambda _: executor.semaphore.release(),
                )
            assert executor.semaphore._value == 2
        finally:
            await executor.close()

    asyncio.run(run())


def test_late_transport_return_cannot_bypass_total_deadline():
    async def run():
        executor = STTExecutor(mock_config(), MockClient())
        try:
            with pytest.raises(STTFailure, match="STT_TIMEOUT"):
                await executor.controlled(asyncio.sleep(0), lambda: None, time.monotonic() - 1)
        finally:
            await executor.close()

    asyncio.run(run())


def test_renewed_expiry_cannot_move_backwards():
    config = mock_config()
    binding, audio = mock_binding(config)
    count = 0

    def checkpoint():
        nonlocal count
        count += 1
        if count == 1:
            return binding.lease.model_copy(update={"expires_ms": binding.lease.expires_ms + 1000})
        return binding.lease

    client = MockClient()
    with pytest.raises(STTFailure, match="STT_LOST_LEASE"):
        execute(config, binding, audio, client, checkpoint)
    assert client.requests == []
