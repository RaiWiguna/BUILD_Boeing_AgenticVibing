# Riset regulasi — FlowLens sebagai produk live di berbagai bandara

**Status:** desk research, 13 Oktober 2026. Dokumen ini **bukan opini hukum** dan **belum dikonfirmasi** oleh Ditjen Perhubungan Udara (DJPU), AirNav Indonesia, maupun konsultan hukum. Setiap butir diberi label sumber: **[P]** = sumber primer (teks peraturan atau dokumentasi resmi yang dibaca langsung), **[S]** = sumber sekunder (berita/ringkasan firma hukum), **[V]** = perlu verifikasi sebelum dipakai di pitch atau proposal.

Konteks produk: FlowLens mengubah audio komunikasi Tower/Ground menjadi transcript (Google STT), memakai Gemini untuk intent dan memori operasi, lalu menampilkan temuan dan kandidat opsi. V1 adalah replay offline ([PRD](../../.agent/PRD.md) §3.3). Riset ini menilai apa yang berubah bila FlowLens dipakai secara nyata di bandara.

## 1. Ringkasan eksekutif

1. **Satu pintu utama: AirNav Indonesia.** PP 77/2012 menjadikan Perum LPPNPI (AirNav) satu-satunya penyelenggara pelayanan navigasi penerbangan sipil [S]. Penerapan di "berbagai bandara" berarti satu negosiasi korporat dengan kantor pusat AirNav, bukan negosiasi per bandara. Pengecualian: bandara enclave sipil-militer (ATC oleh TNI AU) dan bandara yang hanya punya AFIS/UPBU.
2. **Persetujuan regulator tidak diajukan oleh tim FlowLens.** CASR 172.085 mewajibkan **penyelenggara ATS** melakukan safety assessment untuk "implementasi dari komunikasi yang baru, pengawasan atau sistem peralatan keselamatan penting lainnya, termasuk yang menyediakan fungsi dan/atau kemampuan yang baru" sebelum perubahan dijalankan [P]. FlowLens berposisi sebagai **pemasok**; AirNav adalah **pemohon/sponsor** di hadapan DJPU (Direktorat Navigasi Penerbangan).
3. **Penghambat teknis-hukum terbesar ada di arsitektur kita sendiri.** PRD memakai Gemini Developer API (`store=false`) yang tidak memberi jaminan lokasi pemrosesan. Di Vertex AI, **Jakarta (asia-southeast2) tidak tercantum** sebagai region dengan jaminan ML processing untuk Gemini 3.8 Flash maupun Chirp; Singapura tercantum [P]. Artinya setiap pemrosesan data nyata = **transfer data ke luar negeri** menurut PP 33/2026, dan berpotensi berbenturan dengan aturan penempatan data atau infrastruktur informasi vital, bergantung klasifikasi AirNav [V].
4. **Rekaman ATS adalah data sensitif dengan pemilik yang jelas.** CASR 172.115 menempatkan rekaman komunikasi air-ground dan ground-ground dalam sistem kontrol dokumen dan rekaman penyelenggara [P]. Penjelasan Pasal 359 UU 1/2009 mengklasifikasikan rekaman dan transkrip pembicaraan ATS sebagai **informasi rahasia dalam konteks investigasi KNKT** [S]. Akses audio harus melalui perjanjian data dengan AirNav, bukan menangkap frekuensi radio sendiri (UU 36/1999 Pasal 40 melarang penyadapan informasi yang disalurkan melalui jaringan telekomunikasi [S]).
5. **Advisory real-time dengan LLM generatif belum punya jalur assurance.** EASA NPA 2025-07 (AI Level 1 & 2) secara eksplisit baru mencakup ML berbasis data; AI generatif dan hybrid ditunda ke tahap berikutnya [P/S]. Belum ada regulator penerbangan yang menerbitkan jalur sertifikasi untuk LLM di posisi kerja ATC. Ini penghambat nyata untuk Tier 3 (lihat §2).
6. **Pendukung kuat ada:** AirNav sudah mengembangkan AI asisten (NOTAM AI Generator, penjadwalan ATCO berbasis fatigue) bersama Telkom University, dengan kerja sama riset baru ditandatangani 8 Oktober 2026 [S]. Ditambah ICAO Annex 19/SMS yang mendorong analisis data keselamatan, preseden SESAR (HAAWAII, ASR TRL6) dan CAAS Singapura, serta kebijakan TKDN yang menguntungkan software lokal.

