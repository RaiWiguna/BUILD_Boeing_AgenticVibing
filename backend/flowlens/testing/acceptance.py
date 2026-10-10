"""B06 local acceptance runner. Explicit MOCK ports; never production composition.

Run with --suite to include B01-B05 regression and both frozen contract tracks.
No credential discovery, paid provider call, route or worker handler installation.
"""

import argparse
import asyncio
import hashlib
import json
import platform as runtime_platform
import sqlite3
import subprocess  # nosec B404
import sys
import time
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from uuid import UUID

from flowlens import CONTRACT_VERSION
from flowlens.advisory.diagnostics import diagnostics
from flowlens.advisory.provider import AdvisoryExecutor
from flowlens.advisory.service import register_advisory
from flowlens.advisory.service import repo as advisory_repo
from flowlens.analysis.config import AnalysisConfig
from flowlens.analysis.module import AnalysisFoundation, register_analysis
from flowlens.analysis.transcript_records import RawTranscript
from flowlens.analysis.transcripts import RAW, TranscriptLifecycle, register_transcripts
from flowlens.analysis.transcripts import repo as transcript_repo
from flowlens.contracts.models import RequestContext
from flowlens.contracts.ports import UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistration, ModuleRegistry, order_migrations
from flowlens.memory.service import register_memory
from flowlens.memory.service import repo as memory_repo
from flowlens.providers.stt.adapter import map_response
from flowlens.testing.advisory import (
    AdvisoryReferenceTransactions,
    MockAdvisoryClient,
    setup,
)
from flowlens.testing.analysis import PLATFORM_REFERENCE
from flowlens.testing.intent_memory import STAMP, MockAuthority, fixture, mock_provenance
from flowlens.testing.stt import mock_binding, mock_config, mock_response

