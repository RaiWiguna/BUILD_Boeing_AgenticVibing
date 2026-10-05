# Status Implementasi ATC FlowLens

- **Pemeriksaan source dan verifikasi terpilih terakhir:** 5 Oktober 2026
- **Cakupan:** inventaris source/config/docs yang ada di repository
- **Metode:** inspeksi source; suite BE-01 sampai BE-06 yang ditargetkan dijalankan pada 4 Oktober 2026, suite BE-06/BE-07 dan gabungan BE-03 sampai BE-08 pada 5 Oktober 2026, serta suite penuh pada virtualenv Python 3.13 setelah deklarasi dependency multipart diperbaiki. Pemeriksaan tersebut bukan build/deployment atau validasi domain/operasional.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, kontrak sesi, simulasi, deteksi, review, dan arsip SQLite tersedia di `backend/`. BE-01–04 menyediakan normalized replay import/read/evidence dan imported read-only review. BE-05 menambah asset/audio/job lifecycle; BE-06 menambah typed result/evidence, immutable analyses, scoped reads, evaluator-only options, dan assist stream. BE-07 menambah transcript revisions, candidate annotations, receipts, current-decision reads, dan debrief exports. BE-08 menambah committed-state rollback/receipt reconciliation, compatible synthetic checkpoint branching, backup API, serta manifest runtime/dependency. | BE-02 memakai source/detector/lifecycle stubs; BE-03–08 memakai fixture sintetik dan SQLite sementara. Worker BE-05/06 adapter berjalan lewat `asyncio.to_thread`; AI-01 DTO package dan AI-02 process worker/provider belum tersedia. Tidak ada mitra/replay berizin yang dikonfirmasi; belum ada domain review atau validasi operasional. |
| API dan stream | Source mendefinisikan endpoint health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, source WebSocket, replay import/source/frame/evidence, audio upload/job/content, transcript/highlight/option reads, transcript correction/highlight/option review, assist snapshot, assist WebSocket, imported `/debrief` JSON/CSV/HTML, dan manifest `/api/v1/runtime-manifest`. | BE-04–08 diuji melalui TestClient saja. Kehadiran route dan hasil harness tidak membuktikan startup/deployment atau alur browser. Main WebSocket synthetic tetap menggunakan first-message auth; assist stream mempunyai `assist-1` typed union termasuk `review_annotation`. |
| Persistensi | `backend/storage.py` tetap memiliki schema replay aditif immutable. `assist_storage.py` menambah tabel asset/job/attempt/result/analysis/receipt/sequence serta revision/annotation/receipt review melalui koneksi `Archive.db` yang sama; tidak membuka writer SQLite kedua. Migrasi stream BE-06 mempertahankan rows lama dan memperluas CHECK constraint secara additive. BE-08 memulihkan memory ke frame committed ketika save gagal dan menyediakan backup melalui SQLite backup API. | BE-05–08 membuktikan transaksi terpilih, fault-injection/reopen, dan snapshot backup pada SQLite sementara; recovery disk fisik, beban, deployment, offline package cold-run, dan AI-02 multi-process worker belum diuji. |
| Frontend | `frontend/` memiliki konfigurasi Vite, entry point React, API helper, dan type TypeScript. | Belum menjadi dashboard: `main.tsx` mengimpor `App` dan `styles.css`, tetapi kedua modul tersebut tidak tersedia pada pemeriksaan ini. |
| Penyajian UI | `backend/app.py` menyajikan bundle dari `frontend/dist`; direktori tersebut belum memiliki `index.html`. Tanpa hasil build, route `/` mengembalikan halaman instruksi dengan HTTP 503. | Belum dapat digunakan sebagai aplikasi web end-to-end dari kondisi bundle yang diperiksa. |
| Test dan validasi manusia | `python -m pytest` lulus 78 tests pada run penuh kedua di virtualenv baru Python 3.13 setelah deklarasi dependency multipart diperbaiki. | Log Actions yang diberikan pengguna mencatat 43 failed dan 35 passed karena multipart import mendapat HTTP 400. Workflow kini hanya menguji 3.13; metadata tetap mengklaim `>=3.11`, sehingga kompatibilitas 3.11 belum diuji otomatis. Tidak ada review trainer, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |
| CI/CD | `.github/workflows/ci.yml` menjalankan backend tests, Ruff, dan mypy di lingkungan Python 3.13; diff check tidak membutuhkan Python. Job promosi menunggu semua check. | Dependency fix dipush pada `4c035e4`; perubahan agar semua interpreter CI memakai 3.13 saja masih lokal. Hasil Actions setelah perubahan multipart belum diverifikasi. Metadata tetap `>=3.11`; kompatibilitas versi minimum tidak diverifikasi oleh workflow. Branch protection tidak dapat diperiksa atau diubah dari lingkungan ini. Tidak ada merge/deployment otomatis. |
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

## Verifikasi BE-08 pada 5 Oktober 2026