**Rekomendasi inti:** definisikan "live" secara bertahap. Tahap yang paling realistis dalam 12–18 bulan adalah **Tier 2: QA/safety/training review internal AirNav atas rekaman terbaru, di luar posisi kerja**. Advisory real-time (Tier 3) diposisikan sebagai riset jangka panjang.

## 2. "Live" mengubah profil regulasi — tiga tier

| Tier | Bentuk penggunaan | Data | Beban regulasi | Mitra utama |
| --- | --- | --- | --- | --- |
| **1. Training/simulator** | Replay sesi simulator ATC di lembaga diklat | Audio simulator, suara siswa/instruktur | **Rendah.** Persetujuan peserta, PDP dasar, tidak menyentuh pelayanan ATS | PPI Curug / Poltekbang (BPSDM Perhubungan), training center AirNav |
| **2. Review operasional pasca-kejadian** | QA, safety investigation internal, debrief, pelatihan berbasis rekaman nyata; **tidak di posisi kerja aktif** | Rekaman ATS nyata (beberapa jam–hari setelah kejadian) | **Sedang–tinggi.** Perjanjian data dengan AirNav, DPIA, transfer lintas negara, kerahasiaan rekaman, penerimaan ATCO/just culture | AirNav (Direktorat Keselamatan/QA, Operasi, TI) |
| **3. Advisory real-time** | Copilot di posisi Tower/Ground (FR-19/FR-20 PRD) | Feed audio live dari VCCS/voice recorder | **Sangat tinggi.** Perubahan sistem fungsional ATS (CASR 172.085), safety case, kemungkinan sertifikasi fasilitas, latensi/ketersediaan, keamanan siber IIV, AI assurance yang belum ada untuk LLM | AirNav + DJPU (DNP), BSSN, Kemenhub |

Tier 2 sudah dapat disebut "dipakai di berbagai bandara" tanpa menjadi bagian dari pelayanan ATS secara langsung. Namun bila hasilnya dipakai untuk menilai kinerja individu controller, kategorinya berubah (lihat §3.4).

## 3. Regulasi Indonesia

### 3.1 Penerbangan dan pelayanan ATS

