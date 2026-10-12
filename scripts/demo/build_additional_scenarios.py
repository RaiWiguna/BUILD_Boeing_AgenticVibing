"""Build only five additional cached demo cases. Never writes the protected 87/88 case.

Source WAVs are acquired through SSH, not by this builder. Transcripts remain cached STT
hypotheses; speaker/identity/intent annotations and the optional surface points are authored.
No provider calls. Run from the repo root with Python and ffmpeg installed.
"""

from __future__ import annotations

import array
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from flowlens_demo.adsb import FIELDS, parse  # noqa: E402
from flowlens_demo.scenarios import variant_key  # noqa: E402
from kagc_layout import ARP, LAYOUT_VERSION, M_PER_DEG_LAT, M_PER_DEG_LON, layout_view  # noqa: E402

from synth_additional_adsb import fixes  # noqa: E402

SELECTED = (50, 51, 47, 156, 123)
CACHE = ROOT / "outputs/tartan-research/transcripts50.json"
TITLES = {
    50: "KAGC · Multi-object Tower",
    51: "KAGC · Landing readback",
    47: "KAGC · Conditional departure",
    156: "KAGC · Clearance memory",
    123: "KAGC · Departure handoff",
}
# Per cached segment: role, source entity candidate. UNKNOWN fragments have no identity.
ANNOTATIONS = {
    50: [
        ("UNKNOWN", None),
        ("CONTROLLER", "Quebec?"),
        ("CONTROLLER", "Quebec?"),
        ("PILOT", "Quebec?"),
        ("CONTROLLER", "Alpha?"),
        ("UNKNOWN", None),
    ],
    51: [
        ("CONTROLLER", "Quebec?"),
        ("CONTROLLER", "Quebec?"),
        ("PILOT", "Quebec?"),
        ("UNKNOWN", None),
        ("CONTROLLER", "Alpha?"),
        ("PILOT", "Alpha?"),
        ("UNKNOWN", None),
    ],
    47: [("PILOT", "Uniform?"), ("CONTROLLER", "Uniform?")],
    156: [
        ("CONTROLLER", "Julia Charlie?"),
        ("CONTROLLER", "Kilo Alpha?"),
        ("UNKNOWN", None),
        ("UNKNOWN", None),
        ("CONTROLLER", "Julia Charlie?"),
    ],
    123: [
        ("CONTROLLER", "936?"),
        ("PILOT", "936?"),
        ("PILOT", "Other transmission"),
        ("CONTROLLER", "Other transmission"),
    ],
}
# Trigger after the last supporting word; facts intentionally avoid unsupported slots.
CARDS = {
    50: [
        (
            3,
            "RWY 13 · Downwind read back",
            [
                ("Instruction", "Midfield left downwind RWY 13"),
                ("Readback", "Downwind/runway repeated; identity candidate"),
            ],
            [1, 2, 3],
        ),
        (
            4,
            "Alpha? · Takeoff clearance",
            [("Runway", "13"), ("Traffic advised", "Duchess backtaxi (voice report)")],
            [4],
        ),
    ],
    51: [
        (
            2,
            "RWY 13 · Landing clearance read back",
            [
                ("Said", "RWY 13 clear to land"),
                ("Heard", "Runway/action repeated"),
                ("Traffic", "Departure roll reported, not position evidence"),
            ],
            [0, 1, 2],
        ),
        (
            5,
            "Alpha? · Turnout exchange",
            [
                ("Context", "Separate transmission from the landing exchange"),
                ("Direction", "South mentioned; association candidate"),
            ],
            [4, 5],
        ),
    ],
    47: [
        (
            1,
            "RWY 13 · Conditional backtaxi approved",
            [
                ("Takeoff", "Runway 13"),
                ("Backtaxi", "If needed"),
                ("Readback", "Not present in the cached clip"),
            ],
            [0, 1],
        )
    ],
    156: [
        (
            4,
            "Clearance · 3,000 ft / 4131",
            [
                ("Assigned altitude", "Maintain 3,000 ft"),
                ("Squawk", "4131"),
                ("FL180", "Expectation wording unresolved; not assigned altitude"),
            ],
            [4],
        )
    ],
    123: [
        (
            1,
            "119.35 · Frequency read back",
            [
                ("Said", "Contact departure 119.35"),
                ("Heard", "119.35 repeated"),
                ("Heading", "Unresolved"),
                ("Contact", "Completion not observed"),
            ],
            [0, 1],
        )
    ],
}
REMINDERS = {
    50: [
        (2, "INTENT", "Quebec? · Midfield left downwind RWY 13"),
        (2, "TRAFFIC", "Duchess backtaxi advised · voice report"),
    ],
    51: [(1, "LIMIT", "Quebec? · Landing clearance RWY 13")],
    47: [(1, "LIMIT", "RWY 13 · Takeoff cleared; backtaxi if needed")],
    156: [
        (4, "LIMIT", "Julia Charlie? · Maintain 3,000 ft"),
        (4, "INTENT", "Squawk 4131"),
    ],
    123: [(0, "INTENT", "936? · Contact departure 119.35")],
}


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def clock(ms: int) -> str:
    tenth = round(ms / 100)
    return f"{tenth // 600:02}:{tenth // 10 % 60:02}.{tenth % 10}"


