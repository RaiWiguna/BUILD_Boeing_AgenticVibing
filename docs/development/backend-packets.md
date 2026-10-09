# Backend A/B packets and handoff

Start after Phase 0/1 evidence; independent implementation until final Phase 10 composition. Contract baseline 1.0.0. Pengguna menyatakan sebagai Pihak A pada 8 Oktober 2026; individu owner B belum ditetapkan.

## Package A — Platform & Replay

Rincian eksekusi per sesi: [Paket A: A01–A10](package-a-execution.md). A01.1–A01.3/A01/Phase 2.1 `done`; Phase 2 `in_progress`. A02/accounts+HTTP sessions done; next A03.1 grants/RequestContext/worker principal; remaining units planned. Paket B B01/B02 standalone acceptance done; B03 partial/in_progress; B04 in_progress (local MOCK accepted; real smoke/benchmark open); B05 in_progress (local standalone MOCK); B06 in_progress (acceptance lokal, [evidence](../testing/b06-evidence.md)).

1. Phase 2: host/config; platform schemas/migration runner/UOW; accounts/grants/cookie/CSRF/worker principal; audit/idempotency/versioning. Tests fresh/upgrade/auth/cross-scope/rollback.
2. Phase 3 + 6.1: import preview/atomic commit, immutable source manifest/rights/clock/coverage, private assets/ranges. Tests malformed/path/hash/duplicate/conflict/forbidden transfer.
3. Phase 6.3 after Phase 2: durable job lease/heartbeat/deadline/budget/retry/cancel and accepted result coordinator through frozen B handler. Test restart/late result/rights change, no duplicate receipt.
4. Phase 4: event source/reducer/checkpoints/as-of/replay controls/REST/WS/archive/compatibility. Test ordering/seek/reconnect/permission revoke, no provider call on seek.
5. Phase 5: footprint/occupancy/prediction/eligibility/observed rules/source alerts. Use independent numeric/time oracle and S01–S10; no labels/provider dependency.
6. Phase 9 A: artifact download/promotion/expiry, retention/purge inventory, ops/provider profiles/backup/restore/audit. Test permissions/purge/consistent disposable recovery.
7. Run shared contract suite with fake analysis and package-owned security/recovery/performance tests. Submit manifest + evidence.

## Package B — Analysis & AI

[Rencana B01–B06](package-b-execution.md), [evidence B01](../testing/b01-evidence.md),
[B02.1](../testing/b021-evidence.md), [B02.2](../testing/b022-evidence.md),
[B03](../testing/b03-evidence.md). B01 foundation, B02.1 real FFmpeg dan B02.2 isolated
worker standalone acceptance done. B03 STT V2 adapter/transcript lifecycle deterministic
acceptance tersedia; approved real GCP profile/smoke, audited benchmark dan worker/
artifact reconciliation masih terbuka. Readiness false; no real A/B composition.

Keputusan sequencing pengguna9 Oktober2026: B04 local engineering boleh dimulai
dengan MOCK transcript fixtures/injected frozen ports walaupun B03 belum closed.
Flag B03_EXTERNAL_ACCEPTANCE_PENDING (STT_ACCOUNT_LOGIN_REQUIRED dan
AUDITED_BENCHMARK_PENDING); B03/Phase7 tetap in_progress. Exception ini tidak
menghapus real-provider/benchmark acceptance dan tidak mengizinkan paid RPC atau
penutupan gates. B04 masih planned/local start authorized pada pencatatan keputusan.

1. After Phase 1: analysis module/config/migrations/repositories/registration via transaction ports; reference FK schemas supplied harness. Do not import A internals.
2. Phase 6.2/6.4: controlled FFmpeg processing/chunks/time mapping and isolated worker using fake platform ports; no SQLite import/mount in worker.
3. Phase 7: STT V2 adapter/transcripts/append-only corrections/stale dependencies. Mock failures plus real synthetic STT smoke after readiness; pronunciation audit/critical-slot baseline.
4. Phase 8: Gemini structured parsing/bounded read-only tools/association/memory/loops. Ambiguity, correction/cancellation/negation/rebuild/injection/error tests and real smoke after readiness.
5. Phase 9 B: evidence-linked findings/options/review/reanalysis/journal/briefs/report renderer, P1 query/metrics and sanitized provider diagnostics. No execute command path.
6. Run shared contract suite with fake platform, repository/semantic/failure tests, and actual provider smoke. Submit manifest + evidence.

## Independent acceptance and final integration

Both packets submit entrypoints/routes/migrations/config/dependencies/job handlers/snapshots/purge inventory, contract/schema versions, candidate SHA, performed commands/results, provider versions/smoke (B), limitations/blockers. Parent Phase 6/9 stays open until both owner subparts complete.

Phase 10 installs real A/B implementation and verifies cross-package atomic transactions, all registrations, pipeline API, negative isolation, canonical/held-out benchmark, recovery and capacity. Contract test pass with mocks does not prove integrated runtime compatibility. Only G-BE passed permits frontend implementation. No implementation A/B is started by the baseline packet.


B04 continuation9 Oktober2026: private intent/association/memory/open-loop services,
bounded Gemini2.29.0 Interactions adapter and analysis.0003 ledger implemented with
injected ports/caller UOW. Standalone MOCK evidence: [B04](../testing/b04-evidence.md).
No production pipeline readiness or handler wiring. B04 external smoke/benchmark
and B03_EXTERNAL_ACCEPTANCE_PENDING remain; B05 and integration gates not advanced.


B05 continuation9 Oktober2026: independent local engineering authorized before
external B03/B04 acceptance. `advisory/` + analysis.0004/register_advisory/testing.advisory
provide standalone MOCK behavior; [B05 evidence](../testing/b05-evidence.md).
B03_EXTERNAL_ACCEPTANCE_PENDING (STT_ACCOUNT_LOGIN_REQUIRED, AUDITED_BENCHMARK_PENDING)
and B04_EXTERNAL_ACCEPTANCE_PENDING (GEMINI_ACCOUNT_ACCESS_UNVERIFIED,
REAL_GEMINI_SMOKE_PENDING, AUDITED_SEMANTIC_BENCHMARK_PENDING) remain.
GEMINI_EXTERNAL_ACCEPTANCE_PENDING remains. Real calls0/smoke NOT_RUN/benchmark
BLOCKED/metrics=null/readiness=false. B05 in_progress, B06 and gates not closed.
