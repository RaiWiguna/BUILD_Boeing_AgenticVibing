"""Local tooling boundaries and private/public compatibility using fake ports only."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
from flowlens.contracts.models import CriticalSlot, Intent, JobResult
from flowlens.testing.advisory import setup
from flowlens.testing.intent_memory import context, fixture
from pydantic import ValidationError

from scripts.capacity_b import run, sample

ROOT = Path(__file__).resolve().parents[2]


def test_capacity_opt_in_and_bounds(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/capacity_b.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2 and "--execute is required" in result.stderr
    with pytest.raises(ValueError, match="BOUNDS"):
        asyncio.run(sample(1025, 214))
    with pytest.raises(ValueError, match="BOUNDS"):
        asyncio.run(run([4], 6, 214))


def test_capacity_reproducible_and_disposable():
    results = asyncio.run(run([4, 9], 2, 214))
    samples = results["samples"]
    for first, second in (samples[:2], samples[2:]):
        assert first["input_sha256"] == second["input_sha256"]
        assert first["output_bytes"] == second["output_bytes"]
        assert first["ledger_rows"] == {"memory": first["size"], "advisory": 1}
        assert first["advisory_window_events"] == min(first["size"], 8)
        assert first["semantic_invariants"] == "PASS"
        assert first["disposable_storage_cleaned"] and second["disposable_storage_cleaned"]
        assert first["real_stt_calls"] == first["real_gemini_calls"] == 0


def test_critical_slot_is_representable_but_candidate_needs_explicit_projection():
    _, candidate = fixture(context(), 10, "FLN214 hold short runway 27")
    slot = CriticalSlot.model_validate_json(candidate.callsign.model_dump_json())
    assert slot.value == "FLN214" and slot.evidence_ids == list(candidate.callsign.evidence_ids)
    assert slot.quality == candidate.callsign.quality
    with pytest.raises(ValidationError):
        Intent.model_validate_json(candidate.model_dump_json())
    # Evidence has no available-time field. QuoteSlot is representable, but the
    # full private candidate includes condition/negation uncertainty and private
    # version/segment fields that cannot be silently passed to public Intent.
    assert "available_time_ms" not in type(candidate.evidence[0]).model_fields


def test_actual_private_document_is_not_a_frozen_job_output(tmp_path):
    from flowlens.advisory.provider import AdvisoryExecutor
    from flowlens.testing.advisory import MockAdvisoryClient
    from flowlens.testing.intent_memory import mock_provenance

    ctx, cfg, tx, _, _, service = setup(tmp_path / "compatibility.db")
    with tx.begin() as uow:
        inputs = service.inputs(ctx, uow)

    async def proposal():
        executor = AdvisoryExecutor(cfg, MockAdvisoryClient())
        try:
            return await service.propose(
                ctx,
                "FINDINGS",
                inputs,
                executor,
                checkpoint=lambda: None,
                reserve=lambda _: None,
                local_provenance=mock_provenance(ctx, cfg),
            )
        finally:
            await executor.close()

    document = asyncio.run(proposal()).document
    body = json.loads((ROOT / "contracts/examples/job_result.json").read_text())
    body["outputs"] = [document.model_dump(mode="json")]
    with pytest.raises(ValidationError):
        JobResult.model_validate_json(json.dumps(body))
