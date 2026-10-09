"""Safe provider readiness and measured communication indicators only."""

from flowlens.advisory.models import Inputs
from flowlens.contracts.models import Contract, RequestContext
from flowlens.intent.validation import visible
from flowlens.memory.models import AcceptedEvent
from flowlens.memory.reducer import reconstruct
from flowlens.providers.gemini.models import GeminiConfig
from flowlens.providers.gemini.smoke import SmokeApproval, preflight


class Metrics(Contract):
    label: str = "MEASURED_COMMUNICATION_INDICATORS_NOT_WORKLOAD_OR_FITNESS"
    observed_speech_span_ms: int
    observed_entity_switches: int
    known_open_loops: int
    unknown_loops: int
    frequency_occupancy: None = None
    limitations: tuple[str, ...] = ("NO_VALIDATED_VAD_OR_CHANNEL_OVERLAP", "OBSERVED_CONTEXT_ONLY")


def metrics(ctx: RequestContext, inputs: Inputs) -> Metrics:
    ctx.require("read", ctx.session_id, ctx.analysis_run_id)
    intervals = []
    entities = []
    for e in sorted(inputs.events, key=lambda e: (e.event_time_ms, str(e.id))):
        visible(ctx, e)
        if isinstance(e, AcceptedEvent):
            for ev in e.candidate.evidence:
                if ev.start_ms is not None and ev.end_ms is not None:
                    intervals.append((ev.start_ms, ev.end_ms))
            if len(e.candidate.entity_candidates) == 1:
                entities.append(e.candidate.entity_candidates[0])
    total, end = 0, 0
    for start, stop in sorted(intervals):
        total += max(0, stop - max(start, end))
        end = max(end, stop)
    projection = reconstruct(ctx, inputs.events)
    return Metrics(
        observed_speech_span_ms=total,
        observed_entity_switches=sum(a != b for a, b in zip(entities, entities[1:], strict=False)),
        known_open_loops=sum(p.loop == "OPEN" and not p.stale for p in projection),
        unknown_loops=sum(p.loop == "UNKNOWN" and not p.stale for p in projection),
    )


def diagnostics(
    config: GeminiConfig,
    approval: SmokeApproval | None = None,
    *,
    credential_present: bool = False,
) -> dict[str, object]:
    reasons = preflight(config, approval, credential_present=credential_present)
    return {
        "profile": config.profile,
        "model": config.model,
        "sdk_version": config.sdk_version,
        "config_hash": config.digest(),
        "mock_only": config.profile == "MOCK",
        "account_acceptance": "UNVERIFIED",
        "real_smoke": "NOT_RUN",
        "preflight_reasons": reasons,
        "real_provider_ready": False,
        "integrated_pipeline_ready": False,
        "benchmark_status": "BLOCKED",
        "benchmark_metrics": None,
        "B03_EXTERNAL_ACCEPTANCE_PENDING": [
            "STT_ACCOUNT_LOGIN_REQUIRED",
            "AUDITED_BENCHMARK_PENDING",
        ],
        "B04_EXTERNAL_ACCEPTANCE_PENDING": [
            "GEMINI_ACCOUNT_ACCESS_UNVERIFIED",
            "REAL_GEMINI_SMOKE_PENDING",
            "AUDITED_SEMANTIC_BENCHMARK_PENDING",
        ],
        "GEMINI_EXTERNAL_ACCEPTANCE_PENDING": True,
    }
