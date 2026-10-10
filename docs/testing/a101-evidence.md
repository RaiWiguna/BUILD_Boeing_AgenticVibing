# A10.1 — Acceptance mandiri Paket A

9 Oktober 2026. Branch `feat/backend-aben`; input clean `1f88f38971f1e171fd2421aa8647424e429e26f1`. HEAD cocok dengan candidate yang diharapkan; tidak ada existing changes yang diganti. Candidate A10.1 adalah commit yang membawa evidence ini (lihat `git log`); source hashes pengukuran ada pada [report aktual](a101-benchmark.json). Frozen contracts/ports/schema tetap **1.0.0**, lock dan seluruh 18 migrations unchanged. Real API host lifespan, authorization, private filesystem dan SQLite WAL; hanya B yang fake melalui `ModuleRegistration.snapshot_reader`/`AnalysisModule` frozen. Tidak memakai SQLiteHarness sebagai storage aplikasi.

## Prasyarat dan acceptance source/tests

[A01–A09 completion audit](a07-a09-completion-audit.md) diperiksa terhadap source, tests, evidence dan actual Git ancestry. Commit A07.1→A09.3 tersedia dan input A09.3 adalah `1f88f389…`; tidak sekadar membaca status roadmap. Full suite berikut menguji kembali seluruh prasyarat, termasuk historical compatibility.

| Acceptance wajib | Source aktual | Evidence yang dijalankan kembali |
| --- | --- | --- |
| A01 fresh/upgrade/legacy, immutable source IDs | storage/sqlite/{database,migrate,schema,legacy}, replay/compatibility | test_persistence, test_legacy, test_recovery_cli, test_replay_compatibility |
| A02–A03 akun/auth/context/CSRF/truth/isolation/mutation | auth, api/serializers, storage/sqlite/mutations | test_accounts/sessions/permissions/transport/mutations; actual HTTP/WS/media denial tests |
| A04 import/provenance/clock/rights/raw immutable | imports, clocks, sources | test_imports/import_metadata/import_commit; independent time oracle, fault boundaries |
| A05 evidence/hash/range/quote/live authority | assets, evidence | test_assets_evidence (service dan actual HTTP ranges); scope/rights/revocation/private path denial |
| A06 durable jobs/lease/cancel/revision/budget/atomic result | jobs | test_jobs; race/native crash/reopen, late/duplicate/stale denial and same UOW rollback |
| A07 replay/time/order/control/archive/REST/WS | replay | test_replay_snapshots/controls/transport/compatibility; genuine native transport and restart cases |
| A08 geometry/occupancy/rules/source alerts | geometry | test_geometry_kernel/occupancy/observed_rules/alert_reducer/rule_service/indicators/routes |
| A09 artifacts/retention/tombstones/ops/recovery | artifacts, retention, ops, recovery | test_report_artifacts/retention/tombstones/artifact_retention_routes/ops_*/recovery* |
| Capacity/timing | real host and all configured A services | opt-in test_acceptance_capacity; full decode, actual commits/range/list/seek/snapshot/WS measurements |

Module names pada tabel relatif ke `backend/flowlens` dan `tests/platform`. Linked per-unit evidence menyediakan metode/detail negatif; full run baru menguji semua module tersebut. Recovery termasuk WAL SQLite backup API, hashes, grants/revisions/evidence/jobs/checkpoints, purge retry/current tombstones sebelum akses restored, ENOSPC/fsync faults dan native subprocess crashes. Local recovery tidak membuktikan off-host encryption/scheduler/RPO24h/RTO4h.

