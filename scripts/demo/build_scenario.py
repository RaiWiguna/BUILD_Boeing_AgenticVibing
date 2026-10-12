"""Build data/demo-scenarios/kagc-2022-09-10-88/scenario.json for the demo backend.

The scenario has two recordings from the same KAGC frequency on 10 Sep 2022:
- 88.wav (main, 19:03:13) — a taxi route revision.
- 87.wav (before, 19:00:25) — the original taxi clearance and its readback. Optional.
Each recording may come with its ADS-B CSV. One prepared analysis is built per accepted file
combination ("variant"); the backend picks it from the uploaded files.

Inputs per recording:
- <n>.wav (raw, immutable) → derived/<n>.pcm16.wav (browser playback) + waveform peaks (ffmpeg).
- Cached STT hypothesis (Google STT V1 latest_long, 50 s chunks); no provider call here.
- SYNTHETIC ADS-B CSV (synth_adsb.py), parsed with the backend parser into track waypoints.
- Authored analysis below (entities, speech acts, findings). Findings are hand-written
  interpretations of the STT hypothesis; they are not Gemini output and not evaluator truth.

Usage: python3 scripts/demo/build_scenario.py
"""

from __future__ import annotations

import array
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowlens_demo.adsb import parse  # noqa: E402
from flowlens_demo.scenarios import variant_key  # noqa: E402
from kagc_layout import FOCUS_88, FOCUS_WITH_87, LAYOUT_VERSION, layout_view, to_xy  # noqa: E402
from synth_adsb import (  # noqa: E402
    AUDIO_START,
    AUDIO_START_87,
    CSV_NAME,
    CSV_NAME_87,
    crossing_events,
    traffic_events,
)

SCENARIO_ID = "kagc-2022-09-10-88"
DIR = ROOT / "data" / "demo-scenarios" / SCENARIO_ID
RESEARCH = ROOT / "outputs" / "tartan-research"
PEAK_BUCKET_MS = 100
ARCHER, CESSNA = "N147G", "CESSNA EB"
NO_ALERT = {
    "status": "NOT_AVAILABLE",
    "severity": None,
    "note": "No source alert for this recording.",
}


@dataclass(frozen=True)
class Part:
    id: str
    position: str  # before | main | after
    wav: str
    sha256: str
    start: datetime
    csv: str
    stt_run: str


