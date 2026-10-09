# Session Handoff — ATC FlowLens

| Atribut | Nilai |
| --- | --- |
| Tanggal | 9 Oktober 2026 |
| Objective | B05 local engineering/standalone MOCK accepted; B04 tetap in_progress; external acceptance open; B03 external acceptance tetap pending; konteks B01/B02/B03 dan A02.2 dipertahankan |
| Status | Phase0–1 done; A01/A02 dan Phase2.1/2.2 done; Phase2 in_progress; B01/B02.1 done; B02.2/6.4 done untuk standalone MOCK acceptance; B03 in_progress (D1/D2/D3 standalone accepted); B04 in_progress (local MOCK accepted); B05 in_progress (local standalone MOCK); B06 in_progress (acceptance lokal); contract1.0.0 |
| Candidate | HEAD/upstream feat/backend-rai = 5beeffd5726aae0321574ba8e302d47db6c46171 sebelum continuation; evaluator/package/capacity/compatibility continuation siap di-commit setelah final checks |
| Next focus | External B03/B04 smoke dan audited/domain B05 acceptance terbuka; Linux runtime bila host tersedia; real A/B transport Phase10 belum dimulai; A tetap A03.1 independen |
| Gate | G-BE, G-FE, G-DELIVERY: not_started |

## Handoff terkini — B05 local engineering, 9 Oktober 2026

B05 in_progress; local standalone MOCK acceptance tersedia. `advisory/` memuat
findings-1, evidence-bound provider selection advisory-select-1, append-only
analysis.0004 ledger, review/version/idempotency/reanalysis/journal, read-only query,
JSON/CSV/HTML private renderer, metrics/diagnostics dan injected analysis retention.
No HTTP route/job handler/public projection/real composition; readiness false.
User-authorized sequencing membolehkan B05 sebelum external B03/B04 closure.
No paid calls/provider fallback/contracts change/A implementation/frontend/deployment.
B06 acceptance lokal in_progress; parent phases/G-BE/G-FE/G-DELIVERY belum closed.

Baseline baru: 589 PASS tanpa skip setelah FFmpeg ditambahkan hanya ke PATH proses;
run awal tanpa binary: 582 PASS/2 FAIL/5 SKIP (AUDIO_BINARY_MISSING), bukan regression.
B05 focused77 PASS; final isolated full B666 PASS/no skip (58.36s), contractsA66 PASS.
Native B59/Linux-target84 mypy PASS; native Windows A POSIX7 unchanged. Ruff108 files,
schema drift/Bandit/audit/build/diff PASS. One concurrent STT cancellation timing
failure is retained in [B05 evidence](../docs/testing/b05-evidence.md), isolated rerun passes
without changing assertions/timeouts. Evidence includes persistence/security/contract gaps.
Harness B05 MOCK calls3/real0/disposable-cleaned; B04 MOCK calls2/real0 tetap PASS.
Real smoke NOT_RUN; audited external benchmarks BLOCKED/metrics=null.
Existing dirty work docs/pitch/tests/browser/tmp/D3/evaluator/B04 dipertahankan.
No stage/commit/push/reset/clean/merge/branch change; no daemon/server ditinggalkan.

Next: cloud operator menyiapkan approved STT/Gemini identity/access/rights/budget
untuk smoke nyata; evaluation/domain lead menyediakan audited held-out labels dan
thresholds/protocol. Phase10 owners mengikat authority/evidence/artifact/receipt/public
projection dan atomic coordinator. MOCK bukan evidence kesiapan pipeline.

## Previous handoff — B04 local engineering,9 Oktober2026

- Implemented private `intent/`, `association/`, `memory/`, `loops/`;
  `providers/gemini/` pinned SDK2.29.0/Developer Interactions v1beta;
  `bindings/intent_memory.py` consumes existing transcript lifecycle/dependency index.
- `analysis.0003` append-only memory ledger uses injected connection/caller UOW,
  scoped FKs, provenance, deterministic reconstruction, explicit invalidations,
  restart/rollback/purge. No worker SQLite, HTTP route or job handler installed.
- Provider LOOKUP and EXTRACT are separate stateless schema requests. Server tools
  stay read-only/scoped/bounded; no native execution/continuation history or thought
  traces persisted. Transport enforces one actual send per reservation despite SDK
  attempts0 mutation; no implicit credential lookup/fallback.
- Gemini target/API support published; account access, actual compatibility smoke,
  source rights/terms/quota/budget approval and audited semantic benchmark unverified.
  Real Google/Gemini calls0. Default Gemini preflight BLOCKED, benchmark metrics=null.
- B04 in_progress; B05 not started. B03/Phase7 in_progress with
  B03_EXTERNAL_ACCEPTANCE_PENDING: STT_ACCOUNT_LOGIN_REQUIRED,
  AUDITED_BENCHMARK_PENDING. STT smoke0, benchmark BLOCKED/metrics=null.
- Final verification: B589 PASS/no skips (89 B04), contractsA66 PASS; native B49/
  Linux-target74/scorer1 mypy PASS; Ruff/format/schema/Bandit/audit/build/diff PASS.
  Harness MOCK calls2/real0/disposable-cleaned. Commands/gaps: docs/testing/b04-evidence.md.
  Native full Windows mypy still has seven pre-existing A POSIX errors; A unchanged.
  Frozen1.0.0, integrated readiness false; parent phases/G-BE/G-FE/G-DELIVERY unchanged.
- Working tree preserved (D3/evaluator/docs/pitch/tests/browser/tmp); no reset,
  clean, stage, commit, push, merge or branch change. No daemon/server left running.

## Previous handoff — izin sequencing B04,9 Oktober2026

