# Status Implementasi ATC FlowLens

- **Pemeriksaan source/build terakhir:** 6 Oktober 2026
- **Progress FE-01 sampai FE-05 diperiksa:** 6 Oktober 2026
- **Cakupan:** typed adapter FE-01/FE-02; source context, runway map/board, deterministic evidence FE-03; event history timeline, playback/seek controls, transcript/audio state UI FE-04; transcript provenance, candidate evidence review, correction/review editor, debrief FE-05
- **Build FE-05** dari `frontend/`: `npm run typecheck` dan `npm run build` lulus pada 6 Oktober 2026. Ini bukti build FE, bukan runtime atau browser test.
- **Command aktual QA-05** dari root repository pada 6 Oktober 2026: `python -m pytest tests/browser -k 'fe_ or mock_stack or adapter_parity'` — 8 passed, 1 xfailed; `python -m pytest tests/browser/test_options_boundary.py` — 6 passed; `python -m pytest tests/browser` — 16 passed, 1 xfailed. Lihat bagian QA-05 di bawah.
- **QA-01** pada 6 Oktober 2026: canonical public/private fixture data, exact-byte hash manifests, 12-scenario mapping, dan independent authored oracles tersedia. Python data-integrity inspection selesai; QA-02 fixture suite not run karena suite belum ada. Lihat bagian QA-01 di bawah.
- **QA-06** pada 6 Oktober 2026: offline package preflight gagal karena `requirements.lock`/`wheelhouse/` tidak tersedia; cold runtime unavailable. Mock package tests 3 passed; synthetic current-source benchmark 2 passed, 100/100 run terukur. Lihat bagian QA-06 di bawah.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, model kontrak, simulasi, deteksi, sesi, review, laporan, dan arsip SQLite tersedia di `backend/`. QA-05 menjalankan instance lokal dari source dengan temporary SQLite dan throwaway test key. | Login, create/end/open review, seat role scope dan participant denial dites; bukan uji recovery, persistensi correction, beban, atau concurrency. |
| API dan stream | Source mendefinisikan route health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, dan WS direct snapshot. FE adapter dapat meminta review beku lewat route `POST .../reviews`, menyimpan token review-control dalam memory, lalu memakai command `START/PAUSE/SET_SPEED/SEEK`; SEEK UI ms dikonversi ke detik wire. QA-05 memverifikasi current API flow dan denial role menggunakan backend aktual. | Backend tidak menerbitkan credential `source_read` terpisah dan tidak menyediakan historical frame-at-time, evidence/transcript/assist tambahan, atau audio asset content route. Transcript route mengembalikan 404 dalam current API check; UI menampilkan unavailable/unauthorized dan tidak beralih ke fixture. Belum ada additive API E2E. |
| Persistensi | Source `backend/storage.py` menyediakan arsip SQLite untuk metadata, event, snapshot, checkpoint, dan command. QA-06 mengukur 100 operasi `Archive.create` + `Archive.save` pada fixture synthetic. | Belum ada hasil uji backup/recovery, endurance, atau concurrency; latency fixture bukan bukti persistensi replay/mitra. |
| Frontend | FE-01/FE-02 menyediakan `ReplayReviewAdapter`, fixture/API adapter, runtime decoder dan scoped credentials; FE-03 map/board/evidence; FE-04 timeline/replay/audio state; FE-05 transcript provenance/revision, candidate evidence review dan debrief. Authored fixture receipts hanya in-memory. API mode tidak fallback ke fixture. `npm run typecheck` dan `npm run build` lulus pada 6 Oktober. QA-05 menjalankan UI melalui Vite fixture dan API mode. | Browser runtime membuktikan tampilan/interaction yang diuji, bukan kebenaran source/domain. FE adapter tidak menerima source-read dari operator token. Backend receipt correction/review belum ada. |
| Penyajian UI | Backend source memiliki route `/` untuk static `frontend/dist`; build FE-05 menghasilkan `dist/index.html` dan assets. QA-05 membuka Vite dev app di fixture dan API modes. | Browser test belum menguji route backend `/` atau distribusi offline/production bundle. |
| Test dan validasi manusia | QA-05 native Playwright: fixture command 8 passed/1 xfailed; action boundary 6 passed; full suite 16 passed/1 xfailed pada 6 Oktober. | Satu expected failure mencatat FE-05 fixture subscription menampilkan provider status `Unknown`, bukan `Unavailable`. Tidak ada review trainer/domain, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |
| Canonical fixture data QA-01 | `tests/fixtures/replay/`, `tests/fixtures/assist/`, dan `tests/fixtures/private/` berisi versioned synthetic source/assist inputs serta evaluator-only labels/oracles. Data integrity inspection memeriksa hash, mapping, schema parse, dan C-03 times. | Suite QA-02 `tests/contracts/test_fixtures.py` belum tersedia; belum ada contract test pass atau consumer/API integration dari bundle ini. Domain review/operational validation belum dilakukan. |
| AI advisory replay | FE-05 inline authored transcript/revision, highlight dan opsi synthetic dipakai untuk UI checks; bukan ASR, AI/provider output, data mitra, server result, atau bukti operasional. Training view menyembunyikan options. | Worker/provider dan assist/transcript/evidence/audio route serta source-read credential belum tersedia. API panels tetap unavailable/unauthorized tanpa fallback. Provider-unavailable badge adalah expected failure. Tidak ada partner replay berizin, domain review, atau validasi operasional. |
| Offline package / benchmark QA-06 | Packager, package tests, performance suite, dan benchmark manifest tersedia dalam ownership QA-06. Source runner dan dependency Python tersedia; built frontend `frontend/dist/index.html` sudah ada. | Package preflight gagal: `requirements.lock` dan `wheelhouse/` wajib tidak tersedia. Tidak ada package/cold runtime. Detector dan SQLite diukur pada synthetic local microbenchmark; delivery/browser, reconnect, LAN, endurance, provider, dan domain accuracy tidak terbukti. |

