# B04 — local Analysis & AI engineering evidence

Tanggal: 9 Oktober 2026. Branch feat/backend-rai; HEAD/upstream baseline
da279281f1698197df1efef569f578adb1610cef. Existing D3/STT/evaluator/docs changes,
docs/pitch, tests/browser and tmp preserved. No reset/clean/stage/commit/push/merge
or branch change. B04 remains in_progress; frozen contracts1.0.0 unchanged.

## Status and authority

Local structured intent, bounded read-only orchestration, conservative association,
application-owned persistence/reconstruction and open-loop engineering are implemented.
Standalone acceptance uses explicit MOCK provider/platform ports and disposable SQLite.
This does not establish real-provider or integrated runtime readiness.

B03/Phase7 remains in_progress. B03_EXTERNAL_ACCEPTANCE_PENDING remains visible,
with STT_ACCOUNT_LOGIN_REQUIRED and AUDITED_BENCHMARK_PENDING. D1/D2/D3/local scorer
acceptance is preserved. Real STT smoke not run, provider_calls0; B03 benchmark
BLOCKED, metrics=null. No B05, real A/B composition, frontend or deployment work.
Parent phases and G-BE/G-FE/G-DELIVERY remain open/not_started.

## Entrypoints and implementation

- providers/gemini/{models,adapter,tools,transport,smoke}.py: GeminiConfig gemini-1,
  google-genai2.29.0, target gemini-3.8-flash, Developer Interactions v1beta,
  prompt intent-policy-1. Explicit credential/approval; fixed HTTPS endpoint;
  store=false/background=false/stream=false; no previous interaction ID or fallback.
- GeminiExecutor.extract: bounded stateless LOOKUP proposals, then EXTRACT JSON
  schema. Server provides context/identity catalog. Six frozen read-only tools use
  injected ContextReader/EvidenceService. No HTTP/SQL/filesystem/shell/clearance tool.
- intent/{models,validation}.py: private Candidate with uncertainty, original exact
  callsign/runway/action/condition/negation quotes and evidence. No inferred numeric
  expansion or guessed aliases. Unknown/multiple identities remain uncertain.
  Server role attestation prevents pilot readback becoming issued instruction.
- association: deterministic relationship candidates with alternatives, bounded
  timing and role/identity/content checks. No nearest-speaker forced pairing.
  Mismatching runway/action/negation and omitted/uncertain conditions cannot close
  a readback obligation. Wrong-target correction/cancellation cannot change another
  object's instruction. Matching speech never establishes physical compliance.
- memory/{models,service,store,reducer}.py: private AcceptedEvent/Invalidation and
  analysis.0003 ledger. register_memory exposes service/inventory/reconstruction/
  purge, no HTTP route/job handler. AcceptanceAccess is required, checks authority
  inside caller UOW, including duplicates and authenticated candidate/provenance.
  No permissive real implementation is installed.
- bindings/intent_memory.py: TranscriptMemoryBinding uses existing B03 raw/original
  lifecycle, local evidence validation and stable TranscriptDependency IDs. Explicit
  correction/reanalysis invalidation retains old accepted events and stale dependents.
  Invalidation clocks must be supplied by caller; no historical clock is fabricated.
- loops: REQUEST_RESPONSE, REPORT_EXPECTED, COORDINATION_PENDING, READBACK_EXPECTED;
  exact matching evidence and known coverage required for closure. Missing coverage
  stays UNKNOWN. Cancellation/supersession are not successful evidence closure.
  Report clear can satisfy an eligible report obligation but movement remains
  NOT_EVALUABLE. Timers use synthetic-no-deadline-1, expected_window_ms=null.
- testing.intent_memory is an executable disposable MOCK acceptance harness.
  Tests remain evaluator-only; runtime/provider/observer tools import no evaluator
  truth. No new background process/server/worker is left running.

## Limits and failure behavior

Defaults: provider30s/call,120s total,2 extra transient retries,2 concurrent calls,
8 calls maximum,64KiB request/response,8192 output tokens,65536 conservative reserved
tokens per extraction;4 tool rounds/8 invocations,64KiB total tool data,5s/tool.
Reservations include UTF-8 request/policy/schema bytes plus output cap, including
failed attempts. Platform reserve callback owns monetary pricing/rights/job budget;
unknown actual usage remains null. Configured maxima do not guarantee all rounds
fit the token budget. Tests use smaller output caps for small tool-driven fixtures.

