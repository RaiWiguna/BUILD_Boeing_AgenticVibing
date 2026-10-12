"""Minimal WAV header inspection (RIFF/WAVE, PCM or IEEE float). No decoding."""

from __future__ import annotations

import struct
from dataclasses import dataclass

FORMATS = {1: "PCM", 3: "IEEE float", 0xFFFE: "extensible"}


@dataclass
class WavInfo:
    format: str
    channels: int
    sample_rate_hz: int
    bits_per_sample: int
    duration_ms: int

    def describe(self) -> str:
        layout = "mono" if self.channels == 1 else f"{self.channels} ch"
        return f"{self.duration_ms / 1000:.1f} s · {layout} · {self.sample_rate_hz / 1000:g} kHz · {self.format} {self.bits_per_sample}-bit"


def inspect_wav(head: bytes, total_size: int) -> WavInfo | None:
    """Parse the RIFF header from the first bytes of a file. Returns None if not a WAV."""
    if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
        return None
    pos, fmt, data_size = 12, None, None
    while pos + 8 <= len(head):
        cid, size = head[pos : pos + 4], struct.unpack("<I", head[pos + 4 : pos + 8])[0]
        body = pos + 8
        if cid == b"fmt " and body + 16 <= len(head):
            code, ch, rate, _brate, _align, bits = struct.unpack("<HHIIHH", head[body : body + 16])
            fmt = (code, ch, rate, bits)
        elif cid == b"data":
            data_size = min(size, total_size - body)
            break
        pos = body + size + (size & 1)
    if fmt is None or data_size is None:
        return None
    code, ch, rate, bits = fmt
    frame = ch * bits // 8
    if not frame or not rate:
        return None
    return WavInfo(
        FORMATS.get(code, f"format {code}"), ch, rate, bits, round(data_size / frame / rate * 1000)
    )
