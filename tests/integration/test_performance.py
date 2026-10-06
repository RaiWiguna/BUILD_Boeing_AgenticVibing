from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import median
from typing import Any

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.detection import detect  # noqa: E402
from backend.models import SimulationConfig  # noqa: E402
from backend.scenarios import CATALOGUE, scenario_config  # noqa: E402
from backend.simulator import Simulator  # noqa: E402
from backend.storage import Archive  # noqa: E402


MANIFEST_PATH = REPOSITORY_ROOT / "tests/fixtures/replay/benchmark-manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "unavailable"


def _environment() -> dict[str, Any]:
    try:
        import psutil
        ram_bytes: int | None = int(psutil.virtual_memory().total)
    except ImportError:
        ram_bytes = None
    cpu = platform.processor() or platform.uname().processor or "unknown"
    return {
        "cpu_model": cpu,
        "cpu_logical_count": __import__("os").cpu_count(),
        "ram_bytes": ram_bytes,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": sys.version.split()[0],
        "sqlite": __import__("sqlite3").sqlite_version,
        "dependencies": {
            "fastapi": _version("fastapi"),
            "uvicorn": _version("uvicorn"),
            "pydantic": _version("pydantic"),
            "shapely": _version("shapely"),
            "pytest": _version("pytest"),
            "psutil": _version("psutil"),
        },
        "browser": "not measured",
        "network_topology": "in-process localhost/temporary SQLite; no LAN or second machine",
    }


