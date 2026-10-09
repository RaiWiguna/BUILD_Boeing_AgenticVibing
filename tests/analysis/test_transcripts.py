"""Disposable API-side MOCK transaction acceptance; no real platform composition."""

import asyncio
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
from flowlens.analysis.transcript_projection import project
from flowlens.analysis.transcript_records import TranscriptDependency
from flowlens.analysis.transcript_store import RECORDS, TRANSCRIPT_MIGRATIONS
from flowlens.analysis.transcripts import (
    RAW,
    TranscriptLifecycle,
    register_transcripts,
)
from flowlens.contracts.models import RequestContext, TranscriptSegment
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistry
from flowlens.providers.stt.adapter import STTExecutor
from flowlens.testing.analysis import PLATFORM_REFERENCE, AnalysisReferenceTransactions
from flowlens.testing.harness import FakePlatform
from flowlens.testing.stt import MockClient, mock_binding, mock_config
from flowlens.testing.transcripts import TranscriptReferenceTransactions
from pydantic import ValidationError


class MockAuthority:
    profile = "MOCK"

    def __init__(self, raw):
        self.raw = raw
        self.cancelled = False
        self.calls = 0

    def __call__(self, context, raw, uow):
        uow.check_open()
        self.calls += 1
        if self.cancelled or raw != self.raw:
            raise ContractError("LEASE_EXPIRED")


@pytest.fixture
def lifecycle(tmp_path):
    config = mock_config()
    binding, audio = mock_binding(config)

    async def run():
        executor = STTExecutor(config, MockClient())
        try:
            return await executor.transcribe(
                binding, audio, lambda: binding.lease, reserve=lambda lease, ms: None
            )  # MOCK budget
        finally:
            await executor.close()

    raw, _ = asyncio.run(run())
    context = RequestContext.model_validate(
        binding.context.model_dump()
        | {"capabilities": ["read", "audio", "analysis", "review", "admin"], "as_of_ms": 100000}
    )
    segment = project(raw, recorded_at=datetime(2026, 10, 9, tzinfo=UTC), origin="MOCK")[0]
    evidence = FakePlatform([], [segment])
    authority = MockAuthority(raw)
    service = TranscriptLifecycle(evidence, authority)
    transactions = TranscriptReferenceTransactions(tmp_path / "transcripts.db")
    transactions.seed(context)
    return transactions, service, context, raw, segment, evidence, authority


def counts(transactions):
    with closing(sqlite3.connect(transactions.path)) as conn:
        return tuple(
            conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in [
                *(t for t, _ in RECORDS.values()),
                "reference_records",
                "reference_audit",
                "reference_events",
            ]
        )


def accept(bundle):
    transactions, service, context, raw, segment, _, _ = bundle
    with transactions.begin() as uow:
        service.store_raw(context, raw, uow)
        service.add_original(context, raw.id, segment, uow)
        uow.commit()


def correction(previous, text="hold short"):
    identifier = uuid4()
    evidence = previous.evidence[0].model_copy(
        update={
            "id": uuid4(),
            "segment_id": identifier,
            "quote": text,
            "span_start": 0,
            "span_end": len(text),
        }
    )
    return TranscriptSegment.model_validate(
        previous.model_dump()
        | {
            "id": identifier,
            "text": text,
            "recorded_at": previous.recorded_at + timedelta(seconds=1),
            "evidence": [evidence.model_dump()],
            "origin": "HUMAN_CORRECTION",
            "supersedes_id": previous.id,
            "reason": "Reviewed synthetic audio",
            "confidence": None,
            "quality": "AMBIGUOUS",
        }
    )


def dependency(context, identifier):
    return TranscriptDependency(
        id=uuid4(),
        session_id=context.session_id,
        analysis_run_id=context.analysis_run_id,
        revision=context.input_revision,
        input_hash=context.input_hash,
        transcript_ids=(identifier,),
        kind="INTENT",
    )


