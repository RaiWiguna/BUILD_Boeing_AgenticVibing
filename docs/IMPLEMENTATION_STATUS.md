# Status Implementasi ATC FlowLens

- **Pemeriksaan source dan verifikasi terpilih terakhir:** 6 Oktober 2026
- **Cakupan source:** BE-01–08, FE-01–05, QA-01, QA-05, dan QA-06 sesuai snapshot masing-masing workstream.
- **Backend:** 78 pytest lulus pada run penuh Python 3.13 tanggal 5 Oktober setelah dependency multipart diperbaiki. Itu adalah hasil harness sebelum merge saat ini, bukan rerun pada combined HEAD.
- **Frontend:** `npm run typecheck` dan `npm run build` lulus pada 6 Oktober sebelum merge backend terbaru. QA-05 browser run menghasilkan 16 passed, 1 xfailed, juga terhadap source sebelum merge backend terbaru.
- **QA-01:** fixture public/private dan authored oracles tersedia; data-integrity inspection selesai. `tests/contracts/test_fixtures.py` tidak dijalankan karena suite QA-02 belum ada.
- **QA-06:** mock package tests 3 passed dan benchmark synthetic 2 passed pada run sebelumnya. Package nyata gagal preflight karena `requirements.lock`/`wheelhouse` tidak ada; cold runtime unavailable.
- **Combined verification:** automated tests, FE build, dan browser/API integration **tidak dijalankan ulang setelah penggabungan branch**. Domain review dan validasi operasional belum dilakukan.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, kontrak sesi, simulasi, deteksi, review, dan arsip SQLite tersedia di `backend/`. BE-01–04 menyediakan normalized replay import/read/evidence dan imported read-only review. BE-05 menambah asset/audio/job lifecycle; BE-06 menambah typed result/evidence, immutable analyses, scoped reads, evaluator-only options, dan assist stream. BE-07 menambah transcript revisions, candidate annotations, receipts, current-decision reads, dan debrief exports. BE-08 menambah committed-state rollback/receipt reconciliation, compatible synthetic checkpoint branching, backup API, serta manifest runtime/dependency. | BE-02 memakai source/detector/lifecycle stubs; BE-03–08 memakai fixture sintetik dan SQLite sementara. Worker BE-05/06 adapter berjalan lewat `asyncio.to_thread`; AI-01 DTO package dan AI-02 process worker/provider belum tersedia. Tidak ada mitra/replay berizin yang dikonfirmasi; belum ada domain review atau validasi operasional. |
| API dan stream | Source mendefinisikan endpoint health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, source WebSocket, replay import/source/frame/evidence, audio upload/job/content, transcript/highlight/option reads, transcript correction/highlight/option review, assist snapshot, assist WebSocket, imported `/debrief` JSON/CSV/HTML, dan manifest `/api/v1/runtime-manifest`. | BE-04–08 diuji melalui TestClient saja. Kehadiran route dan hasil harness tidak membuktikan startup/deployment atau alur browser. Main WebSocket synthetic tetap menggunakan first-message auth; assist stream mempunyai `assist-1` typed union termasuk `review_annotation`. |
| Persistensi | `backend/storage.py` tetap memiliki schema replay aditif immutable. `assist_storage.py` menambah tabel asset/job/attempt/result/analysis/receipt/sequence serta revision/annotation/receipt review melalui koneksi `Archive.db` yang sama; tidak membuka writer SQLite kedua. Migrasi stream BE-06 mempertahankan rows lama dan memperluas CHECK constraint secara additive. BE-08 memulihkan memory ke frame committed ketika save gagal dan menyediakan backup melalui SQLite backup API. | BE-05–08 membuktikan transaksi terpilih, fault-injection/reopen, dan snapshot backup pada SQLite sementara; recovery disk fisik, beban, deployment, offline package cold-run, dan AI-02 multi-process worker belum diuji. |
| Frontend | FE-01/02 typed adapters dan API decoder; FE-03 source/map/evidence; FE-04 timeline/seek/audio state; FE-05 transcript review/debrief tersedia di source. API adapter tidak fallback ke fixture. | FE build sebelumnya lulus; belum dibuild ulang pada combined HEAD. UI/browser results diuji pada source sebelum backend BE merge terbaru. Tidak ada klaim full FE-BE integration. |
| Penyajian UI | FE React/Vite source kini tersedia; backend menyediakan route static untuk bundle build. | Bundle `frontend/dist` tidak termasuk dalam merge; build/runtime pada combined HEAD belum diverifikasi. |
| Test dan validasi manusia | BE full suite 78 passed (5 Okt); QA-05 browser suite 16 passed, 1 xfailed; QA-06 mock package tests 3 passed dan benchmark bookkeeping 2 passed pada run bertanggal. | Hasil QA-05 berasal dari source sebelum backend BE merge terbaru; API 404 assertion bersifat historis. Tidak ada rerun suite pada combined HEAD. Expected failure QA-05 terkait badge provider `Unknown`; trainer/domain review dan validasi operasional belum dilakukan. |
| Canonical fixture data QA-01 | `tests/fixtures/replay/`, `assist/`, dan `private/` berisi versioned synthetic inputs/oracles dengan exact-byte hashes; private oracle terpisah dari public indexes. | QA-02 fixture suite tidak tersedia saat QA-01 diperiksa dan tidak dijalankan. Data check bukan pytest/build/runtime. |
| Offline package / benchmark QA-06 | Package helper, mock/performance suites, benchmark manifest, dan final report tersedia. | `requirements.lock` dan `wheelhouse/` tetap tidak ada; package preflight gagal dan cold runtime tidak dijalankan. QA-06 run tidak menggunakan QA-01 labels; accuracy tidak tersedia. |
| CI/CD | `.github/workflows/ci.yml` menjalankan backend tests, Ruff, dan mypy di lingkungan Python 3.13; diff check tidak membutuhkan Python. Job promosi menunggu semua check. | Dependency fix dipush pada `4c035e4`, lalu seluruh job Python diselaraskan ke 3.13 pada `a3ac1a5`. Hasil Actions untuk SHA terbaru belum diverifikasi. Metadata tetap `>=3.11`; kompatibilitas versi minimum tidak diverifikasi oleh workflow. Branch protection tidak dapat diperiksa atau diubah dari lingkungan ini. Tidak ada merge/deployment otomatis. |
| AI advisory replay | Backend BE-04–07 menyediakan source/audio/job/transcript/evidence/option routes dan storage; FE-04/05 menyediakan transcript/evidence review UI. | Tidak ada bukti browser/API parity pasca-merge. AI-01/AI-02 provider/ASR inference belum tersedia; fixtures/stubs bukan hasil ASR, data mitra, atau validasi operasional. |

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
- Fix dependency ini dipush pada `4c035e4`; penyesuaian workflow 3.13 saja dipush pada `a3ac1a5`. Hasil CI remote untuk versi workflow ini belum tersedia.

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

