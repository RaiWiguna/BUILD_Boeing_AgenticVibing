"""A08.2 hand-derived timing and real source/clock/identity/evidence integration."""

import importlib
import json
from uuid import uuid4

import pytest
from flowlens.core.errors import ContractError
from test_geometry_kernel import layout, track
from test_import_commit import commit, context
from test_import_commit import committed as committed
from test_import_metadata import prepare, request
from test_imports import importer as importer
from test_imports import stage, upload


def module():
    return importlib.import_module("flowlens.geometry.occupancy")


def geometry():
    from flowlens.geometry.kernel import Geometry

    return Geometry(layout())


def test_linear_prediction_full_footprint_eta_exit_oracle():
    t = track(-130, time=1000).model_copy(update={"speed_mps": 10.0})
    forecast = module().predict(geometry(), t, 1000, module().Policy(), 0)
    assert forecast.eta_ms == 3000 and forecast.exit_ms == 25000
    assert [(r.start_ms, r.end_ms) for r in forecast.intervals] == [(3000, 25001)]
    assert not forecast.unknown and not forecast.exit_unknown


def test_margins_and_timing_uncertainty_expand_not_shrink_intervals():
    t = track(-130, time=1000).model_copy(update={"speed_mps": 10.0})
    policy = module().Policy(temporal_margin_ms=200)
    forecast = module().predict(geometry(), t, 1000, policy, 50)
    assert forecast.eta_ms == 3000 and forecast.exit_ms == 25000
    assert [(r.start_ms, r.end_ms) for r in forecast.intervals] == [(2750, 25251)]


def test_crossing_and_arrival_use_same_runway_resource_and_time_oracle():
    crossing = track(0, -30, 90, time=1000).model_copy(update={"speed_mps": 10.0})
    arrival = track(-150, 0, time=1000).model_copy(update={"speed_mps": 20.0})
    a, b = [
        module().predict(geometry(), t, 1000, module().Policy(), 0) for t in (crossing, arrival)
    ]
    assert [(r.start_ms, r.end_ms) for r in a.intervals] == [(2000, 6001)]
    assert [(r.start_ms, r.end_ms) for r in b.intervals] == [(3000, 14001)]
    assert module().overlap(a.intervals, b.intervals) == 3001
    from flowlens.contracts.models import TimeRange

    assert (
        module().overlap(
            [TimeRange(start_ms=100, end_ms=300)], [TimeRange(start_ms=200, end_ms=400)]
        )
        == 100
    )


def test_observed_interpolation_has_independent_entry_exit_times():
    a, b = track(-130, time=1000), track(130, time=3000)
    intervals = module().interpolate(geometry(), a, b, 0)
    # 20/260 and240/260 of2000ms; lower bound floor, closed contact -> exclusive ceil+1.
    assert [(r.start_ms, r.end_ms) for r in intervals] == [(1153, 2848)]


@pytest.mark.parametrize("x,occupied", [(0, True), (130, False)])
def test_zero_speed_preserves_unknown_motion_and_exit(x, occupied):
    forecast = module().predict(geometry(), track(x, time=1000), 1000, module().Policy(), 0)
    assert forecast.unknown and forecast.eta_ms is None and forecast.exit_ms is None
    assert forecast.exit_unknown is occupied
    if occupied:
        assert [(r.start_ms, r.end_ms) for r in forecast.intervals] == [(1000, 31001)]
    else:
        assert forecast.intervals == []


def test_away_direction_horizon_and_layout_limit_are_explicit():
    t = track(-150, heading=180, time=1000).model_copy(update={"speed_mps": 10.0})
    assert module().predict(geometry(), t, 1000, module().Policy(), 0).intervals == []
    t = track(-1000, time=1000).model_copy(update={"speed_mps": 1.0})
    assert module().predict(geometry(), t, 1000, module().Policy(), 0).eta_ms is None
    t = track(0, time=99999).model_copy(update={"speed_mps": 1.0})
    f = module().predict(geometry(), t, 99999, module().Policy(), 0)
    assert f.exit_unknown and f.intervals[-1].end_ms <= 100000


@pytest.mark.parametrize(
    "kwargs",
    [
        {"horizon_ms": 0},
        {"horizon_ms": True},
        {"temporal_margin_ms": -1},
        {"stale_ms": 0},
        {"protection_margin_m": float("nan")},
        {"speed_floor_mps": 0.0},
        {"max_speed_mps": 0.0},
    ],
)
def test_invalid_policy_rejected(kwargs):
    with pytest.raises(ValueError):
        module().Policy(**kwargs)


