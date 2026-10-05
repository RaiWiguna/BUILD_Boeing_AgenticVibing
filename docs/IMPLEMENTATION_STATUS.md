# Status Implementasi ATC FlowLens

- **Pemeriksaan source dan verifikasi terpilih terakhir:** 5 Oktober 2026
- **Cakupan:** inventaris source/config/docs yang ada di repository
- **Metode:** inspeksi source; suite BE-01 sampai BE-06 yang ditargetkan dijalankan pada 4 Oktober 2026 dan suite BE-06/BE-07 yang ditargetkan dijalankan pada 5 Oktober 2026. Pemeriksaan tersebut bukan build/deployment atau validasi domain/operasional.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, kontrak sesi, simulasi, deteksi, review, dan arsip SQLite tersedia di `backend/`. BE-01–04 menyediakan normalized replay import/read/evidence dan imported read-only review. BE-05 menambah asset/audio/job lifecycle; BE-06 menambah typed result/evidence, immutable analyses, scoped reads, evaluator-only options, dan assist stream. BE-07 menambah transcript revisions, candidate annotations, receipts, current-decision reads, dan debrief exports. | BE-02 memakai source/detector/lifecycle stubs; BE-03–07 memakai fixture sintetik dan SQLite sementara. Worker BE-05/06 adapter berjalan lewat `asyncio.to_thread`; AI-01 DTO package dan AI-02 process worker/provider belum tersedia. Tidak ada mitra/replay berizin yang dikonfirmasi; belum ada domain review atau validasi operasional. |
| API dan stream | Source mendefinisikan endpoint health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, source WebSocket, replay import/source/frame/evidence, audio upload/job/content, transcript/highlight/option reads, transcript correction/highlight/option review, assist snapshot, assist WebSocket, dan imported `/debrief` JSON/CSV/HTML. | BE-04/05/06/07 diuji melalui TestClient saja. Kehadiran route dan hasil harness tidak membuktikan startup/deployment atau alur browser. Main WebSocket synthetic tetap menggunakan first-message auth; assist stream mempunyai `assist-1` typed union termasuk `review_annotation`. |
| Persistensi | `backend/storage.py` tetap memiliki schema replay aditif immutable. `assist_storage.py` menambah tabel asset/job/attempt/result/analysis/receipt/sequence serta revision/annotation/receipt review melalui koneksi `Archive.db` yang sama; tidak membuka writer SQLite kedua. Migrasi stream BE-06 mempertahankan rows lama dan memperluas CHECK constraint secara additive. File audio tetap di private runtime directory. | BE-05/06/07 membuktikan transaksi terpilih dan reopen/migrasi pada SQLite sementara; recovery disk/backup, beban, deployment, dan AI-02 multi-process worker belum diuji. |
| Frontend | `frontend/` memiliki konfigurasi Vite, entry point React, API helper, dan type TypeScript. | Belum menjadi dashboard: `main.tsx` mengimpor `App` dan `styles.css`, tetapi kedua modul tersebut tidak tersedia pada pemeriksaan ini. |
| Penyajian UI | `backend/app.py` menyajikan bundle dari `frontend/dist`; direktori tersebut belum memiliki `index.html`. Tanpa hasil build, route `/` mengembalikan halaman instruksi dengan HTTP 503. | Belum dapat digunakan sebagai aplikasi web end-to-end dari kondisi bundle yang diperiksa. |
| Test dan validasi manusia | BE-01–05 sebelumnya lulus 42 tests; BE-06 lulus 24 tests pada 4 Oktober. Pada 5 Oktober, gabungan BE-06/07 lulus 30 integration tests, termasuk enam test BE-07 dengan fake clock, TestClient, temporary SQLite, dan fixed synthetic WorkerResult. Ruff, scoped mypy, serta `git diff --check` juga lulus. | Tidak menjalankan keseluruhan test suite. Tidak ada review trainer, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |
| AI advisory replay | Requirement target mencakup replay offline simulator mitra, transkripsi/evidence, dan kandidat opsi AI yang ditinjau evaluator. Source import/reducer/read/review BE-04, audio/job BE-05, BE-06 result storage/validation/scoped reads/stream, serta BE-07 durable reviewer changes/debrief tersedia. | Hasil BE-06/07 memakai fixed synthetic WorkerResult fixtures, bukan transkripsi dari audio. AI-01 package, AI-02 process isolation/provider, ASR inference, domain review, UI, mitra/replay berizin, dan validasi operasional belum tersedia. |

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

