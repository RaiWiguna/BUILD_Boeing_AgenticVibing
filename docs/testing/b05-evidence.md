# B05 — independent local engineering and standalone MOCK evidence

Tanggal: 9 Oktober 2026. Branch `feat/backend-rai`; HEAD
`da279281f1698197df1efef569f578adb1610cef`; upstream `origin/feat/backend-rai`.
Existing B03/D3/evaluator/B04 edits, docs/pitch, tests/browser and tmp preserved.
No reset/clean/stage/commit/push/merge/branch change. No server/daemon left running.

## Status and sequencing

B05 / Phase9 bagian B remains **in_progress**. Local engineering and executable
standalone MOCK acceptance are implemented; domain/semantic external acceptance is
not established. User authorization permits B05 local work before external B03/B04
closure. It does not authorize paid requests, fallback/provider/model changes,
frozen contract changes, A implementation, real composition, frontend or deployment.
B06 has not started. Parent phases/G-BE/G-FE/G-DELIVERY remain open/not_started.

**B04_EXTERNAL_ACCEPTANCE_PENDING**
- **GEMINI_ACCOUNT_ACCESS_UNVERIFIED**
- **REAL_GEMINI_SMOKE_PENDING**
- **AUDITED_SEMANTIC_BENCHMARK_PENDING**

B04 / Phase8: **in_progress**. Local engineering + standalone MOCK acceptance:
**passed**. Real Gemini provider_calls: **0**. Real smoke: **NOT_RUN**.
Audited semantic benchmark: **BLOCKED**. Benchmark metrics: **null**.
Integrated pipeline readiness: **false**.
Existing **GEMINI_EXTERNAL_ACCEPTANCE_PENDING** remains visible.

**B03_EXTERNAL_ACCEPTANCE_PENDING**
- **STT_ACCOUNT_LOGIN_REQUIRED**
- **AUDITED_BENCHMARK_PENDING**

B03 / Phase7: **in_progress**; local D1/D2/D3/scorer acceptance preserved.
Real STT calls: **0**. Real smoke: **NOT_RUN**. Audited benchmark: **BLOCKED**,
metrics **null**. No account provisioning/authenticated account audit or paid RPC
was attempted. HTTP-MOCK SDK requests are not real provider calls.

## Entrypoints, ownership and contracts

| File / entrypoint | Executable responsibility |
| --- | --- |
| advisory/models.py | Private typed facts, eligibility, findings, selections, hypothetical options, document generations, review/invalidation/proposal/query records |
| advisory/findings.py | findings-1; six PRD categories, deterministic evidence/identity/coverage/source/geometry eligibility and canonical dependency digest |
| advisory/provider.py:AdvisoryExecutor | advisory-select-1; stateless bounded fact/template selection through approved client, checkpoint/budget callbacks |
| providers/gemini/adapter.py:GoogleClient.structured | Reuses existing explicit approvals, pinned model/SDK and SingleSendTransport with private schema/policy; original create delegates with original intent schema/policy |
| advisory/service.py:AdvisoryService | Propose/accept/review/invalidate/reanalyze/query/purge; required authoritative source/attempt binding and caller UOW |
| advisory/service.py:register_advisory | Registers service, repository, migration, inventory and purge; routes empty, job_handlers empty, readiness false |
| advisory/store.py | analysis.0004 scoped append-only ledger; injected connection and UOW guard; no worker-owned DB |
| advisory/exports.py:ReportRenderer | JSON/CSV/HTML private report bytes + frozen ArtifactSubmission, mandatory export policy and evidence allowlist |
| advisory/diagnostics.py | Measured communication indicators; sanitized MOCK/account/runtime distinctions and pending flags |
| advisory/retention.py:AnalysisRetention | Injected analysis-owned participant inventory/purge, dependency-safe order, required authority, caller transaction |
| testing/advisory.py | `python -m flowlens.testing.advisory`; disposable SQLite with explicit MOCK authority/provider/platform ports |
| tests/analysis/test_advisory.py | Independent synthetic semantic/security/persistence/failure oracles; not an audited benchmark |

Frozen contracts/generated schemas1.0.0 unchanged. Private records do not hide
structured payload in wire text/reason/Usage. No new dependency was needed.
Architecture: [ADR0006](../adr/0006-evidence-bound-advisory-revisions.md).

## Semantic behavior and deliberate limits