PARTS = {
    "87": Part(
        "87",
        "before",
        "87.wav",
        "34f189130e908974a9d7be9f196b2a4d7c768a8ae54413f114ff35d100d3df4f",
        AUDIO_START_87,
        CSV_NAME_87,
        "12 Oct 2026",
    ),
    "88": Part(
        "88",
        "main",
        "88.wav",
        "8c114b9f37e8ef0ca35735e4aea89634db1ec9040a397cdc3d679ce981fde7a3",
        AUDIO_START,
        CSV_NAME,
        "11 Oct 2026",
    ),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clk(ms: float) -> str:
    """ms → 'MM:SS.t' (scenario DSL clock, 100 ms resolution)."""
    tenths = int(round(ms / 100))
    m, rest = divmod(tenths, 600)
    s, t = divmod(rest, 10)
    return f"{m:02d}:{s:02d}.{t}"


def mmss(ms: float) -> str:
    """ms → 'MM:SS' for statements (matches the session clock in the UI)."""
    s = int(ms // 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


# ── per-recording assets ────────────────────────────────────────────────


def audio_assets(part: Part) -> tuple[dict, list[float]]:
    raw = DIR / part.wav
    if sha256(raw) != part.sha256:
        raise SystemExit(f"{part.wav} checksum does not match the research manifest")
    derived = DIR / "derived" / f"{part.id}.pcm16.wav"
    derived.parent.mkdir(exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ac", "1", "-ar", "44100"]
        + ["-c:a", "pcm_s16le", str(derived)],
        check=True,
    )
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(raw), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        check=True,
        capture_output=True,
    ).stdout
    samples = array.array("h", pcm)
    per = 16 * PEAK_BUCKET_MS
    peaks = [max(abs(v) for v in samples[i : i + per]) / 32768 for i in range(0, len(samples), per)]
    audio = {
        "name": part.wav,
        "sha256": part.sha256,
        "size_bytes": raw.stat().st_size,
        "format": "WAV · IEEE float32 · mono · 44.1 kHz",
        "duration_ms": round(len(samples) / 16),
        "derived": {
            "path": f"derived/{part.id}.pcm16.wav",
            "sha256": sha256(derived),
            "format": "WAV · PCM16 · mono · 44.1 kHz",
            "media_type": "audio/wav",
        },
        "source": f"TartanAviation KAGC kagc/2022/9/09-10-22_audio.zip → {part.wav} (CC BY 4.0)",
        "metadata_start": part.start.isoformat(),
    }
    return audio, peaks


def stt_chunks(part: Part) -> list[dict]:
    if part.id == "88":
        data = json.loads((RESEARCH / "transcripts50.json").read_text())["files"]["88.wav"]
        if data["source_sha256"] != part.sha256:
            raise SystemExit("STT cache is for a different source")
        return data["chunks"]  # type: ignore[no-any-return]
    run = json.loads((RESEARCH / f"stt-{part.id}" / "run.json").read_text())
    if run["status"] != "COMPLETE" or run["files"][0]["source_sha256"] != part.sha256:
        raise SystemExit(f"STT cache for {part.wav} is missing or incomplete")
    return run["chunks"]  # type: ignore[no-any-return]


# Callsign the recogniser misheard ("one first seven" for 147); corrected in the transcript.
def fix_text(text: str) -> str:
    return text.replace("one first seven", "one four seven")


def fix_word(words: list[dict], i: int) -> str:
    w = words[i]["text"]
    prev = words[i - 1]["text"].lower() if i else ""
    nxt = words[i + 1]["text"].lower().strip(",.") if i + 1 < len(words) else ""
    return "four" if w.lower() == "first" and prev == "one" and nxt == "seven" else w


def stt_segments(part: Part) -> list[dict]:
    out = []
    for chunk in stt_chunks(part):
        for seg in chunk["segments"]:
            words = [
                {
                    "text": fix_word(seg["words"], i),
                    "start_ms": round(w["source_start_s"] * 1000),
                    "end_ms": round(w["source_end_s"] * 1000),
                }
                for i, w in enumerate(seg["words"])
            ]
            out.append(
                {
                    "text": fix_text(seg["text"].strip()),
                    "confidence": round(seg["confidence"], 3),
                    "words": words,
                    "chunk": f"{part.id}:{chunk['id']}",
                    "chunk_range_ms": [
                        round(chunk["source_offset_s"] * 1000),
                        round(chunk["source_end_s"] * 1000),
                    ],
                }
            )
    return out


def adsb_file(part: Part) -> dict:
    path = DIR / part.csv
    rep = parse(path.read_bytes())
    return {
        "name": part.csv,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "format": "CSV · TartanAviation raw ADS-B (13 columns)",
        "label": "ADS-B",
        "summary": rep.summary(),
    }


def tracks_from_csvs(paths: list[Path], t0: datetime, duration_ms: int) -> list[dict]:
    obs_all = [o for p in paths for o in parse(p.read_bytes()).observations]
    names = {0xA0B1C7: ARCHER, 0xAD5F31: CESSNA}
    tracks = []
    for icao, callsign in names.items():
        obs = sorted((o for o in obs_all if o.icao == icao), key=lambda o: o.t)
        wps: list[list] = []
        gaps: list[list[str]] = []
        prev = None
        for o in obs:
            t_ms = (o.t - t0.timestamp()) * 1000
            if t_ms < -1000:
                continue
            x, y = to_xy(o.lat, o.lon)
            if prev is not None and t_ms - prev > 5000:
                gaps.append([clk(prev + 1000), clk(t_ms)])
            wps.append([clk(max(0, t_ms)), round(x, 1), round(y, 1), o.heading_deg, o.speed_kt])
            prev = t_ms
        if not wps:
            continue
        tracks.append(
            {
                "entity": callsign,
                "footprint": False,
                "staleAfter": clk(prev + 6000)
                if prev is not None and prev < duration_ms - 7000
                else None,
                "waypoints": wps,
                "gaps": gaps,
            }
        )
    return tracks


# ── authored analysis ───────────────────────────────────────────────────


def finding(
    key, category, priority, entity, t_ms, avail_ms, pending_ms, title, statement, evidence,
    quality, unknowns, movement, slots=None, track_note=None, live=None, until=None, facts=None,
):  # fmt: skip
    out = {
        "key": key,
        "category": category,
        "priority": priority,
        "status": "OPEN",
        "entity": entity,
        "t": clk(t_ms),
        "available": clk(avail_ms),
        "pending": clk(pending_ms),
        "title": title,
        "statement": statement,
        "evidence": evidence,
        "quality": quality,
        "unknowns": unknowns,
        "movement": movement,
        "sourceAlert": NO_ALERT,
    }
    if slots:
        out["slots"] = slots
    if track_note:
        out["trackNote"] = track_note
    if live:
        out["live"] = {"title": live[0], "text": live[1]}
        # Lost or unreadable audio shows in the transcript and timeline, not as a highlight.
        if category == "QUALITY_GAP" or "unreadable" in live[0].lower():
            out["live"]["attention"] = False
        # Live view: the situation ends at `until` (ms); the card then shows the resolution.
        if until:
            out["live"]["until"] = clk(until[0])
            out["live"]["resolved"] = until[1]
        if facts:
            out["live"]["facts"] = [
                {"label": f[0], "value": f[1], **({"tone": f[2]} if len(f) > 2 else {})}
                for f in facts
            ]
    return out


def meta_87() -> list[dict]:
    return [
        {
            "act": "INSTRUCTION",
            "role": "CONTROLLER",
            "entity": ARCHER,
            "action": "TAXI",
            "highlight": "turn right at Bravo 1",
            "callsignQuality": "SUPPORTED",
            "latency": 900,
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "Right at B1",
                "interpretation": "SUPPORTED",
            },
            "unknowns": ['"Archer" heard as "Number"'],
        },
        {
            "act": "INSTRUCTION",
            "role": "CONTROLLER",
            "entity": ARCHER,
            "action": "TAXI",
            "runway": "13",
            "runwayQuality": "SUPPORTED",
            "highlight": "taxi via Bravo, Alpha",
            "latency": 900,
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "RWY 13 via B, A, C",
                "readback": "NOT_OBSERVED",
                "readbackSummary": "Not observed yet",
                "interpretation": "SUPPORTED",
            },
        },
        {
            "act": "INSTRUCTION",
            "role": "CONTROLLER",
            "entity": ARCHER,
            "action": "HOLD_SHORT",
            "runway": "28",
            "runwayQuality": "AMBIGUOUS",
            "highlight": "Holt short of Runway to it",
            "latency": 900,
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "Via B, A, C · hold short RWY 28",
                "interpretation": "SUPPORTED",
            },
            "unknowns": ['runway number heard as "to it"; 28 from the readback'],
        },
        {
            "act": "READBACK",
            "role": "PILOT",
            "entity": ARCHER,
            "action": "HOLD_SHORT",
            "runway": "28",
            "runwayQuality": "SUPPORTED",
            "highlight": "via Bravo Alpha Charlie hold short of Runway 28",
            "callsignQuality": "AMBIGUOUS",
            "latency": 900,
            "assoc": {
                "target": "@87-3",
                "relationship": "READBACK_OF",
                "status": "PROPOSED",
                "unknowns": ['callsign heard as "1.7 bill"'],
            },
            "effects": {
                "readback": "MATCHED",
                "readbackSummary": "Route and hold short read back",
                "interpretation": "SUPPORTED",
            },
            "unknowns": ["callsign in readback"],
        },
    ]