## Verifikasi BE-04 pada 4 Oktober 2026

- `python -m pytest tests/integration/test_be_04.py` — lulus, 5 tests memakai `TestClient`, temporary SQLite, fake wall/monotonic clock, operator test token, dan fixture replay authored synthetic. Assertions mencakup multipart receipt/retry/conflict/invalid input, projection privacy, historical frame/explicit analysis, event cutoff sebelum paging dan ordinal tie, evidence resolution/unresolved refs, source-read scope/expiry, imported review read-only, serta compatibility login/command/snapshot/WebSocket synthetic.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/review.py tests/integration/test_be_04.py` — lulus. `B008` untuk dependency `Depends(...)` FastAPI dan `UP041` pada timeout handling dikecualikan sesuai pola legacy BE-01 yang tercatat.
- `python -m ruff check backend/app.py backend/review.py tests/integration/test_be_04.py` — belum bersih: melaporkan 17 temuan `B008`/`UP041` pada pola FastAPI/timeout `app.py`; scoped Ruff di atas lulus dengan pengecualian tersebut.
- `python -m mypy --follow-imports=skip backend/app.py backend/review.py tests/integration/test_be_04.py` — lulus untuk tiga file; imported modules dilewati.
- `git diff --check` — exit 0; Git memberi peringatan bahwa line endings `backend/app.py` dan `backend/review.py` akan dikonversi ke CRLF.
- TestClient membuktikan runtime dalam test harness saja. Tidak ada build, deployment, domain review, mitra/data replay berizin, atau validasi operasional yang dijalankan.

## Verifikasi BE-05 pada 4 Oktober 2026

- `python -m pytest tests/integration/test_be_05.py` — lulus, 7 tests dengan TestClient, SQLite sementara, actor/token uji, fake wall/monotonic clock, WAV PCM sintetik, dan fake worker. Assertions mencakup file+metadata commit sebelum dispatch, server hash, invalid metadata/file/permission, source scope dan playback privacy, `source_read_token` expiry/read-only boundary, cancel/timeout/retry/late attempt, worker failure aman, worker nonblocking terhadap replay/simulation clock, default unavailable config, dan BE-04 synthetic route compatibility.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_05.py` — lulus. `B008`/`UP041` dikecualikan sesuai pola FastAPI/timeout legacy BE-04.
- `python -m mypy --follow-imports=skip backend/app.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_05.py` — lulus pada empat file; imported modules sengaja dilewati.
- `git diff --check` — exit 0; Git mengeluarkan notifikasi line-ending untuk `backend/app.py`.
- File WAV dibatasi pada PCM, 1–2 channels, sample widths 1–4 byte, dan 64 MiB. Worker/config default tidak tersedia sehingga upload menyimpan asset/job lalu memberi status `failed` dengan diagnostic eksplisit; test-only config menjalankan fake worker. Saat verifikasi BE-05 ini belum ada AI-02 spawn process atau BE-06 result sink; implementasi BE-06 dan keterbatasannya dicatat pada bagian berikut.
- TestClient membuktikan runtime dalam test harness saja. Tidak ada build, deployment, domain review, mitra/data replay berizin, atau validasi operasional yang dijalankan.

## Verifikasi BE-06 pada 4 Oktober 2026

