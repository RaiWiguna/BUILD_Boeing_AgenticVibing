# Session Handoff — ATC FlowLens

| Atribut | Nilai |
| --- | --- |
| Tanggal | 9 Oktober 2026 |
| Objective | Persistent goal A07.1–A09.3, berurutan/local commit per unit; berhenti sebelum A10 |
| Status | A01–A06 verified; A07.1–A07.3/A07 done; A08.1 done; A08.2 next; B/Phase10 tidak dimulai |
| Candidate | A07.3 commit8941ef904f4ac6d3fdff60a5355333d81b1d0137; A08.1 SHA reported after checks/commit |
| Next focus | A08.2 observed/predicted occupancy, ETA/exit/margins/eligibility; checkout sama feat/backend-aben |
| Gate | G-BE, G-FE, G-DELIVERY: not_started |

## Handoff terkini — A08.1

- Input `8941ef904f4ac6d3fdff60a5355333d81b1d0137`, clean. A07.3 committed/accepted; current goal progress verified from Git/source/checks.
- A08.1/Phase5.1 metric kernel tersedia ([evidence](../docs/testing/a081-evidence.md), [workflow](../docs/development/geometry.md)): XY heading0+X/90+Y CCW from actual baseline/historical atan2; rotated footprint/finite hold corridor/protection miter buffer; exact linear translation vs conservative rotation envelope, no source mutation/evaluator/provider.
- Independent37 oracle cases, final533 platform/66contracts each track/Ruff75/mypy51/drift/Bandit -ll/lock/build/dependency audit PASS;14 migrations unchanged, frozen1.0.0 unchanged; Shapely2.2.0/GEOS3.14.1/types-shapely2.1.0.20260728 locked. Finite clip/collapsed shape bugs RED→GREEN, no weakened assertions.
- Review/secret scan/local commit SHA reported from actual results. Runtime only disposable tests; no geometry daemon/worker/API retained, full-suite native owners/threads/clients closed. No push/merge/amend/destructive Git/B/Phase10/frontend/deploy; parent B phases/gates not completed.
- Next A08.2 after local commit, automatically: real SourceReader + source declaration/clock/layout/identity/coverage/evidence, GeometryReader frozen port, observed/predicted occupancy/ETA/exit/margins. Kernel model alone is not eligibility or observed path certification. A08.3 and S01–S10 rules not done yet. Goal until A09.3 committed, then A10.1 handoff only.

## Rekam A07.3

- Input `52a6954aca3ab1e20ea4effc9aab99701277e5ad`, clean; A07.1–A07.2 previously accepted/committed. A01–A06 source/check verified baseline retained.
- A07.3 REST catalogue/source/history/snapshot/playback/legacy metadata + typed WS incremental/initial snapshot/resync tersedia ([evidence](../docs/testing/a073-evidence.md), [workflow](../docs/development/replay.md)). Fake B via frozen snapshot port, real A SQLite/assets/auth. Native loopback Upgrade/resync/idle revoke/oversize proved; no provider/real B.
- Fixed cursor0 duplicate proof without relaxing uniqueness; temporal/cross-scope/body/authority negative cases remain. WS recheck250ms + before publication, incremental window100, max32/4account, three race retries then1013. Frozen1.0.0/migrations14 unchanged; wsproto1.3.2 added, Uvicorn0.54.0 locked native frame bound1024.
- Final496 platform/66contracts each track A/B/Ruff73/mypy50/drift/Bandit -ll/build/lock/dependency audit PASS. All14 migration SQL unchanged; scan/review/local SHA recorded from actual results. No persistent runtime; native listener/server threads/clients closed. No push/merge/amend/destructive Git/B/Phase10/frontend/deploy. Phase4 A done; parent B phases/release gates remain incomplete/not_started.
- Next A08.1 after commit A07.3, automatic. Read evaluation protocol/numeric oracle and relevant PRD/Phase5 before code. Goal remains until A09.3 committed then A10.1 next only; A10 implementation prohibited in this goal.

