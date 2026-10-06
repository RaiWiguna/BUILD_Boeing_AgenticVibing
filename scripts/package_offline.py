"""Assemble a local, synthetic-only FlowLens package without network access.

The packager never invokes pip, npm, or a model provider. Runtime dependencies
must be pinned and hashed in requirements.lock and already present as wheels in
wheelhouse/. A package is not produced when any required input is missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import sys
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LOCK_NAME = "requirements.lock"
WHEELHOUSE_NAME = "wheelhouse"

REQUIRED_FILES = (
    "pyproject.toml",
    "requirements.lock",
    "backend/__init__.py",
    "backend/app.py",
    "backend/detection.py",
    "backend/models.py",
    "backend/reporting.py",
    "backend/review.py",
    "backend/scenarios.py",
    "backend/session.py",
    "backend/simulator.py",
    "backend/storage.py",
    "backend/data/scenarios.json",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/dist/index.html",
    "tests/fixtures/replay/benchmark-manifest.json",
)

COPY_FILES = (
    "pyproject.toml",
    LOCK_NAME,
    "backend/__init__.py",
    "backend/app.py",
    "backend/detection.py",
    "backend/models.py",
    "backend/reporting.py",
    "backend/review.py",
    "backend/scenarios.py",
    "backend/session.py",
    "backend/simulator.py",
    "backend/storage.py",
    "backend/data/scenarios.json",
    "frontend/package.json",
    "frontend/package-lock.json",
    "tests/fixtures/replay/benchmark-manifest.json",
)

SENSITIVE_PARTS = {
    ".env", "private", "private-audio", "truth", "restricted", "credential",
    "credentials", "secret", "secrets", "token", "tokens", "operator-key",
    "audio", "recordings", "exports",
}
SENSITIVE_CONTENT = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~-]{24,}"),
    re.compile(r"\bqa05-local-throwaway-key\b"),
)
FORBIDDEN_SUFFIXES = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".sqlite", ".sqlite3", ".db", ".csv"}


class PackagePreflightError(RuntimeError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class LockedRequirement:
    name: str
    normalized_name: str
    version: str
    hashes: frozenset[str]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _parse_lock(path: Path) -> list[LockedRequirement]:
    try:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
    except ImportError as error:  # build-time helper; never needed by packaged runtime
        raise PackagePreflightError(["build tool 'packaging' is unavailable to validate the lock"]) from error

    requirements: list[LockedRequirement] = []
    problems: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([^\s]+)(.*)$", line)
        if not match:
            problems.append(f"{LOCK_NAME}:{line_number}: malformed lock row")
            continue
        try:
            requirement = Requirement(match.group(1))
        except Exception:
            problems.append(f"{LOCK_NAME}:{line_number}: invalid requirement")
            continue
        if requirement.url or requirement.extras or requirement.marker:
            problems.append(f"{LOCK_NAME}:{line_number}: use plain pinned requirements without URL, extras, or markers")
            continue
        if len(requirement.specifier) != 1 or not next(iter(requirement.specifier)).operator == "==":
            problems.append(f"{LOCK_NAME}:{line_number}: dependency must be pinned with ==")
            continue
        version = next(iter(requirement.specifier)).version
        hashes = frozenset(re.findall(r"--hash=sha256:([0-9a-fA-F]{64})", match.group(2)))
        remainder = re.sub(r"--hash=sha256:[0-9a-fA-F]{64}", "", match.group(2)).strip()
        if not hashes or remainder:
            problems.append(f"{LOCK_NAME}:{line_number}: every dependency needs one or more SHA-256 hashes")
            continue
        requirements.append(LockedRequirement(
            name=requirement.name,
            normalized_name=canonicalize_name(requirement.name),
            version=version,
            hashes=frozenset(item.lower() for item in hashes),
        ))
    if not requirements:
        problems.append(f"{LOCK_NAME} contains no pinned dependencies")
    names = [item.normalized_name for item in requirements]
    if len(names) != len(set(names)):
        problems.append(f"{LOCK_NAME} contains duplicate dependency rows")
    if problems:
        raise PackagePreflightError(problems)
    return requirements


def _wheel_metadata(path: Path) -> tuple[str, str] | None:
    if not zipfile.is_zipfile(path):
        return None
    try:
        with zipfile.ZipFile(path) as wheel:
            metadata_files = [name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")]
            if len(metadata_files) != 1:
                return None
            content = wheel.read(metadata_files[0]).decode("utf-8", errors="replace")
    except (OSError, zipfile.BadZipFile):
        return None
    name = re.search(r"(?m)^Name:\s*(.+?)\s*$", content)
    version = re.search(r"(?m)^Version:\s*(.+?)\s*$", content)
    return (name.group(1), version.group(1)) if name and version else None


def _compatible_tags(path: Path) -> bool:
    try:
        from packaging.tags import sys_tags
        from packaging.utils import parse_wheel_filename
        _, _, _, tags = parse_wheel_filename(path.name)
    except (ImportError, ValueError):
        return False
    return not tags.isdisjoint(set(sys_tags()))


def _validate_direct_dependencies(root: Path, requirements: list[LockedRequirement]) -> list[str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    locked = {item.normalized_name for item in requirements}
    problems: list[str] = []
    try:
        from packaging.requirements import Requirement
        from packaging.version import Version
    except ImportError:
        return ["build tool 'packaging' is unavailable to validate project requirements"]
    by_name = {item.normalized_name: item for item in requirements}
    for raw in project.get("project", {}).get("dependencies", []):
        try:
            dependency = Requirement(raw)
        except Exception:
            problems.append(f"pyproject.toml has an invalid runtime dependency: {raw}")
            continue
        normalized = _normalized_name(dependency.name)
        if normalized not in locked:
            problems.append(f"runtime dependency {dependency.name} is absent from {LOCK_NAME}")
            continue
        try:
            if Version(by_name[normalized].version) not in dependency.specifier:
                problems.append(f"locked {dependency.name} version does not satisfy pyproject.toml")
        except Exception:
            problems.append(f"cannot validate locked version for {dependency.name}")
    return problems


def _wheel_plan(root: Path, requirements: list[LockedRequirement]) -> tuple[list[tuple[Path, str]], list[str]]:
    wheelhouse = root / WHEELHOUSE_NAME
    if not wheelhouse.is_dir():
        return [], [f"required dependency wheelhouse missing: {WHEELHOUSE_NAME}/"]
    wheels = sorted(wheelhouse.glob("*.whl"))
    problems: list[str] = []
    selected: list[tuple[Path, str]] = []
    for requirement in requirements:
        matches: list[Path] = []
        for wheel in wheels:
            metadata = _wheel_metadata(wheel)
            if not metadata:
                continue
            wheel_name, wheel_version = metadata
            if _normalized_name(wheel_name) != requirement.normalized_name or wheel_version != requirement.version:
                continue
            if _sha256(wheel) not in requirement.hashes:
                continue
            if not _compatible_tags(wheel):
                continue
            matches.append(wheel)
        if not matches:
            problems.append(
                f"no compatible, hash-matching wheel for {requirement.name}=={requirement.version} in {WHEELHOUSE_NAME}/"
            )
            continue
        selected.append((matches[0], f"wheelhouse/{matches[0].name}"))
    return selected, problems


def _is_sensitive(relative_path: str) -> bool:
    parts = [part.lower() for part in Path(relative_path).parts]
    if any(part in SENSITIVE_PARTS for part in parts):
        return True
    if any(part.startswith(".env") for part in parts):
        return True
    return any(any(marker in part for marker in ("operator-key", "restricted-export", "private-truth")) for part in parts)


def _read_manifest(root: Path) -> dict[str, Any]:
    try:
        return json.loads((root / "tests/fixtures/replay/benchmark-manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagePreflightError(["benchmark manifest is missing or invalid JSON"]) from error


def _preflight(root: Path) -> tuple[list[LockedRequirement], list[tuple[Path, str]], dict[str, Any]]:
    problems = [f"required artifact missing: {relative}" for relative in REQUIRED_FILES if not (root / relative).is_file()]
    if not (root / "frontend/dist").is_dir():
        problems.append("required built frontend directory missing: frontend/dist/")
    if not (root / WHEELHOUSE_NAME).is_dir():
        problems.append(f"required dependency wheelhouse missing: {WHEELHOUSE_NAME}/")
    for directory in (root / "frontend/dist", root / WHEELHOUSE_NAME):
        if directory.is_symlink():
            problems.append(f"symlink input directory rejected: {directory.relative_to(root).as_posix()}")
    for relative in REQUIRED_FILES:
        path = root / relative
        current = path
        while current != root:
            if current.is_symlink():
                problems.append(f"symlink input rejected: {current.relative_to(root).as_posix()}")
            current = current.parent
        if path.is_file() and _is_sensitive(relative):
            problems.append(f"sensitive input path rejected: {relative}")
    if problems:
        raise PackagePreflightError(problems)

    requirements = _parse_lock(root / LOCK_NAME)
    problems.extend(_validate_direct_dependencies(root, requirements))
    wheels, wheel_problems = _wheel_plan(root, requirements)
    problems.extend(wheel_problems)
    scenario_rows = json.loads((root / "backend/data/scenarios.json").read_text(encoding="utf-8"))
    if not isinstance(scenario_rows, list) or len(scenario_rows) != 12:
        problems.append("required synthetic scenario catalogue must contain the 12 source scenarios")
    benchmark = _read_manifest(root)
    if problems:
        raise PackagePreflightError(problems)
    return requirements, wheels, benchmark


def _safe_copy(source: Path, destination: Path, root: Path) -> None:
    relative = source.relative_to(root).as_posix()
    if _is_sensitive(relative) or source.is_symlink():
        raise PackagePreflightError([f"sensitive or symlink input rejected: {relative}"])
    if source.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise PackagePreflightError([f"restricted/audio/database artifact rejected: {relative}"])
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def _source_replay_status(root: Path) -> dict[str, str]:
    return {
        "status": "unavailable",
        "reason": "QA-01 canonical replay bundle and additive replay API are not available; this package profile is current synthetic training source only.",
        "qa01_bundle": "unavailable",
        "qa04_launcher": "unavailable",
    }


def _ai_status(root: Path) -> dict[str, str]:
    provider = root / "backend/ai_harness"
    assets = root / "assets/ai"
    if not provider.is_dir() or not assets.is_dir() or not any(assets.rglob("*")):
        reason = "AI provider implementation or provisioned offline model assets are missing; no ASR/provider result is included."
    else:
        reason = "AI assets/provider are outside this QA-06 package allowlist; AI remains unavailable until separately provisioned and verified."
    return {"status": "unavailable", "reason": reason}


def _version_snapshot(root: Path, requirements: list[LockedRequirement]) -> dict[str, Any]:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    frontend = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))
    models = (root / "backend/models.py").read_text(encoding="utf-8")
    scenarios = (root / "backend/scenarios.py").read_text(encoding="utf-8")
    engine = re.search(r'ENGINE_VERSION\s*=\s*["\']([^"\']+)', models)
    config = re.search(r'CONFIG_VERSION\s*=\s*["\']([^"\']+)', models)
    layout = re.search(r'"id"\s*:\s*"([^"]+)"\s*,\s*"version"\s*:\s*"([^"]+)"', scenarios)
    return {
        "project": pyproject.get("project", {}).get("version", "unknown"),
        "engine": engine.group(1) if engine else "unknown",
        "config": config.group(1) if config else "unknown",
        "layout_id": layout.group(1) if layout else "unknown",
        "layout_version": layout.group(2) if layout else "unknown",
        "frontend": frontend.get("version", "unknown"),
        "frontend_package_lock_sha256": _sha256(root / "frontend/package-lock.json"),
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "sqlite": sqlite3.sqlite_version,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "locked_python_dependencies": [
            {"name": item.name, "version": item.version} for item in requirements
        ],
    }


def build_package(repository_root: str | Path, output: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    destination = Path(output).resolve()
    if destination.exists() or destination.is_symlink():
        raise PackagePreflightError([f"output already exists; refusing to overwrite local artifacts: {destination}"])
    if destination == root or root not in destination.parents:
        # Package outputs must remain under the repository's explicitly selected output tree.
        raise PackagePreflightError(["output must be a new path inside the repository"])

    requirements, wheels, benchmark = _preflight(root)
    source_replay = _source_replay_status(root)
    ai = _ai_status(root)
    stage_parent = destination.parent
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=stage_parent))
    try:
        for relative in COPY_FILES:
            _safe_copy(root / relative, stage / relative, root)
        for wheel, relative in wheels:
            _safe_copy(wheel, stage / relative, root)
        dist_root = root / "frontend/dist"
        for source in sorted(dist_root.rglob("*")):
            if source.is_dir():
                continue
            if source.is_symlink():
                raise PackagePreflightError([f"symlink frontend artifact rejected: {source.relative_to(root).as_posix()}"])
            _safe_copy(source, stage / source.relative_to(root), root)

        readme = (
            "ATC FlowLens local synthetic training package\n"
            "Profile: FIXTURE/MOCK current source; NOT OPERATIONALLY VALIDATED.\n"
            "AI status: unavailable. QA-01 canonical source replay bundle and QA-04 launcher are unavailable.\n"
            "Install only from this package's local wheelhouse: python -m pip install --no-index --find-links wheelhouse -r requirements.lock\n"
            "Run from this directory with: python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000\n"
            "Use local-only synthetic training. This package is not a source replay integration or LAN readiness result.\n"
            "Runtime storage and operator credentials are created locally and are not included in this package.\n"
        )
        (stage / "README-OFFLINE.txt").write_text(readme, encoding="utf-8")

        artifact_rows: list[dict[str, Any]] = []
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            relative = path.relative_to(stage).as_posix()
            if relative == "manifest.json":
                continue
            if _is_sensitive(relative):
                raise PackagePreflightError([f"sensitive package path rejected: {relative}"])
            if path.suffix.lower() in {".html", ".js", ".css", ".json", ".txt", ".toml", ".py", ".lock"}:
                data = path.read_bytes()
                for pattern in SENSITIVE_CONTENT:
                    if pattern.search(data.decode("utf-8", errors="ignore")):
                        raise PackagePreflightError([f"credential-like content rejected from package: {relative}"])
            artifact_rows.append({
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            })

        ai_assets = []
        manifest: dict[str, Any] = {
            "schema_version": "flowlens-offline-package-1",
            "label": "FIXTURE/MOCK — current synthetic training source; NOT OPERATIONALLY VALIDATED",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "versions": _version_snapshot(root, requirements),
            "package_profile": "offline-local-synthetic-training",
            "scenario_catalogue": {
                "file": "backend/data/scenarios.json",
                "scenario_count": 12,
                "label": "current source synthetic catalogue; not QA-01 canonical replay fixture",
                "sha256": _sha256(root / "backend/data/scenarios.json"),
            },
            "source_replay": source_replay,
            "ai": ai,
            "ai_assets_included": ai_assets,
            "cold_runtime": {
                "status": "not_run",
                "reason": "Package assembly does not prove cold boot, offline installation, replay lifecycle, or backup/restart behavior.",
            },
            "dependencies": {
                "python_lock": LOCK_NAME,
                "python_wheels_included": len(wheels),
                "python_wheels": [
                    {"path": relative, "name": requirement.name, "version": requirement.version,
                     "sha256": _sha256(source)}
                    for (source, relative), requirement in zip(wheels, requirements, strict=True)
                ],
                "frontend_runtime": "compiled frontend/dist is included; Node/npm are build-time only",
                "packager_network_calls": False,
                "cold_runtime_download_status": "not_run",
            },
            "security": {
                "credentials_included": False,
                "operator_tokens_included": False,
                "private_truth_included": False,
                "restricted_exports_included": False,
                "audio_included": False,
                "runtime_database_included": False,
                "policy": "allowlisted source/build artifacts only; local runtime storage is excluded",
            },
            "benchmark_manifest": {
                "path": "tests/fixtures/replay/benchmark-manifest.json",
                "sha256": _sha256(root / "tests/fixtures/replay/benchmark-manifest.json"),
                "profile": benchmark.get("label", "unknown"),
            },
            "artifacts": artifact_rows,
            "manifest_hash_note": "manifest.json is intentionally excluded from its own artifacts hash list",
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(stage, destination)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="new output directory inside the repository")
    args = parser.parse_args(argv)
    output = Path(args.output)
    if not output.is_absolute():
        output = REPOSITORY_ROOT / output
    try:
        manifest = build_package(REPOSITORY_ROOT, output)
    except PackagePreflightError as error:
        print("Offline package preflight failed:", file=sys.stderr)
        for problem in error.problems:
            print(f"- {problem}", file=sys.stderr)
        print("- source replay status: unavailable (QA-01 canonical bundle and QA-04 launcher missing)", file=sys.stderr)
        print(f"- AI status: unavailable ({_ai_status(REPOSITORY_ROOT)['reason']})", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "built",
        "output": str(output.resolve()),
        "artifact_count": len(manifest["artifacts"]),
        "ai": manifest["ai"]["status"],
        "source_replay": manifest["source_replay"]["status"],
        "label": manifest["label"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
