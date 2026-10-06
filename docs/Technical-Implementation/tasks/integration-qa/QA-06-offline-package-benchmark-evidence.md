# QA-06 — Offline package dan benchmark evidence

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** Pada 6 Oktober 2026, backend source dan Vite UI berhasil dijalankan bersama di localhost; flow UI API-mode berhasil login, membuat sesi synthetic, dan membaca snapshot. Package tests pada repository mock lulus dan benchmark source/detector/SQLite lulus 100/100. Package offline aktual masih gagal preflight karena Python lock/wheelhouse tidak tersedia. Packaged cold runtime, normalized source replay, reconnect, LAN, endurance, provider/ASR, domain review, dan validasi operasional belum dibuktikan.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan paket lokal yang cold-run tanpa download dan laporan technical benchmark yang memisahkan compute/delivery/replay/AI measurements.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE (setelah full-stack run 6 Oktober 2026):** Python runtime dependencies tersedia tanpa `requirements.lock`/`wheelhouse/`. Vite frontend dependencies dipasang dari `package-lock.json`; `frontend/dist/index.html` berhasil dibangun. QA-01 raw F-REPLAY-01 fixtures ada, tetapi QA-05 direct import ditolak HTTP 422 oleh strict normalized DTO; projection QA-05 bukan canonical mapping. QA-04 launcher tersedia sebagai mock stack saja. Provider adapter/model assets tidak tersedia.

