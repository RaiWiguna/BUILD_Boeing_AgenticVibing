# CI/CD build log and progress

**Diperbarui:** 5 Oktober 2026

**Status:** multipart dependency fix dipush ke `origin/feat/backend` pada `4c035e4`; workflow diselaraskan ke Python 3.13 saja pada `a3ac1a5`. Suite lokal lulus pada Python 3.13; hasil GitHub Actions untuk head terbaru masih menunggu.

Dokumen ini mencatat requirement, keputusan implementasi, hasil CI, akar masalah, dan pekerjaan tersisa. [CI/CD setup](../CI_CD.md) tetap menjadi panduan konfigurasi GitHub. Workflow yang menjadi sumber perilaku adalah [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

## Cakupan dan kriteria

CI memverifikasi source FlowLens yang memakai baseline sintetik/offline. CI tidak memasang production feed/audio, provider inference, secret, live advisory, atau deployment.

Kriteria target:

1. Push ke `dev` dan `main` menjalankan seluruh check.
2. PR yang menargetkan `dev` atau `main` menjalankan seluruh check. Push `feat/*` sendiri tidak menjalankan CI; PR `feat/* → dev` menjalankannya.
3. Check stabil yang dapat dijadikan required checks: `ATC FlowLens CI / backend tests`, `ATC FlowLens CI / ruff`, `ATC FlowLens CI / mypy`, dan `ATC FlowLens CI / diff check`.
4. Hanya push ke `dev` yang lulus semua check membuat atau memperbarui satu PR `dev → main`. Workflow tidak merge PR dan tidak melakukan deployment.
5. Izin token dibatasi per job. Job promosi memakai `GITHUB_TOKEN` dengan `pull-requests: write`; job verifikasi hanya membaca source.

## Keputusan implementasi

| Area | Keputusan | Alasan/catatan |
|---|---|---|
| Test | Gunakan `python -m pytest` untuk seluruh suite. | Gate lengkap mencakup contract, unit, dan integration tests; kegagalan apa pun menahan promosi. |
| Lint dan typing | Jalankan cakupan Ruff dan mypy yang sudah dipakai BE-08. | `mypy --follow-imports=skip` memeriksa file yang disebut, sementara imported modules dilewati. |
| Whitespace | Jalankan `git diff --check` terhadap rentang branch/push. | Tidak hanya memeriksa working tree kosong. |
| Branch promotion | Serialisasi job promosi, cek bahwa SHA `dev` sama dengan SHA yang diuji, lalu edit PR terbuka atau buat jika belum ada. | Push baru memperbarui head PR yang sama. Duplikat yang sudah ada perlu dirapikan manual; workflow tidak menutup PR. |
| GitHub token | `pull-requests: write` hanya pada job promosi. | Repository juga harus mengizinkan Actions membuat pull request. Tidak ada token pribadi di source. |
| Status check PR | Jalankan check pada event `push` untuk SHA `dev` yang sama dengan head PR promosi, selain trigger `pull_request`. | Workflow `pull_request` yang dipicu `GITHUB_TOKEN` dapat menunggu persetujuan; pastikan status head tampil di PR. |
| Deployment | Tidak ada job deployment atau auto-merge. | Scope saat ini hanya verifikasi dan pembuatan PR promosi. |

## Rekap run dan akar masalah

### GitHub Actions sebelum perbaikan

PR [#2 `feat/backend → dev`](https://github.com/RaiWiguna/BUILD_Boeing_AgenticVibing/pull/2) pada head `1a01745` menjalankan workflow. Run [37313539898](https://github.com/RaiWiguna/BUILD_Boeing_AgenticVibing/actions/runs/37313539898) dan run terkait berakhir gagal:

- Job `backend tests` gagal pada step `Run the complete Python test suite`.
- Ruff, mypy, dan diff check lulus.
- Job promosi dilewati karena event-nya adalah PR, bukan push ke `dev`.
- Reproduksi lokal sebelum perbaikan: `python -m pytest` menghasilkan 77 passed dan 1 failed pada `test_injected_ports_are_used_once_and_control_capabilities_stay_separate`.

### Akar masalah dan koreksi

BE-08 mengubah pembuatan branch agar child belum terlihat sebelum frame restored pertama lengkap. `Session.restore()` menulis frame itu melalui `SessionWriter.save()`; `Archive.save()` kemudian membuat row sesi dan frame dalam operasi persistensi yang sama. Karena itu, assertion lama yang mengharapkan `SessionWriter.create()` dipanggil untuk branch sudah tidak sesuai dengan desain atomik BE-08.

Saat assertion tersebut diperbarui untuk mencerminkan perilaku BE-08, test juga menunjukkan bahwa `Session.execute()` membaca receipt command biasa lewat `Archive.command()` secara langsung. Itu melewati port `SessionWriter.command()` yang dipakai composition root dan mengurangi cakupan injeksi writer. Perbaikannya mengembalikan lookup receipt biasa ke writer yang diinjeksi. Pemeriksaan Archive langsung tetap dipakai untuk merekonsiliasi hasil commit yang ambigu.

Perubahan lokal:

- [`backend/session.py`](../../backend/session.py): lookup receipt pada jalur command biasa memakai `self.writer.command(...)`.
- [`test_composition.py`](../../tests/integration/test_composition.py): test mengharapkan `create()` hanya untuk sesi asal dan memastikan frame branch pertama ditulis melalui `save()`.

Perubahan ini menjaga batas port dan semantik persistensi branch BE-08 tanpa mengubah clearance, otorisasi, atau aturan domain.

## Verifikasi lokal setelah koreksi

Worktree lokal memakai branch `codex/ci-test-fix` yang berawal dari head PR `1a01745`. Hasil pemeriksaan pada 5 Oktober 2026:

- `python -m pytest tests/integration/test_composition.py` — lulus, 2 tests.
- `python -m pytest` — lulus, 78 tests.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` — lulus.
- `python -m mypy --follow-imports=skip backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` — lulus untuk enam file yang disebut; imported modules dilewati.
- `git diff --check origin/feat/backend`, `git diff --check origin/main`, dan whitespace check untuk file build log baru — lulus.

Commit `120c587` berisi perbaikan dan log ini, lalu berhasil dipush ke `origin/feat/backend` pada 5 Oktober 2026. `git ls-remote` mengonfirmasi pointer branch remote pada SHA tersebut. Pemeriksaan daftar run Actions melalui API GitHub mengembalikan HTTP 404; log yang kemudian diberikan pengguna menjadi bukti kegagalan yang lebih baru, tetapi tidak memuat run ID atau SHA untuk dicocokkan.

## Kegagalan multipart replay import dan koreksi lokal

Log CI yang diberikan pengguna menunjukkan `43 failed, 35 passed`; sebagian besar kegagalan berhenti saat fixture mengimpor replay dan menerima `400 Invalid multipart replay import` dari `POST /api/v1/replay-imports`. Jadi assertion BE-06 di sekitar `test_be_06.py:352` adalah titik setup bersama, bukan bukti kegagalan validasi result/evidence BE-06.

Akar masalahnya adalah endpoint memakai `Request.form()` untuk membaca file multipart, tetapi `python-multipart` belum dideklarasikan sebagai dependency runtime di `pyproject.toml`. Exception parser ditangkap endpoint dan dibungkus sebagai HTTP 400; instalasi Python pengembang yang sudah memiliki paket ini menyamarkan masalah pada runner bersih. Koreksi lokal menambahkan `python-multipart` ke dependency proyek.

Verifikasi koreksi pada 5 Oktober 2026:

- Membuat virtualenv baru dengan Python 3.13, lalu `python -m pip install -e ".[dev]"` — berhasil dan memasang `python-multipart 0.0.32` dari deklarasi proyek.
- `python -m pytest` pada run pertama — 77 passed dan satu kegagalan sementara pada assertion attempt BE-05 (`stored_job["attempts"]` kosong); test itu lulus saat dijalankan sendiri.
- `python -m pytest` pada run penuh berikutnya — 78 passed, 1 warning.
- Lingkungan lokal hanya menyediakan Python 3.13; saat suite ini pertama diverifikasi, runner CI memakai Python 3.11. Hasil lokal ini belum menggantikan rerun GitHub Actions.
- Perubahan dependency dan job Python 3.13 dipush ke `origin/feat/backend` pada `4c035e4`. GitHub Actions untuk SHA baru belum diperiksa.

## Strategi versi Python

`requires-python = ">=3.11"` menyatakan batas minimum metadata proyek, bukan pin versi runtime. Source memakai `tomllib` pada `backend/app.py`; modul standard-library itu baru ditambahkan pada Python 3.11, jadi penurunan minimum ke versi lebih tua memerlukan dependency atau perubahan implementasi. Inspeksi source tidak menemukan API khusus Python 3.13.

Python 3.11 sebelumnya dipakai CI untuk menguji batas minimum metadata. Atas pilihan pengguna, seluruh job workflow sekarang memakai interpreter Python 3.13 agar cocok dengan runtime lokal; suite BE-03–BE-08 lulus pada virtualenv lokal 3.13. Konsekuensinya, klaim metadata `>=3.11` belum diuji otomatis pada versi minimum sampai job 3.11 dipulihkan atau batas metadata dinaikkan secara terpisah. `python_version = "3.11"` di konfigurasi mypy adalah target bahasa yang dianalisis, bukan interpreter runner CI.

## Progres dan pekerjaan tersisa

| Item | Status | Bukti/pekerjaan berikutnya |
|---|---|---|
| Workflow CI pada `feat/backend` | Dependency multipart dipush pada `4c035e4`; seluruh job Python diselaraskan ke 3.13 pada `a3ac1a5`. | Periksa check PR #2 pada SHA terbaru. |
| Cakupan versi Python | Semua job Python pada workflow lokal memakai 3.13 saja. | Verifikasi CI setelah push. Metadata tetap `>=3.11`; minimum 3.11 belum diuji oleh CI. |
| Test suite lengkap | 78 tests lulus pada run penuh lokal kedua di virtualenv Python 3.13 yang menginstal deklarasi terbaru. | Run pertama pada env bersih memiliki satu kegagalan sementara di BE-05; GitHub Actions pada SHA versi terbaru belum berjalan/diverifikasi. |
| Ruff, mypy, diff check | Lulus pada run remote sebelum fix; Ruff dan mypy juga lulus lokal sesudah fix. | Pastikan seluruh check remote berhasil pada SHA terbaru. |
| Promosi `dev → main` | Job menunggu semua check dan hanya berjalan pada push ke `dev`. | Verifikasi satu PR promosi dibuat/diperbarui setelah push `dev` dengan semua check sukses. |
| Branch protection `main` dan `dev` | Belum diverifikasi atau diubah. | Aktifkan kewajiban PR, required checks, larangan force-push/penghapusan, dan izin Actions membuat PR di GitHub. |
| Deployment/auto-merge | Tidak termasuk scope dan tidak dikonfigurasi. | Tidak ada. |

Setiap perubahan trigger, nama check, gate, izin token, atau hasil remote baru harus ditambahkan di bagian progres/run ini dan dicerminkan pada [implementation status](../IMPLEMENTATION_STATUS.md).
