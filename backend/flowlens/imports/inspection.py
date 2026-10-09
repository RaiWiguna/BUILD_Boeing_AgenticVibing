"""Bounded audio decoder subprocess and explicit canonical sidecar profiles."""

import csv
import io
import json
import math
import os
import resource
import struct
import subprocess
import sys
from collections.abc import Iterator
from typing import Literal

from flowlens.contracts.models import SourceEvent, Track
from pydantic import BaseModel, ConfigDict, ValidationError


class InvalidContent(Exception):
    def __init__(self, code: str, row: int | None = None) -> None:
        self.code, self.row = code, row
        super().__init__(code)


class AudioFacts(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    frames: int
    channels: int
    sample_rate_hz: int
    duration_ms: int


def wav_container(fd: int) -> None:
    size = os.fstat(fd).st_size
    header = os.pread(fd, 12, 0)
    if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"WAVE":
        raise InvalidContent("CONTENT_MISMATCH")
    if struct.unpack_from("<I", header, 4)[0] + 8 != size:
        raise InvalidContent("INVALID_AUDIO")
    offset = 12
    kinds: list[bytes] = []
    while offset < size:
        chunk = os.pread(fd, 8, offset)
        if len(chunk) != 8:
            raise InvalidContent("INVALID_AUDIO")
        length = struct.unpack_from("<I", chunk, 4)[0]
        offset += 8 + length + length % 2
        if offset > size:
            raise InvalidContent("INVALID_AUDIO")
        if len(kinds) >= 128 or (chunk[:4] != b"data" and length > 16 * 1024**2):
            raise InvalidContent("AUDIO_METADATA_LIMIT")
        kinds.append(chunk[:4])
    if kinds.count(b"fmt ") != 1 or kinds.count(b"data") != 1:
        raise InvalidContent("INVALID_AUDIO")


def decode(fd: int, kind: str, max_duration: int) -> AudioFacts:
    import soundfile  # type: ignore[import-untyped]

    if kind == "wav":
        wav_container(fd)
    else:
        if os.pread(fd, 4, 0) != b"fLaC":
            raise InvalidContent("CONTENT_MISMATCH")
        offset = 4
        for index in range(128):
            header = os.pread(fd, 4, offset)
            if len(header) != 4:
                raise InvalidContent("INVALID_AUDIO")
            length = int.from_bytes(header[1:], "big")
            block_type = header[0] & 127
            if index == 0 and (block_type != 0 or length != 34):
                raise InvalidContent("INVALID_AUDIO")
            offset += 4 + length
            if offset > os.fstat(fd).st_size:
                raise InvalidContent("INVALID_AUDIO")
            if offset > 16 * 1024**2:
                raise InvalidContent("AUDIO_METADATA_LIMIT")
            if header[0] & 128:
                break
        else:
            raise InvalidContent("AUDIO_METADATA_LIMIT")
    os.lseek(fd, 0, os.SEEK_SET)
    try:
        with soundfile.SoundFile(fd, closefd=False) as audio:
            if audio.format not in (("WAV", "WAVEX") if kind == "wav" else ("FLAC",)):
                raise InvalidContent("CONTENT_MISMATCH")
            if audio.channels not in (1, 2):
                raise InvalidContent("CHANNEL_LIMIT")
            if not 8000 <= audio.samplerate <= 192000:
                raise InvalidContent("SAMPLE_RATE_LIMIT")
            if audio.frames <= 0:
                raise InvalidContent("EMPTY_AUDIO")
            if audio.frames * 1000 > max_duration * audio.samplerate:
                raise InvalidContent("DURATION_LIMIT")
            if audio.subtype not in ("PCM_U8", "PCM_16", "PCM_24", "PCM_32", "FLOAT", "DOUBLE"):
                raise InvalidContent("UNSUPPORTED_AUDIO_ENCODING")
            count = 0
            while count < audio.frames:
                data = audio.buffer_read(min(8192, audio.frames - count), dtype="float64")
                if not data or len(data) % (audio.channels * 8):
                    raise InvalidContent("INVALID_AUDIO")
                if any(not math.isfinite(value) for value in memoryview(data).cast("d")):
                    raise InvalidContent("NONFINITE_AUDIO")
                count += len(data) // (audio.channels * 8)
            return AudioFacts(
                frames=count,
                channels=audio.channels,
                sample_rate_hz=audio.samplerate,
                duration_ms=max(1, (count * 1000 + audio.samplerate // 2) // audio.samplerate),
            )
    except InvalidContent:
        raise
    except (soundfile.SoundFileError, ValueError, OSError):
        raise InvalidContent("INVALID_AUDIO") from None


def inspect_audio(fd: int, kind: str, max_duration: int, timeout: int) -> AudioFacts:
    # Only an already authorized private fd crosses the process boundary; no user path/shell.
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "flowlens.imports.inspection",
                str(fd),
                kind,
                str(max_duration),
                str(timeout),
            ],
            pass_fds=(fd,),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
            env={
                "PATH": os.defpath,
                "LANG": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
            },
        )
    except subprocess.TimeoutExpired:
        raise InvalidContent("DECODER_TIMEOUT") from None
    if result.returncode or len(result.stdout) > 1024:
        raise InvalidContent("DECODER_FAILED")
    try:
        message = json.loads(result.stdout)
        if "error" in message:
            raise InvalidContent(message["error"])
        return AudioFacts.model_validate(message)
    except (ValueError, TypeError, ValidationError):
        raise InvalidContent("DECODER_FAILED") from None


def finite(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise InvalidContent("NONFINITE_NUMBER")
    return number


def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in values:
        if key in output:
            raise InvalidContent("DUPLICATE_FIELD")
        output[key] = value
    return output


def strict_json(text: str) -> object:
    try:
        return json.loads(
            text,
            object_pairs_hook=pairs,
            parse_float=finite,
            parse_constant=lambda value: (_ for _ in ()).throw(InvalidContent("NONFINITE_NUMBER")),
        )
    except (ValueError, RecursionError):
        raise InvalidContent("MALFORMED_JSON") from None


def records(
    fd: int, extension: str, role: Literal["events", "tracks"], max_rows: int
) -> Iterator[SourceEvent | Track]:
    os.lseek(fd, 0, os.SEEK_SET)
    count = 0
    model = Track if role == "tracks" else SourceEvent
    seen: set[str] = set()
    try:
        with io.TextIOWrapper(
            io.FileIO(fd, mode="rb", closefd=False), encoding="utf-8", newline=""
        ) as stream:
            iterator: Iterator[object]
            if extension == "json":
                if os.fstat(fd).st_size > 8 * 1024**2:
                    raise InvalidContent("JSON_SIZE_LIMIT")
                data = strict_json(stream.read())
                iterator = iter(data if isinstance(data, list) else [data])
            elif extension == "jsonl":
                iterator = (strict_json(line) for line in stream if line.strip())
            else:
                reader = csv.DictReader(stream, strict=True)
                headers = reader.fieldnames or []
                required = set(Track.model_fields) - {"schema_version"}
                if len(headers) != len(set(headers)):
                    raise InvalidContent("DUPLICATE_FIELD")
                if set(headers) not in (
                    required | {"units"},
                    required | {"units", "schema_version"},
                ):
                    raise InvalidContent("CSV_PROFILE_REQUIRED")

                def csv_rows() -> Iterator[object]:
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):
                            raise InvalidContent("SCHEMA_MISMATCH")
                        if row.pop("units") != "m":
                            raise InvalidContent("UNKNOWN_UNITS")
                        converted: dict[str, object] = dict(row)
                        for field in ("event_time_ms", "available_time_ms", "revision", "age_ms"):
                            value = row[field]
                            converted[field] = (
                                None if value == "" and field == "available_time_ms" else int(value)
                            )
                        for field in (
                            "x_m",
                            "y_m",
                            "heading_deg",
                            "speed_mps",
                            "length_m",
                            "width_m",
                        ):
                            converted[field] = finite(row[field])
                        for field in ("analysis_run_id", "entity_id"):
                            if row[field] == "":
                                converted[field] = None
                        yield converted

                iterator = csv_rows()
            for count, row in enumerate(iterator, 1):
                if count > max_rows:
                    raise InvalidContent("ROW_LIMIT", count)
                try:
                    item = model.model_validate_json(json.dumps(row, allow_nan=False))
                    if role == "events" and item.kind == "TRACK":
                        raise InvalidContent("SCHEMA_MISMATCH", count)
                    if str(item.id) in seen:
                        raise InvalidContent("DUPLICATE_RECORD", count)
                    seen.add(str(item.id))
                    for name, value in item.model_dump().items():
                        if name.endswith("_ms") and value is not None and value > 2**63 - 1:
                            raise InvalidContent("IMPOSSIBLE_TIME", count)
                    yield item
                except ValidationError:
                    raise InvalidContent("SCHEMA_MISMATCH", count) from None
    except InvalidContent as error:
        if error.row is None and count:
            error.row = count
        raise
    except (ValueError, UnicodeError, csv.Error, RecursionError):
        raise InvalidContent("MALFORMED_SIDECAR", count or 1) from None
    if count == 0:
        raise InvalidContent("EMPTY_SIDECAR")
    # Yielding occurs only after strict validation of each row.


def rows(fd: int, extension: str, role: Literal["events", "tracks"], max_rows: int) -> int:
    return sum(1 for _ in records(fd, extension, role, max_rows))


if __name__ == "__main__":
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (int(sys.argv[4]), int(sys.argv[4])))
        # Darwin's memory rlimits reject this setting on the supported host; CPU,
        # wall timeout, metadata/byte/frame caps and bounded buffers still apply.
        if sys.platform != "darwin":
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
        print(decode(int(sys.argv[1]), sys.argv[2], int(sys.argv[3])).model_dump_json())
    except InvalidContent as error:
        print(json.dumps({"error": error.code}))
