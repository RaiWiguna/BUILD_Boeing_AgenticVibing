"""Human-readable export with explicit separation between product metrics and research targets."""
import csv
import html
import io
import statistics

from .storage import Archive


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
        def cell(value):
            text = str(value or "")
            return "'"+text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text
        writer.writerow([e["ordinal"], e["sim_ms"], e["type"], cell(e["message"]),
                         cell(e.get("actor")), cell(e.get("target"))])
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