Critical-slot uncertainty, readback discrepancy, open-loop, speech-record,
movement-divergence and source-quality categories remain separate. Said, Heard,
Reported, Observed, source alerts and reviewer decisions keep distinct labels/state.
Unknown/multiple identity and incomplete slots cannot become definite mismatches.
Coverage gaps cannot establish a missed response. Matching speech never proves
movement compliance; reported clear never proves physical runway clearance.

External comparisons require authoritative typed eligibility for identity,
association, clock alignment, coverage and instruction applicability. Movement also
requires freshness and scoped EVALUATED GeometryResult with layout/rule/evidence,
known occupancy/uncertainty and bounded past intervals. Observations require
TRACK/EVENT evidence; source records require EVENT/POLICY. Missing inputs fail closed.
Authority must still prove actual semantic support and current source freshness;
the mock test geometry is not real numeric geometry acceptance.

Gemini selects validated fact IDs, rather than free factual prose. Speech text is
an exact evidence excerpt; source facts must be attested by the injected adapter.
Briefs keep fixed known-situation/instruction/open-loop/findings/unknown sections.
Source alerts/severity and unresolved context cannot disappear through selection.
Hypothetical options use bounded review/compare-offline templates with preconditions,
unknowns and tradeoffs; they contain no command/transmission/clearance payload.
Zero options/INSUFFICIENT_CONTEXT is valid. This is intentionally conservative:
selection relevance, paraphrase quality and usefulness need audited domain evaluation.
It does not claim rich free-form operational advice or an optimal alternative.

Queries are read-only, bounded by server scope/as-of and current evidence checks,
and never become memory/instruction events. Provider failure returns UNAVAILABLE
without changing cached replay. No query history is persisted by this service.
All statements point to evidence; arbitrary output fields/native tools are rejected.
Prompt/transcript injection cannot introduce a write/command tool because none exists.

## Persistence, authority and security evidence

analysis.0004 depends on analysis.0003, owns only analysis_advisory_ledger and has
session/run/revision foreign keys, JSON/input-hash checks and unique stream/version
constraints. Genuine upgrade from .0003 preserves prior migration hashes/parents;
fresh schema, restart and foreign_key_check pass. ID/normalized-content duplicates
reuse the original row; changed payload and competing optimistic versions fail.

Review actor is server-bound, subject must exist, unsupported physical findings
cannot be confirmed and stale/source-changed documents cannot be reviewed. Reviews
append without overwriting findings/source alerts. Reanalysis appends invalidation
plus a new document version atomically; old versions remain visible at historical
as-of. Current source digest changes mark exports stale and block reviews. Explicit
correction/reanalysis invalidations retain caller-supplied event/availability clocks.

Document/evidence references/audit/safe notices share caller transaction boundaries.
Evidence is referenced after authoritative resolution rather than reinserted into
the platform registry. Missing commit, audit failure and reanalysis failure roll back.
Services never commit or publish. Authority must recheck active attempts/leases,
cancellation/deadline/rights/config/revision and authenticated candidates, including
duplicates. No permissive real authority callback or placeholder handler is installed.

ExportAccess must authorize current per-source rights and return private expiry,
allowlisted evidence and text policy. Redaction covers excerpts, review reasons and
source-provided unknown details across all three formats. HTML escapes full content;
CSV neutralizes formula prefixes/leading whitespace/control characters in every
cell. Metadata contains labels/versions/unknowns/evidence inventory/review/corrections/
limitations. Audio is excluded, with no public audio URL or audio export grant.
Artifact publication/ACL/download/expiry enforcement stay with platform composition.

Retention test coordinates advisory, memory, all transcript namespaces and config
in dependency-safe order. Purge rollback, failure after an earlier participant,
scoped inventory and preservation of platform parent rows are verified. No platform
artifact/audit/receipt/tombstone lifecycle is implemented. Runtime provider import
tests exclude SQLite, platform storage, testing/evaluator imports.

Communication metrics union duplicate evidence spans, count observed entity switches
and known/unknown loops. They do not infer active frequency occupancy, workload,
fitness-for-duty or safety benefit. Occupancy remains null without validated VAD.

## Actual verification

Python3.12.15 from .venv/Scripts and uv used. FFmpeg9.0.2 added only to test-process
PATH. Numbers below are actual runs in this session, not copied historical evidence.

