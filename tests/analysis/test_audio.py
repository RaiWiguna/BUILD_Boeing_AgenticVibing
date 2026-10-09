"""B02.1 synthetic tests: real binary smoke is explicitly separate from mocks."""

import ast
import json
import shutil
import struct
import sys
import wave
from pathlib import Path
from uuid import UUID

import pytest
from flowlens.audio import (
    AudioError,
    AudioLimits,
    AudioTools,
    FrameRange,
    plan_chunks,
    prepare_audio,
)
from flowlens.audio.models import ProbeInfo
from flowlens.audio.preparation import digest, local_path
from flowlens.audio.process import run_bounded
from flowlens.audio.tools import parse_probe
from flowlens.contracts.models import Asset, ClockMapping, SourceManifest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
CLOCK = ClockMapping(offset_ms=None, uncertainty_ms=None, timezone="UTC")


def test_chunk_overlap_final_and_exact_mapping():
    plans = plan_chunks(
        decoded_frames=1_616_000,
        source_rate=48000,
        channels=2,
        clock=ClockMapping(offset_ms=125, uncertainty_ms=5, timezone="UTC"),
        limits=AudioLimits(),
    )
    assert len(plans) == 6
    assert [(p.derivative_frames.start, p.derivative_frames.end) for p in plans[:3]] == [
        (0, 800000),
        (784000, 1584000),
        (1568000, 1616000),
    ]
    assert [p.overlap_frames for p in plans[:3]] == [0, 16000, 16000]
    assert plans[1].source_frames == FrameRange(start=2352000, end=4752000)
    assert plans[1].source_start_ms == 49000.0
    assert plans[1].session_start_ms == 49125.0
    assert plans[2].session_end_ms == 101125.0
    assert [p.channel for p in plans] == [0, 0, 0, 1, 1, 1]
    assert plans[2].expected_bytes == 96044


def test_effective_size_includes_header_and_overlap():
    limits = AudioLimits(max_chunk_bytes=1044, overlap_ms=10)
    plans = plan_chunks(
        decoded_frames=1000, source_rate=16000, channels=1, clock=CLOCK, limits=limits
    )
    assert [(p.derivative_frames.start, p.derivative_frames.end) for p in plans] == [
        (0, 500),
        (340, 840),
        (680, 1000),
    ]
    assert all(p.expected_bytes <= 1044 for p in plans)
    assert all(p.session_start_ms is None and p.session_end_ms is None for p in plans)
    assert sum(p.expected_bytes for p in plans) == 2772
    with pytest.raises(ValidationError):
        AudioLimits(max_chunk_bytes=1044)  # effective capacity smaller than overlap


def test_gaps_break_coverage_without_becoming_overlap():
    plans = plan_chunks(
        decoded_frames=160000,
        source_rate=16000,
        channels=1,
        clock=CLOCK,
        limits=AudioLimits(chunk_ms=3000, overlap_ms=1000),
        source_gaps=(FrameRange(start=32000, end=64000), FrameRange(start=144000, end=160000)),
    )
    assert [(p.derivative_frames.start, p.derivative_frames.end) for p in plans] == [
        (0, 32000),
        (64000, 112000),
        (96000, 144000),
    ]
    assert [p.overlap_frames for p in plans] == [0, 0, 16000]
    assert [p.gap_before_source_frames for p in plans] == [0, 32000, 0]
    assert [p.coverage_segment for p in plans] == [0, 1, 1]
    assert (
        plan_chunks(
            decoded_frames=16000,
            source_rate=16000,
            channels=1,
            clock=CLOCK,
            limits=AudioLimits(),
            source_gaps=(FrameRange(start=0, end=16000),),
        )
        == ()
    )  # missing coverage, never fabricated silence-as-observation


@pytest.mark.parametrize(
    "changes",
    [
        {"decoded_frames": 0},
        {"source_rate": 0},
        {"channels": 3},
        {"limits": AudioLimits(max_chunks=1, chunk_ms=500, overlap_ms=0)},
        {"limits": AudioLimits(max_output_bytes=64000)},
        {"source_gaps": (FrameRange(start=100, end=200), FrameRange(start=50, end=60))},
        {"source_gaps": (FrameRange(start=0, end=16001),)},
    ],
)
def test_invalid_plans_and_limits(changes):
    args = dict(
        decoded_frames=16000, source_rate=16000, channels=1, clock=CLOCK, limits=AudioLimits()
    )
    args.update(changes)
    with pytest.raises(ValueError):
        plan_chunks(**args)


