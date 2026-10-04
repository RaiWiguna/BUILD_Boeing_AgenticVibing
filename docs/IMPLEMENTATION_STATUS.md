# Status Implementasi ATC FlowLens

- **Pemeriksaan source dan verifikasi terpilih terakhir:** 4 Oktober 2026
- **Cakupan:** inventaris source/config/docs yang ada di repository
- **Metode:** inspeksi source; suite BE-01/BE-02/BE-03 yang ditargetkan dijalankan pada 4 Oktober 2026. Pemeriksaan tersebut bukan build/deployment atau validasi domain/operasional.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, kontrak sesi, simulasi, deteksi, sesi, review, laporan, dan arsip SQLite tersedia di `backend/`. BE-01 menyediakan DTO replay `replay-1`, typed ports, dan seam composition; BE-02 menyediakan source reader, observed-state reducer, dan builder analysis in-memory; BE-03 menyediakan import normalized atomik, archive replay aditif, event-source adapter, serta public read projection. | Test BE-02 memakai source/detector/lifecycle stubs; BE-03 memakai fixture sintetis dan SQLite sementara. Route HTTP BE-04 dan detector SD riil belum tersedia. Base detector port belum mengikat source layout, sehingga jalur base ditandai degraded. |
| API dan stream | Source mendefinisikan endpoint health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, serta WebSocket stream. | Kehadiran route di source tidak membuktikan alur API berhasil. |
| Persistensi | Source `backend/storage.py` menyediakan arsip SQLite synthetic yang ada serta schema replay aditif versi 1 untuk immutable source bytes/records/receipt dan namespace analysis/frame terpisah. | Suite BE-03 membuktikan transaksi dan reopen pada temporary SQLite; recovery disk, backup, beban, deployment, dan concurrency belum diuji. |
| Frontend | `frontend/` memiliki konfigurasi Vite, entry point React, API helper, dan type TypeScript. | Belum menjadi dashboard: `main.tsx` mengimpor `App` dan `styles.css`, tetapi kedua modul tersebut tidak tersedia pada pemeriksaan ini. |
| Penyajian UI | `backend/app.py` menyajikan bundle dari `frontend/dist`; direktori tersebut belum memiliki `index.html`. Tanpa hasil build, route `/` mengembalikan halaman instruksi dengan HTTP 503. | Belum dapat digunakan sebagai aplikasi web end-to-end dari kondisi bundle yang diperiksa. |
| Test dan validasi manusia | Suite terpilih BE-01, BE-02, dan BE-03 lulus: 30 tests terpilih. | Tidak menjalankan keseluruhan test suite. Tidak ada review trainer, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |
| AI advisory replay | Requirement target mencakup replay offline simulator mitra, transkripsi/evidence, dan kandidat opsi AI yang ditinjau evaluator. Import normalized dan reducer observed-state tersedia di source. | Belum ada route API BE-04, worker ASR, kandidat opsi, audio store/replay review UI, atau integrasi SD. Belum ada mitra/replay berizin yang dikonfirmasi. Tidak ada domain review atau validasi operasional. |

## Verifikasi BE-01 pada 4 Oktober 2026

- `python -m pytest tests/contracts/test_be_01.py` — lulus, 9 tests.
- `python -m pytest tests/integration/test_composition.py` — lulus, 2 tests memakai `TestClient`, kredensial uji, fixed clock, fake ports, dan SQLite sementara.
- `python -m ruff check --ignore B008,UP041 backend/replay_contracts.py backend/ports.py backend/session.py backend/app.py tests/contracts/test_be_01.py tests/integration/test_composition.py` — lulus. `B008` dan `UP041` dikecualikan untuk pola FastAPI/exception yang sudah ada di `app.py`.
- `python -m mypy --follow-imports=skip backend/replay_contracts.py backend/ports.py backend/session.py backend/app.py` — lulus untuk empat file yang diperiksa; imported modules dilewati.
- `python -m mypy backend/replay_contracts.py backend/ports.py backend/session.py backend/app.py` — belum bersih: 9 error typing di `models.py`, `scenarios.py`, `detection.py`, dan anotasi legacy `session.py`; tidak ada error pada `ports.py` atau `replay_contracts.py`. Ini dicatat terpisah dari hasil scoped check.
- `git diff --check` — lulus.
- TestClient memulai aplikasi dengan database sementara. Ini bukti runtime dalam test harness saja; startup deployment, build, dan runtime service di luar test belum diperiksa.