## QA-01 canonical fixtures dan independent oracles — 6 Oktober 2026

### Source dan fixture data

`tests/fixtures/replay/` berisi manifest `replay-1`, normalized source events, public source-only frames, geometry/quality/time inputs, dan mapping seluruh 12 source catalogue IDs. `tests/fixtures/assist/` berisi stub/mock transcript, entities, highlight, evaluator-only option, metadata tanpa audio bytes, dan negative/failure/scope/review/stream inputs. `tests/fixtures/private/` terpisah dan memegang authored evaluator labels serta numerical, quality/time, evidence, dan causal oracles. `tests/fixtures/replay/benchmark-manifest.json` milik QA-06 dipertahankan.

Semua fixture berlabel **SYNTHETIC / NOT OPERATIONALLY VALIDATED**. Transcript bukan ASR; provider/model dan audio bytes unavailable. Private oracle tidak termasuk manifest/hash index public dan tidak ditujukan untuk detector payload, mock-server response, frontend, atau package publik.

Source yang diperiksa: katalog backend berisi 12 IDs, layout memakai `LOCAL_METRES` dan memetakan 09/27 ke physical runway yang sama, `Track` current extra-forbid, serta detector menghitung stale dari `now_ms - observed_ms > 3000`. Replay importer, AI harness, dan additive replay/assist API belum ada; fixture profile adalah authored target data, belum dikonsumsi runtime.

Mapping QA-01 mengikuti Rencana Teknis MVP §15.2: S01 `safe_cross`, S02 `overlap`, S11/S12 workflow-only tanpa hazard stratum. QA-06 benchmark manifest saat ini membalik mapping S01/S02. QA-01 mencatat discrepancy dan tidak mengubah file QA-06; run QA-06 yang ada tidak memakai QA-01 independent labels, sehingga accuracy metrics tetap unavailable.

### Runner dan pemeriksaan data

- Dependency check: `python --version` → 3.13.14; `python -m pytest --version` → pytest 9.0.3; Pydantic 2.13.3, Shapely 2.1.2, FastAPI 0.136.1, httpx 0.28.1, Playwright 1.60.0 tersedia.
- Data-integrity inspection dijalankan dengan `python -` yang menerima script dari PowerShell here-string. Hash exact bytes untuk replay/assist/private terverifikasi; JSON/JSONL parse, mapping 12 source IDs, S11/S12 workflow-only, pemisahan hash index private/public, cutoff availability, dan C-03 causal margin 70 ms cocok dengan fixture. Pydantic `Track` dan `Clearance` current DTO menerima nested fixture fields; outer replay import/runtime tidak diuji.
- `python -m pytest tests/contracts/test_fixtures.py` — **not run** karena suite QA-02 belum tersedia. Pemeriksaan data di atas bukan pytest, test pass, build, atau runtime verification.
- QA-03 integration suite dan QA-04 launcher belum tersedia; additive replay/assist API unavailable. QA-05 inline fixtures dan QA-06 benchmark bukan consumer bundle kanonis QA-01. `requirements.lock` dan `wheelhouse/` tetap tidak tersedia.