def folder(n: int) -> Path:
    assert n in SELECTED
    date = "2022-09-11" if n == 156 else "2022-09-10"
    return ROOT / f"data/demo-scenarios/kagc-{date}-{n}"


def raw_segments(n: int, cache: dict) -> list[dict]:
    return [
        s for c in cache[f"{n}.wav"]["chunks"] for s in c["segments"] if s.get("words")
    ]


def prepare(n: int, cache: dict) -> dict:
    d = folder(n)
    f = cache[f"{n}.wav"]
    wav = d / f"{n}.wav"
    if digest(wav) != f["source_sha256"]:
        raise ValueError(f"{n} source checksum mismatch")
    stamps = re.findall(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+", f["metadata_text"])
    start = datetime.fromisoformat(stamps[0]).replace(tzinfo=UTC)
    derived = d / "derived" / f"{n}.pcm16.wav"
    derived.parent.mkdir(exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(wav),
            "-ac",
            "1",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(derived),
        ],
        check=True,
    )
    pcm = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(wav),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "s16le",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    samples = array.array("h", pcm)
    peaks = [
        round(max(abs(v) for v in samples[i : i + 1600]) / 32768, 3)
        for i in range(0, len(samples), 1600)
    ]
    audio = dict(
        name=wav.name,
        sha256=digest(wav),
        size_bytes=wav.stat().st_size,
        duration_ms=round(f["duration_seconds"] * 1000),
        format="WAV · mono · 44.1 kHz",
        derived=dict(
            path=f"derived/{n}.pcm16.wav",
            sha256=digest(derived),
            format="WAV · PCM16 · mono · 44.1 kHz",
            media_type="audio/wav",
        ),
        source="TartanAviation KAGC · CC BY 4.0",
        metadata_start=start.isoformat(),
        clock_interpretation="UTC_FOR_DEMO_SOURCE_TIMEZONE_UNVERIFIED",
    )
    # Authored centre-point fixtures, never paired historical observations.
    path = d / f"kagc_adsb_{start:%Y-%m-%d}_{n}.csv"
    points = {}
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        for entity, icao, t, x, y, heading, speed in fixes(n, f["duration_seconds"]):
            tm = start + timedelta(seconds=t)
            writer.writerow(
                dict(
                    ID=icao,
                    Time=str([str(tm.hour), str(tm.minute), str(tm.second)]),
                    Date=str([str(tm.year), str(tm.month), str(tm.day)]),
                    Altitude=1252,
                    Speed=round(speed, 3),
                    Heading=round(heading, 2),
                    Lat=ARP[0] + y / M_PER_DEG_LAT,
                    Lon=ARP[1] + x / M_PER_DEG_LON,
                    Age=0,
                    Range=round(math.hypot(x, y) / 1000, 6),
                    Bearing=round(math.degrees(math.atan2(x, y)), 2),
                    Tail=entity,
                    AltisGNSS=False,
                )
            )
            points.setdefault(entity, []).append(
                [
                    clock(t * 1000),
                    round(x, 2),
                    round(y, 2),
                    round(heading, 2),
                    round(speed, 3),
                ]
            )
    adsb = dict(
        name=path.name,
        sha256=digest(path),
        size_bytes=path.stat().st_size,
        format="CSV · 13 columns",
        label="ADS-B",
        summary=parse(path.read_bytes()).summary(),
        origin="SYNTHETIC",
        coverage="AUTHORED_POINT_ONLY",
    )
    return dict(audio=audio, adsb=adsb, peaks=peaks, start=start, points=points)


