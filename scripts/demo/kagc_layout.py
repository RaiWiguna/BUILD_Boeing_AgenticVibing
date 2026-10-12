"""KAGC surface layout for the demo scenario.

Runway ends come from public runway-end coordinates (AirNav, retrieved 12 Oct 2026; current data,
not a surveyed 2022 layout). The runways really intersect (13/31 crosses 10/28 about 125 m east of
the ARP). Taxiways and hold lines are a schematic of the real arrangement (OpenStreetMap: A parallel
south of 10/28 and crossing 13/31, C and G crossing 28 towards 13/31, B near the south ramp), laid
out so the 87.wav/88.wav route story fits; they are not a surveyed taxiway graph.
"""

from __future__ import annotations

import math

LAYOUT_VERSION = "kagc-2"

# Local metric frame: equirectangular around the airport reference point (accurate to well
# under a metre over the ~2 km extent used here).
ARP = (40.3544376, -79.9290467)
M_PER_DEG_LAT = 111_045.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(ARP[0]))

# ADS-B receiver reference inferred from Range/Bearing in the real KAGC CSV (diagnostic).
RECEIVER = (40.35132142239519, -79.92398867653723)

RUNWAYS = [
    {
        "id": "10/28",
        "ends": ("10", "28"),
        "a": (40.3542842, -79.9410996),
        "b": (40.3543109, -79.9177762),
        "width_m": 46.0,
    },
    {
        "id": "13/31",
        "ends": ("13", "31"),
        "a": (40.3572940, -79.9343298),
        "b": (40.3520574, -79.9224336),
        "width_m": 30.0,
    },
]

# Taxiways and hold lines in local metres (x east, y north of the ARP). They keep the real
# relationships that matter for the radio story: Alpha is the parallel south of 10/28 and crosses
# 13/31 (hold lines on both sides); Bravo/B1 lead from the south ramp to Alpha clear of 13/31;
# Charlie runs from the ramp to a hold line short of 28; Golf, west of Charlie, crosses 28 and ends
# at the runway 13/31 edge behind a hold line. Distances along Alpha are compressed relative to
# the airport diagram so the recorded movements fit the recording window.
ALPHA_Y = -126.3
BRAVO_X = 170.0
B1_Y = -246.0
CHARLIE_X = 25.0
GOLF_X = -47.0

_XY_TAXIWAYS = [
    {
        "id": "TWY-A",
        "label": "TWY A",
        "xy": [(-800.0, ALPHA_Y), (760.0, ALPHA_Y)],
        "label_xy": (-250.0, ALPHA_Y - 14.0),
    },
    {
        "id": "TWY-B",
        "label": "TWY B",
        "xy": [(BRAVO_X, ALPHA_Y), (BRAVO_X, -285.0)],
        "label_xy": (BRAVO_X - 14.0, -195.0),
    },
    {
        "id": "TWY-B1",
        "label": "B1",
        "xy": [(BRAVO_X, B1_Y), (BRAVO_X + 120.0, B1_Y)],
        "label_xy": (BRAVO_X + 95.0, B1_Y - 12.0),
    },
    {
        "id": "TWY-C",
        "label": "TWY C",
        "xy": [(CHARLIE_X, -38.0), (CHARLIE_X, -300.0)],
        "label_xy": (CHARLIE_X + 14.0, -200.0),
    },
    {
        "id": "TWY-G",
        "label": "TWY G",
        "xy": [(GOLF_X, ALPHA_Y), (GOLF_X, 68.0)],
        "label_xy": (GOLF_X - 16.0, -60.0),
    },
]

