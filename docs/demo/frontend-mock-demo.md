# Demo script — FlowLens frontend (MOCK track)

Tanggal: 8 Oktober 2026. Durasi inti ±12 menit, ditambah ±5 menit skenario opsional. Bahasa UI: English. Semua data **SYNTHETIC + MOCK** dan dilayani adapter in-browser. Tidak ada backend, provider (STT/Gemini) atau audio. Kalimat narasi ditulis dalam tanda kutip dan boleh dibacakan apa adanya.

Pesan utama untuk audiens: *"Yang kalian lihat adalah UI dan perilaku produk yang final secara alur. Datanya simulasi. Nanti adapter mock diganti dengan backend nyata tanpa mengubah layar."*

---

## 1. Persiapan (sekali, sebelum demo)

```bash
cd frontend
npm install
npm run dev
```

1. Buka `http://localhost:5173` di Chrome, jendela lebar ≥ 1440 px. Zoom browser 100%.
2. Pakai **satu tab** saja. Status login disimpan per tab (sessionStorage), jadi tab baru perlu login ulang.
3. **Refresh halaman akan me-reset data mock** (review, export dan brief baru hilang), tetapi login tetap. Gunakan ini untuk mengulang demo dari awal.
4. Di pojok kanan bawah ada tombol oranye **Mock** (ikon labu) untuk mengaktifkan skenario gangguan. Pastikan semua switch mati sebelum mulai.

### Target nanti

`npm run dev` hanya menjalankan frontend. Pada versi integrasi, frontend berbicara ke FastAPI host + worker (setelah gate G-BE lulus), dan tombol Mock hilang dari build produksi.

---

## 2. Login

Halaman `/login` menampilkan kartu **MOCK demo accounts**. Klik salah satu kartu untuk mengisi email, lalu klik **Sign in**. Password untuk semua akun demo adalah `flowlens-demo`.

| Akun | Email | Role | Kegunaan di demo |
| --- | --- | --- | --- |
| Khalfani Shaquille | `evaluator@flowlens.test` | Evaluator | Alur utama: review, debrief, export |
| Sam Ortiz | `controller@flowlens.test` | Controller review | Review tanpa export |
| Ira Santoso | `observer@flowlens.test` | Observer | Menunjukkan akses read-only |
| Nizam Rahman | `admin@flowlens.test` | Administrator | Settings/admin |

Akun `tyler@flowlens.test` nonaktif dan dipakai untuk menunjukkan login yang ditolak.

Ganti role di tengah demo lewat **menu akun** (nama di kiri bawah sidebar), lalu pilih akun lain. Cache data dibersihkan setiap kali akun berganti.

> "Setiap orang punya akun sendiri, tidak ada login bersama. Kemampuan seseorang ditentukan oleh role dan grant per sesi, dan server mengecek setiap request."

**Target nanti:** login memakai akun individual di backend (cookie httpOnly, idle timeout, reset password oleh admin). Kartu demo dan password bersama tidak ada di produksi.

---

## 3. Alur demo inti (login sebagai Evaluator)

### Langkah 1 — Sessions (comp 01) · ±1 menit

Setelah login, aplikasi membuka **Sessions**.

- Bila sebelumnya sudah membuka sesi, kartu **Continue where you left off** di atas menampilkan sesi dan layar terakhir beserta jumlah finding terbuka.
- Tunjukkan strip KPI, tabel sesi, dan label `SYNTHETIC` / `MOCK` / `Replay offline`. Status Archived tampil sebagai badge di judul, terpisah dari kolom Analysis.
- Klik area baris **Runway 27 · Readback** (bukan judulnya). Panel kanan menampilkan tiga readiness: source ready, analysis, dan review. Klik judul sesi (atau Enter saat fokus) langsung membuka Workspace.
- Item di **Needs checking** membuka tempat penyelesaiannya: finding ke Review, open loop/divergence ke Workspace.

> "Source siap, analisis selesai, dan sudah di-review adalah tiga status berbeda. Kami tidak menggabungkannya menjadi satu centang hijau."