- Pengguna menyatakan belum memiliki akun Google Cloud dan secara eksplisit
  mengizinkan lanjut B04 sambil memberi flag bahwa B03 belum sepenuhnya selesai.
- **B03_EXTERNAL_ACCEPTANCE_PENDING**: **STT_ACCOUNT_LOGIN_REQUIRED** serta
  **AUDITED_BENCHMARK_PENDING**. B03/Phase7 tetap in_progress. D1/D2/D3/scorer lokal
  accepted; real smoke0/benchmark metrics=null. Login saja belum menutup benchmark.
- B04 next focus: engineering lokal Gemini structured intent, bounded read-only tools,
  association dan memory/open loops, dengan transcript fixtures berlabel MOCK serta
  injected frozen ports. B04 tetap planned/local start authorized sampai implementasi
  dimulai. Jangan menunggu login STT untuk pekerjaan independen yang sudah diizinkan.
- Izin ini mengubah sequencing, bukan acceptance: tidak menutup B03/B04/parent gates,
  tidak mengizinkan paid RPC, fallback model/provider, perubahan frozen contracts,
  implementasi A, Phase10 composition, frontend atau deployment. Gemini real smoke
  juga membutuhkan identity/model/API/rights/budget approval tersendiri.
- Audit Git: branch feat/backend-rai/HEAD da279281…; existing dirty/untracked work
  dipertahankan. Sesi ini hanya memperbarui roadmap/handoff/packet/evidence untuk
  keputusan sequencing dan menyiapkan prompt B04. Tidak ada source edit, test aplikasi
  baru atau runtime yang dimulai; angka test500 B/71 evaluator/66 A adalah evidence
  sesi sebelumnya, bukan test baru pada keputusan docs ini. No stage/commit/push.

## Rekam sebelumnya — B03 offline evaluator continuation (partial overall)

- Git audit aktual: branch feat/backend-rai, HEAD/upstream da279281f1698197df1efef569f578adb1610cef.
  Perubahan D3/tooling/docs lama sudah dirty/untracked ketika sesi dimulai dan
  dipertahankan bersama docs/pitch/tests/browser/tmp. Tidak ada stage/commit/push/
  reset/clean/merge, perubahan Paket A, kontrak/generated schema atau handlers.
- D1/D2/D3 tetap accepted mandiri. Gap nyata hanya readiness-only evaluator:
  scripts/stt_scoring.py kini schema label/receipt/bundle, bounded artifact/hash/
  scope/review/adjudication validation dan B02/protobuf reconstruction;14cohorts
  termasuk condition; leakage session/family/speaker/source/chunk dicegah.
  evaluation_stt.py --bundle offline; default plan tetap BLOCKED/metrics=null.
- Arithmetic WER S/D/I/denominators, lexical critical slots/ambiguity, word/segment
  start/end median/p95/max/missing timing/unknown clock diuji TEST_ONLY. Label
  TEST_ONLY/receipt MOCK tidak lolos benchmark. Tidak ada gold/held-out/output nyata
  yang dibuat atau benchmark metrics diklaim; hold-short tetap TTS NOT_GOLD.
- Baseline tanpa PATH425pass/2fail/5skip karena AUDIO_BINARY_MISSING; process-local
  FFmpeg9.0.2/hash B02.1 cocok, baseline432 PASS tanpa skip sebelum edit source.
  Semua standalone harness termasuk real FFmpeg/worker dan D3 MOCK PASS. Native B32
  dan Linux-target backend56 mypy PASS; full native Windows7 POSIX errors A tetap.
  Final B500 PASS tanpa skip, focused evaluator71/Acontracts66 PASS; scorer1-file
  mypy/Ruff/format/schema/Bandit0/dependency audit/build/diff PASS. Detail commands
  dan limitations tercatat pada latest docs/testing/b03-evidence.md.
- Cloud audit ulang: local gcloud inventory0 accounts/0 active, standard ADC false,
  tujuh env config/credentials/budget absent. Tidak membaca credential/token atau
  menjalankan paid RPC. Default smoke BLOCKED/provider_calls0. API/IAM/recognizer/
  model/locale/region/features/quota/billing/logging/budget aktual UNKNOWN.
- Blocker/owner: cloud operator approved local profile/identity/transfer/budget dan
  real execution receipt; annotation/review lead menyediakan held-out rights-cleared
  audio yang belum ada, two waveform reviewers/adjudication, frozen protocol/labels/thresholds.
  Scorer lokal sudah implemented; jalankan setelah reviewed artifacts tersedia.
- Real authenticated A/B coordinator/receipt/staging TTL/promotion/cleanup/handler
  composition tetap Phase10, bukan prerequisite melingkar B03 mandiri. Frozen1.0.0/
  readiness false; B03/Phase7/PaketB in_progress, B04 planned, parents/gates terbuka.
  Tidak ada persistent process/server/container. Detail schema/limits/trust/commands
  di evaluation/protocols/stt-evaluation.md; old evidence/handoff dipertahankan.

## Rekam sebelumnya — B03 private boundary continuation (partial overall)

- D1/D2 acceptance dipertahankan; authorization/audio validator diekstrak reusable.
  D3 standalone done: providers/stt/{execution,provenance}.py + bindings/stt.py,
  ChunkAccess/AcceptanceAccess injection, frozen AssetAccess/JSON_REPORT, bounded
  download/upload/checksum/checkpoint/budget dan full protobuf/B02 reconstruction.
  API binding memvalidasi authority di caller UOW; duplicate preserves recorded_at,
  late/cancelled/stale/fresh-attempt old result ditolak. No handler/routes/real A code.