# axis: the direction the taxiway runs; the bar is drawn across it.
HOLD_LINES = [
    {"id": "HL-G28", "label": "Hold line RWY 10/28 · G", "runway": "10/28", "xy": (GOLF_X, -87.5), "axis": "y"},
    {"id": "HL-G13", "label": "Hold line RWY 13 · G", "runway": "13/31", "xy": (GOLF_X, 40.0), "axis": "y"},
    {"id": "HL-C28", "label": "Hold line RWY 10/28 · C", "runway": "10/28", "xy": (CHARLIE_X, -87.5), "axis": "y"},
    {"id": "HL-A13W", "label": "Hold line RWY 13/31 · A", "runway": "13/31", "xy": (239.0, ALPHA_Y), "axis": "x"},
    {"id": "HL-A13E", "label": "Hold line RWY 13/31 · A", "runway": "13/31", "xy": (399.0, ALPHA_Y), "axis": "x"},
    {"id": "HL-AC", "label": "Hold short C on A", "runway": None, "xy": (CHARLIE_X + 34.0, ALPHA_Y), "axis": "x"},
]  # fmt: skip


def to_xy(lat: float, lon: float) -> tuple[float, float]:
    return ((lon - ARP[1]) * M_PER_DEG_LON, (lat - ARP[0]) * M_PER_DEG_LAT)


def to_latlon(x: float, y: float) -> tuple[float, float]:
    return (ARP[0] + y / M_PER_DEG_LAT, ARP[1] + x / M_PER_DEG_LON)


def _r(v: float) -> float:
    return round(v, 1)


def runway_polygon(rwy: dict) -> list[list[float]]:
    ax, ay = to_xy(*rwy["a"])
    bx, by = to_xy(*rwy["b"])
    length = math.hypot(bx - ax, by - ay)
    nx, ny = -(by - ay) / length, (bx - ax) / length
    h = rwy["width_m"] / 2
    return [
        [_r(ax + nx * h), _r(ay + ny * h)],
        [_r(bx + nx * h), _r(by + ny * h)],
        [_r(bx - nx * h), _r(by - ny * h)],
        [_r(ax - nx * h), _r(ay - ny * h)],
    ]


FOCUS_88 = {"min_x": -380.0, "max_x": 280.0, "min_y": -270.0, "max_y": 110.0}
FOCUS_WITH_87 = {"min_x": -380.0, "max_x": 450.0, "min_y": -300.0, "max_y": 110.0}


def layout_view(focus: dict | None = None) -> dict:
    """LayoutView-shaped dict (frontend PROPOSED_CONTRACT) in local metres."""
    runways = []
    for rwy in RUNWAYS:
        a, b = to_xy(*rwy["a"]), to_xy(*rwy["b"])
        runways.append(
            {
                "id": rwy["id"],
                "ends": list(rwy["ends"]),
                "polygon": runway_polygon(rwy),
                "centerline": [[_r(a[0]), _r(a[1])], [_r(b[0]), _r(b[1])]],
            }
        )
    taxiways = [
        {
            "id": t["id"],
            "label": t["label"],
            "path": [[_r(x), _r(y)] for x, y in t["xy"]],
            "label_at": [_r(c) for c in t["label_xy"]],
        }
        for t in _XY_TAXIWAYS
    ]
    hold_lines = []
    for h in HOLD_LINES:
        x, y = h["xy"]
        pts = (
            [[_r(x - 16), _r(y)], [_r(x + 16), _r(y)]]
            if h["axis"] == "y"
            else [[_r(x), _r(y - 16)], [_r(x), _r(y + 16)]]
        )
        hold_lines.append(
            {"id": h["id"], "label": h["label"], "runway": h["runway"] or "", "points": pts}
        )
    xs = [p[0] for r in runways for p in r["polygon"]]
    ys = [p[1] for r in runways for p in r["polygon"]] + [p[1] for t in taxiways for p in t["path"]]
    return {
        "version": LAYOUT_VERSION,
        "units": "m",
        "caption": "KAGC",
        "runways": runways,
        "hold_lines": hold_lines,
        "taxiways": taxiways,
        "bounds": {
            "min_x": _r(min(xs) - 60),
            "max_x": _r(max(xs) + 60),
            "min_y": _r(min(ys) - 60),
            "max_y": _r(max(ys) + 60),
        },
        # Focus window for the surface view (the recorded route), in metres.
        "focus": dict(focus or FOCUS_88),
    }