## Rekam A07.2

- A07.1 local commit `1d48791ab19c567aa88a6439b53e585bb0f30e1b`; clean before A07.2. PrasyaratA01–A06 dan A07.1 tetap source/check verified ([entry evidence](../docs/testing/a071-evidence.md)).
- A07.2 controls leader/follow/local/archive/recovery dan metadata-only LegacyHistory tersedia ([evidence](../docs/testing/a072-evidence.md), [workflow](../docs/development/replay.md)). Frozen1.0.0/lock unchanged; migration0014. Real A sources/SQLite, optional fake B snapshot via frozen port; controls tidak memanggil B/provider.
- Source immutable; local view independent; optimistic version/durable immutable receipts/events/audit satu UOW. Lost leader authority/restart freeze last committed cursor, bukan infer elapsed downtime. Legacy raw/private/hints/commands tetap quarantine; unknown availability/NOT_EVALUABLE, explicit string/UUID aliases, snake_case; full old monitoring tidak dipulihkan/training commands absent.
- Final466 platform/66contracts each A/B, Ruff69/mypy47/drift/Bandit -ll/build PASS;13 prior migrations unchanged. Secret scan/local SHA dicatat dari actual hasil. Runtime hanya disposable tests/owners/threads, semua selesai; no push/merge/amend/destructive Git/B/Phase10/frontend/deploy. Shared phasesB/gates tidak dinaikkan selesai.
- Next A07.3 setelah commit unit, otomatis tanpa konfirmasi. Goal berhenti setelah A09.3 committed; A10.1 hanya next handoff.

## Rekam A07.1

- Input21457f3, working tree clean; A01–A06 source/evidence diperiksa, baseline425 platform/66contracts each A/B/Ruff63/mypy44/drift/Bandit -ll PASS. A06.1–A06.2 acceptance diverifikasi pada coordinator + actual restart/crash/race/atomic checks.
- A07.1 deterministic observed replay/derived checkpoints/host composition tersedia; [evidence](../docs/testing/a071-evidence.md), [workflow](../docs/development/replay.md). Source immutable, fake B frozen snapshot port, no provider. Shared1.0.0/lock unchanged; platform0013, observed-replay-1. Track snapshot header mengikuti frozen contract, source tracks tetap penuh.
- Checks final:444 platform PASS,66contracts each A/B, Ruff65/mypy45/drift/Bandit -ll/build PASS,12 prior migration SQL unchanged. Local commit SHA dilaporkan dari Git setelah commit; commit hanya file unit, tanpa push/merge/amend. Runtime hanya disposable tests, seluruh owner/clients selesai.
- Next A07.2 setelah commit A07.1, otomatis tanpa konfirmasi. Scope goal tetap sampai A09.3; A10.1 handoff only setelah A09.3. Tidak mengerjakan B/Phase10/frontend/deploy; parent Phase6/9 B tidak dinaikkan selesai.

## Handoff terkini — A06 selesai, local commit dan fresh-chat handover

- Implementation local commit: `7328ae8e420a7b86bfd19b7e788ba71741822e28` — `feat(backend): complete standalone package A through A06`. Working tree clean sesudah commit; handoff ini diperbarui dalam documentation commit terpisah, tanpa amend/push.