- Partial/early/closed upload consumer ditolak dan iterator ditutup; worker tanpa
  disk files; platform owns staged TTL/promotion/cleanup. Restart fresh attempts;
  no exactly-once cloud billing claim. Pure-domain/provider/audio-worker import
  assertions tidak diubah; API binding berada di module terpisah.
- testing.stt_worker executable MOCK/disposable SQLite/restart PASS.
  providers.stt.smoke reusable default preflight BLOCKED/provider_calls0; explicit
  local approved profile/credentials + --execute untuk satu authorized synthetic
  RPC. Actual FFmpeg->MOCK SDK plumbing test terpisah dari real Google success.
- gcloud524.0.0 installed; local status-only auth inventory0/no active account,
  standard ADC/tujuh env config/credentials/budget absent. No authenticated cloud
  project/settings audit/token request/provisioning/paid RPC; real profile UNKNOWN.
- evaluation/protocols/stt-plan.json/stt-evaluation.md + scripts/evaluation_stt.py
  preflight BLOCKED/metrics=null. TTS NOT_GOLD, held-out acquisition planned only;
  audited labels/reviewers/real outputs/scorer/thresholds masih terbuka.
- Baseline359/final432 tests PASS tanpa skip, new73 PASS, contractsA66 PASS;
  all standalone/real FFmpeg harnesses PASS. Native B32 files/Linux-target56 mypy
  PASS; full native Windows same7 POSIX errors A. Ruff/format/schema/Bandit0/audit/
  uv build PASS. Latest evidence + concrete owner/blocker table: b03-evidence.md.
- Git HEAD/upstream da279281…; previous uncommitted descriptions below historical.
  Existing docs/pitch/tests/browser/tmp retained; no stage/commit/push/merge/reset/
  clean. No persistent process/container/server. Task DB/channels/audio scratch
  cleaned; ignored toolchain/build/preflight reports retained, pytest normal retention.
- Frozen1.0.0/readiness false. B03 overall/Phase7/PaketB/gates remain open;
  next B03 cloud-profile/smoke + annotation/scoring. B04 planned, A03.1 independent.
  Real Phase10 integration is not a circular dependency for standalone D3 acceptance.

## Rekam sebelumnya — Paket B B03 adapter/lifecycle (partial)

- providers/stt/{models,adapter}.py: explicit strict config/approval/authorized B02
  binding; SDK2.41.0 async V2 request/response, bounded channel/calls/output,
  permission+lease+deadline checks, mandatory per-attempt budget callback,
  concurrency2, optional bounded retry, cancellation and safe diagnostic codes.
- analysis/transcript_records/projection/store/transcripts.py: immutable private
  protobuf/raw hypotheses/config/B02 provenance, local/source/session timing,
  unknown-clock projection policy, conservative exact overlap canonical-word view,
  analysis.0002 scoped repositories and append-only actor/counter corrections,
  current revision/evidence/audio links, stale dependency/reanalysis ledger.
  Domain/evidence/audit/event share caller UOW; no commit/publication owned by B.
- Separate register_transcripts exposes service/factories/migration/purge only.
  Frozen contracts1.0.0/models/ports/generated schemas remain unchanged;
  readiness false, STT handlers/API/real A/B composition absent. Existing B01 public
  export now lazy so provider record imports cannot load SQLite writers.
- [B03 evidence](../docs/testing/b03-evidence.md) records commands/versions/acceptance;
  [ADR0004](../docs/adr/0004-private-transcript-provenance.md) records internal contract
  gaps and boundaries. MOCK attestations do not prove cloud/platform readiness.
- Baseline before source218 PASS/no skip; final combined B359 PASS/no skip,
  B03 tests141 PASS and contractsA66 PASS; standalone harnesses, FFmpeg bridge,
  mypy/security/build/schema/drift results in
  evidence. Native full Windows retains seven pre-existing POSIX errors in A.
- Presence-only environment audit: no GCP project/location/credential/STT config/
  budget values or standard ADC file. API/IAM/recognizer/quota/billing/logging unknown.
  No cloud request/credential contents/provisioning. Real smoke0; GCP profile needs
  operator verification. Test model/us/en-US settings are MOCK only.
- B03/Phase7 remain in_progress: real smoke, audited pronunciation/critical-slot/
  alignment benchmark, STT worker/private artifact promotion/coordinator contract
  reconciliation open. No fabricated unknown session times, semantic dedup tolerance,
  public stitched transcript, availability or downstream reducer implementation.
- All task mocks/RPC channels/subprocesses/SQLite/audio scratch cleaned; no persistent
  daemon. Existing changes/untracked folders preserved; no stage/commit/push/merge/
  reset/clean. B04 planned until prerequisites close; A03.1 remains independent.
  Paket B, parent phases and G-BE/G-FE/G-DELIVERY remain open/not_started.

## Rekam sebelumnya — Paket B B02.2

- B02.1 real acceptance ditutup dahulu: FFmpeg/ffprobe9.0.2 Gyan verified archive
  `4705843ccaaf54257c16ad90f3e952ece33c17df964ecf7bfdbb0f49c7171077`,
  ignored local bin `artifacts/reports/b022-tools/ffmpeg-9.0.2-essentials_build/bin`.
  Binaries hashes/origin/version dan fixture accounting di [B02.1](../docs/testing/b021-evidence.md).
  Audio57 PASS tanpa skip; hold-short8k64172frames, silence16k16000frames; unchanged raw.