Klik **Open workspace**.

**Target nanti:** daftar sesi datang dari database host. Badge analysis mengikuti job worker yang sebenarnya.

### Langkah 2 — Workspace replay (comp 03) · ±3 menit

Workspace dibuka pada **05:22**, mode **As-known**.

1. **Situation canvas.** Tunjukkan FLN214 di hold line RWY 27, FLN402 di runway, dan VEH03 dengan label "Position not available".
   > "Garis solid adalah posisi yang diamati, garis putus-putus adalah prediksi. Objek tanpa footprint diberi tanda centre-point dan tidak pernah dianggap aman."
2. **Memory strips.** Baca baris FLN214: Instruction *Hold short RWY 27*, Readback *Mismatch*, Movement *NOT_EVALUABLE* berwarna abu-abu.
   > "Said, Heard dan Observed selalu dipisah. Status yang tidak bisa dinilai berwarna abu-abu, tidak pernah hijau."
3. **Needs attention.** Kartu **F-03 · Runway mismatch** ada di panel kanan. Klik kartu: rentang 05:12–05:19 tersorot di timeline.
4. **Timeline.**
   - Tekan **Space** untuk play/pause. Jarum bergerak, dan pill bertuliskan "Visual replay · audio not loaded (MOCK)".
   - Gunakan **← / →** untuk seek dan zoom **1m / 5m / All**.
5. **As-known vs Debrief.**
   - Di As-known 05:22, panel bawah canvas menyebut beberapa item tersembunyi.
   - Klik **Debrief**: item yang datang belakangan (misalnya koreksi E-14 pada 05:24) ikut tampil.
   - Kembalikan ke **As-known**.
   > "As-known menampilkan apa yang diketahui saat itu. Informasi masa depan tidak bocor. Debrief adalah kacamata post-hoc."

**Target nanti:**
- Posisi datang dari track/event sumber dan diselaraskan dengan clock mapping.
- Audio benar-benar bisa diputar per rentang evidence (sesuai izin).
- Mode Follow leader mengikuti stream WebSocket dari host.
- Filter as-of tetap dilakukan di server.

### Langkah 3 — Evidence drawer · ±1 menit

Di kartu F-03, klik **Listen to evidence**. Drawer evidence terbuka di kanan.

- **Said:** "Hold short runway two seven" (E-12). **Heard:** "Holding short runway zero nine" (E-13). Slot runway disorot.
- Buka tab **Audio** untuk melihat association bar dan slot table. Buka **Alternatives & provenance** untuk melihat versi model, prompt dan rule.
- Tutup drawer. Posisi replay tidak berubah.

> "Setiap pernyataan bisa ditelusuri ke evidence. Membuka evidence tidak menggeser jam replay."

**Target nanti:** quote dan span datang dari transcript STT nyata, audio range diputar dari asset turunan, dan versi model/prompt tercatat dari run yang sebenarnya.

### Langkah 4 — Review: Transcript, Findings, Options (comp 05–07) · ±3 menit

Klik **Review** di sidebar. Review, Debrief, Metrics dan Ask membaca **seluruh sesi** (Debrief) secara default; As-known opsional dan menampilkan banner jumlah item yang baru tersedia kemudian, dengan tombol **Show full session**. Sesi bisa diganti dari switcher **Current session** di sidebar tanpa kehilangan area.

1. **Findings** (pilih tab Findings, F-03).
   - Tunjukkan detail: category, priority, "Still unknown: speaker identity", dan **Source alert** yang dicatat terpisah dari AI finding.
   - Di **Reviewer decision**, ketiga opsi awalnya kosong dan **Save review** belum aktif.
   - Filter default **Needs review** dengan progres "0 of 5 reviewed". **J / K** pindah antar finding; **1 / 2 / 3** memilih keputusan; **⌘/Ctrl+Enter** menyimpan.
   - Pilih **Cannot be determined yet** dan tulis alasan, misalnya: *Speaker identity not confirmed in audio.* Klik **Save review**.
   - Halaman tetap di F-03: status "Review saved for F-03 · revision 1" dengan tombol **Next finding**, riwayat review tampil, dan form kembali kosong. "Advance after saving" default mati.
   - Pindah item dengan draft belum tersimpan memunculkan dialog **Discard draft?**.
   > "Review tidak menimpa apa pun. Setiap keputusan menjadi revisi baru dengan alasan wajib, dan acknowledge tidak sama dengan confirm."
