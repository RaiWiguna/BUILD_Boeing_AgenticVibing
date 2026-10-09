"""Private scratch preparation, yielding results only after complete verification."""

import hashlib
import os
import wave
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from flowlens.audio.models import (
    AudioLimits,
    ChunkMetadata,
    FrameRange,
    PreparationMetadata,
)
from flowlens.audio.planning import plan_chunks
from flowlens.audio.process import AudioError
from flowlens.audio.tools import AudioTools
from flowlens.contracts.models import Asset, ClockMapping

DEFAULT_LIMITS = AudioLimits()


def digest(
    path: Path,
    *,
    checkpoint: Callable[[], None] = lambda: None,
    max_bytes: int | None = None,
) -> str:
    with path.open("rb") as stream:
        checksum = hashlib.sha256()
        count = 0
        while block := stream.read(65536):
            checkpoint()
            count += len(block)
            if max_bytes is not None and count > max_bytes:
                raise AudioError("AUDIO_INPUT_LIMIT")
            checksum.update(block)
        return checksum.hexdigest()


def local_path(path: Path, root: Path, *, directory: bool = False) -> Path:
    """Roots are private, trusted caller configuration; no URL/UNC/ADS/symlinks."""
    try:
        text = str(path)
        if (
            not path.is_absolute()
            or text.startswith(("\\\\", "//"))
            or ":" in text[len(path.anchor) :]
            or any(ord(char) < 32 for char in text)
            or ".." in path.parts
            or any(part.is_symlink() or part.is_junction() for part in (path, *path.parents))
        ):
            raise ValueError
        resolved = path.resolve(strict=True)
        private = root.resolve(strict=True)
        if not resolved.is_relative_to(private) or resolved == private and not directory:
            raise ValueError
        if directory:
            if not resolved.is_dir():
                raise ValueError
        elif not resolved.is_file() or resolved.stat().st_nlink != 1:
            raise ValueError
        return resolved
    except (OSError, ValueError):
        raise AudioError("AUDIO_PATH_INVALID") from None


def check_magic(path: Path) -> None:
    with path.open("rb") as stream:
        head = stream.read(12)
    valid = (
        head[:4] in (b"RIFF", b"RF64")
        and head[8:12] == b"WAVE"
        or head[:4] == b"fLaC"
        or head[:4] == b"FORM"
        and head[8:12] in (b"AIFF", b"AIFC")
        or head[:3] == b"ID3"
        or len(head) >= 2
        and head[0] == 255
        and head[1] & 0xE0 == 0xE0
    )
    if not valid:
        raise AudioError("AUDIO_CONTAINER_INVALID")


@dataclass(frozen=True)
class PreparedAudio:
    """Paths exist only inside the prepare_audio context; no platform promotion."""

    directory: Path
    metadata: PreparationMetadata


