# Session Handoff — ATC FlowLens

| Atribut | Nilai |
| --- | --- |
| Tanggal | 9 Oktober 2026 |
| Objective | Paket B B03 Google STT V2/transcript lifecycle; konteks B01/B02 dan A02.2 dipertahankan di bawah |
| Status | Phase0–1 done; A01/A02 dan Phase2.1/2.2 done; Phase2 in_progress; B01/B02.1 done; B02.2/6.4 done untuk standalone MOCK acceptance; B03 in_progress (standalone adapter/lifecycle acceptance); B04–B06 planned; contract1.0.0 |
| Candidate | Base cdb2b9dae3d16c22a524b8a05b2e5583cc48e0d0 + original uncommitted B01/B02 + B03 working tree; tidak commit/push/merge. Rekam commit A02 tetap di Git |
| Next focus | B03 approved real GCP profile/synthetic smoke, audited labels/benchmark dan worker/artifact reconciliation; B04 prerequisites terbuka; A tetap A03.1 secara independen |
| Gate | G-BE, G-FE, G-DELIVERY: not_started |

## Handoff terkini — Paket B B03 (partial)

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

A lanjut A03.1 setelah A02/account+HTTP auth selesai. B02.1 real FFmpeg dan B02.2 standalone acceptance done; B lanjut B03 approved real GCP profile/synthetic smoke, audited labels/benchmark dan worker/artifact reconciliation setelah standalone adapter/lifecycle acceptance. B04 prerequisites belum terpenuhi. Frozen baseline1.0.0/readiness false tetap. Reconcile/version perubahan breaking sebelum Phase10. Frontend tetap menunggu G-BE; container/deployment menunggu gate sesudahnya.

## Perencanaan Paket A — 8 Oktober 2026

Pengguna adalah Pihak A. [Rencana eksekusi Paket A](../docs/development/package-a-execution.md) merinci scope A menjadi 10 tahap/26 unit sesi dengan acceptance dan handoff. Saat perencanaan seluruh unit planned; setelah eksekusi A01/A02 done dan next A03.1. Status foundation dan gate di atas tetap berlaku.