- `python -m pytest tests/integration/test_be_06.py` — lulus, 24 tests memakai `TestClient`, temporary SQLite, fake wall/monotonic clocks, actor/token uji, dan WorkerResult fixtures yang ditulis sintetik. Checks mencakup commit atomik/reopen, receipt idempotent dan conflict, source/asset/hash/model/config/input/attempt bindings, typed extra-forbid DTO dan action-field rejection, evidence foreign/dangling/out-of-window, cancelled/timeout/stale attempts, source-read scope, evaluator-only options, historical cutoff, pagination, unaligned transcript uncertainty, assist snapshot/update/reconnect/gap resync, serta BE-04 synthetic WebSocket compatibility.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py` — lulus.
- `python -m mypy --follow-imports=skip backend/app.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py` — lulus pada empat file; imported modules dilewati sesuai command.
- `git diff --check` — exit 0; Git memberi notifikasi bahwa line ending `backend/app.py`, `backend/assist_service.py`, dan `backend/assist_storage.py` akan dikonversi ke CRLF.
- Result, terminal job status, assist analysis/version metadata, receipt, and sequence use the same `Archive.db` connection and one transaction. Tests reopen a temporary SQLite database to inspect the committed rows.
- A compatibility adapter accepts BE-05's status-only WorkerResult as an empty result; it adds server-known binding metadata and creates no transcript/highlight/option text. The richer DTO exercised by BE-06 is a fixed synthetic fixture unrelated to WAV samples.
- No build, deployment, browser suite, process-worker isolation, AI-01 DTO integration, AI-02 process integration, provider inference/ASR, domain review, partner data, or operational validation was run. No partner/replay permission is implied.

## Verifikasi BE-07 pada 5 Oktober 2026

- `python -m pytest tests/integration/test_be_06.py tests/integration/test_be_07.py` — lulus, 30 tests. BE-07 memakai TestClient, temporary SQLite, fake clock, server-minted test actors/tokens, authored synthetic transcript/candidate/replay fixtures, dan WAV berisi synthetic silence dengan fake worker. Assertions mencakup append-only correction/review, reopen durability, raw result/source immutability, idempotent receipt/collision/stale revision, server reviewer/timestamp, forbidden authority claims, source-read scope, cross-source denial, typed annotation stream/snapshot sequence/reconnect, debrief JSON/CSV/HTML safety/provenance/uncertainty, synthetic `/report`, dan migrasi schema stream BE-06 dengan preservation seluruh event lama.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/review.py backend/reporting.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py tests/integration/test_be_07.py` — lulus.
- `python -m mypy --follow-imports=skip backend/app.py backend/review.py backend/reporting.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py tests/integration/test_be_07.py` — lulus, tanpa isu pada tujuh file yang diperiksa; imported modules dilewati sesuai opsi.
- `git diff --check` — exit 0; Git memberi notifikasi bahwa line ending empat file backend akan dikonversi ke CRLF.
- Receipt, revision/annotation, dan assist sequence ditulis atomik melalui koneksi `Archive.db` yang sama. Migrasi tabel event menyalin seluruh stream rows BE-06 sebelum mengaktifkan event type `review_annotation`; test membaca kembali row lama lalu berhasil menambah satu annotation.
- Tidak menjalankan build, deployment, browser suite, AI-02 process isolation, provider/ASR inference, domain review, mitra/data berizin, atau validasi operasional. Synthetic fixture bukan validasi fidelity operasi.

## Arsitektur target yang didokumentasikan

Rencana Teknis MVP menetapkan satu proses server lokal/LAN sebagai pemilik state sesi, frontend browser React/TypeScript, REST untuk command dan arsip, WebSocket untuk snapshot sinkron, Shapely untuk geometri, serta SQLite lokal untuk persistence. Alur target memisahkan truth simulator dari observasi yang diterima detector, lalu membentuk prediksi occupancy dan alert yang menyertakan evidence serta kualitas data. Sesi ditujukan untuk latihan multi-peran, replay, dan debrief.

Arsitektur tersebut adalah target spesifikasi. Rincian acceptance dan batas MVP berada di [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md); kode aktual perlu diperiksa terpisah sebelum menyatakan bagian target telah selesai.

## Batas produk yang berlaku

- Arah produk jangka panjang adalah advisory berbukti bagi controller Tower/Ground runway; target MVP tetap replay offline, bukan live ATC.
- FlowLens tidak menerbitkan clearance dan tidak mengambil alih keputusan controller.
- Replay simulator mitra yang berizin menjadi target validasi fidelity. Baseline sintetik sementara tidak membuktikan realisme operasional. Source import/reducer normalized BE-04 serta BE-06 transcript/highlight/option read interfaces tersedia; hasil BE-06 yang diuji adalah fixture, bukan ASR/model output. UI review, live integration, persetujuan/assurance, domain review, dan klaim manfaat keselamatan belum dicapai.
- Indikator kompleksitas/workload adalah konteks eksperimen, bukan diagnosis kondisi mental atau ukuran fitness-for-duty.

## Memperbarui status

Perbarui tanggal dan tabel ini setelah ada perubahan implementasi atau verifikasi yang berarti. Sebutkan command/check yang benar-benar dijalankan dan hasilnya. Pisahkan status source, build, runtime, automated test, domain review, dan operational validation; jangan gabungkan menjadi satu label “selesai”.
