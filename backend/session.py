"""Single-writer session state, evidence lifecycle and durable frames."""
import copy
import sqlite3
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from .detection import detect, task_complexity
from .models import (
    CONFIG_VERSION,
    ENGINE_VERSION,
    Clearance,
    Command,
    Instruction,
    Role,
    SimulationConfig,
    Track,
)
from .ports import AlertLifecyclePort, DetectorPort, SessionWriter
from .scenarios import CATALOGUE, LAYOUT, scenario_config
from .simulator import Simulator
from .storage import Archive

RANK = {"ADVISORY": 1, "WARNING": 2, "CRITICAL": 3, "DATA_DEGRADED": 0}
CHECKPOINT_SCHEMA_VERSION = "synthetic-checkpoint-1"
STORAGE_FAILURE_MESSAGE = "Storage could not confirm this change. The committed session state was restored and paused."


class _LegacyAlertLifecycle:
    """Compatibility adapter for the lifecycle behavior previously in evaluate()."""

    def update(self, alerts: dict[str, dict], result: Mapping[str, Any], now_ms: int, emit_event) -> None:
        seen = set()
        for item in result["candidates"]:
            key = item["key"]
            seen.add(key)
            alert = alerts.get(key)
            if not alert or alert["status"] == "RESOLVED":
                alert = {**item, "id": uuid.uuid4().hex[:12], "status": "ACTIVE",
                         "created_ms": now_ms, "updated_ms": now_ms,
                         "safe_since_ms": None, "pending_severity": None}
                alerts[key] = alert
                emit_event("ALERT_OPEN", item["reason"], alert_id=alert["id"], rule=item["rule"],
                           severity=item["severity"], evidence_event_ids=item["evidence_event_ids"])
            else:
                old_severity = alert["severity"]
                if RANK[item["severity"]] < RANK[old_severity]:
                    if alert["pending_severity"] != item["severity"]:
                        alert["safe_since_ms"] = now_ms
                        alert["pending_severity"] = item["severity"]
                    if now_ms-int(alert["safe_since_ms"]) < 3000:
                        item = {**item, "severity": old_severity}
                    else:
                        alert["safe_since_ms"] = None
                        alert["pending_severity"] = None
                else:
                    alert["safe_since_ms"] = None
                    alert["pending_severity"] = None
                alert.update(item, updated_ms=now_ms)
                if old_severity != alert["severity"]:
                    emit_event("ALERT_LEVEL", f"Alert level {old_severity} → {alert['severity']}",
                               alert_id=alert["id"], severity=alert["severity"], rule=alert["rule"])

        degraded = set(result["runway"]["degraded_ids"])
        for key, alert in alerts.items():
            if key in seen or alert["status"] == "RESOLVED":
                continue
            if set(alert["objects"]) & degraded and alert["rule"] != "TRACKING_DEGRADED":
                alert["data_degraded"] = True
                alert["safe_since_ms"] = None
                alert["pending_severity"] = None
                continue
            if alert["safe_since_ms"] is None:
                alert["safe_since_ms"] = now_ms
            if now_ms-alert["safe_since_ms"] >= 3000:
                alert["status"] = "RESOLVED"
                alert["updated_ms"] = now_ms
                emit_event("ALERT_RESOLVED", "Condition absent for three simulation seconds.",
                           alert_id=alert["id"], rule=alert["rule"])


