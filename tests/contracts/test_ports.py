import importlib
from uuid import UUID

import pytest


def test_both_tracks_have_required_ports_and_registration_hooks():
    ports = importlib.import_module("flowlens.contracts.ports")
    harness = importlib.import_module("flowlens.testing.harness")
    for name in [
        "SourceReader",
        "GeometryReader",
        "AssetAccess",
        "JobClient",
        "EvidenceService",
        "UnitOfWork",
        "TransactionFactory",
        "AnalysisModule",
        "ArtifactLifecycle",
        "ProviderAdapter",
        "ContextReader",
    ]:
        assert getattr(ports, name)
    for track in ("A", "B"):
        bundle = harness.build_harness(track)
        assert bundle.profile == "MOCK"
        assert bundle.platform is not None
        assert bundle.analysis is not None
        assert bundle.registry.modules
        registration = bundle.registry.modules[0]
        assert registration.migrations
        assert registration.job_handlers
        assert registration.repositories
        assert registration.services
        assert registration.snapshot_reader is not None
        assert registration.purge_handler is not None
        assert registration.readiness is not None


def test_evidence_resolution_checks_scope_hash_range_and_quote():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    m = importlib.import_module("flowlens.contracts.models")
    h = importlib.import_module("flowlens.testing.harness")
    ctx = m.RequestContext.model_validate_json(
        (root / "contracts/examples/context.json").read_text()
    )
    segment = m.TranscriptSegment.model_validate_json(
        (root / "contracts/examples/transcript.json").read_text()
    )
    service = h.FakePlatform([], [segment])
    evidence = segment.evidence[0]
    assert service.resolve(ctx, evidence) == evidence
    error = importlib.import_module("flowlens.core.errors").ContractError
    for update in [
        {"source_hash": "f" * 64},
        {"end_ms": segment.end_ms + 1},
        {"quote": "invented quote"},
        {"session_id": UUID("00000000-0000-0000-0000-000000000099")},
        {"span_start": 1, "span_end": 3},
    ]:
        with pytest.raises(error):
            service.resolve(ctx, evidence.model_copy(update=update))


def test_migrations_missing_dependency_and_cycle_rejected():
    m = importlib.import_module("flowlens.core.modules")
    with pytest.raises(ValueError):
        m.order_migrations([m.MigrationSpec("analysis.1", "B", ("platform.1",), "SELECT 1;")])
    with pytest.raises(ValueError):
        m.order_migrations(
            [
                m.MigrationSpec("a", "A", ("b",), "SELECT 1;"),
                m.MigrationSpec("b", "B", ("a",), "SELECT 1;"),
            ]
        )


def test_fake_asset_is_scoped_and_limited():
    from pathlib import Path

    m = importlib.import_module("flowlens.contracts.models")
    h = importlib.import_module("flowlens.testing.harness")
    root = Path(__file__).resolve().parents[2]
    ctx = m.RequestContext.model_validate_json(
        (root / "contracts/examples/context.json").read_text()
    )
    asset_id = UUID(int=16)
    service = h.FakeAssets(ctx.session_id, {asset_id: b"abcdef"})
    assert service.download(ctx, asset_id, 1, 4) == b"bcd"
    error = importlib.import_module("flowlens.core.errors").ContractError
    for asset, start, end in ((UUID(int=99), 0, 1), (asset_id, -1, 2), (asset_id, 0, 7)):
        with pytest.raises(error):
            service.download(ctx, asset, start, end)


def test_unit_of_work_rolls_back_and_publishes_after_commit(tmp_path):
    from pathlib import Path

    m = importlib.import_module("flowlens.contracts.models")
    h = importlib.import_module("flowlens.testing.harness")
    root = Path(__file__).resolve().parents[2]
    ctx = m.RequestContext.model_validate_json(
        (root / "contracts/examples/context.json").read_text()
    )
    record = m.Intent.model_validate_json((root / "contracts/examples/intent.json").read_text())
    factory = h.SQLiteTransactionFactory(tmp_path / "uow.db")
    callbacks = []
    with pytest.raises(RuntimeError):
        with factory.begin() as uow:
            uow.repository("analysis").append(ctx, record)
            uow.enqueue_event(ctx, record)
            uow.audit(ctx, "APPEND", record.id)
            uow.after_commit(lambda: callbacks.append("rolled-back"))
            raise RuntimeError("rollback")
    assert callbacks == []
    with factory.begin() as uow:
        with pytest.raises(KeyError):
            uow.repository("analysis").get(ctx, record.id)
        uow.repository("analysis").append(ctx, record)
        uow.enqueue_event(ctx, record)
        uow.audit(ctx, "APPEND", record.id)
        uow.after_commit(lambda: callbacks.append("committed"))
        assert callbacks == []
        uow.commit()
    assert callbacks == ["committed"]
    with factory.begin() as uow:
        assert uow.repository("analysis").get(ctx, record.id) == record
        error = importlib.import_module("flowlens.core.errors").ContractError
        with pytest.raises(error):
            uow.repository("analysis").get(
                ctx.model_copy(update={"session_id": UUID(int=99)}), record.id
            )


def test_b_harness_supplies_all_frozen_platform_interfaces(tmp_path):
    h = importlib.import_module("flowlens.testing.harness")
    bundle = h.build_harness("B", db_path=tmp_path / "harness.db")
    for name in ("assets", "jobs", "evidence", "transactions", "artifacts", "geometry", "context"):
        assert getattr(bundle, name) is not None
    assert bundle.jobs.lease(UUID(int=50), "STT") is None


def test_evidence_registration_and_analysis_validation(tmp_path):
    from pathlib import Path

    m = importlib.import_module("flowlens.contracts.models")
    h = importlib.import_module("flowlens.testing.harness")
    root = Path(__file__).resolve().parents[2]
    ctx = m.RequestContext.model_validate_json(
        (root / "contracts/examples/context.json").read_text()
    )
    segment = m.TranscriptSegment.model_validate_json(
        (root / "contracts/examples/transcript.json").read_text()
    )
    result = m.JobResult.model_validate_json(
        (root / "contracts/examples/job_result.json").read_text()
    )
    service = h.FakePlatform([], [segment])
    validated = h.FakeAnalysis().validate(ctx, result, service)
    factory = h.SQLiteTransactionFactory(tmp_path / "evidence.db")
    with factory.begin() as uow:
        assert service.register(ctx, validated.evidence[0], uow) == validated.evidence[0].id
        uow.commit()
    wrong = result.model_copy(update={"input_hash": "f" * 64})
    with pytest.raises(importlib.import_module("flowlens.core.errors").ContractError):
        h.FakeAnalysis().validate(ctx, wrong, service)