| Skenario | Bukti Paket A | Boundary yang belum diklaim |
| --- | --- | --- |
| S01 | test_s01_crossing_clear_before_arrival_no_modeled_overlap | Temporal lab oracle, bukan SOP arrival nyata |
| S02 | test_s02_interval_overlap_attention_and_no_clearance_claim | Interval/margin evidence; bukan verdict keselamatan |
| S03 | test_s03_stopped_vehicle_in_protection_keeps_unknown_exit | Unknown exit dipertahankan |
| S04 | test_s04_on_hold_line_without_movement_is_not_violation | Footprint/contact bukan bukti gerakan |
| S05 | test_s05_crossing_without_observed_instruction_requires_coverage | Absence membutuhkan declared coverage; intent B belum tersedia |
| S06 | test_s06_hold_short_instruction_crossed_full_footprint | Source lab codec, bukan parsing natural language B |
| S07 | test_s07_cancel_and_report_do_not_clear_occupied_resource | Cancel/report tidak mengosongkan physical occupancy |
| S08 | test_s08_go_around_response_delay_uses_profile_and_availability | Versioned lab timer/as-known/debrief |
| S09 | test_s09_opposite_runway_headings_share_one_resource | Independent geometry/interval expectations |
| S10 | test_s10_active_threat_dropout_preserves_unknown_not_clear | Dropout/coverage/identity/clock/layout mempertahankan abstention |
| S11 | test_mutations, test_jobs; test_durable_idempotency_version_conflicts_and_atomic_audit, test_two_claimants_release_and_revoked_leader_takeover | Duplicate/concurrent effect satu; billing provider tidak exactly once |
| S12 | test_ws_snapshot_reconnect_resync_retry_no_duplicate_state; controls local/follow/leader/restart; measured injected-gap resync | A transport; B semantics dan browser downstream |

S01–S10 tests bernama di `test_observed_rules.py`, dengan actual-source integration pada `test_rule_service.py` dan geometry/rules routes. S11/S12 adalah transport/consistency cases, tidak dihitung sebagai hazard denominator. AC-01/02/09/14/15/17 dan platform portions AC-10/12/13/16/20 terbukti sesuai ownership A. AC-03–08/11, semantic portions AC-10–13, Compose/browser, provider benchmark NFR-06, held-out AC-18 dan domain/operational AC-19 tetap kewajiban B/integrasi/delivery; tidak dinaikkan selesai oleh fake B. NFR-02 browser dan NFR-08 off-host bukan acceptance mandiri A10.

## Pengukuran wajib dan perbaikan

[Raw measurements final](a101-benchmark.json) memuat seluruh samples, nearest-rank percentile, hardware/runtime, fixture dimensions, konfigurasi import, SHA/hashes, thresholds dan limits. [Pengukuran gagal awal](a101-benchmark-before.json) dipertahankan, bukan dihapus: snapshot p95 **940.081 ms** >500 ms pada input/workload yang sama. Profiling direct Replay.snapshot menemukan tiga reducer passes (0.121 dari0.162s pada diagnostic run); biaya model-fields lookup dilakukan berulang per field/row. Fix minimal menyimpan field registry sekali, melewati source-only reducer jika proyeksi B tidak berisi source events, dan melewati merge reducer jika checkpoint sama dengan reconstruction aktual. Full validation, checksum, live authorization, input race check dan non-empty B source verification tetap berjalan. 69 scoped replay/transport regression cases PASS29.88s; opt-in benchmark adalah regression terhadap target yang sebelumnya gagal.

Gap limit import dibuktikan oleh tiga regression tests yang gagal sebelum fix: default2GiB/file dan4GiB/import serta tidak ada aggregate channel-duration ceiling. Fix: default dan maximum512MiB/file,2GiB/import, maksimal2 kanal,7200000ms total duration×channels sebelum preview/commit. 82 import-related cases PASS23.45s sesudah fix. Frozen contracts tidak diubah. Source per-file duration tetap dibatasi2jam; stereo60menit atau dua mono60menit mengisi total120channel-menit.