- `python -m pytest tests/integration/test_be_03.py tests/integration/test_be_04.py tests/integration/test_be_05.py tests/integration/test_be_06.py tests/integration/test_be_07.py tests/integration/test_be_08.py` — lulus, 58 integration tests. BE-08 memakai TestClient, SQLite sementara, fake clock, injected writer sebelum/sesudah commit, dan checkpoint/replay/worker fixture sintetik.
- Assertions BE-08 mencakup rollback command/acknowledgement/assessment/tick, revision/sequence/event/receipt, same-ID retry dan collision actor/body, stale revision, rekonsiliasi commit ambigu, startup `INTERRUPTED` tanpa auto-resume, review BE-07 dan debrief sesudah reopen, branch compatible/private ancestry, checkpoint schema hilang tanpa child row, imported review read-only, SQLite backup, dan manifest runtime.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` — lulus.
- `python -m mypy --follow-imports=skip backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` — lulus tanpa error; imported modules dilewati sesuai opsi.
- `git diff --check` — exit 0; Git memberi pemberitahuan line-ending LF→CRLF pada file backend yang berubah.
- `/api/v1/runtime-manifest` membaca deklarasi dari `pyproject.toml` dan distribusi terpasang saat runtime; optional worker/local model dilaporkan terpisah. Dependency ranges tetap seperti deklarasi; pinned lock tidak dibuat. Test backup membuka hasil snapshot dan memeriksa sessions, commands, events, replay import receipt, assist result/review receipts, transcript revisions, annotations, serta stream sequence.
- Tidak menjalankan build, deployment, browser suite, offline-package cold-run/network-disabled, AI-02 process isolation, provider/ASR inference, domain review, mitra/data replay berizin, atau validasi operasional. Hasil BE-08 adalah bukti harness dan data sintetik, bukan fidelity operasi.

## Verifikasi persiapan CI/CD pada 5 Oktober 2026

- `python -m pytest tests/integration/test_be_03.py tests/integration/test_be_04.py tests/integration/test_be_05.py tests/integration/test_be_06.py tests/integration/test_be_07.py tests/integration/test_be_08.py` — lulus, 58 tests.
- Run GitHub Actions PR #2 pada head `1a01745` — `backend tests` gagal pada step suite lengkap; Ruff, mypy, dan diff check lulus, lalu job promosi dilewati. Run ini mendahului koreksi lokal.
- Sebelum koreksi, `python -m pytest` menghasilkan 77 passed dan 1 failed pada `test_injected_ports_are_used_once_and_control_capabilities_stay_separate`.
- `python -m pytest tests/integration/test_composition.py` sesudah koreksi — lulus, 2 tests.
- `python -m pytest` sesudah koreksi — lulus, 78 tests.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` sesudah koreksi — lulus.
- `python -m mypy --follow-imports=skip backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` sesudah koreksi — lulus pada enam file; imported modules dilewati.
- `git diff --check origin/feat/backend` dan `git diff --check origin/main` — lulus untuk perubahan tracked pada branch/worktree. `git diff --no-index --check -- /dev/null docs/Technical-Implementation/CI_CD_PROGRESS.md` — lulus untuk file log baru.
- Pemeriksaan awal `git ls-remote --heads origin` hanya mengembalikan `main` dan `feat/backend`. Atas permintaan pengguna, branch `dev` kemudian dibuat dari `main` pada commit `2660222` dan berhasil dipush ke `origin/dev`. `gh` tidak terpasang. Permintaan tanpa autentikasi ke endpoint proteksi branch GitHub mengembalikan HTTP 401, yang tidak membuktikan aturan aktif ataupun nonaktif. Tidak ada status proteksi yang diklaim.
- Perbaikan dari worktree branch `codex/ci-test-fix` berhasil dipush ke `origin/feat/backend` pada `120c587`. GitHub Actions untuk SHA terkoreksi belum terverifikasi; PR #2 belum dinyatakan lulus. Branch `dev` saat ini masih di baseline `main`.

## Verifikasi koreksi dependency multipart pada 5 Oktober 2026

- Log Actions yang diberikan pengguna menunjukkan `43 failed, 35 passed`; banyak kegagalan mendapat HTTP 400 `Invalid multipart replay import` pada helper setup replay.
- `pyproject.toml` sebelumnya tidak mendeklarasikan `python-multipart`, walaupun endpoint `POST /api/v1/replay-imports` membaca body melalui `Request.form()`. Dependency runtime itu ditambahkan agar ikut terpasang oleh `pip install -e ".[dev]"` pada runner bersih.
- Virtualenv baru Python 3.13: `python -m pip install -e ".[dev]"` — lulus dan memasang `python-multipart 0.0.32`.
- `python -m pytest` pada virtualenv baru — run pertama: 77 passed, 1 kegagalan sementara BE-05 (`stored_job["attempts"]` kosong); test yang sama lulus saat diisolasi. Run penuh berikutnya: 78 passed, 1 warning.
- Fix dependency ini dipush pada `4c035e4`. Workflow versi 3.13 saja sedang disiapkan lokal; hasil CI remote untuk versi workflow ini belum tersedia.

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
