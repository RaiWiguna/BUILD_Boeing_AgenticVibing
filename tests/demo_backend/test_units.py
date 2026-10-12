"""Pure unit tests for the demo backend (no database)."""

import struct

from flowlens_demo.adsb import FIELDS, parse
from flowlens_demo.media import inspect_wav
from flowlens_demo.processing import PLAN, step_states, total_ms

HEADER = ",".join(FIELDS) + "\r\n"


def row(
    icao="10531271",
    t="['19', '3', '13']",
    speed="10",
    heading="270",
    lat="40.353322",
    lon="-79.926796",
    age="0.61",
    tail="N147G",
):
    return f"{icao},\"{t}\",\"['2022', '9', '10']\",1175,{speed},{heading},{lat},{lon},{age},0.32,-46.9,{tail},False\r\n"


def test_adsb_counts_duplicates_partials_empty_and_truncated():
    content = (
        HEADER
        + row()
        + row()
        + row(t="['19', '3', '14']", speed="", heading="")
        + ",,,,,,,,,,,,\r\n"
        + row(t="['19', '3', '21']")
        + "10531271,\"['19', '4"
    )
    rep = parse(content.encode())
    assert rep.position_rows == 4
    assert rep.duplicate_rows == 1
    assert rep.unique_messages == 3
    assert rep.position_only_rows == 1
    assert rep.empty_records == 1
    assert rep.truncated_records == 1
    assert rep.icao_ids == 1
    # Messages at 13 s, 14 s, 21 s: cadences 1 s and 7 s; one gap above 5 s.
    assert rep.cadence_median_s == 4.0
    assert rep.gaps_over_5s == 1
    assert rep.first_utc == "2022-09-10T19:03:13+00:00"


def test_adsb_time_field_is_never_evaluated_as_code():
    rep = parse((HEADER + row(t="__import__('os').getcwd()")).encode())
    assert rep.position_rows == 0
    assert rep.malformed_records == 1


def wav_header(code: int, channels: int, rate: int, bits: int, data_bytes: int) -> bytes:
    fmt = struct.pack(
        "<HHIIHH", code, channels, rate, rate * channels * bits // 8, channels * bits // 8, bits
    )
    return (
        b"RIFF"
        + struct.pack("<I", 36 + data_bytes)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", 16)
        + fmt
        + b"data"
        + struct.pack("<I", data_bytes)
    )


def test_wav_header_float32_duration():
    # 2.0 s of mono float32 at 44.1 kHz = 44100 * 4 * 2 bytes.
    head = wav_header(3, 1, 44100, 32, 352_800)
    info = inspect_wav(head, len(head) + 352_800)
    assert info is not None
    assert (info.format, info.channels, info.sample_rate_hz, info.duration_ms) == (
        "IEEE float",
        1,
        44100,
        2000,
    )


def test_wav_header_rejects_other_content():
    assert inspect_wav(b"ID,Time,Date", 100) is None


def test_processing_schedule_is_monotonic_and_completes():
    scale = 1.0
    start = step_states(0, scale, {})
    assert start[0]["status"] == "RUNNING"
    assert all(s["status"] == "PENDING" for s in start[1:])
    end = step_states(total_ms(scale), scale, {})
    assert all(s["status"] == "DONE" for s in end)
    mid = step_states(PLAN[0].planned_ms + PLAN[1].planned_ms + 10, scale, {})
    assert [s["status"] for s in mid[:4]] == ["DONE", "DONE", "RUNNING", "PENDING"]
    assert [p.key for p in PLAN][-1] == "save" and "mock" not in end[0]