- Instruksi terbaru pengguna: verifikasi/tutup A06.1–A06.2, commit lokal seluruh perubahan terkait yang pending, tidak push/A07 di chat lama; buat chat baru fresh (bukan fork/worktree), project/checkout yang sama. Chat baru wajib memverifikasi A01–A06 dari source/checks, membuat goal persisten A07.1–A09.3, satu unit berurutan dengan acceptance/checks/review/secret scan/docs/local conventional commit per unit, lalu berhenti setelah A09.3 dengan A10.1 sebagai next. Tidak mengerjakan B/Phase10/frontend/deploy, tidak push/merge/amend/destructive Git.
- Closeout ulang9 Oktober2026: source/result UOW/lease scope/recovery dan acceptance matrix direview; full425 platform PASS,66 contracts each A/B, Ruff63/mypy44/drift/Bandit -ll PASS (2 LOW native subprocess tetap). Source tidak berubah selama final suite. Markdown links/fences dan diff whitespace PASS.
- Secret check: gitleaks/trufflehog/git-secrets tidak tersedia; scoped known-secret signature scan pada67 candidate files menemukan0 matches. Output hanya metadata di ignored artifacts/reports/a06-closeout-secret-scan.json; tidak mengklaim dedicated/history/entropy scan. Tidak stage runtime/private data/secrets. Runtime hanya test clients/DB owners/thread/native/crash subprocesses, seluruhnya selesai; tidak ada persistent runtime sesi untuk diserahkan.


- Otorisasi A04.3→A05→A06 dipenuhi; phase docs diperbarui setelah tiap paket, docs dibaca ulang pada awal fase baru. A07/integrasi B/push/deploy tidak dilakukan; commit lokal kini diizinkan pada closeout.
- A06.1–A06.2 done: [workflow](../docs/development/durable-jobs.md), [evidence](../docs/testing/a06-evidence.md). jobs/{coordinator,routes}.py, platform0012, host trusted AnalysisModule/policies/repository injection dan active-lease guard. Default domain/jobs tidak aktif, test composition MOCK. Source/assets/evidence real A; AnalysisModule/repository fake via frozen ports, tanpa internals B.
- Durable run config/model/API/SDK/prompt/rule/reducer/input hashes; captured as-of, live creator grants/version/rights/retention/revision/config; one-UOW claims, scoped assets, deadlines/heartbeat, concurrency/reservations, bounded retries/cancel expected_version/idempotency, startup/poll/inspect recovery. Lost/unknown usage conservatively charged; aggregate unknown preserved, no exactly-once provider billing claim.
- Result validate outside lock, recheck inside final UOW; read-back every output. Domain/evidence/artifact/audit/usage/job/receipt/sequence atomic; callback commit/rollback/raw COMMIT denied. Stable duplicate/postcommit-publication/crash receipts and late/revoked/stale denial. Concurrent result race reproduced and fixed with deterministic test. Submitted derivatives already durable; acceptance SQL flag/registry only, no FS/DB atomic transaction claim. Actual resync WS remains A07.
- Final checks:60 jobs cases; full425 platform;66 contracts each A/B; Ruff63/mypy44; structural frozen port assignment; drift; Bandit0 medium/high (2 existing LOW); build PASS. 5 committed migration checksums unchanged, current12; upgrade0011→0012 and actual os._exit before/aftercommit recovery/FKs PASS. Contract1.0.0/lock unchanged A05/A06.
- Runtime all disposable DB/files/TestClient/threads/native/crash subprocesses closed; a06-dist ignored. No persistent server/worker/container or provider/network/data migration. No real B/remote worker, domain/provider fidelity, full-size capacity/hardware power-loss/WS/maintenance validation. Readiness HOST_ONLY503; all gates not_started.
- Next A07.1–A09.3 di chat baru sesuai instruksi terbaru, diawali verifikasi prasyarat. A08/A09/A10 and B remain planned; do not infer backend complete/G-BE from fake standalone packet evidence.

## Rekam A05 phase completion

- A05 done: [workflow](../docs/development/private-assets-evidence.md)/[evidence](../docs/testing/a05-evidence.md), platform0011, full365 platform/66 each contracts/Ruff60/mypy42/drift/Bandit threshold PASS. Authorized media ranges, immutable registry scope/hash/time/quote/file verification, private staged derivatives and internal bounded uploads. No B/provider; readiness503/gates not_started. Runtime disposable closed.
- Pada akhir A05, active next A06.1–A06.2: read rules/PRD/phase/handoff; durable leases/budget/recovery and accepted-result UOW with fake registered handlers/repositories. Update docs after full A06. A07 not authorized in this request.

## Rekam A04 phase completion