- `workers/audio/{models,worker}.py`: strict/bounded config/internal authorized input,
  frozen JobClient/AssetAccess, LeaseGuard heartbeat selama work, bounded range download/
  checksum, controlled prepare_audio, cancellation/deadline/lost lease kill/reap,
  scoped chunk+JSON provenance upload, typed result/receipt/retry dan local cleanup.
  `testing/audio_worker.py` executable MOCK+actual subprocess; --real uses actual FFmpeg.
  Consumer-failure Windows open-file leak fixed dengan explicit generator.close.
- Internal InputAccess binding diperlukan: frozen lease tidak membawa size/clock/rights.
  Audio failures eligible memakai FAILED/INVALID_AI_OUTPUT; abort/cancel/expired tidak
  menjadi fabricated result. Artifact report required_capability audio, bukan user export.
  Default lease clock epoch ms+monotonic watchdog, injectable; platform reconcile clock
  dan provenance policy saat integration. Frozen wire DTOs/ports tidak disentuh.
- Acceptance worker74 PASS; combined analysis/contractsB218 PASS/no SKIP. B01 regression21
  dan contractsB66 included. Standalone B/B01/worker MOCK serta --real dan process failures
  PASS; Ruff/format/schema drift/Bandit0/audit/build/diff checks PASS. Mypy B17/native Windows
  dan full Linux-target41 PASS; whole native Windows same7 existing A POSIX API errors.
- [B02.2 evidence](../docs/testing/b022-evidence.md) dan
  [execution](../docs/development/package-b-execution.md) memberi commands/config/limits.
  No DB/A/evaluator imports di worker (AST+actual process inventory), no paid provider,
  frontend/container/deploy/real A/B composition. Readiness false/handlers kosong.
- Ports synchronous memerlukan bounded authenticated thread-safe transport adapters;
  MOCK bukan evidence auth/internal API. Remote staged TTL/promotion/retry coordinator
  dan hard-kill/crash recovery milik platform; no OS sandbox/hard-kill cleanup claim.
  Same candidate response resend maksimal sekali; restart wajib fresh attempt/lease,
  no old scratch/artifact reuse dan no exactly-once provider-billing claim.
- Runtime task processes/threads/scratch cleaned; ignored verified toolchain+b022-dist
  retained. Original user changes/untracked docs/pitch/tests/browser/tmp dan prior A
  context preserved; no stage/commit/push/merge/reset/clean. Tool PATH process-local.
- B02.1/6.2 dan B02.2/6.4 standalone scope done; B03 next: STT V2/transcript timing,
  quality/dedup/correction/evidence/stale. Credentials/region/model/quota/budget/rights
  pending. Hold-short synthetic NOT_GOLD/NOT_DOMAIN_VALIDATED; no WER/domain claim.
  Paket B, parent6/9, G-BE/G-FE/G-DELIVERY remain open. A next A03.1 unchanged.

## Rekam sebelumnya — Paket B B02.1 (sebelum binary tersedia)

- Source `backend/flowlens/audio/{models,planning,process,tools,preparation}.py`,
  exports `audio/__init__.py`; tests `tests/analysis/test_audio.py`.
  Entrypoints `AudioTools.discover`, `plan_chunks`, context manager `prepare_audio`.
  Local immutable records/config/provenance, fixed ffprobe/FFmpeg commands,
  bounded local snapshot, raw hash before/after, PCM16 per-channel WAV chunks,
  source/session frame/time mapping, unknown clock, intentional overlap/gap coverage.
- Default input512MiB/3600s/2channels/≤192kHz; output16kHz mono chunks≤50s/<10MB
  including header; overlap1s;512chunks/output512MiB; probe10s/decode120s.
  Stdout bounded, stderr discarded, timeout kill/wait, exclusive scratch output,
  success only after accounting/hash checks, cleanup on failure/context exit.
  Tool single-allocation64MiB/threads1; not an OS memory sandbox/provider quota claim.
- Baseline before edit B01+contractsB87 PASS. Final audio55 PASS/2 SKIP,
  combined B142 PASS/2 SKIP; B01 regression21 and contractsB66 remain PASS.
  B/B01 standalone MOCK CLI PASS/provider_calls0/readiness false/cleaned.
  Ruff/format/schema drift/Bandit0/dependency audit/build/diff check PASS;
  mypy B native Windows12 files PASS, full Linux target36 PASS. Full native Windows
  same7 POSIX API errors A, no A portability edit.
- **Real acceptance pending:** neither FFmpeg nor ffprobe found on PATH/common
  locations/local .codex inventory; versions unavailable. Real hold-short8k resample
  and silence16k tests skip explicitly. Mock PCM materialization + actual Python
  subprocess controls do not prove real audio decode. Keep B02.1/6.2 in_progress.
  Supply trusted binaries in PATH, rerun audio suite and record actual versions.
- [Evidence B02.1](../docs/testing/b021-evidence.md),
  [execution](../docs/development/package-b-execution.md),
  [ADR 0003](../docs/adr/0003-controlled-local-audio.md) explain limits/privacy/commands.
  Frozen1.0.0/models/ports/generated schemas/pyproject/uv.lock unchanged;
  no migration/handler/promotion/DB/provider calls/real composition added.
  Runtime imports allow audio/shared models/stdlib/Pydantic only.
- Fixtures/hashes unchanged; hold-short remains synthetic NOT_GOLD and
  NOT_DOMAIN_VALIDATED. No evaluator oracle/labels in executor, WER/accuracy claim,
  STT/cloud call or transcript dedup (B03). Windows private-root ACLs remain caller
  responsibility; nonzero media starts rejected until explicit mapping support.
- Runtime: subprocesses/tempdirs task cleaned; ignored b021-dist build artifacts
  retained. No persistent server/worker/container. Original B01 changes/untracked
  docs/pitch/tests/browser/tmp and legacy failed-B01 tempdirs preserved. No Git
  stage/reset/clean/commit/push/merge/deploy.