2. **Transcript.**
   - Baris **07:02 "Roger, holding."** berlabel AMBIGUOUS dan terpilih otomatis.
   - Tunjukkan **Original STT hypothesis** yang read-only, link **Cited by F-07**, lalu tab **Pairing** (kandidat FLN214/VEH03, terbuka otomatis karena ambigu) dan tab **Correction** yang terpisah.
   > "Teks STT asli tidak pernah diubah. Koreksi menjadi revisi baru, dan hasil turunan ditandai stale sampai dianalisis ulang."
   - Opsional: simpan koreksi dengan alasan untuk menunjukkan banner stale dan tombol **Re-analyse as new run**. Run baru tidak dipilih otomatis.
3. **Options.**
   - Tunjukkan opsi *Check the instruction–readback pairing*: evaluation question, Preconditions vs Still unknown, dan label `LAB_ONLY`.
   - Tunjukkan kartu **Insufficient context · VEH03**.
   > "Opsi adalah hipotesis untuk evaluator. Tidak ada tombol execute atau send, dan sistem tidak pernah memberi clearance."

**Target nanti:**
- Findings dan opsi dihasilkan pipeline worker (STT → intent → association → findings → options) dengan rule versi lab.
- Koreksi memicu re-analysis sebagai run baru di backend.
- Conflict antar reviewer ditangani lewat `expectedVersion`.

### Langkah 5 — Debrief & export (comp 08) · ±2 menit

Klik **Debrief**.

1. **Review status** di kolom kanan menampilkan progres dan **Continue reviewing · F-03**. **Journal**: filter **Key / All**, scroll di dalam panel dengan isyarat "Scroll for more". Event E-13 "zero nine" dan koreksi E-14 terlihat berurutan.
2. **Session summary**: kartu biru **Key item to review — F-03**, berlabel "AI interpretation · MOCK". Bagian Known situation, Context changes, Still open dan Unknown & coverage masing-masing punya chip evidence.
3. Di dropdown **Brief rev. 2**, pilih **Brief rev. 1 · stale**. Muncul callout stale, as-of 05:22, dan journal yang berhenti sebelum E-14. Klik **Open brief revision 2**.
4. **Export report** (tombol di header, membuka sheet di kanan):
   - Pilih format HTML/CSV/JSON. **Include provenance** terkunci menyala, dan **Include audio** dinonaktifkan dengan alasan.
   - Klik **Create export**: status berjalan Preparing → Ready, lalu **Download** muncul. File dibuat lokal oleh mock dan membawa label SYNTHETIC/MOCK serta header provenance.

> "Brief juga append-only: revisi lama tetap ada dan ditandai stale bila input berubah. Export selalu membawa provenance dan menghormati izin audio serta masa berlaku."

**Target nanti:** brief disusun model di worker dari hasil run, export dibuat sebagai job di host dengan expiry dan redaksi sesuai grant, dan download lewat URL bertanda tangan.

### Langkah 6 — P1: Metrics & Ask · ±1 menit

1. **Metrics** (badge P1 · Experimental):
   - KPI active audio, open loops dan object switches, dengan perbandingan ke run sebelumnya.
   - Grafik per menit (skala mengikuti data, maksimum 60 s): gap audio tampil sebagai unknown (arsir abu-abu), bukan nol. Klik satu bar untuk beralih ke As-known pada menit itu.
   > "Ini indikator eksperimental, bukan penilaian beban kerja atau kinerja."
