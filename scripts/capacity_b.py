"""Opt-in bounded MOCK capacity measurements, never operational/provider latency."""

import argparse
import asyncio
import hashlib
import json
import platform
import random
import sqlite3
import sys
import time
import tracemalloc
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from uuid import UUID

from flowlens.advisory.exports import ReportRenderer
from flowlens.advisory.models import Inputs
from flowlens.advisory.provider import AdvisoryExecutor
from flowlens.advisory.service import AdvisoryService
from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import UnitOfWork
from flowlens.loops import reconstruct_loops
from flowlens.memory.models import AcceptedEvent
from flowlens.memory.reducer import reconstruct
from flowlens.memory.service import repo
from flowlens.providers.gemini.models import GeminiConfig
from flowlens.testing.advisory import (
    AdvisoryReferenceTransactions,
    MockAdvisoryAccess,
    MockAdvisoryClient,
)
from flowlens.testing.harness import FakePlatform
from flowlens.testing.intent_memory import STAMP, context, fixture, mock_provenance

GENERATOR = "b-capacity-mock-1"


class WindowAccess(MockAdvisoryAccess):
    """Explicit last-eight-event window within unchanged default input/token budgets."""

    def authoritative(
        self, ctx: RequestContext, operation: str, candidate: Contract | None, uow: UnitOfWork
    ) -> Inputs:
        inputs = super().authoritative(ctx, operation, candidate, uow)
        return Inputs(events=inputs.events[-8:], facts=inputs.facts, signals=inputs.signals)


def measured[T](operation: Callable[[], T]) -> tuple[T, float]:
    start = time.perf_counter()
    result = operation()
    return result, time.perf_counter() - start


