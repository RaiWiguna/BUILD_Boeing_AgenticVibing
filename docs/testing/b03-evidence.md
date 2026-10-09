# B03 — Google STT V2 and transcript lifecycle evidence

## Current acceptance flag — user-authorized B04 sequencing (9 October 2026)

**B03_EXTERNAL_ACCEPTANCE_PENDING** — reasons **STT_ACCOUNT_LOGIN_REQUIRED** and
**AUDITED_BENCHMARK_PENDING**. User confirms no Google Cloud account yet and explicitly
authorizes independent B04 engineering while B03 remains incomplete. B03/Phase7
status stays `in_progress`; D1/D2/D3/offline scorer engineering acceptance retained.
Real smoke remains unexecuted/provider_calls0; empirical benchmark BLOCKED/metrics=null.
Account/login alone will not supply audited labels, held-out audio or real outputs.

This is a sequencing exception, not an acceptance waiver or paid-request approval.
B04 may use MOCK transcript fixtures/injected frozen ports before real STT exists.
Cloud smoke and audited benchmark remain required B03 follow-up; real composition
stays Phase10. Frozen1.0.0/readiness false/parent gates unchanged. Documentation-only
decision; no new application tests or cloud calls executed in this update.

## Latest engineering continuation — offline scoring completion (9 October 2026)

Audit began with git status/branch/HEAD/upstream/diff-stat/full tracked diff.
HEAD and upstream remain `da279281f1698197df1efef569f578adb1610cef` on
`feat/backend-rai`. D3/tooling/docs already dirty/untracked at entry were read and
preserved, along with docs/pitch, tests/browser and tmp. No Git mutation, Package A
edit, frozen-contract/schema change, handler registration or B04 work.

**D1/D2/D3 standalone acceptance retained. B03 and Phase7 remain in_progress.**
The proven local gap was an absent scorer/artifact loader, not the accepted STT
adapter/lifecycle/private boundary. `scripts/stt_scoring.py` now supplies strict
waveform-label/receipt/bundle schemas, bounded hash-checked private artifact loading,
review/adjudication/source/channel/range/scope validation, B02/protobuf reconstruction,
session/family/speaker/source/chunk split-leak prevention and all14 cohort checks
(condition added to the plan). Unit arithmetic covers WER S/D/I/denominators, lexical
critical-slot errors/ambiguity and independent word/segment start/end error statistics,
missing timing, clipped exclusion and unknown clocks. Details and commands:
[waveform/scoring protocol](../../evaluation/protocols/stt-evaluation.md).

`scripts/evaluation_stt.py --bundle` can score reviewed artifacts atomically, while
the default plan remains BLOCKED/metrics=null. TEST_ONLY labels cannot enter this
benchmark path. Receipt enums/attestations are operator evidence, not cryptographic
Google authentication; reconstruction proves consistency only. All new arithmetic/
SDK-projection inputs are explicitly TEST_ONLY. No waveform labels, held-out corpus,
real outputs, quality metrics or domain review were invented. Scorer engineering is
implemented; empirical benchmark acceptance is still open.

### Verification of this continuation

Initial baseline without FFmpeg PATH:425 pass/2 fail/5 skip, both failures
AUDIO_BINARY_MISSING. After process-local tool PATH, before source edits:432 PASS
without skip. Binary versions9.0.2 and hashes match B02.1; Python3.12.15, uv0.12.23,
SDK2.41.0. No package/lock changes. Intermediate new evaluator tests caught a range
conversion defect (backend Offset carries schema_version, evaluator Range does not);
fixed using explicit start/end fields, retaining both schemas' strict validation.
Final checks on this continuation:

| Command/check | Actual result |
| --- | --- |
| pytest tests/analysis tests/contracts --track B -q --tb=short (FFmpeg PATH process-local) | 500 PASS, no skip; baseline432 +68 new scorer tests |
| pytest tests/analysis/test_stt_scoring.py tests/analysis/test_stt_evaluation.py --track B -q | 71 PASS on final evaluator source, including final freeze guard |
| pytest tests/contracts --track A -q | 66 PASS |
| python -m flowlens.testing --track B; .analysis; .audio_worker; .audio_worker --real; .stt; .transcripts; .stt_worker | All7 PASS; disposable resources cleaned; real FFmpeg explicitly identified; cloud calls0 |
| ruff check backend tests scripts; ruff format --check backend tests scripts | PASS;78 files formatted |
| Native B mypy audio/workers/analysis/providers/stt/bindings +5 B harnesses | PASS32 files |
| mypy --platform linux | PASS56 backend files; static Linux target, not Linux execution |
| mypy scripts/stt_scoring.py | PASS1 evaluator file |
| Full native Windows mypy | Same7 pre-existing POSIX attribute errors in A storage/sqlite/database.py and cli/bootstrap_admin.py; no A edits |
| python -m flowlens.contracts.generate --check | PASS; frozen schemas unchanged |
| bandit -r backend/flowlens -l; bandit scripts/stt_scoring.py scripts/evaluation_stt.py -l | PASS0 issues; existing6 backend suppressions retained; no evaluator suppressions |
| pip_audit --local | No known vulnerabilities; unpublished atc-flowlens skipped |
| uv build --python .venv/Scripts/python.exe --out-dir artifacts/reports/b03-scoring-dist | PASS sdist/wheel; runtime package contains no evaluator truth |
| git diff --check | PASS |