def probe_payload():
    return {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "pcm_s16le",
                "sample_rate": "16000",
                "channels": 1,
                "duration": "1.000000",
                "duration_ts": 16000,
                "time_base": "1/16000",
            }
        ],
        "format": {"format_name": "wav", "duration": "1.000000"},
    }


def test_resample_gap_rounding_excludes_intersecting_samples():
    plans = plan_chunks(
        decoded_frames=16000,
        source_rate=48000,
        channels=1,
        clock=CLOCK,
        limits=AudioLimits(),
        source_gaps=(FrameRange(start=4, end=8),),
    )
    # At 3 source frames per output frame, gap [4,8) excludes output frames 1 and 2.
    assert [p.derivative_frames for p in plans] == [
        FrameRange(start=0, end=1),
        FrameRange(start=3, end=16000),
    ]
    assert plans[1].source_frames.start == 9
    assert plans[1].source_start_ms == 0.1875
    assert plans[1].overlap_frames == 0


def test_tools_discovery_versions_are_bounded_and_sanitized(tmp_path, monkeypatch):
    for tool in ("ffmpeg", "ffprobe"):
        (tmp_path / f"{tool}.exe").touch()

    def version(args, **kwargs):
        assert args[1:] == ["-version"]
        assert kwargs == {"timeout": 10.0, "max_bytes": 65536}
        return (Path(args[0]).stem + " version 7.1.2 Copyright\nprivate build paths").encode()

    monkeypatch.setattr("flowlens.audio.tools.run_bounded", version)
    tools = AudioTools.discover(ffmpeg=tmp_path / "ffmpeg.exe", ffprobe=tmp_path / "ffprobe.exe")
    assert tools.ffmpeg_version == tools.ffprobe_version == "7.1.2"
    monkeypatch.setattr(
        "flowlens.audio.tools.run_bounded", lambda *args, **kwargs: b"private malformed"
    )
    with pytest.raises(AudioError, match="AUDIO_BINARY_INVALID"):
        AudioTools.discover(ffmpeg=tmp_path / "ffmpeg.exe", ffprobe=tmp_path / "ffprobe.exe")


def test_probe_validation():
    assert parse_probe(json.dumps(probe_payload()).encode(), AudioLimits()).sample_rate == 16000


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration", "NaN"),
        ("duration", "Infinity"),
        ("duration", "-1"),
        ("duration", "3601"),
        ("sample_rate", "0"),
        ("sample_rate", "16000.1"),
        ("sample_rate", True),
        ("channels", 3),
        ("channels", 0),
        ("codec_type", "video"),
        ("duration_ts", 1),
        ("time_base", "1/0"),
        ("start_time", "NaN"),
        ("start_time", "0.1"),
        ("codec_name", "private\npath"),
    ],
)
def test_malformed_stream(field, value):
    payload = probe_payload()
    payload["streams"][0][field] = value
    with pytest.raises(AudioError, match="AUDIO_PROBE_INVALID"):
        parse_probe(json.dumps(payload).encode(), AudioLimits())


@pytest.mark.parametrize(
    "payload",
    [b"{}", b"not json", b"[]", b"null", b'{"streams": []}', b'{"streams": [null], "format": {}}'],
)
def test_malformed_probe_shape(payload):
    with pytest.raises(AudioError, match="AUDIO_PROBE_INVALID"):
        parse_probe(payload, AudioLimits())


def test_inconsistent_container_and_multiple_streams():
    for field, value in (("duration", "2"), ("format_name", "hls"), ("start_time", "1")):
        payload = probe_payload()
        payload["format"][field] = value
        with pytest.raises(AudioError):
            parse_probe(json.dumps(payload).encode(), AudioLimits())
    payload = probe_payload()
    payload["streams"] *= 2
    with pytest.raises(AudioError):
        parse_probe(json.dumps(payload).encode(), AudioLimits())


@pytest.fixture
def local_audio(tmp_path):
    raw = tmp_path / "raw"
    scratch = tmp_path / "scratch"
    raw.mkdir()
    scratch.mkdir()
    source = raw / "-input ; $(no-shell).wav"
    with wave.open(str(source), "wb") as stream:
        stream.setparams((2, 2, 16000, 16000, "NONE", "not compressed"))
        stream.writeframes(struct.pack("<hh", 1000, -2000) * 16000)
    asset = Asset(
        id=UUID(int=10),
        sha256=digest(source),
        duration_ms=1000,
        channels=2,
        sample_rate_hz=16000,
        media_type="audio/wav",
        fixture_path=None,
    )
    return dict(
        source=source,
        raw_root=raw,
        scratch_root=scratch,
        source_id=UUID(int=6),
        asset=asset,
        clock=CLOCK,
    )


