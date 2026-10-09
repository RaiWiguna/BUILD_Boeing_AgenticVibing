# A03.3 — Append-only audit, optimistic version dan durable idempotency

Tanggal: 9 Oktober 2026, Asia/Jakarta. Input cdb2b9d + uncommitted A03.1–A03.2. Prasyarat source/transport/permissions dan 109 scoped tests PASS diperiksa sebelum implementasi. A03.3/A03/Phase2 done; next A04.1. Contract/ports1.0.0 dan lock unchanged; platform.0007 additive, committed0001–0005 checksums verified unchanged;0006 tidak diedit.

## Deliverables dan acceptance

- storage/sqlite/mutations.py: immutable trusted operation registry, typed/canonical payload, human-only live authority, scoped optimistic counters, same-key receipt replay/conflicts dan one-UOW coordinator dengan persisted-result verification melalui Repository ports.
- platform.0007: scoped versions/receipts + FK ke revision/run/aggregate/event/audit, audit/receipt insert/replace/update/delete protections. Existing historical audit rows preserved.
- UnitOfWork: runtime authorizer, coordinator commit/rollback ownership, rollback-only after illegal transaction attempt; recursive_triggers. enqueue_event menerima read+review atau read+analysis, sehingga reviewer tidak perlu analysis grant untuk published annotation. Domain authorization tetap handler/repository owner.
- Host composition menyediakan mutation_operations dan app.state.mutations; default empty registry dan readiness503. Tidak ada production/domain mutation route baru. 58 tests pada tests/platform/test_mutations.py, synthetic handlers/SQLite/Argon2/TestClient dan fake registered review repository melalui frozen ports.
- Existing A03.1 upgrade test dipin ke boundary0005→0006 agar penambahan0007 tidak mengubah arti fixture. Assertions lama tetap dipertahankan.

Coverage: all three audit tables update/delete/replace denial; same key one effect/receipt, canonical key order/new request nonce, changed payload/expected version conflict, stale/new version and old receipt after later mutation, concurrent same-key/different-key requests, invalid key/version, revoked/logout/expired/forged retry, worker bypass denial, missing real context guard, persisted-result verification, callback commit/rollback/raw commit/caught commit prevention, atomic domain/evidence/version/audit/event/receipt rollback, deferred commit failure, durable publication failure/retry, restart, fresh/upgrade/FK checks, safe minimal hashed receipt/audit, review-only port injection, HTTP200 retry/409 conflicts/500 safe failure and lifecycle cleanup.

## Performed checks

Python3.12.14/macOS arm64; real SQLite/Argon2, disposable DBs and synthetic principals. No real account/data/provider access.

| Check | Result |
| --- | --- |
| Initial append-only audit test | RED: UPDATE existing audit accepted |
| Initial mutation coordinator test | RED: service belum tersedia |
| Worker/general coordinator regression | RED: worker tanpa lease dapat commit; denied after fix |
| Persisted-result regression | RED: callback return tanpa repository write memberi receipt; assertion retained, read-back added |
| Independent SQLite receipt replacement regression | RED: composite-key replacement dengan UUID baru diterima; insert identity guard added |
| `.venv/bin/pytest tests/platform -q` | PASS, 277 (219 prior +58 new) |
| `.venv/bin/pytest tests/contracts --track A -q` | PASS, 66 |
| `.venv/bin/pytest tests/contracts --track B -q` | PASS, 66 |
| `.venv/bin/ruff check backend tests scripts` | PASS |
| `.venv/bin/ruff format --check backend tests scripts` | PASS, 42 files |
| `.venv/bin/mypy` | PASS, 28 source files |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues |
| `.venv/bin/uv build --out-dir artifacts/reports/a033-dist` | PASS, sdist/wheel |
| Committed migration checksum comparison via AST/HEAD | PASS,0001–0005 unchanged |
| Changed Markdown links/fences/whitespace + `git diff --check` | PASS |

## Limits dan cleanup

Infrastructure + synthetic operation acceptance saja. Actual target lifecycle/readers/rights semantics dan bookkeeping initialization milik future owner; namespace/version0 bukan automatic domain existence. Existing trusted account/grant management tidak otomatis memakai HTTP idempotency. Real B, worker accepted-result lease coordinator(A06), replay sequence delivery/resync(A07), audit/privacy/purge maintenance(A09) belum dilakukan. Append-only SQL bukan forensic cryptographic log atau proteksi terhadap privileged DB-file replacement. HTTP evidence memakai TestClient, bukan live network deployment.

Disposable DB owners/TestClient/thread pools/connections closed; ignored a033-dist build tersedia. Tidak ada persistent runtime/worker/container, real accounts/data migration, provider calls, commit/push/merge/deploy. G-BE/G-FE/G-DELIVERY tetap not_started/readiness503. [Workflow](../development/mutation-consistency.md). Next A04.1; A04 dan integrasi B tidak dikerjakan pada sesi ini.
