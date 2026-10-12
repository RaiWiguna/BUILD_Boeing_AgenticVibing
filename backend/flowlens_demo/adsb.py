"""Parser and quality report for TartanAviation raw ADS-B CSV (13 columns).

Date/Time are list-strings such as "['19', '3', '13']"; they are parsed with
``ast.literal_eval`` (never ``eval``) and the source strings are kept. Raw rows are never
rewritten; duplicate and partial rows are counted, not silently dropped.
"""

from __future__ import annotations

import ast
import csv
import io
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime

FIELDS = [
    "ID",
    "Time",
    "Date",
    "Altitude",
    "Speed",
    "Heading",
    "Lat",
    "Lon",
    "Age",
    "Range",
    "Bearing",
    "Tail",
    "AltisGNSS",
]


@dataclass
class Observation:
    icao: int
    t: float  # source timestamp, epoch seconds (UTC interpretation, unverified)
    lat: float
    lon: float
    altitude_ft: float | None
    speed_kt: float | None
    heading_deg: float | None
    age_s: float | None
    tail: str
    raw_time: str
    raw_date: str


@dataclass
class AdsbReport:
    total_records: int = 0
    empty_records: int = 0
    truncated_records: int = 0
    malformed_records: int = 0
    position_rows: int = 0
    position_only_rows: int = 0
    duplicate_rows: int = 0
    unique_messages: int = 0
    icao_ids: int = 0
    tails: dict[str, list[str]] = field(default_factory=dict)
    first_utc: str | None = None
    last_utc: str | None = None
    cadence_median_s: float | None = None
    cadence_p95_s: float | None = None
    age_median_s: float | None = None
    age_p95_s: float | None = None
    gaps_over_5s: int = 0
    observations: list[Observation] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        return {k: v for k, v in self.__dict__.items() if k != "observations"}


def _num(v: str) -> float | None:
    v = v.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _parts(v: str) -> list[int] | None:
    try:
        out = ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(out, list) or len(out) != 3:
        return None
    try:
        return [int(x) for x in out]
    except (TypeError, ValueError):
        return None


def _pctl(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def parse(content: bytes) -> AdsbReport:
    rep = AdsbReport()
    text = content.decode("utf-8", errors="replace")
    complete_last = text.endswith("\n")
    lines = text.splitlines()
    if lines and lines[0].strip().split(",")[:2] == ["ID", "Time"]:
        lines = lines[1:]
    seen: set[tuple[int, float]] = set()
    per_id: dict[int, list[Observation]] = {}
    for idx, row in enumerate(csv.reader(io.StringIO("\n".join(lines)))):
        rep.total_records += 1
        if not any(c.strip() for c in row):
            rep.empty_records += 1
            continue
        if len(row) != len(FIELDS):
            if idx == len(lines) - 1 and not complete_last:
                rep.truncated_records += 1
            else:
                rep.malformed_records += 1
            continue
        rec = dict(zip(FIELDS, row, strict=True))
        tm, dt = _parts(rec["Time"]), _parts(rec["Date"])
        lat, lon = _num(rec["Lat"]), _num(rec["Lon"])
        icao = _num(rec["ID"])
        if tm is None or dt is None or lat is None or lon is None or icao is None:
            rep.malformed_records += 1
            continue
        try:
            ts = datetime(dt[0], dt[1], dt[2], tm[0], tm[1], tm[2], tzinfo=UTC).timestamp()
        except ValueError:
            rep.malformed_records += 1
            continue
        rep.position_rows += 1
        speed, heading = _num(rec["Speed"]), _num(rec["Heading"])
        if speed is None or heading is None:
            rep.position_only_rows += 1
        key = (int(icao), ts)
        if key in seen:
            rep.duplicate_rows += 1
            continue
        seen.add(key)
        obs = Observation(
            int(icao),
            ts,
            lat,
            lon,
            _num(rec["Altitude"]),
            speed,
            heading,
            _num(rec["Age"]),
            rec["Tail"].strip(),
            rec["Time"],
            rec["Date"],
        )
        rep.observations.append(obs)
        per_id.setdefault(obs.icao, []).append(obs)
        tails = rep.tails.setdefault(f"{obs.icao:06X}", [])
        if obs.tail and obs.tail not in tails:
            tails.append(obs.tail)
    rep.unique_messages = len(rep.observations)
    rep.icao_ids = len(per_id)
    cadence: list[float] = []
    for series in per_id.values():
        series.sort(key=lambda o: o.t)
        for a, b in zip(series, series[1:], strict=False):
            cadence.append(b.t - a.t)
    rep.gaps_over_5s = sum(1 for c in cadence if c > 5)
    if cadence:
        rep.cadence_median_s = statistics.median(cadence)
        rep.cadence_p95_s = _pctl(cadence, 0.95)
    ages = [o.age_s for o in rep.observations if o.age_s is not None]
    if ages:
        rep.age_median_s = round(statistics.median(ages), 3)
        rep.age_p95_s = round(_pctl(ages, 0.95) or 0, 3)
    if rep.observations:
        ts_all = [o.t for o in rep.observations]
        rep.first_utc = datetime.fromtimestamp(min(ts_all), UTC).isoformat()
        rep.last_utc = datetime.fromtimestamp(max(ts_all), UTC).isoformat()
    return rep