**TARGET:** Offline packaging/backup/version manifest, synthetic cold-run tests, benchmark/endurance and optional ASR quality reporting. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [pyproject.toml](../../../../pyproject.toml)
- [frontend/package.json](../../../../frontend/package.json)
- [backend/app.py](../../../../backend/app.py)
- [backend/storage.py](../../../../backend/storage.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §14.4, §15.3–15.7, §16.4–16.6, §18.7.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Deliverable QA-06:** `scripts/package_offline.py`, `tests/integration/test_offline_package.py`, `tests/integration/test_performance.py`, dan `tests/fixtures/replay/benchmark-manifest.json`.

QA package tooling/tests only; BE-08 owns backend provisioning/backup implementation, FE-01 owns build/lock, AI owns provider adapters. Benchmark manifest file reserved QA-06; QA-01 authors canonical data others. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. QA-03 tidak mengedit reserved tests/integration/test_offline_package.py/test_performance.py; benchmark manifest bukan file QA-01.

## 4. Kontrak dan dependency

**Contract:** SC-01–07. Built frontend+runtime locks/source/schema/config/layout/scenario/model manifest→offline package and actual measured report; no unauthorized partner payload default.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md), [QA-03](../integration-qa/QA-03-backend-worker-integration-failures.md), [QA-05](../integration-qa/QA-05-browser-replay-review-flows.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Stub-provider package valid explicitly mock-labeled; model missing test no download; canonical synthetic scenario bundle.

**Integration dependency:** BE-08 runtime+all feature outputs; ASR/provider real metrics conditional actual assets, no claiming validation from stubs.

## 5. Pendekatan implementasi

1. Implementasikan package_offline.py --output tmp/flowlens-offline; kumpulkan frontend build mode API, runtime locks serta version/hash manifest. Required artifact yang hilang menggagalkan packaging; AI opsional yang hilang tetap berlabel unavailable.
2. Jangan memasukkan credential/private truth/audio ke public static bundle; default package hanya data sintetik. Runtime membuat storage privat lokal; backup memakai SQLite backup API.
3. Cold-run dengan network disabled tanpa download/cloud fallback; uji source replay saat AI unavailable, lalu job/evidence/review saat model provisioned.
4. Benchmark 12 canonical scenarios dan 100 run pada plan: 40 conflict/40 safe/10 delay-noise/10 dropout. Bekukan seeds/parameter, pisahkan tuning/denominator; default tanpa intervention.
5. Ukur detector/delivery/render/reconnect/sync/endurance terpisah dengan environment manifest dan target kanonis. Metrics ASR/candidate per corpus/model hanya dilaporkan jika provider benar-benar dijalankan.

## 6. Output yang harus diserahkan

Paket offline sintetik dan laporan technical evidence aktual beserta batas klaim; tanpa deployment live atau klaim validasi domain/operasional.

## 7. Asumsi dan unknown

**ASSUMPTION:** Satu RUNNING session dengan baseline 5 aircraft+2 vehicles; model/dependency diprovision. Hasil localhost dan real LAN diberi label berbeda.

**UNKNOWN:** Cold-run compatibility, resource use, ASR quality dan fidelity data mitra belum diukur. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-06 owns reserved offline/performance tests. Command dan acceptance berikut adalah target; hasil aktual per 6 Oktober 2026 dirangkum di §9.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Package inputs | Built UI+version locks and optional model missing | `python scripts/package_offline.py --output tmp/flowlens-offline` | Artifact manifest precise, credentials/private exports excluded; missing required artifact explicit failure. |
| Negative cold-run | Network disabled, optional model unavailable | `python -m pytest tests/integration/test_offline_package.py` | No downloads/cloud calls; source replay still usable and AI unavailable explicit. |
| Benchmark bookkeeping | Frozen synthetic strata; independent QA-01 labels unavailable | `python -m pytest tests/integration/test_performance.py` | 100 manifest runs remain in denominator; compute/persistence measured separately; recall/false-warning/lead-time unavailable without independent oracle. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Performance/endurance | Complete runtime+hardware/browser/LAN manifest | `python -m pytest tests/integration/test_performance.py` | Available measurements compared with plan targets; missing source replay, LAN, browser timing, or endurance explicitly unavailable/not run, never reported pass. |
| Package lifecycle | Cold boot→replay/job/review→backup/restart | `python -m pytest tests/integration/test_offline_package.py` | Accepted events/receipts/revisions survive; source private/public isolation and no command option path. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.

## 9. Hasil QA-06 historis — 6 Oktober 2026

Catatan berikut berasal dari run QA-06 sebelumnya dan bukan bukti checkout/rerun QA-06 saat ini. Report historis tetap disimpan pada path yang ditautkan di §9; hasil checkout terkini ada di §10.

### Source dan dependency

- QA-06 menambah empat file yang tercantum pada §3. Backend/FE/launcher source tidak diubah.
- Source yang tersedia: katalog 12 skenario sintetik, `Simulator.delivered`, `detection.detect`, SQLite `Archive`, dan `frontend/dist/index.html`.
- QA-01 canonical fixture bundle belum tersedia (folder replay hanya memuat manifest benchmark QA-06); QA-03 integration suites belum tersedia; QA-05 browser suite dan run manifest tersedia; `scripts/run_mock_stack.py` QA-04 belum tersedia.
- Python runner 3.13.14 dan dependency runtime/dev yang diperlukan untuk test tersedia. `requirements.lock` dan `wheelhouse/` tidak tersedia. Model/provider AI tidak tersedia.

### Build dan package

- FE build tidak dijalankan ulang; file `frontend/dist/index.html` yang sudah ada dipakai sebagai input pemeriksaan.
- `python scripts/package_offline.py --output tmp/flowlens-offline` — **failed** saat preflight: `requirements.lock` dan `wheelhouse/` wajib tidak ada. Package tidak dibuat dan folder output tidak dibuat. Test helper yang lulus di bawah memakai repository mock sementara, bukan package ini.

### Cold runtime dan automated test

- Cold runtime dengan network disabled: **not run / unavailable**, karena package nyata tidak terbentuk. Tidak ada bukti cold boot, install offline, replay/job/review lifecycle, backup, atau restart.
- `python -m pytest tests/integration/test_offline_package.py` — **3 passed**. Ini menguji allowlist/hash/credential exclusion dan preflight pada repository sementara berlabel mock; bukan bukti package source aktual berjalan offline.
- `python -m pytest tests/integration/test_performance.py` — **2 passed** pada final run. Percobaan awal menemukan typo hash katalog di manifest; diperbaiki sebelum run final. Report dari pengembangan sebelumnya dipertahankan; hanya report final dengan hash manifest saat ini yang menjadi evidence di bawah.

### Benchmark teknis

Manifest tetap berisi 12 skenario source, dengan S11/S12 hanya untuk workflow dan tidak masuk strata hazard. Ada 100 run tetap: 40 conflict, 40 safe, 10 delay/noise, 10 dropout. Sepuluh detector warm-up dikecualikan; seluruh 100 run evaluasi tercatat (tidak ada run yang dibuang). Semua input adalah synthetic fixture/mock, bukan QA-01 oracle independen. Dropout dibuat dengan filter observasi QA-06; ini bukan network dropout terukur.

Final report: [QA-06 performance run](../../../../tmp/qa06-performance-20261006T123620051189+0700.json).

| Measurement | Sampel | Hasil lokal aktual | Batas interpretasi |
|---|---:|---:|---|
| Detector compute | 100 | p50 2.10895 ms; p95 2.377 ms; max 4.6145 ms | Di bawah target detector p95 <50 ms pada microbenchmark synthetic 5 aircraft/2 vehicle saja; bukan bukti akurasi/domain atau kesiapan operasi. |
| SQLite `Archive.create` + `Archive.save` | 100 | p50 1.478 ms; p95 2.2651 ms; max 2.8732 ms; 100 session/event/frame tersimpan | Bukan backup/recovery/endurance measurement. Database temporary tidak disalin sebagai package. |
| API delivery/browser render, reconnect, LAN clock sync, endurance 30 menit | — | delivery/render **unavailable**; reconnect/LAN/endurance **not run** | Tidak ada additive replay API/QA-04 launcher, browser timing, atau mesin LAN kedua dalam benchmark ini. |
| ASR/provider dan accuracy (recall/false warning/lead time) | — | AI **unavailable**; accuracy **unavailable** | Provider/model dan QA-01 independent private labels/oracle tidak tersedia. |

Environment: Windows 11 build 26200, Python 3.13.14, SQLite 3.50.4; OS CPU descriptor `Intel64 Family 6 Model 140 Stepping 1, GenuineIntel` (8 logical CPUs), RAM 16,856,219,648 bytes (~15.7 GiB); FastAPI 0.136.1, Uvicorn 0.46.0, Pydantic 2.13.3, Shapely 2.1.2, pytest 9.0.3, psutil 7.1.3. Input disiapkan dari simulator lokal selama 1.0 simulated second per run (100 simulated seconds total); benchmark wall time final 0.3842 s, warm-up 10 evaluations. Hasil hanya localhost/in-process; tidak ada LAN topology atau browser version yang diukur.

### Domain review dan validasi operasional

Domain review trainer/ATCO: **belum dilakukan**. Validasi operasional, partner data/replay, LAN multi-machine, dan kesiapan penggunaan aktif: **belum dilakukan**. Tidak ada klaim validitas domain atau kesiapan operasional dari hasil teknis ini.

## 10. QA-06 rerun sebelum setup Vite — 6 Oktober 2026

### Checkout, source, dan dependency

- Worktree: `C:\Users\ASUS\.codex\worktrees\qa04-mock-stack-launcher\BOEING BUILD`; branch `codex/qa04-mock-stack-launcher`; HEAD `1d4e3d044e9cf512f0b2bdeeae6692833cc448be`. Perubahan QA-04/05 dan browser artifacts dipertahankan.
- QA-06 memperbarui empat source hashes yang kedaluwarsa pada benchmark manifest agar cocok dengan byte source checkout saat ini. Harness persistence kini menyediakan `public.metadata` sesuai kontrak `Archive.save`. Parameter, seed, strata, denominator, dan warm-up tidak berubah.
- Python 3.13.14, pytest 9.0.3, Node 24.19.0, npm 11.17.0; FastAPI 0.136.1, Uvicorn 0.46.0, Pydantic 2.13.3, Shapely 2.1.2, SQLite 3.50.4, psutil 7.1.3, packaging 25.0, Playwright 1.60.0. `faster-whisper` library 1.2.1 terpasang, tetapi `backend/ai_harness/` dan `assets/ai/` tidak ada; tidak ada provider/model run.
- `frontend/package.json` mencantumkan Vite 8.3.2, tetapi `frontend/node_modules/`, executable Vite lokal, dan `frontend/dist/index.html` tidak ada. `requirements.lock` dan `wheelhouse/` juga tidak ada. Tidak ada dependency/model yang diunduh atau dipasang.
- QA-01 raw F-REPLAY-01 bundle tersedia; QA-05 melaporkan direct import HTTP 422 terhadap strict normalized DTO. Projection khusus test QA-05 tidak dipakai sebagai canonical input. `scripts/run_mock_stack.py` QA-04 tersedia, tetapi hanya launcher mock dan bukan source replay runner.

### Package, cold runtime, dan test

- `python scripts/package_offline.py --output tmp/qa06-package-preflight-verified-20261006T080231542Z` — exit 2, **preflight failed**. Missing: `requirements.lock`, `frontend/dist/index.html`, built `frontend/dist/`, dan `wheelhouse/`. Output target tidak dibuat. Diagnostic menyebut raw QA-01 import 422 dan QA-04 mock-only secara tepat. Package aktual tidak terbentuk sehingga cold runtime/offline install tidak dijalankan.
- `python -m pytest -q tests/integration/test_offline_package.py` — **3 passed**. Positive package assembly hanya memakai repository sementara/mock; ia memeriksa allowlist, hash artifact package mock, credential/private/audio exclusion, no-network guard, serta failure eksplisit saat required input hilang. Ini bukan package build source checkout.
- `python -m pytest -q tests/integration/test_performance.py` — **2 passed** pada final run. Run awal gagal karena source hashes stale dan `public.metadata` tidak disediakan; report gagal itu dipertahankan: [initial failed run](../../../../tmp/qa06-performance-20261006T145504436839+0700.json). Setelah perbaikan, semua 100 run terukur.

### Benchmark teknis aktual

Report final: [QA-06 performance evidence](../../../../tmp/qa06-performance-20261006T145853289493+0700.json). Hash manifest di report cocok dengan manifest checkout. Input: current source synthetic simulator → `detect` → temporary SQLite `Archive`; 100 total simulated seconds (1 s/run), tanpa intervention. Sepuluh detector warm-up dikecualikan. Semua 100 manifest runs tetap dalam denominator dan terukur; strata conflict 40, safe 40, delay/noise 10, dropout 10. Dropout adalah filter target observasi harness, bukan packet/network dropout.

| Measurement | Sampel | Hasil aktual | Batas klaim |
|---|---:|---:|---|
| Detector compute | 100 | p50 2.1608 ms; p95 3.1037 ms; max 4.5146 ms | Di bawah target awal p95 <50 ms hanya untuk microbenchmark source synthetic 5 aircraft/2 vehicles; tidak mengukur akurasi atau replay end-to-end. |
| SQLite `Archive.create` + `Archive.save` | 100 | p50 1.37055 ms; p95 1.9888 ms; max 2.2856 ms; 100 sessions/events/frames | Bukan backup, recovery, restart, atau endurance measurement. |
| API delivery/browser render | — | Unavailable | Raw QA-01 input tidak diterima importer; QA-04 launcher mock-only; browser timing tidak diukur. |
| Source replay/reconnect/LAN/endurance 30 menit | — | Not run | Tidak ada normalized source replay runner/browser build, mesin LAN kedua, atau sesi endurance. QA-04 mock reconnect bukan replay performance evidence. |
| ASR/provider dan recall/false-warning/lead-time | — | Unavailable | Provider adapter/model tidak tersedia; independent labels/oracle valid tidak diperiksa/dipakai. Accuracy tidak dihitung dari mapping benchmark QA-06. |

Environment benchmark: Windows 11 build 26200, Python 3.13.14, SQLite 3.50.4; OS CPU descriptor `Intel64 Family 6 Model 140 Stepping 1, GenuineIntel`, 8 logical CPUs, RAM 16,856,219,648 bytes; FastAPI 0.136.1, Uvicorn 0.46.0, Pydantic 2.13.3, Shapely 2.1.2, pytest 9.0.3, psutil 7.1.3. In-process/temporary SQLite; browser tidak diukur dan tidak ada LAN topology.

### Domain review dan validasi operasional

Trainer/ATCO review, partner replay/fidelity, human-factors/safety review, dan validasi operasional **belum dilakukan**. Angka di atas adalah hasil teknis lokal pada synthetic inputs saja.

### Smoke run backend source lokal

- Backend dijalankan langsung dari checkout dengan `uvicorn.run(create_app(...))`, bind `127.0.0.1:18765`; database SQLite dan audio root berada di `tmp/qa06-local-run-20261006T100520624Z/`. Operator key bersifat ephemeral dan tidak disimpan pada artifact report.
- Startup/shutdown Uvicorn berhasil. `GET /health` → 200 (`synthetic-training`, `single_writer=true`); `GET /api/v1/scenarios` → 200, 12 skenario; operator login dan `GET /api/v1/runtime-manifest` → 200 (`SQLite WAL`, assist worker dan local model unavailable).
- Sesi synthetic `safe_cross` berhasil dibuat (201). Perintah START dan PAUSE diterima; snapshot maju dari `sim_ms=0` ke `1200`, memuat 7 observed tracks, dan berakhir `PAUSED` pada revision 4. Ini membuktikan backend source lokal berjalan pada smoke flow terbatas, bukan package offline atau replay QA-01.
- Process dihentikan dengan shutdown bersih; PID tidak lagi berjalan dan tidak ada listener pada port 18765. [Smoke-run summary](../../../../tmp/qa06-local-run-20261006T100520624Z/runtime-smoke-result.json).
- Pada backend-only smoke run tersebut, frontend browser belum dijalankan karena Vite/dependency dan `frontend/dist/index.html` belum tersedia. Vite/full-stack follow-up ada di §11. Cold install package, source replay import, AI, domain review, dan validasi operasional tetap tidak dibuktikan.

## 11. Vite dan full-stack run — 6 Oktober 2026

### Setup

- `npm ci --prefix frontend --no-audit --no-fund` — berhasil; 26 package ditambahkan dari `package-lock.json` dalam 25 detik. `package.json` dan lockfile tidak diubah.
- `frontend/vite.config.ts` kini menetapkan host `127.0.0.1`, port `5173`, `strictPort: true`, serta proxy `/api` (termasuk WebSocket) dan `/health` ke backend `127.0.0.1:8000`.
- Browser smoke awal menemukan render loop pada `AlertEvidence`: array fallback kosong dibuat ulang tiap render dan memicu effect berulang saat belum ada frame. Nilai fallback dijadikan konstanta stabil di `frontend/src/features/runway/AlertEvidence.tsx`.
- `npm --prefix frontend run build` — berhasil setelah perbaikan; TypeScript build lulus dan Vite 8.3.2 menghasilkan bundle `frontend/dist/`.

### Runtime dan browser verification

- Backend source berjalan di `127.0.0.1:8000` memakai SQLite sementara; Vite dev server berjalan di `127.0.0.1:5173` dengan `VITE_FLOWLENS_MODE=api`. Kedua listener aktif saat pencatatan ini.
- Playwright Chromium membuka UI API-mode; health dan 12 skenario termuat. Login operator berhasil; UI membuat sesi `safe_cross` (`572123e332a0`, HTTP 201), memilih sesi itu, lalu membaca snapshot dan event history (HTTP 200). Tidak ada console error setelah perbaikan render loop.
- Dua request awal `/health` dan `/api/v1/scenarios` tercatat dibatalkan saat StrictMode membersihkan effect awal; request berikutnya berhasil HTTP 200. Tidak ada error browser sesudah load.
- [Browser smoke result](../../../../tmp/qa06-user-run-20261006T101645370Z/full-stack-browser-check.json) · [UI screenshot](../../../../tmp/qa06-user-run-20261006T101645370Z/full-stack-ui-session.png).
- Operator key hanya untuk proses lokal sementara: `qa06-ephemeral-local-run-only`. Jangan pakai key ini untuk environment lain.

### Batas full-stack run

- Run ini memverifikasi dashboard + current synthetic-training API/session path. Source replay QA-01 import, evaluator replay/assist profile, provider/ASR, LAN, dan domain flows tidak diuji; tidak ada klaim validasi domain atau kesiapan operasional.
- Package offline aktual tetap gagal preflight setelah Vite build: `python scripts/package_offline.py --output tmp/qa06-package-preflight-post-vite-20261006T102551425Z` — exit 2 karena `requirements.lock` dan `wheelhouse/` tidak tersedia. `frontend/dist/` kini tersedia, tetapi cold package install/run tetap **not run**.
