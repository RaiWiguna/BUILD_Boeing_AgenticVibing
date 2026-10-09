"""Private report bytes only. Artifact publication/audio export belong to platform."""

import csv
import hashlib
import html
import io
import json
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from flowlens.advisory.findings import digest
from flowlens.advisory.models import Document, Entry, Review
from flowlens.advisory.service import AdvisoryService, journal, repo, stale_ids
from flowlens.contracts.models import ArtifactSubmission, Contract, RequestContext
from flowlens.contracts.ports import UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.intent.validation import visible


class ExportPolicy(Contract):
    evidence_ids: tuple[UUID, ...]
    include_text: bool
    expires_at: datetime
    source_labels: tuple[str, ...]


class ExportAccess(Protocol):
    def authorize(self, ctx: RequestContext, document: Entry, uow: UnitOfWork) -> ExportPolicy:
        """Current per-source report rights, recipient redaction, private expiry.

        A report grant does not grant audio access/export. Actual artifact ACL,
        promotion, expiry enforcement and download authorization belong to A.
        """
        ...


def safe_cell(value: str) -> str:
    if value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class ReportRenderer:
    def __init__(self, service: AdvisoryService, access: ExportAccess) -> None:
        self.service, self.access = service, access

    def render(
        self,
        ctx: RequestContext,
        identifier: UUID,
        format: Literal["JSON", "CSV", "HTML"],
        *,
        artifact_id: UUID,
        now: datetime,
        uow: UnitOfWork,
    ) -> tuple[bytes, ArtifactSubmission]:
        ctx.require("export", ctx.session_id, ctx.analysis_run_id)
        current = self.service.inputs(ctx, uow)
        target = repo(uow).get(ctx, identifier)
        visible(ctx, target)
        if not isinstance(target.body, Document) or target.body.as_of_ms > ctx.as_of_ms:
            raise ContractError("INVALID_INPUT")
        policy = self.access.authorize(ctx, target, uow)
        policy = ExportPolicy.model_validate_json(policy.model_dump_json())
        if policy.expires_at <= now:
            raise ContractError("ACCESS_DENIED")
        document = target.body
        history = journal(ctx, repo(uow).inventory(ctx))
        allowed = set(policy.evidence_ids)
        evidence = {e.id: e for f in document.facts for e in f.evidence}
        evidence.update({e.id: e for finding in document.findings for e in finding.evidence})
        inventory = []
        for ev in evidence.values():
            if ev.id not in allowed or ev.kind == "AUDIO":
                continue
            self.service.evidence.resolve(ctx, ev)
            item = ev.model_dump(mode="json")
            if not policy.include_text:
                item["quote"] = None
                item["span_start"] = None
                item["span_end"] = None
            inventory.append(item)
        permitted = {str(e["id"]) for e in inventory}
        facts = [
            {
                "id": str(f.id),
                "label": f.label,
                "statement": f.statement
                if policy.include_text and all(str(e.id) in permitted for e in f.evidence)
                else "REDACTED",
                "source_severity": f.source_severity,
                "evidence_ids": [str(e.id) for e in f.evidence if str(e.id) in permitted],
            }
            for f in document.facts
        ]
        findings = [
            {
                "id": str(f.id),
                "category": f.category,
                "statement": f.statement,
                "status": f.status,
                "priority": f.priority,
                "unknowns": list(f.unknowns)
                if policy.include_text and all(str(e.id) in permitted for e in f.evidence)
                else ["REDACTED_DETAILS"],
                "rule_version": f.rule_version,
                "applicability": f.applicability,
                "quality": f.quality,
                "evidence_ids": [str(e.id) for e in f.evidence if str(e.id) in permitted],
                "redacted": any(str(e.id) not in permitted for e in f.evidence),
            }
            for f in document.findings
        ]
        reviews = [
            {
                "id": str(e.id),
                "version": e.version,
                "actor_id": str(e.body.actor_id),
                "subject_id": str(e.body.subject_id),
                "decision": e.body.decision,
                "reason": e.body.reason if policy.include_text else "REDACTED",
            }
            for e in history
            if isinstance(e.body, Review) and e.body.document_id == target.id
        ]
        payload = {
            "contract_version": "1.0.0",
            "report_version": "advisory-report-1",
            "session_id": str(ctx.session_id),
            "run_id": str(ctx.analysis_run_id),
            "input_revision": ctx.input_revision,
            "input_hash": ctx.input_hash,
            "document_id": str(target.id),
            "document_version": target.version,
            "as_of_ms": document.as_of_ms,
            "mode": document.mode,
            "timebase": "SESSION_RELATIVE_MS",
            "source_labels": policy.source_labels,
            "expires_at": policy.expires_at.isoformat(),
            "status": document.status,
            "stale": target.id in stale_ids(history) or document.input_digest != digest(current),
            "provenance": document.provenance.model_dump(mode="json"),
            "prompt_version": document.prompt_version,
            "sections": document.sections,
            "active_instruction_ids": tuple(str(i) for i in document.active_instruction_ids),
            "open_loop_ids": tuple(str(i) for i in document.open_loop_ids),
            "unknowns": document.unknowns if policy.include_text else ("REDACTED_DETAILS",),
            "limitations": document.limitations,
            "facts": facts,
            "findings": findings,
            "reviews": reviews,
            "options": [
                o.model_dump(mode="json")
                | {
                    "rationale_evidence": [
                        str(i) for i in o.rationale_evidence if str(i) in permitted
                    ],
                    "redacted": any(str(i) not in permitted for i in o.rationale_evidence),
                }
                for o in document.options
            ],
            "evidence_inventory": inventory,
            "corrections": [
                {"id": str(e.id), "kind": e.body.kind, "version": e.version}
                for e in history
                if e.stream_id == target.stream_id
                or (e.body.kind == "INVALIDATE" and target.id in e.body.document_ids)
            ],
            "audio": "EXCLUDED_SEPARATE_PERMISSION_REQUIRED",
        }
        if format == "JSON":
            data = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
            kind: Literal["JSON_REPORT", "CSV_REPORT", "HTML_REPORT"] = "JSON_REPORT"
        elif format == "HTML":
            data = (
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                "<title>Offline research review</title><h1>Offline research review</h1><pre>"
                + html.escape(json.dumps(payload, indent=2, ensure_ascii=False))
                + "</pre></html>"
            ).encode()
            kind = "HTML_REPORT"
        elif format == "CSV":
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer)
            writer.writerow(("section", "field", "value"))
            # Every report field, including metadata/provenance/review, remains present.
            for key, value in payload.items():
                values = value if isinstance(value, list) else [value]
                for csv_item in values:
                    if isinstance(csv_item, dict):
                        for field, cell in csv_item.items():
                            writer.writerow(
                                (
                                    safe_cell(key),
                                    safe_cell(field),
                                    safe_cell(
                                        cell
                                        if isinstance(cell, str)
                                        else json.dumps(cell, ensure_ascii=False)
                                    ),
                                )
                            )
                    else:
                        writer.writerow(
                            (
                                "metadata",
                                safe_cell(key),
                                safe_cell(
                                    csv_item
                                    if isinstance(csv_item, str)
                                    else json.dumps(csv_item, ensure_ascii=False)
                                ),
                            )
                        )
            data, kind = buffer.getvalue().encode(), "CSV_REPORT"
        else:
            raise ContractError("INVALID_INPUT")
        artifact = ArtifactSubmission(
            id=artifact_id,
            session_id=ctx.session_id,
            analysis_run_id=ctx.analysis_run_id,
            revision=ctx.input_revision,
            kind=kind,
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            source_asset_id=None,
            transform_version="advisory-report-1",
            source_range=None,
            derivative_range=None,
            expires_at=policy.expires_at,
            required_capability="export",
        )
        return data, artifact
