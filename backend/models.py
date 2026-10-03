"""Versioned public contracts. Simulator plans are deliberately separate from observed tracks."""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ENGINE_VERSION = "0.1.0"
CONFIG_VERSION = "lab-sop-1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Role(StrEnum):
    INSTRUCTOR = "instructor"
    TOWER = "tower"
    GROUND = "ground"
    OBSERVER = "observer"


class Instruction(StrEnum):
    HOLD_SHORT = "HOLD_SHORT"
    CROSS_RUNWAY = "CROSS_RUNWAY"
    LAND = "LAND"
    LINE_UP_AND_WAIT = "LINE_UP_AND_WAIT"
    TAKEOFF = "TAKEOFF"
    GO_AROUND = "GO_AROUND"


class Track(Contract):
    id: str
    callsign: str
    kind: Literal["aircraft", "vehicle"]
    x_m: float
    y_m: float
    speed_mps: float = Field(ge=0, le=200)
    heading_deg: float
    phase: str
    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)
    runway: Literal["09", "27"] = "27"
    route: list[tuple[float, float]] = Field(default_factory=list)
    owner: Literal["tower", "ground"]
    observed_ms: int = Field(ge=0)
    received_ms: int = Field(ge=0)
    source: str = "simulated-surface"
    event_id: str


class Clearance(Contract):
    id: str
    target: str
    instruction: Instruction
    runway: Literal["09", "27"]
    issued_ms: int
    issuer: str
    status: Literal["ISSUED", "CANCELLED", "COMPLETED", "SUPERSEDED"] = "ISSUED"
    readback: Literal["PENDING", "ACKNOWLEDGED", "MISMATCH_RECORDED"] = "PENDING"
    event_id: str


class SimulationConfig(Contract):
    tick_ms: Literal[100] = 100
    sample_ms: Literal[1000] = 1000
    delay_ms: int = Field(default=500, ge=0, le=10000)
    noise_m: float = Field(default=0, ge=0, le=30)
    horizon_s: Literal[120] = 120
    stale_ms: Literal[3000] = 3000
    buffer_s: float = Field(default=10, ge=0, le=30)
    position_error_m: float = Field(default=5, ge=0, le=30)
    speed_error_fraction: float = Field(default=0.1, ge=0, le=0.5)
    low_visibility: bool = False
    emergency: bool = False
    version: Literal["lab-sop-1"] = CONFIG_VERSION


class CreateSession(Contract):
    scenario_id: str = "overlap"
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    condition: Literal["flowlens", "baseline"] = "flowlens"
    config: SimulationConfig | None = None


class Command(Contract):
    command_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=0)
    type: Literal[
        "START", "PAUSE", "END", "SET_SPEED", "SEEK", "BRANCH", "CLEARANCE", "CANCEL",
        "REQUEST_CROSSING", "READBACK", "STOP_VEHICLE", "RESUME_VEHICLE", "DROPOUT",
        "CLOSE_RUNWAY", "OPEN_RUNWAY", "COORDINATION_COMPLETE",
    ]
    target: str | None = Field(default=None, max_length=100)
    instruction: Instruction | None = None
    runway: Literal["09", "27"] = "27"
    value: float | None = None
    readback: Literal["ACKNOWLEDGED", "MISMATCH_RECORDED"] | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        targeted = {"CLEARANCE", "CANCEL", "REQUEST_CROSSING", "READBACK", "STOP_VEHICLE",
                    "RESUME_VEHICLE", "DROPOUT", "COORDINATION_COMPLETE"}
        if self.type in targeted and not self.target:
            raise ValueError("This command requires a target")
        if self.type == "CLEARANCE" and self.instruction is None:
            raise ValueError("CLEARANCE requires an instruction")
        if self.type == "READBACK" and self.readback is None:
            raise ValueError("READBACK requires a status")
        if self.type in {"SET_SPEED", "SEEK", "BRANCH", "DROPOUT"} and self.value is None:
            raise ValueError("This command requires a value")
        if self.value is not None:
            import math
            if not math.isfinite(self.value):
                raise ValueError("value must be finite")
        if self.type == "SET_SPEED" and self.value not in {0.5, 1, 2, 4}:
            raise ValueError("Playback speed must be 0.5, 1, 2 or 4")
        if self.type == "DROPOUT" and not 1 <= float(self.value or 0) <= 120:
            raise ValueError("Dropout duration must be between 1 and 120 seconds")
        return self


class SeatRequest(Contract):
    role: Role
    label: str = Field(min_length=1, max_length=80)


class Acknowledgement(Contract):
    alert_id: str = Field(max_length=150)


class Assessment(Contract):
    type: Literal["bookmark", "recognition", "answer", "tlx", "trainer_review"]
    text: str = Field(default="", max_length=4000)
    values: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_values(self):
        import math
        if any(not math.isfinite(v) or not 0 <= v <= 100 for v in self.values.values()):
            raise ValueError("Assessment ratings must be finite and between 0 and 100")
        if self.type == "tlx" and set(self.values) != {
            "mental", "physical", "temporal", "performance", "effort", "frustration"
        }:
            raise ValueError("TLX requires all six dimensions; performance is difficulty, higher is worse")
        return self