- Otorisasi aktif pengguna: selesaikan A04.3 lalu seluruh A05 dan A06, docs setelah tiap paket fase selesai, baca ulang docs sebelum fase berikut. Tidak ada izin commit/push/deploy atau integrasi B.
- A04.1–A04.3/Phase3 done; platform0010; shared1.0.0/lock unchanged. [Evidence](../docs/testing/a04-evidence.md)/[workflow](../docs/development/import-commit.md). New15 cases, full356 +both-track66, Ruff/mypy39/drift/Bandit threshold/build PASS. Root/raw durable copy/fsync then atomic DB publication; actual process-exit recovery verified. Source ports enforce grants/current rights/retention/as-of; raw SQL managed-source immutability; no automatic grants.
- Runtime only disposable owners/TestClient/native/crash subprocesses; all closed, a04-dist ignored. No real data/provider/B. Gold pronunciation/domain/physical/hardware power-loss/performance validation not established; G-BE/readiness unchanged503.
- Next A05.1–A05.2: private authorized media/range/worker minimal, EvidenceService register/resolve source/hash/scope/quote/time/as-of/UOW. Read phase docs before code. Then update phase docs and continue A06.1–A06.2 jobs/lease/budget/atomic accepted results with fake AnalysisModule. Do not stop at A05.

## Rekam A04.2

- Deliverables: sources/metadata.py, clocks/normalization.py, imports/{metadata,normalization}.py, records parser/private fd reader/current preview dan POST/GET metadata, platform.0009;29 new cases. [Workflow](../docs/development/import-metadata.md), [evidence](../docs/testing/a042-evidence.md), [ADR elaboration](../docs/adr/0003-private-import-staging.md).
- Prasyarat A04.1 source/rules/PRD/handoff/execution dan35 tests verified sebelum implementasi. Existing uncommitted work preserved; no source/session commit atau real B/provider integration.
- Full draft envelope stores source owner/identifier/dataset, granular tri-state local/cloud_audio/cloud_context/reviewer/export/audio_export/basis, explicit fixed/unknown retention, nullable coverage, per-file checksums/channel/clock, evidenced effective entity aliases/callsigns dan declared metric layout. Unknown tidak menjadi zero/false/permission. Speaker=true memerlukan future evidence adapter; unsupported sekarang ditolak.
- Local preparation memerlukan local ALLOWED + fixed retention, tidak memerlukan cloud/alignment. Owner active-admin, Origin/CSRF/no-store, <=1MiB metadata request; latest/historical revision GET. Immutable <=64 revisions, expected_version/key/hash receipt transaction, current authority/expiry/file check before retry. Latest GET preview reflects metadata; original upload receipt stable. Reserved source/session IDs belum domain records.
- Frozen1.0.0 projection conservative: cloud true only both audio/context allowed; shared local projection requires reviewer allowed; linear drift clock projected unknown. Full envelope harus dipertahankan A04.3. Histori receipt bukan current rights; service preflight loads latest. No provider dispatch/job/result coordinator yet.
- Explicit relative offset/linear drift Decimal + uncertainty/reviewer/basis; tested IANA wall-time/DST adapter. Canonical sidecars retain raw timestamps/recorded/available/source IDs/hashes; imported parent scopes/IDs/layout/evidence checked, known effective identity mapped to import-scoped UUID. Unknown available not fabricated. Metadata summaries no source text, no worker/domain accepted records. Layout LOCAL_CARTESIAN m/ft factor0.3048; unsupported geographic units/CRS denied. Paired METADATA_COMPLETE bukan geometric/domain eligibility.
- platform.0009 immutable rows/auditable actor/time/request hashes, FK cascade on draft cleanup. Fresh/upgrade0008→0009/raw preservation/TTL/retry/concurrency/commit-fault/owner/revocation/tamper tested. Journal ephemeral scratch, no committed audit/atomic FS promotion claim.
- Checks: platform341 (312 prior +29 new) PASS; contracts66 each A/B PASS; Ruff lint/format51, mypy35, schema drift/Bandit threshold/build/pip-audit PASS. Bandit0 medium/high,2 existing low subprocess findings, no suppressions. Committed0001–0005 checksums unchanged; current0001–0009, previous0006–0008 retained. Shared1.0.0/dependency lock unchanged.
- Limits: canonical m/relative-ms/UTC input profiles only, wall adapter standalone tested; no geographic/corpus/speaker adapter, real license/domain/physical alignment verification, full-size throughput/metadata capacity benchmark. Darwin native memory-limit limitation A04.1 remains. Retention declarations not purge execution; propagation to derivatives/export/backups later owners.
- Runtime: disposable DB owners/TestClient/thread pools/native subprocess closed; ignored a042-dist exists. No persistent server/worker/container, real data/account migration, provider calls, commit/push/merge/deploy. All gates not_started, readiness503/HOST_ONLY.
- A04.2/Phase3.2–3.3 done; A04/Phase3 in_progress. Next only A04.3: commit using full envelope, promotion/dedup/conflict, atomic metadata/assets/events plus crash recovery, source reader through ports. No integrasi B.