| Regulasi | Isi relevan | Efek bagi FlowLens |
| --- | --- | --- |
| **UU 1/2009 Penerbangan** (sebagian dicabut UU 21/2025) | Kerangka navigasi penerbangan; Penjelasan Pasal 359: rekaman/transkrip pembicaraan ATS termasuk "informasi rahasia" hasil investigasi [S] | **Penghambat** untuk publikasi atau ekspor transcript. Pastikan output FlowLens tidak dianggap pengungkapan informasi investigasi; atur di perjanjian |
| **PP 77/2012 Perum LPPNPI** | AirNav sebagai penyelenggara tunggal navigasi penerbangan sipil [S] | **Pendukung** (satu pintu untuk skala nasional) sekaligus **penghambat** (satu pembeli, tergantung prioritas dan pengadaan AirNav) |
| **PM 43/2020 — CASR Part 172** (Penyelenggara Pelayanan Lalu Lintas Penerbangan) | 172.075: "fasilitas otomasi" bagian dari fasilitas ATS. 172.080: wajib SMS. **172.085**: safety assessment wajib untuk sistem baru yang menyediakan fungsi baru; implementasi hanya jika risiko dapat diterima; wajib post-implementation monitoring. 172.115: kontrol dokumen dan rekaman, termasuk rekaman komunikasi air-ground dan ground-ground, dan dapat diminta Dirjen [P] | **Penentu jalur Tier 3.** FlowLens wajib menyediakan bahan safety assessment (hazard log, mode kegagalan, mitigasi automation bias). Mekanisme detail persetujuan ke Dirjen diatur peraturan lain [V] |
| **CASR Part 171** (Penyelenggara Pelayanan Telekomunikasi Penerbangan; KP 528/2015 untuk sertifikasi) | Fasilitas komunikasi, navigasi, dan pengamatan wajib bersertifikat (dirujuk oleh 172.075(b)) [P/S] | Relevan bila FlowLens tersambung langsung ke VCCS/recorder. Apakah software analisis termasuk "fasilitas" yang perlu sertifikat belum jelas [V] |
| **CASR Part 69** (lisensi personel ATC, termasuk English Language Proficiency) | Standar kompetensi dan kemahiran bahasa [V] | **Pendukung** untuk Tier 1: FlowLens dapat dipakai untuk pelatihan phraseology/ELP |
| **UU 21/2025 Pengelolaan Ruang Udara** (ditetapkan 24 Des 2025) | Pengelolaan ruang udara lintas instansi, termasuk Kemhan; detail teknologi diserahkan ke aturan pelaksana [S] | Netral saat ini. Pantau PP pelaksananya, terutama bila menyentuh data ruang udara |
| **PM 9/2024 Program Keamanan Nasional** + IAS-CSIRT | Harmonisasi Annex 17 termasuk ancaman siber [S] | Sistem yang tersambung ke jaringan ATS akan diaudit keamanan siber |

### 3.2 Data pribadi

| Regulasi | Isi relevan | Efek bagi FlowLens |
| --- | --- | --- |
| **UU 27/2022 PDP** | Suara controller/pilot dan callsign yang dapat ditautkan ke individu adalah data pribadi | FlowLens (sebagai prosesor) dan AirNav (sebagai pengendali) tunduk |
| **PP 33/2026** (ditetapkan 16 Juli 2026, **berlaku 16 Januari 2027**) [S] | DPIA wajib untuk risiko tinggi: teknologi baru, keputusan otomatis, **pemantauan sistematis**, skala besar. DPO wajib untuk pelayanan publik atau pemantauan sistematis skala besar. Transfer ke luar negeri: negara tujuan setara, atau klausul kontrak standar. Kontrak pengendali–prosesor wajib. Notifikasi kebocoran 3×24 jam. Denda hingga 2% pendapatan tahunan | **Penghambat utama** untuk Tier 2–3 selama pemrosesan di Singapura/global. Harus ada DPIA, kontrak prosesor, dan dasar transfer sebelum data nyata masuk |
| **Lembaga/Badan PDP** | **Belum terbentuk.** Rancangan Perpres sudah diajukan ke Presiden (Mei 2026) [S] | Tidak ada "izin PDP" yang bisa diurus. Kewajiban PP 33 bersifat **kepatuhan mandiri** yang diaudit kemudian |

### 3.3 Sistem elektronik, lokasi data, dan keamanan siber

| Regulasi | Isi relevan | Efek bagi FlowLens |
| --- | --- | --- |
| **PP 71/2019 PSTE** + Permenkominfo 5/2020 (PSE privat) | PSE privat wajib daftar via OSS. PSE lingkup publik wajib mengelola/menyimpan data di Indonesia (kecuali teknologi tidak tersedia). Pemblokiran untuk yang tidak daftar [S] | Badan usaha FlowLens perlu registrasi PSE privat bila melayani pengguna di Indonesia. **Apakah AirNav (Perum/BUMN) masuk lingkup publik belum terverifikasi** [V]; bila ya, data AirNav yang diproses FlowLens bisa terkena kewajiban lokasi di Indonesia |
| **Perpres 82/2022 Infrastruktur Informasi Vital (IIV)** | Sektor transportasi termasuk IIV, dengan Kemenhub sebagai pembina sektor dan BSSN untuk standar keamanan [S] | Bila sistem ATS AirNav ditetapkan IIV [V], integrasi Tier 3 mengikuti standar keamanan IIV, audit, dan pelaporan insiden ke BSSN |
| **Dokumentasi Google Vertex AI — data residency** | Gemini 3.8 Flash dan Chirp: jaminan ML processing di Singapura, Tokyo, Mumbai, Seoul, Sydney, dll. **Jakarta tidak tercantum.** Global endpoint tidak memberi jaminan lokasi sama sekali [P] | Untuk data nyata: pindah dari Developer API ke **Vertex AI regional `asia-southeast1`** sebagai minimum, atau siapkan opsi on-prem/in-country (ASR open-weight + LLM lokal). Availability Google STT V2 `chirp_3` per region perlu dicek terpisah [V] |