### C-03 dan assurance boundary

Fixture mencatat `SEG-TWR-006` pada 72.400 s, `EVT-CLR-021` pada 73.020 s, `EVT-TRK-088` observed 74.180 s / received 74.530 s, dan private expected time `ALRT-009` 74.600 s. Nilai alert adalah oracle authored, bukan hasil run detector. Review trainer/ATCO belum dilakukan; fidelity domain dan validasi operasional belum dilakukan.

## QA-05 browser verification — 6 Oktober 2026

### Source

QA-owned native Playwright suite ada di `tests/browser/`. Test fixture memakai FE-05 inline `fixture-1`, bukan bundle kanonis QA-01 yang tersedia sejak 6 Oktober; QA-04 `run_mock_stack.py` belum ada. Test current API menjalankan source FastAPI dengan database SQLite sementara dan credential uji lokal.

### Build

FE build checks yang dicatat dari FE-05 tetap: `npm run typecheck` dan `npm run build` dari `frontend/` lulus pada 6 Oktober. QA-05 tidak mengubah source FE atau menjalankan build FE baru.

### Runtime

Vite fixture/evaluator, Vite training, Vite API mode, dan satu FastAPI current-source instance berjalan selama suite; lifecycle menghentikan proses setelah test. API flow menguji setup/create/end/open-review untuk sesi sintetik lokal. Route `/transcripts` pada backend actual 404; source-read/evidence/audio/assist/options/correction tetap tidak tersedia dan UI tidak fallback.

### Automated test

- `python -m pytest tests/browser -k 'fe_ or mock_stack or adapter_parity'` — 8 passed, 1 xfailed, 8 deselected.
- `python -m pytest tests/browser/test_options_boundary.py` — 6 passed.
- `python -m pytest tests/browser` — 16 passed, 1 xfailed.

Manifest run penuh dan screenshot ada di [QA-05 run artifacts](../tests/browser/artifacts/run-20261006T121244317654+0700/result-manifest.json). Screenshot memverifikasi UI saja, bukan geometry/domain truth. Provider status xfailed karena FE-05 subscription projection mengganti nilai fixture unavailable menjadi unknown.

### Domain review

Belum dilakukan review trainer/ATCO. Authored fixture, receipt QA stub, dan current API responses bukan label operasional atau hasil AI/provider.

### Validasi operasional

Belum ada partner data, assessment site/hardware/LAN, readiness untuk operasi, certification, atau validasi keselamatan.

## QA-06 offline package dan benchmark — 6 Oktober 2026

### Source

`scripts/package_offline.py`, dua suite `tests/integration/test_offline_package.py` / `test_performance.py`, dan `tests/fixtures/replay/benchmark-manifest.json` ditambahkan dalam ownership QA-06. Source backend/FE dan QA-04 launcher tidak diubah. Katalog 12 skenario, simulator observasi, detector, SQLite `Archive`, `frontend/dist`, dan dependency runner aktual tersedia. QA-01 canonical fixture bundle tersedia setelah pekerjaan QA-01 pada 6 Oktober, tetapi run QA-06 yang dilaporkan tidak menggunakannya; QA-03-owned integration suite, `scripts/run_mock_stack.py`, Python `requirements.lock`/`wheelhouse`, serta AI provider/model assets tidak tersedia. QA-05 browser suite dan run manifest ada.

### Build dan package

Frontend build tidak dijalankan ulang; existing `frontend/dist/index.html` diperiksa sebagai file yang tersedia. `python scripts/package_offline.py --output tmp/flowlens-offline` gagal preflight karena lock dan wheelhouse wajib tidak tersedia; output package tidak dibuat. Packager tidak mengunduh dependency dan menolak overwrite output lama. Source replay package tidak dihasilkan.

### Cold runtime