2. **Ask**:
   - Klik saran *What was the last instruction to FLN214?* Jawaban muncul dengan chip evidence.
   - Lalu ketik *Is runway 27 clear for departure?* dan tekan Enter. Jawabannya **Unknown · not covered** tanpa evidence.
   > "Jawaban hanya dari evidence sesi ini pada as-of saat ini. Pertanyaan soal clear/safe selalu dijawab Unknown."

**Target nanti:** Ask memakai model (Gemini) dengan konteks terbatas pada sesi/run/as-of dan validasi output. Metrics dihitung dari VAD/segmentasi nyata, tetapi tetap berlabel eksperimental (P1).

### Langkah 7 — Role & Settings · ±1 menit

1. Ganti akun ke **Observer** lewat menu akun, lalu buka **Review → Findings**. Form diganti "Review is read-only for your role".
2. Ganti akun ke **Administrator** dan buka **Settings**:
   - Users (aktif/nonaktif, reset password).
   - Session access (grant per sesi; revoke langsung memicu resync).
   - Providers: metadata saja, tanpa key. **Check readiness** hanya pemeriksaan mock.
   - Jobs & budget (retry job gagal), Storage (ambang 80/90%), Audit log, Retention (purge hanya berupa *request* dua langkah).
3. Tutup dengan **Help**: legend status, kategori finding, provenance dan shortcut keyboard.

**Target nanti:** semua aksi admin menulis audit di host, provider readiness memanggil smoke test nyata di server, dan key tidak pernah sampai ke browser.

---

## 4. Skenario opsional (tombol Mock, ±5 menit)

Panel dibuka dari **Mock control** di footer sidebar (di layar sempit: di dalam menu navigasi). Nyalakan satu switch, tunjukkan efeknya, lalu matikan lagi. Switch disimpan di memori, jadi refresh halaman juga mematikannya. Nyalakan switch setelah halaman tujuan terbuka.

| Switch | Apa yang ditunjukkan | Di mana |
| --- | --- | --- |
| Provider outage | Hasil cache tetap terbaca. Create brief revision / Ask / readiness check gagal dengan pesan jelas, tanpa konten palsu | Debrief, Ask, Settings → Providers |
| Connection lost | Banner koneksi terputus. Tombol simpan pause dan draft tetap ada; tidak ada antrean diam-diam | Workspace, Findings |
| Conflict on next save | Simpan review → callout "A newer review was saved by someone else", draft dipertahankan | Findings / Transcript |
| Audio access denied | Player evidence terkunci dengan pesan pembatasan, bukan waveform kosong | Evidence drawer |
| Stale tracks | Movement menjadi NOT_EVALUABLE (abu-abu), marker pudar | Workspace |
| Empty catalogue | Empty state di Sessions | Sessions |
| Disk at 91 % | Status "Imports on hold" | Settings → Storage |
| Sign-in expired | Request berikutnya mengembalikan ke halaman login | Di mana saja |

Slider latency di panel Mock bisa dinaikkan untuk menunjukkan loading state.

---

## 5. Hal yang perlu disampaikan jujur

- Ini **MOCK track**: belum ada backend, provider atau audio. Gate G-FE tetap *blocked* sampai backend nyata lulus G-BE dan journey dijalankan ulang terhadapnya.
- Data, layout bandara dan callsign fiktif (SYNTHETIC) dan belum divalidasi domain (NOT_DOMAIN_VALIDATED).
- FlowLens adalah alat **replay/riset**, bukan sistem operasional. Tidak ada LIVE, tidak ada clearance, dan controller tetap memegang otoritas penuh.

## 6. Troubleshooting cepat

| Gejala | Solusi |
| --- | --- |
| Diminta login lagi | Tab baru atau switch "Sign-in expired" aktif. Login ulang dan matikan switch |
| Review/export yang tadi dibuat hilang | Halaman di-refresh; data mock in-memory di-reset (sesuai desain) |
| Item tidak muncul di Findings | Cek mode dan as-of: di As-known, item dengan *available time* setelah as-of memang disembunyikan |
| Replay tidak bergerak | Klik area halaman lalu tekan Space, atau tekan tombol play |