### 3.4 AI dan faktor manusia

| Regulasi / kebijakan | Status | Efek bagi FlowLens |
| --- | --- | --- |
| **SE Menkominfo 9/2023 Etika AI** | Berlaku, tidak mengikat secara sanksi [V] | Pendukung: rujukan prinsip transparansi dan kendali manusia |
| **Rancangan Perpres Peta Jalan AI 2026–2029 & Perpres Etika AI** | Menunggu pengesahan Presiden per September 2026; sektor prioritas belum mencakup transportasi [S] | Belum menghambat. Pantau bila terbit, terutama klasifikasi risiko |
| **Just culture / pemantauan controller** | ICAO Annex 19 App. 3 melindungi data keselamatan dari penggunaan untuk menyalahkan [S]; IFATCA memiliki kebijakan panjang soal penggunaan rekaman [S] | **Penghambat non-hukum terbesar.** Bila FlowLens dipakai menilai kinerja individu, PP 33 menganggapnya "pemantauan sistematis" (wajib DPIA+DPO) dan asosiasi ATCO kemungkinan menolak. Mitigasi: komitmen tertulis **purpose limitation**, yaitu tidak dipakai untuk penilaian individu atau tindakan disipliner, dan output agregat/anonim untuk QA |

### 3.5 Pengadaan

| Regulasi | Efek |
| --- | --- |
| **Permenperin 35/2025 (TKDN)** + kebijakan TKDN minimal 25% untuk belanja pemerintah/BUMN [S] | **Pendukung**: produk software lokal diprioritaskan dalam pengadaan BUMN seperti AirNav. Perlu sertifikat TKDN; mekanisme TKDN untuk software/SaaS perlu dicek [V] |
| Pengadaan internal AirNav | Pengadaan BUMN mengikuti aturan internal perusahaan; jalur awal yang realistis adalah **kerja sama riset/PoC** (seperti pola Telkom University) sebelum tender [S] |

## 4. Regulasi internasional (untuk ekspansi atau pembanding)

