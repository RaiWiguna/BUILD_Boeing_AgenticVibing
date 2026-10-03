# Status Implementasi ATC FlowLens

- **Pemeriksaan statis terakhir:** 3 Oktober 2026
- **Cakupan:** inventaris source/config/docs yang ada di repository
- **Metode:** inspeksi berkas saja; build, startup, API runtime, dan test tidak dijalankan.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, model kontrak, simulasi, deteksi, sesi, review, laporan, dan arsip SQLite tersedia di `backend/`. | Belum diverifikasi saat runtime. |
| API dan stream | Source mendefinisikan endpoint health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, serta WebSocket stream. | Kehadiran route di source tidak membuktikan alur API berhasil. |
| Persistensi | Source `backend/storage.py` menyediakan arsip SQLite untuk metadata, event, snapshot, checkpoint, dan command. | Belum ada hasil uji recovery, durability, beban, atau concurrency dalam pemeriksaan ini. |
| Frontend | `frontend/` memiliki konfigurasi Vite, entry point React, API helper, dan type TypeScript. | Belum menjadi dashboard: `main.tsx` mengimpor `App` dan `styles.css`, tetapi kedua modul tersebut tidak tersedia pada pemeriksaan ini. |
| Penyajian UI | `backend/app.py` menyajikan bundle dari `frontend/dist`; direktori tersebut belum memiliki `index.html`. Tanpa hasil build, route `/` mengembalikan halaman instruksi dengan HTTP 503. | Belum dapat digunakan sebagai aplikasi web end-to-end dari kondisi bundle yang diperiksa. |
| Test dan validasi manusia | Tidak ditemukan direktori `tests/` atau hasil test pada pemeriksaan ini. | Tidak ada klaim test lulus, review trainer, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |

## Arsitektur target yang didokumentasikan

Rencana Teknis MVP menetapkan satu proses server lokal/LAN sebagai pemilik state sesi, frontend browser React/TypeScript, REST untuk command dan arsip, WebSocket untuk snapshot sinkron, Shapely untuk geometri, serta SQLite lokal untuk persistence. Alur target memisahkan truth simulator dari observasi yang diterima detector, lalu membentuk prediksi occupancy dan alert yang menyertakan evidence serta kualitas data. Sesi ditujukan untuk latihan multi-peran, replay, dan debrief.

Arsitektur tersebut adalah target spesifikasi. Rincian acceptance dan batas MVP berada di [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md); kode aktual perlu diperiksa terpisah sebelum menyatakan bagian target telah selesai.

## Batas produk yang berlaku

- MVP menggunakan skenario sintetik dan ditujukan untuk training/replay; bukan integrasi live ATC.
- FlowLens tidak menerbitkan clearance operasional dan tidak mengambil alih keputusan controller.
- AI transkripsi/parsing komunikasi, koneksi surveillance operasional, sertifikasi, serta klaim pengurangan insiden belum menjadi hasil implementasi yang dibuktikan.
- Indikator kompleksitas/workload adalah konteks eksperimen, bukan diagnosis kondisi mental atau ukuran fitness-for-duty.

## Memperbarui status

Perbarui tanggal dan tabel ini setelah ada perubahan implementasi atau verifikasi yang berarti. Sebutkan command/check yang benar-benar dijalankan dan hasilnya. Pisahkan status source, build, runtime, automated test, domain review, dan operational validation; jangan gabungkan menjadi satu label “selesai”.
