"""A08.1 independent hand-derived Cartesian footprint/hold/sweep oracles."""

import importlib
import json
import math
from pathlib import Path
from uuid import uuid4

import pytest
from flowlens.contracts.models import Track
from flowlens.core.errors import ContractError
from flowlens.sources.metadata import Layout


def kernel():
    return importlib.import_module("flowlens.geometry.kernel")


def layout(*, units="m", uncertainty=0.0):
    fixture = json.loads(Path("tests/fixtures/layouts/fictional-runway.json").read_text())
    return Layout.model_validate_json(
        json.dumps(
            {
                "version": fixture["version"],
                "coordinate_system": "LOCAL_CARTESIAN",
                "units": units,
                "validity": {"start_ms": 0, "end_ms": 100000},
                "uncertainty": uncertainty,
                "runway_polygon": fixture["runway_polygon"],
                "hold_lines": [{"id": "H1", "points": fixture["hold_line"]}],
            }
        )
    )


def track(x=0.0, y=0.0, heading=0.0, length=20.0, width=4.0, time=100):
    t = Track.model_validate_json(Path("contracts/examples/track.json").read_text())
    return Track.model_validate_json(
        t.model_copy(
            update={
                "x_m": float(x),
                "y_m": float(y),
                "heading_deg": float(heading),
                "length_m": float(length),
                "width_m": float(width),
                "event_time_ms": time,
                "available_time_ms": time + 10,
            }
        ).model_dump_json()
    )


@pytest.mark.parametrize(
    "heading,bounds",
    [(0, (-5, 5, 15, 9)), (90, (3, -3, 7, 17)), (180, (-5, 5, 15, 9)), (270, (3, -3, 7, 17))],
)
def test_cardinal_footprint_oracle(heading, bounds):
    t = track(5, 7, heading)
    before = t.model_dump_json()
    shape = kernel().footprint(t)
    assert shape.bounds == pytest.approx(bounds, abs=1e-10)
    assert shape.area == pytest.approx(80)
    assert t.model_dump_json() == before


def test_rotated_corners_independent_hand_oracle():
    t = track(0, 0, 45, length=4 * math.sqrt(2), width=2 * math.sqrt(2))
    shape = kernel().footprint(t)
    actual = {(round(x, 10), round(y, 10)) for x, y in list(shape.exterior.coords)[:-1]}
    assert actual == {(1.0, 3.0), (3.0, 1.0), (-1.0, -3.0), (-3.0, -1.0)}
    assert shape.bounds == pytest.approx((-3, -3, 3, 3))
    assert shape.area == pytest.approx(16)


def test_existing_evaluator_oracles_are_used_only_in_tests():
    cases = json.loads(Path("evaluation/fixtures/oracles/baseline.json").read_text())["cases"]
    geometry = kernel().Geometry(layout())
    for case in cases[:3]:
        t = track(*case["center_xy"], length=case["size_xy"][0], width=case["size_xy"][1])
        assert geometry.occupied(t) is case["expected_occupied"]


@pytest.mark.parametrize(
    "x,occupied",
    [(109.999, True), (110.0, True), (110.001, False), (-110.0, True), (-110.001, False)],
)
def test_full_footprint_boundary_touch_is_occupied(x, occupied):
    assert kernel().Geometry(layout()).occupied(track(x)) is occupied


def test_protection_margin_layout_uncertainty_and_feet_conversion():
    geometry = kernel().Geometry(layout(uncertainty=2), protection_margin_m=5)
    assert geometry.runway.bounds == (-100.0, -10.0, 100.0, 10.0)
    assert geometry.protection.bounds == (-107.0, -17.0, 107.0, 17.0)
    assert not geometry.occupied(track(116))
    assert geometry.occupied(track(117), resource="PROTECTION")
    assert not geometry.occupied(track(117.001), resource="PROTECTION")
    ft = kernel().Geometry(layout(units="ft"), protection_margin_m=0)
    assert ft.runway.bounds == pytest.approx((-30.48, -3.048, 30.48, 3.048))
    assert ft.occupied(track(31, 0, length=2, width=1))
    assert not ft.occupied(track(31.481, 0, length=2, width=1))


@pytest.mark.parametrize(
    "x,relation", [(-41, "BEHIND"), (-40, "TOUCHING"), (-30, "STRADDLING"), (-19, "BEYOND")]
)
def test_hold_line_half_plane_and_full_footprint(x, relation):
    geometry = kernel().Geometry(layout())
    assert geometry.hold_relation(track(x), "H1", allowed_point=(-50.0, 0.0)) == relation
    assert (
        geometry.hold_relation(track(x, 100), "H1", allowed_point=(-50.0, 0.0)) == "OUTSIDE_SEGMENT"
    )
    with pytest.raises(ContractError):
        geometry.hold_relation(track(x), "missing", allowed_point=(-50.0, 0.0))
    with pytest.raises(ContractError):
        geometry.hold_relation(track(x), "H1", allowed_point=(-30.0, 0.0))


