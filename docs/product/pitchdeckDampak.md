# Konten pitch deck — Dampak FlowLens

**Status:** usulan konten, 12 Oktober 2026. V1 adalah replay offline untuk evaluasi/pelatihan; manfaat di bawah ini adalah hipotesis yang harus diuji, bukan hasil yang sudah tercapai.

## Slide utama: Dampak yang akan dibuktikan

**Judul:** Dampak yang bisa diukur dalam simulasi

**Subjudul:** FlowLens membantu evaluator menemukan konteks dan memeriksa bukti komunikasi lebih cepat dan lebih lengkap.

| Dampak | Angka yang ditampilkan setelah pilot | Cara ukur |
| --- | --- | --- |
| **Lebih cepat menemukan konteks** | **Δ waktu per tugas (detik; %)** | Median waktu menemukan instruksi terakhir untuk pesawat tertentu, dengan vs tanpa FlowLens |
| **Lebih sedikit kewajiban terlewat** | **Δ open loop terlewat (jumlah/sesi)** | Request, readback, atau report yang masih menunggu tetapi tidak ditemukan evaluator |
| **Temuan bisa ditelusuri** | **Target 100% temuan yang diterima memiliki tautan bukti** | Audit ID bukti ke kutipan/audio/event pada sesi yang sama; ini syarat desain, bukan hasil pilot |

**Footer kecil:** Pilot replay offline · baseline dan hasil belum tersedia · bukan klaim penurunan insiden atau kesiapan operasi aktif.

### Narasi presenter (±25 detik)

“Dampak pertama yang kami uji bukan jumlah kecelakaan, melainkan pekerjaan yang FlowLens bantu langsung: menemukan instruksi terakhir, melihat kewajiban yang belum tertutup, dan memeriksa asal setiap temuan. Dalam pilot simulasi, kami akan membandingkan tugas yang setara dengan dan tanpa FlowLens. Kami laporkan selisih waktu dalam detik, jumlah open loop yang terlewat per sesi, serta proporsi temuan yang memiliki bukti yang benar-benar dapat dibuka. Hasil ini menentukan apakah produk layak dilanjutkan ke studi domain yang lebih besar.”

## Angka yang sudah ada dan tepat penggunaannya

- **1.694 personel (2021) → 1.677 (2025)** pada tabel draft: selisih **−17 atau −1,0% dalam empat tahun**. Seri berfluktuasi: **2024 1.659 → 2025 1.677 (+1,1%)**. Gunakan sebagai konteks masalah, bukan dampak FlowLens atau bukti penurunan tahunan yang konsisten.
- Riset internal telah memproses **50 klip audio unik, total 1 jam 19 menit 50 detik, dengan 123 segmen berteks**. Ini menunjukkan bahan eksplorasi tersedia, tetapi **belum ada label gold, pengukuran salah/benar, atau review ATCO**. Jangan tampilkan sebagai bukti efektivitas.
- PRD menetapkan **100% accepted findings/options memiliki ID bukti yang valid** sebagai invariant release. Tulis “target/syarat”, bukan “hasil tercapai”.

## Rancangan pengukuran pilot

1. **Pembanding:** replay/audio dan transcript biasa vs replay FlowLens. Tugas, sumber, tingkat kesulitan, dan waktu yang tersedia dibuat setara; urutan kondisi diseimbangkan.
2. **Tugas:** temukan instruksi terakhir dan revisinya; identifikasi request/report yang belum mendapat respons; verifikasi satu kandidat perbedaan readback dengan audio.
3. **Metrik utama:** median waktu tugas (detik); open loop terlewat per sesi; kesalahan interpretasi per tugas; proporsi temuan dengan bukti yang dapat diakses. Laporkan jumlah peserta, jumlah sesi, kasus eligible, dan rentang hasil; jangan hanya melaporkan persentase.
4. **Metrik kualitas yang menjaga interpretasi:** wrong-pair rate (instruksi–readback salah dipasangkan), critical-slot error, false findings per eligible audio hour, serta unknown/abstention rate. Perbaikan waktu yang dibayar dengan kenaikan salah pasangan bukan keberhasilan.
5. **Gate:** tetapkan target peningkatan hanya setelah baseline diukur dan rubric dibekukan. Hasil sintetis, corpus publik, simulator mitra, dan operasi nyata dilaporkan terpisah.

**Rumus setelah data pilot tersedia:** penurunan waktu = `(median baseline − median FlowLens) / median baseline × 100%`; perubahan open loop terlewat = `rerata baseline − rerata FlowLens` per sesi. Untuk semua rasio kualitas, sertakan pembilang, penyebut, dan kasus yang dikeluarkan karena data tidak layak.

## Koreksi klaim draft yang memengaruhi narasi dampak

- FAA menyebut **1.756 runway incursions** pada **FY2023** dari sekitar 54,4 juta takeoff/landing AS. Sekitar **20%** dikaitkan dengan *air traffic controller action or inaction* dalam kategorisasi FAA. Angka itu **bukan 1.756 kecelakaan pesawat**, dan **bukan bukti 20% akibat miskomunikasi**. Jangan menghitung “insiden yang dicegah FlowLens” dari angka ini.
- Rasio `personel ATC / flight / runway` pada draft bukan ukuran beban kerja controller tanpa shift, sektor, durasi tugas, mix trafik, dan prosedur lokal. Tidak cocok sebagai angka dampak atau dasar klaim kebutuhan Juanda tanpa validasi tambahan.
- V1 belum dipakai pada posisi ATC aktif. Dampak yang sah diklaim pada tahap ini terbatas pada **review/pelatihan dalam replay** setelah pilot menghasilkan data.

## Dasar

- [PRD FlowLens](../../.agent/PRD.md), terutama §34.4–34.7 dan §36–37.
- [Handoff riset](../../.agent/sessionHandoff.md), bagian “Volume dan hasil nyata” serta keterbatasan benchmark/domain.
- `Draft Pitchdeck.pdf` dari pengguna, hlm. 1–5 (tabel personel dan kerangka slide Dampak).
- [FAA, kesaksian tentang runway incursions FY2023](https://www.faa.gov/testimony/statement-timothy-l-arel-chief-operating-officer-air-traffic-organization-hearing-united).
- [EUROCONTROL, SHAPE: evaluasi kemitraan manusia–otomasi](https://www.eurocontrol.int/product/solutions-human-automation-partnerships-european-atm).