ROOT = Path(__file__).resolve().parents[3]
STANDALONES = (
    ("flowlens.testing", "--track", "B"),
    ("flowlens.testing.analysis",),
    ("flowlens.testing.audio_worker",),
    ("flowlens.testing.audio_worker", "--real"),
    ("flowlens.testing.stt",),
    ("flowlens.testing.transcripts",),
    ("flowlens.testing.stt_worker",),
    ("flowlens.testing.intent_memory",),
    ("flowlens.testing.advisory",),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def manifest(registrations: tuple[ModuleRegistration, ...]) -> dict[str, object]:
    """Read the actual registration objects; do not invent absent integration hooks."""
    registry = ModuleRegistry(profile="test")
    for registration in registrations:
        registry.register(registration)
    ordered = order_migrations(
        [PLATFORM_REFERENCE, *(m for r in registrations for m in r.migrations)]
    )
    namespaces = [n for r in registrations for n in r.repositories]
    require(len(namespaces) == len(set(namespaces)), "Repository namespace collision")
    require(
        all(
            r.mock
            and r.contract_version == CONTRACT_VERSION
            and r.readiness is not None
            and not r.readiness()
            and not r.routes
            and not r.job_handlers
            and r.snapshot_reader is None
            and r.purge_handler is not None
            and set(r.inventory_namespaces) == set(r.repositories)
            for r in registrations
        ),
        "Registration boundary/readiness violated",
    )
    return {
        "contract_version": CONTRACT_VERSION,
        "modules": [
            {
                "name": r.name,
                "services": sorted(r.services),
                "repositories": sorted(r.repositories),
                "inventory_namespaces": list(r.inventory_namespaces),
                "config_keys": list(r.config_keys),
                "routes": [],
                "job_handlers": [],
                "snapshot_reader": None,
                "purge_handler": True,
                "ready": False,
            }
            for r in registrations
        ],
        "migrations": [
            {
                "id": m.id,
                "owner": m.owner,
                "depends_on": list(m.depends_on),
                "sql_sha256": hashlib.sha256(m.sql.encode()).hexdigest(),
            }
            for m in ordered
        ],
        "b02_registration": "executor/worker only; no route/job handler",
        "platform": "MOCK reference schema and injected ports; not Package A runtime",
    }


async def local_checks() -> dict[str, object]:
    """One disposable DB, actual B registrations, caller-controlled cross-module UOW."""
    with TemporaryDirectory(prefix="flowlens-b06-") as temp:
        path = Path(temp) / "acceptance.db"
        ctx, cfg, tx, platform, access, advisory = setup(path)
        binding, _ = mock_binding(mock_config())
        raw = map_response(mock_config(), binding, mock_response())

        def authority(context: RequestContext, candidate: RawTranscript, uow: UnitOfWork) -> None:
            context.require("analysis", candidate.session_id, candidate.analysis_run_id)
            access.authoritative(context, "TRANSCRIPT", candidate, uow)
            if candidate != raw:
                raise ContractError("SOURCE_REVISION_CHANGED")

        pairs = [
            fixture(ctx, 10, "FLN214 hold short runway 27"),
            fixture(ctx, 11, "FLN214 hold short runway 27", "READBACK", time_ms=3000),
        ]
        registrations = (
            register_analysis(AnalysisConfig(profile="test"), tx),
            register_transcripts(tx, platform, authority),
            register_memory(tx, MockAuthority(ctx, [p[0] for p in pairs], cfg.digest()), platform),
            register_advisory(tx, access, platform),
        )
        inventory = manifest(registrations)
        foundation = cast(AnalysisFoundation, registrations[0].services["analysis"])
        transcripts = cast(TranscriptLifecycle, registrations[1].services["transcript_lifecycle"])
        client = MockAdvisoryClient()
        executor = AdvisoryExecutor(cfg, client)
        try:
            with tx.begin() as uow:
                inputs = advisory.inputs(ctx, uow)
            proposal = await advisory.propose(
                ctx,
                "BRIEF",
                inputs,
                executor,
                checkpoint=lambda: None,
                reserve=lambda _: None,
                local_provenance=mock_provenance(ctx, cfg),
            )

            def write(uow: UnitOfWork) -> None:
                foundation.configure(ctx, uow)
                transcripts.store_raw(ctx, raw, uow)
                advisory.accept(
                    ctx,
                    proposal,
                    identifier=UUID(int=600),
                    stream_id=UUID(int=600),
                    expected_version=0,
                    recorded_at=STAMP,
                    event_time_ms=10000,
                    available_time_ms=10000,
                    uow=uow,
                )

            def ledger_counts() -> tuple[int, ...]:
                with tx.begin() as uow:
                    return tuple(
                        uow.conn.execute(query).fetchone()[0]
                        for query in (
                            "SELECT count(*) FROM reference_records",
                            "SELECT count(*) FROM reference_audit",
                            "SELECT count(*) FROM reference_events",
                        )
                    )

            baseline_ledger = ledger_counts()

            # Omitted commit rolls back all modules, including a memory mutation.
            with tx.begin() as uow:
                write(uow)
                memory_repo(uow).purge(ctx)
            with tx.begin() as uow:
                require(not transcript_repo(uow, RAW).inventory(ctx), "Raw rollback failed")
                require(not advisory_repo(uow).inventory(ctx), "Advisory rollback failed")
                require(len(memory_repo(uow).inventory(ctx)) == 2, "Memory rollback failed")
            require(not foundation.inventory(ctx), "Config rollback failed")
            require(ledger_counts() == baseline_ledger, "Evidence/audit/event rollback failed")
            try:
                with tx.begin() as uow:
                    write(uow)
                    memory_repo(uow).purge(ctx)
                    raise RuntimeError("B06_INJECTED_FAILURE_AFTER_WRITES")
            except RuntimeError as exc:
                if str(exc) != "B06_INJECTED_FAILURE_AFTER_WRITES":
                    raise
            require(ledger_counts() == baseline_ledger, "Failure leaked ledger side effects")
            require(not foundation.inventory(ctx), "Failure leaked configuration")
            published: list[int] = []
            with tx.begin() as uow:
                write(uow)
                uow.after_commit(lambda: published.append(len(foundation.inventory(ctx))))
                require(not published, "Publication before commit")
                uow.commit()
            require(published == [1], "Publication did not observe durable state")
            # Fresh factory proves persistence without relying on in-memory service state.
            restarted = AdvisoryReferenceTransactions(path)
            with restarted.begin() as uow:
                require(len(advisory_repo(uow).inventory(ctx)) == 1, "Restart failed")
                require(len(transcript_repo(uow, RAW).inventory(ctx)) == 1, "Raw restart failed")
                require(len(memory_repo(uow).inventory(ctx)) == 2, "Memory restart failed")
                transcripts.store_raw(ctx, raw, uow)
                uow.commit()
            # Replayed accepted input must recheck current cancellation authority.
            access.cancelled = True
            try:
                with restarted.begin() as uow:
                    transcripts.store_raw(ctx, raw, uow)
            except ContractError as exc:
                require(exc.code == "JOB_CANCELLED", "Wrong cancellation failure")
            else:
                raise RuntimeError("Cancelled duplicate was accepted")
            access.cancelled = False
            with restarted.begin() as uow:
                before = uow.conn.execute("SELECT count(*) FROM platform_runs").fetchone()[0]
                for registration in reversed(registrations):
                    purge = registration.purge_handler
                    if purge is None:
                        raise RuntimeError("Missing purge")
                    purge(ctx, uow)
                require(
                    uow.conn.execute("SELECT count(*) FROM platform_runs").fetchone()[0] == before,
                    "Purge crossed platform ownership",
                )
                require(not uow.conn.execute("PRAGMA foreign_key_check").fetchall(), "FK drift")
                uow.commit()
            with restarted.begin() as uow:
                require(not advisory_repo(uow).inventory(ctx), "Advisory purge failed")
                require(not memory_repo(uow).inventory(ctx), "Memory purge failed")
                require(not transcript_repo(uow, RAW).inventory(ctx), "Raw purge failed")
            require(not foundation.inventory(ctx), "Config purge failed")
        finally:
            await executor.close()
        require(client.closed, "Provider client not closed")
    require(not path.exists(), "Disposable DB not cleaned")
    return {
        **diagnostics(cfg),
        "unit": "B06",
        "status": "passed",
        "profile": "MOCK",
        "manifest": inventory,
        "mock_provider_calls": client.calls,
        "real_stt_calls": 0,
        "real_gemini_calls": 0,
        "real_provider_calls": 0,
        "database": "disposable-cleaned",
        "acceptance": "local only; B06 remains in_progress",
    }


def command(args: tuple[str, ...]) -> dict[str, object]:
    started = time.monotonic()
    try:
        # CLI callers supply only the fixed local verification commands below, without a shell.
        result = subprocess.run(  # nosec B603
            [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        return {"args": list(args), "status": "TIMEOUT", "exit_code": None}
    return {
        "args": list(args),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "exit_code": result.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "stdout": result.stdout[-16000:],
        "stderr": result.stderr[-16000:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", action="store_true", help="Run B regression and A/B contracts")
    parser.add_argument("--output", type=Path, help="Save JSON evidence to a caller-selected file")
    args = parser.parse_args()
    result = asyncio.run(local_checks())
    commands = [command(("-m", *entry)) for entry in STANDALONES]
    if args.suite:
        commands.extend(
            command(("-m", "pytest", *paths, "--track", track, "-q"))
            for paths, track in (
                (("tests/analysis", "tests/contracts"), "B"),
                (("tests/contracts",), "A"),
            )
        )
    result["commands"] = commands
    result["suite"] = "RUN" if args.suite else "NOT_RUN"
    result["status"] = "passed" if all(c["status"] == "PASS" for c in commands) else "failed"
    result["source_sha256"] = {
        str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "backend/flowlens").rglob("*.py"))
    }
    result["uv_lock_sha256"] = hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
    result["verification_input_sha256"] = {
        str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ("tests/analysis", "tests/contracts", "contracts", "scripts")
        for p in sorted((ROOT / directory).rglob("*"))
        if p.is_file() and p.suffix in (".py", ".json", ".wav")
    }
    result["runtime"] = {
        "python": runtime_platform.python_version(),
        "platform": sys.platform,
        "sqlite": sqlite3.sqlite_version,
        "dependencies": {
            name: version(name)
            for name in ("google-cloud-speech", "google-genai", "pydantic", "fastapi", "pytest")
        },
    }
    encoded = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