def meta_88(with87: bool) -> list[dict]:
    t02 = (
        {
            "act": "READBACK",
            "role": "PILOT",
            "entity": ARCHER,
            "action": "HOLD_SHORT",
            "highlight": "hold short of Charlie on Alpha",
            "callsignQuality": "MISSING",
            "latency": 900,
            "assoc": {
                "target": "@88-1",
                "relationship": "POSSIBLE_LINK",
                "status": "AMBIGUOUS",
                "unknowns": ["amending instruction is not on either recording"],
            },
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "Hold short C on A (stated in response)",
                "readback": "PARTIAL",
                "readbackSummary": "Hold short changed · instruction not recorded",
                "interpretation": "CANDIDATE",
            },
            "unknowns": ["callsign", "amending instruction"],
        }
        if with87
        else {
            "act": "READBACK",
            "role": "PILOT",
            "entity": ARCHER,
            "action": "HOLD_SHORT",
            "highlight": "hold short of Charlie on Alpha",
            "callsignQuality": "AMBIGUOUS",
            "latency": 900,
            "assoc": {
                "target": "@88-1",
                "relationship": "POSSIBLE_LINK",
                "status": "AMBIGUOUS",
                "unknowns": [
                    "callsign is a suffix only (Bravo Alpha)",
                    "earlier taxi instruction is before the recording",
                ],
            },
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "Hold short C on A (stated in response)",
                "readback": "PARTIAL",
                "readbackSummary": "Response only · instruction before recording",
                "interpretation": "CANDIDATE",
            },
            "unknowns": ["callsign"],
        }
    )
    return [
        {
            "act": "INFORMATION",
            "role": "CONTROLLER",
            "entity": ARCHER,
            "action": "TAXI",
            "highlight": "opposite direction",
            "latency": 900,
        },
        t02,
        {
            "act": "UNKNOWN",
            "role": "UNKNOWN",
            "entity": None,
            "quality": "AMBIGUOUS",
            "callsignQuality": "MISSING",
            "latency": 900,
            "unknowns": ["STT confidence 0.16", "speaker"],
        },
        {
            "act": "INSTRUCTION",
            "role": "CONTROLLER",
            "entity": ARCHER,
            "action": "TAXI",
            "highlight": "change of plans",
            "callsignQuality": "SUPPORTED" if with87 else "AMBIGUOUS",
            "latency": 900,
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "Route revised · change of plans",
                "readback": "NOT_OBSERVED",
                "readbackSummary": "Not observed yet",
                "interpretation": "CANDIDATE",
            },
            "unknowns": ["route text garbled (roam one, three)"]
            + ([] if with87 else ["callsign (Archer one four seven golf)"]),
        },
        {
            "act": "INSTRUCTION",
            "role": "CONTROLLER",
            "entity": ARCHER,
            "action": "TAXI",
            "highlight": "join Alpha turn right on golf",
            "latency": 900,
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "Join A, right on G",
                "interpretation": "SUPPORTED",
            },
            "unknowns": ["split across two transcript segments"],
        },
        {
            "act": "INSTRUCTION",
            "role": "CONTROLLER",
            "entity": ARCHER,
            "action": "HOLD_SHORT",
            "runway": "13",
            "runwayQuality": "SUPPORTED",
            "highlight": "hold short. Runway one three",
            "latency": 900,
            "effects": {
                "instruction": "ACTIVE",
                "instructionSummary": "A → G, cross (unclear), hold short RWY 13",
                "readback": "NOT_OBSERVED",
                "readbackSummary": "Not observed yet",
                "interpretation": "SUPPORTED",
            },
            "unknowns": ["runway to cross not transcribed (Across from way…)"],
        },
        {
            "act": "READBACK",
            "role": "PILOT",
            "entity": ARCHER,
            "action": "CROSS_RUNWAY",
            "runway": "28",
            "runwayQuality": "AMBIGUOUS",
            "highlight": "Cross Runway, 28",
            "latency": 900,
            "assoc": {
                "target": "@88-6",
                "relationship": "READBACK_OF",
                "status": "PROPOSED",
                "unknowns": ["hold-short runway garbled (rolling rolling three)"],
            },
            "effects": {
                "readback": "AMBIGUOUS",
                "readbackSummary": "Needs review · crossing / hold-short",
                "interpretation": "AMBIGUOUS",
            },
            "unknowns": ["hold-short runway in readback"],
        },
    ]