def _scenario_input(run: dict[str, Any]) -> tuple[list[Any], SimulationConfig, dict[str, Any]]:
    scenario = CATALOGUE[run["source_scenario_id"]]
    parameters = MANIFEST["parameters"]["per_stratum"][run["stratum"]]
    config = scenario_config(scenario).model_copy(update={
        "tick_ms": parameters["tick_ms"],
        "sample_ms": parameters["sample_ms"],
        "delay_ms": parameters["delay_ms"],
        "noise_m": parameters["noise_m"],
    })
    simulator = Simulator(scenario.variant, run["seed"], config)
    tracks: dict[str, Any] = {}
    for _ in range(MANIFEST["methodology"]["synthetic_duration_per_run_ms"] // config.tick_ms):
        simulator.step()
        for track in simulator.delivered():
            tracks[track.id] = track
    for target in parameters["dropout_targets"]:
        tracks.pop(target, None)
    return list(tracks.values()), config, {
        "sim_ms": simulator.now_ms,
        "scenario_id": run["source_scenario_id"],
        "seed": run["seed"],
        "delay_ms": config.delay_ms,
        "noise_m": config.noise_m,
        "dropout_targets": parameters["dropout_targets"],
    }


def _benchmark(tmp_path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    warmup_tracks, warmup_config, warmup_context = _scenario_input(MANIFEST["runs"][0])
    expected_ids = MANIFEST["parameters"]["expected_object_ids"]
    warmup_started = time.perf_counter_ns()
    for _ in range(MANIFEST["methodology"]["warmup_detector_evaluations"]):
        detect(
            tracks={track.id: track for track in warmup_tracks},
            clearances=[],
            now_ms=MANIFEST["methodology"]["synthetic_duration_per_run_ms"],
            config=warmup_config,
            runway_open=True,
            expected_ids=expected_ids,
        )
    warmup_ms = (time.perf_counter_ns() - warmup_started) / 1_000_000

    database_path = tmp_path / "qa06-benchmark.sqlite3"
    archive = Archive(database_path)
    suite_started = time.perf_counter_ns()
    try:
        for run in MANIFEST["runs"]:
            row: dict[str, Any] = {
                **run,
                "label": "FIXTURE/MOCK synthetic source input; current detector/storage source",
                "status": "failed",
                "detector_compute_ms": None,
                "sqlite_create_and_save_ms": None,
                "track_count": None,
                "candidate_count": None,
            }
            try:
                tracks, config, context = _scenario_input(run)
                detector_started = time.perf_counter_ns()
                detection = detect(
                    tracks={track.id: track for track in tracks},
                    clearances=[],
                    now_ms=context["sim_ms"],
                    config=config,
                    runway_open=True,
                    expected_ids=expected_ids,
                )
                detector_ms = (time.perf_counter_ns() - detector_started) / 1_000_000

                session_id = f"QA06-{run['run_id']}"
                public = {
                    "sim_ms": context["sim_ms"],
                    "sequence": 1,
                    "source_profile": "synthetic-fixture-mock",
                    "scenario_id": run["source_scenario_id"],
                    "tracks": [track.model_dump(mode="json") for track in tracks],
                    "detection": detection,
                }
                event = {
                    "id": f"{session_id}:1",
                    "ordinal": 1,
                    "sim_ms": context["sim_ms"],
                    "type": "BENCHMARK_FIXTURE_OBSERVATION",
                    "message": "Authored synthetic benchmark observation; not partner or server data.",
                }
                persist_started = time.perf_counter_ns()
                archive.create(session_id, {
                    "source_profile": "synthetic-fixture-mock",
                    "scenario_id": run["source_scenario_id"],
                    "seed": run["seed"],
                })
                archive.save(session_id, "READY", [event], public, {})
                persistence_ms = (time.perf_counter_ns() - persist_started) / 1_000_000

                row.update({
                    "status": "measured",
                    "detector_compute_ms": detector_ms,
                    "sqlite_create_and_save_ms": persistence_ms,
                    "track_count": len(tracks),
                    "candidate_count": len(detection["candidates"]),
                    "simulated_duration_ms": context["sim_ms"],
                })
            except Exception as error:  # retain failed manifest rows in the denominator
                row["error"] = f"{type(error).__name__}: {str(error)[:240]}"
            rows.append(row)
    finally:
        archive.close()
    with __import__("sqlite3").connect(database_path) as connection:
        persisted_counts = {
            "sessions": connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            "events": connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "frames": connection.execute("SELECT COUNT(*) FROM frames").fetchone()[0],
        }
    suite_wall_s = (time.perf_counter_ns() - suite_started) / 1_000_000_000

    compute = [row["detector_compute_ms"] for row in rows if row["detector_compute_ms"] is not None]
    persistence = [row["sqlite_create_and_save_ms"] for row in rows
                   if row["sqlite_create_and_save_ms"] is not None]
    counts = {stratum: sum(row["stratum"] == stratum for row in rows)
              for stratum in MANIFEST["methodology"]["strata"]}
    p95_compute = _p95(compute) if compute else None
    output = {
        "schema_version": "qa06-performance-result-1",
        "task": "QA-06",
        "label": "actual local technical measurements from the current synthetic simulator, detector, and SQLite archive; no domain validation",
        "manifest": "tests/fixtures/replay/benchmark-manifest.json",
        "manifest_sha256": _sha256(MANIFEST_PATH),
        "run_started_local": datetime.now().astimezone().isoformat(),
        "source_hashes": MANIFEST["source_dependencies"]["current_source_hashes"],
        "environment": _environment(),
        "methodology": {
            "planned_runs": MANIFEST["methodology"]["run_count"],
            "recorded_runs": len(rows),
            "measured_runs": sum(row["status"] == "measured" for row in rows),
            "failed_runs_retained": sum(row["status"] == "failed" for row in rows),
            "strata_counts": counts,
            "warmup_detector_evaluations_excluded_from_denominator": MANIFEST["methodology"]["warmup_detector_evaluations"],
            "warmup_wall_ms": warmup_ms,
            "simulated_duration_per_run_ms": MANIFEST["methodology"]["synthetic_duration_per_run_ms"],
            "simulated_time_total_s": sum(row.get("simulated_duration_ms", 0) for row in rows) / 1000,
            "suite_wall_duration_s": suite_wall_s,
            "interventions": "none",
            "parameter_source": "frozen benchmark manifest; no tuning against these runs",
        },
        "metrics": {
            "detector_compute_ms": {
                "status": "measured" if compute else "unavailable",
                "sample_count": len(compute),
                "p50": median(compute) if compute else None,
                "p95": p95_compute,
                "max": max(compute) if compute else None,
                "target_p95_ms": 50,
                "target_comparison": (
                    "measured_below_target" if p95_compute is not None and p95_compute < 50
                    else "measured_at_or_above_target" if p95_compute is not None else "unavailable"
                ),
                "scope": "one current-source detector evaluation per synthetic 5-aircraft/2-vehicle sample; not a replay or domain-accuracy result",
            },
            "sqlite_create_and_save_ms": {
                "status": "measured" if persistence else "unavailable",
                "sample_count": len(persistence),
                "p50": median(persistence) if persistence else None,
                "p95": _p95(persistence) if persistence else None,
                "max": max(persistence) if persistence else None,
                "scope": "current Archive.create plus Archive.save of one synthetic public frame/event per run; not backup/recovery",
                "persisted_row_counts": persisted_counts,
            },
            "api_delivery_render": {"status": "unavailable", "reason": "No additive source replay API/QA-04 launcher; browser render timing is not measured by this suite."},
            "reconnect": {"status": "not_run", "reason": "Source replay stream integration is unavailable."},
            "synchronization_lan": {"status": "not_run", "reason": "Only one localhost process; no LAN or second machine."},
            "endurance_30m": {"status": "not_run", "reason": "No integrated source replay runtime; no 30-minute session was run."},
            "provider_ai_asr": {"status": "unavailable", "reason": "No provisioned provider/model assets; no provider metrics reported."},
            "recall_false_warning_lead_time": {"status": "unavailable", "reason": "No QA-01 independent private labels/oracles; no accuracy metrics calculated."},
        },
        "domain_review_status": "not_reviewed",
        "operational_validation_status": "not_validated",
        "runs": rows,
    }
    report_dir = REPOSITORY_ROOT / "tmp"
    report_dir.mkdir(exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f%z")
    report_path = report_dir / f"qa06-performance-{stamp}.json"
    with report_path.open("x", encoding="utf-8") as result_file:
        json.dump(output, result_file, indent=2, ensure_ascii=False)
        result_file.write("\n")
    output["result_artifact"] = report_path.relative_to(REPOSITORY_ROOT).as_posix()
    return output


def test_benchmark_manifest_freezes_all_strata_and_seed_parameters() -> None:
    assert MANIFEST["schema_version"] == "qa06-benchmark-1"
    assert len(MANIFEST["scenarios"]) == 12
    assert len(MANIFEST["runs"]) == 100
    assert len({row["run_id"] for row in MANIFEST["runs"]}) == 100
    assert len({row["seed"] for row in MANIFEST["runs"]}) == 100
    assert {row["stratum"]: sum(run["stratum"] == row["stratum"] for run in MANIFEST["runs"])
            for row in MANIFEST["runs"]} == {
                "conflict": 40, "safe": 40, "delay_noise": 10, "dropout": 10,
            }
    assert {row["source_scenario_id"] for row in MANIFEST["scenarios"]} == set(CATALOGUE)
    for relative, expected_hash in MANIFEST["source_dependencies"]["current_source_hashes"].items():
        assert _sha256(REPOSITORY_ROOT / relative) == expected_hash
    assert MANIFEST["source_dependencies"]["qa01_canonical_bundle"].startswith("unavailable")
    assert MANIFEST["source_dependencies"]["qa04_launcher"] == "unavailable"


def test_current_source_benchmark_measures_all_100_runs_and_persists_evidence(tmp_path: Path) -> None:
    report = _benchmark(tmp_path)

    assert report["methodology"]["planned_runs"] == 100
    assert report["methodology"]["recorded_runs"] == 100
    assert report["methodology"]["strata_counts"] == {
        "conflict": 40, "safe": 40, "delay_noise": 10, "dropout": 10,
    }
    assert report["methodology"]["measured_runs"] + report["methodology"]["failed_runs_retained"] == 100
    assert report["metrics"]["detector_compute_ms"]["sample_count"] == 100
    assert report["metrics"]["sqlite_create_and_save_ms"]["sample_count"] == 100
    assert report["metrics"]["api_delivery_render"]["status"] == "unavailable"
    assert report["metrics"]["provider_ai_asr"]["status"] == "unavailable"
    assert report["domain_review_status"] == "not_reviewed"
    assert report["operational_validation_status"] == "not_validated"

    saved = REPOSITORY_ROOT / report["result_artifact"]
    assert saved.is_file()
    saved_report = json.loads(saved.read_text(encoding="utf-8"))
    assert len(saved_report["runs"]) == 100
    assert all(row["status"] == "measured" for row in saved_report["runs"])