## Verifikasi BE-02 pada 4 Oktober 2026

- `python -m pytest tests/unit/test_be_02.py` — lulus, 8 tests dengan fixture sintetis inline.
- `python -m pytest tests/integration/test_replay_analysis.py` — lulus, 1 test dengan fake source serta detector/lifecycle stubs. Pipeline reader → reducer → analysis dieksekusi; test juga melarang koneksi SQLite dan socket.
- `python -m ruff check backend/replay_source.py tests/unit/test_be_02.py tests/integration/test_replay_analysis.py` — lulus.
- `python -m mypy --follow-imports=skip backend/replay_source.py` — lulus untuk file reducer dengan imported modules dilewati.
- `git diff --check` — exit 0; Git memberi notifikasi line-ending untuk file BE-01/pengguna yang telah lebih dulu berubah di working tree.
- Detector/lifecycle runtime mitra tidak dijalankan. Base `DetectorPort` tidak memuat parameter layout; structural extension lokal `evaluate_with_layout` diuji dengan stub, sedangkan fallback port standar ditandai degraded. Source `backend/detection.py` masih mengacu pada geometri global sintetik. Karena itu, hasil ini tidak memverifikasi source-layout fidelity, domain correctness, atau validasi operasional.

## Verifikasi BE-03 pada 4 Oktober 2026

- `python -m pytest tests/integration/test_be_03.py` — lulus, 10 tests dengan fixture normalized sintetik dan SQLite sementara.
- `python -m ruff check backend/storage.py backend/replay_import.py tests/integration/test_be_03.py` — lulus.
- `python -m mypy --follow-imports=skip backend/storage.py backend/replay_import.py tests/integration/test_be_03.py` — lulus untuk tiga file yang diperiksa; imported modules dilewati.
- `git diff --check` — exit 0; Git memberi pemberitahuan bahwa line ending `backend/storage.py` akan dikonversi ke CRLF.
- Test harness membuktikan parse/validasi, byte-exact hash, rollback transaksional, reopen SQLite, cutoff/paging, compatibility dengan frame synthetic, dan reader projection. Ini bukan runtime deployment, recovery/backup, beban produksi, API BE-04, data partner, review domain, atau validasi operasional.

## Arsitektur target yang didokumentasikan

Rencana Teknis MVP menetapkan satu proses server lokal/LAN sebagai pemilik state sesi, frontend browser React/TypeScript, REST untuk command dan arsip, WebSocket untuk snapshot sinkron, Shapely untuk geometri, serta SQLite lokal untuk persistence. Alur target memisahkan truth simulator dari observasi yang diterima detector, lalu membentuk prediksi occupancy dan alert yang menyertakan evidence serta kualitas data. Sesi ditujukan untuk latihan multi-peran, replay, dan debrief.

Arsitektur tersebut adalah target spesifikasi. Rincian acceptance dan batas MVP berada di [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md); kode aktual perlu diperiksa terpisah sebelum menyatakan bagian target telah selesai.

## Batas produk yang berlaku

- Arah produk jangka panjang adalah advisory berbukti bagi controller Tower/Ground runway; target MVP tetap replay offline, bukan live ATC.
- FlowLens tidak menerbitkan clearance dan tidak mengambil alih keputusan controller.
- Replay simulator mitra yang berizin menjadi target validasi fidelity. Baseline sintetik sementara tidak membuktikan realisme operasional. Source import/reducer normalized tersedia, tetapi API BE-04, transkripsi, kandidat opsi AI, dan UI review belum tersedia. Live integration, persetujuan/assurance, dan klaim manfaat keselamatan belum dicapai.
- Indikator kompleksitas/workload adalah konteks eksperimen, bukan diagnosis kondisi mental atau ukuran fitness-for-duty.

## Memperbarui status

Perbarui tanggal dan tabel ini setelah ada perubahan implementasi atau verifikasi yang berarti. Sebutkan command/check yang benar-benar dijalankan dan hasilnya. Pisahkan status source, build, runtime, automated test, domain review, dan operational validation; jangan gabungkan menjadi satu label “selesai”.