Cold run dengan network disabled **not run / unavailable**, sebab package dependency belum dapat dipenuhi. Backup/restart lifecycle juga belum dijalankan; QA-06 tidak menyalin database aktif mentah atau mengklaim backup API.

### Automated test

- `python -m pytest tests/integration/test_offline_package.py` — **3 passed**; positive package assembly memakai repository sementara berlabel mock, termasuk check hash/allowlist/no-network. Ini bukan cold run atas source aktual.
- `python -m pytest tests/integration/test_performance.py` — **2 passed** pada final run. Percobaan awal menemukan dan memperbaiki typo hash pada benchmark manifest.

### Benchmark teknis

100/100 manifest run selesai dan tersimpan: conflict 40, safe 40, delay/noise 10, dropout 10; 10 detector warm-up tidak masuk denominator; seluruh parameter dan seed dibekukan. Dropout adalah observasi yang difilter oleh test harness mock. Detector p50 2.10895 ms, p95 2.377 ms, max 4.6145 ms; di bawah target p95 <50 ms hanya pada microbenchmark synthetic 5 aircraft/2 vehicle ini. SQLite `Archive.create` + `Archive.save` p50 1.478 ms, p95 2.2651 ms, max 2.8732 ms; 100 session/event/frame terverifikasi. Report aktual: [QA-06 performance evidence](../tmp/qa06-performance-20261006T123620051189+0700.json). Environment: Windows 11 build 26200, Python 3.13.14, SQLite 3.50.4, FastAPI 0.136.1, Uvicorn 0.46.0, Pydantic 2.13.3, Shapely 2.1.2; OS-reported CPU descriptor Intel64 Family 6 Model 140 Stepping 1 (8 logical CPUs), RAM 16,856,219,648 bytes; final benchmark wall time 0.3842 s, 100 simulated seconds. API delivery/render unavailable for source replay; reconnect/LAN synchronization/30-minute endurance not run. Recall/false-warning/lead-time remain unavailable in that run because it used no independent QA-01 labels and its S01/S02 mapping differs from canonical §15.2; QA-06 rerun/remediation belongs to QA-06 owner. ASR/provider metrics unavailable without real assets/provider.

### Domain review dan validasi operasional

Belum ada trainer/ATCO review, partner replay, validasi domain, LAN/site/hardware assessment, atau validasi operasional. Microbenchmark ini tidak menyimpulkan domain validity atau operational readiness.

## Arsitektur target yang didokumentasikan

Rencana Teknis MVP menetapkan satu proses server lokal/LAN sebagai pemilik state sesi, frontend browser React/TypeScript, REST untuk command dan arsip, WebSocket untuk snapshot sinkron, Shapely untuk geometri, serta SQLite lokal untuk persistence. Alur target memisahkan truth simulator dari observasi yang diterima detector, lalu membentuk prediksi occupancy dan alert yang menyertakan evidence serta kualitas data. Sesi ditujukan untuk latihan multi-peran, replay, dan debrief.

Arsitektur tersebut adalah target spesifikasi. Rincian acceptance dan batas MVP berada di [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md); kode aktual perlu diperiksa terpisah sebelum menyatakan bagian target telah selesai.

## Batas produk yang berlaku

- Arah produk jangka panjang adalah advisory berbukti bagi controller Tower/Ground runway; target MVP tetap replay offline, bukan live ATC.
- FlowLens tidak menerbitkan clearance dan tidak mengambil alih keputusan controller.
- Replay simulator mitra yang berizin menjadi target validasi fidelity. Frontend replay adapter, source/map/deterministic-evidence, transcript review, evaluator-candidate UI, dan debrief tersedia di source; baseline sintetik tetap tidak membuktikan realisme operasional. Worker transkripsi/provider dan route/flow kandidat opsi AI belum tersedia di backend. Live integration, persetujuan/assurance, dan klaim manfaat keselamatan belum dicapai.
- Indikator kompleksitas/workload adalah konteks eksperimen, bukan diagnosis kondisi mental atau ukuran fitness-for-duty.

## Memperbarui status

Perbarui tanggal dan tabel ini setelah ada perubahan implementasi atau verifikasi yang berarti. Sebutkan command/check yang benar-benar dijalankan dan hasilnya. Pisahkan status source, build, runtime, automated test, domain review, dan operational validation; jangan gabungkan menjadi satu label “selesai”.
