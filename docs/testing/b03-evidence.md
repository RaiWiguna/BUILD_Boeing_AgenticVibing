# B03 — Google STT V2 and transcript lifecycle evidence

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