def test_original_idempotent_exact_payload_restart_and_safe_events(lifecycle):
    transactions, service, context, raw, segment, _, authority = lifecycle
    accept(lifecycle)
    assert counts(transactions) == (1, 1, 0, 0, 1, 2, 2)
    before = counts(transactions)
    with transactions.begin() as uow:
        service.store_raw(context, raw, uow)
        service.add_original(context, raw.id, segment, uow)
        uow.commit()
    assert counts(transactions) == before and authority.calls == 4
    restarted = TranscriptReferenceTransactions(transactions.path)
    with restarted.begin() as uow:
        assert uow.repository(RAW).get(context, raw.id) == raw
        assert service.revision(context, segment.id, uow).segment == segment
        events = [
            json.loads(r[0]) for r in uow.conn.execute("SELECT payload FROM reference_events")
        ]
        assert [e["action"] for e in events] == ["RAW_STORED", "TRANSCRIPT_ADDED"]
        assert all("hold" not in json.dumps(e) and "response_base64" not in e for e in events)
        assert uow.conn.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("failure", ["domain", "evidence", "audit", "event", "omitted_commit"])
def test_shared_transaction_atomic_failure(lifecycle, monkeypatch, failure):
    transactions, service, context, raw, segment, evidence, _ = lifecycle

    def fail(*args):
        raise RuntimeError("injected")

    def write():
        with transactions.begin() as uow:
            if failure == "audit":
                monkeypatch.setattr(uow, "audit", fail)
            if failure == "event":
                monkeypatch.setattr(uow, "enqueue_event", fail)
            if failure == "evidence":
                monkeypatch.setattr(evidence, "register", fail)
            service.store_raw(context, raw, uow)
            service.add_original(context, raw.id, segment, uow)
            if failure == "domain":
                raise RuntimeError("injected")
            if failure != "omitted_commit":
                uow.commit()

    if failure == "omitted_commit":
        write()
    else:
        with pytest.raises(RuntimeError):
            write()
    assert counts(transactions) == (0, 0, 0, 0, 0, 0, 0)


def test_append_correction_original_raw_immutable_stale_and_conflict(lifecycle):
    transactions, service, context, raw, segment, evidence, _ = lifecycle
    accept(lifecycle)
    dep = dependency(context, segment.id)
    corrected = correction(segment)
    evidence.segments.append(corrected)
    with transactions.begin() as uow:
        service.depend(context, dep, uow)
        assert service.stale(context, dep.id, uow) is False
        service.correct(context, segment.id, corrected, uow)
        assert service.stale(context, dep.id, uow) is True
        current = dependency(context, corrected.id)
        service.depend(context, current, uow)
        assert service.stale(context, current.id, uow) is False
        record = service.revision(context, corrected.id, uow)
        assert record.actor_id == context.actor_id and record.correction_revision == 1
        assert record.original_id == segment.id and record.previous_id == segment.id
        assert uow.repository(RAW).get(context, raw.id) == raw
        assert service.revision(context, segment.id, uow).segment == segment
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            service.correct(context, segment.id, correction(segment, "different"), uow)
        uow.commit()
    assert counts(transactions) == (1, 2, 2, 1, 2, 3, 3)
    with transactions.begin() as uow:
        service.invalidate_for_reanalysis(context, corrected.id, uow)
        assert service.stale(context, current.id, uow) is True
        uow.commit()
    restarted = TranscriptReferenceTransactions(transactions.path)
    with restarted.begin() as uow:
        assert service.stale(context, dep.id, uow) and service.stale(context, current.id, uow)


@pytest.mark.parametrize(
    "change",
    [
        {"quote": "wrong"},
        {"span_end": 999},
        {"start_ms": 0},
        {"end_ms": 10000},
        {"source_hash": "f" * 64},
        {"source_id": uuid4()},
        {"session_id": uuid4()},
        {"analysis_run_id": uuid4()},
        {"revision": 2},
        {"segment_id": uuid4()},
    ],
)
def test_evidence_hash_scope_span_range(lifecycle, change):
    transactions, service, context, _, segment, _, _ = lifecycle
    accept(lifecycle)
    with transactions.begin() as uow:
        assert service.validate_evidence(context, segment.evidence[0], uow) == segment.evidence[0]
        with pytest.raises(ContractError):
            service.validate_evidence(context, segment.evidence[0].model_copy(update=change), uow)