| Yurisdiksi | Instrumen | Isi relevan | Efek |
| --- | --- | --- | --- |
| **ICAO** | Annex 11 | Rekaman ATS otomatis disimpan minimal 30 hari [S] | Retensi FlowLens harus mengikuti, bukan memperpanjang tanpa dasar |
| | Annex 19 + Doc 9859 (SMM) | SMS, manajemen perubahan, perlindungan data keselamatan [S] | Pendukung: analisis data keselamatan didorong; FlowLens bisa diposisikan sebagai alat SMS |
| | Assembly ke-42 (2025) | Belasan working paper AI; ICAO menyepakati pendekatan terstruktur untuk mengintegrasikan AI ke pekerjaannya [P] | Belum ada SARPs AI untuk ATM |
| **Uni Eropa** | Reg. 2017/373, ATS.OR.205 | Penyedia ATS wajib safety assessment perubahan "functional system" (prosedur, SDM, peralatan termasuk software); otoritas dapat memilih untuk me-review [S] | Paralel dengan CASR 172.085 |
| | Reg. 2023/1768 & 2023/1769 | Attestation peralatan ATM/ANS: sertifikat, declaration, atau statement of compliance; transisi sampai 13 Sep 2028 [S] | Bila FlowLens masuk sebagai equipment di EU, perlu organisasi desain/produksi yang disetujui |
| | EU AI Act (Reg. 2024/1689) + Digital Omnibus (Reg. 2026/1744) | Aviation masuk Annex I Section B; kewajiban high-risk diterapkan melalui aturan sektoral EASA (Art. 108); tenggat Annex I mundur ke **2 Agustus 2028** [S] | Bukan tenggat langsung bagi FlowLens, tetapi menentukan isi aturan EASA |
| | EASA NPA 2025-07 (RMT.0742) | Spesifikasi AI trustworthiness Level 1 (assistance) & Level 2 (human-AI teaming); hanya ML berbasis data; generatif ditunda; NPA lanjutan 2026 [P/S] | **Penghambat Tier 3**: belum ada jalur assurance untuk LLM. Pendukung: kerangka Level 1 cocok untuk positioning "assistance" |
| | GDPR | Suara controller sebagai data pribadi; EUROCONTROL menerbitkan privacy statement untuk voice logging [S] | DPIA dan dasar hukum wajib |
| **Amerika Serikat** | FAA JO 1000.37C (ATO SMS) | SRM wajib untuk perubahan NAS [S] | Paralel safety assessment |
| | FAA Roadmap AI Safety Assurance (2024) | Prinsip: gunakan proses sertifikasi yang ada, AI sebagai pendukung keselamatan [S] | Pendukung naratif |
| **Inggris** | Wireless Telegraphy Act 2006 s.48 | Mendengarkan transmisi non-broadcast tanpa otorisasi adalah pelanggaran; feed LiveATC dari Inggris tidak tersedia [S] | Contoh bahwa sumber audio harus dari ANSP; jangan berasumsi corpus publik bisa dipakai lintas negara |
| **Singapura** | CAAS bersama MITRE, Searidge, dan I2R | Riset AI ATM termasuk speech recognition [S] | Preseden regional; mitra potensial untuk ekspansi |
| **Riset Eropa** | SESAR HAAWAII | ASR/ASRU untuk callsign highlighting dan readback error detection; tool DLR mencapai TRL6 [S] | Bukti bahwa use case readback check sudah diteliti; FlowLens perlu diferensiasi |

## 5. Ke pihak mana harus mengurus — matriks pemangku kepentingan

Kolom dibedakan antara **izin/persetujuan** (diberikan pihak lain), **kepatuhan mandiri** (kita kerjakan dan dokumentasikan sendiri), dan **persetujuan pemilik data/kontrak**.

