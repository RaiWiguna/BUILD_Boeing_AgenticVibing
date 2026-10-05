# CI dan promosi branch

Rekap requirement, keputusan, run history, dan tindak lanjut kegagalan ada di [CI/CD build log](Technical-Implementation/CI_CD_PROGRESS.md).

## Perilaku workflow

Workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) menjalankan pemeriksaan pada setiap push ke `dev` atau `main`, serta setiap pull request yang menargetkan salah satu branch tersebut. Push ke `feat/*` sendiri tidak memicu workflow; PR `feat/* → dev` tetap menjalankan CI. Hanya push yang berhasil diuji pada `dev` yang dapat menjalankan job promosi.

Lima status check dengan nama stabil:

- `ATC FlowLens CI / backend tests` — menjalankan seluruh test Python dengan Python 3.11, versi minimum proyek.
- `ATC FlowLens CI / backend tests (Python 3.13)` — menjalankan seluruh test Python dengan Python 3.13, versi yang digunakan dalam verifikasi lokal terakhir.
- `ATC FlowLens CI / ruff` — menjalankan gate Ruff BE-08 yang telah digunakan proyek.
- `ATC FlowLens CI / mypy` — menjalankan gate mypy BE-08 yang telah digunakan proyek.
- `ATC FlowLens CI / diff check` — menjalankan `git diff --check` terhadap perubahan branch atau rentang push.

Job `promote dev to main` menunggu kelima check sukses, memeriksa bahwa tip `dev` masih sama dengan commit yang lulus, lalu mencari PR terbuka untuk pasangan `dev → main`. Jika satu PR ditemukan, job memperbarui PR itu; jika tidak ada, job membuat satu PR. Bila duplikat sudah ada, job gagal dan meminta penyelesaian manual, tanpa menutup PR. Push baru ke `dev` memperbarui head PR yang sudah ada secara otomatis. Kegagalan CI melewati job promosi, sehingga PR baru tidak dibuat; PR promosi yang sudah terbuka tetap ada dan menampilkan status check commit barunya.

PR `feat/* → dev`, push ke `main`, dan PR menuju `main` hanya menjalankan pemeriksaan CI. Tidak ada auto-merge atau deployment. Job menggunakan `GITHUB_TOKEN`; hanya job promosi yang meminta `pull-requests: write`, sedangkan job pemeriksaan hanya membaca source. Aksi checkout dan setup Python dipatok ke commit rilis.

Check yang diwajibkan dijalankan pada push ke `dev` untuk SHA yang sama dengan head PR promosi. GitHub menerima workflow job checks dari event `push` untuk evaluasi status PR. Jika workflow `pull_request` yang dihasilkan penggunaan `GITHUB_TOKEN` menunggu persetujuan, hasil push tetap tersedia pada commit head; jalankan/approve workflow PR bila repository menampilkannya dan verifikasi kotak status pada PR. [Dokumentasi event token](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow), [evaluasi required check pada PR](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).

## Pengaturan GitHub yang perlu dilakukan

Branch `dev` sudah dibuat dari `main` pada commit `2660222` dan dipush ke remote pada 5 Oktober 2026. Konfigurasi berikut belum diterapkan; atur repository:

1. Pastikan Actions diizinkan berjalan dan aktifkan **Allow GitHub Actions to create and approve pull requests**, agar job dengan `GITHUB_TOKEN` dan izin `pull-requests: write` dapat membuat PR.
2. Atur branch protection atau ruleset untuk `main`: wajibkan pull request; wajibkan lima check stabil di atas; nonaktifkan force-push dan penghapusan branch.
3. Atur proteksi untuk `dev`: wajibkan pull request dan lima check yang sama agar PR `feat/* → dev` melewati CI.
4. Setelah workflow pertama kali menghasilkan check di GitHub, pilih check dari GitHub Actions sebagai sumber status yang diwajibkan. Verifikasi bahwa setiap check tampil pada PR promosi dan mengikuti SHA head terkini.
5. Pertahankan merge manual. Jangan aktifkan auto-merge untuk PR promosi.

Workflow tidak membuat branch. `dev` kini tersedia dari `main`; perubahan `feat/backend` selanjutnya dikirim melalui PR menuju `dev`.

## Batas verifikasi saat ini

Workflow telah dipush pada `feat/backend` dan dijalankan oleh GitHub Actions pada PR #2 menuju `dev`, tetapi belum digabung ke `dev`. Run terakhir yang dilaporkan pengguna gagal pada 43 test setelah multipart replay import mengembalikan HTTP 400; akar masalahnya adalah dependency parser `python-multipart` belum tercantum. Deklarasi dependency sudah diperbaiki lokal dan suite penuh lulus pada run bersih berikutnya, tetapi fix itu belum dipush dan Actions belum dijalankan ulang. PR tetap terbuka. Lingkungan ini tidak memiliki GitHub CLI dan permintaan baca proteksi branch ke API GitHub mengembalikan HTTP 401 tanpa autentikasi; status atau perubahan branch protection remote tidak dapat diverifikasi.

Test suite lengkap sengaja dijalankan CI agar kegagalan apa pun mencegah promosi. Koreksi composition sebelumnya dipush sebagai `120c587`. Log CI terbaru yang diberikan pengguna menunjukkan kegagalan import multipart. Penambahan `python-multipart` sebagai dependency runtime lulus pada `python -m pytest` di virtualenv baru Python 3.13 (78 passed, 1 warning pada run penuh kedua); run awal memiliki satu kegagalan sementara pada test BE-05 yang lulus saat diulang. Hasil Actions untuk koreksi dependency dan job baru Python 3.13 belum tersedia. CI dirancang menguji batas kompatibilitas 3.11 sekaligus runtime lokal 3.13.

`pyproject.toml` mendeklarasikan dependency dengan rentang; workflow memasang deklarasi itu dan tidak mengklaim dependency terkunci. Opsi `mypy --follow-imports=skip` memang melewati imported modules. Build frontend tidak menjadi check karena entry point saat ini mengimpor `frontend/src/App` dan `frontend/src/styles.css` yang tidak tersedia pada source yang diperiksa. Tidak ada browser, provider, model, data mitra, secret, feed/audio produksi, live advisory, atau langkah deployment yang digunakan.