class SessionError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class Session:
    def __init__(self, archive: Archive, scenario_id: str, seed: int = 42,
                 config: SimulationConfig | None = None, condition: str = "flowlens",
                 parent: dict | None = None, *, detector: DetectorPort | None = None,
                 lifecycle: AlertLifecyclePort | None = None, writer: SessionWriter | None = None,
                 audit_clock: Callable[[], float] = time.time, initialize: bool = True,
                 defer_create: bool = False):
        self.id = uuid.uuid4().hex[:12]
        self.archive = archive
        self.writer = writer or archive
        self.detector = detector
        self.lifecycle = lifecycle or _LegacyAlertLifecycle()
        self.audit_clock = audit_clock
        self.scenario = CATALOGUE[scenario_id]
        self.config = config or scenario_config(self.scenario)
        self.seed = seed
        self.condition = condition
        self.simulator = Simulator(self.scenario.variant, seed, self.config)
        self.status = "READY"
        self.speed = 1.0
        self.revision = 0
        self.sequence = 0
        self.event_ordinal = 0
        self.events: list[dict] = []
        self.pending_events: list[dict] = []
        self.tracks: dict[str, Track] = {}
        self.previous_tracks: dict[str, Track] = {}
        self.clearances: list[Clearance] = []
        self.requests: list[dict] = []
        self.alerts: dict[str, dict] = {}
        self.acknowledgements: list[dict] = []
        self.assessments: list[dict] = []
        self.runway_open = True
        self.error: str | None = None
        self.detection_ms: list[float] = []
        self.result: dict = {}
        self.metadata = {"id": self.id, "scenario": self.scenario.public(), "seed": seed,
                         "config": self.config.model_dump(), "condition": condition,
                         "engine_version": ENGINE_VERSION, "config_version": CONFIG_VERSION,
                         "layout_id": LAYOUT["id"], "layout_version": LAYOUT["version"],
                         "kind": "training", "parent": parent, "created_utc": self.audit_clock()}
        if not defer_create:
            self.writer.create(self.id, self.metadata)
        self._storage_outcome_unknown = False
        self._unknown_command_id: str | None = None
        self._committed_state = self._capture_state()
        if not initialize:
            return
        self.event("SESSION_CREATED", "Session created; synthetic data and unreviewed lab SOP.")
        self.issue("BAW123", Instruction.LAND, "27", "scenario")
        if self.scenario.variant not in {"unauthorized", "reciprocal"}:
            self.issue("ARFF-2", Instruction.HOLD_SHORT if self.scenario.variant in {"hold", "violation"}
                       else Instruction.CROSS_RUNWAY, "27", "scenario")
        if self.scenario.variant == "reciprocal":
            self.issue("GA712", Instruction.TAKEOFF, "09", "scenario")
        if self.scenario.variant == "hold":
            self.request_crossing("ARFF-2", "scenario")
        self.evaluate()
        self.save()

    @property
    def now_ms(self) -> int:
        return self.simulator.now_ms

    def event(self, type: str, message: str, **fields) -> dict:
        self.event_ordinal += 1
        event = {"id": f"{self.id}:{self.event_ordinal}", "ordinal": self.event_ordinal,
                 "sim_ms": self.now_ms, "audit_utc": self.audit_clock(), "type": type, "message": message, **fields}
        self.events.append(event)
        self.pending_events.append(event)
        return event

    def active_clearance(self, target: str) -> Clearance | None:
        return next((c for c in reversed(self.clearances) if c.target == target and c.status == "ISSUED"), None)

    def issue(self, target: str, instruction: Instruction, runway: str, issuer: str) -> None:
        old = self.active_clearance(target)
        if old:
            old.status = "SUPERSEDED"
        channel = "ground" if instruction == Instruction.HOLD_SHORT and target in {"ARFF-2", "OPS-1"} else "tower"
        event = self.event("CLEARANCE", f"{target}: {instruction.value.replace('_', ' ')} RWY {runway}",
                           target=target, issuer=issuer, channel=channel, duration_ms=4000,
                           instruction=instruction.value, runway=runway, received_ms=self.now_ms)
        clearance = Clearance(id=uuid.uuid4().hex[:10], target=target, instruction=instruction,
                              runway=runway, issued_ms=self.now_ms, issuer=issuer, event_id=event["id"])
        self.clearances.append(clearance)
        self.complete_requests(target)

    def complete_requests(self, target: str):
        for request in self.requests:
            if request["target"] == target:
                request["completed"] = True

    def request_crossing(self, target: str, issuer: str) -> None:
        event = self.event("COORDINATION", f"{target}: runway crossing requested; awaiting tower decision.",
                           target=target, issuer=issuer, channel="ground", duration_ms=4000)
        self.requests.append({"id": event["id"], "target": target, "requested_ms": self.now_ms,
                              "completed": False})

    def evaluate(self) -> None:
        begin = time.perf_counter()
        if self.detector is None:
            self.result = detect(self.tracks, self.clearances, self.now_ms, self.config, self.runway_open,
                                 list(self.simulator.mobiles), self.previous_tracks)
        else:
            self.result = dict(self.detector.evaluate(
                self.tracks, self.clearances, self.now_ms, self.config, self.runway_open,
                list(self.simulator.mobiles), self.previous_tracks,
            ))
        self.detection_ms.append((time.perf_counter()-begin)*1000)
        if len(self.detection_ms) > 9000:
            self.detection_ms = self.detection_ms[-9000:]
        self.lifecycle.update(self.alerts, self.result, self.now_ms, self.event)

    def advance(self, ticks: int = 1, persist: bool = True) -> None:
        for _ in range(ticks):
            if self.status != "RUNNING":
                break
            actions = self.simulator.step()
            for type, target, value in actions:
                if type == "DROPOUT":
                    self.simulator.dropout_until[target] = self.now_ms+int(value*1000)
                    self.event("SCENARIO_ACTION", "Observation-channel interruption.", target=target)
                elif type == "CANCEL":
                    old = self.active_clearance(target)
                    if old:
                        old.status = "CANCELLED"
                    self.event("CANCEL", "Scenario cancels crossing; vehicle movement continues.", target=target)
                elif type == "GO_AROUND":
                    self.issue(target, Instruction.GO_AROUND, "27", "scenario")
                    self.simulator.respond(type, target)
            for track in self.simulator.delivered():
                old = self.tracks.get(track.id)
                if old:
                    self.previous_tracks[track.id] = old
                event = self.event("TRACK", "Observed track received.", target=track.id,
                                   observed_ms=track.observed_ms, received_ms=self.now_ms)
                track.event_id = event["id"]
                self.tracks[track.id] = track
                event["track"] = track.model_dump()
                if track.phase in {"clear", "departed"}:
                    clearance = self.active_clearance(track.id)
                    if clearance:
                        clearance.status = "COMPLETED"
            if self.now_ms % 200 == 0 or actions:
                self.evaluate()
                if persist:
                    self.save()
            if self.now_ms >= self.scenario.duration_s*1000:
                self.status = "ENDED"
                self.event("SESSION_ENDED", "Scenario duration completed.")
                if persist:
                    self.save()
                break

    def authorize(self, command: Command, role: Role) -> None:
        instructor_only = {"START", "PAUSE", "END", "SET_SPEED", "SEEK", "BRANCH", "STOP_VEHICLE",
                           "RESUME_VEHICLE", "DROPOUT", "CLOSE_RUNWAY", "OPEN_RUNWAY", "READBACK"}
        if command.type in instructor_only and role != Role.INSTRUCTOR:
            raise SessionError(403, "This control belongs to the instructor")
        if command.type not in instructor_only and role == Role.OBSERVER:
            raise SessionError(403, "Observer cannot issue instructions")
        if command.type == "CLEARANCE" and role == Role.GROUND:
            if command.instruction != Instruction.HOLD_SHORT:
                raise SessionError(403, "Ground coordinates crossing; tower issues runway permissions")
            if command.target not in {"ARFF-2", "OPS-1", "GA712", "QZ804"}:
                raise SessionError(403, "Ground may only hold surface mobiles")

    def execute(self, command: Command, role: Role, actor: str, *, actor_id: str | None = None) -> dict:
        self.authorize(command, role)
        request = {"command": command.model_dump(mode="json"), "actor": actor_id or actor,
                   "role": role.value}
        try:
            # Ordinary receipt reads go through the injected writer port; archive reads below
            # are reserved for reconciling an ambiguous storage outcome.
            prior = self.writer.command(self.id, command.command_id)
        except Exception as error:
            raise SessionError(503, STORAGE_FAILURE_MESSAGE) from error
        if prior:
            if prior[0] != request:
                raise SessionError(409, "Command ID was already used for a different request or actor")
            if self._storage_outcome_unknown:
                self._reconcile_storage(prior)
            return prior[1]
        if self._storage_outcome_unknown:
            self._reconcile_pending_storage()
            try:
                prior = self.archive.command(self.id, command.command_id)
            except Exception as error:
                raise SessionError(503, STORAGE_FAILURE_MESSAGE) from error
            if prior:
                if prior[0] != request:
                    raise SessionError(409, "Command ID was already used for a different request or actor")
                return prior[1]
        if self.status in {"ENDED", "INTERRUPTED"}:
            raise SessionError(409, "This session is frozen; create a review or branch")
        if command.expected_revision != self.revision:
            raise SessionError(409, "State revision changed; refresh and submit a new command ID")
        if command.target and command.target not in self.simulator.mobiles:
            raise SessionError(422, "Unknown mobile target")
        type, target = command.type, command.target
        if type in {"SEEK", "BRANCH"}:
            raise SessionError(422, "Seek belongs to review; branching uses the branch endpoint")
        if type == "CLEARANCE":
            obj = self.simulator.mobiles[str(target)]
            if command.instruction == Instruction.CROSS_RUNWAY and obj["kind"] != "vehicle":
                raise SessionError(422, "This lab crossing instruction targets vehicles")
            if command.instruction in {Instruction.LAND, Instruction.TAKEOFF, Instruction.GO_AROUND,
                                       Instruction.LINE_UP_AND_WAIT} and obj["kind"] != "aircraft":
                raise SessionError(422, "Aircraft instruction cannot target a vehicle")
        if type in {"STOP_VEHICLE", "RESUME_VEHICLE"} and self.simulator.mobiles[str(target)]["kind"] != "vehicle":
            raise SessionError(422, "Vehicle control requires a vehicle")
        if type in {"CANCEL", "READBACK"} and not self.active_clearance(str(target)):
            raise SessionError(409, "Target has no active clearance")
        # All validation precedes state mutation.
        self.error = None
        if type == "START":
            self.status = "RUNNING"
        elif type == "PAUSE":
            self.status = "PAUSED"
        elif type == "END":
            self.status = "ENDED"
        elif type == "SET_SPEED":
            self.speed = float(command.value or 1)
        elif type == "CLEARANCE":
            self.issue(str(target), Instruction(command.instruction), command.runway, actor)
            self.simulator.mobiles[str(target)]["runway"] = command.runway
            self.simulator.respond(str(command.instruction), str(target))
        elif type == "CANCEL":
            self.active_clearance(str(target)).status = "CANCELLED"  # type: ignore[union-attr]
            self.event("CANCEL", "Clearance cancelled; physical occupancy remains independent.", target=target)
        elif type == "READBACK":
            self.active_clearance(str(target)).readback = command.readback  # type: ignore[union-attr,assignment]
            self.event("READBACK", f"Structured readback: {command.readback}", target=target,
                       channel="tower", duration_ms=4000)
        elif type == "REQUEST_CROSSING":
            if self.simulator.mobiles[str(target)]["kind"] != "vehicle":
                raise SessionError(422, "Crossing requests target vehicles in this SOP")
            self.request_crossing(str(target), actor)
        elif type == "COORDINATION_COMPLETE":
            self.complete_requests(str(target))
        elif type in {"STOP_VEHICLE", "RESUME_VEHICLE"}:
            obj = self.simulator.mobiles[str(target)]
            obj["speed_mps"] = 0 if type == "STOP_VEHICLE" else obj["nominal_speed_mps"]
            obj["phase"] = "holding" if type == "STOP_VEHICLE" else "crossing"
            self.simulator.responses = [r for r in self.simulator.responses if r[2] != target]
        elif type == "DROPOUT":
            self.simulator.dropout_until[str(target)] = self.now_ms+int(float(command.value or 0)*1000)
        elif type in {"CLOSE_RUNWAY", "OPEN_RUNWAY"}:
            self.runway_open = type == "OPEN_RUNWAY"
        self.revision += 1
        self.event("COMMAND", f"{actor}: {type}", target=target, actor=actor, role=role.value,
                   command=command.model_dump(mode="json"))
        self.evaluate()
        response = {"session_id": self.id, "revision": self.revision, "status": self.status,
                    "command_id": command.command_id}
        self.save((command.command_id, request, response))
        return response

    def acknowledge(self, alert_id: str, actor: str):
        if self._storage_outcome_unknown:
            self._reconcile_pending_storage()
        if not any(a["id"] == alert_id for a in self.alerts.values()):
            raise SessionError(404, "Alert not found")
        item = {"alert_id": alert_id, "actor": actor, "sim_ms": self.now_ms}
        self.acknowledgements.append(item)
        self.event("ACKNOWLEDGEMENT", "Alert acknowledged; condition is not resolved.", **item)
        self.save()
        return item

    def assess(self, payload: dict, actor: str, role: Role):
        if self._storage_outcome_unknown:
            self._reconcile_pending_storage()
        if payload["type"] == "trainer_review" and role != Role.INSTRUCTOR:
            raise SessionError(403, "Only instructors record a trainer review")
        event = self.event("ASSESSMENT", payload["text"], actor=actor, role=role.value, assessment=payload)
        self.assessments.append(event)
        self.save()
        return event

    def snapshot(self) -> dict[str, Any]:
        visible = [e for e in self.events if e["type"] != "TRACK"][-60:]
        communications = [e for e in self.events if e.get("duration_ms") and e["sim_ms"] > self.now_ms-64000]
        return {"session_id": self.id, "kind": "training", "sequence": self.sequence,
                "sim_ms": self.now_ms, "revision": self.revision, "status": self.status,
                "speed": self.speed, "metadata": self.metadata, "layout": LAYOUT,
                "tracks": [t.model_dump() | {"stale": self.now_ms-t.observed_ms > self.config.stale_ms}
                           for t in self.tracks.values()],
                "clearances": [c.model_dump(mode="json") for c in self.clearances],
                "requests": self.requests, "predictions": self.result.get("predictions", []),
                "runway": self.result.get("runway", {}), "alerts": list(self.alerts.values()),
                "events": visible, "acknowledgements": self.acknowledgements,
                "assessments": self.assessments,
                "complexity": {role: task_complexity(self.tracks, self.clearances, self.requests,
                                                      communications, self.now_ms, self.config, role)
                               for role in ["tower", "ground"]}, "error": self.error}

    def checkpoint(self) -> dict:
        return {"schema_version": CHECKPOINT_SCHEMA_VERSION,
                "engine_version": ENGINE_VERSION, "config_version": CONFIG_VERSION,
                "scenario_id": self.scenario.id, "layout_id": LAYOUT["id"],
                "layout_version": LAYOUT["version"],
                "simulator": self.simulator.checkpoint(), "tracks": {id: t.model_dump() for id, t in self.tracks.items()},
                "previous_tracks": {id: t.model_dump() for id, t in self.previous_tracks.items()},
                "event_ordinal": self.event_ordinal, "runway_open": self.runway_open,
                "detection_ms": self.detection_ms[-200:], "snapshot_marker": self.now_ms % 5000 == 0}

    def save(self, command=None):
        self.sequence += 1
        try:
            self.writer.save(self.id, self.status, self.pending_events, self.snapshot(), self.checkpoint(), command)
        except Exception as error:
            committed, outcome_known = self._attempt_is_committed(command)
            if committed:
                self.pending_events.clear()
                self._storage_outcome_unknown = False
                self._unknown_command_id = None
                self._committed_state = self._capture_state()
                return
            self._restore_state(self._committed_state)
            self.status = "PAUSED"
            self.error = STORAGE_FAILURE_MESSAGE
            self._storage_outcome_unknown = not outcome_known
            self._unknown_command_id = command[0] if command is not None and not outcome_known else None
            raise SessionError(503, STORAGE_FAILURE_MESSAGE) from error
        self.pending_events.clear()
        self._committed_state = self._capture_state()
        self._storage_outcome_unknown = False
        self._unknown_command_id = None

    def _capture_state(self) -> dict[str, Any]:
        names = (
            "status", "speed", "revision", "sequence", "event_ordinal", "events", "pending_events",
            "tracks", "previous_tracks", "clearances", "requests", "alerts", "acknowledgements",
            "assessments", "runway_open", "error", "detection_ms", "result", "metadata",
        )
        state = {name: getattr(self, name) for name in names}
        state["simulator"] = self.simulator.checkpoint()
        return copy.deepcopy(state)

    def _restore_state(self, state: dict[str, Any]) -> None:
        restored = copy.deepcopy(state)
        simulator_state = restored.pop("simulator")
        for name, value in restored.items():
            setattr(self, name, value)
        self.simulator.restore(simulator_state)

    def _attempt_is_committed(self, command) -> tuple[bool, bool]:
        """Return whether the attempted frame and its receipt are durably visible."""
        try:
            stored = self.archive.frame(self.id)
            if not stored:
                return False, True
            public, private = stored
            frame_matches = (
                public.get("sequence") == self.sequence
                and public.get("revision") == self.revision
                and public.get("sim_ms") == self.now_ms
                and private.get("event_ordinal") == self.event_ordinal
            )
            if command is None:
                return frame_matches, True
            key, request, response = command
            receipt = self.archive.command(self.id, key)
            if receipt == (request, response):
                return frame_matches, True
            if frame_matches or receipt is not None:
                return False, False
            return False, True
        except (sqlite3.Error, ValueError, TypeError, KeyError, IndexError, AttributeError):
            return False, False

    def _reconcile_storage(self, receipt: tuple[dict, dict] | None) -> None:
        """Resolve a prior ambiguous writer outcome before accepting another mutation."""
        try:
            stored = self.archive.frame(self.id)
            if not stored:
                raise RuntimeError("no committed session frame is available")
            public, private = stored
            events = self.archive.all_events(self.id)
            if receipt is not None:
                command_id = receipt[0].get("command", {}).get("command_id")
                if (not command_id or public.get("revision", -1) < receipt[1].get("revision", 0)
                        or not any(event.get("command", {}).get("command_id") == command_id
                                   for event in events)):
                    raise RuntimeError("durable command receipt has no matching committed session state")
            self._restore_frame(public, private, events)
        except Exception as error:
            self.status = "PAUSED"
            self.error = STORAGE_FAILURE_MESSAGE
            raise SessionError(503, STORAGE_FAILURE_MESSAGE) from error
        self._storage_outcome_unknown = False
        self._unknown_command_id = None
        if receipt is None:
            # A readable archive with no receipt proves the attempted command was
            # not committed. Require a fresh explicit command from the restored state.
            self.status = "PAUSED"
            self.error = STORAGE_FAILURE_MESSAGE
            self._committed_state = self._capture_state()

    def _reconcile_pending_storage(self) -> None:
        receipt = None
        if self._unknown_command_id is not None:
            try:
                receipt = self.archive.command(self.id, self._unknown_command_id)
            except Exception as error:
                raise SessionError(503, STORAGE_FAILURE_MESSAGE) from error
        self._reconcile_storage(receipt)

    def _restore_frame(self, public: dict, private: dict, events: list[dict]) -> None:
        self.simulator.restore(private["simulator"])
        self.tracks = {key: Track.model_validate(value) for key, value in private["tracks"].items()}
        self.previous_tracks = {
            key: Track.model_validate(value) for key, value in private["previous_tracks"].items()
        }
        self.clearances = [Clearance.model_validate(value) for value in public["clearances"]]
        self.requests = copy.deepcopy(public["requests"])
        self.alerts = {alert["key"]: copy.deepcopy(alert) for alert in public["alerts"]}
        self.acknowledgements = copy.deepcopy(public["acknowledgements"])
        self.assessments = copy.deepcopy(public["assessments"])
        self.events = copy.deepcopy(events)
        self.pending_events = []
        self.event_ordinal = int(private["event_ordinal"])
        self.runway_open = bool(private["runway_open"])
        self.detection_ms = copy.deepcopy(private.get("detection_ms", []))
        self.revision = int(public["revision"])
        self.sequence = int(public["sequence"])
        self.status = str(public["status"])
        self.speed = float(public["speed"])
        self.error = public.get("error")
        self.metadata = copy.deepcopy(public["metadata"])
        self.result = {"predictions": copy.deepcopy(public.get("predictions", [])),
                       "runway": copy.deepcopy(public.get("runway", {}))}
        self._committed_state = self._capture_state()

    @staticmethod
    def checkpoint_compatibility_error(public: dict, private: dict) -> str | None:
        """Validate a saved private checkpoint against this synthetic runtime."""
        if not isinstance(private, dict):
            return "Checkpoint private metadata is unavailable; this frame cannot be branched safely."
        metadata = public.get("metadata")
        if not isinstance(metadata, dict):
            return "Checkpoint metadata is missing; this frame cannot be branched safely."
        scenario_meta = metadata.get("scenario")
        if not isinstance(scenario_meta, dict):
            return "Checkpoint scenario metadata is missing; this frame cannot be branched safely."
        scenario_id = scenario_meta.get("id")
        if (not isinstance(scenario_id, str) or scenario_id not in CATALOGUE
                or scenario_meta.get("version") != CATALOGUE[scenario_id].public().get("version")):
            return "Checkpoint scenario version is unavailable; this frame cannot be branched safely."
        if (metadata.get("engine_version") != ENGINE_VERSION
                or metadata.get("config_version") != CONFIG_VERSION
                or metadata.get("layout_id") != LAYOUT["id"]
                or metadata.get("layout_version") != LAYOUT["version"]):
            return "Checkpoint engine, configuration, or layout version is incompatible."
        try:
            config = SimulationConfig.model_validate(metadata.get("config"))
        except (ValueError, TypeError):
            return "Checkpoint configuration metadata is invalid."
        if config.version != CONFIG_VERSION:
            return "Checkpoint configuration version is incompatible."
        seed = metadata.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            return "Checkpoint seed metadata is invalid."
        expected = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "config_version": CONFIG_VERSION,
            "scenario_id": scenario_id,
            "layout_id": LAYOUT["id"],
            "layout_version": LAYOUT["version"],
        }
        if any(private.get(key) != value for key, value in expected.items()):
            return "Checkpoint schema or runtime metadata is missing or incompatible."
        simulator = private.get("simulator")
        required_simulator = {
            "mobiles", "actions", "action_index", "queue", "dropout_until", "responses", "now_ms", "rng_state",
        }
        if (not isinstance(simulator, dict) or not required_simulator.issubset(simulator)
                or not {"tracks", "previous_tracks", "event_ordinal", "runway_open"}.issubset(private)):
            return "Checkpoint private simulator state is incomplete."
        event_ordinal = private.get("event_ordinal")
        sim_ms = public.get("sim_ms")
        if (isinstance(event_ordinal, bool) or not isinstance(event_ordinal, int) or event_ordinal < 0
                or isinstance(sim_ms, bool) or not isinstance(sim_ms, int)
                or simulator.get("now_ms") != sim_ms or not isinstance(private.get("runway_open"), bool)):
            return "Checkpoint time or event ancestry is inconsistent."
        if (not isinstance(simulator.get("mobiles"), dict)
                or not isinstance(simulator.get("actions"), list)
                or isinstance(simulator.get("action_index"), bool)
                or not isinstance(simulator.get("action_index"), int)
                or not 0 <= simulator["action_index"] <= len(simulator["actions"])
                or not isinstance(simulator.get("queue"), list)
                or not isinstance(simulator.get("dropout_until"), dict)
                or not isinstance(simulator.get("responses"), list)
                or not isinstance(private.get("tracks"), dict)
                or not isinstance(private.get("previous_tracks"), dict)):
            return "Checkpoint private simulator state is malformed."
        for field in ("clearances", "requests", "alerts", "acknowledgements", "assessments"):
            if not isinstance(public.get(field), list):
                return "Checkpoint public state is incomplete."
        try:
            probe = Simulator(CATALOGUE[scenario_id].variant, seed, config)
            probe.restore(simulator)
            for track in (*private["tracks"].values(), *private["previous_tracks"].values(),
                          *simulator["queue"]):
                Track.model_validate(track)
            for clearance in public["clearances"]:
                Clearance.model_validate(clearance)
            if any(not isinstance(alert, dict) or not isinstance(alert.get("key"), str)
                   for alert in public["alerts"]):
                return "Checkpoint alert state is malformed."
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError):
            return "Checkpoint private simulator state is incompatible."
        return None

    def restore(self, public: dict, private: dict, parent_events: list[dict]):
        self.simulator.restore(private["simulator"])
        self.tracks = {id: Track.model_validate(t) for id, t in private["tracks"].items()}
        self.previous_tracks = {id: Track.model_validate(t) for id, t in private["previous_tracks"].items()}
        self.clearances = [Clearance.model_validate(c) for c in public["clearances"]]
        self.requests = copy.deepcopy(public["requests"])
        self.alerts = {a["key"]: copy.deepcopy(a) for a in public["alerts"]}
        self.acknowledgements = copy.deepcopy(public["acknowledgements"])
        self.assessments = copy.deepcopy(public["assessments"])
        self.events = copy.deepcopy(parent_events)
        self.pending_events = self.events.copy()
        self.event_ordinal = int(private["event_ordinal"])
        self.runway_open = private["runway_open"]
        self.revision = 0
        self.status = "PAUSED"
        self.event("BRANCH_CREATED", "Alternative training session from an archived frame.",
                   parent=self.metadata["parent"])
        self.evaluate()
        self.save()