| Pihak | Peran | Izin/persetujuan | Kepatuhan mandiri | Kontrak/persetujuan data | Tier |
| --- | --- | --- | --- | --- | --- |
| **AirNav Indonesia (kantor pusat)**: Direktorat Operasi, Keselamatan/QA, Teknik/TI | Pemilik rekaman, penyelenggara ATS, calon pembeli, **pemohon** safety assessment | Persetujuan PoC; keputusan menjadikan FlowLens bagian SMS | — | Data sharing agreement (lingkup, tujuan, retensi, lokasi pemrosesan, larangan penilaian individu), NDA, kontrak pengendali–prosesor PDP | 2, 3 |
| **Ditjen Perhubungan Udara — Direktorat Navigasi Penerbangan (DNP)** | Regulator ATS/ANS (CASR 171/172) | Menerima/menilai safety assessment AirNav; kemungkinan sertifikasi fasilitas bila tersambung ke sistem ATS [V] | — | — | 3 (diajukan AirNav) |
| **BPSDM Perhubungan — PPI Curug / Poltekbang** | Lembaga diklat ATC, pemilik simulator | Izin penggunaan simulator dan kurikulum | Consent peserta | MoU riset, perjanjian data rekaman simulator | 1 |
| **Kementerian Komunikasi dan Digital (Komdigi)** | Registrasi PSE; pengampu UU PDP sampai Badan PDP terbentuk | **Pendaftaran PSE privat via OSS** | — | — | 1–3 |
| **Badan PDP (belum terbentuk)** | Pengawas PDP setelah Perpres terbit | — | DPIA, DPO, catatan pemrosesan, prosedur notifikasi 3×24 jam, dasar transfer lintas negara | — | 2, 3 |
| **BSSN** (+ IAS-CSIRT Kemenhub) | Keamanan siber, IIV | Tergantung penetapan IIV [V] | Standar keamanan, pelaporan insiden | — | 3 |
| **KNKT** | Investigasi kecelakaan/insiden | — | Aturan agar FlowLens tidak mengganggu atau membuka data investigasi | Prosedur bila rekaman terkait investigasi (freeze, tidak diekspor) | 2, 3 |
| **Asosiasi ATCO (IATCA) / serikat pekerja AirNav** | Pengguna dan pihak terdampak | Bukan izin formal, tetapi **penentu adopsi** | Komitmen just culture tertulis | Konsultasi desain dan uji pengguna | 2, 3 |
| **TNI AU / Kemhan** | ATC di bandara enclave sipil-militer; pemangku UU 21/2025 | Izin terpisah untuk bandara enclave | — | — | 2, 3 (bandara tertentu) |
| **InJourney Airports / UPBU Kemenhub** | Operator bandara; unit AMC (apron) | Hanya bila scope meluas ke apron/AMC | — | Akses data apron | Opsional |
| **Kemenperin** | Sertifikasi TKDN | Sertifikat TKDN | — | — | Pengadaan |
| **Google Cloud** | Prosesor STT/LLM | — | Konfigurasi region, logging off, terms | DPA/terms Vertex AI; dasar transfer ke Singapura | 2, 3 |

**Urutan yang disarankan:**

1. **Sekarang (Tier 1):** MoU dengan PPI Curug atau Poltekbang untuk pilot simulator; registrasi PSE; DPIA ringan; pindahkan pemrosesan ke Vertex AI regional.
2. **3–9 bulan (Tier 2):** pendekatan ke AirNav lewat jalur inovasi/riset (pola kerja sama Telkom University); tandatangani data sharing agreement dan kontrak prosesor; DPIA penuh sebelum 16 Januari 2027; libatkan IATCA sejak awal dengan komitmen purpose limitation.
3. **Jangka panjang (Tier 3):** AirNav menyusun safety assessment CASR 172.085 dengan masukan FlowLens dan berkoordinasi dengan DNP. Shadow mode dulu, tanpa output ke controller. Kemudian advisory dengan human-in-the-loop. Pantau EASA RMT.0742 dan Perpres AI untuk jalur assurance LLM.

## 6. Implikasi langsung ke produk dan arsitektur

1. **Provider profile per sumber** (sudah ada di PRD sebagai `SourcePermissionProfile`) perlu field: lokasi pemrosesan efektif (region Vertex), dasar transfer PP 33, pengendali vs prosesor, dan referensi DPIA.
2. **Jangan memakai Gemini Developer API atau global endpoint untuk data nyata.** Pakai Vertex AI `asia-southeast1` sebagai minimum. Siapkan adapter alternatif in-country/on-prem (ASR + LLM lokal) karena kemungkinan besar diminta AirNav untuk Tier 3.
3. **Sumber audio hanya dari voice recorder/VCCS AirNav melalui antarmuka resmi**, bukan dari penerima radio atau feed publik.
4. **Retensi mengikuti kebijakan rekaman AirNav** (minimal 30 hari ICAO, lebih lama bila terkait investigasi). Purge FlowLens harus mengikuti, termasuk backup (PRD §26, §33 sudah mendukung).
5. **Purpose limitation di produk:** tidak ada fitur skor individu controller; agregasi untuk QA; label "bukan catatan resmi" pada transcript (sudah ada di PRD §3.3).
6. **Bahan safety assessment:** hazard log (salah pasangan readback, automation bias, false negative), definisi degraded mode, dan bukti bahwa FlowLens tidak menerbitkan clearance. Ini menjadi lampiran yang dibutuhkan AirNav untuk CASR 172.085.
7. **Keamanan siber:** pemisahan jaringan (FlowLens tidak boleh menjadi jalur masuk ke jaringan ATS), audit log, dan prosedur insiden 3×24 jam.