@pytest.mark.parametrize(
    "change",
    [
        {"start_ms": 0},
        {"channel": 1},
        {"available_time_ms": 5},
        {"confidence": 0.9},
        {"source_id": uuid4()},
        {"quality": "SUPPORTED"},
        {"recorded_at": datetime(2020, 1, 1, tzinfo=UTC)},
        {"supersedes_id": uuid4()},
        {"reason": "   "},
    ],
)
def test_correction_cannot_rewrite_observed_provenance(lifecycle, change):
    transactions, service, context, _, segment, _, _ = lifecycle
    accept(lifecycle)
    changed = correction(segment).model_copy(update=change)
    before = counts(transactions)
    with pytest.raises((ContractError, ValidationError)):
        with transactions.begin() as uow:
            service.correct(context, segment.id, changed, uow)
            uow.commit()
    assert counts(transactions) == before


@pytest.mark.parametrize("capabilities", [["read"], ["analysis", "read"], ["review", "read"]])
def test_correction_grants(lifecycle, capabilities):
    transactions, service, context, _, segment, _, _ = lifecycle
    accept(lifecycle)
    with transactions.begin() as uow:
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            service.correct(
                context.model_copy(update={"capabilities": capabilities}),
                segment.id,
                correction(segment),
                uow,
            )


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", uuid4()),
        ("analysis_run_id", uuid4()),
        ("revision", 2),
        ("input_hash", "f" * 64),
        ("lease_id", uuid4()),
        ("config_hash", "e" * 64),
    ],
)
def test_reject_stale_mismatched_candidate_before_write(lifecycle, field, value):
    transactions, service, context, raw, _, _, _ = lifecycle
    with pytest.raises(ContractError):
        with transactions.begin() as uow:
            service.store_raw(context, raw.model_copy(update={field: value}), uow)
            uow.commit()
    assert counts(transactions) == (0, 0, 0, 0, 0, 0, 0)


def test_cancelled_late_result_rejected_even_after_duplicate_commit(lifecycle):
    transactions, service, context, raw, _, _, authority = lifecycle
    accept(lifecycle)
    authority.cancelled = True
    with transactions.begin() as uow:
        with pytest.raises(ContractError, match="LEASE_EXPIRED"):
            service.store_raw(context, raw, uow)
    assert counts(transactions) == (1, 1, 0, 0, 1, 2, 2)


def test_parent_hash_closed_repository_duplicate_and_registration(lifecycle):
    transactions, service, context, raw, segment, evidence, authority = lifecycle
    registration = register_transcripts(transactions, evidence, authority)
    assert registration.contract_version == "1.0.0" and registration.readiness() is False
    assert registration.routes == () and registration.job_handlers == {}
    assert registration.migrations == TRANSCRIPT_MIGRATIONS
    assert registration.repositories.keys() == RECORDS.keys()
    ModuleRegistry(profile="test").register(registration)
    with pytest.raises(ValueError, match="MOCK"):
        ModuleRegistry(profile="production").register(registration)
    with transactions.begin() as uow:
        repository = uow.repository(RAW)
        uow.conn.execute("UPDATE platform_revisions SET input_hash=?", ("f" * 64,))
        with pytest.raises(ContractError, match="SOURCE_REVISION_CHANGED"):
            repository.append(context, raw)
    with pytest.raises(RuntimeError, match="closed"):
        repository.get(context, raw.id)
    accept(lifecycle)
    with transactions.begin() as uow:
        with pytest.raises(ContractError, match="VERSION_CONFLICT"):
            uow.repository(RAW).append(context, raw)
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            uow.repository(RAW).get(context.model_copy(update={"session_id": uuid4()}), raw.id)
        with pytest.raises(ContractError, match="SOURCE_REVISION_CHANGED"):
            uow.repository(RAW).get(context.model_copy(update={"input_hash": "f" * 64}), raw.id)
        invalid = segment.model_copy(update={"text": "invented"})
        with pytest.raises(ContractError, match="INVALID_AI_OUTPUT"):
            service.add_original(context, raw.id, invalid, uow)