## Rekam A04.1

- Deliverables: imports/{staging,inspection,routes}.py, optional private host root/lifespan/error handler, platform.0008, decoder/multipart dependencies,35 import cases dan progress/ADR. [Workflow](../docs/development/import-preview.md), [evidence](../docs/testing/a041-evidence.md), [ADR](../docs/adr/0003-private-import-staging.md).
- Prasyarat A03 verified: rules/handoff/PRD/execution dan129 scoped mutation/transport cases. Existing A03.1–A03.3 working tree dipertahankan; no new B/domain endpoints selain private preview.
- POST /api/v1/imports custom streaming multipart langsung private UUID files, no global temp spool; GET owner-scoped metadata. Active admin only, Origin/CSRF/no-store, final authority/expiry check, hash verification, identical retry stable/changed409. Expired original receipt tidak dapat dibaca ulang via POST. Current evaluator global import grant tidak tersedia; admin lain bukan owner draft.
- Strict versioned WAV/FLAC/canonical events JSON/JSONL dan tracks JSON/explicit-unit CSV; bounds bytes/duration/channels/rows/headers/slots/drafts. Malformed/nonfinite/traversal termasuk Windows paths ditolak; raw original bytes/hash dipertahankan. Preview shows unknown clock/layout, undeclared rights blocking, track presence/audio facts/counts; no storage path/key/content/truth.
- No replay sessions/source/assets/jobs/runs at preview. Draft-only startup recovery interrupted/expired/orphans dan restart persistence checked; domain manifest/rights/coverage/normalization/atomic promotion/source reader remain A04.2–A04.3. Continuous TTL maintenance belum tersedia; reclaim startup-only.
- Native subprocess fixed argv/fd/no shell, minimal env tanpa host secrets, CPU/wall timeout + bounded byte/metadata/frames/buffer. macOS menolak memory rlimit; no hard memory cap/security sandbox claim. Linux cap/full-size throughput belum tested. Native library coverage tidak dibuktikan pip-audit.
- Versions: shared contracts1.0.0 unchanged; migrations0001–0008, committed0001–0005 checksums unchanged, prior0006/0007 retained. Lock adds soundfile0.14.0/python-multipart0.0.32/numpy2.5.3; observed libsndfile1.2.2.
- Checks: platform312 (277 prior +35 import cases) PASS; contracts66 each A/B PASS; Ruff lint/format46, mypy31, schema drift/build/pip-audit PASS. Bandit0 medium/high,2 low subprocess B404/B603 reviewed without skips. Synthetic/disposable SQLite/Argon2/TestClient/native decoder; no live network upload/provider/domain validation.
- Runtime: disposable owners/TestClient/native subprocess closed; ignored a041-dist available. No persistent server/worker/container, real account/data migration, commit/push/merge/deploy. Readiness503/HOST_ONLY, all gates not_started.
- A04.1/Phase3.1 done; A04/Phase3 in_progress. Next only A04.2; A04.3/integrasi B belum dikerjakan.

