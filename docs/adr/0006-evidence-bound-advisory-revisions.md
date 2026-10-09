# ADR 0006 — Evidence-bound advisory revisions and private reports

Status: accepted architecture; standalone MOCK evidence recorded separately.
Tanggal: 9 Oktober 2026.

## Context

Frozen contracts1.0.0 cannot carry all private eligibility, document generations,
review streams, dependency digests and report policy. Evidence IDs alone cannot
justify arbitrary AI prose. Memory and observations have different authority.

## Decision

Use private typed advisory records and analysis.0004 without extending generated
schemas or concealing data in text/reason/Usage. Findings derive from accepted memory
and authoritative comparison signals. Missing identity, coverage, source records or
eligible geometry stays unknown/NOT_EVALUABLE. Observations need TRACK/EVENT evidence;
source records need EVENT/POLICY. Required authority additionally attests semantic
support, rights, identity, alignment, freshness and applicability inside caller UOW.

Gemini selects validated fact IDs and bounded hypothetical review templates using
the existing approved GoogleClient/SingleSendTransport. No free factual prose,
clearance payload or native tool is accepted. Speech statements are exact excerpts
with Said/Heard/Reported labels. Source alerts and unresolved context remain in
documents even when the provider omits them. Conservative validation does not prove
relevance or domain usefulness. Zero options/INSUFFICIENT_CONTEXT is valid.

The client exposes a schema-parametric structured request using the same approval,
model and transport guards as intent extraction. Advisory requests use GeminiConfig,
checkpoint and reservation bounds. Prompt advisory-select-1 and schema/config/request/
response hashes are recorded. No fallback, evaluator truth or conversation state.

Connection-injected ledger rows use scoped FKs, unique stream/version keys and
immutable IDs. Documents, reviews and invalidations append. Reanalysis appends
invalidation and replacement in one caller UOW. Current source digest changes mark
old outputs stale and block reviews. Explicit invalidations retain availability
clocks. Authority rechecks include duplicates. Caller must roll back on error and
owns commit/publication. Notices contain IDs/kind only. Query has no write port.

ReportRenderer returns JSON/CSV/HTML bytes and private ArtifactSubmission metadata.
Required ExportAccess supplies current source rights, evidence allowlist, text
redaction and expiry. Report permission never exports audio. Artifact publication,
ACL/TTL/download remain platform-owned. Escaping/formula neutralization covers all
fields, including review reasons; no public audio URL is produced.

AnalysisRetention only orchestrates injected analysis-owned participants in
dependency-safe order, with authority/caller UOW. It never deletes platform artifacts,
audit, receipts or tombstones. Metrics describe measured speech evidence spans,
entity switches and known/unknown loops; occupancy stays null without validated VAD.

## Alternatives and consequences

Unconstrained prose was rejected because references alone do not prove support.
Template selection is less expressive and still needs independent domain evaluation.
Free paraphrases and richer hypotheses require a separately evaluated validator.
Authority is a trust boundary, not an implementation of platform/geometry/jobs.
Synchronous adapters must be bounded and enforce server availability; frozen evidence
lacks that metadata. Real composition must prevent direct unvalidated repository writes.

## Validation and follow-up

[B05 evidence](../testing/b05-evidence.md) covers local oracles, persistence, restart,
rollback, redaction, escaping and HTTP-MOCK SDK behavior. B03/B04 real smoke,
audited semantics, domain validation and Phase10 authority/artifact/receipt/public
projection/atomic handler wiring remain mandatory. No routes/job handlers installed;
readiness remains false. MOCK acceptance cannot close parent phases or gates.
