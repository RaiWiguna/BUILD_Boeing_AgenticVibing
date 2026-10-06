"""Human-readable export with explicit separation between product metrics and research targets."""
import csv
import html
import io
import json
import statistics
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from .storage import Archive


def _csv_safe_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    first_significant = next(
        (character for character in text
         if not character.isspace() and not unicodedata.category(character).startswith("C")),
        "",
    )
    if first_significant in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def session_report(archive: Archive, source_id: str) -> dict:
    metadata = archive.metadata(source_id)
    frame = archive.frame(source_id)
    if not metadata or not frame:
        raise KeyError(source_id)
    public, private = frame
    events = archive.all_events(source_id)
    durations = private.get("detection_ms", [])
    p95 = sorted(durations)[max(0, int(len(durations)*.95)-1)] if durations else None
    recognised = [e for e in events if e.get("assessment", {}).get("type") == "recognition"]
    return {"metadata": metadata, "duration_ms": public["sim_ms"], "event_count": len(events),
            "metrics": {"detector_p95_ms_recent": p95,
                        "detector_samples_recent": len(durations),
                        "alert_open_count": sum(e["type"] == "ALERT_OPEN" for e in events),
                        "command_count": sum(e["type"] == "COMMAND" for e in events),
                        "acknowledgement_count": len(public["acknowledgements"]),
                        "recognition_marks": [{"sim_ms": e["sim_ms"], "actor": e["actor"]} for e in recognised]},
            "assessments": public["assessments"], "events": events,
            "ground_truth_samples": archive.truth_samples(source_id),
            "research_status": "No trainer review or participant study has been completed by this software release.",
            "limits": ["Synthetic single-runway training only.", "Occupancy overlap is not a predicted collision.",
                       "Task-complexity weights are experimental.",
                       "Raw TLX is an unweighted mean, not the weighted NASA-TLX score.",
                       "Detector timing covers recent recorded samples; LAN metrics need browser measurement."]}