@contextmanager
def prepare_audio(
    *,
    source: Path,
    raw_root: Path,
    scratch_root: Path,
    source_id: UUID,
    asset: Asset,
    clock: ClockMapping,
    tools: AudioTools,
    limits: AudioLimits = DEFAULT_LIMITS,
    source_gaps: tuple[FrameRange, ...] = (),
    checkpoint: Callable[[], None] = lambda: None,
) -> Iterator[PreparedAudio]:
    """Caller supplies authorized local asset and source-relative coverage only.

    No manifest labels, evaluator oracle, database, network or provider input is
    accepted here. Clock carries its mapping version/uncertainty unchanged.
    """
    try:
        checkpoint()
        limits = AudioLimits.model_validate_json(limits.model_dump_json())
        asset = Asset.model_validate_json(asset.model_dump_json())
        clock = ClockMapping.model_validate_json(clock.model_dump_json())
        raw = local_path(source, raw_root)
        scratch = local_path(scratch_root, scratch_root, directory=True)
        raw_base = raw_root.resolve(strict=True)
        if scratch.is_relative_to(raw_base) or raw_base.is_relative_to(scratch):
            raise AudioError("AUDIO_PATH_INVALID")
        if not 0 < raw.stat().st_size <= limits.max_input_bytes:
            raise AudioError("AUDIO_INPUT_LIMIT")
        before = digest(raw, checkpoint=checkpoint, max_bytes=limits.max_input_bytes)
        if before != asset.sha256:
            raise AudioError("AUDIO_SOURCE_CHANGED")
        with TemporaryDirectory(prefix="flowlens-audio-", dir=scratch) as name:
            work = Path(name)
            if os.name != "nt":
                work.chmod(0o700)
            # Snapshot a bounded input so decoder never opens the immutable raw path.
            snapshot = work / "input.audio"
            with raw.open("rb") as reader, snapshot.open("xb") as writer:
                count = 0
                while block := reader.read(65536):
                    checkpoint()
                    count += len(block)
                    if count > limits.max_input_bytes:
                        raise AudioError("AUDIO_INPUT_LIMIT")
                    writer.write(block)
            if digest(snapshot, checkpoint=checkpoint, max_bytes=limits.max_input_bytes) != before:
                raise AudioError("AUDIO_SOURCE_CHANGED")
            check_magic(snapshot)
            info = tools.probe(snapshot, limits)
            expected_container = {
                "audio/wav": "wav",
                "audio/flac": "flac",
                "audio/mpeg": "mp3",
                "audio/aiff": "aiff",
            }[asset.media_type]
            if (
                info.sample_rate != asset.sample_rate_hz
                or info.channels != asset.channels
                or info.container != expected_container
                or abs(info.duration_seconds * 1000 - asset.duration_ms) > 1.0
            ):
                raise AudioError("AUDIO_ASSET_MISMATCH")
            pcm = work / "decoded.pcm"
            tools.decode(snapshot, pcm, info, limits)
            checkpoint()
            size = pcm.stat().st_size
            frame_bytes = info.channels * 2
            frames = size // frame_bytes
            if (
                size == 0
                or size % frame_bytes
                or size > limits.max_output_bytes
                or abs(frames / limits.output_rate - info.duration_seconds)
                > 1 / limits.output_rate + 0.000001
            ):
                raise AudioError("AUDIO_DECODE_INVALID")
            plans = plan_chunks(
                decoded_frames=frames,
                source_rate=info.sample_rate,
                channels=info.channels,
                clock=clock,
                limits=limits,
                source_gaps=source_gaps,
            )
            chunks: list[ChunkMetadata] = []
            with pcm.open("rb") as reader:
                for index, plan in enumerate(plans):
                    checkpoint()
                    filename = f"chunk-{index:04d}.wav"
                    target = work / filename
                    count = plan.derivative_frames.end - plan.derivative_frames.start
                    reader.seek(plan.derivative_frames.start * frame_bytes)
                    # Fixed generated filename in an exclusive private scratch directory.
                    with target.open("xb") as sink, wave.open(sink, "wb") as writer:
                        writer.setparams(
                            (1, 2, limits.output_rate, count, "NONE", "not compressed")
                        )
                        remaining = count
                        while remaining:
                            checkpoint()
                            take = min(remaining, 32768)
                            block = reader.read(take * frame_bytes)
                            if len(block) != take * frame_bytes:
                                raise AudioError("AUDIO_DECODE_INVALID")
                            channel = plan.channel * 2
                            mono = bytearray(take * 2)
                            mono[0::2] = block[channel::frame_bytes]
                            mono[1::2] = block[channel + 1 :: frame_bytes]
                            writer.writeframesraw(mono)
                            remaining -= take
                    if target.stat().st_size != plan.expected_bytes:
                        raise AudioError("AUDIO_DECODE_INVALID")
                    chunks.append(
                        ChunkMetadata(
                            filename=filename,
                            plan=plan,
                            sha256=digest(target, checkpoint=checkpoint),
                            byte_count=target.stat().st_size,
                            local_frames=FrameRange(start=0, end=count),
                        )
                    )
            after = digest(raw, checkpoint=checkpoint, max_bytes=limits.max_input_bytes)
            checkpoint()
            if after != before:
                raise AudioError("AUDIO_SOURCE_CHANGED")
            metadata = PreparationMetadata(
                source_id=source_id,
                asset_id=asset.id,
                source_sha256=before,
                source_after_sha256=after,
                probe=info,
                decoded_frames=frames,
                output_rate=limits.output_rate,
                decoded_sha256=digest(pcm, checkpoint=checkpoint),
                clock=clock,
                source_gaps=source_gaps,
                config=limits,
                config_sha256=limits.digest(),
                ffmpeg_version=tools.ffmpeg_version,
                ffprobe_version=tools.ffprobe_version,
                chunks=tuple(chunks),
            )
            yield PreparedAudio(work, metadata)
    except AudioError:
        raise
    except (OSError, ValueError, wave.Error):
        raise AudioError("AUDIO_PREPARATION_FAILED") from None