New tests exercise exact S/D/I/empty denominators/repetition/normalization, critical
condition/negation ambiguity, insertions inside slot spans, independent timing
statistics/missing/unmatched/unknown-clock outcomes, bounded file and JSON loading,
path escape, duplicate JSON keys/nonfinite values, label/reviewer/range constraints,
all five split-leak identities, source/scope/receipt mismatch and SDK reconstruction
tampering. TEST_ONLY SDK projection is consistency testing only; no actual waveform
quality or successful real-origin benchmark loading claimed. CLI invalid artifacts
emit BLOCKED/metrics=null with safe diagnostics; subprocess imports prove runtime
does not load evaluator modules. Final source adds label-adjudication-before-freeze
and execution-after-freeze checks; descriptive scoring never closes a gate.

No persistent process/server/container was started. Harnesses cleaned their own
SQLite/audio/channels/subprocesses; normal pytest retention and ignored toolchain/
build/preflight reports remain. Existing user folders and all previous changes were
preserved. No approved provider profile or reviewed corpus became available.

### Rechecked cloud prerequisites and external ownership

Local gcloud status-only inventory:0 accounts/0 active, standard ADC absent; all7
project/location/credential/model/language/recognizer/budget env names absent. No
token request, credential read, authenticated cloud-setting audit, provisioning or
paid RPC. Project/API/IAM/recognizer/model/locale/region/endpoint/features/quota/
billing/budget/logging remain UNKNOWN. Default smoke:BLOCKED/provider_calls0;
safe report `artifacts/reports/b03-smoke-preflight.json`. Default evaluation:
BLOCKED/metrics=null; safe report `artifacts/reports/b03-evaluation-preflight.json`.
Actual FFmpeg->MOCK SDK remains separate from real Google execution.

