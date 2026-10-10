"""Build-artifact audit and clean locked wheel install outside the source checkout."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404 -- bounded local tool invocations, no shell
import sys
import tarfile
import time
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = (
    "flowlens.testing.analysis",
    "flowlens.testing.stt",
    "flowlens.testing.transcripts",
    "flowlens.testing.stt_worker",
    "flowlens.testing.intent_memory",
    "flowlens.testing.advisory",
)


def command(args: list[str], cwd: Path, env: dict[str, str]) -> dict[str, object]:
    started = time.perf_counter()
    result = subprocess.run(  # nosec B603 -- trusted uv/python executables, shell=False
        args, cwd=cwd, env=env, capture_output=True, text=True, timeout=300, check=False
    )
    record = {
        "argv": args,
        "exit_code": result.returncode,
        "seconds": time.perf_counter() - started,
        "stdout": result.stdout[-16000:],
        "stderr": result.stderr[-16000:],
    }
    if result.returncode:
        raise RuntimeError(json.dumps(record))
    return record


def audit(wheel: Path, sdist: Path) -> dict[str, object]:
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = archive.namelist()
    with tarfile.open(sdist, "r:gz") as archive:
        sdist_files = archive.getnames()
    prohibited = ("evaluation/", "tests/", "scripts/", "docs/", "artifacts/")
    if any(name.startswith(prohibited) or "/evaluation/" in name for name in wheel_files):
        raise RuntimeError("EVALUATOR_OR_PRIVATE_FILES_IN_WHEEL")
    expected = {
        "flowlens/intent/models.py",
        "flowlens/memory/reducer.py",
        "flowlens/advisory/exports.py",
        "flowlens/providers/gemini/adapter.py",
    }
    if not expected <= set(wheel_files):
        raise RuntimeError("RUNTIME_MODULES_MISSING")
    if any(
        "/evaluation/reports/" in name and not name.endswith(".gitkeep") for name in sdist_files
    ):
        raise RuntimeError("PRIVATE_EVALUATION_REPORT_IN_SDIST")
    if any(
        any(f"/{prefix}/" in name for prefix in ("docs/pitch", "tests/browser", "tmp"))
        for name in sdist_files
    ):
        raise RuntimeError("UNRELATED_WORKSPACE_FILES_IN_SDIST")
    return {
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "sdist_sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
        "wheel_bytes": wheel.stat().st_size,
        "sdist_bytes": sdist.stat().st_size,
        "wheel_files": wheel_files,
        "sdist_files": sdist_files,
        "runtime_wheel_truth_fixtures": "ABSENT",
    }


def run(wheel: Path, sdist: Path) -> dict[str, object]:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("UV_REQUIRED")
    report = audit(wheel, sdist)
    env = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"):
        env.pop(name, None)
    records = []
    with TemporaryDirectory(prefix="flowlens-installed-") as temporary:
        work = Path(temporary).resolve()
        if work.is_relative_to(ROOT):
            raise RuntimeError("SMOKE_MUST_BE_OUTSIDE_CHECKOUT")
        requirements = work / "locked.txt"
        records.append(
            command(
                [
                    uv,
                    "export",
                    "--locked",
                    "--no-dev",
                    "--no-emit-project",
                    "--format",
                    "requirements-txt",
                    "--output-file",
                    str(requirements),
                ],
                ROOT,
                env,
            )
        )
        records.append(
            command([uv, "venv", "--python", sys.executable, str(work / "env")], work, env)
        )
        python = work / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        records.append(
            command(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    "--require-hashes",
                    "-r",
                    str(requirements),
                ],
                work,
                env,
            )
        )
        records.append(
            command(
                [uv, "pip", "install", "--python", str(python), "--no-deps", str(wheel)], work, env
            )
        )
        probe = """
import importlib, importlib.metadata, json, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
modules = [importlib.import_module(n) for n in (
    'flowlens', 'flowlens.intent.models', 'flowlens.memory.reducer',
    'flowlens.advisory.exports', 'flowlens.providers.gemini.adapter',
    'flowlens.providers.stt.adapter')]
paths = [str(pathlib.Path(m.__file__).resolve()) for m in modules]
if any(pathlib.Path(p).is_relative_to(root) for p in paths):
    raise RuntimeError('CHECKOUT_IMPORT_LEAK')
if any(pathlib.Path(p).resolve().is_relative_to(root) for p in sys.path if p):
    raise RuntimeError('CHECKOUT_SYS_PATH_LEAK')
print(json.dumps({'modules': paths, 'sys_path': sys.path,
    'dependencies': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}}))
"""
        probe_result = command([str(python), "-I", "-c", probe, str(ROOT)], work, env)
        records.append(probe_result)
        installed = json.loads(str(probe_result["stdout"]))
        report["import_probe"] = installed
        records.append(command([uv, "pip", "check", "--python", str(python)], work, env))
        for entrypoint in ENTRYPOINTS:
            records.append(command([str(python), "-I", "-m", entrypoint], work, env))
        report["working_directory"] = str(work)
        report["locked_requirements_sha256"] = hashlib.sha256(requirements.read_bytes()).hexdigest()
    return report | {
        "status": "PASS",
        "commands": records,
        "disposable_environment_cleaned": not work.exists(),
        "repo_local_not_run": [
            "flowlens.testing.acceptance (tests/scripts/contracts tree)",
            "flowlens.testing.audio_worker (source fixtures)",
            "flowlens.testing (explicit --fixtures directory required)",
        ],
        "real_stt_calls": 0,
        "real_gemini_calls": 0,
        "integrated_readiness": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.wheel.resolve(), args.sdist.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: report[k]
                for k in ("status", "wheel_bytes", "sdist_bytes", "disposable_environment_cleaned")
            }
        )
    )


if __name__ == "__main__":
    main()
