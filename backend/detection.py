"""Deterministic detector. Accepts observed contracts only, never simulator plans."""
import math
from itertools import combinations
from typing import Any

from shapely.affinity import rotate, translate
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box

from .models import ENGINE_VERSION, Clearance, Instruction, SimulationConfig, Track
from .scenarios import LAYOUT

PROTECTED = Polygon(LAYOUT["protected_area"])


def footprint(track: Track) -> Polygon:
    rect = box(-track.length_m / 2, -track.width_m / 2, track.length_m / 2, track.width_m / 2)
    return translate(rotate(rect, track.heading_deg, origin=(0, 0)), track.x_m, track.y_m)


def expanded_area(track: Track, heading: float) -> Polygon:
    """Minkowski sum for the convex synthetic area and oriented rectangular footprint."""
    rect = rotate(box(-track.length_m / 2, -track.width_m / 2,
                      track.length_m / 2, track.width_m / 2), heading, origin=(0, 0))
    points = [(x - dx, y - dy) for x, y in PROTECTED.exterior.coords
              for dx, dy in rect.exterior.coords]
    return MultiPoint(points).convex_hull


def overlap(a: dict, b: dict) -> float:
    return max(0.0, min(a["exit_s"], b["exit_s"]) - max(a["entry_s"], b["entry_s"]))


def predict(track: Track, now_ms: int, config: SimulationConfig) -> list[dict]:
    if track.phase in {"go_around", "departed", "downwind"}:
        return []
    occupied = footprint(track).intersects(PROTECTED)
    if track.speed_mps < 0.05:
        return ([{"entry_s": 0.0, "exit_s": float(config.horizon_s), "exit_unknown": True}]
                if occupied else [])
    if not track.route:
        return ([{"entry_s": 0.0, "exit_s": float(config.horizon_s), "exit_unknown": True}]
                if occupied else [])
    age_s = max(0, now_ms - track.observed_ms) / 1000
    elapsed = 0.0
    current = (track.x_m, track.y_m)
    intervals = []
    # Route is declared intent. Future speed changes and planned events are not inputs.
    for endpoint in track.route:
        endpoint = tuple(endpoint)
        distance = math.dist(current, endpoint)
        if distance < 1e-8:
            current = endpoint
            continue
        heading = math.degrees(math.atan2(endpoint[1] - current[1], endpoint[0] - current[0]))
        segment = LineString([current, endpoint])
        clipped = segment.intersection(expanded_area(track, heading))
        if not clipped.is_empty:
            geometries = list(clipped.geoms) if hasattr(clipped, "geoms") else [clipped]
            for part in geometries:
                if isinstance(part, Point):
                    distances = [segment.project(part)]
                elif isinstance(part, LineString):
                    distances = [segment.project(Point(p)) for p in part.coords]
                else:
                    continue
                enter = elapsed + min(distances) / track.speed_mps - age_s
                leave = elapsed + max(distances) / track.speed_mps - age_s
                if leave >= 0 and enter <= config.horizon_s:
                    intervals.append({"entry_s": max(0.0, enter),
                                      "exit_s": min(float(config.horizon_s), leave),
                                      "exit_unknown": False})
        elapsed += distance / track.speed_mps
        current = endpoint
        if elapsed - age_s > config.horizon_s:
            break
    merged: list[dict] = []
    for interval in sorted(intervals, key=lambda v: v["entry_s"]):
        if merged and interval["entry_s"] <= merged[-1]["exit_s"] + 1e-6:
            merged[-1]["exit_s"] = max(merged[-1]["exit_s"], interval["exit_s"])
        else:
            merged.append(interval)
    # A moving object whose declared route ends inside the area has no observed exit plan.
    if occupied and not merged:
        return [{"entry_s": 0.0, "exit_s": float(config.horizon_s), "exit_unknown": True}]
    if merged and Point(current).within(expanded_area(track, track.heading_deg)) and elapsed - age_s < config.horizon_s:
        merged[-1]["exit_s"] = float(config.horizon_s)
        merged[-1]["exit_unknown"] = True
    return merged


def threshold_eta(track: Track, now_ms: int) -> float | None:
    if track.phase != "final" or track.speed_mps < 0.05 or not track.route:
        return None
    current = (track.x_m, track.y_m)
    accumulated = 0.0
    threshold_x = 0 if track.runway == "27" else 3000
    for endpoint in track.route:
        x, y = endpoint
        if min(current[0], x) <= threshold_x <= max(current[0], x) and abs(x-current[0]) > 1e-8:
            fraction = (threshold_x-current[0]) / (x-current[0])
            crossing_y = current[1] + fraction * (y-current[1])
            if abs(crossing_y) > 75:
                return None
            distance = accumulated + fraction * math.dist(current, endpoint)
            return max(0.0, distance/track.speed_mps - max(0, now_ms-track.observed_ms)/1000)
        accumulated += math.dist(current, endpoint)
        current = tuple(endpoint)
    return None