@pytest.fixture
def mocked_tools(monkeypatch):
    """MOCK decode copies synthetic PCM; this is not an FFmpeg smoke."""

    def probe(self, source, limits):
        return ProbeInfo(
            sample_rate=16000, channels=2, duration_seconds=1.0, codec="pcm_s16le", container="wav"
        )

    def decode(self, source, target, info, limits):
        with wave.open(str(source), "rb") as stream:
            target.write_bytes(stream.readframes(stream.getnframes()))

    monkeypatch.setattr(AudioTools, "probe", probe)
    monkeypatch.setattr(AudioTools, "decode", decode)
    return AudioTools(Path("mock-ffmpeg"), Path("mock-ffprobe"), "MOCK", "MOCK")


def test_materialization_channels_hashes_and_cleanup(local_audio, mocked_tools):
    before = digest(local_audio["source"])
    with prepare_audio(**local_audio, tools=mocked_tools) as result:
        work = result.directory
        metadata = result.metadata
        assert metadata.decoded_frames == 16000
        assert metadata.source_after_sha256 == metadata.source_sha256 == before
        assert metadata.clock.offset_ms is None
        assert metadata.config_sha256 == AudioLimits().digest()
        for chunk, expected in zip(metadata.chunks, (1000, -2000), strict=True):
            output = work / chunk.filename
            assert digest(output) == chunk.sha256
            assert chunk.byte_count == 32044
            with wave.open(str(output), "rb") as stream:
                assert (
                    stream.getnchannels(),
                    stream.getsampwidth(),
                    stream.getframerate(),
                    stream.getnframes(),
                ) == (1, 2, 16000, 16000)
                assert stream.readframes(1) == struct.pack("<h", expected)
    assert not work.exists()
    assert list(local_audio["scratch_root"].iterdir()) == []
    assert digest(local_audio["source"]) == before


def test_materialization_gap_short_chunks_and_consumer_cleanup(local_audio, mocked_tools):
    limits = AudioLimits(chunk_ms=500, overlap_ms=100)
    with (
        pytest.raises(RuntimeError, match="consumer"),
        prepare_audio(
            **local_audio,
            tools=mocked_tools,
            limits=limits,
            source_gaps=(FrameRange(start=4000, end=8000),),
        ) as result,
    ):
        chunks = result.metadata.chunks
        assert len(chunks) == 4
        assert [c.local_frames.end for c in chunks] == [4000, 8000, 4000, 8000]
        assert chunks[1].plan.gap_before_source_frames == 4000
        assert chunks[1].plan.overlap_frames == 0
        raise RuntimeError("consumer")
    assert not list(local_audio["scratch_root"].iterdir())


@pytest.mark.parametrize("failure", ["probe", "decode", "partial", "duration", "mutation", "write"])
def test_failure_cleanup_and_no_success(local_audio, mocked_tools, monkeypatch, failure):
    def fail_probe(*args):
        raise AudioError("AUDIO_PROBE_INVALID")

    def fail_decode(self, source, target, info, limits):
        target.write_bytes(b"partial")
        if failure == "decode":
            raise AudioError("AUDIO_TIMEOUT")
        if failure == "partial":
            return
        if failure == "duration":
            target.write_bytes(b"\0" * 4)
        if failure == "mutation":
            target.write_bytes(struct.pack("<hh", 1, 2) * 16000)
            local_audio["source"].write_bytes(b"changed by external actor")

    if failure == "probe":
        monkeypatch.setattr(AudioTools, "probe", fail_probe)
    elif failure == "write":
        monkeypatch.setattr(
            wave.Wave_write,
            "writeframesraw",
            lambda *args: (_ for _ in ()).throw(OSError("private path disk full")),
        )
    else:
        monkeypatch.setattr(AudioTools, "decode", fail_decode)
    with pytest.raises(AudioError) as error, prepare_audio(**local_audio, tools=mocked_tools):
        pytest.fail("Partial preparation must never yield success")
    assert "private" not in str(error.value)
    assert not list(local_audio["scratch_root"].iterdir())