- Next implementation **B02.2 / Phase6.4**, after real B02.1 smoke: isolated worker
  through JobClient/AssetAccess, minimal authenticated input/result, lease/heartbeat/
  cancel/retry/restart. Readiness false; Paket B, parent6/9 and gates remain open.

## Rekam Paket B B01

- Deliverables: `backend/flowlens/analysis/`, `testing/analysis.py`, `tests/analysis/test_foundation.py`, [execution plan](../docs/development/package-b-execution.md) dan [evidence](../docs/testing/b01-evidence.md).
- `flowlens.analysis:register_analysis(config, transactions)` memakai frozen ModuleRegistration. AnalysisConfig strict immutable, run configuration/input/config hash; analysis.0001 owner B depends platform.0001; scoped FK/unique constraints. Repository factory connection+guard disuntikkan; service melalui transaction/UOW ports, tanpa import internals A.
- Configure/audit/internal config ledger event satu caller UOW, commit eksplisit; inventory konfigurasi dan exact-scope admin purge tersedia. Platform audit/ledger retention tetap A. Snapshot/worker handlers/routes belum dipasang; validate/accept/snapshot NOT_EVALUABLE, readiness false. Tidak ada accepted-result coordinator/receipt nyata atau provider pipeline.
- Standalone MOCK platform reference keys + SQLite disposable; 21 B01 tests membuktikan fresh/upgrade/FK/order/rollback, scope/hash/permissions, shared evidence/audit/event UOW, publication setelah commit/failure durability/restart, registry rejection dan runtime import boundary. B03–B05 menyediakan AnalysisRepository domain nantinya.
- Baseline sebelum source edit: track B 64 passed/2 failed karena shared harness constructor tidak menutup SQLite connection (WinError32 cleanup). Fixed dengan explicit closing; return annotation reference UOW memakai existing Repository port. Setelah fix shared A/B masing-masing 66 PASS; baseline B CLI dan B01 CLI PASS/cleaned/provider_calls0.
- Ruff/format/schema drift/Bandit0/dependency audit/build PASS. Mypy B native Windows PASS6; full `--platform linux` PASS30. Native whole-backend mypy tetap 7 existing POSIX API errors A database/bootstrap CLI; tidak mengubah Paket A atau menyatakan whole-backend Windows support. Environment Windows/CPython3.12.15/SQLite3.53.1/uv0.12.23; lock/manifest/frozen models/ports/generated outputs tetap.
- Limits: B01 saja done; 7.3 in_progress untuk foundation, transcript lifecycle planned. B02–B06 belum dikerjakan; provider access/model/transport/budget unverified; TTS NOT_GOLD, no benchmark/domain/operational validation. Real composition menunggu Phase10; Phase6/9/gates tidak ditutup.
- Runtime: no server/worker/container/cloud calls/real data. Passing CLI tempdirs cleaned; dua folder Temp dari baseline gagal awal tersisa karena automatic approval review menolak cleanup (blocked by policy), tanpa bypass. Ignored .venv dan build artifacts b01-dist tersedia. Existing untracked docs/pitch, tests/browser dan tmp dipertahankan. Tidak commit/push/merge/deploy.
- Next B02.1: Phase6.2 controlled FFmpeg/ffprobe decode/resample/chunks/channel/source-time/overlap/gaps; B02.2 Phase6.4 isolated worker JobClient/AssetAccess heartbeat/cancel/retry/minimal input/results. A tetap next A03.1.

## Rekam A02.2

- Deliverables: auth/sessions.py + routes.py, platform.0005, host session/router lifecycle, exact origin config, launcher forwarding disabled, Account successful rehash/password-version guard, session HTTP/service tests dan auth/evidence docs.
- Cookie-only opaque sessions: random raw token hanya Set-Cookie HttpOnly/SameSiteLax/Secure pada configured HTTPS; SQLite menyimpan digest/stamp/timing/revocation. CSRF token derived HMAC, Origin/CSRF pada auth mutations, responses/errors no-store. No bearer/query fallback.
- Login/logout/session/password endpoints nyata. Restricted forced-change flow, cookie rotation, persistent logout, idle60min/absolute8h, reset/deactivation/version rechecks. Successful verification rehashes older Argon2 parameters tanpa revoking stamp untuk representation-only update.
- Durable fixed-window account5/peer20 attempts per60s sebelum hashing, termasuk password-change account budget; max10k subjects, two concurrent HTTP hashing slots, no hashing in write UOW. RATE_LIMITED429 + safe Retry-After.
- Checks: 110 platform tests (22 session cases) + shared contracts66 masing-masing A/B PASS; lint/format/mypy24/schema drift/Bandit0/build/real loopback HTTP login/session/CSRF logout/revocation/forwarding smoke PASS. [Evidence](../docs/testing/a022-evidence.md), [contract/limits](../docs/development/authentication.md).
- Versions: contract1.0.0; platform.0001–.0005; dependency lock A02.1 unchanged. Auth DTOs local host OpenAPI; final frontend generation/freeze remains Phase10.
- Limits: auth-specific CSRF prerequisite implemented; generic mutation/WS/media/export/internal policy, grants/RequestContext and worker auth remain A03/A07. No UI/TLS VM/WS disconnect/performance or operational/domain validation.
- Runtime: disposable DB/synthetic admin/TestClient/actual subprocess smoke cleaned; build artifact a022-dist ignored. No persistent server/worker/container, real account change/provider calls. Commit lokal diizinkan pengguna; tidak ada push/deploy. Gitleaks unavailable; scoped patterns checks only.
- Gate/next: A02.1–A02.2/A02/Phase2.2 done; Phase2 still in_progress. Next A03.1 grants/capabilities, trusted RequestContext and worker principal; all gates not_started.