## 7. Hal yang belum terverifikasi

- Mekanisme formal persetujuan DJPU atas safety assessment perubahan sistem ATS (aturan pelaksana yang dirujuk 172.085(f)).
- Apakah software analisis rekaman termasuk "fasilitas" yang wajib sertifikat CASR 171.
- Klasifikasi AirNav sebagai PSE lingkup publik atau privat, dan apakah sistem ATS AirNav sudah ditetapkan sebagai IIV.
- Retensi rekaman ATS yang ditetapkan Indonesia (aturan turunan atau MOS); angka 30 hari di dokumen ini berasal dari ICAO Annex 11.
- Region Google STT V2 untuk `chirp_3`; tabel data residency yang dibaca adalah tabel Vertex AI generative.
- Isi lengkap PP 33/2026 (ringkasan diambil dari sumber sekunder karena teks resmi tidak terbaca).
- Kebijakan resmi IATCA terkait penggunaan rekaman dan AI.
- Aturan bandara enclave TNI AU dan dampak PP pelaksana UU 21/2025.

## 8. Sumber

**Primer [P]**
- PM 43/2020 — CASR Part 172: [JDIH Kemenko Infra](https://jdih.kemenkoinfra.go.id/id/peraturan-menteri-perhubungan-no-43-tahun-2020) (PDF dibaca langsung: 172.075, 172.080, 172.085, 172.115).
- [Google Cloud — Vertex AI generative AI data residency](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency).
- [ICAO A42 working papers tentang AI](https://www.icao.int/sites/default/files/Meetings/a42/Documents/WP/wp_467_en.pdf).
- [EASA NPA 2025-07](https://www.easa.europa.eu/document-library/notices-of-proposed-amendment/npa-2025-07); [EASA ATM/ANS Equipment Attestation](https://easa.europa.eu/en/domains/air-traffic-management/atmans-equipment-attestation).
- [FAA Roadmap for AI Safety Assurance](https://www.faa.gov/aircraft/air_cert/step/roadmap_for_AI_safety_assurance); [FAA JO 1000.37C](https://www.faa.gov/documentLibrary/media/Order/JO_1000.37C_CHG1_ATO_Safety_Management_System_(COO).pdf).
- [UU 21/2025 Pengelolaan Ruang Udara](https://peraturan.go.id/id/uu-no-21-tahun-2025).
- [Setkab — Perpres 82/2022 IIV](https://setkab.go.id/presiden-terbitkan-perpres-82-2022-tentang-pelindungan-infrastruktur-informasi-vital/).

**Sekunder [S]**
- PP 33/2026: [Veritask](https://veritask.ai/id/artikel/pengaturan-teknis-pelindungan-data-pribadi-dan-kewajiban-pengendali-serta-prosesor-akhirnya-terbit-lewat-pp-33-2026), [FWP](https://fwp.co.id/pp-33-tahun-2026-pelindungan-data-pribadi/), [Kres](https://www.kres.id/pp-33-2026-aturan-pelaksana-uu-pdp).
- Badan PDP: [Kompas 27 Jul 2026](https://nasional.kompas.com/read/2026/07/27/15423511/komdigi-ungkap-perpres-pembentukan-badan-perlindungan-data-pribadi-sedang), [CNBC Indonesia 16 Sep 2026](https://www.cnbcindonesia.com/tech/20260916115609-37-768328/lembaga-perlindungan-data-belum-ada-di-ri-padahal-aturannya-sudah-ada).
- Perpres AI: [Kompas.id](https://www.kompas.id/artikel/program-perpres-2026-ditetapkan-dua-rancangan-atur-etika-dan-peta-jalan-ai-nasional), [JDIH Komdigi](https://jdih.komdigi.go.id/berita/view/113).
- UU 1/2009 Pasal 359: [Bisnis.com](https://ekonomi.bisnis.com/read/20210115/98/1343627/isi-blackbox-sriwijaya-bukan-konsumsi-publik-ini-penyebabnya); [JDIH BPK](https://peraturan.bpk.go.id/Details/54656).
- UU 36/1999 Pasal 40: [Hukumonline](https://www.hukumonline.com/berita/a/pemerintah--uu-telekomunikasi-jamin-perlindungan-data-pribadi-lt5c37182e842cd).
- PP 71/2019 dan PSE: [Hukumonline](https://www.hukumonline.com/berita/a/mengenal-pokok-pokok-aturan-baru-pp-pste-lt5de653d86d627/?page=all), [Bisnis.com — penegakan PSE 2026](https://teknologi.bisnis.com/read/20260918/101/2005294/lion-air-hingga-kcic-diminta-segera-daftar-pse-paling-lambat-22-september).
- AirNav × Telkom University: [ANTARA](https://www.antaranews.com/berita/5778089/airnav-telkom-university-kembangkan-ai-untuk-keselamatan-penerbangan), [Telkom University](https://telkomuniversity.ac.id/en/kolaborasi-telkom-university-dan-airnav-indonesia-lahirkan-inovasi-ai-berdaulat-pada-ajang-satria-2026/).
- PP 77/2012 AirNav: [IDX Channel](https://www.idxchannel.com/economics/ingin-jadi-perusahaan-navigasi-penerbangan-bertaraf-global-ini-upaya-airnav/all).
- CASR 171 / KP 528/2015: [salinan peraturan](https://www.ukm.my/aaip/wp-content/uploads/2019/02/Peraturan%20Direktorat%20Jenderal/Peraturan%20Direktorat%20Jenderal%20Nomor%20KP%20528%20Tahun%202015.pdf).
- Keamanan siber penerbangan: [SWA — IAS-CSIRT](https://swa.co.id/read/378004/ias-csirt-guna-memproteksi-insiden-siber-di-sektor-penerbangan).
- TKDN: [Detik — aturan baru TKDN](https://finance.detik.com/industri/d-8107759/aturan-baru-tkdn-terbit), [Bisnis.com — TKDN 25%](https://ekonomi.bisnis.com/read/20250507/257/1875038/prabowo-revisi-aturan-tkdn-untuk-belanja-pemerintahbumn-jadi-minimal-25).
- EU AI Act Digital Omnibus: [Cooley](https://cdp.cooley.com/digital-ai-omnibus-delays-key-deadlines-introduces-new-rules/), [euaiact.com — aviation amendments](https://www.euaiact.com/digital-omnibus-ai/sectoral-amendments).
- Reg. 2017/373 ATS.OR.205: [EASA Easy Access Rules](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-atm-ans-regulation-eu?page=7).
- ICAO Annex 11 retensi rekaman: [TCAA](https://www.tcaa.go.tz/uploads/documents/en-1781313666-Recording%20of%20Voice%20Communication%20and%20Surveillance%20Data.pdf).
- UK WTA s.48: [legislation.gov.uk](https://www.legislation.gov.uk/id/ukpga/2006/36/section/48/5), [LiveATC FAQ](https://liveatc.net/faq).
- CAAS: [CAAS × MITRE](https://www.caas.gov.sg/who-we-are/newsroom/Detail/caas-and-mitre-expand-collaboration-to-explore-artificial-intelligence-in-air-traffic-management).
- SESAR HAAWAII: [SIDs 2023 paper](https://www.sesarju.eu/sites/default/files/documents/sid/2023/Papers/SIDs_2023_paper_6%20final.pdf).
- IFATCA: [WP98](https://ifatca.org/wp-content/uploads/WP98_AMD.pdf).
- PPI Curug: [Jurnal PPI Curug](https://journal.ppicurug.ac.id/index.php/jurnal-ilmiah-aviasi/article/view/438).
