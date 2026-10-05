# CI/CD build log and progress

**Diperbarui:** 5 Oktober 2026

**Status:** perbaikan lokal terverifikasi; belum dikirim ke PR #2 atau divalidasi ulang oleh GitHub Actions.

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

Hasil ini membuktikan pemeriksaan lokal saja. GitHub Actions belum menjalankan ulang PR #2 pada source yang telah dikoreksi; hasil remote terbaru masih berasal dari head sebelum fix.

## Progres dan pekerjaan tersisa

| Item | Status | Bukti/pekerjaan berikutnya |
|---|---|---|
| Workflow CI pada `feat/backend` | Ada di source dan telah dijalankan pada PR #2. | Jalankan lagi setelah koreksi dikirim ke branch PR. |
| Test suite lengkap | Lulus lokal, 78 tests. | Tunggu hasil remote pada SHA koreksi sebelum menyatakan CI lulus. |
| Ruff, mypy, diff check | Lulus pada run remote sebelum fix; Ruff dan mypy juga lulus lokal sesudah fix. | Pastikan seluruh check remote berhasil pada SHA terbaru. |
| Promosi `dev → main` | Job menunggu semua check dan hanya berjalan pada push ke `dev`. | Verifikasi satu PR promosi dibuat/diperbarui setelah push `dev` dengan semua check sukses. |
| Branch protection `main` dan `dev` | Belum diverifikasi atau diubah. | Aktifkan kewajiban PR, required checks, larangan force-push/penghapusan, dan izin Actions membuat PR di GitHub. |
| Deployment/auto-merge | Tidak termasuk scope dan tidak dikonfigurasi. | Tidak ada. |

Setiap perubahan trigger, nama check, gate, izin token, atau hasil remote baru harus ditambahkan di bagian progres/run ini dan dicerminkan pada [implementation status](../IMPLEMENTATION_STATUS.md).