Actual SDK fault testing found attempts0 becomes1 and allows an extra request.
SingleSendTransport rejects second sends per reservation, disables HTTP transport
retries/redirects/environment endpoints, and caps streamed response bytes. 503 SDK
test verifies exactly one HTTP-MOCK send. API retry is then application-owned with
fresh reservation. Oversized, unreserved and wrong-endpoint sends fail closed.

Cancellation/timeout reap async request tasks. Refusal, malformed JSON, unsupported
tool arguments, unavailable provider, partial responses and budget failure have safe
codes. Partial lookup/provider status remains PARTIAL in final output. Raw exceptions,
credentials, source payloads and thought traces are not diagnostics. Executor itself
has no accepted-state write port. Acceptance validates after server authority checks;
stale/late/cancelled/revoked attempts require rejection by that authoritative port.

Frozen synchronous context/evidence ports require bounded thread-safe adapters;
Python cannot forcibly stop an uncooperative injected IO thread. Tool await and all
evidence lookups are bounded; late data cannot reach acceptance. This limitation is
not a claim of production thread recovery. All supplied MOCK adapters terminate.

## Persistence and semantic evidence

Ledger rows have scoped run/revision FKs, input-hash validation, immutable IDs and
JSON constraints. Connection/UOW guard is injected; repository opens no DB. Domain,
evidence/audit/events rollback together. Fresh install, upgrade from analysis.0002,
FK checks, omitted commit, audit failure, scoped purge, closed-repository guard,
restart and duplicate authority checks are exercised. No implicit parent creation.

Independent expected outcomes cover interleaving/similar callsigns, competing targets,
late/overlapping timing, runway discrepancy, missing negation/condition, wrong-target
correction, cancellation, delayed readback, unknown coverage and report clear.
Same accepted events/reducer memory-1 reconstruct identically under permutations
and restart. AS_KNOWN excludes future/unknown availability; DEBRIEF retains its label.
Invalidations preserve historical events and propagate stale dependency information.
Said/readback/report/movement/reviewer remain independent; no absence-to-compliance
transition exists. Local oracles are tests, not an audited benchmark or domain review.

## Gemini verification — published support versus account access