**Urutan integrasi:** run QA-05 di bawah dilakukan pada 6 Oktober terhadap FE branch sebelum backend BE merge terbaru. Pada combined source, replay/assist routes sudah ada dari BE-04–08; 404 assertions di run QA-05 adalah hasil historis dari source lama. Tidak ada browser/API rerun setelah merge.

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


### Status dependency setelah snapshot QA-01

`origin/dev` kini membawa QA-03 backend integration suite dari BE-03–08. Suite tersebut tidak dijalankan dalam merge ini. QA-02 `tests/contracts/test_fixtures.py` dan QA-04 `scripts/run_mock_stack.py` tetap tidak tersedia. Catatan QA-01 tentang QA-03 unavailable merekam kondisi saat task QA-01 dikerjakan.


## Arsitektur target yang didokumentasikan

Rencana Teknis MVP menetapkan satu proses server lokal/LAN sebagai pemilik state sesi, frontend browser React/TypeScript, REST untuk command dan arsip, WebSocket untuk snapshot sinkron, Shapely untuk geometri, serta SQLite lokal untuk persistence. Alur target memisahkan truth simulator dari observasi yang diterima detector, lalu membentuk prediksi occupancy dan alert yang menyertakan evidence serta kualitas data. Sesi ditujukan untuk latihan multi-peran, replay, dan debrief.

Arsitektur tersebut adalah target spesifikasi. Rincian acceptance dan batas MVP berada di [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md); kode aktual perlu diperiksa terpisah sebelum menyatakan bagian target telah selesai.

## Batas produk yang berlaku

- Arah produk jangka panjang adalah advisory berbukti bagi controller Tower/Ground runway; target MVP tetap replay offline, bukan live ATC.
- FlowLens tidak menerbitkan clearance dan tidak mengambil alih keputusan controller.
- Replay simulator mitra yang berizin tetap menjadi target validasi fidelity. Backend replay/assist routes dan frontend review UI tersedia di source setelah merge, tetapi combined browser/API behavior belum diuji. Hasil fixture/provider stub bukan ASR/model output; live integration, persetujuan/assurance, domain review, dan klaim manfaat keselamatan belum dicapai.
- Indikator kompleksitas/workload adalah konteks eksperimen, bukan diagnosis kondisi mental atau ukuran fitness-for-duty.

## Memperbarui status

Perbarui tanggal dan tabel ini setelah ada perubahan implementasi atau verifikasi yang berarti. Sebutkan command/check yang benar-benar dijalankan dan hasilnya. Pisahkan status source, build, runtime, automated test, domain review, dan operational validation; jangan gabungkan menjadi satu label “selesai”.