@pytest.mark.parametrize(
    "bad",
    [
        "https://example.org/a.wav",
        "file:///private/a.wav",
        "../input.wav",
        "//server/share/a.wav",
        "\\\\server\\share\\a.wav",
        "-protocol_whitelist",
        "pipe:0",
    ],
)
def test_network_argument_and_relative_paths_rejected(local_audio, mocked_tools, bad):
    local_audio["source"] = Path(bad)
    with (
        pytest.raises(AudioError, match="AUDIO_PATH_INVALID"),
        prepare_audio(
            **local_audio,
            tools=mocked_tools,
        ),
    ):
        pytest.fail("Unsafe input accepted")


def test_path_scope_aliases_and_raw_output_rejected(local_audio, mocked_tools, tmp_path):
    with pytest.raises(AudioError):
        local_path(local_audio["source"], local_audio["scratch_root"])
    alias = local_audio["raw_root"] / "alias.wav"
    alias.hardlink_to(local_audio["source"])
    with pytest.raises(AudioError):
        local_path(alias, local_audio["raw_root"])
    alias.unlink()
    local_audio["scratch_root"] = local_audio["raw_root"]
    with (
        pytest.raises(AudioError, match="AUDIO_PATH_INVALID"),
        prepare_audio(
            **local_audio,
            tools=mocked_tools,
        ),
    ):
        pytest.fail("Raw directory accepted as scratch")


def test_invalid_input_hash_magic_metadata_and_size(local_audio, mocked_tools):
    for changes, expected in (
        ({"limits": AudioLimits(max_input_bytes=1)}, "AUDIO_INPUT_LIMIT"),
        (
            {"asset": local_audio["asset"].model_copy(update={"sha256": "a" * 64})},
            "AUDIO_SOURCE_CHANGED",
        ),
        (
            {"asset": local_audio["asset"].model_copy(update={"duration_ms": 100})},
            "AUDIO_ASSET_MISMATCH",
        ),
    ):
        with (
            pytest.raises(AudioError, match=expected),
            prepare_audio(
                **(local_audio | changes),
                tools=mocked_tools,
            ),
        ):
            pytest.fail("Invalid input accepted")
    local_audio["source"].write_bytes(b"#EXTM3U\nhttps://private.example/asset")
    local_audio["asset"] = local_audio["asset"].model_copy(
        update={"sha256": digest(local_audio["source"])}
    )
    with (
        pytest.raises(AudioError, match="AUDIO_CONTAINER_INVALID"),
        prepare_audio(
            **local_audio,
            tools=mocked_tools,
        ),
    ):
        pytest.fail("Network playlist accepted")