## Rekam A03.3

- Deliverables: storage/sqlite/mutations.py, platform.0007, UOW authorizer/domain commit ownership/review events, host trusted operation registration/lifecycle; 58 new tests. [Workflow](../docs/development/mutation-consistency.md), [evidence](../docs/testing/a033-evidence.md).
- Human-only general mutation coordinator memakai frozen repositories/UOW ports. Trusted registry chooses capability/type/handler/namespace; current authority checked sebelum receipt lookup. Worker ditolak agar tidak bypass actual lease/result coordinator A06. Domain callback validates target/transition/source rights; no domain endpoint atau real B baru.
- Same scoped actor/session/run/operation/target/key + canonical payload/input/version → stable original receipt, no repeat effect/publication. Changed payload/version conflicts409; new key with stale version conflicts409. Version0 adalah missing bookkeeping, bukan target existence; actual aggregate creation must initialize bookkeeping before first shared Review expected_version1.
- Callback persisted-result read-back + version/event/audit/receipt satu real UOW. Callback commit/rollback/raw transaction attempts denied; caught attempts poison UOW. Domain/evidence/storage/commit fault rollback semua writes/publication. After-commit failure durable, retry serves original receipt; real resync A07.
- Three audit tables dan mutation receipts append-only, termasuk replacement lewat composite key/new UUID pada ordinary SQLite connection. Historical audit preserved .0006→.0007; existing committed .0001–.0005 checksums unchanged. .0006 retained, contracts1.0.0/lock unchanged. Enforcement bukan cryptographic tamper evidence atau proteksi privileged DB-file replacement; audit privacy/maintenance A09.
- Checks: platform277 (219 prior +58 new), contracts66 masing-masing A/B PASS; Ruff lint/format42, mypy28, schema drift, Bandit0, sdist/wheel PASS. Real disposable SQLite/Argon2/TestClient/thread concurrency, fake review repository melalui frozen ports; no live network/provider/domain validation.
- Runtime: owners/TestClient/connections/thread pools closed; ignored a033-dist tersedia. No persistent server/worker/container, real accounts/data migration, commit/push/merge/deploy. Readiness503/G-BE/G-FE/G-DELIVERY tetap not_started.
- A03.1–A03.3/A03/Phase2 done; next A04.1 (private staging/size-content-duration-path-hash validation/preview). A04/A06/A07/A09 atau integrasi B tidak dimulai pada sesi ini.

## Rekam A03.2

- Deliverables: auth/transport.py + authenticate_worker, api/serializers.py, host HTTP/WS/no-store integration dan HTTPConnection auth helpers; 71 new tests dan prior test setup diperbarui. [Workflow](../docs/development/transport-policy.md), [evidence](../docs/testing/a032-evidence.md).
- Automatic host /api/v1 human principal/Origin/CSRF policy; auth restricted flows tetap endpoint-specific. Internal /internal dan /api/v1/internal require live worker bearer, tanpa browser cookies/Origin/Fetch Metadata. Query/context claims, bearer public dan ambiguous headers/cookies denied. Scoped helpers memakai server state, bukan client mode/as-of/context.
- WS policy sebelum accept dan scoped recheck helper tersedia. Validation/HTTP/contract failures1008 dan unexpected1011 dengan reason kosong; default validation input leak reproduced/fixed. TestClient probe rechecks logout/reset/expiry/grant revoke; actual stream scheduling/disconnect/resync tetap A07.3.
- Public projection live-UOW: exact observed typed DTOs only, nested scope/revision/time/mode, copied-model revalidation; worker/internal/raw/truth/private/subclass denied. Manifest source rights current; no audio grant → assets empty; explicit audio → authorized metadata tanpa fixture/private paths. Truth tidak punya frozen public DTO; trusted readers tetap memisahkan truth/secret dalam teks.
- Checks: platform219 (148 prior +71 new), contracts66 masing-masing A/B PASS; Ruff lint/format40, mypy27, schema drift, Bandit0, sdist/wheel PASS. Disposable SQLite/Argon2/TestClient only; no new live network WS/provider/domain validation. Contract1.0.0/lock/migrations.0001–.0006 unchanged.
- Compatibility: transport denial precedes route/body validation. Legacy bearer sekarang403; legacy routes tetap absent. Existing safe-error tests diberi authenticated fixtures dengan assertions tetap. Tidak ada real domain/admin/job/media/export endpoints baru; future handlers wajib memakai object capability/rights guards dan serializer secara eksplisit.
- Runtime: disposable DB/TestClient owners closed; ignored a032-dist tersedia. No persistent server/worker/container, real accounts/data changes, commit/push/merge/deploy. All gates tetap not_started/readiness503.
- Next A03.3/Phase2.4; A03.1–A03.2/Phase2.3 done, A03/Phase2 in_progress. A03.3, A04 dan integrasi B tidak dikerjakan pada sesi ini.