def test_exact_straight_sweep_detects_tunneling_with_both_endpoints_outside():
    geometry = kernel().Geometry(layout())
    a, b = track(-120), track(120, time=200)
    assert not geometry.occupied(a) and not geometry.occupied(b)
    sweep = geometry.sweep(a, b)
    assert sweep.exact and sweep.motion_model == "LINEAR_FIXED_HEADING"
    assert sweep.shape.bounds == pytest.approx((-130, -2, 130, 2))
    assert sweep.shape.area == pytest.approx(1040)
    assert geometry.swept_occupied(a, b)
    assert geometry.crosses_hold(a, b, "H1", allowed_point=(-50.0, 0.0))


def test_rotation_envelope_contains_independent_extreme_corner():
    from shapely.geometry import Point

    geometry = kernel().Geometry(layout())
    a, b = track(102.1, length=4, width=2), track(102.1, heading=90, length=4, width=2, time=200)
    assert not geometry.occupied(a) and not geometry.occupied(b)
    sweep = geometry.sweep(a, b)
    # A 4x2 rectangle's half-diagonal is sqrt(5), achieved at atan(1/2).
    assert sweep.shape.covers(Point(102.1 - math.sqrt(5), 0))
    assert not sweep.exact and sweep.motion_model == "LINEAR_ROTATION_BOUND"
    assert geometry.swept_occupied(a, b)


def test_stopped_pose_sweep_and_line_contact_not_movement():
    geometry = kernel().Geometry(layout())
    a, b = track(-40), track(-40, time=200)
    assert geometry.sweep(a, b).shape.equals(kernel().footprint(a))
    assert not geometry.crosses_hold(a, b, "H1", allowed_point=(-50.0, 0.0))


@pytest.mark.parametrize(
    "change",
    [
        {"entity_id": None},
        {"entity_id": uuid4()},
        {"session_id": uuid4()},
        {"analysis_run_id": uuid4()},
        {"revision": 2},
        {"source_id": uuid4()},
        {"source_hash": "0" * 64},
        {"layout_version": "other"},
        {"event_time_ms": 100},
        {"length_m": 21.0},
    ],
)
def test_sweep_refuses_unknown_scope_time_layout_or_changing_dimensions(change):
    a, b = track(), track(10, time=200).model_copy(update=change)
    with pytest.raises(ContractError):
        kernel().Geometry(layout()).sweep(a, b)


@pytest.mark.parametrize(
    "change",
    [
        {"x_m": float("nan")},
        {"length_m": 0.0},
        {"heading_deg": 360.0},
        {"width_m": float("inf")},
        {"x_m": 1e100},
    ],
)
def test_copied_invalid_or_unbounded_track_denied(change):
    with pytest.raises(ContractError):
        kernel().footprint(track().model_copy(update=change))


def test_invalid_layout_resource_expired_period_and_margin_fail_closed():
    with pytest.raises(ContractError):
        kernel().Geometry(layout().model_copy(update={"coordinate_system": "WGS84"}))
    with pytest.raises(ContractError):
        kernel().Geometry(layout(), protection_margin_m=float("inf"))
    with pytest.raises(ContractError):
        kernel().Geometry(layout()).occupied(track(time=100000))
    with pytest.raises(ContractError):
        kernel().Geometry(layout()).occupied(track(), resource="UNKNOWN")
    with pytest.raises(ContractError):
        kernel().Geometry(layout()).occupied(track().model_copy(update={"layout_version": "bad"}))


def test_finite_hold_segment_clips_lateral_footprint_before_half_plane():
    data = layout().model_dump(mode="json")
    data["hold_lines"] = [{"id": "SHORT", "points": [[0.0, 0.0], [1.0, 0.0]]}]
    g = kernel().Geometry(Layout.model_validate_json(json.dumps(data)))
    # Diagonal rectangle crosses the infinite y=0 line at x<0. Its part in x∈[0,1]
    # lies entirely above the finite hold segment, so it remains BEHIND, not straddling.
    assert (
        g.hold_relation(track(-1, 1, 45, length=4, width=0.1), "SHORT", allowed_point=(0.0, 1.0))
        == "BEHIND"
    )


def test_collapsed_numeric_footprint_and_subresolution_hold_line_are_not_evaluable():
    with pytest.raises(ContractError):
        kernel().footprint(track(1e7, 1e7, length=1e-12, width=1e-12))
    data = layout().model_dump(mode="json")
    data["hold_lines"] = [{"id": "TINY", "points": [[0.0, 0.0], [1e-12, 0.0]]}]
    with pytest.raises(ContractError):
        kernel().Geometry(Layout.model_validate_json(json.dumps(data)))
    with pytest.raises(ContractError):
        kernel().Geometry(layout()).hold_relation(track(), "H1", allowed_point=(0.0, 0.0, 0.0))