## Rekam A02.1 — 9 Oktober 2026

- Deliverables: auth/accounts.py, cli/bootstrap_admin.py, platform.0004, host internal account service, account tests, manifest/lock dan workflow/evidence docs.
- One-time private bootstrap, strict canonical logins, actual Argon2id/random salts, active admin create/reset/deactivate, forced password change dan monotonic credential_version. Safe account view tidak memuat hash/password; account audit menggunakan IDs/actions/UTC dalam transaksi yang sama.
- Hashing/verification di luar writer transaction, actor/target version diperiksa kembali sebelum commit. Pending admin mutation ditolak bila credential berubah; audit/marker failure rollback; last-admin guard.
- CLI memakai getpass terminal atau owner-only regular secret file; no default password/secret arguments/output. Tests seluruhnya synthetic/disposable, tidak membuat akun nyata pada DB pengguna.
- Checks: 88 platform + 66 contracts masing-masing A/B PASS; lint/format/mypy 22 files/schema drift/Bandit 0/dependency audit/build/private bootstrap CLI checks PASS. [Evidence A02.1](../docs/testing/a021-evidence.md), [account workflow](../docs/development/account-lifecycle.md).
- Dependency: argon2-cffi 25.1.0, bindings 26.1.0/cffi 2.1.1/pycparser 3.1 locked; contract 1.0.0, platform migrations .0001–.0004. SQLite ALTER CHECK read-only quick_check diizinkan authorizer; writable PRAGMA/transaction/ledger safeguards tetap aktif.
- Limits: service actor IDs trusted server input; belum ada HTTP login/users/session/cookie/expiry/rate limiting. Credential snapshot revocation terbukti, actual session/stream invalidation transport menunggu A02.2/A03/A07. Gitleaks unavailable, scoped patterns/Bandit bukan audit penuh; unpublished app skipped pip-audit.
- Runtime/cleanup: temporary DB/private secret fixtures dan CLI subprocess selesai; ignored build artifacts a021-dist tersedia. Tidak ada persistent server/worker/container, provider call, real account/data migration, commit/push/merge/deploy untuk unit ini.
- Gate/next: A02.1 done, A02/Phase 2.2 in_progress; next A02.2. Semua gates tetap not_started.

## Rekam A01.3 — 9 Oktober 2026

- Deliverables: `backend/flowlens/storage/sqlite/legacy.py`, migration platform.0003, `backend/flowlens/cli/migrate_archive.py`, `tests/platform/test_legacy.py` dan compatibility/evidence docs. Source pre-reset diaudit lewat Git (2660222); tidak dipulihkan sebagai runtime.
- Read-only source snapshot → explicit separate target conversion; original string IDs/JSON/ordinals/frame times/sequence/commands tetap di quarantine tables, UUIDv5 alias untuk platform ID. Private checkpoints terpisah; tidak masuk observed records/streams/AI. Active statuses diberi runtime_status INTERRUPTED tanpa menimpa original status atau auto-resume.
- Atomic import, logical snapshot digest/idempotent retry, changed legacy-ID conflict; unsupported/inconsistent/nonfinite/duplicate-key JSON dan schema ditolak. Source asli tetap immutable, termasuk WAL snapshot support.
- Auth legacy deprecated: old operator config ditolak, operator/seats/commands routes absent/404; key files/tokens tidak dikonversi menjadi accounts/grants.
- Checks: 71 platform tests (32 host/21 persistence/18 legacy) PASS; shared contracts A/B masing-masing 66 PASS, lint/format/mypy 20 files/schema drift/Bandit 0/build/CLI subprocess/link-whitespace checks PASS. [Evidence](../docs/testing/a013-evidence.md), [mapping dan limits](../docs/development/legacy-compatibility.md).
- Versions: contract 1.0.0, lock tetap; platform migrations .0001–.0003, legacy profile legacy-2660222-archive-1. Tidak ada actual B integration atau provider calls.
- Limits: audited four-table profile/synthetic evidence saja; quarantine bukan public replay/source adapter. Archived public payload masih dapat membawa seeds/hints; A07 perlu eligibility/redaction/grants/as-of disposition. Individual auth berikutnya A02.1; grants/CSRF A03.
- Runtime/cleanup: temporary DB dan CLI subprocess selesai; ignored build artifacts a013-dist tersedia. Tidak ada server/worker/container persisten atau real data migration. Commit lokal diizinkan pengguna; tidak ada push/merge/deploy.
- Gate/next: A01.1–A01.3/A01/Phase 2.1 done; Phase 2 tetap in_progress. Next A02.1; Phase 2.2–2.4 planned. G-BE/G-FE/G-DELIVERY tetap not_started.

## Rekam A01.2 — 9 Oktober 2026