def detect(tracks: dict[str, Track], clearances: list[Clearance], now_ms: int,
           config: SimulationConfig, runway_open: bool, expected_ids: list[str],
           previous_tracks: dict[str, Track] | None = None) -> dict[str, Any]:
    active = {c.target: c for c in clearances if c.status == "ISSUED"}
    stale = {id for id, t in tracks.items() if now_ms - t.observed_ms > config.stale_ms}
    missing = set(expected_ids) - tracks.keys()
    fresh = {id: t for id, t in tracks.items() if id not in stale}
    predictions = []
    candidates = []
    occupied_ids = []
    unknown_routes = set()

    def evidence(objects: list[str]) -> list[str]:
        result = [tracks[id].event_id for id in objects if id in tracks]
        result += [active[id].event_id for id in objects if id in active]
        return list(dict.fromkeys(result))

    def candidate(rule, objects, severity, reason, metrics=None):
        objects = sorted(objects)
        candidates.append({"key": ":".join([rule, "RWY-09-27", *objects]),
                           "rule": rule, "rule_version": ENGINE_VERSION, "objects": objects,
                           "runway": "RWY-09-27", "severity": severity, "reason": reason,
                           "metrics": metrics or {}, "evidence_event_ids": evidence(objects),
                           "calculated_ms": now_ms,
                           "track_ages_ms": {id: now_ms-tracks[id].observed_ms for id in objects if id in tracks},
                           "assumptions": "Current speed and declared route continue; synthetic protection geometry.",
                           "data_degraded": any(id in stale or id in missing for id in objects)})

    for id, track in tracks.items():
        if track.phase not in {"go_around", "departed", "downwind"} and footprint(track).intersects(PROTECTED):
            occupied_ids.append(id)
        if id in stale:
            continue
        if track.speed_mps > 0.05 and not track.route and track.phase not in {"downwind", "departed", "go_around"}:
            unknown_routes.add(id)
        intervals = predict(track, now_ms, config)
        for index, interval in enumerate(intervals):
            uncertainty = config.position_error_m/max(track.speed_mps, 0.05)
            uncertainty += interval["entry_s"]*config.speed_error_fraction
            predictions.append({"object_id": id, "physical_runway_id": "RWY-09-27",
                                "direction": track.runway, "interval_index": index, **interval,
                                "assumed_entry_range_s": [max(0.0, interval["entry_s"]-uncertainty),
                                                          interval["entry_s"]+uncertainty],
                                "assumed_exit_range_s": [max(0.0, interval["exit_s"]-uncertainty),
                                                         min(float(config.horizon_s), interval["exit_s"]+uncertainty)],
                                "threshold_eta_s": threshold_eta(track, now_ms),
                                "model_version": ENGINE_VERSION,
                                "source_event_id": track.event_id})
        clearance = active.get(id)
        if clearance and clearance.instruction == Instruction.HOLD_SHORT:
            crossed_hold = track.kind == "vehicle" and abs(track.x_m-1500) < 40 and abs(track.y_m) < 95
            old = (previous_tracks or {}).get(id)
            swept_hold = bool(old and track.kind == "vehicle" and
                              abs(track.x_m-1500) < 40 and
                              ((old.y_m < -95 <= track.y_m) or (old.y_m > 95 >= track.y_m)))
            if id in occupied_ids or crossed_hold or swept_hold:
                candidate("HOLD_VIOLATION", [id], "WARNING", "Observed movement violates active HOLD SHORT.")
        if not runway_open and (intervals or (clearance and clearance.instruction != Instruction.HOLD_SHORT)):
            candidate("CLOSED_RUNWAY", [id], "CRITICAL" if id in occupied_ids else "WARNING",
                      "Observed or instructed use of a closed simulated runway.")

    for a, b in combinations(predictions, 2):
        if a["object_id"] == b["object_id"]:
            continue
        ta, tb = fresh[a["object_id"]], fresh[b["object_id"]]
        if ta.kind == tb.kind == "vehicle":
            continue
        amount = overlap(a, b)
        start = max(a["entry_s"], b["entry_s"])
        margin = max(a["entry_s"], b["entry_s"])-min(a["exit_s"], b["exit_s"])
        assumed_a = {"entry_s": a["assumed_entry_range_s"][0],
                     "exit_s": a["assumed_exit_range_s"][1]+config.buffer_s}
        assumed_b = {"entry_s": b["assumed_entry_range_s"][0],
                     "exit_s": b["assumed_exit_range_s"][1]+config.buffer_s}
        if amount > 1e-6 or overlap(assumed_a, assumed_b) > 0:
            rule = "DEPARTURE_OCCUPANCY" if "takeoff_roll" in {ta.phase, tb.phase} else "ARRIVAL_OCCUPANCY"
            candidate(rule, [ta.id, tb.id],
                      "CRITICAL" if amount > 0 and start <= 30 else "WARNING" if amount > 0 else "ADVISORY",
                      "Predicted simultaneous runway-area occupancy; this is not a collision-time estimate."
                      if amount > 0 else "Only the assumed error range / experiment buffer overlaps.",
                      {"overlap_s": amount, "start_s": start, "margin_s": margin,
                       "intervals": [a, b], "buffer_s": config.buffer_s})

    for ca, cb in combinations(active.values(), 2):
        if ca.target == cb.target:
            continue
        use = {Instruction.LAND, Instruction.TAKEOFF, Instruction.CROSS_RUNWAY, Instruction.LINE_UP_AND_WAIT}
        if ca.instruction in use and cb.instruction in use:
            # Local SOP: simultaneous runway permissions require explicit attention.
            # Permission conflict is independent of physical occupancy.
            candidate("CLEARANCE_INCONSISTENCY", [ca.target, cb.target], "ADVISORY",
                      "Concurrent runway-use permissions under lab SOP; inspect movement and timing.")

    for id in sorted(stale | missing | unknown_routes):
        candidate("TRACKING_DEGRADED", [id], "DATA_DEGRADED",
                  "Track missing, stale, or moving without a known route; clear state cannot be established.")
    # A fast observed transit must not disappear between samples.
    for id, old in (previous_tracks or {}).items():
        new = fresh.get(id)
        if new and new.observed_ms > old.observed_ms and new.kind == "vehicle":
            swept = LineString([(old.x_m, old.y_m), (new.x_m, new.y_m)])
            if swept.length and swept.intersects(PROTECTED) and id not in occupied_ids:
                for other in occupied_ids:
                    if tracks[other].kind == "aircraft":
                        candidate("SWEPT_OCCUPANCY", [id, other], "WARNING",
                                  "Sample-to-sample transit intersects runway area; exact simultaneous occupancy is uncertain.")
    degraded_ids = sorted(stale | missing | unknown_routes)
    return {"predictions": predictions, "candidates": candidates,
            "runway": {"physical_id": "RWY-09-27", "open": runway_open,
                       "observed_occupants": occupied_ids, "data_quality": "DEGRADED" if degraded_ids else "NOMINAL",
                       "degraded_ids": degraded_ids,
                       "state": "OCCUPIED_LAST_KNOWN" if occupied_ids and degraded_ids else "OCCUPIED"
                       if occupied_ids else "UNKNOWN" if degraded_ids else "NO_OCCUPANCY_OBSERVED"}}


