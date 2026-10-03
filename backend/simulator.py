"""Private truth simulator and observation channel. No detector is imported into this module."""
import copy
import math
import random
from typing import Any

from .models import SimulationConfig, Track
from .scenarios import initial_mobiles, scheduled_actions


class Simulator:
    def __init__(self, variant: str, seed: int, config: SimulationConfig):
        self.config = config
        self.mobiles = initial_mobiles(variant)
        self.actions = scheduled_actions(variant)
        self.action_index = 0
        self.rng = random.Random(seed)
        self.queue: list[dict] = []
        self.dropout_until: dict[str, int] = {}
        self.responses: list[tuple[int, str, str]] = []
        self.now_ms = 0
        self.sample()

    def sample(self) -> None:
        for id, obj in self.mobiles.items():
            if self.dropout_until.get(id, -1) > self.now_ms:
                continue
            fields = {k: copy.deepcopy(v) for k, v in obj.items()
                      if k not in {"nominal_speed_mps", "route_index"}}
            fields["x_m"] += self.rng.uniform(-self.config.noise_m, self.config.noise_m)
            fields["y_m"] += self.rng.uniform(-self.config.noise_m, self.config.noise_m)
            fields["route"] = copy.deepcopy(obj["route"][obj["route_index"]:])
            fields.update(observed_ms=self.now_ms, received_ms=self.now_ms+self.config.delay_ms,
                          source="simulated-surface", event_id="pending")
            self.queue.append(fields)

    def step(self) -> list[tuple[str, str, float]]:
        self.now_ms += self.config.tick_ms
        dt = self.config.tick_ms/1000
        for obj in self.mobiles.values():
            remaining = obj["speed_mps"]*dt
            while remaining > 0 and obj["route_index"] < len(obj["route"]):
                dest = obj["route"][obj["route_index"]]
                distance = math.dist((obj["x_m"], obj["y_m"]), dest)
                if distance < 1e-8:
                    obj["route_index"] += 1
                    continue
                obj["heading_deg"] = math.degrees(math.atan2(dest[1]-obj["y_m"], dest[0]-obj["x_m"]))
                amount = min(distance, remaining)
                obj["x_m"] += (dest[0]-obj["x_m"])/distance*amount
                obj["y_m"] += (dest[1]-obj["y_m"])/distance*amount
                remaining -= amount
                if amount >= distance:
                    obj["route_index"] += 1
            if obj["kind"] == "aircraft" and obj["phase"] == "final" and 0 <= obj["x_m"] <= 3000:
                obj["phase"] = "landing_roll"
            if obj["route"] and obj["route_index"] == len(obj["route"]):
                obj["speed_mps"] = 0
                if obj["kind"] == "aircraft":
                    obj["phase"] = "departed" if not 0 <= obj["x_m"] <= 3000 else "holding"
                else:
                    obj["phase"] = "clear" if abs(obj["y_m"]) > 81 else "holding"
        for due, type, target in list(self.responses):
            if due <= self.now_ms:
                self.responses.remove((due, type, target))
                obj = self.mobiles[target]
                if type == "GO_AROUND":
                    obj["phase"] = "go_around"
                    obj["route"] = [(obj["x_m"]+4000, 800)]
                    obj["route_index"] = 0
                elif type == "CROSS_RUNWAY":
                    obj["speed_mps"] = obj["nominal_speed_mps"]
                    obj["phase"] = "crossing"
                elif type == "TAKEOFF":
                    obj["speed_mps"] = 45
                    obj["phase"] = "takeoff_roll"
                    obj["route"] = [(3600 if obj["runway"] == "27" else -800, 0)]
                    obj["route_index"] = 0
                elif type == "HOLD_SHORT":
                    obj["speed_mps"] = 0
                    obj["phase"] = "holding"
                elif type == "LINE_UP_AND_WAIT":
                    obj["speed_mps"] = 8
                    obj["phase"] = "taxi"
                    obj["route"] = [(obj["x_m"], 0)]
                    obj["route_index"] = 0
        due_actions = []
        while self.action_index < len(self.actions) and self.actions[self.action_index][0] <= self.now_ms:
            _, type, target, value = self.actions[self.action_index]
            due_actions.append((type, target, value))
            self.action_index += 1
        if self.now_ms % self.config.sample_ms == 0:
            self.sample()
        return due_actions

    def delivered(self) -> list[Track]:
        ready = [q for q in self.queue if q["received_ms"] <= self.now_ms]
        self.queue = [q for q in self.queue if q["received_ms"] > self.now_ms]
        return [Track.model_validate(q) for q in ready]

    def respond(self, instruction: str, target: str) -> None:
        # Remove obsolete pending responses, but cancellation alone never changes physical movement.
        self.responses = [r for r in self.responses if r[2] != target]
        delay = 8000 if instruction == "GO_AROUND" else 2000
        self.responses.append((self.now_ms+delay, instruction, target))

    def checkpoint(self) -> dict[str, Any]:
        return {"mobiles": copy.deepcopy(self.mobiles), "actions": self.actions,
                "action_index": self.action_index, "queue": copy.deepcopy(self.queue),
                "dropout_until": self.dropout_until.copy(), "responses": self.responses.copy(),
                "now_ms": self.now_ms, "rng_state": self.rng.getstate()}

    def restore(self, data: dict) -> None:
        def tuples(value):
            return tuple(tuples(v) for v in value) if isinstance(value, list) else value
        self.mobiles = copy.deepcopy(data["mobiles"])
        self.actions = [tuple(a) for a in data["actions"]]
        self.action_index = data["action_index"]
        self.queue = copy.deepcopy(data["queue"])
        self.dropout_until = data["dropout_until"].copy()
        self.responses = [tuple(r) for r in data["responses"]]
        self.now_ms = data["now_ms"]
        self.rng.setstate(tuples(data["rng_state"]))