def test_real_subprocess_limits_and_safe_errors(tmp_path, monkeypatch):
    # Actual local subprocesses test the runner; these are not audio decode tests.
    with pytest.raises(AudioError, match="AUDIO_BINARY_MISSING"):
        run_bounded([str(tmp_path / "missing.exe")], timeout=1.0, max_bytes=100)
    with pytest.raises(AudioError, match="AUDIO_TIMEOUT"):
        run_bounded(
            [sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.1, max_bytes=100
        )
    with pytest.raises(AudioError, match="AUDIO_PROCESS_FAILED") as error:
        run_bounded(
            [sys.executable, "-c", "import sys; sys.stderr.write('private payload'); sys.exit(3)"],
            timeout=5.0,
            max_bytes=100,
        )
    assert "private" not in str(error.value)
    with pytest.raises(AudioError, match="AUDIO_OUTPUT_LIMIT_OR_IO"):
        run_bounded(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x'*1000000)"],
            timeout=5.0,
            max_bytes=100,
            output=tmp_path / "bounded.pcm",
        )
    assert (tmp_path / "bounded.pcm").stat().st_size <= 100
    assert (
        run_bounded(
            [sys.executable, "-c", "import sys; sys.stderr.write('x'*1000000); print('ok')"],
            timeout=5.0,
            max_bytes=10,
        ).strip()
        == b"ok"
    )
    existing = tmp_path / "existing.pcm"
    existing.write_bytes(b"immutable")
    with pytest.raises(AudioError, match="AUDIO_OUTPUT_LIMIT_OR_IO"):
        run_bounded(
            [sys.executable, "-c", "print('replacement')"],
            timeout=5.0,
            max_bytes=100,
            output=existing,
        )
    assert existing.read_bytes() == b"immutable"
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(AudioError, match="AUDIO_BINARY_MISSING"):
        AudioTools.discover()


def test_fixed_adapter_arguments(tmp_path, monkeypatch):
    calls = []

    def record(args, **kwargs):
        calls.append((args, kwargs))
        return json.dumps(probe_payload()).encode()

    monkeypatch.setattr("flowlens.audio.tools.run_bounded", record)
    tools = AudioTools(Path("ffmpeg.exe"), Path("ffprobe.exe"), "TEST", "TEST")
    source = tmp_path / "input.audio"
    info = tools.probe(source, AudioLimits())
    tools.decode(source, tmp_path / "decoded.pcm", info, AudioLimits())
    for args, kwargs in calls:
        assert args[args.index("-protocol_whitelist") + 1] == "file"
        assert args[args.index("-format_whitelist") + 1] == "wav,flac,mp3,aiff"
        assert kwargs["timeout"] > 0
        assert kwargs["max_bytes"] > 0
    assert "-nostdin" in calls[1][0]
    assert calls[1][0][-1] == "pipe:1"


@pytest.mark.parametrize("fixture,output_rate", [("hold-short.wav", 8000), ("silence.wav", 16000)])
def test_real_ffmpeg_smoke(tmp_path, fixture, output_rate):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("REAL FFMPEG BLOCKER: ffmpeg/ffprobe unavailable on PATH")
    tools = AudioTools.discover()
    manifest = SourceManifest.model_validate_json(
        (ROOT / "tests/fixtures/manifests/synthetic-audio.json").read_text()
    )
    raw = tmp_path / "raw"
    scratch = tmp_path / "scratch"
    raw.mkdir()
    scratch.mkdir()
    source = raw / fixture
    shutil.copyfile(ROOT / "tests/fixtures/audio" / fixture, source)
    with wave.open(str(source), "rb") as reader:
        duration_ms = round(reader.getnframes() * 1000 / reader.getframerate())
        raw_frames, raw_rate = reader.getnframes(), reader.getframerate()
    asset = (
        manifest.assets[0]
        if fixture == "hold-short.wav"
        else Asset(
            id=UUID(int=11),
            sha256=digest(source),
            duration_ms=duration_ms,
            channels=1,
            sample_rate_hz=16000,
            media_type="audio/wav",
            fixture_path=None,
        )
    )
    limits = AudioLimits(output_rate=output_rate, chunk_ms=3000, overlap_ms=500)
    with prepare_audio(
        source=source,
        raw_root=raw,
        scratch_root=scratch,
        source_id=manifest.id,
        asset=asset,
        clock=manifest.clock,
        tools=tools,
        limits=limits,
    ) as result:
        metadata = result.metadata
        assert metadata.ffmpeg_version != "MOCK"
        assert metadata.probe.container == "wav" and metadata.probe.codec == "pcm_s16le"
        assert metadata.probe.channels == 1 and metadata.probe.sample_rate == 16000
        assert metadata.decoded_frames == (raw_frames * output_rate + raw_rate - 1) // raw_rate
        expected_boundaries = (
            [(0, 24000), (20000, 44000), (40000, 64000), (60000, 64172)]
            if fixture == "hold-short.wav"
            else [(0, 16000)]
        )
        assert [
            (chunk.plan.derivative_frames.start, chunk.plan.derivative_frames.end)
            for chunk in metadata.chunks
        ] == expected_boundaries
        assert abs(metadata.decoded_frames / output_rate * 1000 - duration_ms) <= 1
        assert metadata.chunks[-1].plan.derivative_frames.end == metadata.decoded_frames
        for chunk in metadata.chunks:
            with wave.open(str(result.directory / chunk.filename), "rb") as reader:
                assert reader.getframerate() == output_rate
                assert reader.getnchannels() == 1
                assert reader.getsampwidth() == 2
                assert reader.getnframes() == chunk.local_frames.end
            assert chunk.byte_count <= limits.max_chunk_bytes
            assert digest(result.directory / chunk.filename) == chunk.sha256
            assert chunk.plan.channel == 0
            assert (
                chunk.plan.source_start_ms
                == chunk.plan.derivative_frames.start * 1000 / output_rate
            )
            assert chunk.plan.session_start_ms == (
                None
                if manifest.clock.offset_ms is None
                else chunk.plan.source_start_ms + manifest.clock.offset_ms
            )
        assert digest(source) == asset.sha256
    assert not list(scratch.iterdir())


def test_audio_runtime_boundary():
    for file in (ROOT / "backend/flowlens/audio").glob("*.py"):
        tree = ast.parse(file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                assert not module.startswith(
                    ("evaluation", "sqlite3", "flowlens.storage", "flowlens.testing")
                )
                if module.startswith("flowlens."):
                    assert module.startswith(("flowlens.audio", "flowlens.contracts.models"))
        assert not any(
            token in file.read_text() for token in ("evaluation/fixtures", "gold_transcript")
        )