- Deliverables: `backend/flowlens/storage/sqlite/{schema,migrate,database,repository}.py`, host/config lifespan integration, `tests/platform/test_persistence.py`; workflow/ADR/progress/evidence diperbarui.
- Real platform schema .0001/.0002, immutable migration checksums/atomic batches, scoped FKs/unique keys, typed source-event/evidence repositories, explicit UOW commit/rollback dan after-commit callbacks. Tabel lifecycle masih minimal; tidak ada auth/import/jobs business APIs atau real B tables.
- Local POSIX owner lock menolak second Database owner/process; lifecycle host mengambil DB hanya jika optional FLOWLENS_DB_PATH dikonfigurasi. Lock dilepas saat shutdown/startup failure. WAL/FK/FULL synchronous; safe startup failure. Readiness tetap 503/HOST_ONLY.
- Checks: 53 platform tests (32 host + 21 persistence) PASS; contracts A/B masing-masing 66 PASS; lint/format, mypy 18 files, schema drift, Bandit 0 issues dan sdist/wheel build PASS. Real host dua subprocess starts/restart mempertahankan ID, menolak owner kedua dan integrity check PASS. [Evidence dan limits](../docs/testing/a012-evidence.md).
- Versions: contract 1.0.0, dependency lock tetap; platform migrations .0001/.0002. ADR 0002 diperjelas untuk lifecycle/migration/ownership, tanpa mengubah stack/boundary.
- Limits: unversioned archive ditolak; historical migration/compatibility A01.3 belum selesai. POSIX/local-path advisory ownership saja; Windows/network/hardlink support tidak dibuktikan. Grants/CSRF/as-of/source/evidence semantic validation dan domain lifecycle menunggu unit owner. Backup/full recovery/provider/domain benchmarks belum dilakukan.
- Runtime/cleanup: disposable DB/tempdirs dan kedua smoke subprocess dihentikan/dihapus. Ignored build artifacts di artifacts/reports/a012-dist tetap tersedia. Tidak ada daemon/worker/container, provider call, commit/push/merge/deploy.
- Next A01.3: audit format archive/operator-key via Git, fixture migration/compatibility dan preservation historical IDs/events/frames/commands. A01 dan Phase 2.1 belum done; semua gates tetap not_started.

## Rekam A01.1 — 8 Oktober 2026

- Deliverables: `backend/flowlens/core/host_config.py`, `backend/flowlens/api/host.py`, `backend/flowlens/api/serve.py`, `tests/platform/test_host.py`; workflow/progress/evidence diperbarui.
- Host A memakai frozen ModuleRegistration/ports, tanpa mengimpor testing storage atau internals B. Test menyuntikkan fake B secara eksplisit; development menolak mock registrations. Baseline contract harness tetap utuh.
- Config strict/immutable: profile/loopback/port/api_workers, unknown env ditolak; supported launcher workers=1/reload=false. Production ditolak, `/ready` 503/HOST_ONLY. Safe request IDs/errors; tidak mencetak invalid config values atau exception text.
- Checks: 32 host tests PASS; shared contracts A/B masing-masing 66 PASS; Ruff lint/format, mypy 14 files, schema drift dan Bandit (0 issues) PASS. Real loopback subprocess smoke `/health` 200 + `/ready` 503 PASS; process dihentikan. Link/fence/whitespace checks PASS. [Evidence dan limits](../docs/testing/a011-evidence.md).
- Limitations: persistence/auth/jobs/business APIs belum tersedia; single-process config/launcher belum membuktikan lock terhadap dua process manager/launcher terpisah. Database lifecycle/ownership berikutnya A01.2. Tidak ada provider calls, benchmark/domain review, frontend/container/deployment.
- Versions: shared contract 1.0.0; dependency/lock dan baseline schemas tidak berubah. Tidak ada ADR baru: mengikuti accepted ownership/registry ADR 0002.
- Runtime/cleanup: tidak ada server/worker/container persisten tersisa; tests memakai disposable baseline harness; live smoke tidak membuka DB. Tidak ada commit/push/merge/deploy.
- Next: A01.2, entry baseline/host A01.1 terbukti. A01.3 historical archive compatibility belum dimulai; Phase 2.1 belum done. G-BE/G-FE/G-DELIVERY tetap not_started.

## Rekam baseline Phase 0–1 — deliverables dan decisions

FR/AC audit, offline/provider/P1 scope, external dependencies, ownership/transaction/migration policy, evaluation protocol/oracles/actual synthetic fixtures, independent A/B packets, ADR 0002. Python 3.12/root pyproject/uv.lock; strict Pydantic models/ports/errors; ModuleRegistration; schema generation/drift; disposable constrained SQLite/UOW; fake platform/analysis and CLI/API MOCK harness.

Mulai dari [developer workflow](../docs/development/backend-foundation.md), [A/B packets](../docs/development/backend-packets.md), [shared contracts](../docs/api/shared-contracts.md), dan [evidence record](../docs/testing/phase01-evidence.md). Baseline memakai default Q-01 offline replay dan Q-02 Gemini Developer API; P1 query/metrics tetap scheduled. Target model/API belum verified, tidak diganti.

A/B tidak mengimpor internals pihak lain. Host API memiliki transaksi/DB writer; worker tidak membuka DB. Shared inputs ada di tests/fixtures dan contracts/examples; evaluator truth/labels/oracles terpisah di evaluation. MOCK profiles tidak boleh production. Real implementations baru di-composition pada Phase 10 setelah kedua packet acceptance selesai.

## Performed checks baseline Phase 0–1

66 shared contract tests PASS pada masing-masing track A dan B; CLI both tracks provider_calls=0; lint/format/mypy, schema drift, constrained fresh/upgrade/FK/rollback/receipt tests, source distribution/wheel build dan independent clean wheel install PASS. Bandit 0 issues, pip-audit no known dependency vulnerabilities (unpublished project skipped), scoped secret patterns/document links/fences/tables/whitespace checked. Detailed commands, versions, outputs and limits: evidence record.

## Limitations baseline / external dependencies

Foundation dan host A01.1 bukan production API atau G-BE. Historical archive migration, auth/grants, actual import/replay/geometry, worker/SDK/provider adapters dan domain pipeline belum diimplementasikan. Real STT/Gemini model/API/account/region/quota/budget belum tersedia/verified; no provider smoke. TTS script NOT_GOLD (audit pronunciation/time pending), NOT_DOMAIN_VALIDATED; no held-out/domain/operational benchmark. Real source rights/partner/reviewer/VM/domain/backup operator tidak diasumsikan tersedia.

