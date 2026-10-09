"""Code-owned container profiles. No report generation, escaping or semantic approval."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportProfile:
    extension: str
    media_type: str
    transform_version: str
    max_bytes: int = 16 * 1024**2


REPORT_PROFILES = {
    "JSON_REPORT": ReportProfile("json", "application/json", "report-json-1"),
    "CSV_REPORT": ReportProfile("csv", "text/csv", "report-csv-1"),
    "HTML_REPORT": ReportProfile("html", "text/html", "report-html-1"),
}