def task_complexity(tracks: dict[str, Track], clearances: list[Clearance], requests: list[dict],
                    events: list[dict], now_ms: int, config: SimulationConfig, role: str) -> dict:
    relevant = [t for t in tracks.values() if t.owner == role]
    spans = sorted((max(now_ms-60000, e["sim_ms"]), min(now_ms, e["sim_ms"]+e["duration_ms"]))
                   for e in events if e.get("channel") == role and e.get("duration_ms")
                   and e["sim_ms"] <= now_ms and e["sim_ms"]+e["duration_ms"] > now_ms-60000)
    occupied = 0
    end = now_ms-60000
    for start, stop in spans:
        occupied += max(0, stop-max(start, end))
        end = max(end, stop)
    pending = sum(c.status == "ISSUED" and c.readback == "PENDING"
                  and c.target in {t.id for t in relevant} for c in clearances)
    crossings = sum(not r["completed"] for r in requests)
    components = {"traffic": min(1.0, len(relevant)/7), "communication": occupied/60000,
                  "pending_tasks": min(1.0, (pending+crossings)/5),
                  "crossing_activity": min(1.0, crossings/2),
                  "low_visibility": float(config.low_visibility), "emergency": float(config.emergency)}
    weights = {"traffic": .25, "communication": .25, "pending_tasks": .20,
               "crossing_activity": .15, "low_visibility": .10, "emergency": .05}
    score = sum(components[k]*weights[k] for k in components)*100
    return {"score": round(score, 1), "level": "LOW" if score < 25 else "MEDIUM" if score < 50
            else "HIGH" if score < 75 else "VERY_HIGH", "components": components, "weights": weights,
            "label": "Experimental task complexity; not an individual workload or fatigue diagnosis.",
            "model_version": "complexity-1"}
