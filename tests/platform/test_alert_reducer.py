"""Immutable alert projection separates source severity, deterministic priority, and seen state."""

import importlib
import json
from uuid import uuid4

import pytest
from flowlens.contracts.models import Evidence
from flowlens.core.errors import ContractError
from test_observed_rules import ctx, event, pose, run, signal


def reducer():
    return importlib.import_module("flowlens.geometry.alerts")


def active():
    return signal(run([pose(0)], time=1000), "STOPPED_IN_PROTECTION")


def test_deterministic_active_unchanged_clear_unknown_reproducible():
    s = active()
    first = reducer().reduce_signal(None, s)
    assert first.version == 1 and first.origin == "DETERMINISTIC" and first.source_severity is None
    assert first.status == "ACTIVE" and first.priority == "ATTENTION"
    same = reducer().reduce_signal(first, s.model_copy(update={"as_of_ms": 1100}))
    assert same == first
    unknown = reducer().reduce_signal(
        first, s.model_copy(update={"as_of_ms": 7000, "status": "UNKNOWN", "reason": "STALE_TRACK"})
    )
    assert (
        unknown.version == 2
        and unknown.status == "UNKNOWN"
        and unknown.previous_revision_id == first.revision_id
    )
    clear = reducer().reduce_signal(
        unknown,
        s.model_copy(
            update={"as_of_ms": 8000, "status": "INACTIVE", "reason": "NO_STOPPED_OCCUPANCY"}
        ),
    )
    assert clear.status == "CLEARED" and clear.version == 3
    assert reducer().reduce_signal(None, s) == first


def test_backward_projection_never_overwrites_newer_alert():
    s = active()
    first = reducer().reduce_signal(None, s)
    with pytest.raises(ContractError):
        reducer().reduce_signal(first, s.model_copy(update={"as_of_ms": 999}))


def source(status="ACTIVE", severity="CRITICAL", time=1000):
    e = event("", time, kind="ALERT").model_copy(
        update={
            "statement": json.dumps(
                {
                    "profile_version": "lab-source-1",
                    "type": "SOURCE_ALERT",
                    "alert_key": "hazard-1",
                    "status": status,
                    "severity": severity,
                }
            )
        }
    )
    c = ctx(time)
    anchor = Evidence(
        id=uuid4(),
        session_id=c.session_id,
        analysis_run_id=None,
        revision=c.input_revision,
        kind="EVENT",
        source_id=e.source_id,
        source_hash=e.source_hash,
        segment_id=e.id,
        start_ms=time,
        end_ms=time + 1,
        quote=None,
        span_start=None,
        span_end=None,
    )
    return c, e, anchor


def test_source_alert_severity_and_closure_owned_only_by_source():
    c, e, a = source()
    first = reducer().reduce_source(None, c, e, a)
    assert (
        first.origin == "SOURCE" and first.source_severity == "CRITICAL" and first.priority is None
    )
    assert first.source_event == e and first.evidence == [a]
    c, e, a = source("CLEARED", "WARNING", 2000)
    next = reducer().reduce_source(first, c, e, a)
    assert next.status == "CLEARED" and next.source_severity == "WARNING" and next.version == 2
    with pytest.raises(ContractError):
        reducer().reduce_signal(first, active().model_copy(update={"id": first.id}))


def test_source_unknown_codec_not_invented_or_regraded():
    c, e, a = source()
    with pytest.raises(ContractError):
        reducer().reduce_source(
            None, c, e.model_copy(update={"statement": "AI says alert clear"}), a
        )


def test_source_evidence_scope_and_future_visibility_denied():
    c, e, a = source()
    with pytest.raises(ContractError):
        reducer().reduce_source(None, c, e, a.model_copy(update={"session_id": uuid4()}))
    with pytest.raises(ContractError):
        reducer().reduce_source(None, c.model_copy(update={"as_of_ms": 999}), e, a)


def test_seen_receipt_never_changes_alert_status_or_source_severity():
    c, e, a = source()
    first = reducer().reduce_source(None, c, e, a)
    ack = reducer().seen(c, first)
    assert (
        ack.alert_id == first.id
        and ack.alert_revision_id == first.revision_id
        and ack.actor_id == c.actor_id
    )
    assert ack.meaning == "SEEN_ONLY"
    assert first.status == "ACTIVE" and first.source_severity == "CRITICAL"