## Rekam A03.1

- Deliverables: auth/permissions.py, platform.0006, Sessions.authenticate same-UOW, host permissions service/guard, guarded platform/injected repositories/event/audit dan 38 authorization tests. [Workflow](../docs/development/authorization.md), [evidence](../docs/testing/a031-evidence.md).
- Explicit expiring/revocable per-account/session capabilities; role bounded, admin tidak otomatis punya domain/truth access, truth evaluator+DEBRIEF only. Legacy nullable grants fail closed. Management trusted service memakai live admin cookie credential dan atomic audit; belum HTTP endpoints.
- RequestContext dibangun dari credential/grants/run/revision/hash/server replay state; full DTO digest receipts TTL5m. Every host repository/event/audit checks live proof/session/version/grant/scope/revision in same UOW; forged/cache after revoke/logout/reset denied. Worker credentials hashed/SecretStr, separate principal with one-run scope and bounded explicit source/asset allowlists; no truth/export/admin/inventory.
- Source local/cloud/export/audio_export policy dan safe asset metadata helpers membaca ulang manifest/hash/rights. Real media/export routes belum ada. Current input/run must be latest; missing replay state NOT_EVALUABLE. Historical readers/as-of filtering A07, source writers A04, leases A06.
- Checks: 148 platform + contracts66 masing-masing A/B PASS; Ruff format/lint, mypy25, schema drift, Bandit0 dan sdist/wheel build PASS. Fresh/upgrade/restart/rollback negative cases covered. TestClient host guard; no new live HTTP smoke because no new route. No provider/real B/domain/operational validation.
- Contract1.0.0/lock unchanged; migrations .0001–.0006. Direct DB/raw SQL trusted infrastructure; domain host guard wajib, no client context ingestion. Public role DTOs/transport guards A03.2; append-only audit/version/idempotency A03.3.
- Runtime: all disposable fixtures/DB owners/TestClient closed, ignored a031-dist build available. No persistent runtime, real accounts/data changes, commit/push/merge/deploy. Gates all not_started.
- Next A03.2; A03.1 done, A03/Phase2.3 in_progress. Do not start A03.3/A04 or integrate B in same unit.

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

A lanjut A04.1 setelah A01–A03/Phase2 grants/transport/mutation foundation selesai dan frozen baseline 1.0.0; B dapat mulai mandiri. Reconcile/version perubahan breaking sebelum Phase 10; credential/model readiness sebelum real smoke. Frontend tetap menunggu G-BE; container/deployment menunggu gate sesudahnya.

## Perencanaan Paket A — 8 Oktober 2026

Pengguna adalah Pihak A. [Rencana eksekusi Paket A](../docs/development/package-a-execution.md) merinci scope A menjadi 10 tahap/26 unit sesi dengan acceptance dan handoff. Saat perencanaan seluruh unit planned; setelah eksekusi A01/A02/A03/Phase2 done, next A04.1. Status foundation dan gate di atas tetap berlaku.
