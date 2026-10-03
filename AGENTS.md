# Panduan untuk coding agent

## Batas proyek

ATC FlowLens ditujukan menjadi advisory berbukti bagi controller Tower/Ground untuk operasi runway. MVP yang direncanakan adalah replay offline dari simulator mitra dengan kandidat opsi AI yang ditinjau evaluator; selama mitra belum tersedia, gunakan baseline sintetik berbasis sumber resmi dan labeli belum tervalidasi terhadap operasi. Tidak ada mitra atau akses data yang dikonfirmasi per 3 Oktober 2026. Controller tetap memegang keputusan dan kewenangan clearance. Tujuan live advisory adalah arah jangka panjang, bukan izin integrasi operasional: jangan sambungkan production feed/audio atau tampilkan rekomendasi pada posisi aktif sebelum intended use, izin ANSP/pemilik data, keamanan, human factors, safety assurance, dan kewajiban regulator ditentukan.

## Urutan sumber kebenaran

- **Perilaku saat ini:** periksa source code dan test yang relevan. `docs/IMPLEMENTATION_STATUS.md` adalah inventaris bertanggal, bukan pengganti inspeksi source atau verifikasi runtime.
- **Produk dan arsitektur yang dituju:** ikuti `docs/Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md`. Kode yang sudah ada tidak otomatis mengubah kebutuhan target.
- **Requirement AI advisory:** ikuti `docs/Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md` untuk replay simulator berizin, transkripsi/evidence, kandidat opsi offline, dan gate menuju live advisory. Prompt itu adalah target dokumen, bukan bukti implementasi atau izin live integration.
- **Evidence domain:** gunakan `docs/Knowledge-Review/ATC_FlowLens_Operational_Reality_Research.md`; pertahankan cakupan, tanggal, dan label kepastian setiap klaim.
- **Latar belakang dan presentasi:** `docs/General-Information/`, proposal, materi mentor, dan pitch deck adalah konteks atau materi komunikasi eksternal. Dokumen tersebut bukan spesifikasi implementasi.
- Jika sumber-sumber ini bertentangan, jelaskan konflik dan pisahkan implementasi saat ini, rancangan target, dan evidence. Minta keputusan pengguna sebelum mengubah scope produk.

## Menggunakan konteks proyek

1. Baca file ini dan `docs/README.md` terlebih dahulu.
2. Muat hanya bagian rencana teknis dan source yang relevan dengan tugas; gunakan peta dokumen dan jangan anggap seluruh dokumen wajib dibaca.
3. Nyatakan status implementasi secara tepat: bedakan **ada di source**, **berhasil dibuild**, **berjalan**, **lulus test**, **direview pakar domain**, dan **tervalidasi secara operasional**. Jangan menyimpulkan status yang lebih tinggi dari bukti yang ada.
4. Saat fitur penting atau status terverifikasi berubah, perbarui dokumen kanonis yang relevan dan inventaris implementasi bertanggal. Hindari menyalin seluruh arsitektur atau roadmap ke dokumen ringkasan.
5. Laporkan pemeriksaan yang benar-benar dijalankan dan hasilnya. Inspeksi statis bukan bukti build, runtime, atau test berhasil.