def source_fixture(importer, committed, *, rows=None, modify=None):
    originals = rows if rows is not None else [track(0, time=1000)]
    raw = [
        r.model_copy(
            update={"id": uuid4(), "source_event_id": f"t{i}", "available_time_ms": r.event_time_ms}
        ).model_dump(mode="json")
        for i, r in enumerate(originals)
    ]
    preview = stage(
        importer,
        [
            upload(),
            upload(
                json.dumps(raw).encode(),
                role="tracks",
                filename="tracks.json",
                media_type="application/json",
            ),
        ],
    )

    def declaration(d):
        for f in d["files"]:
            f["clock"] = {
                "timezone": "UTC",
                "method": "DECLARED_OFFSET",
                "offset_ms": 0,
                "uncertainty_ms": 0,
                "basis": "synthetic timing oracle",
                "reviewer": "fixture",
            }
        d["layout"] = layout().model_dump(mode="json")
        d["coverage"] = {
            "vehicles": True,
            "speaker_identity": None,
            "gaps": [],
            "basis": "synthetic observed track coverage",
        }
        d["identities"] = [
            {
                "source_entity_id": raw[0]["entity_id"],
                "callsign": "fixture123",
                "aliases": [],
                "validity": {"start_ms": 0, "end_ms": 100000},
                "evidence_file_id": str(preview.files[1].id),
                "evidence_record_ids": ["t0"],
            }
        ]
        if modify:
            modify(d)

    prepared = prepare(importer, preview, request(preview, modify=declaration))
    receipt = commit(committed, preview, prepared)
    c = context(committed, receipt)
    tracks = committed[1].tracks(c, prepared.identities[0].entity_id) if prepared.identities else []
    return receipt, prepared, tracks


def at(committed, receipt, time, mode="DEBRIEF", run=None):
    with committed[0].imports.database.begin() as uow:
        uow.connection.execute(
            "UPDATE platform_context_state SET as_of_ms=?,mode=? WHERE session_id=?",
            (time, mode, str(receipt.session_id)),
        )
        uow.commit()
    return committed[2].human_context(
        committed[3].token.get_secret_value(), receipt.session_id, run_id=run
    )


def reader(committed, tmp_path):
    from flowlens.assets.access import Assets
    from flowlens.assets.storage import PrivateFiles
    from flowlens.evidence.registry import EvidenceRegistry

    files = PrivateFiles(tmp_path / "derivatives")
    evidence = EvidenceRegistry(committed[1], Assets(committed[1], files))
    return module().Occupancy(committed[1], evidence), files, evidence


def test_real_geometry_reader_port_resolvable_indexed_evidence_and_atomicity(
    importer, committed, tmp_path
):
    receipt, prepared, tracks = source_fixture(importer, committed)
    service, files, evidence = reader(committed, tmp_path)
    try:
        c = at(committed, receipt, 1000, "AS_KNOWN")
        # Read-only canonical source anchors; arbitrary registration remains privileged.
        committed[2].revoke(
            committed[3].token.get_secret_value(), c.actor_id, c.session_id, "analysis"
        )
        c = at(committed, receipt, 1000, "AS_KNOWN")
        result = service.observations(c, prepared.identities[0].entity_id)
        assert result.status == "EVALUATED" and result.occupied is True
        assert result.evidence and evidence.get(c, result.evidence[0].id) == result.evidence[0]
        assert evidence.resolve(c, result.evidence[0]) == result.evidence[0]
        assert result == service.observations(c, prepared.identities[0].entity_id)
        with importer[0].database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 1
            )
        report = service.report(c, prepared.identities[0].entity_id)
        assert (
            report.prediction_unknown and report.exit_ms is None and report.last_observed_occupied
        )
        assert report.observed_at_ms == 1000 and report.result == result
    finally:
        files.close()


