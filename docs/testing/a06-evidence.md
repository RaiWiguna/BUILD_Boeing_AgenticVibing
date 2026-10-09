# A06 — Durable jobs dan accepted results evidence

Tanggal: 9 Oktober 2026. A06.1–A06.2 done, roadmap Phase6.3 milik A done; shared Phase6 tetap in_progress (B6.2/6.4 planned). Prasyarat A01–A05 source/checks diperiksa; phase docs A04 dan A05 diperbarui sebelum fase berikut, lalu rules/PRD/handoff/roadmap/packet/ports dibaca kembali pada awal A06. [Workflow](../development/durable-jobs.md).

Deliverables: jobs/{coordinator,routes}.py, platform.0012, optional host AnalysisModule/policy/repository injection, live active-lease permissions guard, trusted pending evidence registration. Actual source/assets/evidence tetap A-owned; fake typed analysis repository/module hanya test. Shared1.0.0 dan lock tidak diubah oleh A05/A06.

60 cases tests/platform/test_jobs.py: scoped durable creation/receipt, lease/heartbeat/deadline/concurrency/reservations, two claimants and two identical results, conservative lost/unknown usage, retry backoff/max attempts, partial/transient failure, cancel expected version/key stability, live grant/rights/worker/scope/credential/revision/config/policy/readiness gates, copied hash/quote/channel/budget/scope/available-time denial, minimal audio/context input, nonlease operator scope denial, callback transaction ownership/readback, seven rollback boundaries, staged derivative and new transcript quote atomic acceptance, publication failure/event resync, internal HTTP auth/body caps/no-store, host MOCK/default-off composition, ordinary SQL update/delete/replace denial for result/create/cancel receipts, upgrade0011→0012/history/FKs, restart active then expired lease, actual subprocess os._exit91 precommit and92 postcommit publication + restarted owners/stable receipt.

Initial scheduler/result cases RED because Jobs/result absent. A concurrent-result race was reproduced: second request lost scope after first commit before context creation, producing AUTH_REQUIRED. A deterministic interleaving case was RED, fixed via live-authority/immutable-receipt recheck, then concurrency/regression PASS. Inspection without worker polling initially retained expired reservation (RED); authorized inspection now reaps and commits state. No test thresholds/assertions weakened.

| Check | Result |
| --- | --- |
| Final jobs cases (covered in full platform run) | PASS60; initial scoped57 +3 immutable receipt cases |
| Final full platform suite | PASS425 (365 A05 +60 A06) |
| Shared contracts track A / B | PASS66 each |
| Ruff check / format backend tests scripts | PASS63 files |
| mypy backend/flowlens | PASS44 source files |
| Structural frozen AssetAccess/SourceReader/EvidenceService/JobClient assignment | PASS temporary mypy check |
| Shared schema drift (`python -m flowlens.contracts.generate --check`) | PASS |
| Migration compatibility | 5 committed migration checksums unchanged; current12, prior0011 upgrade preserves history/FKs |
| Bandit -ll | PASS0 medium/high;2 existing low native subprocess findings, no suppressions |
| uv build artifacts/reports/a06-dist | PASS sdist/wheel |

Synthetic/disposable owners, actual WAV/hash/ranges, TestClient/thread concurrency/native decoder and process-exit tests; all task runtime closed. Build outputs ignored; no persistent server/worker/container, provider request, real B, private account/data migration, commit/push/deploy. Provider billing/fidelity, domain semantics/operational use, full-size capacity/performance, hardware power loss, real remote worker process, actual WS resync and maintenance purge/backups not validated. Readiness remains HOST_ONLY503; G-BE/G-FE/G-DELIVERY not_started. A07–A10 remain planned.

Final migration formatting sempat diubah saat satu test run masih memuat manifest lama di memory:2 process-restart cases mendeteksi mismatch (423 lainnya PASS), bukan data developer. Scoped final9 cases termasuk crash/upgrade/immutability PASS, lalu full final425 PASS setelah source dibekukan. Final build dibuat ulang dari source tersebut.

## Local closeout sebelum fresh chat — 9 Oktober2026

Acceptance A06.1–A06.2 direview ulang dari source dan actual tests, bukan status dokumen saja. Final rerun:425 platform PASS (80.98s),66 contracts each A/B PASS, Ruff63/mypy44/schema drift/Markdown links/fences/git diff --check PASS; Bandit -ll0 medium/high,2 known LOW. Dedicated secret scanners gitleaks/trufflehog/git-secrets tidak tersedia. Scoped known-secret signature scan seluruh67 candidate modified/untracked files:0 matches; limited signature coverage, bukan dedicated/history/entropy scan. Metadata report ignored: artifacts/reports/a06-closeout-secret-scan.json.

User mengizinkan local conventional closeout commit terkait A03.1–A06. Commit actual SHA dilaporkan dari Git; tidak push. Fresh chat menggunakan project dan checkout sama (bukan fork/worktree), memverifikasi prasyarat sebelum goal A07.1–A09.3. Chat ini berhenti pada A06, tanpa A07 implementation. No persistent session runtime; all newly started checks/test children selesai.