Official Google pages rechecked9 October2026:
[Recognize V2/IAM](https://docs.cloud.google.com/speech-to-text/docs/reference/rest/v2/projects.locations.recognizers/recognize)
requires speech.recognizers.recognize and cloud-platform scope;
[quotas](https://docs.cloud.google.com/speech-to-text/docs/quotas) retains10MB/60s
inline synchronous limits and project-shared regional quotas;
[Chirp3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3) supports
Recognize and en-US with published US/EU availability, but account-specific feature
approval still requires the [locations check](https://docs.cloud.google.com/speech-to-text/docs/locations).
[WordInfo](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.types.WordInfo)
warns timing accuracy varies; Chirp3 word confidence is not a correctness probability.
[SDK async client](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.services.speech.SpeechAsyncClient)
exposes retry/timeout; existing explicit retry=None/bounded attempts retained.
[Pricing](https://cloud.google.com/speech-to-text/pricing) describes per-request
whole-second rounding and separate channel charging; no unapproved price assumed.
[Setup](https://docs.cloud.google.com/speech-to-text/docs/setup),
[IAM](https://docs.cloud.google.com/speech-to-text/docs/iam) and
[data logging](https://docs.cloud.google.com/speech-to-text/docs/v1/data-logging)
describe identity/API/billing and project opt-in logging. Published default logging
behavior does not verify this account. No zero-retention or account-compatibility claim.

| Owner/blocker | Required evidence / next action | Acceptance impact |
| --- | --- | --- |
| Cloud/platform operator: approved identity/profile/budget absent | Verify project/API/IAM/model/locale/region/endpoint/recognizer/features/quota/billing/logging; provide approved local credential/profile plus synthetic-transfer and maximum-cost authorization; then one opt-in real smoke | Real smoke open; calls0 |
| Annotation/review lead: audited labels and held-out audio absent | Acquire licensed independent sessions/families/speakers; audit actual waveform with two reviewers/adjudication; freeze labels/protocol/thresholds before execution; supply private bundle with real outputs/receipt | Empirical WER/slots/timing benchmark BLOCKED; metrics=null |
| Paket B | Maintain tested offline scorer; validate supplied artifacts and run descriptive benchmark after review | Local scorer no longer waiting for corpus to be implemented |
| A+B Phase10 | Authenticated bounded ports, durable coordinator/reservation/receipt, private staging ACL/promotion/TTL/cleanup and atomic handler composition | Separate real integration; not circular dependency for B03 standalone |

Frozen1.0.0/readiness false retained. JobResult.artifacts can carry private JSON_REPORT
without schema extension; ProviderAdapter typed AuthorizedChunk/private return,
unknown-clock wire representation and correction counters still need explicit
Phase10 reconciliation/version decision if extended. No placeholder API/handler.

## Previous continuation — standalone private boundary (9 October 2026)

Git audit: `feat/backend-rai`; HEAD and `origin/feat/backend-rai` both
`da279281f1698197df1efef569f578adb1610cef` (`feat: add audio worker and STT transcript
lifecycle`). Earlier uncommitted-base descriptions below are historical evidence,
not the current Git state. Start-of-session tracked tree clean; existing untracked
docs/pitch, tests/browser and tmp preserved. No stage/commit/push/merge/reset/clean.

**B03.D1/D2 retained; B03.D3 standalone acquisition/submission/revalidation completed.
B03 overall remains partial/in_progress: real smoke and audited benchmark are open.
Real A/B composition stays Phase 10, not a prerequisite for D3 acceptance.**

### Implemented boundary and ownership

- `providers/stt/adapter.py`: existing authorization/audio validation extracted into
  reusable functions; executor behavior retained. No remapping/timing/dedup rewrite.
- `providers/stt/execution.py:execute_attempt`: injected ChunkAccess + frozen
  AssetAccess, executor, authoritative checkpoint and per-RPC budget callback.
  Rights/scope/config/stage/index/size preflight before download; 64KiB range blocks,
  strict type/length/checksum/WAV checks; monotonic whole-attempt timeout and lease
  checkpoints across download/RPC/upload/return; exact live attempt guarded by executor.
  No disk files, DB, evaluator or Package A imports. Caller owns heartbeat and executor
  closure. Sync port adapters must have bounded transport timeouts/cooperate; this is
  not a scheduler, hard-kill supervisor or OS resource sandbox.
- `providers/stt/provenance.py`: canonical raw JSON private artifact, <=8MiB;
  deterministic attempt/chunk UUID, SHA256/size/scope/source chunk binding,
  JSON_REPORT + `stt-private-provenance-1` + audio capability. Hypotheses/words/config/
  protobuf stay in private artifact bytes, never text/reason/Usage/wire extras.
  Decode rejects altered manifest, noncanonical/duplicate-key JSON and reconstructs
  every raw field via original protobuf + authoritative B02 audio/metadata/config.
  This proves self-consistency, not a cryptographic Google response signature.
- `bindings/stt.py:PrivateTranscriptIngest`: standalone API-side binding, outside
  pure domain and worker modules. Injected AcceptanceAccess must authenticate staged
  artifact ownership/scope and resolve active job/attempt/lease/input revision/config/
  rights **inside caller UOW**, on every replay. Local checks also reject expired
  leases and mismatched contexts; existing TranscriptLifecycle checks/evidence/audit/
  event writes remain in that UOW. Exact duplicate preserves first recorded_at and
  writes no duplicate state; unknown-clock raw yields no invented public segment.
  Caller owns explicit commit and final job transition/receipt. No handler or HTTP
  route registered; there is no real coordinator/promotion implementation here.
- `testing/stt_worker.py`: executable MOCK in-memory transport/authority plus real
  disposable SQLite acceptance/restart. Actual process import isolation tested.
  Prototype file placement failed existing AST import rules; moved binding/execution
  to their appropriate modules, leaving existing boundary assertions unchanged.

Upload generator is explicitly closed on success/failure, and complete consumption
is required (including consumer-close/early-return negatives). Worker creates no
scratch files. Remote partial/staged bytes are platform-owned: TTL/promotion/cleanup
must be reconciled at Phase 10; frozen AssetAccess has no delete/abort port. Restart
uses fresh attempt/lease and distinct artifact/raw IDs; accepted chunk uniqueness
prevents a second accepted record. Same-attempt billing across a crashed/restarted
process is not exactly-once; durable retry/reservation/idempotency remains coordinator
authority. Mock staging is cleared by the harness's mock platform after completion.

### Actual continuation checks

Python3.12.15 `.venv/Scripts`, uv0.12.23, SDK2.41.0 (`Requires-Python >=3.10`),
frozen contracts1.0.0, pyproject/uv.lock/generated schemas unchanged. FFmpeg/ffprobe
versions9.0.2 and binary hashes rechecked against B02.1 (match); PATH process-local.
Waveform and synthetic manifest hashes rechecked (match historical hashes below).

| Command/check | Actual result |
| --- | --- |
| Baseline pytest tests/analysis tests/contracts --track B -q | 359 PASS, no skip, before source edits |
| Final same suite --tb=short | 432 PASS, no skip (original359 + new73) |
| New boundary/smoke/evaluator suites | 73 PASS:58 boundary +12 smoke +3 evaluator |
| pytest tests/contracts --track A -q | 66 PASS |
| python -m flowlens.testing --track B; .analysis; .audio_worker; .stt; .transcripts | PASS standalone MOCK; provider_calls0 |
| python -m flowlens.testing.audio_worker --real | PASS actual FFmpeg subprocess, cleaned; provider_calls0 |
| python -m flowlens.testing.stt_worker | PASS MOCK SDK/private artifact/UOW/restart; disposable-cleaned; readiness false |
| ruff check backend tests scripts; ruff format --check backend tests scripts | PASS;76 files formatted |
| mypy B audio/workers/analysis/providers/stt/bindings + five B harnesses | PASS32 native Windows files |
| mypy --platform linux | PASS56 files; static Linux target, not Linux runtime proof |
| Full native Windows mypy | Same7 existing POSIX API errors A; no A source edits |
| python -m flowlens.contracts.generate --check | PASS unchanged frozen schema |
| bandit -r backend/flowlens -l | PASS0 issues; existing6 suppressions unchanged |
| pip-audit --local | No known vulnerabilities; unpublished project skipped |
| uv build --python .venv/Scripts/python.exe --out-dir artifacts/reports/b03-closure-dist | PASS sdist/wheel |
| git diff --check | PASS |

New tests prove candidate hypothesis/word/timing/config/preparation/SDK/status/hash/
manifest tampering rejection; scope/owner/input/config/asset/stage/rights negatives;
late/cancelled/stale/changed-attempt rejection even on duplicate replay; atomic
evidence/audit/event/no-commit rollback; fresh attempt/restart uniqueness; partial/
early/closed consumer cleanup; whole-attempt download timeout; unknown clock and
safe subprocess diagnostics/import isolation. Original deterministic/real FFmpeg
regressions retain their independent timing and failure assertions.
Intermediate new-test failures used a wrong plural table name and stale MOCK evidence
after fresh attempt; corrected harness expectations, not production constraints.
Lint/Bandit issues in new harness corrected with explicit checks; no new suppressions.

### Real provider smoke — BLOCKED, zero real calls

Reusable entrypoint: `python -m flowlens.providers.stt.smoke`. Default performs no
credential loading or RPC and emits safe JSON. Actual result: BLOCKED,
APPROVED_PROFILE_UNAVAILABLE/CREDENTIALS_UNAVAILABLE, provider_calls0, readiness false.
Safe report: ignored `artifacts/reports/b03-smoke-preflight.json`.

Explicit `--profile <local-approved-json> --credentials <local-credential-file>`
performs attestation preflight only; `--execute` additionally opts into the single
paid request. Local profile schema is `SmokeProfile.model_json_schema()`; it requires
STTConfig, ProviderApproval (matching config digest), quota/rights attestations,
positive budget and operator conservative per-second price including rounding.
Require max_calls1/max_attempts1/timeout<=30s and budget>=9 seconds at that price.
Only pinned synthetic hold-short and its pinned rights manifest are eligible; real
FFmpeg prepares one mono16kHz PCM16 chunk. Credentials are explicit/injected, never
implicit ADC. Budget reservation is per invocation, not a project-wide cost ledger.
Safe output includes SDK/API/Python/config hash, status, call count, latency/usage/
reserved budget and response hash; actual billed cost remains unknown. No transcript,
audio, credentials or private paths printed. RPC failure retains attempted call/
audio/reservation counters; transport cancellation does not reverse billing.

Presence audit: all seven previously listed config/credential/budget env names absent;
standard ADC absent. **gcloud524.0.0 is installed**, `gcloud auth list` status-only
inventory finds0 credentialed accounts/no active account; no token was requested.
This is local credential inventory, not an authenticated audit of cloud settings.
API enablement/IAM/project/recognizer/features/quota/billing/logging remain UNKNOWN.
No provisioning/API enablement/logging/billing changes or cloud request performed.
The real-preparation smoke test injects MOCK SDK explicitly; it is actual FFmpeg
plumbing evidence only and never real Google success.

Official Google sources rechecked on9 October: [Recognize/IAM/response](https://docs.cloud.google.com/speech-to-text/docs/reference/rest/v2/projects.locations.recognizers/recognize),
[Chirp3 models/locales/features](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3),
[locations](https://docs.cloud.google.com/speech-to-text/docs/locations),
[quotas10MB/60s](https://docs.cloud.google.com/speech-to-text/docs/quotas),
[channel/decoding](https://docs.cloud.google.com/speech-to-text/docs/multi-channel),
[WordInfo offsets/unset confidence](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.types.WordInfo),
[async timeout/retry](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.services.speech.SpeechAsyncClient),
[account setup](https://docs.cloud.google.com/speech-to-text/docs/setup),
[opt-in logging terms](https://docs.cloud.google.com/speech-to-text/docs/v1/data-logging-terms).
Published compatibility is not account compatibility or region approval; MOCK
mock-project/us/en-US/chirp_3 remains no release profile.

### Evaluation and external blockers

`evaluation/protocols/stt-evaluation.md`, `stt-plan.json` and
`scripts/evaluation_stt.py` prepare corpus/split/provenance/annotation/cohort audit.
Actual preflight BLOCKED/metrics=null; report in ignored
`artifacts/reports/b03-evaluation-preflight.json`. Two manifest entries mean one
NOT_GOLD tuning waveform and one **planned, absent** held-out acquisition. No cohort
coverage claimed. Requires two waveform reviewers, adjudication, source/range/channel/
ambiguity labels and separate domain review; hashes alone cannot unlock scoring.
No WER, critical-slot accuracy or timestamp quality reported. Actual scorer and
held-out benchmark remain open until audited artifacts/real outputs exist.

| Blocker/owner | Impact | Required evidence and next action |
| --- | --- | --- |
| Cloud/platform operator: no approved profile/identity | Real7.1/7.4 cannot pass | Verify project/API/IAM/model/locale/region/recognizer/features/quota/billing/logging/price/budget; supply approved local config/credential, then opt-in synthetic smoke |
| Evaluation/annotation lead: labels/held-out corpus absent | Quality7.4 cannot pass | Acquire rights-cleared independent held-out families; two waveform reviewers/adjudication; freeze label/source/split hashes and thresholds; B implements scoring on audited artifacts |
| A+B at Phase10: real transport/coordinator/staging policy | Real integration not yet demonstrated | Implement authenticated bounded ChunkAccess/AcceptanceAccess, durable checkpoint/budget/receipt and artifact promotion/TTL within shared UOW; run real A/B acceptance |

Frozen `JobResult.artifacts` **can** reference the private JSON_REPORT; no frozen
schema change is needed for this standalone transport. It has no typed raw field;
ProviderAdapter.transcribe lacks AuthorizedChunk/private return, and unknown session
time/correction counters still lack wire representation. Exact codec/transform,
private artifact access, usage/output-hash/receipt semantics, TTL and handler wiring
require Phase10 reconciliation; a breaking typed extension needs a version decision.
See ADR0004 continuation. No handler registered merely because an artifact uploaded.

Next unit remains **B03 real-profile/smoke + annotation/scoring closure**, not B04.
Readiness false; B03/Phase7/PaketB and G-BE/G-FE/G-DELIVERY not advanced. No persistent
server/daemon/container started. Task channels, subprocesses, disposable DB/audio
scratch closed/cleaned; ignored toolchain/build/preflight reports retained. Pytest
temporary files follow pytest retention. No Package A or existing test edits.

## Historical adapter/lifecycle implementation record

Date: 9 October 2026; branch feat/backend-rai; base SHA
cdb2b9dae3d16c22a524b8a05b2e5583cc48e0d0 plus existing B01/B02 working tree.
Existing user changes and untracked docs/pitch, tests/browser, tmp retained.
No reset/clean/stage/commit/push/merge. Package A implementation unchanged.

**Status: B03 partially implemented, standalone deterministic acceptance passes.
B03 and Phase 7 are NOT done.** Real Google smoke/profile readiness, audited
critical-slot/alignment benchmark and real worker/artifact/coordinator reconciliation
remain open. This evidence does not close AC-03/AC-18 or any delivery gate.

## Audit and baseline

Read rules/PRD STT, permission/clock/evidence/correction/stale/job/security/recovery
requirements; roadmap §6 and Phase7; handoff; package execution; B01/B02 evidence;
ADR0002/0003; baseline/structure/shared contracts, current B code/models/ports/
registration/harnesses/tests, contract examples and synthetic manifest.

Baseline before source edits: Python3.12.15 from .venv/Scripts; analysis+contractsB
218 PASS without skip; native B mypy17 files PASS; Linux-target backend41 files PASS.
First attempted pytest flag --contract-track was invalid; corrected to the actual
--track B flag. No test result claimed from the invalid command.

FFmpeg9.0.2 path added only to each testing process PATH:
artifacts/reports/b022-tools/ffmpeg-9.0.2-essentials_build/bin.
Actual binary checksums match [B02.1](b021-evidence.md):
ffmpeg3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec;
ffprobef0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52.
Fixture hold-short.wav hash remains
cf3baa73bc59e37ddbd16e99e8a5f7493c22057d01c02b4030585b88486ba044;
silence.wav643f8a8dc8bd9c19225afffad2becfec5426180b3749cb208abdf1a6c8354efc.
synthetic-audio.json hash37472d982c0591f32fe36897aebca727d56d5b812c82ce8f3a201cd7d24cf008.
hold-short is synthetic NOT_GOLD/NOT_DOMAIN_VALIDATED; TTS script is not pronunciation
gold. No WER, slot accuracy, alignment quality, domain or operational claim.

## Official Google verification and effective configuration

Verified 9 October 2026 against official sources and installed SDK source:

- [SDK2.41.0](https://pypi.org/project/google-cloud-speech/) supports Python3.12;
  installed/pinned through uv. types-protobuf7.35.1.20260906 added to dev group for
  strict typechecking; pyproject.toml and uv.lock updated consistently.
- [V2 quotas](https://docs.cloud.google.com/speech-to-text/docs/quotas): inline
  synchronous audio capped at10MB/60s; published regional synchronous quota300/min
  is project-shared, not a guarantee of this account's allocated quota. Mono B02
  WAV chunks meet a stricter9,999,999 byte/50s local baseline. No GCS/batch dependency.
- [V2 request](https://docs.cloud.google.com/speech-to-text/docs/reference/rest/v2/projects.locations.recognizers/recognize):
  recognizer resource path, inline content/config/config_mask; response results and
  metadata; recognize needs speech.recognizers.recognize and cloud-platform scope.
- [Recognizer configuration](https://docs.cloud.google.com/speech-to-text/docs/recognizers):
  request config can override stored defaults. Adapter config_mask=* prevents hidden
  recognizer defaults changing the effective requested features.
- [Regional features](https://docs.cloud.google.com/speech-to-text/docs/locations) and
  [supported languages](https://docs.cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages)
  require checking location/model/language/feature combinations. The code requires
  explicit operator/platform approval; it does not assert account compatibility.
- [Chirp3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3) supports
  V2 Recognize; published US/EU availability and word timestamp behavior remain
  subject to effective regional features. chirp_3 is the PRD candidate, not a frozen
  release model. MOCK tests use mock-project/us/en-US/chirp_3/recognizers/_ only.
- [WordInfo](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.types.WordInfo):
  word offsets may be absent and accuracy varies; confidence default0 is unset.
  Preserve null and AMBIGUOUS; no numeric probability/precision benchmark claim.
- [Async client](https://docs.cloud.google.com/python/docs/reference/speech/latest/google.cloud.speech_v2.services.speech.SpeechAsyncClient)
  accepts explicit timeout/retry; adapter disables SDK retries and controls attempts.
  Installed grpc transport defaults had unbounded message sizes; explicit channel
  now caps receive1MiB and send10,010,000bytes, verified with actual SDK construction.
- [Cloud setup](https://docs.cloud.google.com/speech-to-text/docs/setup) requires
  billing/API/identity. Data logging is project opt-in, not a Recognize request
  store=false switch. Approval must attest DISABLED; [logging terms](https://docs.cloud.google.com/speech-to-text/docs/v1/data-logging-terms)
  and source rights still apply. No zero-retention claim.

**Real effective provider profile: unavailable/unverified; provider calls0.**
Presence-only audit found no GOOGLE_CLOUD_PROJECT/LOCATION/APPLICATION_CREDENTIALS,
STT_MODEL/LANGUAGE_CODES/RECOGNIZER or AI_RUN_BUDGET environment value, and no standard
APPDATA/gcloud/application_default_credentials.json. No credential contents printed,
ADC/network identity lookup, cloud API enablement/provisioning, or paid call attempted.
Injected/other-host identity was not exhaustively searched. Actual API enablement,
IAM, recognizer, regional features, quota, billing authorization and logging settings
are unknown. Synthetic manifest cloud right is true; that does not supply project
authorization/budget. Owner: cloud/platform operator; required evidence: approved
effective config, identity/IAM/API/billing/quota/logging/budget and real synthetic
request result/version/latency/usage. Never send credential material through chat.

## Entry points and implemented behavior

- providers/stt/models.py: strict immutable versioned STTConfig, ProviderApproval,
  AuthorizedChunk and allowlisted STTFailure. No provider defaults for project,
  model, locale, region, endpoint, recognizer or credentials.
- adapter.py: GoogleClient(config, credentials), STTExecutor(config, client).
  await transcribe(binding, audio, checkpoint, reserve=budget_reservation) returns
  private RawTranscript plus frozen Usage; await close() cleans the client/channel.
  Checkpoint supplies current authorized lease and rejects cancellation/revocation;
  reserve must durably authorize each attempted audio duration using platform pricing.
  Explicit callbacks are mandatory; MOCK reservation functions do not prove budget
  enforcement on a real platform. Active heartbeat remains caller/coordinator-owned.
- B02 metadata/config/source hash/channel/plan/local PCM header/bytes/checksum checked;
  exact session/run/revision/input/config/owner/asset/STT stage binding; preflight rights
  and profile checks. No unrestricted source inventory, DB/writer, A internals,
  evaluator, Gemini, real composition or accepted-state write in executor.
- Private records preserve exact deterministic protobuf bytes/base64/hash, all
  alternative hypotheses/words, original config, full B02 preparation metadata and
  word local/source/session nanoseconds, channel, coverage, uncertainty and billed
  duration. Nanoseconds are representation, not accuracy. Silence is NO_SPEECH;
  missing alignment/incomplete responses are PARTIAL; malformed/overflow rejected.
- projection.py: original top hypotheses project to frozen transcript only with
  known nonnegative session clock. Unknown clock stays internal with no invented
  public timestamp; unavailable word alignment is explicit enclosing CHUNK_RANGE.
  Availability and speaker identity remain null; confidence0 remains null.
- deduplicate: exact text/time within real same-scope/channel/coverage overlap only;
  canonical words retain all raw/hypothesis/word references. Genuine repetitions and
  ambiguous/jittered/unknown boundaries retained. Bounds4096raw/65536words/1million
  comparisons. Raw/public hypothesis text retains punctuation; canonical words are
  a separate provider view, not a stitched human transcript or quality benchmark.
- analysis.0002 and analysis.transcript.{raw,revision,dependency,change} factories;
  separate register_transcripts(transactions,evidence,authority) exposes lifecycle,
  migrations/factories/purge only. Existing B01 registration/migration unchanged.
- TranscriptLifecycle: store_raw/add_original, current_segments, canonical_provider_words,
  correct, revision/validate_evidence/resolve_audio, depend/stale,
  invalidate_for_reanalysis and purge. Corrections use internal counter with actor,
  original/previous refs and reason; retain source/timing/availability. Evidence quote/
  span/range/hash/scope validated; audio link maps original chunk/asset/hash/channel.
- Raw acceptance authority callback must validate active job/lease/config/artifact
  and SDK candidate consistency in caller UOW. Exact duplicate returns existing ID;
  changed payload or duplicate chunk/revision conflicts. Cancellation/stale authority
  rejects even duplicate replay. Domain/evidence/audit/notice share caller UOW; no
  implicit commit/publication. Reanalysis invalidates old dependencies; creation of
  new run/revision remains platform-owned. Future B04/B05 must register full lineage.
- [ADR0004](../adr/0004-private-transcript-provenance.md) documents boundary/gaps.

Limits: timeout30s (<=120), concurrency2 (<=2), attempts1 (<=3 with explicit reserve
per attempt), retry delay0.25s (<=5), calls512/lifetime (<=4096), binding512KiB,
response1MiB, hypotheses256, words8192, cumulative text65536characters. Usage records
provider billed duration when present; attempted_audio_ms counts retries separately.
No fabricated cost/tokens/billing certainty. Cooperative async cancellation/poll50ms
and final deadline/lease checks; SDK RPC timeout shares total queue/retry deadline.
Callbacks must be bounded; hostile in-process synchronous callback/client cannot be
forcibly interrupted. External process supervision and OS resource sandbox are open.

## Acceptance and actual checks

Commands from workspace use .venv/Scripts tools/Python3.12, process-local FFmpeg PATH.

| Command | Actual result |
| --- | --- |
| pytest tests/analysis/test_stt.py tests/analysis/test_transcripts.py -q | 141 PASS:101STT/40lifecycle; actual FFmpeg->MOCK SDK separate |
| pytest tests/analysis tests/contracts --track B -q | 359 PASS, no skip:21B01+57audio+74worker+101STT+40lifecycle+66contracts |
| pytest tests/contracts --track A -q | 66 PASS |
| python -m flowlens.testing --track B | PASS MOCK/provider_calls0/disposable-cleaned |
| python -m flowlens.testing.analysis | PASS B01 MOCK/readiness false/disposable-cleaned |
| python -m flowlens.testing.audio_worker and --real | PASS standalone MOCK; actual FFmpeg separate, cleanup and import boundary |
| python -m flowlens.testing.stt | PASS MOCK SDK1/provider_calls0/readiness false |
| python -m flowlens.testing.transcripts | PASS MOCK SQLite/correction/stale/restart/audio link/disposable-cleaned |
| ruff check backend tests scripts; ruff format --check backend tests scripts | PASS on final inputs |
| mypy B audio/workers/analysis/providers/stt and four B harnesses | PASS26 files native Windows |
| mypy --platform linux | PASS50 backend files; static target, not Linux runtime proof |
| mypy whole native Windows | unchanged7 POSIX API errors in A database/bootstrap_admin; no B errors |
| python -m flowlens.contracts.generate --check | PASS, no frozen schema drift |
| bandit -r backend/flowlens -l | PASS zero issues; two existing subprocess and four static-table SQL suppressions documented inline |
| pip-audit --local | no known vulnerabilities; unpublished project itself skipped |
| uv build --python .venv/Scripts/python.exe --out-dir artifacts/reports/b03-dist | PASS sdist+wheel; uv0.12.23 |
| git diff --check | PASS |

Tests cover strict config and SDK mapping, unauthorized/undetermined rights, project
approval, full binding negatives, bad metadata/audio, nonfinite confidence and bad
protobuf duration/order/range/channel/language/billing, unknown clock/silence/partial/
gap/channel/short chunk, conservative dedup/repetition/ambiguity, budgets before retry,
quota/denial/transient timeout/cancellation/lost lease, concurrency, fresh attempts,
bounded output/calls, actual SDK channel construction/closure, safe exception codes,
provider AST+actual subprocess import inventory and B02 real FFmpeg bridge.
Persistence tests cover migration upgrade/FKs, exact duplicate recovery, current
correction chain/optimistic conflicts, grants, evidence quote/span/hash/scope/time,
raw immutability through ports, stale state/reanalysis/restart, original source audio
links, shared UOW domain/evidence/audit/event rollback, cancellation/late/stale result
and safe ledger metadata. MOCK authority is explicit, not a real durable coordinator.

Intermediate tests found a wrong prepare_audio argument, eager package SQLite import,
and a wall-time-dependent cancellation fixture; fixed API use, lazy registration,
and synchronized interruption after RPC starts. One later local rerun omitted the
process-local FFmpeg PATH and failed AUDIO_BINARY_MISSING; rerun with correct PATH.
No assertions weakened, provider mock relabelled as real, unexpected skips accepted,
or Package A portability work performed. Final result table supersedes these runs.

## Open scope, cleanup and next unit

No production CLI STT worker/JobClient transport/download/artifact staging/promotion
or STT JobResult handler: frozen provider/result signatures cannot carry private
records. Phase10 must reconcile authorized chunk acquisition, response revalidation,
private artifact manifest/promotion and accepted coordinator integration. Do not
smuggle provenance into unrelated DTO fields or register success placeholders.
Readiness false and frozen1.0.0 unchanged. B03/Phase7/PaketB/G-BE/G-FE/G-DELIVERY open.

Real STT smoke0; model/region approval unverified. No manual pronunciation audit,
held-out semantic/critical-slot/timestamp benchmark or operational validation.
Public unknown-clock transcript support, calibrated jitter dedup/stitched transcript,
run/input-revision mutation APIs and downstream reducers remain open reconciliations.
No claim to implement full frozen AnalysisRepository methods belonging to B04/B05.

All task RPC mocks/channels/subprocesses/database connections closed; standalone
harness disposable DB directories and audio scratch cleaned. Pytest retains its
framework-managed temporary test files under its normal retention policy.
No persistent daemon/server/container started. Ignored toolchain/build/security report
artifacts retained for inspection. Old B01 failed tempdirs and user folders untouched.
Next **B03 closure**: operator-approved GCP profile/budget/rights, real synthetic smoke,
audited labels/benchmark, and worker/artifact boundary reconciliation. B04 remains
planned until its B03 prerequisites are fulfilled; A03.1 remains independent.