def variant(
    main: int, parts: list[int], csv_parts: list[int], assets: dict, cache: dict
) -> dict:
    start = min(assets[p]["start"] for p in parts)
    offsets = {
        p: round((assets[p]["start"] - start).total_seconds() * 1000) for p in parts
    }
    duration = max(offsets[p] + assets[p]["audio"]["duration_ms"] for p in parts)
    segments, live, findings, reminders = [], [], [], []
    scoped = {}
    entities = []
    for p in parts:
        rs = raw_segments(p, cache)
        annotations = ANNOTATIONS[p]
        if len(rs) != len(annotations):
            raise ValueError(
                f"{p}: annotate {len(rs)} segments, got {len(annotations)}"
            )
        keys = []
        for i, (seg, (role, entity)) in enumerate(zip(rs, annotations, strict=True)):
            if entity and p != main:
                entity += " [50]"
            key = f"T-{p}-{i}"
            keys.append(key)
            words = [
                dict(
                    text=w["text"],
                    start_ms=round(w["source_start_s"] * 1000) + offsets[p],
                    end_ms=round(w["source_end_s"] * 1000) + offsets[p],
                )
                for w in seg["words"]
            ]
            begin, end = words[0]["start_ms"], words[-1]["end_ms"]
            scoped[(p, i)] = (key, begin, end, entity)
            if entity and entity not in [x["callsign"] for x in entities]:
                entities.append(
                    dict(
                        callsign=entity,
                        kind="AIRCRAFT",
                        type="Identity candidate",
                        role="Prior clip · Radio context"
                        if p != main
                        else "Radio context",
                        aliases=[],
                    )
                )
            readback = (p, i) in ((50, 3), (51, 2), (123, 1))
            act = (
                "READBACK"
                if readback
                else "REPORT"
                if role == "PILOT"
                else "INSTRUCTION"
                if role == "CONTROLLER"
                else "UNKNOWN"
            )
            if (p, i) in ((51, 0), (50, 2)):
                act = "INFORMATION"
            spec = dict(
                key=key,
                evidence=f"E-{p}-{i}",
                t=clock(begin),
                dur=end - begin,
                ch=0,
                text=seg["text"].strip(),
                act=act,
                role=role,
                entity=entity,
                quality="AMBIGUOUS",
                callsignQuality="AMBIGUOUS",
                latency=400,
                unknowns=[
                    "Speaker and identity are authored candidates; raw STT is unreviewed."
                ],
            )
            instructions = {
                (50, 1): ("TAXI", "13", "Midfield left downwind RWY 13"),
                (50, 4): ("TAKEOFF", "13", "Takeoff clearance RWY 13"),
                (51, 1): ("LAND", "13", "Landing clearance RWY 13"),
                (51, 4): ("UNKNOWN", None, "Separate turnout exchange"),
                (47, 1): ("TAKEOFF", "13", "Takeoff RWY 13; backtaxi if needed"),
                (156, 4): ("UNKNOWN", None, "Maintain 3,000 ft; squawk 4131"),
                (123, 0): ("CONTACT", None, "Contact departure 119.35"),
            }
            if (p, i) in instructions:
                action, runway, summary = instructions[(p, i)]
                spec.update(
                    action=action,
                    runway=runway,
                    runwayQuality="AMBIGUOUS" if runway else "MISSING",
                    effects=dict(
                        instruction="ACTIVE",
                        instructionSummary=summary,
                        interpretation="AMBIGUOUS",
                    ),
                )
            if readback:
                target = f"T-{p}-{1 if p == 50 else i - 1}"
                spec["assoc"] = dict(
                    target=target,
                    relationship="READBACK_OF",
                    status="AMBIGUOUS",
                    unknowns=["Candidate identity; requires audio review."],
                )
                spec["effects"] = dict(
                    readback="AMBIGUOUS",
                    readbackSummary="Candidate response; critical slots require review",
                )
            segments.append(spec)
            live.append(
                dict(
                    key=key,
                    part=str(p),
                    part_start_ms=begin - offsets[p],
                    text=seg["text"].strip(),
                    confidence=seg.get("confidence") or 0,
                    words=words,
                    chunk=f"{p}:{i}",
                    chunk_range_ms=[begin, end],
                )
            )
        for i, title, facts, refs in CARDS[p]:
            key, begin, end, entity = scoped[(p, i)]
            evidence = [scoped[(p, j)][0] for j in refs]
            findings.append(
                dict(
                    key=f"F-{p}-{i}",
                    category="CRITICAL_SLOT_UNCERTAIN",
                    priority="INFO",
                    status="OPEN",
                    entity=entity,
                    t=clock(end),
                    available=clock(end + 800),
                    pending=clock(end + 400),
                    title=title,
                    statement=title
                    + " · cached hypothesis; association requires review.",
                    evidence=evidence,
                    quality="AMBIGUOUS",
                    unknowns=[
                        "Identity and phraseology not human-reviewed.",
                        "No real paired ADS-B for this date.",
                    ],
                    movement="NOT_EVALUABLE",
                    live=dict(
                        title=title,
                        text=" · ".join(v for _, v in facts),
                        facts=[dict(label=k, value=v) for k, v in facts],
                    ),
                )
            )
            if (p, i) in ((50, 3), (51, 2)):
                findings[-1]["slots"] = [
                    dict(slot="RUNWAY", said="13", heard="13", status="AMBIGUOUS"),
                    dict(
                        slot="ACTION",
                        said="Midfield left downwind" if p == 50 else "Clear to land",
                        heard="Downwind repeated"
                        if p == 50
                        else "Landing clearance repeated",
                        status="AMBIGUOUS",
                    ),
                ]
        for i, kind, title in REMINDERS[p]:
            # The row already renders the entity; don't repeat it in its title.
            key, begin, end, entity = scoped[(p, i)]
            base_entity = entity.removesuffix(" [50]")
            if title.startswith(base_entity + " · "):
                title = title[len(base_entity) + 3 :]
            reminders.append(
                dict(
                    key=f"R-{p}-{len(reminders)}",
                    entity=entity,
                    kind=kind,
                    steps=[
                        dict(
                            t=clock(end),
                            available=clock(end + 800),
                            title=title,
                            text="From the recorded transmission",
                            source="ATC",
                        )
                    ],
                    evidence=[key],
                )
            )
    # Continuity across the optional before is candidate-only; no missing gap instructions.
    gaps = [
        dict(start_ms=offsets[a] + assets[a]["audio"]["duration_ms"], end_ms=offsets[b])
        for a, b in zip(parts, parts[1:])
        if offsets[b] > offsets[a] + assets[a]["audio"]["duration_ms"]
    ]
    tracks = [
        dict(
            entity=entity if p == main else entity + " [50]",
            footprint=False,
            waypoints=[
                [clock(round(t * 1000) + offsets[p]), x, y, h, v]
                for time, x, y, h, v in points
                for t in [int(time[:2]) * 60 + float(time[3:])]
            ],
            predicted=[],
            gaps=[],
            **(
                {
                    "staleAfter": clock(
                        offsets[p] + assets[p]["audio"]["duration_ms"] + 6000
                    )
                }
                if p != main
                else {}
            ),
        )
        for p in csv_parts
        for entity, points in assets[p]["points"].items()
    ]
    perms = {
        k: dict(
            state="ALLOWED"
            if k in ("local_read", "reviewer_access", "report_export")
            else "DENIED"
            if k == "audio_export"
            else "UNDETERMINED",
            note="Cached research demo; no cloud processing.",
        )
        for k in (
            "local_read",
            "cloud_audio",
            "cloud_transcript",
            "reviewer_access",
            "report_export",
            "audio_export",
        )
    }
    spec = dict(
        key=f"kagc-additional-{main}",
        title=TITLES[main],
        context="KAGC · Radio review",
        lifecycle="READY",
        analysis="COMPLETED",
        durationMs=duration,
        recordedAt=start.isoformat(),
        updatedAt=start.isoformat(),
        sourceLabel=f"TartanAviation KAGC · {main}.wav",
        sourceKind="PUBLIC_CORPUS",
        layoutVersion=LAYOUT_VERSION,
        channels=[dict(index=0, label="KAGC radio", role="ATC + pilots (mixed)")],
        entities=entities,
        hasTracks=bool(tracks),
        hasLayout=True,
        gaps=gaps,
        permissions=perms,
        retentionDays=30,
        providerAvailable=False,
        speakerIdentity=False,
        runs=[
            dict(
                label="#01", revision=1, status="COMPLETED", createdAt=start.isoformat()
            )
        ],
        segments=segments,
        movements=[],
        tracks=tracks,
        findings=findings,
        reminders=reminders,
        options=[],
        insufficient=[],
        notices=[],
    )
    peaks = []
    for p in parts:
        peaks += [0.0] * max(0, offsets[p] // 100 - len(peaks))
        peaks += assets[p]["peaks"]
    return dict(
        audio_parts=[str(p) for p in parts],
        csv_parts=[str(p) for p in csv_parts],
        duration_ms=duration,
        recordings=[
            dict(
                part=str(p),
                name=f"{p}.wav",
                offset_ms=offsets[p],
                duration_ms=assets[p]["audio"]["duration_ms"],
                recorded_at=assets[p]["start"].isoformat(),
            )
            for p in parts
        ],
        spec=spec,
        live=dict(
            segments=live,
            speakers={
                s["key"]: "ATC"
                if s["role"] == "CONTROLLER"
                else "Pilot"
                if s["role"] == "PILOT"
                else "Unknown speaker"
                for s in segments
            },
            chunk_boundaries_ms=[],
        ),
        peaks=dict(bucket_ms=100, values=peaks),
        layout=layout_view(
            None
            if main == 47
            else dict(
                min_x=250 if main == 123 else -1100,
                max_x=1200,
                min_y=100 if main == 123 else -320,
                max_y=470,
            )
        ),
        stt=dict(
            provider="Google Cloud STT V1 · latest_long · en-US",
            run="Cached research · 11 Oct 2026",
            chunks=sum(len(cache[f"{p}.wav"]["chunks"]) for p in parts),
        ),
        adsb=[
            {
                k: v
                for k, v in assets[p]["adsb"].items()
                if k in ("name", "label", "summary")
            }
            for p in csv_parts
        ],
    )


def main() -> None:
    cache = json.loads(CACHE.read_text())["files"]
    assets = {n: prepare(n, cache) for n in SELECTED}
    for n in SELECTED:
        d = folder(n)
        part_ids = [50, 51] if n == 51 else [n]
        if n == 51:
            for filename in [
                "50.wav",
                "50.txt",
                assets[50]["adsb"]["name"],
                "derived/50.pcm16.wav",
            ]:
                dest = d / filename
                dest.parent.mkdir(exist_ok=True)
                shutil.copyfile(folder(50) / filename, dest)
        variants = {
            variant_key(
                [(str(p), "audio") for p in audio] + [(str(p), "adsb") for p in cs]
            ): variant(n, audio, cs, assets, cache)
            for audio, cs in (
                [([n], [n]), ([50, 51], [51]), ([50, 51], [50, 51])]
                if n == 51
                else [([n], [n])]
            )
        }
        data = dict(
            version=2,
            scenario_id=d.name,
            title=TITLES[n],
            main_part=str(n),
            labels=[
                "PUBLIC_CORPUS audio",
                "STT_HYPOTHESIS",
                "SYNTHETIC authored track",
                "NOT_DOMAIN_VALIDATED",
            ],
            attribution="TartanAviation · Patrikar et al. · CC BY 4.0",
            limits=dict(before=1, after=1),
            parts={
                str(p): dict(
                    position="main" if p == n else "before",
                    recorded_at=assets[p]["start"].isoformat(),
                    audio=assets[p]["audio"],
                    adsb=assets[p]["adsb"],
                )
                for p in part_ids
            },
            variants=variants,
        )
        target = d / "scenario.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, indent=1))
        temporary.replace(target)
        print(n, len(variants), "variants", flush=True)


if __name__ == "__main__":
    main()
