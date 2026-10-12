"""Generate the SYNTHETIC KAGC ADS-B CSVs aligned with 87.wav and 88.wav (demo scenario).

Calibration comes from the real KAGC raw CSV analysis (27/30 Aug 2022, outputs/tartan-research/
adsb): row cadence, Age, duplicate ratio, position-only and empty records, the list-string
Date/Time format, ground altitude band and low-speed taxi behaviour. The movements themselves are
invented to match the radio exchanges in 87.wav (taxi clearance) and 88.wav (route revision).
Time t is seconds relative to the 88.wav start; the 87 window is negative t.

Usage: python3 scripts/demo/synth_adsb.py [--calibration DIR] [--out FILE] [--events FILE]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowlens_demo.adsb import FIELDS, parse  # noqa: E402
from kagc_layout import ALPHA_Y, B1_Y, BRAVO_X, CHARLIE_X, GOLF_X, RECEIVER, to_latlon  # noqa: E402

SCENARIO_DIR = ROOT / "data" / "demo-scenarios" / "kagc-2022-09-10-88"
CSV_NAME = "kagc_adsb_2022-09-10_88.csv"
CSV_NAME_87 = "kagc_adsb_2022-09-10_87.csv"
# Audio sidecar "Start Time" values (timezone not verified; treated as UTC like the ADS-B recorder).
AUDIO_START = datetime(2022, 9, 10, 19, 3, 13, 318769, tzinfo=UTC)
AUDIO_DURATION_S = 96.905986
AUDIO_START_87 = datetime(2022, 9, 10, 19, 0, 25, 311830, tzinfo=UTC)
ARCHER_T0_X = 147.5  # Archer westbound on A at the 88.wav start, just past Bravo
MPS_TO_KT = 1.943844

Pt = tuple[float, float]


class Mover:
    """Moves along a polyline following a piecewise-linear speed schedule [(t, v_mps)]."""

    def __init__(self, path: list[Pt], schedule: list[tuple[float, float]], start_s: float = 0.0):
        self.path = path
        self.schedule = schedule
        self.seg = [
            math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:], strict=False)
        ]
        self.length = sum(self.seg)
        self.start_s = start_s

    def speed(self, t: float) -> float:
        s = self.schedule
        if t <= s[0][0]:
            return s[0][1]
        for (ta, va), (tb, vb) in zip(s, s[1:], strict=False):
            if ta <= t <= tb:
                return va + (vb - va) * (t - ta) / (tb - ta)
        return s[-1][1]

    def dist(self, t: float) -> float:
        d, x, dt = 0.0, self.start_s, 0.05
        while x < t:
            d += self.speed(x) * dt
            x += dt
        return min(d, self.length)

    def at(self, t: float) -> tuple[Pt, float, float]:
        """(position, speed m/s, track deg) at time t."""
        d = self.dist(t)
        moving = d < self.length and self.speed(t) > 0.05
        for i, L in enumerate(self.seg):
            if d <= L or i == len(self.seg) - 1:
                a, b = self.path[i], self.path[i + 1]
                k = 0 if L == 0 else min(1.0, d / L)
                pos = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
                trk = (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360
                return pos, (self.speed(t) if moving else 0.0), trk
            d -= L
        raise AssertionError


def rounded(path: list[Pt], r: float = 14.0, steps: int = 6) -> list[Pt]:
    """Replace interior corners with short arcs so turns look like real taxi turns."""
    out = [path[0]]
    for i in range(1, len(path) - 1):
        p, c, n = path[i - 1], path[i], path[i + 1]
        d1, d2 = math.hypot(c[0] - p[0], c[1] - p[1]), math.hypot(n[0] - c[0], n[1] - c[1])
        a = (c[0] - (c[0] - p[0]) / d1 * r, c[1] - (c[1] - p[1]) / d1 * r)
        b = (c[0] + (n[0] - c[0]) / d2 * r, c[1] + (n[1] - c[1]) / d2 * r)
        for k in range(steps + 1):
            u = k / steps
            out.append(
                (
                    (1 - u) ** 2 * a[0] + 2 * (1 - u) * u * c[0] + u**2 * b[0],
                    (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * c[1] + u**2 * b[1],
                )
            )
    out.append(path[-1])
    return out


def range_bearing(lat: float, lon: float) -> tuple[float, float]:
    dy = (lat - RECEIVER[0]) * 111.045
    dx = (lon - RECEIVER[1]) * 111.32 * math.cos(math.radians(RECEIVER[0]))
    return math.hypot(dx, dy), math.degrees(math.atan2(dx, dy))


def path_length(path: list[Pt]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:], strict=False))


def ramp_path() -> tuple[list[Pt], list[tuple[float, float]]]:
    """87.wav: ramp → B1 westbound → right onto B → west on A, arriving where 88.wav starts."""
    schedule = [(-40.0, 0.0), (-37.0, 6.5), (-6.0, 6.5), (-2.0, 3.0), (0.0, 3.0)]
    need = Mover([(0.0, 0.0), (1e4, 0.0)], schedule, -40.0).dist(0.0)
    lo, hi = 1.0, 400.0
    for _ in range(60):  # ramp-side B1 length so the rounded path ends exactly at t = 0
        mid = (lo + hi) / 2
        path = rounded(
            [
                (BRAVO_X + mid, B1_Y),
                (BRAVO_X, B1_Y),
                (BRAVO_X, ALPHA_Y),
                (ARCHER_T0_X, ALPHA_Y),
            ],
            r=12.0,
        )
        lo, hi = (mid, hi) if path_length(path) < need else (lo, mid)
    return path, schedule


def build_aircraft() -> list[dict]:
    """Synthetic aircraft. Geometry in local metres (see kagc_layout)."""
    alpha_y, golf_x, c_x = ALPHA_Y, GOLF_X, CHARLIE_X + 0.5
    pre_path, pre_schedule = ramp_path()
    archer_hold_x = CHARLIE_X + 40.0
    archer = {
        "label": "Archer 147G",
        "icao": 0xA0B1C7,
        "tail": "N147G",
        "alt": (1150, 1175),
        "coverage": [
            (-62.0, 38.0),
            (55.0, 97.0),
        ],  # transponder on at the call; stationary ground target drops out (real behaviour)
        "phases": [
            Mover(pre_path, pre_schedule, -40.0),
            Mover(
                [(ARCHER_T0_X, alpha_y), (archer_hold_x, alpha_y)],
                [(0, 3.0), (24, 3.0), (31, 0.0)],
                0.0,
            ),
            Mover(
                rounded([(archer_hold_x, alpha_y), (golf_x, alpha_y), (golf_x, 32.0)], r=12.0),
                [
                    (58.0, 0.0),
                    (61.5, 7.0),
                    (65.5, 7.0),
                    (67.0, 5.0),
                    (70.0, 5.0),
                    (73.0, 9.5),
                    (88.2, 9.5),
                    (92.2, 0.0),
                ],
                58.0,
            ),
        ],
    }
    cessna = {
        "label": "Cessna (opposite direction)",
        "icao": 0xAD5F31,
        "tail": "N5326K",
        "alt": (1175, 1200),
        "coverage": [(-28.0, 74.0)],
        "phases": [
            Mover([(-300.0 - 28 * 6.4, alpha_y), (-300.0, alpha_y)], [(-28.0, 6.4)], -28.0),
            Mover(
                rounded([(-300.0, alpha_y), (c_x, alpha_y), (c_x, -300.0)], r=14.0),
                [(0, 6.4), (44, 6.4), (47, 4.0), (52, 4.0), (56, 6.0), (90, 6.0)],
                0.0,
            ),
        ],
    }
    airborne = {
        "label": "Airborne traffic (outside surface view)",
        "icao": 0xA7E2D4,
        "tail": "N92814",
        "alt": (2300, 2325),
        "coverage": [(-1.0, 97.0)],
        "phases": [Mover([(-4200.0, -3100.0), (4200.0, -3050.0)], [(0, 49.0), (97, 49.0)], 0.0)],
    }
    departing = {
        "label": "Airborne traffic before 88.wav (outside surface view)",
        "icao": 0xA3C1F0,
        "tail": "N3317F",
        "alt": (2650, 2675),
        "coverage": [(-170.0, -61.0)],
        "phases": [Mover([(-3500.0, 2600.0), (5200.0, 2450.0)], [(-170.0, 52.0)], -170.0)],
    }
    return [archer, cessna, airborne, departing]


def state(ac: dict, t: float) -> tuple[Pt, float, float]:
    phases = ac["phases"]
    cur = phases[0]
    for ph in phases:
        if t >= ph.start_s:
            cur = ph
    if cur is not phases[0] and t < cur.schedule[0][0]:
        cur = phases[0]
    return cur.at(t)


def covered(ac: dict, t: float) -> bool:
    return any(a <= t <= b for a, b in ac["coverage"])


WINDOWS = {
    # name: (first recorder second, seconds, seed, forced empty rows)
    "88": (AUDIO_START.replace(microsecond=0), int(AUDIO_DURATION_S) + 2, 88, (21, 63)),
    # 87.wav start up to the second before 88.wav (the recorder keeps running across the audio gap).
    "87": (AUDIO_START_87.replace(microsecond=0), 168, 87, (34, 131)),
}


def generate(window: str = "88") -> tuple[list[list[str]], list[dict]]:
    first, n_seconds, seed, blanks = WINDOWS[window]
    rng = random.Random(seed)
    rows: list[list[str]] = []
    truth: list[dict] = []
    aircraft = build_aircraft()
    last_msg: dict[int, dict] = {}
    for k in range(n_seconds):
        utc = first + timedelta(seconds=k)
        t = (utc - AUDIO_START).total_seconds()
        if k in blanks or rng.random() < 0.004:
            rows.append([""] * len(FIELDS))
        for ac in aircraft:
            if not covered(ac, t):
                prev = last_msg.pop(ac["icao"], None)
                if prev is not None:  # final stale row: Age near the recorder's 60 s horizon
                    rows.append(prev["row"][:8] + [f"{59 + rng.random():.6f}"] + prev["row"][9:])
                continue
            # Real cadence: mostly every second, occasional 2-6 s silences.
            if ac["icao"] in last_msg and rng.random() < 0.09:
                continue
            (x, y), v, trk = state(ac, t)
            jitter = 0.0 if v == 0 else 1.2
            x += rng.gauss(0, jitter)
            y += rng.gauss(0, jitter)
            lat, lon = to_latlon(x, y)
            prev = last_msg.get(ac["icao"])
            new_msg = prev is None or v > 0 or rng.random() < 0.25
            if not new_msg:
                lat, lon = prev["lat"], prev["lon"]
            rng_km, brg = range_bearing(lat, lon)
            lo, hi = ac["alt"]
            alt = rng.choice([lo, lo, hi]) if ac["icao"] not in (0xA7E2D4, 0xA3C1F0) else lo
            speed_kt = round(v * MPS_TO_KT)
            pos_only = rng.random() < 0.012
            tail = "" if rng.random() < 0.03 else ac["tail"]
            age = rng.uniform(0.6, 2.0) if new_msg else (prev["age"] if prev else 1.0)
            row = [
                str(ac["icao"]),
                str([str(utc.hour), str(utc.minute), str(utc.second)]),
                str([str(utc.year), str(utc.month), str(utc.day)]),
                str(alt),
                "" if pos_only else str(speed_kt),
                "" if pos_only else str(round(trk) % 360),
                f"{lat:.6f}",
                f"{lon:.6f}",
                f"{age:.6f}",
                repr(rng_km),
                repr(brg),
                tail,
                "False",
            ]
            last_msg[ac["icao"]] = {"row": row, "lat": lat, "lon": lon, "age": age}
            # Recorder polls repeat the same message (~63 % duplicate rows in the real CSVs).
            for _ in range(
                1 + (1 if rng.random() < 0.85 else 0) + (1 if rng.random() < 0.6 else 0)
            ):
                rows.append(row)
            truth.append(
                {
                    "icao": f"{ac['icao']:06X}",
                    "label": ac["label"],
                    "t": round(t, 3),
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "speed_mps": round(v, 2),
                    "track_deg": round(trk, 1),
                }
            )
    return rows, truth


def crossing_events(truth: list[dict]) -> dict[str, float | None]:
    """Times (audio seconds) when the synthetic Archer enters/leaves the 10/28 strip and stops."""
    pts = [p for p in truth if p["icao"] == f"{0xA0B1C7:06X}" and p["t"] > 55]
    enter = next((p["t"] for p in pts if p["y"] > -38.0), None)
    leave = next((p["t"] for p in pts if p["y"] > 8.0), None)
    stop = next((p["t"] for p in pts if p["y"] > 8.0 and p["speed_mps"] == 0), None)
    return {"runway_10_28_enter_s": enter, "runway_10_28_exit_s": leave, "stopped_short_13_s": stop}


def traffic_events(truth: list[dict]) -> dict[str, float]:
    """Archer/Cessna opposite-direction facts on Alpha (audio seconds, metres, knots)."""
    archer = {round(p["t"]): p for p in truth if p["icao"] == f"{0xA0B1C7:06X}"}
    cessna = {round(p["t"]): p for p in truth if p["icao"] == f"{0xAD5F31:06X}"}
    both = sorted(t for t in archer if t in cessna and t >= 0)
    first = both[0]
    a0, c0 = archer[first], cessna[first]
    hold = next(t for t in sorted(archer) if t > 10 and archer[t]["speed_mps"] == 0)
    off_a = next(t for t in sorted(cessna) if t > 0 and cessna[t]["y"] < ALPHA_Y - 20)
    closest = min(
        math.hypot(archer[t]["x"] - cessna[t]["x"], archer[t]["y"] - cessna[t]["y"])
        for t in both
        if t <= off_a
    )
    return {
        "start_s": archer[first]["t"],
        "start_distance_m": round(math.hypot(a0["x"] - c0["x"], a0["y"] - c0["y"])),
        "archer_kt": round(a0["speed_mps"] * MPS_TO_KT),
        "cessna_kt": round(c0["speed_mps"] * MPS_TO_KT),
        "archer_hold_s": archer[hold]["t"],
        "cessna_off_alpha_s": cessna[off_a]["t"],
        "closest_m": round(closest),
    }


def write_csv(path: Path, rows: list[list[str]], tail: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(FIELDS)
        w.writerows(rows)
        # Real CSVs end with a truncated final record (recorder stopped mid-write).
        fh.write(tail)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=SCENARIO_DIR)
    ap.add_argument(
        "--calibration", type=Path, default=ROOT / "outputs" / "tartan-research" / "adsb"
    )
    args = ap.parse_args()
    rows, truth = generate("88")
    out = args.dir / CSV_NAME
    write_csv(out, rows, f"{0xA7E2D4},\"['19', '4', '5")
    rows87, truth87 = generate("87")
    out87 = args.dir / CSV_NAME_87
    write_csv(out87, rows87, f"{0xA0B1C7},\"['19', '3', '1")
    events = crossing_events(truth)
    rep = parse(out.read_bytes())
    rep87 = parse(out87.read_bytes())
    report = {"synthetic": rep.summary(), "synthetic_87": rep87.summary(), "events": events}
    cal_files = {
        "analysis": args.calibration / "analysis.json",
        "quality": args.calibration / "quality-extra.json",
    }
    if all(p.exists() for p in cal_files.values()):
        real = json.loads(cal_files["analysis"].read_text())
        report["calibration"] = [
            {
                "day": d["day"],
                "duplicate_ratio": round(d["duplicate_rows"] / d["valid_rows"], 3),
                "cadence_s": d["cadence_seconds"],
                "age_s": d["age_seconds"],
                "altitude_band_ft_near_slow": "1075-1200 (low-speed near-airport points)",
            }
            for d in real
        ]
    report["synthetic_duplicate_ratio"] = round(rep.duplicate_rows / max(1, rep.position_rows), 3)
    derived = args.dir / "derived"
    derived.mkdir(exist_ok=True)
    (derived / "adsb-synthetic-truth.json").write_text(json.dumps(truth))
    (derived / "adsb-synthetic-truth-87.json").write_text(json.dumps(truth87))
    (derived / "adsb-calibration-report.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "events": events,
                "synthetic": rep.summary(),
                "synthetic_87": rep87.summary(),
                "dup_ratio": report["synthetic_duplicate_ratio"],
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