| Check | Actual result |
| --- | --- |
| Initial baseline without process FFmpeg PATH | 582 PASS / 2 FAIL / 5 SKIP; AUDIO_BINARY_MISSING |
| Before source edits, baseline with process FFmpeg PATH | 589 PASS, no skips,47.74s |
| Full B regression before final eligibility/redaction tightening | 665 PASS, no skips,65.80s |
| B05 focused after eligibility and source-detail redaction | 77 PASS,26.35s |
| Concurrent full regression during final tightening | 664 PASS / 1 FAIL,104.25s; existing STT cancellation timing test, task cancelled before mock client recorded cancellation; no test/timeout weakened |
| Contracts A | 66 PASS,12.50s |
| Standalone B04 | PASS; MOCK calls2, real0, disposable-cleaned |
| Standalone B05 | PASS; MOCK calls3, real STT/Gemini0, disposable-cleaned, readiness false |
| Default Gemini preflight | BLOCKED, GEMINI_EXTERNAL_ACCEPTANCE_PENDING, provider_calls0, metrics=null |
| Ruff check backend tests scripts | PASS |
| Ruff format --check backend tests scripts | PASS,108 files |
| Native scoped B mypy | PASS,59 source files |
| Linux-target backend mypy | PASS,84 source files |
| Focused advisory/testing mypy after final eligibility/redaction | PASS,10 source files |
| Full native Windows mypy | Seven pre-existing POSIX errors in A storage/sqlite/database.py and cli/bootstrap_admin.py;84 files checked |
| flowlens.contracts.generate --check | PASS, frozen schema/OpenAPI drift absent |
| Bandit -r backend/flowlens -ll | PASS, zero issues all severities; existing exclusions preserved |
| pip-audit --local | No known dependency vulnerabilities; local unpublished atc-flowlens package cannot be audited via PyPI |
| uv build --out-dir artifacts/reports/b05-dist | PASS, sdist and wheel; ignored local outputs |
| git diff --check | PASS |

Final isolated `pytest tests/analysis tests/contracts --track B -q` on final source:
**666 PASS, no skips,58.36s** (589 existing +77 B05). The existing cancellation test
passed without source/test/timeout changes. The failed concurrent run is retained
above; scheduling sensitivity is not treated as a semantic benchmark result.
Final source wheel/sdist refresh and Bandit passed after source-detail redaction.
No real smoke, held-out benchmark, domain review or integrated readiness is claimed.
No test thresholds, mocks or assertions were weakened to obtain a pass.

## Contract gaps and remaining acceptance

Private records need Phase10 public projection/route/job-handler reconciliation;
frozen ProviderAdapter/JobResult do not express these full private document/review/
dependency records. Source comparison/coverage/alias/role/freshness and evidence
availability require authoritative adapters; wire Evidence lacks availability.
Current input-digest staleness is conservative: new context can require regeneration
even when earlier claims remain valid. Explicit revision APIs keep old documents.
Synchronous authority/evidence ports need bounded implementations; Python cannot
forcibly terminate an uncooperative synchronous adapter. Provider checkpoint/budget
callbacks must enforce current scope/rights throughout async work.

| Blocker | Owner | Required evidence and next action |
| --- | --- | --- |
| STT_ACCOUNT_LOGIN_REQUIRED | User/cloud operator | Approved account/profile/API/locale/model/region/rights/quota/budget, then authorized synthetic STT smoke |
| AUDITED_BENCHMARK_PENDING (B03) | Annotation/evaluation lead | Audited audio/critical-slot/timing labels, held-out splits/protocol/thresholds and real output receipts; run existing scorer |
| GEMINI_ACCOUNT_ACCESS_UNVERIFIED / REAL_GEMINI_SMOKE_PENDING | User/cloud operator | Approved identity/key/model/API access, terms/rights/quota/budget and paid authorization; actual structured compatibility smoke |
| AUDITED_SEMANTIC_BENCHMARK_PENDING / B05 domain semantics | Evaluation/domain lead | Audited held-out intent/association/finding/relevance/abstention labels and real outputs; assess conservative briefs/options usefulness |
| Real composition | Platform/analysis owners,Phase10 | Durable authority/receipts, private artifact ACL/TTL/promotion, evidence availability, public projections and atomic handler/API wiring |

Research output remains **NOT_DOMAIN_VALIDATED**. MOCK acceptance never closes the
external acceptance flags, parent phases or backend/frontend/delivery gates.


Final source refresh: Linux-target mypy84/Ruff108/schema drift/Bandit/build PASS.
Wheel inspection confirms all9 advisory modules plus testing/advisory.py are present.
Final tracked diff whitespace and new B05 file whitespace/link checks pass.