## Runtime / cleanup baseline Phase 0–1

Tidak ada server/worker/container persisten dimulai. Disposable DB/clean install tempdir ditutup/dihapus. Local .venv dan ignored artifacts/reports tetap tersedia untuk developer/evidence. Tidak ada cloud inference, provisioning, commit/push, merge atau deployment pada task ini.

## Next action

A lanjut A03.1 setelah A02/account+HTTP auth selesai. B mulai B04 local engineering/MOCK standalone sesuai izin pengguna9 Oktober2026, sementara B03_EXTERNAL_ACCEPTANCE_PENDING (STT account/login/real smoke dan audited benchmark) tetap in_progress. Real transport/coordinator/artifact policy tetap Phase10 terpisah. Frozen baseline1.0.0/readiness false tetap. Reconcile/version perubahan breaking sebelum Phase10. Frontend tetap menunggu G-BE; container/deployment menunggu gate sesudahnya.

## Perencanaan Paket A — 8 Oktober 2026

Pengguna adalah Pihak A. [Rencana eksekusi Paket A](../docs/development/package-a-execution.md) merinci scope A menjadi 10 tahap/26 unit sesi dengan acceptance dan handoff. Saat perencanaan seluruh unit planned; setelah eksekusi A01/A02 done dan next A03.1. Status foundation dan gate di atas tetap berlaku.

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

## Handoff B06 lokal — 9 Oktober 2026

B06 in_progress; local acceptance passed. Branch/HEAD/upstream tetap
feat/backend-rai/da279281f1698197df1efef569f578adb1610cef. Seluruh existing dirty
B03/D3/evaluator/B04/B05 dan docs/pitch/tests/browser/tmp dipertahankan, tanpa Git
mutation. Source baru hanya testing/acceptance.py + tests/analysis/test_acceptance.py;
docs B06/roadmap/handoff/packet status diperbarui. Tidak ada compatibility edit
B03–B05 atau perubahan frozen1.0.0/Paket A/locks.

Entrypoint `.venv/Scripts/python.exe -m flowlens.testing.acceptance --suite --output
artifacts/reports/b06/acceptance.json`; process FFmpeg PATH mengikuti evidence.
Manifest dari actual registrations; cross-service rollback/exception/restart,
post-commit publication, duplicate cancellation dan ownership purge di DB disposable.
Suite existing memberi security/semantic/failure/export/import-isolation coverage.
Ini MOCK test composition, bukan audio-to-report pipeline production.

Actual baseline666 PASS/65.73s; final676 B/contractsB PASS/49.18s tanpa skip,
contractsA66 PASS/4.57s;9 standalones PASS. Ruff110/scoped B mypy61/Linux-target85/
scorer1/schema/Bandit0/dependency audit/build/diff PASS. Full Windows mypy tetap7
error POSIX A. Initial B06 SQL Bandit finding diperbaiki dengan literal SQL;
source/test/threshold existing tidak dilonggarkan. Ignored reports/build tinggal
untuk inspeksi; tidak ada persistent runtime yang ditinggalkan.

Detail: [B06 evidence](../docs/testing/b06-evidence.md). Next: cloud operator/user
menyediakan approved account/config/rights/budget dan authorization real smoke;
evaluation/domain lead menyediakan audited held-out labels/real outputs/domain review.
Platform+analysis owners menangani public/private projection, evidence availability,
durable coordinator/artifact ACL/TTL/receipts pada Phase10 terpisah, belum dimulai.
B03_EXTERNAL_ACCEPTANCE_PENDING (STT_ACCOUNT_LOGIN_REQUIRED,
AUDITED_BENCHMARK_PENDING), B04_EXTERNAL_ACCEPTANCE_PENDING
(GEMINI_ACCOUNT_ACCESS_UNVERIFIED, REAL_GEMINI_SMOKE_PENDING,
AUDITED_SEMANTIC_BENCHMARK_PENDING), GEMINI_EXTERNAL_ACCEPTANCE_PENDING tetap.
Real STT/Gemini0, smoke NOT_RUN, external benchmark BLOCKED/metrics=null,
integrated readiness=false; B03/B04/B05/B06/parent phases/gates tidak ditutup.

### Continuation tooling — 9 Oktober 2026

Evaluator semantic offline, clean-install smoke, bounded synthetic capacity baseline
dan compatibility matrix selesai di working tree. Final `pytest tests/analysis
tests/contracts --track B -q`: **718 PASS**, tanpa skip; 42 test baru mencakup
evaluator dan compatibility. Ruff116 files, scoped mypy tooling, schema drift,
Bandit zero issues, pip-audit, build dan clean-install pass. Wheel/sdist smoke berjalan
di luar checkout dengan locked requirements, enam installed MOCK entrypoints, tanpa
source/PYTHONPATH leak, dan disposable environment bersih. sdist mengecualikan
untracked pitch/browser/tmp.

Capacity 16/128/512 ×3 pass invariant dan cleanup; hasil synthetic MOCK baseline
dengan target UNSET, bukan kapasitas operasional. Linux runtime **NOT_RUN**: WSL2
kernel ada, tetapi docker-desktop tidak memiliki Python/uv/FFmpeg dan Docker daemon
unavailable. `mypy --platform linux` static-only. External B03/B04/B05 acceptance,
audited corpus/reviewer/domain review, real STT/Gemini smoke, public projections,
coordinator/Phase10 dan parent gates tetap terbuka. Real calls0, smoke NOT_RUN,
benchmark BLOCKED/metrics null, integrated readiness false.
