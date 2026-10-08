# Backend A/B packets and handoff

Start after Phase 0/1 evidence; independent implementation until final Phase 10 composition. Contract baseline 1.0.0. Pengguna menyatakan sebagai Pihak A pada 8 Oktober 2026; individu owner B belum ditetapkan.

## Package A — Platform & Replay

Rincian eksekusi per sesi: [Paket A: A01–A10](package-a-execution.md). A01.1–A01.3/A01/Phase 2.1 `done`; Phase 2 `in_progress`. Next A02.1 accounts/bootstrap/reset/deactivation; remaining units planned. Paket B belum dimulai.

1. Phase 2: host/config; platform schemas/migration runner/UOW; accounts/grants/cookie/CSRF/worker principal; audit/idempotency/versioning. Tests fresh/upgrade/auth/cross-scope/rollback.
2. Phase 3 + 6.1: import preview/atomic commit, immutable source manifest/rights/clock/coverage, private assets/ranges. Tests malformed/path/hash/duplicate/conflict/forbidden transfer.
3. Phase 6.3 after Phase 2: durable job lease/heartbeat/deadline/budget/retry/cancel and accepted result coordinator through frozen B handler. Test restart/late result/rights change, no duplicate receipt.
4. Phase 4: event source/reducer/checkpoints/as-of/replay controls/REST/WS/archive/compatibility. Test ordering/seek/reconnect/permission revoke, no provider call on seek.
5. Phase 5: footprint/occupancy/prediction/eligibility/observed rules/source alerts. Use independent numeric/time oracle and S01–S10; no labels/provider dependency.
6. Phase 9 A: artifact download/promotion/expiry, retention/purge inventory, ops/provider profiles/backup/restore/audit. Test permissions/purge/consistent disposable recovery.
7. Run shared contract suite with fake analysis and package-owned security/recovery/performance tests. Submit manifest + evidence.

## Package B — Analysis & AI

1. After Phase 1: analysis module/config/migrations/repositories/registration via transaction ports; reference FK schemas supplied harness. Do not import A internals.
2. Phase 6.2/6.4: controlled FFmpeg processing/chunks/time mapping and isolated worker using fake platform ports; no SQLite import/mount in worker.
3. Phase 7: STT V2 adapter/transcripts/append-only corrections/stale dependencies. Mock failures plus real synthetic STT smoke after readiness; pronunciation audit/critical-slot baseline.
4. Phase 8: Gemini structured parsing/bounded read-only tools/association/memory/loops. Ambiguity, correction/cancellation/negation/rebuild/injection/error tests and real smoke after readiness.
5. Phase 9 B: evidence-linked findings/options/review/reanalysis/journal/briefs/report renderer, P1 query/metrics and sanitized provider diagnostics. No execute command path.
6. Run shared contract suite with fake platform, repository/semantic/failure tests, and actual provider smoke. Submit manifest + evidence.

## Independent acceptance and final integration

Both packets submit entrypoints/routes/migrations/config/dependencies/job handlers/snapshots/purge inventory, contract/schema versions, candidate SHA, performed commands/results, provider versions/smoke (B), limitations/blockers. Parent Phase 6/9 stays open until both owner subparts complete.

Phase 10 installs real A/B implementation and verifies cross-package atomic transactions, all registrations, pipeline API, negative isolation, canonical/held-out benchmark, recovery and capacity. Contract test pass with mocks does not prove integrated runtime compatibility. Only G-BE passed permits frontend implementation. No implementation A/B is started by the baseline packet.