def test_upgrade_preserves_b01_and_foreign_keys(tmp_path, lifecycle):
    _, _, context, raw, _, _, _ = lifecycle
    baseline = AnalysisReferenceTransactions(tmp_path / "upgrade.db")
    baseline.seed(context)
    upgraded = TranscriptReferenceTransactions(baseline.path)
    with upgraded.begin() as uow:
        assert [r[0] for r in uow.conn.execute("SELECT id FROM mock_migrations ORDER BY id")] == [
            "analysis.0001",
            "analysis.0002",
            "platform.0001",
        ]
        assert uow.conn.execute("SELECT count(*) FROM platform_runs").fetchone()[0] == 1
        uow.conn.execute("DELETE FROM platform_runs")
        with pytest.raises(sqlite3.IntegrityError):
            uow.repository(RAW).append(context, raw)
    with pytest.raises(ValueError, match="downgrade"):
        upgraded.migrate((PLATFORM_REFERENCE, *ANALYSIS_MIGRATIONS))


def test_correction_atomic_failure_and_purge(lifecycle, monkeypatch):
    transactions, service, context, raw, segment, evidence, _ = lifecycle
    accept(lifecycle)
    before = counts(transactions)
    changed = correction(segment)
    evidence.segments.append(changed)
    with pytest.raises(RuntimeError):
        with transactions.begin() as uow:
            monkeypatch.setattr(
                uow, "enqueue_event", lambda *args: (_ for _ in ()).throw(RuntimeError())
            )
            service.correct(context, segment.id, changed, uow)
            uow.commit()
    assert counts(transactions) == before
    with transactions.begin() as uow:
        service.purge(context, uow)
        uow.commit()
    assert counts(transactions)[:4] == (0, 0, 0, 0)
    # Platform evidence/audit retention is separate; old IDs no longer resolve via lifecycle.
    with transactions.begin() as uow:
        with pytest.raises(ContractError, match="EVIDENCE_UNAVAILABLE"):
            service.validate_evidence(context, segment.evidence[0], uow)
        with pytest.raises(ContractError, match="EVIDENCE_UNAVAILABLE"):
            uow.repository(RAW).get(context, raw.id)


def test_audio_link_and_current_transcript_revision(lifecycle):
    transactions, service, context, raw, segment, evidence, _ = lifecycle
    accept(lifecycle)
    corrected = correction(segment)
    evidence.segments.append(corrected)
    with transactions.begin() as uow:
        assert service.current_segments(context, uow) == (segment,)
        service.correct(context, segment.id, corrected, uow)
        assert service.current_segments(context, uow) == (corrected,)
        link = service.resolve_audio(context, corrected.id, uow)
        assert link.raw_id == raw.id and link.chunk_id == raw.chunk_id
        assert str(link.source_asset_id) == "00000000-0000-0000-0000-000000000006"
        assert (link.chunk_source_range.start_ns, link.chunk_source_range.end_ns) == (0, 3000000000)
        assert link.channel == 0 and link.uncertainty_ms == 5
        assert service.canonical_provider_words(context, uow)[0].text == "hold"
        audio = segment.evidence[0].model_copy(
            update={"kind": "AUDIO", "quote": None, "span_start": None, "span_end": None}
        )
        assert service.validate_evidence(context, audio, uow) == audio
        with pytest.raises(ContractError, match="ACCESS_DENIED"):
            service.resolve_audio(
                context.model_copy(update={"capabilities": ["read"]}), segment.id, uow
            )
        with pytest.raises(ContractError, match="EVIDENCE_UNAVAILABLE"):
            service.validate_evidence(
                context, audio.model_copy(update={"source_hash": "f" * 64}), uow
            )