@pytest.mark.parametrize(
    "cause,reason",
    [
        ("clock", "CLOCK_UNKNOWN"),
        ("layout", "LAYOUT_MISSING"),
        ("identity", "IDENTITY_UNKNOWN"),
        ("expired_identity", "IDENTITY_EXPIRED"),
        ("coverage", "COVERAGE_GAP"),
        ("stale", "STALE_TRACK"),
        ("dropout", "TRACK_GAP"),
        ("layout_expired", "LAYOUT_EXPIRED"),
        ("quality", "TRACK_AMBIGUOUS"),
    ],
)
def test_ineligible_source_keeps_unknown_occupancy(importer, committed, tmp_path, cause, reason):
    rows = [track(0, time=1000)]
    if cause == "dropout":
        rows = [track(0, time=100), track(0, time=6000)]
    if cause == "quality":
        rows = [track(0, time=1000).model_copy(update={"quality": "AMBIGUOUS"})]

    def modify(d):
        if cause == "clock":
            for f in d["files"]:
                f["clock"] = {"timezone": "UTC", "method": "UNKNOWN"}
        elif cause == "layout":
            d["layout"] = None
        elif cause == "identity":
            d["identities"] = []
        elif cause == "expired_identity":
            d["identities"][0]["validity"]["end_ms"] = 1001
        elif cause == "coverage":
            d["coverage"]["gaps"] = [{"start_ms": 1001, "end_ms": 1500}]
        elif cause == "layout_expired":
            d["layout"]["validity"]["end_ms"] = 1001

    receipt, prepared, tracks = source_fixture(importer, committed, rows=rows, modify=modify)
    service, files, _ = reader(committed, tmp_path)
    try:
        time = (
            6000
            if cause == "dropout"
            else 7000
            if cause == "stale"
            else 1500
            if cause in ("coverage", "expired_identity", "layout_expired")
            else 1000
        )
        c = at(committed, receipt, time)
        entity = prepared.identities[0].entity_id if prepared.identities else uuid4()
        report = service.report(c, entity)
        assert report.result.status == "NOT_EVALUABLE" and report.result.occupied is None
        assert report.result.reason == reason and report.prediction_unknown
        if cause in ("stale", "dropout", "coverage"):
            assert report.last_observed_occupied is True
    finally:
        files.close()


def test_as_known_no_future_track_and_live_access_loss(importer, committed, tmp_path):
    receipt, prepared, tracks = source_fixture(
        importer, committed, rows=[track(0, time=1000), track(130, time=3000)]
    )
    service, files, _ = reader(committed, tmp_path)
    try:
        c = at(committed, receipt, 1000, "AS_KNOWN")
        result = service.observations(c, prepared.identities[0].entity_id)
        assert result.occupied is True and len(result.evidence) == 1
        c = at(committed, receipt, 3000, "AS_KNOWN")
        assert service.observations(c, prepared.identities[0].entity_id).occupied is False
        committed[2].revoke(committed[3].token.get_secret_value(), c.actor_id, c.session_id, "read")
        with pytest.raises(ContractError):
            service.observations(c, prepared.identities[0].entity_id)
    finally:
        files.close()


def test_concave_resource_has_multiple_disjoint_time_intervals():
    from flowlens.geometry.kernel import Geometry

    data = layout().model_dump(mode="json")
    data["runway_polygon"] = [
        [-100, -20],
        [-40, -20],
        [-40, 10],
        [40, 10],
        [40, -20],
        [100, -20],
        [100, 20],
        [-100, 20],
    ]
    from flowlens.sources.metadata import Layout

    g = Geometry(Layout.model_validate_json(json.dumps(data)))
    t = track(-130, -10, time=1000).model_copy(update={"speed_mps": 10.0})
    f = module().predict(g, t, 1000, module().Policy(), 0)
    assert [(r.start_ms, r.end_ms) for r in f.intervals] == [(3000, 11001), (17000, 25001)]


def test_observed_stays_causal_and_prediction_respects_identity_expiry(
    importer, committed, tmp_path
):
    def modify(d):
        d["identities"][0]["validity"]["end_ms"] = 3500

    receipt, prepared, _ = source_fixture(
        importer,
        committed,
        rows=[
            track(-130, time=1000).model_copy(update={"speed_mps": 10.0}),
            track(-120, time=2000).model_copy(update={"speed_mps": 10.0}),
        ],
        modify=modify,
    )
    service, files, _ = reader(committed, tmp_path)
    try:
        c = at(committed, receipt, 2000, "AS_KNOWN")
        report = service.report(c, prepared.identities[0].entity_id)
        assert all(r.end_ms <= 2001 for r in report.observed)
        assert report.predicted and all(r.end_ms <= 3500 for r in report.predicted)
        assert report.exit_unknown
    finally:
        files.close()


def test_future_coverage_gap_preserves_prediction_unknown(importer, committed, tmp_path):
    def modify(d):
        d["coverage"]["gaps"] = [{"start_ms": 3000, "end_ms": 4000}]

    receipt, prepared, _ = source_fixture(
        importer,
        committed,
        rows=[track(-130, time=1000).model_copy(update={"speed_mps": 10.0})],
        modify=modify,
    )
    service, files, _ = reader(committed, tmp_path)
    try:
        report = service.report(at(committed, receipt, 1000), prepared.identities[0].entity_id)
        assert report.prediction_unknown
    finally:
        files.close()