async def sample(size: int, seed: int) -> dict[str, object]:
    if not 1 <= size <= 1024:
        raise ValueError("SIZE_OUT_OF_BOUNDS")
    rng = random.Random(seed)  # nosec B311 -- reproducible synthetic generation only
    ctx = RequestContext.model_validate(
        context().model_dump()
        | {
            "capabilities": [
                "read",
                "analysis",
                "review",
                "export",
                "admin",
            ]
        }
    )
    cfg = GeminiConfig()
    pairs = []
    for i in range(size):
        runway = rng.choice(("09", "27"))
        pairs.append(
            fixture(
                ctx, i + 1000, f"FLN214 hold short runway {runway}", runway=runway, time_ms=10 * i
            )
        )
    segments = [s for s, _ in pairs]
    fake = FakePlatform([], segments)
    provenance = mock_provenance(ctx, cfg)
    events = tuple(
        AcceptedEvent(
            id=c.id,
            session_id=ctx.session_id,
            analysis_run_id=ctx.analysis_run_id,
            revision=ctx.input_revision,
            input_hash=ctx.input_hash,
            config_hash=cfg.digest(),
            provenance=provenance,
            candidate=c,
            link=None,
            coverage_known=True,
            dependency_hashes=(hashlib.sha256(s.model_dump_json().encode()).hexdigest(),),
            event_time_ms=s.event_time_ms,
            available_time_ms=s.available_time_ms,
            recorded_at=STAMP,
        )
        for s, c in pairs
    )
    with TemporaryDirectory(prefix="flowlens-capacity-") as temporary:
        path = Path(temporary) / "mock.db"
        tx = AdvisoryReferenceTransactions(path)
        tx.seed(ctx)
        tracemalloc.start()
        try:

            def append() -> None:
                with tx.begin() as uow:
                    for event in events:
                        repo(uow).append(ctx, event)
                    uow.commit()

            _, append_s = measured(append)
            ledger_bytes = path.stat().st_size

            def inventory() -> tuple[AcceptedEvent, ...]:
                with tx.begin() as uow:
                    rows = repo(uow).inventory(ctx)
                if not all(isinstance(row, AcceptedEvent) for row in rows):
                    raise RuntimeError("UNEXPECTED_INVALIDATION")
                return tuple(row for row in rows if isinstance(row, AcceptedEvent))

            rows, inventory_s = measured(inventory)
            projection, reconstruction_s = measured(lambda: reconstruct(ctx, rows))
            loops, loops_s = measured(lambda: reconstruct_loops(ctx, rows))
            if len(rows) != size or len(projection) != size or len(loops) != size:
                raise RuntimeError("COUNT_INVARIANT_FAILED")
            if reconstruct(ctx, tuple(reversed(rows))) != projection:
                raise RuntimeError("ORDER_INVARIANT_FAILED")
            if any(
                p.instruction != "ACTIVE"
                or p.movement != "NOT_EVALUABLE"
                or p.readback != "NOT_OBSERVED"
                for p in projection
            ):
                raise RuntimeError("SAID_HEARD_OBSERVED_INVARIANT_FAILED")
            if any(loop.status != "OPEN" or loop.closing_evidence_ids for loop in loops):
                raise RuntimeError("FALSE_CLOSURE_INVARIANT_FAILED")
            access = WindowAccess(ctx, cfg)
            service = AdvisoryService(access, fake)
            client = MockAdvisoryClient()
            executor = AdvisoryExecutor(cfg, client)
            try:
                with tx.begin() as uow:
                    inputs = service.inputs(ctx, uow)
                started = time.perf_counter()
                proposal = await service.propose(
                    ctx,
                    "BRIEF",
                    inputs,
                    executor,
                    checkpoint=lambda: None,
                    reserve=lambda _: None,
                )
                advisory_s = time.perf_counter() - started
                identifier = UUID(int=500000)
                with tx.begin() as uow:
                    service.accept(
                        ctx,
                        proposal,
                        identifier=identifier,
                        stream_id=identifier,
                        expected_version=0,
                        recorded_at=STAMP,
                        event_time_ms=10000,
                        available_time_ms=10000,
                        uow=uow,
                    )
                    uow.commit()
                renderer = ReportRenderer(service, access)
                outputs = {}
                export_seconds = {}
                formats: tuple[Literal["JSON", "CSV", "HTML"], ...] = ("JSON", "CSV", "HTML")
                for fmt in formats:
                    with tx.begin() as uow:
                        started = time.perf_counter()
                        body, artifact = renderer.render(
                            ctx,
                            identifier,
                            fmt,
                            artifact_id=UUID(int=500001),
                            now=STAMP,
                            uow=uow,
                        )
                        elapsed = time.perf_counter() - started
                    if artifact.sha256 != hashlib.sha256(body).hexdigest():
                        raise RuntimeError("EXPORT_HASH_INVARIANT_FAILED")
                    outputs[fmt] = len(body)
                    export_seconds[fmt] = elapsed
                with closing(sqlite3.connect(path)) as conn:
                    if conn.execute("PRAGMA foreign_key_check").fetchall():
                        raise RuntimeError("FOREIGN_KEY_INVARIANT_FAILED")
                    counts = {
                        "memory": conn.execute(
                            "SELECT count(*) FROM analysis_memory_ledger"
                        ).fetchone()[0],
                        "advisory": conn.execute(
                            "SELECT count(*) FROM analysis_advisory_ledger"
                        ).fetchone()[0],
                    }
                _, peak = tracemalloc.get_traced_memory()
                result = {
                    "size": size,
                    "seed": seed,
                    "generator_version": GENERATOR,
                    "input_bytes": sum(len(e.model_dump_json().encode()) for e in events),
                    "input_sha256": hashlib.sha256(
                        "".join(e.model_dump_json() for e in events).encode()
                    ).hexdigest(),
                    "seconds": {
                        "ledger_append": append_s,
                        "inventory": inventory_s,
                        "reconstruction": reconstruction_s,
                        "loops": loops_s,
                        "mock_brief_proposal": advisory_s,
                        "export": export_seconds,
                    },
                    "memory_python_peak_bytes": peak,
                    "memory_method": "tracemalloc; excludes native allocations/RSS/generator",
                    "ledger_database_bytes": ledger_bytes,
                    "final_database_bytes": path.stat().st_size,
                    "output_bytes": outputs,
                    "ledger_rows": counts,
                    "advisory_window_events": len(inputs.events),
                    "semantic_invariants": "PASS",
                    "mock_calls": client.calls,
                    "real_stt_calls": 0,
                    "real_gemini_calls": 0,
                }
            finally:
                await executor.close()
        finally:
            tracemalloc.stop()
    return result | {"disposable_storage_cleaned": not path.exists()}


async def run(sizes: list[int], repetitions: int, seed: int) -> dict[str, object]:
    if not 1 <= repetitions <= 5 or not 1 <= len(sizes) <= 5 or len(set(sizes)) != len(sizes):
        raise ValueError("RUN_BOUNDS_INVALID")
    samples = []
    for size in sizes:
        for repetition in range(repetitions):
            samples.append(await sample(size, seed) | {"repetition": repetition + 1})
    return {
        "profile": "MOCK",
        "status": "SYNTHETIC_BASELINE_NOT_OPERATIONAL_CAPACITY",
        "generator_version": GENERATOR,
        "seed": seed,
        "repetitions": repetitions,
        "environment": {
            "os": platform.platform(),
            "python": sys.version,
            "sqlite": sqlite3.sqlite_version,
            "executable": sys.executable,
        },
        "samples": samples,
        "performance_targets": "UNSET",
        "integrated_readiness": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Opt in to bounded synthetic work")
    parser.add_argument("--sizes", type=int, nargs="+", default=[16, 128, 512])
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--seed", type=int, default=214)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required; no capacity work runs by default")
    if any(not 1 <= size <= 1024 for size in args.sizes):
        parser.error("sizes must be within 1..1024")
    report = asyncio.run(run(args.sizes, args.repetitions, args.seed))
    body = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