Official [model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
publishes stable gemini-3.8-flash with structured outputs and function calling.
Official [Interactions overview](https://ai.google.dev/gemini-api/docs/interactions-overview)
and [getting started](https://ai.google.dev/gemini-api/docs/get-started) document
Developer Interactions/stateless store=false and structured JSON. These are published
capabilities, not evidence of access for this user's account.

Official [SDK repository](https://github.com/googleapis/python-genai),
[SDK package metadata](https://pypi.org/project/google-genai/2.29.0/) and installed
metadata verify2.29.0/requires-python>=3.10. Python3.12.15 installation and real SDK
serialization/usage/503 behavior pass locally through HTTP MockTransport only.
No native function tools are enabled; strict ToolRequests are separate schema
proposals executed by the server. No provider continuation/thought state is needed
for this workflow. Local async cancellation does not guarantee remote billing stops.

[Google API terms](https://ai.google.dev/gemini-api/terms) distinguish paid/unpaid
data handling. store=false is not a zero-retention/residency guarantee. Explicit
identity/model access/quota/synthetic rights/terms/paid approval/budget are required
before real adapter construction. No credential lookup or paid API call was made.

Default `python -m flowlens.providers.gemini.smoke`: BLOCKED, provider_calls0,
GEMINI_EXTERNAL_ACCEPTANCE_PENDING, benchmark_metrics=null, pipeline_ready=false.
This CLI is a readiness inspection; an approved actual account compatibility smoke
has not been run. Real Gemini calls0; standalone B04 harness MOCK provider calls2.
HTTP-MOCK SDK sends are test traffic, not real Gemini calls or provider acceptance.

## Actual checks

Commands run using .venv/Scripts Python3.12 and uv. FFmpeg9.0.2 is added only to
the regression process PATH. Historical counts are not reused as session evidence.
| Check | Actual result |
| --- | --- |
| Before source edits: pytest tests/analysis tests/contracts --track B -q | 500 PASS, no skips (44.12s) |
| Final pytest tests/analysis tests/contracts --track B -q | 589 PASS, no skips (45.06s), including89 B04 cases |
| Focused B04 before final loop revision | 88 PASS (7.36s); final superseded-loop case passes within final589 |
| pytest tests/contracts --track A -q | 66 PASS (4.29s) |
| flowlens.testing.intent_memory | PASS; MOCK calls2 / real0; disposable-cleaned; readiness false |
| flowlens.providers.gemini.smoke | BLOCKED; provider_calls0; metrics=null |
| Ruff check backend tests scripts | PASS |
| Ruff format --check backend tests scripts | PASS:97 files |
| Native Windows scoped B mypy | PASS:49 source files |
| Full backend mypy --platform linux | PASS:74 source files |
| Native scoped scripts/stt_scoring.py mypy | PASS:1 file, preserved B03 evaluator |
| Full native Windows mypy | Seven pre-existing A POSIX errors in database.py/bootstrap_admin.py;74 checked, no B errors |
| flowlens.contracts.generate --check | PASS; no schema/OpenAPI drift |
| Bandit -r backend/flowlens -ll | PASS: zero issues at all severities |
| pip-audit --local | No known vulnerabilities; unpublished editable atc-flowlens itself not on PyPI/skipped |
| uv build --out-dir artifacts/reports/b04-dist | PASS: sdist and wheel |
| git diff --check | PASS |

Scoped B mypy includes analysis/audio/workers/audio/providers/bindings/intent/
association/memory/loops and testing/{analysis,audio_worker,stt,transcripts,stt_worker,
intent_memory}. Full native Windows failure is isolated to existing Package A
O_NOFOLLOW/flock/LOCK_EX/LOCK_NB/geteuid references; A source was not changed.
No real smoke, held-out benchmark, expert review, real host/composition or deployment
is claimed. Existing STT regressions/scorer run within the full B suite.

## Contract gaps and next acceptance

Frozen ProviderAdapter/JobResult lack these private typed intent/provenance records;
no data is hidden in Usage/text/reason. Private ledger/projection fields do not extend
public contracts. Evidence lacks availability metadata, so authoritative resolve
must enforce server as-of/rights against source records. Active policy evidence
without bounded/known support is unavailable. Source aliases/roles/coverage must
be supplied from permitted server records, not model claims or diarization guesses.

Real integration must reconcile private artifact codec/ACL/TTL/promotion, durable
attempt/lease/cancellation/receipt/result hashes and atomic job handler, accepted
public MemoryEvent/OpenLoop/Snapshot adapters and transport. These are Phase10
requirements; registration remains unready. Frozen schema changes require an
explicit version/reconciliation decision.

External owners and next actions:

| Blocker | Owner | Evidence required / next action |
| --- | --- | --- |
| STT_ACCOUNT_LOGIN_REQUIRED | Cloud operator/user | Approved account/profile/identity/API/quota/rights/budget; then approved synthetic STT smoke |
| AUDITED_BENCHMARK_PENDING (B03) | Annotation/evaluation lead | Actual audio audit, held-out labels, frozen protocol/thresholds and real outputs; run existing scorer |
| GEMINI_EXTERNAL_ACCEPTANCE_PENDING | Cloud operator/user | Approved account/API key/tier/model access/terms/rights/quota/price/budget and paid-request approval; run actual structured/schema/timeout compatibility smoke |
| B04 held-out semantic benchmark | Evaluation/domain lead | Audited speech-act/association/loop labels, interleaving/condition/negation cohorts, wrong-pair/abstention/closure metrics and real provider outputs |
| Real integration | Platform and analysis owners | Phase10 authority/artifact/receipt/projection adapters and integrated acceptance |

Research output remains NOT_DOMAIN_VALIDATED. MOCK passes do not close B03/B04 or
backend/frontend/delivery gates. Architecture rationale: [ADR0005](../adr/0005-application-owned-intent-memory.md).

## External acceptance tetap pending — 9 Oktober 2026

**B04_EXTERNAL_ACCEPTANCE_PENDING**
- GEMINI_ACCOUNT_ACCESS_UNVERIFIED
- REAL_GEMINI_SMOKE_PENDING
- AUDITED_SEMANTIC_BENCHMARK_PENDING

B04 / Phase8: `in_progress`; local engineering + standalone MOCK acceptance:
passed. Real Gemini provider_calls: **0**. Real smoke: **NOT_RUN**.
Audited semantic benchmark: **BLOCKED**; benchmark metrics: **null**.
Integrated pipeline readiness: **false**.
Existing **GEMINI_EXTERNAL_ACCEPTANCE_PENDING** tetap terlihat dan belum ditutup.

**B03_EXTERNAL_ACCEPTANCE_PENDING**
- STT_ACCOUNT_LOGIN_REQUIRED
- AUDITED_BENCHMARK_PENDING

B03 / Phase7: `in_progress`; local standalone acceptance dipertahankan.
Real STT calls: **0**; real smoke **NOT_RUN**; audited benchmark **BLOCKED**,
metrics **null**. Izin engineering lokal B05 mengubah sequencing saja.
