# A01.1 — Host/config/composition Paket A

Tanggal: 8 Oktober 2026 (konteks tanggal pengguna, Asia/Jakarta). Status: **done untuk A01.1**, A01 dan Phase 2.1 tetap `in_progress`. Input HEAD: `e24acf5804363dfdb8fb21c3b7a40eecd2abe6ef` + perubahan lokal dokumentasi perencanaan yang sudah ada. Candidate: working tree, belum commit/push. Contract: 1.0.0, tidak berubah.

## Deliverables dan acceptance

- `backend/flowlens/core/host_config.py`: immutable strict settings, validasi profile/port/loopback, hanya satu API process, parser environment eksplisit. Unknown `FLOWLENS_*` ditolak agar typo tidak diabaikan. Production belum tersedia.
- `backend/flowlens/api/host.py`: composition root A memakai frozen ModuleRegistry/ModuleRegistration; injectable routes/services/repositories/handlers/callbacks melalui registry tanpa dependency pada internals B. Tidak memakai/import storage atau fake implementation dari `flowlens.testing`.
- Fake B disuntikkan secara eksplisit dari harness pada test profile, berlabel MOCK; development menolak mock modules. Incompatible/duplicate registrations dan duplicate/reserved HTTP/WS route keys ditolak sebelum serving.
- Safe HTTP boundary: server-generated UUID request ID, domain code/status frozen, validation locations tanpa input/context, sanitized HTTP/unexpected failures. Exception text dan HTTP exception headers tidak diteruskan. Access logs launcher dinonaktifkan.
- `/health` menunjukkan liveness; `/ready` selalu 503/false/HOST_ONLY untuk fase ini; `/release.json` hanya safe identifiers. Module callbacks tidak dapat menaikkan readiness menjadi production-ready.
- `backend/flowlens/api/serve.py`: launcher lokal, workers=1, reload=false, bind loopback; invalid config berhenti dengan pesan aman tanpa mencetak values. Tidak ada harness validators pada host A; baseline app/schema generation tetap terpisah.

## Performed checks

Environment: existing .venv, Python 3.12.14, macOS arm64. Dependency/lock tidak berubah.

| Pemeriksaan | Hasil |
| --- | --- |
| Test-first `pytest tests/platform/test_host.py -q` sebelum implementation | 32 failures karena host/config/launcher belum tersedia |
| `.venv/bin/pytest tests/platform/test_host.py -q` pada final source | 32 PASS |
| `.venv/bin/pytest tests/contracts --track A -q` | 66 PASS |
| `.venv/bin/pytest tests/contracts --track B -q` | 66 PASS |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS, baseline OpenAPI/JSON Schema tidak berubah |
| `.venv/bin/ruff check backend tests scripts` | PASS |
| `.venv/bin/ruff format --check backend tests scripts` | PASS, 21 files |
| `.venv/bin/mypy` | PASS, 14 source files |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues |
| Real subprocess `.venv/bin/python -m flowlens.api.serve` pada disposable loopback port | PASS, HTTP /health 200 dan /ready 503 HOST_ONLY; process dihentikan dan awaited |
| Local documentation links/fences dan `git diff --check` | PASS |

Tests mencakup invalid/multiworker/boolean config, external worker environment overrides, immutable settings, explicit fake registration, reserved/duplicate routes, incompatible module versions, safe domain/validation/HTTP/unexpected errors dan launcher fail-closed. Live smoke tidak membuka DB, memanggil provider atau membuat persistent runtime.

## Limitations / next action

- Single-process enforcement tersedia pada settings dan supported launcher. Menjalankan arbitrary external process manager/uvicorn command atau dua launcher bersamaan belum dicegah dengan database ownership lock; persistence/ownership lifecycle menjadi scope A01.2. Tidak mengklaim runtime multi-process lock sudah teruji.
- Config mendukung hanya profile/host/port/api_workers pada environment. Tidak membaca `.env`, credentials, DB paths atau provider profiles; tambahkan setting sesuai unit owner berikutnya.
- Host transport menambahkan `INTERNAL_ERROR`, `NOT_FOUND`, `HTTP_ERROR` untuk fallback lokal; domain ErrorResponse dan shared contracts 1.0.0 tetap utuh. Business OpenAPI/generated client freeze tetap Phase 10.
- Route collision checks membandingkan path/method keys; ini bukan auth policy atau audit lengkap equivalence parameterized routes. Auth/CSRF/grants/WS lifecycle belum tersedia.
- Persistence/migrations/UOW, historical migration, imports/replay/geometri/jobs/provider analysis belum tersedia. Host tidak menjalankan migrations, readiness probes DB/assets, provider checks atau readiness callbacks pada fase ini.
- Build/clean wheel install, dependency audit/hosted CI, provider smoke/benchmark dan domain review tidak dijalankan ulang dalam task ini. Dependency manifest/lock tidak berubah. Scoped lint/type/tests/Bandit bukan full security audit.
- G-BE/G-FE/G-DELIVERY tetap `not_started`. Next unit A01.2; A01.3 tetap planned. Tidak ada commit/push/merge/deploy.
