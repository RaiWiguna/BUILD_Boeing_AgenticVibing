"""Deterministic processing schedule.

Cheap checks (checksum, WAV header, ADS-B parse) run at upload; their results become step
details. The analysis stages use the prepared scenario: their status is derived from the time
elapsed since processing started, so the schedule survives an API restart without a background
worker and never calls a provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StepPlan:
    key: str
    label: str
    planned_ms: int


# The stages a real run goes through, in order. Durations are for two files at scale 1.0.
PLAN: list[StepPlan] = [
    StepPlan("upload", "Upload received", 600),
    StepPlan("checksum", "Integrity check", 700),
    StepPlan("audio", "Audio decoding", 1200),
    StepPlan("vad", "Voice activity detection", 1400),
    StepPlan("adsb", "ADS-B ingest and quality check", 1600),
    StepPlan("clock", "Time alignment", 1100),
    StepPlan("transcription", "Speech recognition", 5200),
    StepPlan("speakers", "Speaker roles", 1100),
    StepPlan("phraseology", "Phraseology extraction (LLM)", 3000),
    StepPlan("pairing", "Instruction–readback pairing", 1500),
    StepPlan("tracks", "Track association", 1500),
    StepPlan("conformance", "Conformance checks", 1400),
    StepPlan("highlights", "Highlights", 1100),
    StepPlan("save", "Session saved", 500),
]


def total_ms(scale: float) -> int:
    return int(sum(p.planned_ms for p in PLAN) * scale)


def _clock(ms: float) -> str:
    s = int(ms // 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


def step_details(
    scenario: Any,
    variant: dict[str, Any],
    files: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Detail lines per step; lines are revealed one by one while a step runs."""
    spec = variant["spec"]
    segs = spec["segments"]
    live = variant["live"]["segments"]
    findings = spec["findings"]
    recs = variant["recordings"]
    audio = [f for f in files if f["role"] == "audio"]
    adsb_meta = {a["name"]: a["summary"] for a in variant["adsb"]}
    total_mb = sum(f["size_bytes"] for f in new) / 1_000_000
    gaps = [
        (a["offset_ms"] + a["duration_ms"], b["offset_ms"])
        for a, b in zip(recs, recs[1:], strict=False)
        if b["offset_ms"] - (a["offset_ms"] + a["duration_ms"]) > 1000
    ]

    # Voice activity per recording, from the recognised word timings.
    speech = []
    for r in recs:
        mine = [x for x in live if x["part"] == r["part"]]
        ms = sum(x["words"][-1]["end_ms"] - x["words"][0]["start_ms"] for x in mine)
        speech.append(
            f"{r['name']} · {len(mine)} transmissions · {round(100 * ms / r['duration_ms'])}% speech"
        )

    words = sum(len(x["words"]) for x in live)
    conf = sum(x["confidence"] for x in live) / max(1, len(live))
    chunks = variant["stt"]["chunks"]
    low = [x for x in live if x["confidence"] < 0.5]
    roles = {r: sum(1 for x in segs if x.get("role") == r) for r in ("CONTROLLER", "PILOT")}
    unknown_role = len(segs) - sum(roles.values())

    callsigns = sorted({e["callsign"] for e in spec["entities"] if e.get("callsign")})
    runways = sorted({x["runway"] for x in segs if x.get("runway")})
    instructions = [x for x in segs if x.get("act") == "INSTRUCTION"]
    readbacks = [x for x in segs if x.get("act") == "READBACK"]
    paired = [x for x in readbacks if x.get("assoc")]
    matched = sum(1 for x in paired if (x.get("effects") or {}).get("readback") == "MATCHED")

    tails = {}
    for a in variant["adsb"]:
        tails.update(a["summary"].get("tails", {}))
    linked = [f"{t[0]} ↔ ICAO {hexid}" for hexid, t in tails.items() if t and t[0] in callsigns]
    layout = variant["layout"]
    movement = [f for f in findings if f["category"] == "MOVEMENT_DIVERGENCE"]
    shown = [f for f in findings if f.get("live", {}).get("attention", True)]
    attention = sum(1 for f in shown if f["priority"] == "ATTENTION")

    adsb = [f for f in files if f["role"] == "adsb"]
    adsb_lines = []
    for f in adsb:
        rep = f["detected"]
        dup = adsb_meta.get(f["name"], {}).get("duplicate_rows", 0)
        adsb_lines += [
            f"{f['name']} · {rep['position_rows']} position reports · {rep['icao_ids']} aircraft",
            f"{dup} duplicate rows removed",
        ]
        if rep["gaps_over_5s"]:
            n = rep["gaps_over_5s"]
            adsb_lines.append(f"⚠ {f['name']} · {n} position gap{'s' if n != 1 else ''} over 5 s")
    return {
        "upload": [f"{len(new)} file{'s' if len(new) != 1 else ''} · {total_mb:.1f} MB"]
        + [f"{f['name']} → {f['position']}" for f in new],
        "checksum": [f"{len(new)} file{'s' if len(new) != 1 else ''} verified · SHA-256"]
        + [f"{f['name']} · {f['sha256'][:12]}…" for f in new],
        "audio": [
            f"{len(audio)} recording{'s' if len(audio) != 1 else ''} · resampled to 16 kHz mono"
        ]
        + [f"{f['name']} · {f['detected'].get('describe', 'WAV')}" for f in audio],
        "vad": [f"{len(live)} transmissions detected"] + speech,
        "adsb": (
            [
                f"{sum(f['detected']['position_rows'] for f in adsb)} position reports · {len(tails)} aircraft"
            ]
            if adsb
            else []
        )
        + adsb_lines,
        "clock": [f"{len(recs)} recording{'s' if len(recs) != 1 else ''} on one UTC timeline"]
        + [f"{r['name']} · {r['recorded_at'][11:19]}Z · at {_clock(r['offset_ms'])}" for r in recs]
        + ["ADS-B aligned to the audio clock"]
        + [f"⚠ Not recorded {_clock(a)}–{_clock(b)}" for a, b in gaps],
        "transcription": [f"Chunk {i + 1} of {chunks} transcribed" for i in range(chunks)]
        + [f"{len(segs)} transmissions · {words} words · mean confidence {conf:.2f}"]
        + (
            [f"⚠ {len(low)} transmission{'s' if len(low) != 1 else ''} with low confidence"]
            if low
            else []
        ),
        "speakers": [
            f"ATC {roles['CONTROLLER']} · Pilot {roles['PILOT']}"
            + (f" · unknown {unknown_role}" if unknown_role else "")
        ],
        "phraseology": [
            f"{len(instructions)} instructions · {len(readbacks)} readbacks",
            f"Callsigns: {', '.join(callsigns) or '—'}",
            f"Runways: {', '.join(runways) or '—'}",
        ],
        "pairing": [
            f"{len(paired)} readback(s) paired · {matched} matched · {len(paired) - matched} to check"
        ],
        "tracks": linked
        + [f"{len(layout['taxiways'])} taxiways · {len(layout['hold_lines'])} hold lines mapped"],
        "conformance": [
            f"{len(spec['movements'])} movement intervals checked",
            f"{len(movement)} movement highlight(s)",
        ],
        "highlights": [f"{len(shown)} highlights · {attention} need attention"],
        "save": ["Session saved", "Opening workspace"],
    }


def summary_of(lines: list[str]) -> list[str]:
    """One line for a finished step (progress lines skipped), plus its warnings."""
    head = next((x for x in lines if not x.startswith(("Chunk ", "⚠"))), None)
    return ([head] if head else []) + [x for x in lines if x.startswith("⚠")]


def step_states(
    elapsed_ms: float, scale: float, details: dict[str, list[str]]
) -> list[dict[str, Any]]:
    out, t = [], 0.0
    for p in PLAN:
        dur = p.planned_ms * scale
        if elapsed_ms >= t + dur:
            status, progress = "DONE", 1.0
        elif elapsed_ms >= t:
            status, progress = "RUNNING", (elapsed_ms - t) / dur if dur else 1.0
        else:
            status, progress = "PENDING", 0.0
        out.append(
            {
                "key": p.key,
                "label": p.label,
                "status": status,
                "progress": round(progress, 3),
                "planned_ms": int(dur),
                "detail": details.get(p.key, []),
                "summary": summary_of(details.get(p.key, [])),
            }
        )
        t += dur
    return out
