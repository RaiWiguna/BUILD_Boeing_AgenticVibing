"""Private, validated scenario catalogue; public views omit future actions and initial truth."""
import json
from pathlib import Path
from typing import Any

from pydantic import Field

from .models import Contract, SimulationConfig

LAYOUT: dict[str, Any] = {
    "id": "synthetic-lab", "version": "1.0", "name": "FlowLens Research Airfield",
    "coordinate_system": "LOCAL_METRES", "physical_runway_id": "RWY-09-27",
    "runway": [[0, -22.5], [3000, -22.5], [3000, 22.5], [0, 22.5]],
    "protected_area": [[0, -75], [3000, -75], [3000, 75], [0, 75]],
    "taxiways": [[[0, -160], [3000, -160]], [[1500, -260], [1500, 260]],
                 [[300, -160], [300, -75]], [[2700, -160], [2700, -75]]],
    "hold_lines": [[[1470, -95], [1530, -95]], [[1470, 95], [1530, 95]]],
    "directions": {"27": "RWY-09-27", "09": "RWY-09-27"},
    "note": "Synthetic geometry; protected-area dimensions are experiment assumptions, not airport standards.",
}


class Scenario(Contract):
    id: str
    title: str
    objective: str
    variant: str
    duration_s: int = Field(ge=30, le=1800)
    low_visibility: bool = False
    emergency: bool = False

    def public(self) -> dict:
        return {"id": self.id, "title": self.title, "objective": self.objective,
                "version": "1.0", "duration_s": self.duration_s,
                "aircraft_count": 5, "vehicle_count": 2,
                "domain_review": "NOT_YET_REVIEWED"}


CATALOGUE = {s.id: s for s in (
    Scenario.model_validate(row) for row in json.loads(
        (Path(__file__).parent / "data" / "scenarios.json").read_text(encoding="utf-8")
    )
)}


def scenario_config(scenario: Scenario) -> SimulationConfig:
    return SimulationConfig(low_visibility=scenario.low_visibility, emergency=scenario.emergency)


def initial_mobiles(variant: str) -> dict[str, dict]:
    def aircraft(id, x, y, speed, phase, route, runway="27"):
        return {"id": id, "callsign": id, "kind": "aircraft", "x_m": x, "y_m": y,
                "speed_mps": speed, "nominal_speed_mps": speed, "heading_deg": 0,
                "phase": phase, "length_m": 38, "width_m": 35, "runway": runway,
                "route": route, "owner": "tower", "route_index": 0}
    distance = 9000 if variant == "safe" else 3333.6
    rows = [
        aircraft("BAW123", -distance, 0, 145 * 1852 / 3600, "final", [(3600, 0)]),
        aircraft("SIA456", -14500, 480, 0, "downwind", []),
        aircraft("GA712", 2650, -160, 0, "taxi", [], "09"),
        aircraft("QZ804", 300, -160, 0, "taxi", []),
        aircraft("JTA610", -18000, -420, 0, "downwind", []),
        {"id": "ARFF-2", "callsign": "ARFF-2", "kind": "vehicle", "x_m": 1500,
         "y_m": -65 if variant not in {"hold", "violation"} else -110,
         "speed_mps": 0 if variant in {"hold", "stopped"} else 146 / 58,
         "nominal_speed_mps": 146 / 58, "heading_deg": 90, "phase": "holding" if variant == "hold" else "crossing",
         "length_m": 12, "width_m": 3, "runway": "27", "route": [(1500, 260)],
         "owner": "ground", "route_index": 0},
        {"id": "OPS-1", "callsign": "OPS-1", "kind": "vehicle", "x_m": 2300, "y_m": -260,
         "speed_mps": 0, "nominal_speed_mps": 5, "heading_deg": 0, "phase": "holding",
         "length_m": 6, "width_m": 2, "runway": "27", "route": [], "owner": "ground", "route_index": 0},
    ]
    if variant == "reciprocal":
        rows[2] = aircraft("GA712", 2900, 0, 45, "takeoff_roll", [(-800, 0)], "09")
        rows[5]["y_m"] = -260
        rows[5]["speed_mps"] = 0
    return {row["id"]: row for row in rows}


def scheduled_actions(variant: str) -> list[tuple[int, str, str, float]]:
    return {
        "cancel": [(10000, "CANCEL", "ARFF-2", 0)],
        "goaround": [(10000, "GO_AROUND", "BAW123", 0)],
        "dropout": [(10000, "DROPOUT", "ARFF-2", 30)],
    }.get(variant, [])