def test_evidence_cache_rolls_back_whole_geometry_read(importer, committed, tmp_path, monkeypatch):
    receipt, prepared, _ = source_fixture(
        importer, committed, rows=[track(0, time=1000), track(5, time=2000)]
    )
    service, files, evidence = reader(committed, tmp_path)
    original = evidence.index_track
    count = 0

    def failed(ctx, t, uow):
        nonlocal count
        count += 1
        result = original(ctx, t, uow)
        if count == 2:
            raise RuntimeError("synthetic cache failure")
        return result

    monkeypatch.setattr(evidence, "index_track", failed)
    try:
        with pytest.raises(RuntimeError):
            service.observations(at(committed, receipt, 2000), prepared.identities[0].entity_id)
        with importer[0].database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 0
            )
    finally:
        files.close()


def test_authority_recheck_after_math_prevents_publication(
    importer, committed, tmp_path, monkeypatch
):
    receipt, prepared, _ = source_fixture(importer, committed)
    service, files, _ = reader(committed, tmp_path)
    original = module().predict

    def revoked(*args, **kwargs):
        forecast = original(*args, **kwargs)
        c = at(committed, receipt, 1000)
        committed[2].revoke(committed[3].token.get_secret_value(), c.actor_id, c.session_id, "read")
        return forecast

    monkeypatch.setattr(module(), "predict", revoked)
    try:
        with pytest.raises(ContractError):
            service.observations(at(committed, receipt, 1000), prepared.identities[0].entity_id)
        with importer[0].database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 0
            )
    finally:
        files.close()


def test_shared_resource_never_treats_missing_or_stopped_as_safe(importer, committed, tmp_path):
    from dataclasses import replace

    receipt, prepared, _ = source_fixture(importer, committed)
    service, files, _ = reader(committed, tmp_path)
    try:
        a = service.report(at(committed, receipt, 1000), prepared.identities[0].entity_id)
        b = replace(a, result=a.result.model_copy(update={"entity_id": uuid4()}))
        assert module().shared_resource(a, b) == "OBSERVED_MODEL_OVERLAP"
        b = replace(b, observed=[], predicted=[], prediction_unknown=True)
        assert module().shared_resource(a, b) == "UNKNOWN"
        with pytest.raises(ContractError):
            module().shared_resource(a, replace(b, resource="PROTECTION"))
    finally:
        files.close()


def test_geometry_http_uses_server_cursor_and_live_permissions(importer, committed, tmp_path):
    from fastapi.testclient import TestClient
    from flowlens.api.host import create_host
    from flowlens.core.host_config import HostSettings
    from flowlens.replay.controls import Controls
    from flowlens.replay.snapshots import Replay

    receipt, prepared, _ = source_fixture(importer, committed)
    service, files, _ = reader(committed, tmp_path)
    app = create_host(HostSettings(profile="test"))
    app.state.permissions = committed[2]
    app.state.sessions = committed[2].sessions
    app.state.transactions = importer[0].database
    app.state.geometry = service
    app.state.controls = Controls(Replay(committed[1]))
    token = committed[3].token.get_secret_value()
    app.state.controls.command(
        token,
        receipt.session_id,
        "SEEK",
        view="LOCAL",
        value=1000,
        key="geometry-cursor",
        expected_version=0,
    )
    url = (
        f"/api/v1/sessions/{receipt.session_id}/entities/"
        f"{prepared.identities[0].entity_id}/geometry?view=LOCAL&mode=AS_KNOWN"
    )
    try:
        with TestClient(app, base_url="http://127.0.0.1:8000") as client:
            assert client.get(url).status_code == 401
            client.cookies.set("flowlens_session", token)
            response = client.get(url)
            assert response.status_code == 200 and response.json()["result"]["occupied"] is True
            assert response.json()["observed_at_ms"] == 1000
            assert str(files.root) not in response.text
            assert client.get(url + "&resource=private").status_code == 422
            assert response.headers["Cache-Control"] == "no-store"
            committed[2].revoke(token, committed[3].account.id, receipt.session_id, "read")
            assert client.get(url).status_code == 403
    finally:
        files.close()


def test_same_time_motion_conflict_is_not_arbitrarily_selected(importer, committed, tmp_path):
    a = track(0, time=1000)
    receipt, prepared, _ = source_fixture(
        importer, committed, rows=[a, a.model_copy(update={"speed_mps": 10.0})]
    )
    service, files, _ = reader(committed, tmp_path)
    try:
        result = service.observations(
            at(committed, receipt, 1000), prepared.identities[0].entity_id
        )
        assert result.status == "NOT_EVALUABLE" and result.reason == "TRACK_CONFLICTING"
    finally:
        files.close()