def build_variant(audio_parts: list[str], csv_parts: list[str], assets: dict) -> dict:
    with87 = "87" in audio_parts
    csv87 = "87" in csv_parts
    t0 = PARTS[audio_parts[0]].start
    # Same base as spec.recordedAt (whole seconds), so text and UI clock agree.
    base = t0.replace(microsecond=0)

    def utc(ms: float) -> str:
        return (base + timedelta(milliseconds=ms)).strftime("%H:%M:%SZ")

    offsets = {p: round((PARTS[p].start - t0).total_seconds() * 1000) for p in audio_parts}
    off = offsets["88"]
    duration = off + assets["88"]["audio"]["duration_ms"]

    # Segments: internal keys "@<part>-<n>", renumbered T-01… in time order below.
    raw_segments: list[tuple[str, dict, dict, int]] = []
    for p in audio_parts:
        stt = assets[p]["stt"]
        metas = meta_87() if p == "87" else meta_88(with87)
        for i, (seg, meta) in enumerate(zip(stt, metas, strict=True)):
            raw_segments.append((f"@{p}-{i + 1}", seg, meta, offsets[p]))
    raw_segments.sort(key=lambda r: r[1]["words"][0]["start_ms"] + r[3])
    keymap = {k: f"T-{i + 1:02d}" for i, (k, *_rest) in enumerate(raw_segments)}

    def K(*keys: str) -> list[str]:
        return [keymap[k] for k in keys]

    segments, live = [], []
    for i, (k, seg, meta, o) in enumerate(raw_segments):
        start = seg["words"][0]["start_ms"] + o
        end = max(seg["words"][-1]["end_ms"] + o, start + 300)
        m = dict(meta)
        if "assoc" in m:
            m["assoc"] = {**m["assoc"], "target": keymap[m["assoc"]["target"]]}
        segments.append(
            {
                "key": keymap[k],
                "evidence": f"E-{i + 1:02d}",
                "t": clk(start),
                "dur": end - start,
                "ch": 0,
                "text": seg["text"],
                **m,
            }
        )
        live.append(
            {
                "key": keymap[k],
                "part": k[1:3],
                "confidence": seg["confidence"],
                "words": [
                    {"text": w["text"], "start_ms": w["start_ms"] + o, "end_ms": w["end_ms"] + o}
                    for w in seg["words"]
                ],
                "chunk": seg["chunk"],
                "chunk_range_ms": [seg["chunk_range_ms"][0] + o, seg["chunk_range_ms"][1] + o],
            }
        )

    def seg_end(k: str) -> int:
        seg, o = next((s, oo) for kk, s, _m, oo in raw_segments if kk == k)
        return seg["words"][-1]["end_ms"] + o  # type: ignore[no-any-return]

    def seg_start(k: str) -> int:
        seg, o = next((s, oo) for kk, s, _m, oo in raw_segments if kk == k)
        return seg["words"][0]["start_ms"] + o  # type: ignore[no-any-return]

    ev = assets["events"]
    cross_in = ev["runway_10_28_enter_s"] * 1000 + off
    cross_out = ev["runway_10_28_exit_s"] * 1000 + off
    stop = ev["stopped_short_13_s"] * 1000 + off
    t03a, t03b = seg_end("@88-2"), seg_start("@88-4")
    findings: list[dict] = []

    if with87:
        clr, rb = seg_start("@87-1"), seg_end("@87-4")
        findings.append(
            finding(
                "@clearance",
                "READBACK_DISCREPANCY",
                "INFO",
                ARCHER,
                rb,
                rb + 2400,
                rb + 300,
                "Readback matches the taxi clearance",
                f'ATC at {mmss(clr)}: "147 Golf, turn right at Bravo 1, runway 13, taxi via Bravo, Alpha, Charlie, hold short of runway 28". The readback repeats runway 13, the route and the hold short of runway 28. "Turn right at Bravo 1" is not repeated and the callsign at the end is unclear ("1.7 bill").',
                K("@87-1", "@87-2", "@87-3", "@87-4"),
                "AMBIGUOUS",
                ["callsign in readback"],
                "CONSISTENT" if csv87 else "UNKNOWN",
                slots=[
                    {
                        "slot": "CALLSIGN",
                        "said": "147 Golf",
                        "heard": "1.7 bill",
                        "status": "AMBIGUOUS",
                    },
                    {"slot": "RUNWAY", "said": "13", "heard": "13", "status": "MATCHED"},
                    {
                        "slot": "ACTION",
                        "said": "via Bravo, Alpha, Charlie",
                        "heard": "via Bravo Alpha Charlie",
                        "status": "MATCHED",
                    },
                    {
                        "slot": "CONDITION",
                        "said": "hold short of runway 28",
                        "heard": "hold short of Runway 28",
                        "status": "MATCHED",
                    },
                ],
                live=(
                    "Readback matches · right at B1 not read back",
                    f"Cleared {utc(clr)}: right at B1, RWY 13, via B A C, hold short RWY 28. Readback has RWY 13, route and hold short; right at B1 missing. Callsign unclear.",
                ),
            )
        )
        if csv87:
            go = 128_000 + offsets["87"]
            findings.append(
                finding(
                    "@taxi",
                    "MOVEMENT_DIVERGENCE",
                    "INFO",
                    ARCHER,
                    go + 9_000,
                    go + 10_500,
                    go + 6_000,
                    "Taxi follows the clearance",
                    f"The track leaves the ramp at {mmss(go)}, turns right onto B at B1 and joins A westbound — consistent with the clearance read back at {mmss(rb)}.",
                    K("@87-2", "@87-4"),
                    "SUPPORTED",
                    ["real observation"],
                    "CONSISTENT",
                    track_note="Centre point only · ADS-B",
                    live=(
                        "Taxiing as cleared",
                        f"Off the ramp {utc(go)}, right at B1, westbound on A.",
                    ),
                )
            )
        gap_a, gap_b = assets["87"]["audio"]["duration_ms"], off
        findings.append(
            finding(
                "@gap",
                "QUALITY_GAP",
                "NOTICE",
                "Frequency",
                gap_a,
                gap_b + 600,
                gap_b - 1_200,
                f"{round((gap_b - gap_a) / 1000)} s not recorded",
                f"The recording stops at {mmss(gap_a)} and resumes at {mmss(gap_b)}. Anything said in between is not available.",
                K("@87-4", "@88-1"),
                "MISSING",
                [f"radio between {mmss(gap_a)} and {mmss(gap_b)}"],
                "NOT_EVALUABLE",
                live=(
                    f"Audio lost {round((gap_b - gap_a) / 1000)} s",
                    f"No audio {utc(gap_a)}–{utc(gap_b)}. Transmissions in that window unknown.",
                ),
            )
        )

    e02 = seg_end("@88-2")
    if with87:
        hold28 = seg_start("@87-3")
        findings.append(
            finding(
                "@holdshort",
                "CRITICAL_SLOT_UNCERTAIN",
                "ATTENTION",
                ARCHER,
                e02,
                e02 + 2400,
                e02 + 200,
                "Hold short changed off the recording",
                f'At {mmss(hold28)} the clearance ended "hold short of runway 28". At {mmss(seg_start("@88-2"))} the response says "Bravo Alpha then hold short of Charlie on Alpha". The instruction that moved the hold short to Charlie is not on either recording. "Bravo Alpha" is the route, not a callsign.',
                K("@87-3", "@87-4", "@88-1", "@88-2"),
                "AMBIGUOUS",
                ["amending instruction", "callsign in response"],
                "UNKNOWN",
                slots=[
                    {"slot": "CALLSIGN", "said": "147 Golf", "heard": None, "status": "MISSING"},
                    {
                        "slot": "CONDITION",
                        "said": "hold short of runway 28",
                        "heard": "hold short of Charlie on Alpha",
                        "status": "MISMATCH",
                    },
                ],
                live=(
                    "Hold short changed · RWY 28 → C on A",
                    f'Cleared hold short RWY 28 ({utc(hold28)}). Pilot reports hold short C on A ({utc(seg_start("@88-2"))}). No amending instruction heard. "Bravo Alpha" is the route.',
                ),
            )
        )
    else:
        findings.append(
            finding(
                "@suffix",
                "CRITICAL_SLOT_UNCERTAIN",
                "NOTICE",
                ARCHER,
                e02,
                e02 + 2200,
                e02 + 200,
                "Response identity is a suffix only",
                'The response repeats "hold short of Charlie on Alpha" but identifies itself only as "Bravo Alpha". The taxi instruction it refers to was issued before this recording starts.',
                K("@88-1", "@88-2"),
                "AMBIGUOUS",
                ["full callsign", "original taxi instruction"],
                "UNKNOWN",
                slots=[
                    {
                        "slot": "CALLSIGN",
                        "said": None,
                        "heard": "Bravo Alpha",
                        "status": "AMBIGUOUS",
                    },
                    {
                        "slot": "ACTION",
                        "said": None,
                        "heard": "hold short of Charlie on Alpha",
                        "status": "MISSING",
                    },
                ],
                live=(
                    "Callsign incomplete",
                    f'"Bravo Alpha … hold short of Charlie on Alpha" ({utc(seg_start("@88-2"))}). No full callsign; original taxi instruction not heard.',
                ),
            )
        )

    t3 = seg_start("@88-3")
    findings.append(
        finding(
            "@untranscribed",
            "QUALITY_GAP",
            "INFO",
            "Frequency",
            t3,
            t3 + 3500,
            t3 + 500,
            "Transmission likely not transcribed",
            f'Between {mmss(t03a)} and {mmss(t03b)} the recognizer returned only "One." (confidence 0.16). Audio energy suggests speech may be present. An empty transcript is not evidence that the frequency was silent or that no readback was given.',
            K("@88-3"),
            "MISSING",
            [f"content between {mmss(t03a)} and {mmss(t03b)}"],
            "NOT_EVALUABLE",
            live=(
                "Transmission unreadable",
                f"Speech {utc(t03a)}–{utc(t03b)} not readable. Content unknown; a readback may be in it.",
            ),
        )
    )
    e04 = seg_end("@88-4")
    findings.append(
        finding(
            "@revised",
            "CRITICAL_SLOT_UNCERTAIN",
            "ATTENTION",
            ARCHER,
            e04,
            e04 + 2600,
            e04 + 300,
            "Route revised · change of plans",
            (
                f'ATC announces a change of plans to "Archer one four seven golf" — 147 Golf, as in the {mmss(seg_start("@87-1"))} clearance. The route via Alpha and Charlie is superseded; the first leg of the new route is garbled ("roam one, three").'
                if with87
                else 'ATC announces a change of plans to "Archer one four seven golf". The earlier hold short of Charlie on Alpha is superseded by a new route; the start of the new route is garbled ("roam one, three"). The link between "Bravo Alpha" and "147 Golf" is a candidate, not a confirmed identity.'
            ),
            K("@88-2", "@88-4") if not with87 else K("@87-2", "@88-2", "@88-4"),
            "AMBIGUOUS",
            ["first leg of the new route"]
            + ([] if with87 else ["identity link Bravo Alpha ↔ 147 Golf"]),
            "UNKNOWN",
            slots=(
                []
                if with87
                else [
                    {
                        "slot": "CALLSIGN",
                        "said": "Archer one four seven golf",
                        "heard": "Bravo Alpha",
                        "status": "AMBIGUOUS",
                    }
                ]
            )
            + [
                {
                    "slot": "ACTION",
                    "said": "change of plans · continue taxiing via …",
                    "heard": None,
                    "status": "MISSING",
                }
            ],
            live=(
                "Route revised",
                f"Change of plans for Archer 147G ({utc(seg_start('@88-4'))}). Route via A, C cancelled. First leg of new route unreadable."
                + ("" if with87 else ' Link to "Bravo Alpha" unconfirmed.'),
            ),
        )
    )
    e06 = seg_end("@88-6")
    findings.append(
        finding(
            "@crossing",
            "CRITICAL_SLOT_UNCERTAIN",
            "NOTICE",
            ARCHER,
            e06,
            e06 + 2300,
            e06 + 300,
            "Crossing runway not transcribed",
            'The instruction continues "join Alpha, turn right on Golf … hold short runway one three", but the crossing part reads "Across from way to a golf". Which runway the aircraft is cleared to cross is not available in Said. The transmission is also split across two transcript segments.',
            K("@88-4", "@88-5", "@88-6"),
            "AMBIGUOUS",
            ["runway to cross", "condition wording"],
            "UNKNOWN",
            slots=[
                {
                    "slot": "ACTION",
                    "said": "join Alpha, turn right on Golf",
                    "heard": None,
                    "status": "MISSING",
                },
                {
                    "slot": "RUNWAY",
                    "said": "cross: unclear · hold short: 13",
                    "heard": None,
                    "status": "AMBIGUOUS",
                },
            ],
            live=(
                "Crossing runway unreadable",
                f"Instruction ({utc(seg_start('@88-4'))}): join A, right on G, hold short RWY 13. Runway to cross unreadable.",
            ),
        )
    )
    e07 = seg_end("@88-7")
    findings.append(
        finding(
            "@readback",
            "READBACK_DISCREPANCY",
            "ATTENTION",
            ARCHER,
            e07,
            e07 + 2600,
            e07 + 300,
            "Readback needs review",
            'The readback contains "right turn on golf, cross runway 28, hold short … three on golf, 147 Golf". Crossing runway 28 appears only in the readback because the instruction\'s crossing slot was not transcribed, and the hold-short runway in the readback is garbled. This is not a confirmed mismatch — listen to both transmissions.',
            K("@88-6", "@88-7"),
            "AMBIGUOUS",
            [
                "crossing runway in the instruction",
                "hold-short runway in the readback",
                "speaker identity",
            ],
            "UNKNOWN",
            slots=[
                {
                    "slot": "CALLSIGN",
                    "said": "Archer one four seven golf",
                    "heard": "147, golf",
                    "status": "MATCHED",
                },
                {
                    "slot": "ACTION",
                    "said": "join Alpha, turn right on Golf",
                    "heard": "right turn on golf",
                    "status": "MATCHED",
                },
                {
                    "slot": "RUNWAY",
                    "said": "cross: not transcribed",
                    "heard": "cross runway 28",
                    "status": "MISSING",
                },
                {
                    "slot": "CONDITION",
                    "said": "hold short runway one three",
                    "heard": "hold short … three on golf",
                    "status": "AMBIGUOUS",
                },
            ],
            live=(
                "Readback adds cross RWY 28",
                f"Readback ({utc(seg_start('@88-7'))}): right on G, cross RWY 28, hold short …3 on G. Crossing runway not heard in instruction; hold-short runway unclear.",
            ),
        )
    )
    findings.append(
        finding(
            "@crossed",
            "MOVEMENT_DIVERGENCE",
            "ATTENTION",
            ARCHER,
            cross_in,
            cross_in + 1500,
            cross_in,
            "On RWY 10/28 · crossing not confirmed",
            f"The track enters the 10/28 strip on Golf at {mmss(cross_in)} and leaves it at {mmss(cross_out)}. Crossing runway 28 appears only in the readback at {mmss(seg_start('@88-7'))}: the crossing part of the instruction is unreadable, and no ATC confirmation or correction is heard after the readback.",
            K("@88-6", "@88-7"),
            "AMBIGUOUS",
            ["crossing clearance wording", "ATC confirmation"],
            "CONSISTENT",
            track_note="Centre point only · ADS-B",
            live=(
                "On RWY 10/28 · crossing not confirmed",
                f"Entered RWY 10/28 on G {utc(cross_in)}. Cross 28 only in the readback; no ATC confirmation heard.",
            ),
            until=(cross_out, f"Clear of RWY 10/28 {utc(cross_out)}."),
            facts=[
                ("Position", "RWY 10/28 · on G"),
                ("Instruction", "cross: unreadable", "notice"),
                ("Readback", "cross RWY 28"),
                ("ATC confirm", "none heard", "attention"),
            ],
        )
    )
    findings.append(
        finding(
            "@stopped",
            "MOVEMENT_DIVERGENCE",
            "NOTICE",
            ARCHER,
            stop,
            stop + 2000,
            stop - 1500,
            "Stopped short of hold line 13",
            "The centre point stops about 25 m before the hold line for runway 13 and about 8 m north of the 10/28 edge. Without aircraft footprint, whether the tail is clear of runway 10/28 is NOT_EVALUABLE.",
            K("@88-6", "@88-7"),
            "AMBIGUOUS",
            ["aircraft footprint", "surveyed hold-line position"],
            "NOT_EVALUABLE",
            track_note="Footprint not available · runway clearance not evaluable",
            live=(
                "Holding short RWY 13",
                "Stopped ~25 m before RWY 13 hold line, ~8 m north of RWY 10/28 edge. Tail clear of 10/28: unknown.",
            ),
        )
    )
    tr = assets["traffic"]
    call = seg_start("@88-1")
    held = tr["archer_hold_s"] * 1000 + off
    off_a = tr["cessna_off_alpha_s"] * 1000 + off
    findings.append(
        finding(
            "@opposite",
            "MOVEMENT_DIVERGENCE",
            "ATTENTION",
            ARCHER,
            call,
            call + 1500,
            call,
            "Opposite-direction traffic on A",
            f"At {mmss(call)} ATC advises opposite-direction traffic: a Cessna eastbound on Alpha to Charlie. ADS-B shows N147G westbound and the Cessna eastbound on A, {tr['start_distance_m']} m apart. N147G stops short of C at {mmss(held)}; the Cessna leaves A onto C at {mmss(off_a)}, closest {tr['closest_m']} m.",
            K("@88-1", "@88-2"),
            "SUPPORTED",
            ["Cessna clearance (not on the recording)"],
            "CONSISTENT",
            track_note="Centre points only · ADS-B",
            live=(
                "Opposite direction on A · Cessna",
                f"N147G westbound, Cessna eastbound on A, {tr['start_distance_m']} m apart. Traffic called {utc(call)}.",
            ),
            until=(
                off_a,
                f"Cessna off A onto C {utc(off_a)}. N147G held short of C from {utc(held)}. Closest {tr['closest_m']} m.",
            ),
            facts=[
                ("N147G", f"Westbound on A · {tr['archer_kt']} kt"),
                ("Cessna", f"Eastbound on A · {tr['cessna_kt']} kt"),
                ("Distance", f"{tr['start_distance_m']} m, closing", "attention"),
                ("Traffic call", f"ATC {utc(call)}"),
            ],
        )
    )
    findings.sort(key=lambda f: (f["available"], f["key"]))
    for i, f in enumerate(findings):
        f["key"] = f"F-{i + 1:02d}"

    # Standing items to keep in mind: a step replaces the previous one; `until` marks it done.
    def step(t_ms: float, avail_ms: float, title: str, text: str, source: str | None) -> dict:
        return {
            "t": clk(t_ms),
            "available": clk(avail_ms),
            "title": title,
            "text": text,
            "source": source,
        }

    first_limit = (
        step(seg_start("@87-3"), seg_end("@87-3"), "Hold short RWY 28 at C", f"Cleared {utc(seg_start('@87-1'))}: RWY 13 via B, A, C.", "ATC")
        if with87
        else step(off, off, "Limit not heard", "Taxi instruction issued before the recording.", None)
    )  # fmt: skip
    reminders = [
        {
            "key": "R-limit",
            "entity": ARCHER,
            "kind": "LIMIT",
            "steps": [
                first_limit,
                step(seg_start("@88-6"), seg_end("@88-6"), "Hold short RWY 13 on G", f"Cleared {utc(seg_start('@88-5'))}: join A, right on G. Crossing part unreadable.", "ATC"),
            ],
            "evidence": K("@87-3", "@88-5", "@88-6") if with87 else K("@88-5", "@88-6"),
        },
        {
            "key": "R-traffic",
            "entity": ARCHER,
            "kind": "TRAFFIC",
            "steps": [step(call, seg_end("@88-1"), "Traffic: Cessna, opposite direction on A", f"Told {utc(call)}: Cessna eastbound on A to C.", "ATC")],
            "until": clk(off_a),
            "done": f"Cessna off A onto C {utc(off_a)}.",
            "evidence": K("@88-1"),
        },
        {
            "key": "R-intent",
            "entity": ARCHER,
            "kind": "INTENT",
            "steps": [step(seg_start("@88-2"), seg_end("@88-2"), "Will hold short C on A", f"Pilot {utc(seg_start('@88-2'))}: B, A, then hold short C on A.", "PILOT")],
            "until": clk(seg_start("@88-4")),
            "done": f"Replaced by the new route {utc(seg_start('@88-4'))}.",
            "evidence": K("@88-2"),
        },
    ]  # fmt: skip

    movements: list[dict] = []
    if with87:
        movements += (
            [
                {"entity": ARCHER, "from": "00:00.0", "state": "UNKNOWN", "summary": "On the ramp", "reason": "Before the taxi clearance"},
                {"entity": ARCHER, "from": clk(128_000), "state": "CONSISTENT", "summary": "Taxiing via B1 and B", "reason": "Consistent with the clearance (via Bravo, Alpha)"},
                {"entity": ARCHER, "from": clk(off - 22_000), "state": "CONSISTENT", "summary": "Westbound on A", "reason": "Consistent with the clearance"},
            ]
            if csv87
            else [
                {"entity": ARCHER, "from": "00:00.0", "state": "UNKNOWN", "summary": "No position", "reason": "No ADS-B file for this period"},
            ]
        )  # fmt: skip
    movements += [
        {
            "entity": ARCHER,
            "from": clk(off),
            "state": "UNKNOWN",
            "summary": "Taxiing westbound on A",
            "reason": f"Cleared at {mmss(seg_start('@87-1'))}" if with87 else "Instruction before the recording",
        },
        {"entity": ARCHER, "from": clk(off + 31_000), "state": "UNKNOWN", "summary": "Holding short of C on A", "reason": "Amending instruction not recorded" if with87 else None},
        {"entity": ARCHER, "from": clk(off + 58_500), "state": "UNKNOWN", "summary": "Moving towards G", "reason": "Readback still under review"},
        {"entity": ARCHER, "from": clk(cross_in), "state": "CONSISTENT", "summary": "Crossing 10/28 on G", "reason": "Consistent with readback; instruction crossing slot unclear"},
        {"entity": ARCHER, "from": clk(stop), "state": "NOT_EVALUABLE", "summary": "Stopped short of hold line 13", "reason": "Centre point only · runway 10/28 clearance not evaluable"},
    ]  # fmt: skip
    cessna_from = (off - 28_000) if csv87 else off
    movements += [
        {"entity": CESSNA, "from": clk(cessna_from), "state": "UNKNOWN", "summary": "Taxiing eastbound on A", "reason": "No instruction for this object in the recording"},
        {"entity": CESSNA, "from": clk(off + 50_000), "state": "UNKNOWN", "summary": "Turning south onto C", "reason": "No instruction for this object in the recording"},
    ]  # fmt: skip
    if with87:
        movements.append(
            {"entity": CESSNA, "from": "00:00.0", "state": "UNKNOWN", "summary": "Not in view", "reason": "No position reported"},
        )  # fmt: skip
    movements.sort(key=lambda m: (m["entity"], m["from"]))

    csv_paths = [DIR / PARTS[p].csv for p in ("87", "88") if p in csv_parts]
    tracks = tracks_from_csvs(csv_paths, t0, duration)
    gaps = [{"start_ms": assets["87"]["audio"]["duration_ms"], "end_ms": off}] if with87 else []

    names = " + ".join(PARTS[p].wav for p in audio_parts)
    spec = {
        "key": SCENARIO_ID,
        "title": "",  # set per workspace
        "context": "KAGC · Ground · taxi clearance and route revision"
        if with87
        else "KAGC · Ground · taxi route revision",
        "lifecycle": "READY",
        "analysis": "COMPLETED",
        "durationMs": duration,
        "recordedAt": t0.isoformat().replace("+00:00", "Z")[:19] + "Z",
        "updatedAt": "",
        "sourceLabel": f"TartanAviation KAGC {names} (CC BY 4.0)",
        "sourceKind": "PUBLIC_CORPUS",
        "layoutVersion": LAYOUT_VERSION,
        "channels": [{"index": 0, "label": "KAGC radio", "role": "ATC + pilots (mixed)"}],
        "entities": [
            {
                "callsign": ARCHER,
                "kind": "AIRCRAFT",
                "type": "PA-28 Archer (from speech)",
                "role": "Taxi · route revised",
                "aliases": ["Archer one four seven Golf", "147 Golf"]
                + ([] if with87 else ["Bravo Alpha (candidate)"]),
            },
            {
                "callsign": CESSNA,
                "kind": "AIRCRAFT",
                "type": "Cessna (from speech)",
                "role": "Opposite-direction traffic",
                "aliases": ["Cessna eastbound", "N5326K"],
            },
        ],
        "hasTracks": True,
        "hasLayout": True,
        "gaps": gaps,
        "permissions": {
            "local_read": {"state": "ALLOWED", "note": "Public corpus, CC BY 4.0."},
            "cloud_audio": {"state": "UNDETERMINED", "note": "Not used in this workspace."},
            "cloud_transcript": {"state": "UNDETERMINED", "note": "Not used in this workspace."},
            "reviewer_access": {"state": "ALLOWED", "note": "Granted reviewers may open evidence."},
            "report_export": {
                "state": "ALLOWED",
                "note": "Attribution to TartanAviation (CC BY 4.0) required.",
            },
            "audio_export": {"state": "DENIED", "note": "Audio is not redistributed."},
        },
        "retentionDays": 30,
        "providerAvailable": False,
        "speakerIdentity": False,
        "runs": [{"label": "#01", "revision": 1, "status": "COMPLETED", "createdAt": ""}],
        "segments": segments,
        "movements": movements,
        "tracks": tracks,
        "findings": findings,
        "reminders": reminders,
        "options": [],
        "insufficient": [
            {
                "entity": ARCHER,
                "needed": ["human review of the transmissions", "real paired track"],
                "reason": "Options are not available for this session.",
            }
        ],
        "notices": [
            {"tone": "muted", "title": "STT hypothesis", "detail": "Transcript not human-reviewed"},
        ],
    }

    peaks: list[float] = []
    for p in audio_parts:
        start = offsets[p] // PEAK_BUCKET_MS
        peaks += [0.0] * max(0, start - len(peaks))
        peaks += assets[p]["peaks"]
    top = sorted(peaks)[int(len(peaks) * 0.995)] or 1.0
    peaks = [round(min(1.0, v / top), 3) for v in peaks]

    chunk_starts = sorted({s["chunk_range_ms"][0] for s in live})
    all_chunks = sorted(
        {
            round(c["source_offset_s"] * 1000) + offsets[p]
            for p in audio_parts
            for c in stt_chunks(PARTS[p])
        }
    )
    return {
        "audio_parts": audio_parts,
        "csv_parts": csv_parts,
        "duration_ms": duration,
        "recordings": [
            {
                "part": p,
                "name": PARTS[p].wav,
                "offset_ms": offsets[p],
                "duration_ms": assets[p]["audio"]["duration_ms"],
                "recorded_at": PARTS[p].start.isoformat().replace("+00:00", "Z"),
            }
            for p in audio_parts
        ],
        "spec": spec,
        "live": {
            "segments": live,
            "speakers": {
                s["key"]: {"CONTROLLER": "ATC", "PILOT": "Pilot"}.get(s["role"], "Unknown speaker")
                for s in segments
            },
            "chunk_boundaries_ms": [c for c in all_chunks if c > 0] or chunk_starts[1:],
        },
        "peaks": {"bucket_ms": PEAK_BUCKET_MS, "values": peaks},
        "layout": layout_view(FOCUS_WITH_87 if with87 else FOCUS_88),
        "stt": {
            "provider": "Google Cloud STT V1 · latest_long · en-US",
            "run": " / ".join(f"{PARTS[p].wav} {PARTS[p].stt_run}" for p in audio_parts),
            "chunks": len(all_chunks),
        },
        "adsb": [
            {k: v for k, v in assets[p]["adsb"].items() if k in ("name", "label", "summary")}
            for p in csv_parts
        ],
    }


