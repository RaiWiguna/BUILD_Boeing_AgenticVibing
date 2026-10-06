# QA-06 — Offline package dan benchmark evidence

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** Implementasi QA-06 tersedia di file ownership task per 6 Oktober 2026. Test package memakai repository mock lulus; benchmark sintetik source/detector/SQLite aktual tercatat. Package nyata gagal preflight karena `requirements.lock` dan `wheelhouse/` tidak tersedia. Cold runtime, integrasi source replay, domain review, dan validasi operasional belum dibuktikan.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan paket lokal yang cold-run tanpa download dan laporan technical benchmark yang memisahkan compute/delivery/replay/AI measurements.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE (6 Oktober 2026):** Python project dependencies belum mempunyai lock penuh/wheelhouse; `frontend/dist/index.html` tersedia; QA-01 canonical bundle dan QA-04 launcher tidak tersedia; provider/model assets AI tidak tersedia. Benchmark report di packet ini adalah source synthetic lokal, bukan LAN/study result.

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

## 9. Hasil QA-06 — 6 Oktober 2026

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
