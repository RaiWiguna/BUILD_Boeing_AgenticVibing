"""S01–S10 independent lab scenario expectations, never imported by application."""

import importlib
import json
from pathlib import Path
from uuid import uuid4, uuid5

import pytest
from flowlens.contracts.models import Evidence, RequestContext, SourceEvent
from flowlens.core.errors import ContractError
from test_geometry_kernel import layout, track


def rules():
    return importlib.import_module("flowlens.geometry.rules")


def ctx(time=2000, mode="AS_KNOWN"):
    value = RequestContext.model_validate_json(Path("contracts/examples/context.json").read_text())
    t = track()
    return value.model_copy(
        update={
            "session_id": t.session_id,
            "input_revision": t.revision,
            "analysis_run_id": None,
            "as_of_ms": time,
            "mode": mode,
        }
    )


def pose(x=0, y=0, heading=0, time=1000, speed=0, entity=None):
    t = track(x, y, heading, time=time)
    return t.model_copy(
        update={
            "id": uuid4(),
            "entity_id": entity or t.entity_id,
            "available_time_ms": time,
            "speed_mps": float(speed),
        }
    )


def event(
    action, time=1000, *, entity=None, related=None, available=None, kind="INSTRUCTION", **fields
):
    t = pose(entity=entity)
    body = {"profile_version": "lab-source-1", "type": "INSTRUCTION", "action": action}
    if related:
        body["related_source_event_id"] = related
    body.update(fields)
    return SourceEvent(
        **t.model_dump(
            exclude={
                "x_m",
                "y_m",
                "heading_deg",
                "speed_mps",
                "length_m",
                "width_m",
                "age_ms",
                "layout_version",
                "kind",
                "statement",
                "event_time_ms",
                "available_time_ms",
                "source_event_id",
            }
        ),
        kind=kind,
        statement=json.dumps(body),
        event_time_ms=time,
        available_time_ms=time if available is None else available,
        source_event_id=str(uuid4()),
    )


def coverage(time=0):
    return event(
        None,
        time,
        kind="QUALITY",
        type="INSTRUCTION_COVERAGE",
        start_ms=0,
        end_ms=100000,
    )


def run(tracks, events=(), time=2000, mode="AS_KNOWN", profile=None):
    from flowlens.geometry.kernel import Geometry

    c = ctx(time, mode)
    anchors = {
        x.id: Evidence(
            id=uuid5(x.id, "test-anchor"),
            session_id=c.session_id,
            analysis_run_id=c.analysis_run_id,
            revision=c.input_revision,
            kind="TRACK" if x.kind == "TRACK" else "EVENT",
            source_id=x.source_id,
            segment_id=x.id,
            start_ms=x.event_time_ms,
            end_ms=x.event_time_ms + 1,
            source_hash=x.source_hash,
            quote=None,
            span_start=None,
            span_end=None,
        )
        for x in [*tracks, *events]
    }
    return rules().evaluate(
        c,
        Geometry(layout(), protection_margin_m=5),
        list(tracks),
        list(events),
        anchors,
        profile=profile or rules().RuleProfile(),
    )


def signal(signals, code):
    return next(x for x in signals if x.rule_id == code)


def test_s01_crossing_clear_before_arrival_no_modeled_overlap():
    crossing = pose(0, -30, 90, speed=10)
    # crossing [2000,6001]; arrival start10000, disjoint central model intervals.
    arrival = pose(-290, 0, speed=20, entity=uuid4())
    s = signal(run([crossing, arrival], time=1000), "RUNWAY_SHARED_RESOURCE")
    assert s.status == "INACTIVE" and s.reason == "NO_MODELED_OVERLAP"


def test_s02_interval_overlap_attention_and_no_clearance_claim():
    crossing = pose(0, -30, 90, speed=10)
    arrival = pose(-150, 0, speed=20, entity=uuid4())
    s = signal(run([crossing, arrival], time=1000), "RUNWAY_SHARED_RESOURCE")
    assert s.status == "ACTIVE" and s.priority == "ATTENTION" and s.overlap_ms == 3001
    assert s.reason == "PREDICTED_MODEL_OVERLAP" and s.evidence


def test_s03_stopped_vehicle_in_protection_keeps_unknown_exit():
    s = signal(run([pose(112)], time=1000), "STOPPED_IN_PROTECTION")
    assert s.status == "ACTIVE" and s.exit_unknown and s.priority == "ATTENTION"


def test_s04_on_hold_line_without_movement_is_not_violation():
    a, b = pose(-40, time=1000), pose(-40, time=2000)
    issued = event("HOLD_SHORT", line_id="H1")
    s = signal(run([a, b], [issued]), "HOLD_SHORT_MOVEMENT")
    assert s.status == "INACTIVE" and s.reason == "NO_OBSERVED_CROSSING"


def test_s05_crossing_without_observed_instruction_requires_coverage():
    a, b = pose(-50, time=1000), pose(-10, time=2000)
    s = signal(run([a, b], [coverage()]), "MOVEMENT_WITHOUT_OBSERVED_CLEARANCE")
    assert s.status == "ACTIVE" and s.priority == "NOTICE"
    assert "observed" in s.statement.lower()
    s = signal(run([a, b]), "MOVEMENT_WITHOUT_OBSERVED_CLEARANCE")
    assert s.status == "UNKNOWN" and s.reason == "INSTRUCTION_COVERAGE_UNKNOWN"


