# Panduan untuk coding agent

## Batas proyek

ATC FlowLens adalah proyek simulasi, pelatihan keselamatan runway, dan replay. MVP menggunakan skenario sintetik dan ditujukan untuk dijalankan secara lokal atau pada LAN laboratorium. Produk ini bukan sistem ATC live, tidak menerbitkan clearance operasional, dan tidak menggantikan controller. Jangan menambahkan akses data live, rekomendasi operasional, atau klaim sertifikasi/manfaat keselamatan tervalidasi kecuali pengguna secara eksplisit mengubah scope dan evidence yang diperlukan tersedia.

## Urutan sumber kebenaran

- **Perilaku saat ini:** periksa source code dan test yang relevan. `docs/IMPLEMENTATION_STATUS.md` adalah inventaris bertanggal, bukan pengganti inspeksi source atau verifikasi runtime.
- **Produk dan arsitektur yang dituju:** ikuti `docs/Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md`. Kode yang sudah ada tidak otomatis mengubah kebutuhan target.
- **Evidence domain:** gunakan `docs/Knowledge-Review/ATC_FlowLens_Operational_Reality_Research.md`; pertahankan cakupan, tanggal, dan label kepastian setiap klaim.
- **Latar belakang dan presentasi:** `docs/General-Information/`, proposal, materi mentor, dan pitch deck adalah konteks atau materi komunikasi eksternal. Dokumen tersebut bukan spesifikasi implementasi.
- Jika sumber-sumber ini bertentangan, jelaskan konflik dan pisahkan implementasi saat ini, rancangan target, dan evidence. Minta keputusan pengguna sebelum mengubah scope produk.

## Menggunakan konteks proyek

1. Baca file ini dan `docs/README.md` terlebih dahulu.
2. Muat hanya bagian rencana teknis dan source yang relevan dengan tugas; gunakan peta dokumen dan jangan anggap seluruh dokumen wajib dibaca.
3. Nyatakan status implementasi secara tepat: bedakan **ada di source**, **berhasil dibuild**, **berjalan**, **lulus test**, **direview pakar domain**, dan **tervalidasi secara operasional**. Jangan menyimpulkan status yang lebih tinggi dari bukti yang ada.
4. Saat fitur penting atau status terverifikasi berubah, perbarui dokumen kanonis yang relevan dan inventaris implementasi bertanggal. Hindari menyalin seluruh arsitektur atau roadmap ke dokumen ringkasan.
5. Laporkan pemeriksaan yang benar-benar dijalankan dan hasilnya. Inspeksi statis bukan bukti build, runtime, atau test berhasil.
