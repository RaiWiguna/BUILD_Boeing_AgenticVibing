# A01.3 — Historical archive migration dan auth deprecation

Tanggal: 9 Oktober 2026, Asia/Jakarta. A01.3/A01/Phase 2.1 **done**; Phase 2 tetap in_progress (2.2–2.4 planned). Input HEAD e24acf5804363dfdb8fb21c3b7a40eecd2abe6ef + working tree A01.1–A01.2/planning; candidate belum commit/push.

## Deliverables

- Static audit pre-reset commit 2660222, storage/session/models/app; [compatibility mapping](../development/legacy-compatibility.md) berdasarkan format yang benar-benar ditemukan.
- Migration `platform.0003` menambah quarantine archive tables, import receipts, original-ID mapping dan private-frame isolation. .0001/.0002 tidak diedit; contract 1.0.0 dan uv.lock tetap.
- `backend/flowlens/storage/sqlite/legacy.py`: read-only bounded source snapshot, finite/unique JSON validation, exact table/column inventory, integrity/reference/key checks; transactional import preserving original IDs/ordinals/times/sequence/command IDs dan verbatim JSON. Logical snapshot digest mendukung retry; changed same-ID conflicts ditolak.
- `backend/flowlens/cli/migrate_archive.py`: explicit separate-source/target maintenance command, safe output/failure, target owner lock, tanpa credentials/runtime simulator.
- `tests/platform/test_legacy.py`: representative synthetic archive mengikuti historical DDL. Persistence tests menggunakan noncolliding test migration IDs dan expected applied-count dari actual manifest sehingga SQL fault tests tetap menguji execution failure, bukan duplicate ID.
- Legacy auth deprecation diuji: old operator setting ditolak; auth/operator, seats dan command paths tetap absent/404 meski legacy credential dikirim. Tidak mengklaim individual auth sudah tersedia.

## Checks

Python 3.12.14/macOS arm64, local disposable SQLite.

| Check | Result |
| --- | --- |
| Initial test-first legacy suite | 14 expected missing-implementation failures, 1 existing deprecation behavior PASS |
| `.venv/bin/pytest tests/platform -q` | 71 PASS: 32 host, 21 persistence, 18 legacy cases |
| `.venv/bin/pytest tests/contracts --track A -q` | 66 PASS |
| `.venv/bin/pytest tests/contracts --track B -q` | 66 PASS |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS |
| Ruff check/format backend/tests/scripts | PASS, format 29 files |
| `.venv/bin/mypy` | PASS, 20 source files |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues |
| `.venv/bin/uv build --out-dir artifacts/reports/a013-dist` | PASS, sdist/wheel |
| CLI subprocess synthetic conversion/failure tests | PASS, safe JSON summary and sanitized errors |
| Documentation local links/fences / final diff whitespace | PASS |

Tests cover original payload/ID preservation, separated private frames, no provider/stream/account writes, source bytes unchanged, interrupted-status disposition, identical retry/conflict, unsupported columns/tables, malformed/nonfinite/overflow/duplicate-key JSON, inconsistent identifiers/ordinal/time, orphan rows, injected mid-import rollback, committed WAL snapshot, same-file rejection and retired auth/routes.

## Limitations / handoff

- Conversion supports the audited four-table profile only; original sessions are preserved in quarantine plus canonical UUID aliases. It is not a completed public replay/source adapter or automatic in-place migration.
- Archived "public" payload can include scenario metadata/seed/assessments. No reader/provider ports expose it here; future A07 compatibility requires explicit eligibility/redaction/grants. Unknown historical availability stays unknown. Private checkpoints are not restored/executed.
- No real operator archive was opened, migrated or sampled. Synthetic preservation pass is not real-corpus fidelity/domain/operational validation.
- Auth bootstrap/login/logout/reset and actual grants remain A02/A03; legacy auth rejection does not prove new auth acceptance.
- CLI target may retain fresh platform schema after source validation failure; import content remains all-or-none. Atomic DB import is not a filesystem backup/restore or source data rights audit.
- No dependency changes, provider calls/smoke/benchmarks, hosted CI, clean wheel install, frontend/containers/deploy. Tests/subprocesses completed with disposable data; ignored build artifacts remain. No persistent runtime and no commit/push/merge.
- Next A02.1: accounts, Argon2id, private bootstrap/reset/deactivation. G-BE/G-FE/G-DELIVERY remain not_started.