| Dimensi / target PRD | Metode dan actual result | Status |
| --- | --- | --- |
| Replay60menit /20objek | 1220 canonical tracks,20 evidenced entity mappings,61 samples/entity dari0→3600000ms; real sidecar validation/normalization/commit; seek30positions;1220events/20IDs pada end snapshot | Measured PASS, cadence60000ms |
| Metadata100sesi | 100 distinct source identifiers melalui Imports→metadata→ImportCommit, actual read grants, authorized catalogue100items;99 tiny audio +1 full baseline | Measured PASS; max_owner_drafts100 explicitly configured, byte/duration limits default |
| Dua kanal /total2jam | Dua mono PCM16 WAV16kHz60menit/channel;115200044bytes/file; generation dan full decoder import timing recorded; stored SHA and authorized final-byte range206 verified | Measured PASS; silence, no speech/provider inference |
| NFR-01 list p95≤500ms | 5concurrent logical API clients ×10requests;100items; p50 277.255/p95 **385.162**/max389.496ms | PASS |
| NFR-01 snapshot p95≤500ms | Same5×10;1220events at final60min; p50 462.558/p95 **488.148**/max531.742ms | PASS p95; narrow margin, max is above500 |
| NFR-03 seek state p95≤1000ms | 30sequential seeks + subsequent authorized snapshot, independent time filtering assertion; p50 110.783/p95 **141.646**/max145.762ms | PASS |
| NFR-04 authorized resync≤3000ms | Healthy local ASGI WS reconnect with future after_sequence99999 → RESYNC_REQUIRED→full authorized1220event snapshot; **181.843ms** | PASS |

Environment: Apple M4,10logical CPUs,16GiB RAM,macOS26.3.1 arm64,Python3.12.14,SQLite3.53.1; local filesystem/WAL/FULL sync, single API owner. Five concurrent request streams share one authorized account; this is API client capacity, not five authenticated browser actors. Timing includes routing, auth, serialization and complete response decode. It excludes LAN/TLS/browser. Cadence60seconds is the declared synthetic benchmark profile; no proof for1Hz/continuous high-rate tracks, arbitrary archive shape or target4vCPU/8GiB VM. No requirement threshold was lowered; higher-rate/real B/VM benchmarks must be repeated at integration. Full-size benchmark completed1PASS33.32s; provider_calls0. Two-hour requirement is aggregate cross-channel audio per PRD§5.2, not two2-hour channels.

## Checks dan reproduksi

```sh
.venv/bin/pytest tests/platform -q
FLOWLENS_RUN_CAPACITY=1 .venv/bin/pytest tests/platform/test_acceptance_capacity.py -q
.venv/bin/pytest tests/contracts --track A -q
.venv/bin/pytest tests/contracts --track B -q
.venv/bin/ruff check backend tests scripts
.venv/bin/ruff format --check backend tests scripts
.venv/bin/mypy
.venv/bin/python -m flowlens.contracts.generate --check
.venv/bin/bandit -r backend/flowlens -ll
.venv/bin/pip-audit --local
.venv/bin/uv lock --check
.venv/bin/uv build --out-dir artifacts/reports/a101-dist
.venv/bin/python scripts/checks/scan_secrets.py --report artifacts/reports/a101-tracked-secrets.json
.venv/bin/python scripts/checks/scan_secrets.py --staged --report artifacts/reports/a101-staged-secrets.json
git diff --check
```

Final full platform: 715PASS,1opt-in skip after replay fix; 715 passed, 1 skipped in 182.64s (0:03:02); opt-in benchmark executes separately because normal suite deliberately skips large fixture. Contracts66PASS each A/B; Ruff123files/formatted PASS; mypy78source files PASS; schema drift PASS; lock/build sdist+wheel PASS. Bandit -ll0medium/high;2existing LOW decoder findings and4existing validated-SQL exclusions, no new suppression. pip-audit: no known vulnerabilities in installed audited dependencies; unpublished atc-flowlens skipped, not itself vulnerability-audited. Checks logs/build/profiler live under ignored artifacts/reports; durable measurements and this result summary are committed.

Gitleaks/trufflehog/git-secrets unavailable. Reproducible fallback scanner checks complete tracked files and complete staged files for PEM/Google/AWS/GitHub/Slack known signatures, without printing matched values. This is not entropy/history/full certification. Tracked353files/0matches; staged13complete files/0matches. Staged scan and source/diff review performed before commit; generated schemas/ports/migrations/lock diff empty. No provider/network inference/private corpus/frontend/container/deployment; dependency advisory lookup only. All disposable DB/files/TestClient/native processes close through fixture/lifespan cleanup; no persistent runtime remains.

A10.1 selesai setelah final checks/scan/review dan commit lokal; **A10.2 harus langsung dilanjutkan**, goal tetap active. G-BE `not_started`, Phase10 `planned`, provider verified **NO**, domain **NOT_DOMAIN_VALIDATED**, operational validation **NO**.