def report_csv(report: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ordinal", "simulation_ms", "type", "message", "actor", "target"])
    for e in report["events"]:
        # Prevent spreadsheet formula interpretation in trainer-provided text.
        writer.writerow([e["ordinal"], e["sim_ms"], _csv_safe_cell(e["type"]),
                         _csv_safe_cell(e["message"]), _csv_safe_cell(e.get("actor")),
                         _csv_safe_cell(e.get("target"))])
    return output.getvalue()


def report_html(report: dict) -> str:
    esc = lambda x: html.escape(str(x))
    rows = "".join(f"<tr><td>{e['sim_ms']/1000:.1f}s</td><td>{esc(e['type'])}</td><td>{esc(e['message'])}</td></tr>"
                   for e in report["events"] if e["type"] != "TRACK")
    assessments = []
    for event in report["assessments"]:
        values = event["assessment"]["values"]
        rating = f" · Raw TLX {statistics.mean(values.values()):.1f}" if values else ""
        assessments.append(f"<p>{esc(event['actor'])}: {esc(event['message'])}{esc(rating)}</p>")
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>FlowLens session report</title>
    <style>body{{font:15px system-ui;margin:40px;color:#142735;max-width:1100px}}table{{border-collapse:collapse;width:100%}}
    td,th{{padding:9px;text-align:left;border-bottom:1px solid #ddd}}.note{{background:#fff4d9;padding:16px}}</style>
    <h1>ATC FlowLens · Training debrief</h1><p>{esc(report['metadata']['scenario']['title'])} ·
    Session {esc(report['metadata']['id'])} · Seed {report['metadata']['seed']}</p>
    <p class="note">{esc(report['research_status'])}</p>
    <h2>Recorded metrics</h2><pre>{esc(report['metrics'])}</pre><h2>Assessments</h2>{''.join(assessments)}
    <h2>Event timeline</h2><table><tr><th>Time</th><th>Event</th><th>Evidence / action</th></tr>{rows}</table>
    <h2>Limits</h2><ul>{''.join('<li>'+esc(v)+'</li>' for v in report['limits'])}</ul></html>"""


def replay_debrief(
    metadata: Mapping[str, Any],
    event_refs: Sequence[Mapping[str, Any]],
    analyses: Sequence[Mapping[str, Any]],
    assist_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Build an imported-replay public debrief without accessing restricted truth or audio."""
    manifest = metadata.get("manifest", {})
    manifest = manifest if isinstance(manifest, Mapping) else {}
    source_kind = manifest.get("source_kind", "unknown")
    if source_kind == "synthetic":
        data_label = "synthetic_fixture_not_operationally_validated"
    elif source_kind == "authorized_simulator_replay":
        data_label = "authorization_claim_from_source_metadata_not_independently_verified"
    else:
        data_label = "source_classification_unknown"

    payload = assist_snapshot.get("payload", {})
    payload = payload if isinstance(payload, Mapping) else {}
    segments = list(payload.get("segments", []))
    highlights = list(payload.get("highlights", []))
    options = list(payload.get("options", []))
    annotations = list(payload.get("review_annotations", []))
    segment_ids = {
        item.get("segment", {}).get("id")
        for item in segments if isinstance(item, Mapping) and isinstance(item.get("segment"), Mapping)
    }
    event_ids = {
        item.get("id") for item in event_refs if item.get("kind") == "session_event"
    }
    unresolved_refs: list[dict[str, Any]] = []
    uncertainty: list[dict[str, Any]] = []
    for item in segments:
        if not isinstance(item, Mapping):
            continue
        segment = item.get("segment", {})
        segment_id = segment.get("id") if isinstance(segment, Mapping) else None
        if item.get("time_alignment") == "unknown":
            unresolved_refs.append({
                "kind": "transcript_segment", "id": segment_id,
                "status": "alignment_unknown",
            })
        if item.get("alignment_uncertainty"):
            uncertainty.append({
                "target_kind": "transcript_segment", "target_id": segment_id,
                "detail": item["alignment_uncertainty"],
            })
    for candidate in highlights:
        if not isinstance(candidate, Mapping):
            continue
        for segment_id in candidate.get("transcript_segment_ids", []):
            if segment_id not in segment_ids:
                unresolved_refs.append({"kind": "transcript_segment", "id": segment_id, "status": "unresolved"})
        for event_id in candidate.get("session_event_ids", []):
            if event_id not in event_ids:
                unresolved_refs.append({"kind": "session_event", "id": event_id, "status": "unresolved"})
        if candidate.get("uncertainty"):
            uncertainty.append({
                "target_kind": "highlight", "target_id": candidate.get("id"),
                "detail": candidate["uncertainty"],
            })
    for candidate in options:
        if not isinstance(candidate, Mapping):
            continue
        for ref in candidate.get("supporting_evidence_ids", []):
            if not isinstance(ref, Mapping):
                continue
            kind, ref_id = ref.get("kind"), ref.get("id")
            if ((kind == "session_event" and ref_id not in event_ids)
                    or (kind == "transcript_segment" and ref_id not in segment_ids)):
                unresolved_refs.append({"kind": kind, "id": ref_id, "status": "unresolved"})
        for unknown in candidate.get("unknowns", []):
            uncertainty.append({
                "target_kind": "option", "target_id": candidate.get("id"), "detail": unknown,
            })

    return {
        "schema_version": "debrief-1",
        "source": {
            "source_session_id": metadata.get("source_session_id"),
            "source_id": metadata.get("source_id"),
            "content_hash": metadata.get("content_hash"),
            "import_status": metadata.get("import_status"),
            "source_kind": source_kind,
            "data_label": data_label,
            "schema_version": manifest.get("schema_version"),
            "provenance": manifest.get("provenance", {}),
            "permission_profile": manifest.get("permission_profile", {}),
            "timebase": manifest.get("timebase", {}),
            "coverage": manifest.get("coverage", {}),
        },
        "analyses": [dict(item) for item in analyses],
        "source_event_refs": [dict(item) for item in event_refs],
        "transcripts": segments,
        "highlights": highlights,
        "options": options,
        "review_annotations": annotations,
        "uncertainty": uncertainty,
        "unresolved_refs": unresolved_refs,
        "limits": [
            "This debrief contains source and reviewer records; it does not establish domain truth or factual support.",
            "Source permission and source-kind labels are copied from import metadata and are not independently verified.",
            "No operational validation is implied.",
        ],
    }


def debrief_csv(debrief: Mapping[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "record_type", "source_session_id", "analysis_id", "target_kind", "target_id",
        "simulation_ms", "decision", "reviewer", "text", "payload_json",
    ])
    source = debrief.get("source", {})
    source_session_id = source.get("source_session_id") if isinstance(source, Mapping) else None

    def emit(record_type: str, *, analysis_id: Any = None, target_kind: Any = None,
             target_id: Any = None, simulation_ms: Any = None, decision: Any = None,
             reviewer: Any = None, text: Any = None, payload: Any = None) -> None:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        writer.writerow([_csv_safe_cell(value) for value in (
            record_type, source_session_id, analysis_id, target_kind, target_id,
            simulation_ms, decision, reviewer, text, serialized,
        )])

    for item in debrief.get("source_event_refs", []):
        emit("event_ref", target_kind=item.get("kind"), target_id=item.get("id"),
             simulation_ms=item.get("sim_ms"), payload=item)
    for item in debrief.get("analyses", []):
        emit("analysis", analysis_id=item.get("id"), payload=item)
    for item in debrief.get("transcripts", []):
        segment = item.get("segment", {})
        emit("transcript", analysis_id=(item.get("revision_history") or [{}])[0].get("analysis_id"),
             target_kind="transcript_segment", target_id=segment.get("id"),
             text=segment.get("text"), payload=item)
    for group_name in ("highlights", "options"):
        for item in debrief.get(group_name, []):
            emit(group_name[:-1], analysis_id=item.get("analysis_id") or item.get("replay_analysis_id"),
                 target_kind=group_name[:-1], target_id=item.get("id"),
                 text=item.get("statement", item.get("option_statement")), payload=item)
    for item in debrief.get("review_annotations", []):
        emit("review_annotation", analysis_id=item.get("analysis_id"),
             target_kind=item.get("target_kind"), target_id=item.get("target_id"),
             decision=item.get("decision"), reviewer=item.get("reviewer"),
             text=item.get("correction") or item.get("reason"), payload=item)
    for item in debrief.get("unresolved_refs", []):
        emit("unresolved_ref", target_kind=item.get("kind"), target_id=item.get("id"), payload=item)
    return output.getvalue()


def debrief_html(debrief: Mapping[str, Any]) -> str:
    serialized = json.dumps(debrief, sort_keys=True, ensure_ascii=False, indent=2)
    escaped = html.escape(serialized)
    return (
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
        "<title>ATC FlowLens replay debrief</title>"
        "<h1>ATC FlowLens · Replay debrief</h1>"
        "<pre>" + escaped + "</pre></html>"
    )
