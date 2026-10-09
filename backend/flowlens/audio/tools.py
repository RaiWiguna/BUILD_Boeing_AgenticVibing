"""Fixed ffprobe/FFmpeg adapters for self-contained local audio containers."""

import json
import math
import re
import shutil
import threading
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from flowlens.audio.models import AudioLimits, ProbeInfo
from flowlens.audio.process import AudioError, run_bounded

FORMATS = "wav,flac,mp3,aiff"


def parse_probe(payload: bytes, limits: AudioLimits) -> ProbeInfo:
    try:
        if len(payload) > 65536:
            raise ValueError
        data = json.loads(payload)
        streams = data["streams"]
        if not isinstance(streams, list) or len(streams) != 1:
            raise ValueError
        if not isinstance(streams[0], dict) or streams[0]["codec_type"] != "audio":
            raise ValueError
        stream = streams[0]
        container = data["format"]
        if not isinstance(container, dict):
            raise ValueError

        def integer(value: Any) -> int:
            if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
                raise ValueError
            return int(value)

        rate = integer(stream["sample_rate"])
        channels = integer(stream["channels"])
        if isinstance(stream.get("duration"), bool) or isinstance(container["duration"], bool):
            raise ValueError
        duration = float(stream["duration"] if "duration" in stream else container["duration"])
        format_duration = float(container["duration"])
        if (
            not math.isfinite(duration)
            or not math.isfinite(format_duration)
            or not 0 < duration <= limits.max_duration_seconds
            or not 0 < format_duration <= limits.max_duration_seconds
            or abs(duration - format_duration) > max(0.001, 1 / rate)
            or not 8000 <= rate <= limits.max_input_rate
            or not 1 <= channels <= limits.max_channels
            or container["format_name"] not in FORMATS.split(",")
            or not re.fullmatch(r"[a-zA-Z0-9_]{1,64}", stream["codec_name"])
        ):
            raise ValueError
        for record in (stream, container):
            if isinstance(record.get("start_time"), bool):
                raise ValueError
            start = float(record.get("start_time", "0"))
            if not math.isfinite(start) or start != 0:
                # Timestamp discontinuities require an explicit mapping adapter.
                raise ValueError
        if "duration_ts" in stream:
            ticks = integer(stream["duration_ts"])
            if abs(float(ticks * Fraction(stream["time_base"])) - duration) > max(0.001, 1 / rate):
                raise ValueError
        return ProbeInfo(
            sample_rate=rate,
            channels=channels,
            duration_seconds=duration,
            codec=stream["codec_name"],
            container=container["format_name"],
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ZeroDivisionError,
        OverflowError,
        RecursionError,
    ):
        raise AudioError("AUDIO_PROBE_INVALID") from None


@dataclass(frozen=True)
class AudioTools:
    """Executables are trusted deployment configuration, never application input."""

    ffmpeg: Path
    ffprobe: Path
    ffmpeg_version: str
    ffprobe_version: str
    cancel: threading.Event | None = None

    @classmethod
    def discover(cls, *, ffmpeg: Path | None = None, ffprobe: Path | None = None) -> "AudioTools":
        resolved: list[Path] = []
        versions: list[str] = []
        for name, configured in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)):
            found = str(configured) if configured is not None else shutil.which(name)
            if not found:
                raise AudioError("AUDIO_BINARY_MISSING")
            path = Path(found).resolve()
            if not path.is_file() or path.suffix.lower() not in ("", ".exe"):
                raise AudioError("AUDIO_BINARY_INVALID")
            output = run_bounded([str(path), "-version"], timeout=10.0, max_bytes=65536)
            match = re.match(rb"(?:ffmpeg|ffprobe) version ([a-zA-Z0-9_.+~:/-]{1,120})", output)
            if match is None or not output.startswith(name.encode() + b" version "):
                raise AudioError("AUDIO_BINARY_INVALID")
            resolved.append(path)
            versions.append(match.group(1).decode("ascii"))
        return cls(resolved[0], resolved[1], versions[0], versions[1])

    def probe(self, source: Path, limits: AudioLimits) -> ProbeInfo:
        payload = run_bounded(
            [
                str(self.ffprobe),
                "-v",
                "error",
                "-max_alloc",
                "67108864",
                "-protocol_whitelist",
                "file",
                "-format_whitelist",
                FORMATS,
                "-show_entries",
                "stream=codec_type,codec_name,sample_rate,channels,duration,duration_ts,time_base,start_time:"
                "format=format_name,duration,start_time",
                "-of",
                "json",
                str(source),
            ],
            timeout=limits.probe_timeout_seconds,
            max_bytes=65536,
            cancel=self.cancel,
        )
        return parse_probe(payload, limits)

    def decode(self, source: Path, target: Path, info: ProbeInfo, limits: AudioLimits) -> None:
        run_bounded(
            [
                str(self.ffmpeg),
                "-nostdin",
                "-hide_banner",
                "-v",
                "error",
                "-xerror",
                "-max_alloc",
                "67108864",
                "-threads",
                "1",
                "-protocol_whitelist",
                "file",
                "-format_whitelist",
                FORMATS,
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-vn",
                "-sn",
                "-dn",
                "-threads",
                "1",
                "-ac",
                str(info.channels),
                "-ar",
                str(limits.output_rate),
                "-c:a",
                "pcm_s16le",
                "-f",
                "s16le",
                "pipe:1",
            ],
            timeout=limits.process_timeout_seconds,
            max_bytes=min(
                limits.max_output_bytes,
                limits.max_duration_seconds * limits.output_rate * info.channels * 2,
            ),
            output=target,
            cancel=self.cancel,
        )
