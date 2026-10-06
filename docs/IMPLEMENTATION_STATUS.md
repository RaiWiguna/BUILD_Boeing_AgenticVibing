# Status Implementasi ATC FlowLens

- **Pemeriksaan source/build terakhir:** 6 Oktober 2026
- **Progress FE-01 sampai FE-05 diperiksa:** 6 Oktober 2026
- **Cakupan:** typed adapter FE-01/FE-02; source context, runway map/board, deterministic evidence FE-03; event history timeline, playback/seek controls, transcript/audio state UI FE-04; transcript provenance, candidate evidence review, correction/review editor, debrief FE-05
- **Build FE-05** dari `frontend/`: `npm run typecheck` dan `npm run build` lulus pada 6 Oktober 2026. Ini bukti build FE, bukan runtime atau browser test.
- **Command aktual QA-05** dari root repository pada 6 Oktober 2026: `python -m pytest tests/browser -k 'fe_ or mock_stack or adapter_parity'` — 8 passed, 1 xfailed; `python -m pytest tests/browser/test_options_boundary.py` — 6 passed; `python -m pytest tests/browser` — 16 passed, 1 xfailed. Lihat bagian QA-05 di bawah.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, model kontrak, simulasi, deteksi, sesi, review, laporan, dan arsip SQLite tersedia di `backend/`. QA-05 menjalankan instance lokal dari source dengan temporary SQLite dan throwaway test key. | Login, create/end/open review, seat role scope dan participant denial dites; bukan uji recovery, persistensi correction, beban, atau concurrency. |
| API dan stream | Source mendefinisikan route health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, dan WS direct snapshot. FE adapter dapat meminta review beku lewat route `POST .../reviews`, menyimpan token review-control dalam memory, lalu memakai command `START/PAUSE/SET_SPEED/SEEK`; SEEK UI ms dikonversi ke detik wire. QA-05 memverifikasi current API flow dan denial role menggunakan backend aktual. | Backend tidak menerbitkan credential `source_read` terpisah dan tidak menyediakan historical frame-at-time, evidence/transcript/assist tambahan, atau audio asset content route. Transcript route mengembalikan 404 dalam current API check; UI menampilkan unavailable/unauthorized dan tidak beralih ke fixture. Belum ada additive API E2E. |
| Persistensi | Source `backend/storage.py` menyediakan arsip SQLite untuk metadata, event, snapshot, checkpoint, dan command. | Belum ada hasil uji recovery, durability, beban, atau concurrency dalam pemeriksaan ini. |
| Frontend | FE-01/FE-02 menyediakan `ReplayReviewAdapter`, fixture/API adapter, runtime decoder dan scoped credentials; FE-03 map/board/evidence; FE-04 timeline/replay/audio state; FE-05 transcript provenance/revision, candidate evidence review dan debrief. Authored fixture receipts hanya in-memory. API mode tidak fallback ke fixture. `npm run typecheck` dan `npm run build` lulus pada 6 Oktober. QA-05 menjalankan UI melalui Vite fixture dan API mode. | Browser runtime membuktikan tampilan/interaction yang diuji, bukan kebenaran source/domain. FE adapter tidak menerima source-read dari operator token. Backend receipt correction/review belum ada. |
| Penyajian UI | Backend source memiliki route `/` untuk static `frontend/dist`; build FE-05 menghasilkan `dist/index.html` dan assets. QA-05 membuka Vite dev app di fixture dan API modes. | Browser test belum menguji route backend `/` atau distribusi offline/production bundle. |
| Test dan validasi manusia | QA-05 native Playwright: fixture command 8 passed/1 xfailed; action boundary 6 passed; full suite 16 passed/1 xfailed pada 6 Oktober. | Satu expected failure mencatat FE-05 fixture subscription menampilkan provider status `Unknown`, bukan `Unavailable`. Tidak ada review trainer/domain, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |
| AI advisory replay | FE-05 inline authored transcript/revision, highlight dan opsi synthetic dipakai untuk UI checks; bukan ASR, AI/provider output, data mitra, server result, atau bukti operasional. Training view menyembunyikan options. | Worker/provider dan assist/transcript/evidence/audio route serta source-read credential belum tersedia. API panels tetap unavailable/unauthorized tanpa fallback. Provider-unavailable badge adalah expected failure. Tidak ada partner replay berizin, domain review, atau validasi operasional. |

## QA-05 browser verification — 6 Oktober 2026

### Source

QA-owned native Playwright suite ada di `tests/browser/`. Test fixture memakai FE-05 inline `fixture-1`; QA-01 canonical bundle dan QA-04 `run_mock_stack.py` belum ada. Test current API menjalankan source FastAPI dengan database SQLite sementara dan credential uji lokal.

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
