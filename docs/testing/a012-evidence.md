# A01.2 — Platform SQLite, migrations, repositories dan UOW

Tanggal: 9 Oktober 2026, Asia/Jakarta. Status: **A01.2 done**; A01/Phase 2.1 tetap `in_progress`, next A01.3 historical archive compatibility. Input HEAD `e24acf5804363dfdb8fb21c3b7a40eecd2abe6ef` + working tree A01.1 dan dokumentasi perencanaan. Candidate belum commit/push. Contract 1.0.0 dan dependency lock tidak berubah.

## Deliverables

- `backend/flowlens/storage/sqlite/schema.py`: migrations `platform.0001` dan `platform.0002`; accounts/grants/sessions/revisions/runs serta sources/assets/jobs/attempts/receipts/records/evidence/events/audit/replay/artifacts. Composite scoped FKs, unique keys dan basic checks. Tidak membuat tabel `analysis_*`.
- `migrate.py`: deterministic dependency order dari frozen MigrationSpec; immutable checksum mencakup ID/owner/dependencies/SQL, applied-history/downgrade checks, atomic pending batch dan FK validation. Parser menangani SQL literals/triggers dengan semicolon. Authorizer melarang transaction control, PRAGMA, ATTACH/DETACH dan akses migration ledger oleh migration SQL.
- `database.py`: private local DB, POSIX advisory owner lock sepanjang lifetime, WAL/FULL synchronous/FK, serial API-owned transactions, close/rollback/commit discipline. Session/run tidak dibuat otomatis oleh append. File DB baru mode 0600; existing insecure DB dan direct symlink ditolak.
- `repository.py`: typed append/get untuk `source_events` (SourceEvent/Track) dan `evidence` (Evidence), fixed parameterized SQL, capabilities dan exact session/run/revision scope. Duplicate append ditolak; retained repository tidak dapat dipakai setelah UOW ditutup. Namespace `analysis`/`analysis.*` dapat di-inject dengan factory melalui connection dan lifecycle guard yang sama; tidak ada implementasi B nyata.
- UOW menyediakan repository, session sequence, bounded audit identifier, after_commit, explicit commit/rollback. Missing commit/exception/failed commit membatalkan writes dan callbacks. Publikasi dilakukan setelah connection ditutup dan transaction mutex dilepas; callback gagal tidak menghapus committed state, callback lain tetap dicoba, lalu caller menerima durable-publication error.
- Host config menambah optional `database_path`/`FLOWLENS_DB_PATH`; host membuka/migrates DB pada lifespan dan melepas owner saat shutdown/startup failure. Fake migration registrations tidak dijalankan. Invalid startup disanitasi tanpa path/SQL detail. `/ready` tetap 503 karena auth/domain/coordinator belum lengkap.

## Performed checks

Environment: existing .venv, Python 3.12.14, macOS arm64/local disposable SQLite. Tidak memasang dependency baru.

| Command / cakupan | Hasil |
| --- | --- |
| Initial test-first persistence suite | 14 failures karena persistence/lifespan belum tersedia; tambahan case startup sanitation diuji RED sebelum perbaikan |
| `.venv/bin/pytest tests/platform -q` | 53 PASS: 32 host + 21 persistence cases |
| `.venv/bin/pytest tests/contracts --track A -q` | 66 PASS |
| `.venv/bin/pytest tests/contracts --track B -q` | 66 PASS |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS, shared schemas/OpenAPI tetap |
| `.venv/bin/ruff check backend tests scripts` | PASS |
| `.venv/bin/ruff format --check backend tests scripts` | PASS, 26 files |
| `.venv/bin/mypy` | PASS, 18 source files |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues; dynamic query construction diganti fixed SQL tanpa suppressions |
| `.venv/bin/uv build --out-dir artifacts/reports/a012-dist` | PASS, sdist dan wheel |
| Two real host subprocess starts dengan `FLOWLENS_DB_PATH` temp | PASS: liveness, owner rejection, persistent session ID setelah restart, SQLite integrity check dan readiness 503 |
| Documentation local links/fences, final diff/whitespace | PASS |

Cases meliputi fresh/upgrade, ID preservation, checksum drift/downgrade, failed/malicious SQL rollback, trigger parsing, untouched unversioned archive, cross-process owner denial/release, scoped FK dan receipt uniqueness, permission/scope/type denial, no automatic scope creation, missing commit/exception/deferred-FK commit failure, callback durability, repository extension guard, session-scoped sequences, 12 concurrent writes, unsafe paths, host lifespan dan sanitized startup failure.

## Limitations dan gate impact

- Migrations ini adalah **schema aplikasi baru**, bukan historical archive migration. Existing unversioned DB ditolak; mapping archive/operator-key lama dan historical IDs/events/frames/commands merupakan A01.3.
- Tabel foundation mempunyai keys/relations dan minimal metadata; lifecycle columns/stores/service behaviors ditambahkan lewat migrations baru pada A02–A09. Schema keberadaan jobs/accounts bukan job coordinator/auth yang sudah berjalan. Generic source-event/evidence repositories tidak menggantikan source eligibility/evidence semantic resolution services A04/A05/A07.
- RequestContext diasumsikan dibangun trusted server; grants/revocation/CSRF belum diimplementasikan. Repository belum menjadi REST endpoint. Read as-of/availability filtering tetap scope replay.
- Direct `UnitOfWork.connection` adalah trusted internal extension boundary, bukan API worker/model/browser. SQL dari modul adalah code-owned, bukan user input; authorizer menjaga transaksi/ledger, bukan sandbox seluruh SQL namespace.
- Ownership lock adalah POSIX advisory pada canonical local path; hanya runtime yang mematuhi lock berpartisipasi. Windows/network filesystem/hard-link aliases, filesystem tampering dan cross-platform deployment tidak dibuktikan. Lock file tidak dihapus saat release untuk mencegah inode race; OS melepas flock saat process mati.
- Semua transaksi, termasuk reads, memakai `BEGIN IMMEDIATE` dan serial mutex pada fondasi ini; tuning read-only throughput menunggu measurement. Provider calls/long jobs tidak boleh berada di dalam UOW.
- Backup/restore/retention/disk-full fault injection bukan acceptance unit ini; bagian A09. Batch migration rollback dan deferred-FK failure sudah teruji, tetapi bukan seluruh recovery matrix.
- Clean wheel install/dependency audit/hosted CI/provider smoke/benchmark/domain review tidak dijalankan di unit ini. Build artifacts tersedia lokal di ignored reports. Tidak ada real B integration/front-end/container/deployment.
- Semua test DB disposable, subprocess smoke dihentikan, temp DB dihapus; tidak ada runtime persisten tersisa. G-BE/G-FE/G-DELIVERY tetap `not_started`.