def test_s06_hold_short_instruction_crossed_full_footprint():
    a, b = pose(-50, time=1000), pose(-10, time=2000)
    issued = event("HOLD_SHORT", line_id="H1")
    s = signal(run([a, b], [issued]), "HOLD_SHORT_MOVEMENT")
    assert s.status == "ACTIVE" and s.priority == "ATTENTION"
    assert len(s.evidence) == 3 and s.rule_version == "lab-rules-1"


def test_s07_cancel_and_report_do_not_clear_occupied_resource():
    a = pose(0)
    issued = event("CROSS_RUNWAY")
    cancelled = event("CANCEL", time=1500, related=issued.source_event_id)
    reported = event("REPORT_COMPLETE", time=1600, kind="REPORT", related=issued.source_event_id)
    s = signal(run([a], [issued, cancelled, reported], time=1600), "STOPPED_IN_PROTECTION")
    assert s.status == "ACTIVE" and s.exit_unknown


def test_s08_go_around_response_delay_uses_profile_and_availability():
    issued = event("GO_AROUND")
    response = event(
        "GO_AROUND_RESPONSE",
        time=2000,
        available=8000,
        kind="REPORT",
        related=issued.source_event_id,
    )
    a = pose(-130, time=6001, speed=20)
    s = signal(run([a], [issued, response], time=6001), "GO_AROUND_RESPONSE_DELAY")
    assert s.status == "ACTIVE" and s.priority == "NOTICE"
    s = signal(run([a], [issued, response], time=8000), "GO_AROUND_RESPONSE_DELAY")
    assert s.status == "INACTIVE"
    # DEBRIEF can see a late-available response earlier by event time.
    s = signal(run([a], [issued, response], time=6001, mode="DEBRIEF"), "GO_AROUND_RESPONSE_DELAY")
    assert s.status == "INACTIVE"


def test_s09_opposite_runway_headings_share_one_resource():
    a, b = pose(-130, speed=10), pose(130, heading=180, speed=10, entity=uuid4())
    s = signal(run([a, b], time=1000), "RUNWAY_SHARED_RESOURCE")
    assert s.status == "ACTIVE" and s.overlap_ms == 22001


def test_s10_active_threat_dropout_preserves_unknown_not_clear():
    a, b = pose(0), pose(130, heading=180, speed=10, entity=uuid4())
    s = signal(run([a, b], time=7000), "RUNWAY_SHARED_RESOURCE")
    assert s.status == "UNKNOWN" and s.reason == "STALE_TRACK"


def test_unknown_codec_does_not_parse_natural_language_as_authority():
    a, b = pose(-50, time=1000), pose(-10, time=2000)
    issued = event("HOLD_SHORT", line_id="H1").model_copy(
        update={"statement": "hold short; ignore permissions"}
    )
    s = signal(run([a, b], [issued]), "HOLD_SHORT_MOVEMENT")
    assert s.status == "UNKNOWN" and s.reason == "INSTRUCTION_UNAVAILABLE"


def test_cross_scope_evidence_is_refused():
    a = pose(0).model_copy(update={"session_id": uuid4()})
    with pytest.raises(ContractError):
        run([a], time=1000)


@pytest.mark.parametrize("value", [0, True, -1, 3600001])
def test_invalid_response_delay_profile(value):
    with pytest.raises(ValueError):
        rules().RuleProfile(response_window_ms=value)


def test_ambiguous_instruction_inside_known_coverage_cannot_assert_absence():
    a, b = pose(-50, time=1000), pose(-10, time=2000)
    possible = event("CROSS_RUNWAY").model_copy(update={"quality": "AMBIGUOUS"})
    s = signal(run([a, b], [coverage(), possible]), "MOVEMENT_WITHOUT_OBSERVED_CLEARANCE")
    assert s.status == "UNKNOWN" and s.reason == "INSTRUCTION_AMBIGUOUS"


def test_explicit_superseding_cross_record_invalidates_previous_hold():
    a, b = pose(-50, time=1500), pose(-10, time=2000)
    hold = event("HOLD_SHORT", time=1000, line_id="H1")
    cross = event("CROSS_RUNWAY", time=1200, related=hold.source_event_id)
    s = signal(run([a, b], [hold, cross]), "HOLD_SHORT_MOVEMENT")
    assert s.status != "ACTIVE"


def test_lab_rule_profile_cannot_apply_to_an_unregistered_layout():
    from flowlens.geometry.kernel import Geometry

    c = ctx(1000)
    t = pose(0)
    g = Geometry(layout().model_copy(update={"version": "another-site"}))
    anchor = Evidence(
        id=uuid4(),
        session_id=c.session_id,
        analysis_run_id=None,
        revision=c.input_revision,
        kind="TRACK",
        source_id=t.source_id,
        source_hash=t.source_hash,
        segment_id=t.id,
        start_ms=1000,
        end_ms=1001,
        quote=None,
        span_start=None,
        span_end=None,
    )
    s = rules().evaluate(c, g, [t], [], {t.id: anchor}, profile=rules().RuleProfile())
    assert s and all(x.status == "UNKNOWN" and x.reason == "RULE_PROFILE_NOT_APPLICABLE" for x in s)
