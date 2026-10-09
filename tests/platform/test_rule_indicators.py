"""Experimental metrics use measured annotations and frozen B context, never mental-state claims."""

from uuid import uuid4

from flowlens.contracts.models import OpenLoop
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_observed_rules import event, pose
from test_occupancy import at
from test_rule_service import service, source


def activity(start, end, channel=0, time=5000):
    return event(
        None,
        time,
        kind="QUALITY",
        type="AUDIO_ACTIVITY",
        start_ms=start,
        end_ms=end,
        channel=channel,
        measurement_version="synthetic-active-audio-1",
    )


def test_source_reported_audio_activity_unions_overlap_and_stays_experimental(
    importer, committed, tmp_path
):
    receipt, _ = source(
        importer,
        committed,
        tracks=[pose(0, time=5000)],
        events=[activity(1000, 3000), activity(2000, 4000, 1)],
    )
    s, files, evidence = service(committed, tmp_path)
    try:
        c = at(committed, receipt, 5000)
        metrics = s.evaluate(c).indicators
        assert metrics.reported_active_audio_ms == 3000
        assert metrics.activity_status == "SOURCE_REPORTED_NOT_VAD_VERIFIED"
        assert metrics.occupied_audio_ms is None and metrics.open_loop_count is None
        assert (
            metrics.label == "EXPERIMENTAL_NOT_WORKLOAD"
            and metrics.definition_version == "lab-indicators-1"
        )
        assert metrics.queued_job_count == 0 and metrics.active_entity_count == 1
        for e in metrics.evidence:
            assert evidence.get(c, e.id) == e
    finally:
        files.close()


def test_no_vad_or_activity_annotation_stays_unknown_not_silence(importer, committed, tmp_path):
    receipt, _ = source(importer, committed)
    s, files, _ = service(committed, tmp_path)
    try:
        metrics = s.evaluate(at(committed, receipt, 1000)).indicators
        assert metrics.reported_active_audio_ms is None and metrics.activity_status == "UNAVAILABLE"
        assert metrics.occupied_audio_ms is None and metrics.open_loop_status == "UNAVAILABLE"
    finally:
        files.close()


def test_activity_end_after_evidence_event_not_used_as_a_known_measurement(
    importer, committed, tmp_path
):
    receipt, _ = source(importer, committed, events=[activity(1000, 6000, time=5000)])
    s, files, _ = service(committed, tmp_path)
    try:
        assert s.evaluate(at(committed, receipt, 5000)).indicators.reported_active_audio_ms is None
    finally:
        files.close()


def test_open_loop_count_from_injected_frozen_context_reader_and_evidence_validation(
    importer, committed, tmp_path
):
    receipt, _ = source(importer, committed)
    calls = []

    class FakeContext:
        def lookup(self, c, request):
            calls.append(request)
            from flowlens.contracts.models import Evidence

            t = committed[1].tracks(c, prepared_entity)[0]
            anchor = Evidence(
                id=t.id,
                session_id=c.session_id,
                analysis_run_id=c.analysis_run_id,
                revision=c.input_revision,
                kind="TRACK",
                source_id=t.source_id,
                source_hash=t.source_hash,
                segment_id=t.id,
                start_ms=t.event_time_ms,
                end_ms=t.event_time_ms + 1,
                quote=None,
                span_start=None,
                span_end=None,
            )
            return [
                OpenLoop(
                    id=uuid4(),
                    session_id=c.session_id,
                    analysis_run_id=c.analysis_run_id,
                    revision=c.input_revision,
                    event_time_ms=1000,
                    available_time_ms=1000,
                    recorded_at=t.recorded_at,
                    evidence=[anchor],
                    originating_id=uuid4(),
                    entity_ids=[prepared_entity],
                    kind="READBACK_EXPECTED",
                    status="OPEN",
                    started_ms=1000,
                    expected_window_ms=5000,
                    coverage_known=True,
                    closing_evidence_ids=[],
                    timer_profile_version="synthetic-1",
                )
            ]

    with committed[1].database.begin() as uow:
        from flowlens.imports.metadata import PreparedImport

        prepared = PreparedImport.model_validate_json(
            uow.connection.execute(
                "SELECT payload FROM platform_source_packages WHERE session_id=?",
                (str(receipt.session_id),),
            ).fetchone()[0]
        )
        prepared_entity = prepared.identities[0].entity_id
    s, files, _ = service(committed, tmp_path, context_reader=FakeContext())
    try:
        metrics = s.evaluate(at(committed, receipt, 1000)).indicators
        assert metrics.open_loop_count == 1 and metrics.open_loop_status == "EVALUATED"
        assert calls[0].name == "get_active_rule_context" and calls[0].limit == 100
    finally:
        files.close()


def test_context_reader_failure_reports_unavailable_without_private_error(
    importer, committed, tmp_path
):

    receipt, _ = source(importer, committed)

    class BrokenContext:
        def lookup(self, c, request):
            raise RuntimeError("private provider message")

    s, files, _ = service(committed, tmp_path, context_reader=BrokenContext())
    try:
        result = s.evaluate(at(committed, receipt, 1000))
        assert result.indicators.open_loop_status == "UNAVAILABLE"
        assert "private provider message" not in result.model_dump_json()
    finally:
        files.close()


def test_duplicate_loop_ids_and_over_limit_context_do_not_inflate_count(
    importer, committed, tmp_path
):
    from uuid import uuid4

    from flowlens.contracts.models import Evidence

    receipt, _ = source(importer, committed)

    class RepeatedContext:
        def lookup(self, c, request):
            t = committed[1].read_events(c)[-1]
            anchor = Evidence(
                id=t.id,
                session_id=c.session_id,
                analysis_run_id=c.analysis_run_id,
                revision=c.input_revision,
                kind="TRACK",
                source_id=t.source_id,
                source_hash=t.source_hash,
                segment_id=t.id,
                start_ms=t.event_time_ms,
                end_ms=t.event_time_ms + 1,
                quote=None,
                span_start=None,
                span_end=None,
            )
            loop = OpenLoop(
                id=uuid4(),
                session_id=c.session_id,
                analysis_run_id=c.analysis_run_id,
                revision=c.input_revision,
                event_time_ms=1000,
                available_time_ms=1000,
                recorded_at=t.recorded_at,
                evidence=[anchor],
                originating_id=uuid4(),
                entity_ids=[t.entity_id],
                kind="READBACK_EXPECTED",
                status="OPEN",
                started_ms=1000,
                expected_window_ms=5000,
                coverage_known=True,
                closing_evidence_ids=[],
                timer_profile_version="synthetic-1",
            )
            return [loop] * 101

    s, files, _ = service(committed, tmp_path, context_reader=RepeatedContext())
    try:
        metrics = s.evaluate(at(committed, receipt, 1000)).indicators
        assert metrics.open_loop_count == 1 and metrics.open_loop_status == "PARTIAL"
    finally:
        files.close()
