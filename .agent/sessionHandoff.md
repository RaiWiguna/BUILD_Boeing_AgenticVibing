# Session Handoff — ATC FlowLens

| Atribut | Nilai |
| --- | --- |
| Tanggal | 9 Oktober 2026 |
| Objective | Paket A A02.2: HTTP login/logout, cookie sessions, expiry/rate limits |
| Status | Phase 0–1 done; A01/A02 dan Phase 2.1/2.2 done; Phase 2 in_progress; B belum dimulai; contract 1.0.0 |
| Candidate | Input c36cf04; perubahan A02.1–A02.2 dicommit lokal atas instruksi pengguna 9 Oktober 2026; SHA akhir tersedia di Git log; tanpa push |
| Next focus | A03.1 grants/RequestContext/worker principal; B tetap independen |
| Gate | G-BE, G-FE, G-DELIVERY: not_started |

## Handoff terkini — A02.2

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

A lanjut A03.1 setelah A02/account+HTTP auth selesai dan frozen baseline 1.0.0; B dapat mulai mandiri. Reconcile/version perubahan breaking sebelum Phase 10; credential/model readiness sebelum real smoke. Frontend tetap menunggu G-BE; container/deployment menunggu gate sesudahnya.

## Perencanaan Paket A — 8 Oktober 2026

Pengguna adalah Pihak A. [Rencana eksekusi Paket A](../docs/development/package-a-execution.md) merinci scope A menjadi 10 tahap/26 unit sesi dengan acceptance dan handoff. Saat perencanaan seluruh unit planned; setelah eksekusi A01/A02 done dan next A03.1. Status foundation dan gate di atas tetap berlaku.