VARIANTS = [
    (["88"], ["88"]),
    (["87", "88"], ["88"]),
    (["87", "88"], ["87", "88"]),
]


def main() -> None:
    assets: dict = {}
    for pid, part in PARTS.items():
        audio, peaks = audio_assets(part)
        assets[pid] = {
            "audio": audio,
            "peaks": peaks,
            "stt": stt_segments(part),
            "adsb": adsb_file(part),
        }
    truth = json.loads((DIR / "derived" / "adsb-synthetic-truth.json").read_text())
    assets["events"] = crossing_events(truth)
    assets["traffic"] = traffic_events(truth)
    variants = {}
    for audio_parts, csv_parts in VARIANTS:
        key = variant_key([(p, "audio") for p in audio_parts] + [(p, "adsb") for p in csv_parts])
        variants[key] = build_variant(audio_parts, csv_parts, assets)
    scenario = {
        "scenario_id": SCENARIO_ID,
        "version": 2,
        "labels": [
            "PUBLIC_CORPUS audio",
            "STT_HYPOTHESIS",
            "SCHEMATIC taxiways",
            "NOT_DOMAIN_VALIDATED",
        ],
        "attribution": "Audio: TartanAviation (AirLab, Carnegie Mellon University), CC BY 4.0.",
        "main_part": "88",
        "parts": {
            pid: {
                "position": part.position,
                "recorded_at": part.start.isoformat().replace("+00:00", "Z"),
                "audio": assets[pid]["audio"],
                "adsb": assets[pid]["adsb"],
            }
            for pid, part in PARTS.items()
        },
        "events": assets["events"],
        "variants": variants,
    }
    (DIR / "scenario.json").write_text(json.dumps(scenario, indent=1))
    print(
        json.dumps(
            {
                key: {
                    "duration_ms": v["duration_ms"],
                    "segments": len(v["spec"]["segments"]),
                    "findings": [
                        (f["key"], f["title"], f["available"]) for f in v["spec"]["findings"]
                    ],
                    "tracks": [
                        (t["entity"], len(t["waypoints"]), t["gaps"]) for t in v["spec"]["tracks"]
                    ],
                }
                for key, v in variants.items()
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    assert math.isfinite(sum(v["duration_ms"] for v in variants.values()))


if __name__ == "__main__":
    main()
