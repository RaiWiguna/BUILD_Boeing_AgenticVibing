# Riset Kondisi Operasional ATC dan Kelayakan ATC FlowLens

**Tanggal pemeriksaan sumber:** 30 September 2026  
**Cakupan:** seluruh dokumen di folder docs dan sumber publik; source code proyek tidak diaudit  
**Status produk untuk laporan ini:** konsep dan MVP simulasi, sesuai asumsi dalam brief. Tidak ada klaim bahwa FlowLens telah dipakai, diuji, disertifikasi, atau terhubung ke operasi ATC nyata.

## Cara membaca dan batas riset

Temuan membedakan bukti untuk Indonesia, contoh implementasi negara lain, dan rancangan FlowLens. Status teknologi dibedakan antara **terbukti operasional di lokasi tertentu**, **tersedia sebagai standar/produk**, **program atau pilot**, **tidak dapat dibuktikan dari sumber publik**, dan **tidak relevan untuk scope FlowLens**. Adanya teknologi di satu fasilitas tidak membuktikan pemasangan, penggunaan aktif, cakupan, atau akses data di fasilitas lain.

Label kepastian pada klaim penting:

- **[FAKTA]** sumber tertaut mendukung klaim dalam lingkup yang disebutkan.
- **[INFERENSI]** penilaian analitis dari fakta yang ditautkan.
- **[ASUMSI]** parameter atau kondisi yang belum dibuktikan.
- **[SIMULASI]** hanya berlaku pada skenario atau data FlowLens.
- **[BELUM TERVERIFIKASI]** bukti publik yang memadai tidak ditemukan.
- **[KONTRADIKSI]** materi berbeda memberi gambaran atau status yang tidak sama.

Laporan ini bukan audit akses jaringan, source code, SOP lokal yang tidak dipublikasikan, kontrak vendor, atau wawancara petugas. Ketiadaan bukti publik tidak berarti teknologinya tidak ada. Untuk kondisi spesifik bandara, langkah akhir tetap perlu konfirmasi langsung dari regulator, AirNav, pengelola bandara, operator, dan pemilik sistem/data terkait.

## 1. Executive summary

1. **[FAKTA]** Ekosistem Indonesia telah memakai teknologi digital dan surveillance yang nyata. Laporan Tahunan Ditjen Perhubungan Udara 2024 menyebut 50 unit peralatan ADS-B untuk pelayanan surveillance, area ATS surveillance separation, dan penggunaan ADS-B sebagai position reporting pada sejumlah sektor dan tower. Laporan yang sama mencatat dua fasilitas Air Traffic Situational Awareness (ATSA) di Budiarto dan Sultan Hasanuddin, mencakup radar/MSSR dan ADS-B untuk area terminal, ATM, komunikasi VHF, rekaman suara dan air situation display, cuaca aerodrome, serta simulator ATC. Ini bukti khusus terhadap layanan dan fasilitas yang disebut, bukan inventaris seluruh permukaan bandara Indonesia. [Laporan Tahunan DJPU 2024](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf)
2. **[FAKTA]** Pada 11 September 2026 AirNav memaparkan New ATMAS di New JATSC, dengan surveillance radar dan ADS-B, CPDLC/ADS-C, safety net STCA/APW/APM, AIM dan ATFM, serta AMHS dan pengembangan AIDC. Bukti ini berlaku untuk kapabilitas sistem yang diumumkan dalam konteks JATSC. Sumber tidak memetakan deployment, cakupan, status commissioning tiap fungsi, atau akses feed ke pihak ketiga di seluruh bandara. [AirNav Indonesia, New JATSC/New ATMAS](https://www.airnavindonesia.co.id/berita-dan-siaran-pers/kunjungi-airnavindonesia-presiden-icao-tinjau-langsung-fasilitas-new-jatsc/)
3. **[FAKTA]** Contoh global memperlihatkan lapisan surface safety yang lebih lengkap pada lokasi tertentu. FAA menyebut ASDE-X di 35 bandara dan ASSC di 9 lokasi operasional pada halaman ASSC; RWSL beroperasi di 20 bandara AS. FAA juga sedang memasang atau merencanakan Surface Awareness Initiative di hingga 220 bandara bertower FAA sampai 2028. Angka SAI adalah target instalasi, bukan 220 sistem yang seluruhnya sudah aktif. [FAA ASSC](https://www.faa.gov/air_traffic/technology/adsb/atc/assc), [FAA RWSL](https://www.faa.gov/air_traffic/technology/rwsl/index.cfm?print=go), [FAA VMAT/SAI](https://www.faa.gov/airports/runway_safety/airfield_drivers/enhancing-surface-safety-guide-vehicle-movement-area)
4. **[FAKTA]** Keberadaan data tidak sama dengan hak akses. Track surveillance, flight plan, clearance/strip, rekaman radio, event alert, dan posisi kendaraan umumnya berada di sistem pengelola layanan navigasi atau operator bandara. Dokumen publik tidak memberikan feed operasional Indonesia yang dapat langsung diambil FlowLens. Perlu kesepakatan, otorisasi, pemeriksaan keamanan dan privasi, interface yang disetujui, serta aturan retensi dan penggunaan. Contoh FAA SWIM menunjukkan akses data bisa diberikan kepada pelanggan yang terdaftar, sedangkan OpenSky membatasi penggunaan komersial maupun integrasi operasional tanpa izin tertulis. [FAA SWIM access](https://www.faa.gov/air_traffic/technology/swim/products/get_connected), [OpenSky Terms](https://opensky-network.org/about/terms-of-use)
5. **[FAKTA]** ATC tetap memakai komunikasi suara untuk fungsi yang belum tersedia atau tidak cocok untuk datalink; CPDLC adalah saluran pelengkap pada operasi tertentu. Pembacaan dan konfirmasi readback clearance runway merupakan kontrol manusia/prosedur penting. ICAO menyatakan controller harus mendengarkan readback dan memperbaiki perbedaan. Transcript otomatis tidak boleh menjadi sumber clearance otoritatif tanpa konfirmasi petugas. [ICAO Doc 9870](https://www.icao.int/safety/RunwaySafety/Documents/ICAO_manual_prev_RI.pdf), [EUROCONTROL CPDLC di Maastricht UAC](https://www.eurocontrol.int/service/controller-pilot-datalink-communications-our-maastricht-uac)
6. **[FAKTA]** Laporan KNKT atas runway incursion Adisutjipto pada 20 November 2013 mengidentifikasi taxi clearance yang disalahpahami, transfer control/communication, dan koordinasi Tower–Approach sebagai isu keselamatan pada kejadian itu. Ini contoh Indonesia yang kuat untuk desain skenario dan pertanyaan riset, tetapi tidak mengukur frekuensi masalah saat ini atau membuktikan workflow semua bandara. [KNKT, Runway Incursion Adisutjipto](https://knkt.go.id/Repo/Files/Laporan/Penerbangan/2013/PK-AXG%20%26%20PK-LBH%20Final%20Report.pdf)
7. **[INFERENSI]** Posisi FlowLens paling realistis untuk hackathon dan adopsi awal adalah **simulator training serta replay/debrief berbasis skenario**, memakai data sintetik dan aturan deterministik. Langkah berikutnya dapat berupa riset dengan instruktur ATC. Dashboard awareness non-safety-critical atau analitik berbasis data mitra dapat dipertimbangkan sesudah ada kesepakatan data dan validasi pengguna. Integrasi real-time ke posisi controller adalah jalur jangka panjang yang belum dapat dibenarkan oleh bukti yang tersedia.
8. **[SIMULASI]** Contoh BAW123/ARFF-2, RWY 27, touchdown 42 detik, kendaraan clear 58 detik, dan overlap 16 detik berasal dari dokumen internal FlowLens. Angka tersebut bukan data pesawat, airport, clearance, atau hasil sensor nyata. Tampilan ilustrasi yang menamai situasi “high risk” juga bukan threshold yang telah dikalibrasi.
9. **[BELUM TERVERIFIKASI]** Bukti publik yang memadai belum ditemukan untuk inventaris nasional yang menyatakan bandara mana di Indonesia memakai surface movement radar/A-SMGCS/RIMCAS, transponder kendaraan, electronic flight strips, RWSL, remote/digital tower, atau AI speech-to-text ATC operasional. Maka tingkat kematangan permukaan tidak diberi skor nasional atau per kelas bandara hanya berdasarkan ukuran atau status internasional.

### Positioning aman

> **ATC FlowLens adalah simulator dan alat replay yang dapat menjelaskan hubungan gerak, instruksi, serta waktu pada skenario runway; sistem ini membantu latihan dan review, tidak mengeluarkan clearance, tidak menggantikan controller, dan belum divalidasi untuk operasi ATC nyata.**

## 2. Kondisi nyata ekosistem ATC/ATM dan bandara

### Indonesia

- **[FAKTA]** Ditjen Perhubungan Udara menetapkan aturan dan pengawasan keselamatan penerbangan; AirNav Indonesia bertindak sebagai penyelenggara layanan navigasi penerbangan pada wilayah/layanan yang dikelolanya; operator bandara mengelola aerodrome, fasilitas dan kondisi movement area; BMKG menyediakan informasi meteorologi penerbangan; airline/operator mengelola operasi pesawat; KNKT menginvestigasi kecelakaan dan kejadian serius untuk keselamatan. Koordinasi dan perjanjian antarunit penting karena data dan tanggung jawab dapat melintasi badan-badan tersebut. [Ditjen Hubud: CASR Part 170](https://jdih.dephub.go.id/peraturan/detail?data=3IMxkCe8aHLI1JCFrczIFY8cNscTorqfV4Dx4eRjLnqG4vQiLcKBjTM4JJhaePerlh4q9FBY8eNFc4koCXYvVDl58m5frhWQ9lU4ua5QCBaZlr9iiYnEv5bD5BWItzCydyxPALl0UxLo1cOHg05gV6Qnlp), [KNKT Subkomite Penerbangan](https://www.knkt.go.id/subkomite/penerbangan)
- **[FAKTA]** Bukti pemerintah untuk ADS-B menggambarkan penggunaan pada sektor/area surveillance dan position-reporting tertentu; laporan tahunan 2024 menyebut 50 unit fasilitas ADS-B dan mencantumkan area seperti Jakarta, Bali, Surabaya, Ujung Pandang, serta beberapa CTR/TMA. Layanan tower yang disebut antara lain Ngurah Rai, Soekarno-Hatta, Juanda, Sultan Hasanuddin, Pontianak, Palembang, Pekanbaru dan Tanjungpinang. Daftar tersebut bukan bukti bahwa seluruh pesawat dan kendaraan di permukaan bandara menghasilkan track yang bisa diakses aplikasi luar. [Laporan Tahunan DJPU 2024, bagian surveillance/ADS-B](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf)
- **[FAKTA]** ATSA yang dilaporkan DJPU adalah dua fasilitas cadangan/backup yang dapat digunakan dalam keadaan darurat; fasilitas mencakup surveillance pesawat ke TMA, komunikasi dan display/voice recording, cuaca aerodrome, serta simulator. Jangan menyamakannya dengan deployment surveillance runway kendaraan secara nasional. [Laporan Tahunan DJPU 2024](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf)
- **[FAKTA]** Sistem AIM Indonesia menampilkan update AIP/NOTAM, tetapi halaman yang diperiksa meminta login untuk akses lebih lanjut. Halaman mencantumkan AIP Amendment tahun 2026, sehingga aeronautical information bersifat dinamis dan harus dibaca menurut tanggal publikasi serta tanggal efektif. API publik, syarat redistribusi, bulk download, dan hak penggunaan komersial tidak terverifikasi dari landing page. [AIM Indonesia](https://aimindonesia.kemenhub.go.id/login)
- **[FAKTA]** BMKG memublikasikan produk meteorologi penerbangan termasuk METAR/SPECI, TAF, SIGMET dan informasi cuaca bandara pada layanan web. Daftar informasi publik BMKG mengidentifikasi METAR sebagai pengamatan rutin dengan interval 30 menit–1 jam dan TAF dengan siklus 6 jam/perubahan; peringatan khusus dikeluarkan saat diperlukan. Halaman BMKG meminta pengguna memeriksa timestamp dan validity serta mengingatkan produk bisa berubah, tidak lengkap atau tidak terkini. Tampilan web bukan bukti API berjaminan latensi atau feed operasional. [Daftar Informasi Publik BMKG](https://ppid.bmkg.go.id/daftar-informasi-publik), [Sistem Informasi Meteorologi Penerbangan BMKG](https://web-aviation.bmkg.go.id/)
- **[FAKTA]** AirNav menyebut sistem New ATMAS di New JATSC memakai radar/ADS-B, CPDLC/ADS-C, safety net STCA/APW/APM, serta terhubung dengan AIM/ATFM dan AMHS/AIDC. AirNav juga menyebut Cengkareng, Medan, Pontianak dan Balikpapan, lalu Sabang, Denpasar dan Yogyakarta sebagai urutan pengembangan/modernisasi berikutnya; itu rencana bertahap, bukan bukti bahwa lokasi tersebut sudah menerima fungsi New ATMAS. [AirNav Indonesia, New JATSC/New ATMAS](https://www.airnavindonesia.co.id/berita-dan-siaran-pers/kunjungi-airnavindonesia-presiden-icao-tinjau-langsung-fasilitas-new-jatsc/)

### Praktik kerja dan batas informasi publik

**[FAKTA]** Pekerjaan controller menggabungkan observasi keadaan trafik, instruksi/clearance, radio, koordinasi, prosedur, display dan penilaian manusia. Prosedur runway menuntut komunikasi loop tertutup untuk clearance keselamatan: pilot/operator menyampaikan readback; controller memeriksa dan mengoreksi jika ada perbedaan. Detail alokasi tugas, fraseologi lokal, unit yang mengendalikan tiap titik taxi/runway, dan fallback ketika alat gagal mengikuti aturan serta SOP yang berlaku di unit setempat, sehingga tidak digeneralisasi dari manual FAA atau kasus satu bandara. [ICAO Doc 9870](https://www.icao.int/safety/RunwaySafety/Documents/ICAO_manual_prev_RI.pdf), [CASR Part 170 Indonesia](https://jdih.dephub.go.id/peraturan/detail?data=3IMxkCe8aHLI1JCFrczIFY8cNscTorqfV4Dx4eRjLnqG4vQiLcKBjTM4JJhaePerlh4q9FBY8eNFc4koCXYvVDl58m5frhWQ9lU4ua5QCBaZlr9iiYnEv5bD5BWItzCydyxPALl0UxLo1cOHg05gV6Qnlp)

**[FAKTA]** Runway incursion Adisutjipto tahun 2013 memperlihatkan bagaimana clearance taxi yang ambigu/disalahpahami, kontrol dan komunikasi APP–Tower, perkiraan terhadap posisi pesawat lain, serta respons go-around muncul pada satu urutan kejadian. Laporan KNKT mencatat pesawat taxi melampaui holding position dan masuk sekitar 16 meter ke runway, sedangkan pesawat landing berhenti setelah pengereman sekitar 100 meter dari pesawat tersebut. Angka dan kronologi ini khusus untuk laporan tersebut; jangan dipakai sebagai tingkat kejadian kini atau ukuran performa sistem. [KNKT final report](https://knkt.go.id/Repo/Files/Laporan/Penerbangan/2013/PK-AXG%20%26%20PK-LBH%20Final%20Report.pdf)

**[INFERENSI]** Alur informasi yang relevan untuk FlowLens kemungkinan melibatkan setidaknya ANSP/controller, pilot, airport operations, ARFF atau pengemudi kendaraan, pemilik flight plan, unit cuaca, dan pemegang data surveillance. Tanpa akses observasi atau SOP mitra, peta ini adalah hipotesis riset, bukan peta implementasi bandara tertentu.

**[BELUM TERVERIFIKASI]** Tidak ditemukan sumber publik yang cukup untuk menyatakan berapa banyak bandara Indonesia masih memakai strip kertas, seluruhnya telah memakai strip elektronik, berapa lama rekaman ATS disimpan, siapa yang dapat mengaksesnya, sistem perekam/format apa yang dipakai di setiap unit, atau apakah ada transkrip otomatis resmi.

## 3. Audit klaim dan asumsi dari dokumen internal

### Inventaris artefak yang dibaca

| Kelompok | Dokumen |
|---|---|
| Riset ATC | [atc-atm-master-research-and-solution.md](../General-Information/atc-atm-master-research-and-solution.md); [atc-atm-workflow-communication-visualization.md](../General-Information/atc-atm-workflow-communication-visualization.md); [atc-technology-visualization.md](../General-Information/atc-technology-visualization.md); [atc-workload-research.md](../General-Information/atc-workload-research.md); [boeing-build-aerospace-defense-research.md](../General-Information/boeing-build-aerospace-defense-research.md). |
| Knowledge review | [ATC_FlowLens_Knowledge_Review.md](ATC_FlowLens_Knowledge_Review.md) dan [PDF](ATC_FlowLens_Knowledge_Review.pdf); [ATC_FlowLens_Rancangan_Slide_MVP.md](ATC_FlowLens_Rancangan_Slide_MVP.md); [ATC_FlowLens_Rencana_Teknis_MVP.md](ATC_FlowLens_Rencana_Teknis_MVP.md) dan [PDF](ATC_FlowLens_Rencana_Teknis_MVP.pdf). |
| Proposal dan deck | Proposal/draft Markdown: [atc-flowlens-general-proposal.md](../Proposal/atc-flowlens-general-proposal.md), [proposal-umum-atc-flowlens-id.md](../Proposal/proposal-umum-atc-flowlens-id.md), [draft_PitchDeck_EN.md](../Proposal/draft_PitchDeck_EN.md), [draft_PitchDeck_ID.md](../Proposal/draft_PitchDeck_ID.md). Tiga HTML deck: [BUILD final](../Proposal/BUILD_TeamAgenticVibing_AdvancedTechnologyAndInnovation.html), [CommandDesign](../Proposal/ATC_FlowLens_PitchDeck_CommandDesign.html), [Detailed pre-mission-control](../Proposal/ATC_FlowLens_PitchDeck_Detailed.before-mission-control.html). Empat PDF deck: [Agentic Vibing](../Proposal/ATC_FlowLens_PitchDeck_Agentic_Vibing.pdf), [CommandDesign](../Proposal/ATC_FlowLens_PitchDeck_CommandDesign.pdf), [Detailed pre-mission-control](../Proposal/ATC_FlowLens_PitchDeck_Detailed.before-mission-control.pdf), [BUILD final](../Proposal/BUILD_TeamAgenticVibing_AdvancedTechnologyAndInnovation.pdf). Dua PPTX: [Agentic Vibing](../Proposal/ATC_FlowLens_PitchDeck_Agentic_Vibing.pptx), [CommandDesign](../Proposal/ATC_FlowLens_PitchDeck_CommandDesign.pptx). Draft, final dan variasi visual dibaca silang sebagai versi/narasi, bukan bukti independen. |
| Aset visual | [slide1_image_generation_prompt.md](../Proposal/assets/slide1_image_generation_prompt.md), [slide1_runway_asset.html](../Proposal/assets/slide1_runway_asset.html), [slide1_runway_asset.png](../Proposal/assets/slide1_runway_asset.png), [slide1_runway_conflict_reference.png](../Proposal/assets/slide1_runway_conflict_reference.png). PNG menampilkan skenario runway konseptual dan pesan “high risk”; bukan diagram aerodrome, sensor display, atau hasil risk assessment operasional. |

Semua dokumen Markdown/HTML diekstrak dan dibaca untuk klaim FlowLens; teks PDF dan slide yang dapat diekstrak diperiksa. PPTX CommandDesign tidak menyediakan teks slide yang terbaca dari struktur presentasinya; isinya diperiksa melalui HTML/PDF padanannya. Materi aerospace/defense tentang SAF, supply chain, robotika atau drone tidak dipakai sebagai bukti kondisi ATC.

### Matriks audit

| ID | Klaim | Sumber internal | Status | Masalah | Bukti yang dibutuhkan | Rekomendasi |
|---|---|---|---|---|---|---|
| I-01 | Controller workload tinggi karena trafik, radio, cuaca, runway, staffing dan banyak layar. | [Riset workload](../General-Information/atc-workload-research.md); [master research](../General-Information/atc-atm-master-research-and-solution.md) | [FAKTA] workload merupakan isu human factors; [INFERENSI] daftar faktor adalah kerangka umum | Faktor berbeda per posisi, traffic sample, fasilitas dan prosedur; tidak semua berlaku di setiap kejadian. | Observasi tugas, interview controller, data sektoral yang sah dan instrumen workload. | Ubah ke “faktor yang perlu diuji”, jangan klaim sebab lokal tanpa studi. |
| I-02 | Komunikasi suara dominan dan komunikasi operasional direkam di fasilitas ATC. | [Workflow/communication](../General-Information/atc-atm-workflow-communication-visualization.md) | [FAKTA] suara masih saluran penting; [BELUM TERVERIFIKASI] cakupan rekaman nasional | Bukti recording ada untuk ATSA tertentu, tetapi bukan inventaris semua unit/retensi. Datalink berlaku untuk fungsi/lokasi/equipage tertentu. | SOP dan inventory per ANSP/unit; retention, format, akses, izin penggunaan. | Ganti “umumnya direkam” dengan pernyataan lokasi/layanan yang memang didukung. |
| I-03 | Data operasional tersebar sehingga controller perlu menyusun gambaran sendiri. | Proposal, riset, draft pitch | [INFERENSI] | Bisa menjadi narasi yang terlalu luas atau menggambarkan display lokal secara salah. | Observasi kerja dan interface map di unit sasaran. | Sebut “hipotesis gap integrasi yang perlu diuji” hingga divalidasi. |
| I-04 | Radar, ADS-B, MLAT, A-SMGCS, ASDE-X/ASSC, RIMCAS, RWSL, STCA, MTCD, e-strip, SWIM dan lainnya adalah teknologi “yang ada sekarang”. | Riset teknologi; proposal | [FAKTA] teknologi ada pada industri; [BELUM TERVERIFIKASI] deployment domestik setiap item | Mencampur sensor, automation, alert, data exchange, konsep operasi dan fitur yang hanya terbukti di negara tertentu. | Register deployment resmi per negara, ANSP dan bandara, status operasional serta tanggal. | Di matriks baru pisahkan fungsi, pengguna, lokasi bukti, maturity dan akses data. |
| I-05 | FlowLens memiliki konteks gabungan aircraft, vehicle, runway, clearance, cuaca dan workload. | Proposal; knowledge review | [SIMULASI]/[ASUMSI] | Itu daftar input/roadmap, bukan feed tersedia atau integrasi. | Dataset, interface agreement, timestamp, provenance dan uji kualitas. | Tandai setiap feed sebagai sintetik, publik, atau mitra. |
| I-06 | BAW123 touchdown 42 detik; ARFF-2 clear 58 detik; overlap 16 detik. | Knowledge Review, deck, gambar | [SIMULASI] | Angka berasal dari skenario pitch; tidak mengandung distribusi error/ketidakpastian yang dibuktikan. | Skenario reproducible, ground truth, model kinematik, asumsi, toleransi dan uji dengan trainer. | Selalu beri label “contoh simulasi”; jangan tampilkan sebagai hasil sensor atau prediksi nyata. |
| I-07 | Clearance state engine dan alert level mengidentifikasi konflik serta menyatakan risiko high/critical. | Rencana teknis MVP; asset HTML/PNG | [SIMULASI]/[ASUMSI] | Urutan clearance dan severity ditentukan model; time overlap sendiri bukan risk probability atau aturan clearance operasional. | Hazard analysis, clearance logic disetujui ahli, uncertainty model, sensitivity/false-alert study. | Jelaskan “indikasi overlap pada skenario”; hilangkan kata “high risk” kecuali threshold divalidasi dan maknanya jelas. |
| I-08 | Workload indicator memperlihatkan workload controller. | Master research, workflow, tech visualization, proposal, rencana MVP | [ASUMSI] | Traffic count, weather dan event count bukan pembacaan mental workload; istilah berisiko memberi kesan diagnosis/penilaian operator. | Studi dengan controller; task analysis; validasi instrumen subjektif/observasional dan desain lokal. | Sebut “indikator kompleksitas tugas skenario”; jangan menyebut skor mental workload atau fatigue. |
| I-09 | Voice AI dapat melakukan speech-to-text, callsign/clearance parsing, readback mismatch. | Riset, roadmap dan pitch awal | [BELUM TERVERIFIKASI] untuk bahasa, frekuensi dan phraseology Indonesia; [FAKTA] riset ASR ATC ada | Data training Inggris/global tidak membuktikan kinerja di radio Indonesia, noise, call sign, campur bahasa, overlap atau unit sasaran. | Audio legal/berizin dan berlabel, test split Indonesia, WER/entity/critical error metrics, human review. | Tunda live use; batasi eksperimen offline/replay dengan data berlisensi/sintetik dan anotator domain. |
| I-10 | FlowLens mengurangi workload, menemukan konflik lebih cepat, mengurangi incident, go-around, delay atau fuel burn. | Pitch, proposal, master research | [BELUM TERVERIFIKASI] | Outcome disampaikan sebagai dampak meski belum ada pilot, baseline atau studi. | Studi komparatif, sample/power, task-specific metrics, baseline yang sah dan evaluasi independen. | Ganti menjadi hipotesis manfaat/target penelitian, bukan hasil atau janji produk. |
| I-11 | Sistem konvensional kurang menjelaskan sebab alert dan FlowLens mengisi gap yang belum dilayani. | Knowledge Review; pitch | [INFERENSI]/[BELUM TERVERIFIKASI] | A-SMGCS/RMCA memiliki alert, track/flight plan dan fungsi penjelasan yang dapat bergantung implementasi; belum dibandingkan di unit tertentu. | Uji interface dan workflow incumbent di lokasi calon pengguna. | Posisi pembeda pada replay/training dan provenance yang dapat ditelusuri; hindari “belum ada sistem”. |
| I-12 | Semua daftar persona adalah pembeli/pengguna FlowLens. | Proposal, pitch | [ASUMSI] | Controller, trainer, airport operations, ARFF, safety office dan investigator punya tugas serta izin data berbeda. | Interview terpisah, workflow ownership, willingness-to-use dan procurement discovery. | Prioritaskan trainer/peserta untuk tahap awal; validasi aktor lain sebelum perluas produk. |
| I-13 | Roadmap dari hackathon ke airport operation dan integrasi operasional adalah jalur adopsi yang feasible. | Knowledge Review, rencana MVP, deck | [INFERENSI] | Fase produk bukan persetujuan organisasi, regulator, data owner atau deployment. | Sponsor, use-case owner, hazard analysis, security review, data access dan acceptance criteria. | Posisikan sebagai pilihan bersyarat, bukan komitmen waktu/hasil. |
| I-14 | Perangkat remote/digital tower dan AI sudah relevan sebagai tech landscape FlowLens. | Riset ATC dan workload | [FAKTA] teknologi dikembangkan/dioperasikan pada negara tertentu; [BELUM TERVERIFIKASI] Indonesia | Kehadiran remote tower tidak memberi akses data permukaan, dan visual system sendiri perlu validasi/approval. | Bukti otoritas/ANSP lokal dan fungsi sistem terkait. | Cantumkan sebagai benchmark/roadmap lingkungan, bukan integration target MVP. |
| I-15 | Pitch “prototipe demonstrasi” atau “MVP” berarti aplikasi ATC runtime nyata. | Knowledge Review 14 Agustus 2026 dan rencana MVP 15 September 2026 | [KONTRADIKSI] antar-istilah; dokumen rencana menyatakan spec, bukan hasil implementasi | “MVP”, wireframe, scenario, acceptance target, HTML deck dan angka benchmark dapat terbaca seperti kemampuan tersedia. | Bukti demonstrasi yang dapat dijalankan dan catatan build terpisah; audit source code di luar cakupan laporan ini. | Untuk dokumen/pitch, tulis status eksplisit per artefak: konsep, desain, simulasi, atau hasil uji. |
| I-16 | Kasus LaGuardia 2026 membuktikan FlowLens akan mencegah collision. | Riset workload/master/technology; pitch deck | [KONTRADIKSI] implikasi kausal, bukan fakta kasus | Per 30 September 2026 NTSB masih menyatakan investigation ongoing; temuan awal dapat berubah. | Final report dan evaluasi kontrafaktual produk yang tidak bersandar pada hindsight. | Gunakan hanya sebagai konteks keselamatan dengan status preliminary; jangan klaim pencegahan. |
| I-17 | Insiden Austin menunjukkan perlunya awareness, low-visibility training dan surface surveillance. | Riset workload/knowledge review | [FAKTA] untuk temuan NTSB atas kasus; [INFERENSI] untuk kebutuhan FlowLens | Insiden melibatkan dua pesawat dan ATC; bukan bukti efektivitas suatu tool tertentu. | Rujuk final report dan recommendations; validasi lokal sebelum transfer. | Kaitkan ke desain skenario latihan saja, bukan estimasi dampak FlowLens. |
| I-18 | Sustainability: lebih sedikit go-around/holding/delay otomatis menghemat fuel. | Master research, proposal | [BELUM TERVERIFIKASI] | Rantai kausal, baseline, model bahan bakar, operasi dan dampak FlowLens tidak tersedia. | Data operasi maskapai/bandara, counterfactual, metodologi emisi, izin. | Tunda atau label sebagai manfaat jangka panjang yang belum diukur. |
| I-19 | Kematangan teknologi dapat dinilai sebagai Level 0–4 per tipe bandara. | Rencana/materi maturity visualization | [ASUMSI] kerangka analisis internal | Level bukan standar ICAO; ukuran bandara bukan pengganti bukti equipage, integrasi dan penggunaan aktif. | Inventaris dan status per fasilitas. | Gunakan framework hanya dengan kriteria eksplisit; pakai “tidak dapat dinilai dari sumber publik” bila bukti kurang. |
| I-20 | Materi pitch/visual memperlihatkan operational map/runway risk. | Asset prompt, PNG dan deck HTML/PDF/PPTX | [SIMULASI] | Ilustrasi bukan chart resmi, plot posisi, sensor accuracy, live system, atau threshold risiko. | Referensi AIP yang diizinkan serta validasi geometri/data bila kelak dipakai di simulator. | Label visual “concept art / simulated scenario”; jangan menyajikannya sebagai layar bandara. |

## 4. Peta aktor, keputusan, sistem dan data

| Aktor/unit | Tanggung jawab umum | Keputusan/aktivitas terkait FlowLens | Sistem/data yang kemungkinan dipakai/dibutuhkan | Koordinasi dan batas yang perlu diuji |
|---|---|---|---|---|
| Regulator / Ditjen Hubud | Aturan, sertifikasi/persetujuan dan pengawasan keselamatan penerbangan/navigasi | Menentukan kerangka keselamatan serta apakah fungsi baru memerlukan persetujuan | CASR, sertifikat, laporan audit, persetujuan fasilitas | Applicability FlowLens harus diklarifikasi dengan otoritas; laporan ini tidak menentukan klasifikasi produk. |
| AirNav / ANSP | Menyelenggarakan ATS/ATM, unit, komunikasi dan surveillance pada cakupan layanan | Separation, instruksi, handoff, keselamatan operasi, pengelolaan data ATS | Radar/ADS-B, ATM automation, VHF, CPDLC/AIDC, flight plan, strip/recording sesuai fasilitas | Pemberi keputusan operasional dan gatekeeper utama untuk feed ATC; lokasi dan hak integrasi spesifik belum tersedia publik. |
| Area control / ACC | Mengelola layanan en-route sesuai ruang udara/prosedur | Clearance/separation, koordinasi dan sequencing trafik en-route | Surveillance, flight data, voice/data link, traffic management | Data dan urutan service berbeda dari tower runway; bukan target pertama FlowLens. |
| Approach / APP | Mengelola terminal sequencing/handoff ke aerodrome control sesuai SOP | Arrival sequence, approach clearance/coordination, transfer komunikasi/control | Radar/MSSR/ADS-B, flight data, voice/data link, cuaca | Handoff dan responsibility points harus dipetakan menurut LOA/SOP setempat; contoh KNKT menunjukkan interface ini dapat kritis. |
| Tower / aerodrome control | Memberi ATS pada aerodrome sesuai unit/prosedur | Landing, departure, runway use, koordinasi crossing/hold | ATC display, radio, flight data, observasi visual; surface surveillance bila disediakan | Keputusan keselamatan tetap pada controller; display tambahan tidak otomatis berwenang memberi clearance. |
| Ground controller / surface movement | Mengatur ground movements sesuai fungsi di bandara | Taxi, route, hold, crossing dan koordinasi | Voice, strip/automation, airport layout, surface track bila tersedia | Tidak semua fasilitas membagi posisi/otoritas dengan cara sama; validasi lokal wajib. |
| Airport operator / operations center | Kondisi aerodrome, akses movement area, inspeksi, works-in-progress, gangguan | Mengelola status permukaan/fasilitas dan koordinasi aktivitas airport | AODB/ops logs, NOTAM process, radios, vehicle/maintenance system | Data status runway tidak identik dengan clearance ATC; akses feed harus disepakati dengan operator dan ANSP. |
| Airline/operator pesawat | Kesiapan dan dispatch penerbangan, operasi penerbangan dan dukungan crew | Flight plan, dispatch, performance, taxi/departure coordination, flight deck response | Airline operations system, flight plan, onboard avionics/FMS, ACARS/datalink sesuai equipage | AOC/dispatch data bersifat komersial dan bukan data publik FlowLens. |
| Pilot/flight crew | Mengoperasikan pesawat dan mematuhi clearances/prosedur | Membaca clearance, melakukan readback, taxi/landing/take-off, melaporkan situasi | Radio VHF, charts/AIP/NOTAM, avionics, transponder/ADS-B sesuai airspace/equipage | Track pesawat yang terlihat tidak menunjukkan niat/clearance dengan sendirinya. |
| Dispatcher / flight operations officer | Mendukung perencanaan dan pemantauan penerbangan sesuai operator | Flight planning, weather/NOTAM, route, monitoring dan coordination | Flight planning, weather, NOTAM/AIP, airline movement data | Bukan pengambil clearance runway; kebutuhan data bergantung maskapai. |
| Ground handling / pushback | Menangani aircraft turnaround dan ground services | Pushback, marshalling, koordinasi ground movement | Radio/dispatch perusahaan, movement permits/airport procedure | Detail izin/route lokal harus ditentukan operator; jangan masukkan sebagai aktor yang otomatis terpantau. |
| ARFF/PKP-PK | Siaga dan merespons kondisi darurat sesuai airport emergency plan | Dispatch kendaraan, staging, akses movement area/runway sesuai otorisasi | Radio, dispatch log, AVL/GPS bila ada, emergency plan | Pergerakan darurat memiliki koordinasi spesifik dan prioritas tersendiri; exact SOP tidak diasumsikan. |
| Inspection/maintenance vehicle | Melaksanakan inspeksi runway, lighting, pavement, wildlife atau maintenance | Request/otorisasi untuk masuk ke movement area, rute/batas, melaporkan status | Vehicle radio, work order, airport ops/maintenance record, AVL/transponder bila ada | Kendaraan tidak boleh diasumsikan transponder-equipped atau masuk feed surveillance. |
| BMKG / meteorological unit | Mengamati dan menyebarkan weather aerodrome/route sesuai tugas | METAR/SPECI, TAF, windshear/aerodrome warning, visibility/weather context | AWOS/sensor, weather station, products and bulletins | METAR/TAF bukan observasi posisi runway real-time; timestamp/validity harus dipertahankan. |
| Airport IT / CNS / vendor | Mengelola jaringan, sistem, fasilitas CNS, support dan vendor interface sesuai kontrak | Konektivitas, maintenance, cybersecurity, integrasi dan akses teknis | ATM network, sensor networks, identity/access management, logs | Vendor bukan pemilik keputusan ATS; arsitektur/interface bisa proprietary dan tunduk kontrak. |
| Safety office / runway safety team | Hazard reporting, safety promotion, koordinasi keselamatan dan follow-up rekomendasi | Risk review, safety action, training priority, occurrence analysis | SMS/safety reports, de-identified event data, audit/procedure records | Safety data perlu perlindungan dan batas penggunaan; laporan sukarela tidak selalu representatif. |
| ATC instructor / training center | Training, assessment dan debriefing berdasarkan kewenangan kurikulum | Menulis skenario, menilai prosedur/decision points, memfasilitasi replay | ATC simulator, lesson plan, scenario/event log, rubrik | Pengguna prioritas awal FlowLens; perlu review qualified trainer agar simulasi tidak mengajarkan prosedur yang salah. |
| KNKT / investigator | Investigasi kecelakaan/kejadian serius dan rekomendasi keselamatan | Merekonstruksi urutan dan faktor keselamatan | FDR/CVR, ATC recording, radar/track, dokumen operator, report | Tidak mengakses atau mengolah bukti investigasi tanpa persetujuan; laporan final publik tidak selalu memuat raw data. |

Tanggung jawab spesifik antarunit, radio, system custodian dan controller position tidak dapat disimpulkan dari nama jabatan saja. Peta ini adalah kerangka stakeholder untuk wawancara, bukan diagram RACI bandara yang telah divalidasi.

## 5. Inventaris teknologi dan tingkat bukti

Untuk latency: jika angka performa lokasi atau produk tidak ditemukan, kolom menyatakan “tidak dipublikasikan/bergantung konfigurasi”. Target performa suatu standar bukan ukuran aktual tiap instalasi.

| Teknologi | Fungsi/pengguna | Infrastruktur dan data/output | Status/coverage yang terbukti | Latency dan batasan FlowLens |
|---|---|---|---|---|
| Primary radar | Surveillance non-cooperative pesawat; ATS/ANSP | Radar returns, plot/track tergantung processing | **Operasional Indonesia pada area/fasilitas tertentu**: laporan DJPU menyebut radar/MSSR pada ATSA; New ATMAS mencantumkan radar surveillance. | Update/feed tidak dipublikasikan di materi yang diperiksa; raw/radar track bukan data publik. |
| SSR / Mode S | Aircraft transponder reply dan identification/altitude; controller | Ground interrogator + onboard transponder, track correlation | **Operasional sebagai surveillance capability**; cakupan dan equipage bergantung area, pesawat dan perangkat. | Field berbeda; identity/flight-plan correlation dapat salah atau stale. |
| ADS-B Out / ADS-B | Broadcast posisi/kecepatan/identitas pesawat dan penerimaan oleh ground/aircraft | Onboard GNSS/transponder + ADS-B receivers/ATC automation | **Indonesia: deployment dan area layanan tertentu terbukti**; laporan DJPU menyebut 50 unit dan area layanan. FAA menyebut ADS-B Out broadcast position/altitude/ground speed sekali per detik dalam konteks AS. [FAA ADS-B](https://www.faa.gov/about/office_org/headquarters_offices/avs/offices/afx/afs/afs400/afs410/ads-b) | Nilai 1Hz adalah deskripsi FAA, bukan jaminan feed Indonesia. Gaps, GNSS, equipage, callsign mismatch, coverage dan license tetap ada. |
| MLAT/WAM | Mengestimasi lokasi dari waktu tiba transponder di sejumlah sensor; surveillance provider | Sensor remote, clock/network dan multilateration processor | **Teknologi operasional global; deployment bandara Indonesia tidak terverifikasi** dari sumber publik yang diperiksa. | Update/accuracy/failure mode bergantung site design; perlu data service dan coverage map vendor/ANSP. |
| Surface Movement Radar / SMR | Mendeteksi target permukaan tanpa harus semua target cooperative; tower | Surface radar, track/display | **A-SMGCS benchmark** memakai SMR/MLAT/ADS-B sebagai sumber sesuai konfigurasi; inventaris domestik per bandara tidak ditemukan. [EUROCONTROL A-SMGCS](https://www.eurocontrol.int/service/advanced-surface-movement-guidance-and-control-system) | Tidak dipublikasikan per site Indonesia; blind zones, clutter/identification, display integration perlu dipahami. |
| A-SMGCS / S-SMGCS | Surveillance, identification, tracking; dapat menambah RMCA/CATC/conformance alerts, routing dan guidance | Sensor cooperative/noncooperative, map/runway state, flight plan, controller display, alert/light outputs | **Standar dan layanan tersedia.** EUROCONTROL menegaskan A-SMGCS modular dan penerapannya keputusan lokal. **Instalasi Indonesia tidak terverifikasi** pada sumber yang diperiksa. [EUROCONTROL Specification](https://www.eurocontrol.int/publication/eurocontrol-specification-smgcs-services) | ICAO Doc 9830 yang tersedia publik adalah edisi 2004 dan menyebut target desain surveillance yang ketat; itu bukan hasil instalasi atau FlowLens. |
| ASDE-X / ASSC | Surface situational awareness, track correlation, route conformance/alerts; FAA tower | Surface radar, multilateration, ADS-B, Mode-S/terminal automation | **ASDE-X operasional di 35 bandara AS; ASSC di 9 FAA locations** pada halaman FAA. Bukan sistem Indonesia. [FAA ASSC](https://www.faa.gov/air_traffic/technology/adsb/atc/assc) | Feed surface dipakai untuk operasi; bukan raw/public feed bebas FlowLens. |
| RMCA / RIMCAS / runway incursion alert | Memonitor runway movement dan memberi alert konflik/clearance | Surface track, identity, runway geometry/state, alert logic | **Fungsi dan standar/produk terbukti; implementasi spesifik Indonesia tidak terverifikasi**. EUROCONTROL menamai RMCA bagian Airport Safety Support Service. | Threshold, logic, nuisance alert, procedures dan approval site-specific; bukan logika yang boleh diambil dari demo. |
| RWSL / runway status lights | REL/THL memberikan cue visual otomatis untuk pilot/vehicle operator; tidak memberi ATC clearance | Surface/approach surveillance + runway/taxiway lights | **Operasional di 20 bandara AS**. FAA menegaskan RWSL adalah safety enhancement independen dan tidak menggantikan clearance ATC. Deployment Indonesia tidak ditemukan. [FAA RWSL](https://www.faa.gov/air_traffic/technology/rwsl/index.cfm?print=go) | Output visual otomatis; tidak cocok dijadikan alert FlowLens atau proksi clearance. |
| VMAT / vehicle transponder | Memancarkan identitas dan lokasi kendaraan airport agar terlihat di surface display | Vehicle ADS-B Out/978 MHz UAT pada contoh FAA, vehicle id, surface surveillance | **Tersedia/diadopsi oleh sebagian lokasi AS**; FAA mendorong equipage dan menyatakan rencana/perluasan SAI. **Tidak universal, tidak terbukti di Indonesia.** [FAA VMAT](https://www.faa.gov/airports/runway_safety/airfield_drivers/enhancing-surface-safety-guide-vehicle-movement-area) | Kendaraan tanpa equipment, perangkat mati, atau di luar coverage tidak otomatis tampak; GPS/AVL internal belum tentu dibagi ke ATC. |
| STCA / APW / APM | Alert separation/conflict/proximity pada lalu lintas udara/approach; controller | Surveillance/trajectory state + alert engine | AirNav menyebut fungsi STCA, APW dan APM pada New ATMAS/JATSC. Bukti untuk tiap bandara/tower Indonesia tidak tersedia di release. | Alert input, setting dan status operasi tidak dipublikasikan; bukan surface runway clearance monitor. |
| MTCD | Mengidentifikasi potensi konflik trafik berdasarkan prediksi jangka menengah; center/approach menurut sistem | Radar/ADS-B track, flight plan dan trajectory prediction | **Tersedia pada sistem ATM global; deployment Indonesia tidak terverifikasi** pada sumber yang diperiksa. | Horizon dan alert khusus sistem; tidak disamakan dengan FlowLens time-to-conflict sederhana. |
| Electronic flight strip / FDP | Menangani data flight/clearance/status antar posisi; controller | ATM automation, flight plan/clearance events, user inputs | **Global:** FAA masih mengganti paper-strip workflow melalui TFDM, dengan implementasi bertahap 2020–2028. **Indonesia:** status e-strip per unit tidak ditemukan. [FAA TFDM status](https://www.faa.gov/air_traffic/technology/tfdm/timeline) | Latency/equipage Indonesia tidak terpublikasi; strip/flight data sensitif dan memerlukan integrasi berotorisasi. |
| VHF/UHF voice / radio recorder | Tactical voice ATC-pilot/vehicle dan ground-ground; ATC/pilot/driver | VHF radio, voice communication/control, recorder | **Operasional secara umum dan didukung bukti fasilitas ATSA**, yang dilaporkan memiliki VHF serta voice/air situation display recorder. Deployment/retensi per unit tidak ditemukan. | Live voice saat operasi; akses rekaman, retention, format dan transcript tidak dipublikasikan. |
| CPDLC / Data Comm / ADS-C | Exchange message digital controller–pilot; cocok untuk pesan tertentu, bukan mengganti semua voice | Data link service, equipped aircraft, ATC ground system dan prosedur | AirNav menyebut CPDLC/ADS-C pada New ATMAS. FAA Data Comm deployed pada tower locations tertentu; EUROCONTROL MUAC memakai CPDLC sebagai medium tambahan. | Coverage/equipage/service continuity bergantung lokasi dan pesawat; MUAC tetap memakai voice sebagai tactical primary. |
| AMHS / AFTN / AIDC / ASTERIX | Pesan flight plan/ATS dan pertukaran surveillance/ATM | Network messaging serta format/interface standar | AirNav menyebut AMHS dan pengembangan AIDC pada New ATMAS; A-SMGCS CAT011 menjelaskan data surveillance, flight plan, alert dan holdbar. Bukan bukti akses feed FlowLens. [EUROCONTROL CAT011](https://www.eurocontrol.int/publication/cat011-eurocontrol-specification-surveillance-data-exchange-part-8-category-011) | Perlu kontrak/interface version, timestamps, data-quality contract, cyber review; bukan API publik. |
| SWIM / data sharing | Distribusi data ATM antar sistem/stakeholder dengan layanan dan standar | Messaging, service registry, access control, schemas | **FAA:** STDDS memublikasikan data dari 400+ sistem/200+ airports kepada NAS/non-NAS subscribers; SWIFT akses publik berbasis registrasi/otorisasi layanan. Penerapan Indonesia tidak terverifikasi. [FAA STDDS](https://www.faa.gov/air_traffic/technology/swim/stdds), [FAA SWIM access](https://www.faa.gov/air_traffic/technology/swim/products/get_connected) | “Published” bukan sinonim open data/lisensi komersial; dataset, subscription, authentication, latency dan use policy harus dicek. |
| AMAN / DMAN / TBFM / ATFM | Arrival/departure sequencing dan flow/capacity management; ANSP/operator | Flight plan, estimated times, slots, runway config, surface/terminal data | AirNav menyebut ATFM terkait ATMAS; FAA menerapkan TFDM/TBFM/TFMS. Deployment AMAN/DMAN tertentu di Indonesia belum ditemukan. | Tidak disimpulkan setiap arrival schedule digital tersedia; FlowLens bukan sequence optimizer pada MVP. |
| PBN / RNAV / RNP / FMS | Navigasi berbasis performance dan prosedur; pilot/operator/ANSP | GNSS/IRS, FMS/navigation database, procedure design/validation | Laporan DJPU 2024 mencantumkan implementasi IAP/PBN SID-STAR/approach per bandara. Keberadaan prosedur tidak berarti seluruh pesawat equipage setara, posisi dibagi, atau akses FMS diberikan. | Data avionics operator dan FMS bukan feed publik FlowLens; simulator memakai flight position sintetik. |
| Airport weather / AWOS / RVR / METAR / TAF | Observasi, runway visibility dan forecast; BMKG, controller, pilot, airport ops | AWOS/anemometer/RVR/observations, reporting stations, weather products | BMKG public aviation portal menunjukkan METAR/SPECI/TAF dan airport weather; BMKG juga melaporkan alat tingkat tinggi di Soekarno-Hatta, contoh site, bukan bukti equipage merata. | Timestamp/validity penting; METAR/TAF interval tidak sepadan dengan surface tracking per detik. Gunakan untuk konteks/training. |
| AIP / NOTAM / airport layout | Informasi aeronautika resmi, status fasilitas/prosedur dan perubahan | AIS/AIM publication, charts, notices, AIRAC cycle | AIM Indonesia mencantumkan eAIP dan amendment; halaman akses meminta login. Data inti berpotensi tersedia melalui kanal resmi, tetapi API/reuse terms belum terverifikasi. | Layout resmi memiliki hak penggunaan/kemutakhiran; NOTAM bukan live runway occupancy. |
| Incident/safety report, replay evidence | Pelaporan sukarela, investigasi formal, rekomendasi keselamatan | KNKT investigation, ATS recording/track/FDR/CVR dengan akses otorisasi; NASA ASRS untuk konteks AS | **KNKT menerbitkan laporan final tertentu**; NASA ASRS menyediakan narasi sukarela didesidentifikasi, tidak memverifikasi tiap laporan dan bukan denominator semua insiden. [KNKT](https://www.knkt.go.id/subkomite/penerbangan), [NASA ASRS](https://asrs.arc.nasa.gov/search/database.html) | Laporan publik tidak sama dengan raw time-synced dataset. Jangan ukur incidence rate dari narasi sukarela. |
| Remote/digital tower | Memberikan aerodrome ATS dari lokasi terpisah dengan optical/technical system | Kamera, display, audio, networking, fallback, training, safety case | **Operasional di Swedia sejak 2015; regulatory guidance EASA tersedia.** Sumber publik Indonesia untuk operational deployment tidak ditemukan. [LFV Remote Tower](https://lfv.se/en/services/airport-services/remote-tower-services), [EASA remote tower GM](https://www.easa.europa.eu/en/document-library/acceptable-means-of-compliance-and-guidance-material/group/remote-tower-operations) | Bukan “kamera = tower”; connectivity, latency/integrity, sightline, procedures, approval dan faktor manusia kritis. |
| AI / ASR / NLP / prediction | Membantu transkripsi, entity extraction, event search atau scenario authoring | ATC speech corpora, labels, track context, models, validation and human review | **Riset dan corpus ATCO2 tersedia**; tidak ada bukti AI FlowLens/Indonesia operational. [ATCO2 dataset](https://atco2.org/data), [NASA ATC speech research](https://ntrs.nasa.gov/citations/20240014494) | Corpus ATCO2 memiliki bahasa/airport tertentu dan lisensi beragam; bukan jaminan kinerja Bahasa Indonesia/phraseology lokal. |

## 6. Ketersediaan dan akses data untuk FlowLens

Kolom “pemilik” di bawah adalah pihak yang secara operasional paling mungkin menjadi kustodian/otorisasi. Kepemilikan hukum, controller/processor status, retention dan redistribusi harus dipastikan dengan perjanjian tiap instansi. Format dan latency spesifik Indonesia umumnya tidak dipublikasikan.

| Jenis data dan field contoh | Kustodian/sumber yang perlu didekati | Ketersediaan/format | Akses, kualitas dan syarat | Kelayakan FlowLens |
|---|---|---|---|---|
| Aircraft track: timestamp, lat/lon, altitude, groundspeed, track, callsign/ICAO24 | ANSP; aggregator pihak ketiga/OpenSky untuk riset | Real-time/historis tergantung sensor/API; ADS-B position/state vectors | Coverage/equipage/identity/quality tidak merata. OpenSky membatasi komersial dan operational API tanpa perjanjian tertulis. | **Demo:** sintetik atau file berlisensi cocok. **Riset:** akses berizin/de-identified. **Operasi:** feed ANSP; aggregator publik tidak cukup. |
| Radar / SSR/Mode S | ANSP dan system provider | Operational plot/track, internal format atau standar pertukaran | Tidak ditemukan raw feed publik Indonesia. Sensitif; site coverage dan latency khusus sistem. | Hanya melalui kerja sama; bukan prasyarat MVP simulator. |
| ADS-B messages | Aircraft transmitters dan receiver/ANSP/network aggregator | Broadcast dan decoded tracks; receiver logs/API | Sebagian aircraft/area; identity, update/loss dan provider terms berbeda. ADS-B publik bukan clearance atau verified operational track. | Open dataset sesuai license untuk analisis; kendaraan permukaan perlu sumber tersendiri. |
| MLAT/WAM/surface track | ANSP, airport/operator atau supplier | Fused track/monosensor report; ASTERIX tertentu | Tidak ada interface publik Indonesia terverifikasi; coverage khusus. | Perjanjian dan integration work; tidak diasumsikan untuk pilot awal. |
| Vehicle GPS/AVL/transponder position | Fleet operator, ARFF, airport ops, supplier | Internal AVL/GPS, radio reports, VMAT output di equipped areas | Fleet-specific; no universal transponder. GPS bisa pribadi, offline atau delayed; airport movement permission adalah datum berbeda. | **Demo:** synthetic. **Pilot riset:** posisi/event manual atau AVL mitra dengan izin tertulis. |
| Flight identity/callsign | Operator flight plan, ANSP, ADS-B/transponder decoder | Operational flight data/ADS-B identity | Mismatch, anonymization, security, filtering aircraft; public identity belum tentu benar. | Synthetic callsigns direkomendasikan; jangan expose identitas real tanpa persetujuan. |
| Flight plan / estimated arrival/departure | ANSP/AIM/AMHS/AOC/airline dispatch | Internal AFTN/AMHS/AIDC/FDP messages dan airline systems | Feed live Indonesia terbuka tidak terverifikasi; source dan update semantics bervariasi. | Tidak dibutuhkan untuk demo; partner wajib untuk penggunaan operasional. |
| Clearance, taxi route, hold, runway crossing, readback | ANSP/controller working system; voice record; operator untuk izin kendaraan | Voice atau structured entries; strip/automation site-specific | Data safety-sensitive; tidak ditemukan clearance API publik. Transcript bukan clearance otoritatif. | Synthetic event log untuk demo; manual verified labels untuk replay; integrasi butuh otorisasi. |
| Electronic strip / FDP events | ANSP | Local system events; bisa electronic atau paper/digital hybrid | Coverage dan field contract Indonesia tidak ditemukan di sumber publik. | Jangan klaim connected sebelum interface owner konfirmasi. |
| VHF/UHF recording dan transcript | ANSP communications/recording custodian; regulator/investigator jika berwenang | Audio, time/channel metadata; transcript bila dibuat | Privacy, restricted access, retensi, chain of custody dan keamanan. Kebijakan akses nasional tidak ditemukan. | Hanya data offline yang disetujui; selain itu synthetic audio/manual transcript. |
| CPDLC/Data Comm/ADS-C messages | ANSP datalink system, airline/aircraft system | Structured message sequences dan service metadata | Equipped aircraft, coverage dan service status bervariasi; release New ATMAS tidak memberi public feed. | Berguna pada replay mitra; tidak diasumsikan untuk surface runway. |
| Runway occupancy/status | Tower/ANSP dan airport operations | Derived from controller/surveillance/light systems, ATIS/AIP/NOTAM, reports | Tidak ada satu public record yang pasti mewakili occupancy fisik terkini. NOTAM/status bukan track per detik. | Simulator: state synthetic. Real feed: perlu pemilik lokal. |
| Weather, METAR/SPECI, TAF, visibility/wind | BMKG/station, official aviation met service | Web products/bulletins; METAR/TAF/SIGMET and advisories | Produk publik ada; BMKG menyebut validitas dan ketidakpastian. Situs bukan guaranteed operational API atau commercial license. | **Demo/riset:** data time-tagged jika diizinkan atau synthetic weather. Operasi perlu interface disetujui dan degraded state. |
| AIP, charts dan airport layout | Ditjen Hubud AIM/official AIS, airport operator | AIP/eAIP, AIP SUP, AIC, NOTAM, charts and facility data | AIM portal menampilkan update tetapi full access diamati di balik login; AIRAC berubah. Reuse dan chart rights perlu dicek. | Gunakan chart resmi yang diizinkan atau geometri fiktif untuk MVP. |
| NOTAM / closures / works in progress | AIS, airport operator, ANSP | Official NOTAM text, AIP supplement, internal work-order/ops system | NOTAM text dapat dipublikasi; direct feed/license dan local operational state berbeda. | Konteks skenario offline; bukan pengganti status tower/airport. |
| ATC simulator event log/assessment | Training organization/instructor | Scenario, command, assessment dan debrief records | Institution controls training records; trainee evaluation sensitive. | Dataset mitra paling realistis untuk pilot awal dengan consent, access role dan retensi. |
| Safety report / occurrence narrative | KNKT, airport/ANSP SMS owner, NASA ASRS (U.S.) | Final/interim report atau sanitized voluntary reports | Laporan publik terbatas; ASRS eksplisit tidak memvalidasi tiap narasi dan bukan sampel representatif. | Baik untuk tema skenario, bukan trend denominator atau replay persis tanpa bukti lain. |
| Airline operations/AODB/dispatch/taxi/turnaround | Airline, airport operator, ground handler | Proprietary operational records/APIs | Commercial, security dan data-person constraints; feed publik tidak ditemukan. | Partner-only; tidak perlu untuk hackathon. |
| Airport infrastructure dan vehicle registry | Airport operator, ANSP/CNS/maintenance | AIP/engineering diagram, maintenance system, vehicle/fleet records | Sebagian layout tersedia; detail fasilitas, asset dan kendaraan mungkin restricted. | Synthetic layout MVP; geometry authorized untuk pilot. |

### Data suitability per tahap

| Tahap | Data minimum | Kelayakan | Syarat/batas |
|---|---|---|---|
| Demo offline/hackathon | Synthetic track, fictional geometry, authored clearance/event dan weather states | **Layak.** Membuktikan skenario, timeline, aturan deterministik dan replay. | Tandai semua data simulated; jangan klaim live detection atau alert accuracy. |
| MVP simulator/training lab | Versioned synthetic scenario, seeded trajectories, instructor control, event log, optional licensed sample audio | **Layak.** | Scenario ditinjau trainer; tidak mengajarkan prosedur real sebelum review. |
| Riset kampus | Synthetic/public permitted weather/AIP, licensed historic trajectories atau consented simulator records | **Conditional.** | Research ethics, agreement, license, identity privacy, provenance, timestamp, ground truth dan de-identification. |
| Pilot bersama ANSP/bandara | Site data interface yang dipilih partner; awalnya replay/export offline dengan data yang diizinkan | **Conditional.** | MoU/data processing, threat assessment, security architecture, user workflow dan protocol safety/human-factors. |
| Airport ops support | Read-only authoritative current feed dengan health/status metadata | **Belum terbukti layak saat ini.** | Provider SLA/latency, fallback, safety assessment, change approval, human factors, cyber review, formal acceptance. |
| ATC live integration | Qualified surveillance/flight/clearance interface, safety nets dan local procedures | **Tidak layak diasumsikan untuk MVP.** | Owner/regulator approval, integration test, assurance case, human performance dan operational change safety management. |

### Data-quality policy yang disarankan

- **[INFERENSI]** Setiap datum perlu source, observation time, receipt time, validity window, coordinate system, identity provenance, confidence/quality dan schema version. Timestamp sumber yang hilang berarti “unknown”, bukan “fresh”.
- **[INFERENSI]** Track fusion harus menyimpan source disagreement, duplicate, identity mismatch, dropout dan time alignment. Jangan diam-diam menginterpolasi kendaraan ke runway atau mengubah posisi yang hilang menjadi ancaman presisi.
- **[ASUMSI]** Threshold “stale” harus ditentukan provider dan safety analysis; angka dalam konsep FlowLens belum valid untuk operasi.
- **[FAKTA]** EUROCONTROL CAT011 menstandarkan pertukaran data A-SMGCS surveillance/flight plan/alert/holdbar; standar tidak memberi akses, hak data atau menjamin kompatibilitas dengan interface lokal. [CAT011](https://www.eurocontrol.int/publication/cat011-eurocontrol-specification-surveillance-data-exchange-part-8-category-011)

## 7. Rekonstruksi workflow operasional

Tabel ini menggabungkan prosedur keselamatan ICAO, manual pembanding FAA, serta bukti lokal KNKT. Ini bukan SOP tower tertentu. “Data terlambat/hilang” menunjuk gap publik atau informasi yang perlu diverifikasi, bukan kondisi yang pasti terjadi setiap hari.

| Skenario | Aktor dan urutan umum | Data tersedia / terlambat atau mungkin hilang | Pekerjaan manual dan risiko | Peluang FlowLens yang aman |
|---|---|---|---|---|
| 1. Landing saat kendaraan melintasi runway | Tower/ground, APP, aircraft, vehicle operator. Urutan ilustratif: vehicle meminta akses dan menunggu di batas yang ditentukan → controller menilai runway/approach context → controller menahan atau memberi instruksi eksplisit menurut SOP → kendaraan melaporkan/acknowledge sesuai prosedur → runway state dan landing/vacate dikonfirmasi. | Posisi aircraft/vehicle hanya sebaik coverage source; runway state/clearance mungkin berada pada display/log terpisah. Tidak ditemukan public feed Indonesia yang menyatukan clearance dan surface track. | Visual/radio, konfirmasi posisi dan clearance penting. ETA model bisa salah; overlap bukan bukti controller memberi izin keliru. | Counterfactual training: tracks synthetic, clearance event terpisah, uncertainty dan alasan rule. Jangan sajikan prediksi sebagai alert operational. |
| 2. Departure sequencing | Pilot/dispatch, clearance delivery, ground, tower/APP, airline/airport ops. Urutan ilustratif: flight/ready information disiapkan → clearance/taxi route dan holds dikomunikasikan → aircraft taxi ke posisi sesuai → tower/APP mengelola runway/traffic sequence → takeoff clearance dan departure handoff menurut prosedur lokal. | Flight-plan/slot/A-CDM/TBFM feeds dan surface movement tidak otomatis terbuka. FAA TFDM benchmark integrasi, bukan Indonesia. | Event ready/push/taxi perlu koordinasi; taxi time/ready status bervariasi. | Training replay dan scenario authoring; jangan rekomendasikan urutan departure real-time. |
| 3. Low visibility | Tower/ground, pilot, airport ops, meteorology; prosedur lokal dan approved surveillance menentukan operasi. Urutan ilustratif: weather/visibility condition diamati → unit menerapkan prosedur low-visibility yang berlaku → movement/clearance dipisah dan readback dikonfirmasi → surveillance/visual aid yang tersedia dipakai → prosedur berakhir menurut kriteria lokal. | Visibility/RVR/AWOS/METAR memberi konteks berbeda dari track; equipment availability site-specific. | Berkurangnya pengamatan visual menambah pentingnya prosedur, readback, position report dan approved aids. | Buat skenario low-vis serta source/quality display; tidak memberi clearance atau mengganti LVP. |
| 4. Emergency vehicle / ARFF | ARFF, tower/ground, airport command/ops dan crew berkoordinasi sesuai emergency plan. Urutan ilustratif: emergency dilaporkan → dispatch menetapkan kendaraan/tugas → koordinasi akses/path dilakukan dengan unit ATS/airport → status kendaraan/runway diperbarui saat response → event selesai dan pihak terkait mengonfirmasi. | Dispatch log, vehicle location, radio, runway status dan emergency plan mungkin di sistem berbeda; transponder belum terbukti universal. | Emergency priority, path, authorization dan runway status bersifat lokal/time-critical. | Offline exercise/replay; real-time map butuh vehicle feed dan SOP terotorisasi. |
| 5. Handoff APP–Tower–Ground | APP/tower/ground/pilot. Urutan ilustratif: APP menyampaikan sequencing/traffic context → transfer komunikasi/control pada titik yang berlaku → receiving position menerima/acknowledge → tower mengelola runway event → ground menerima aircraft/vehicle untuk taxi setelah statusnya sesuai. Titik dan tugas aktual mengikuti unit setempat. | Radar track dan messages mungkin berbagi di ATM system; local agreement dan position handover tidak umum terbuka. KNKT 2013 memperlihatkan risiko ketika controller mengira unit lain melakukan tindakan. | Controller perlu memastikan transfer benar dan membaca ulang situasi. | Timeline untuk simulator; jangan simpulkan siapa memegang control dari track saja. |
| 6. Clearance/readback | Controller menyampaikan instruction; pilot/driver membaca atau mengakui; controller mendengar dan memperbaiki mismatch. Urutan umum: request/context → clearance/instruction disampaikan → penerima readback/acknowledge → controller memastikan complete/correct → discrepancy dikoreksi sebelum tindakan berlanjut. | Voice live; CPDLC hanya untuk pesan/coverage/equipment tertentu. Transcript pihak ketiga belum tentu tepat dan tidak mengikat. | Closed-loop communication, callsign dan item safety penting. ICAO menetapkan controller memeriksa readback. | Simulasikan event dengan ground truth; tampilkan original message dan verified state. |
| 7. Readback mismatch | Pilot/operator, controller, frequency participants. Urutan umum: instruction didengar → readback diamati → mismatch terdeteksi manusia/simulator → controller meminta klarifikasi/koreksi → konfirmasi diulang → debrief dilakukan. | Tanpa authorized audio/transcript, FlowLens tidak tahu pesan yang dipancarkan. ASR dapat salah pada callsign, angka, runway, direction atau negation. | Error kata kunci mengubah arti; false mismatch juga menambah noise. | Manual annotation untuk replay; AI hanya candidate transcript berlabel unverified. |
| 8. Radio congestion | Controller, pilot, vehicle/ops; urutan transmisi dan clarification mengikuti prosedur setempat. Urutan latihan: beberapa pesan masuk → sebagian menunggu/terulang → controller mengatur prioritas dan memberi instruksi → readback/correction → evaluasi konsekuensi delay/ambiguity. | Tidak ditemukan dataset publik Indonesia yang menghitung congestion atau busy-channel patterns. Recording/queue telemetry terbatas. | Beberapa pihak menunggu giliran; informasi bisa meminta repeat, tetapi prevalensi tidak diketahui. | Scenario authoring overload untuk training; ukur task/time response, bukan klaim mengurangi congestion. |
| 9. Track dropout/stale | Surveillance/automation, controller, target aircraft/vehicle, CNS/IT. Urutan umum: source health/time dinilai → feed menjadi stale/dropout → display menandai degraded → controller memakai approved observation/communication/contingency → sistem kembali saat source tervalidasi. | Track feeds, sensor health dan timestamp tidak publik; ADS-B/MLAT/radar masing-masing punya gaps. | Controller menggunakan instrumen, visual/radio dan contingency sesuai kondisi fasilitas. | Tampilkan data-quality/stale state, tahan prediksi bila data kurang; demo fallback ke manual/simulated entry. |
| 10. Runway inspection | Ops/maintenance/inspection driver, tower/ground dan safety unit. Urutan ilustratif: inspection request → clearance/rute/hold sesuai prosedur → vehicle melakukan inspeksi dan melaporkan hazard/clear → pihak berwenang memperbarui status runway → operasi normal dibuka kembali sesuai prosedur. | Work order/vehicle track/inspection result dan NOTAM/closure mungkin ada di log berbeda. Exact interface Indonesia tidak ditemukan. | Konfirmasi inspection selesai dan runway available; perubahan runway state membutuhkan otorisasi. | Debrief timeline/bookmark; jangan auto-clear atau menerbitkan runway-available. |
| 11. Incident replay | Safety team/investigator/trainer mengumpulkan records yang sah, menyelaraskan clock/source, membuat timeline dan debrief. Urutan umum: izin data → preserve original files → align clocks/source IDs → annotate gaps/uncertainty → replay → investigator/trainer interprets evidence. | KNKT menerbitkan report tertentu; raw CVR/FDR/ATC recording tidak selalu publik. ASRS narrative sukarela bukan ground truth terverifikasi. | Time sync, missing records dan uncertainty harus dipertahankan. | Replay synthetic/authorized; source label dan provenance ada per event; jangan tampilkan rekonstruksi sebagai transcript faktual. |
| 12. Training/debrief | Instructor, trainee/controller/pilot/vehicle role, evaluator menetapkan tujuan, scenario, rubric dan debrief. Urutan umum: instructor memilih objective → scenario disiapkan/briefed → trainee menjalankan → event markers/observations dicatat → replay dan debrief dengan instructor. | Simulator logs realistis untuk pilot pertama; data dan trainee assessment perlu tata kelola. | Instructor menghubungkan keputusan dengan prosedur dan komunikasi; FlowLens indicator bukan rating kompetensi resmi. | Prioritaskan scenario builder, replay, annotation, alternative branch dan instructor notes; evaluasi bersama trainer. |

### Status prosedur yang menjadi acuan

- **[FAKTA]** ICAO Doc 9870 menekankan readback untuk clearance runway dan kewajiban controller memperbaiki discrepant readback. [ICAO Doc 9870](https://www.icao.int/safety/RunwaySafety/Documents/ICAO_manual_prev_RI.pdf)
- **[FAKTA]** Manual FAA memberi contoh taxi/runway crossing dan hold-short instruction spesifik, tetapi hanya berlaku sebagai pembanding U.S.; jangan salin phraseology/minimum operasional sebagai SOP Indonesia. [FAA ATC terminal procedures](https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_7.html)
- **[FAKTA]** Laporan KNKT Adisutjipto mengutip koordinasi/control/communication lokal untuk kasus 2013. Usia dan konteks satu bandara membatasi generalisasi. [KNKT final report](https://knkt.go.id/Repo/Files/Laporan/Penerbangan/2013/PK-AXG%20%26%20PK-LBH%20Final%20Report.pdf)
- **[BELUM TERVERIFIKASI]** Prosedur nasional yang sama untuk ARFF crossing, runway inspection, low visibility, emergency priority dan voice recorder retention tidak dibuktikan oleh materi publik yang ditinjau; dokumen unit/LOA perlu diminta melalui kerja sama.

## 8. Pemerataan teknologi dan tingkat kematangan

Level berikut memakai kerangka yang diminta dalam brief dan **bukan standar ICAO atau sertifikasi**:

| Level | Kriteria analitis |
|---|---|
| 0 | Bukti menunjukkan observasi visual, voice dan prosedur manual dominan tanpa bukti sistem digital untuk layanan yang dinilai. |
| 1 | Sistem digital berdiri sendiri terbukti tersedia/aktif, tetapi integrasi lintas sistem belum dibuktikan. |
| 2 | Sebagian surveillance/flight information/safety functions terintegrasi pada fasilitas tertentu. |
| 3 | Surface surveillance dan safety net terintegrasi dengan procedure/controller display pada bandara spesifik. |
| 4 | Data sharing terkelola dan dukungan prediktif/decision-support matang pada ekosistem yang dinilai. |

| Segmen/kelas | Bukti yang bisa dipakai | Skor dan alasan | Yang tidak dapat disimpulkan |
|---|---|---|---|
| Indonesia: ANSP/en-route/terminal | Laporan DJPU 2024 menyebut 50 ADS-B units dan lokasi/area layanan; AirNav 2026 menyebut radar+ADS-B, STCA/APW/APM, data link, AIM/ATFM pada konteks New ATMAS/JATSC. | **Level 2 untuk integrasi surveillance/ATM pada fasilitas yang didokumentasikan [INFERENSI]**; ATSA juga mengintegrasikan input pada fasilitas backup. | Tidak menilai surface movement safety; tidak berarti semua tower/ACC memakai set sama atau FlowLens dapat akses data. |
| Indonesia: bandara hub internasional | ADS-B service pada beberapa area/tower terbukti; bandara hub memiliki operasi ATS dan public AIP. | **Tidak diberi level surface maturity.** Inventaris terbuka A-SMGCS/SMR/RIMCAS/vehicle equipage site-by-site tidak ditemukan. | Ukuran, traffic atau klasifikasi internasional tidak membuktikan surface surveillance. |
| Indonesia: domestik utama | Beberapa tower tercantum dalam ADS-B position reporting, bukan bukti peralatan permukaan. | **Tidak dapat dinilai** untuk Level 0–4 per bandara. | Tidak menyamakan ADS-B aircraft en-route/terminal dengan aircraft+vehicle runway picture. |
| Indonesia: regional/kecil | ATS dan informasi aeronautika/weather tersedia sesuai lokasi; data surface technology by airport class tidak ditemukan. | **Tidak dapat dinilai.** Jangan label Level 0 sebagai fakta karena data publik tidak tersedia. | Tidak ada persentase adopsi terverifikasi atau klaim semua bandara kecil manual. |
| Indonesia: terpencil/konektivitas/infrastruktur terbatas | Konteks nasional geografis dan fasilitas beragam; bukti teknologi spesifik perlu diperiksa per lokasi. | **Tidak dapat dinilai;** kebutuhan kontingensi/fallback kemungkinan penting [INFERENSI]. | Jangan membuat skor digitalisasi terpencil tanpa inventaris dan wawancara. |
| Amerika Serikat (benchmark FAA) | 35 ASDE-X, 9 ASSC dan 20 operational RWSL; FAA memasang/merencanakan SAI di hingga 220 towered airports by 2028; STDDS berisi data dari 400+ systems/200+ airports bagi subscribers. | **Level 3 pada fasilitas ASDE-X/ASSC/RWSL [FAKTA + mapping level INFERENSI]; Level 4 hanya untuk ekosistem FAA data-sharing [INFERENSI].** SAI adalah target, bukan installed total. | Bukan coverage semua airport, bukan data gratis, bukan deployment Indonesia. |
| Eropa/benchmark EUROCONTROL | A-SMGCS modular specification memetakan surveillance, airport safety support, routing/guidance; penerapan keputusan lokal. CPDLC operasional di MUAC sejak 2003. | **Bukti teknologi dan site tertentu kuat; maturity lintas negara tidak diberi level agregat.** | Satu specification/centre tidak mewakili semua bandara Eropa. |
| Swedia/remote tower benchmark | LFV mendapat operational approval pada 2014; service ke Örnsköldsvik mulai 2015 dari RTC Sundsvall. | **Bukti operasi remote tower di site tertentu [FAKTA].** | Tidak menjadi bukti remote tower di Indonesia atau integrasi ke FlowLens. |

**[INFERENSI]** Faktor yang mungkin memengaruhi investasi/deployment meliputi traffic density, kompleksitas runway/taxiway, visibility/weather, volume vehicle, capex, konektivitas, maintenance, aircraft/vehicle equipage, vendor integration, staffing dan return-on-investment. Ini kandidat penjelas untuk diuji, bukan penyebab yang telah diukur di Indonesia.

**[BELUM TERVERIFIKASI]** Baseline nasional publik untuk memetakan tiap kelas bandara ke Level 0–4 tidak ditemukan, termasuk jumlah instalasi, status operational, commissioning date, maintenance state, coverage/equipage kendaraan, dan hubungan sistem ke posisi controller. Keluaran maturity yang aman saat ini adalah peta bukti/tidak-bukti, bukan ranking bandara.

## 9. Perbandingan Indonesia dengan ICAO, FAA, EUROCONTROL dan contoh lain

| Benchmark | Pelajaran | Bukti deployment/regulasi | Batas generalisasi ke Indonesia |
|---|---|---|---|
| ICAO | Prinsip keselamatan, service requirements, readback, runway incursion prevention dan human factors; kerangka interoperability global. | Doc 9870 communication best practices; Doc 9830 A-SMGCS modular functions/performance; ICAO GANP remote ATS/operational approval enablers. [Doc 9870](https://www.icao.int/safety/RunwaySafety/Documents/ICAO_manual_prev_RI.pdf), [Doc 9830 listing](https://store.icao.int/en/advance-surface-movement-guidance-and-control-systems-a-smgcs-manual-doc-9830), [GANP remote tower](https://ganpportal.icao.int/asbu?blocks=b1) | ICAO guidance tidak menunjukkan setiap negara memasang teknologi yang sama. Doc 9830 yang diperiksa edisi 2004; angka performanya bukan hasil Indonesia/FlowLens. |
| Indonesia | Surveillance automation, ADS-B, backup ATSA, ATM modernization, VHF/datalink, AIS/weather service dan regulasi ATS nyata. | DJPU 2024 ADS-B/ATSA; AirNav 2026 New ATMAS; BMKG met information; PM 10/2022 perubahan CASR Part 170. | Sumber publik mengungkap lebih banyak airspace/ATM daripada surface safety di tiap aerodrome. Tidak ada denominator surface coverage. |
| FAA (U.S.) | Surface awareness stack memakai fused surveillance; safety layers incremental; SAI berupaya memperluas situational awareness; SWIM/STDDS structured sharing; TFDM introduces electronic strips/surface management. | ASDE-X 35, ASSC 9, RWSL 20, SAI hingga 220 bandara target by 2028; STDDS 38 TRACON/200+ airports/400+ systems (FAA pages). | Angka U.S.-only, tanggal pembaruan halaman beda, SWIM subscription bukan open data. FAA strip status tidak boleh diklaim untuk Indonesia. |
| EUROCONTROL / EASA | A-SMGCS modular functions; local site adoption; interface/performance specs; remote tower membutuhkan faktor manusia dan safety review. | Spec-171 v2.0 (2020); EASA remote tower guidance; EASA 2023/1768 conformity assessment bergantung fungsi intended; LFV Sweden site operational. | Satu centre atau regional standard tidak membuktikan deployment semua lokasi. Klasifikasi/sertifikasi Indonesia perlu ditentukan DGCA/ANSP. |
| Contoh APAC lainnya | Runway safety dan remote/digital ATS muncul sebagai teknologi serta implementation initiatives kawasan. | ICAO APAC working papers mencakup laporan/proposal Malaysia remote tower dan China surface warning system. | Working paper yang diajukan negara adalah bukti first-party program, bukan pengukuran independen, dan bukan bukti Indonesia deployment. |

**[INFERENSI]** Modernisasi ATM Indonesia yang terdokumentasi harus membentuk desain FlowLens pada interoperabilitas, procedural constraints dan data governance. Kesempatan produk bukan “menambah peta karena controller tidak punya teknologi”; kesempatan lebih masuk akal adalah lapisan training/replay untuk menguji apakah pengaitan event, movement, instruction dan uncertainty memperbaiki kualitas debrief.

### Rujukan internasional spesifik

- **[FAKTA]** EUROCONTROL mendefinisikan basic A-SMGCS sebagai surveillance/position-identification-tracking of mobiles; Airport Safety Support (RMCA/CATC/CMAC), routing dan guidance dapat ditambahkan. Deployment adalah keputusan lokal. [A-SMGCS service](https://www.eurocontrol.int/service/advanced-surface-movement-guidance-and-control-system), [Spec-171](https://www.eurocontrol.int/publication/eurocontrol-specification-smgcs-services)
- **[FAKTA]** FAA RWSL memberi red light otomatis dari surveillance permukaan/approach, independen dari controller, dan tidak menggantikan ATC clearance. [FAA RWSL](https://www.faa.gov/air_traffic/technology/rwsl/index.cfm?print=go)
- **[FAKTA]** FAA SWIM architecture memublikasikan services kepada subscribers; non-NAS subscribers melalui registration/request, sebagian services perlu permohonan tambahan. [FAA SWIM](https://www.faa.gov/air_traffic/technology/swim/products/get_connected)
- **[FAKTA]** MUAC menyebut CPDLC sebagai secondary communication; VHF voice remains primary tactical. Centre tersebut melaporkan lebih dari 65% traffic yang crossing MUAC receives some CPDLC clearances—angka ini site-specific, bukan rate Indonesia. [EUROCONTROL MUAC CPDLC](https://www.eurocontrol.int/service/controller-pilot-datalink-communications-our-maastricht-uac)
- **[FAKTA]** EASA menyatakan conformity assessment untuk ATM/ANS ground equipment tergantung intended function dan criticality; sebagian performance specification remote tower belum harmonized. Ini pelajaran desain, bukan penentuan regulasi FlowLens Indonesia. [EASA ground equipment FAQ](https://www.easa.europa.eu/en/the-agency/faqs/air-traffic-management-air-navigation-services-atmans-ground-equipment)

## 10. Gap antara teknologi yang ada dan kebutuhan operator

| Kebutuhan lapangan | Evidence yang tersedia | Gap yang masih perlu dibuktikan | Arti bagi FlowLens |
|---|---|---|---|
| Mengetahui pesawat/kendaraan dan runway state | ADS-B/ATM dan surveillance domestik terbukti di area tertentu; surface surveillance global memiliki preseden A-SMGCS/ASDE-X/ASSC. | Cakupan surveillance kendaraan dan fusion data untuk runway per bandara Indonesia tidak dipetakan publik. | Fokus MVP pada synthetic scenario. Pilot perlu peta source dan gap data untuk satu lokasi. |
| Memahami clearance dan rute aktual | ATC memakai prosedur/voice; KNKT 2013 menunjukkan ambiguity taxi, transfer dan koordinasi sebagai faktor kasus tertentu. | Clearances real dapat berupa voice, data log, readback, radio vehicle dan system entry dengan clock berbeda; hak akses tidak publik. | Bangun timeline event yang berprovenance; jangan menyimpulkan clearance hanya dari posisi track. |
| Menghitung runway occupancy dan conflict window | A-SMGCS/RMCA memiliki fungsi surveil dan alert; ICAO/EUROCONTROL membahas kebutuhan surface data dan safety support. | Tidak ada ground truth FlowLens; ETA touchdown/vehicle-clear dipengaruhi kinerja, status/route, uncertainty, sensor latency dan operating procedure. | Tampilkan interval dan asumsi, jangan memberi probability/severity klaim dari point estimate. |
| Voice review/readback | ICAO menetapkan readback/hearback sebagai pertahanan prosedural; ada riset ASR dan corpus ATCO2. | Data ATC Indonesia berlabel, berlisensi dan diuji pada noise/phraseology lokal tidak tersedia pada public sources. | Utamakan manual transcript/event entry pada pilot awal; AI offline hanya sebagai candidate. |
| Mengukur workload dan task load | NASA-TLX adalah penilaian subjektif multidimensi; EUROCONTROL CAPAN melibatkan controller dalam workload/capacity simulation dan task weights. | Skor internal FlowLens yang dihitung dari traffic/weather/events bukan ukuran workload controller yang tervalidasi atau diagnosis fatigue. | Namai “kompleksitas tugas skenario”; ukur pengalaman operator terpisah dari signal objektif. |
| Replay terintegrasi | KNKT dan ASRS membuktikan laporan keselamatan dapat menjadi bahan pembelajaran; training simulator adalah kemampuan pada ATSA. | Raw audio/track/FDR/CVR/investigation evidence sensitif dan sering tidak tersedia sebagai dataset publik tersinkron. | Replay skenario sintetis/authorized adalah use case paling feasible; jangan menjanjikan investigator replay dari report publik saja. |
| Integrasi sistem dan data sharing | New ATMAS menyebut sejumlah integrasi di JATSC; FAA SWIM/STDDS memperlihatkan subscription data distribution. | Interface, format, cyber, ownership, license dan support berbeda per provider; belum ada agreement FlowLens. | Isolasi adapter; simulasikan input terlebih dahulu, masuk integrasi hanya dengan partner yang mengotorisasi. |
| Training kondisi bandara berbeda | Teknologi, cuaca, staffing, layout dan procedures bervariasi; sumber publik tidak menyediakan inventory per tier. | Belum ada representativitas geometri/layanan untuk hub, regional, kecil atau terpencil di skenario saat ini. | Scenario parameters harus dapat diubah; satu runway fictional tidak boleh dijual sebagai representative of Indonesia. |
| Alert yang benar-benar membantu petugas | FAA RWSL dan A-SMGCS menunjukkan safety nets harus terhubung ke approved procedures dan controller/crew roles. | FlowLens belum dibandingkan dengan incumbent dan belum punya evidence false alert, lead time, trust atau workload impact. | Position alert sebagai simulator feedback; studi pilot ukur comprehension, not accident prevention. |

### Evidence on call / claim scope

- **[FAKTA]** FAA ADS-B rules berlaku pada airspace tertentu di A.S. dan mensyaratkan equipage pesawat yang beroperasi di sana; aturan tersebut tidak boleh dipindahkan ke Indonesia. Indonesia ADS-B rules/equipage harus dirujuk ke regulasi dan AIP Indonesia yang berlaku. [FAA ADS-B airspace](https://www.faa.gov/air_traffic/technology/equipadsb/research/airspace), [Laporan Tahunan DJPU 2024](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf)
- **[FAKTA]** ICAO Doc 9830 berisi target performance A-SMGCS pada edisi 2004, termasuk update posisi/identifikasi dan latency. Target pada manual tersebut adalah rancangan A-SMGCS safety-critical, bukan default threshold FlowLens atau pernyataan real-time performance Indonesia. [ICAO Store Doc 9830](https://store.icao.int/en/advance-surface-movement-guidance-and-control-systems-a-smgcs-manual-doc-9830)
- **[FAKTA]** ATCO2 menyatakan corpora-nya berisi airport-level splits dan lisensi berbeda: training/official test dapat berlisensi untuk komersial/non-komersial melalui ELRA, sedangkan subset 1 jam untuk riset. Ini bukti dataset ATC yang tersedia untuk riset tertentu, bukan izin memakai rekaman operasi Indonesia. [ATCO2 data](https://atco2.org/data)
- **[FAKTA]** NASA ASRS bersifat voluntary confidential reporting; NASA menyatakan tidak memvalidasi kebenaran tiap laporan. Database bermanfaat untuk hazard themes, bukan denominator semua kejadian atau ground truth rekonstruksi. [NASA ASRS Database](https://asrs.arc.nasa.gov/search/database.html)

## 11. Posisi FlowLens yang paling realistis

| Opsi produk | Nilai potensial | Data minimum | Integrasi | Risiko/hambatan | Kelayakan MVP dan rekomendasi |
|---|---|---|---|---|---|
| 1. Offline training simulator | Skenario runway berulang, instruction/event timeline, rehearsal koordinasi dan debrief. | Fictitious airport map, aircraft/vehicle trajectories, clearance/message ground truth, scenario seed. | Tidak perlu sistem ATC live; satu aplikasi lokal dengan trainer control. | Simulasi salah prosedur dapat mengajari perilaku salah; generic geometry tidak representatif. | **Tinggi.** Pilih sebagai positioning hackathon dan v1. Minta trainer review sebelum dipakai untuk pelatihan. |
| 2. Replay dan safety analytics | Meninjau urutan, data source, event bookmark dan debrief; mendukung safety learning. | Log berizin yang sinkron: track, clearance/message, runway state, optional audio, timestamps. | Impor file/offline terlebih dahulu; satu source per pilot. | Data evidentiary/privacy; clock drift dan missing data; jangan menyebut causal analysis tanpa investigator. | **Menengah–tinggi dengan data mitra.** Kembangkan setelah training simulator; mulai dari synthetic and consented exercise replay. |
| 3. Airport operations awareness dashboard | Status aerodrome/works, weather, vehicle location dan event context untuk airport ops. | Authorized airport status, weather, vehicle system, runway closure/NOTAM; data quality metadata. | Airport ops systems, vehicle AVL dan ANSP interfaces. | Data owner banyak; display bisa keliru dianggap otoritas atau situational truth. | **Rendah sebagai MVP.** Mungkin sandbox non-safety-critical setelah ada airport sponsor dan verified interface. |
| 4. Non-safety-critical advisory | Menyajikan referensi event/data quality tanpa memberi instruksi atau clearance; human remains authoritative. | Authoritative source health and timestamps; verified configuration; display role. | Read-only, controlled network, clear “advisory/degraded” behavior. | Automation bias, alert fatigue, security review, safety classification/regulator interpretation. | **Riset jangka menengah.** Jangan deploy ke controller operating position sebelum safety/human-factors evaluation. |
| 5. Real-time integration ATC/ATM operasional | Dapat menyatukan context apabila integrasi, approved data dan safety case mendukung. | Real-time surface surveillance, flight plan/clearance, authoritative runway state, comm/event data, time sync, fail status. | ANSP/airport ATM stack, approved interface, cybersecurity and change management. | Safety-criticality, certification/approval, liability, vendor, false positives, failure fallback, data rights dan procurement. | **Tidak layak untuk MVP.** Hanya fase masa depan bersyarat; bukan promise, bukan pengganti controller. |

### Posisi per konteks penggunaan

| Konteks | Posisi yang direkomendasikan | Klaim yang boleh dibuat | Klaim yang belum boleh dibuat |
|---|---|---|---|
| Hackathon | Simulator demonstrasi offline | “Menampilkan konflik waktu pada skenario synthetic dan dapat direplay.” | Real-time safety alert, detection accuracy, live integration, collision prevention. |
| ATC pilot training | Scenario authoring + instructor replay/debrief | “Menguji workflow latihan dan pemahaman event timeline bersama trainer.” | Mengurangi workload/insiden atau menilai kompetensi bersertifikat. |
| Pilot riset | Simulator/replay analytics non-operasional | “Mengukur usability, event comprehension dan task performance pada protokol studi.” | Generalisasi ke semua controller/bandara tanpa sample/study design yang memadai. |
| Airport operations support | Read-only dashboard eksperimental | “Menyajikan data source X/Y yang diotorisasi dengan timestamp dan status kualitas.” | Clearance, runway available, dispatch order, atau surface surveillance jika feed belum diverifikasi. |
| Produk komersial jangka panjang | Produk training/replay lebih dahulu; integrasi sebagai fitur terpisah jika diminta dan disetujui institusi | “Training/replay platform dengan data yang diizinkan.” | “Certified ATC system”, replacement controller, safety guarantee, atau deployment nasional. |
| Kemungkinan fase operasional | Gate perubahan/safety case dan approval khusus | Klaim terbatas per site sesuai hasil validasi dan izin | Roadmap waktu atau operational use tanpa authority, ANSP dan data owner. |

## 12. Saran pengembangan berbasis kondisi nyata

### A. Perbaikan scope produk

**Prioritaskan kombinasi training + replay** dengan fokus sempit pada runway event timeline. Untuk MVP, gunakan satu layout fictional yang konsisten, beberapa pesawat/kendaraan, event clearance/readback yang ditulis eksplisit oleh author, cuaca sebagai skenario context, deterministic event rules dan instructor-controlled replay.

**Tunda airport operations dashboard, voice AI live, automated readback mismatch, live conflict detection dan predictive workload** sampai ada data serta partner. Jangan menjual workload awareness sebagai kemampuan membaca keadaan mental controller. Jika fitur tersebut tetap di deck, pindahkan ke “riset masa depan” dengan syarat validasi.

**[INFERENSI]** Pembeda terkuat yang dapat diuji tanpa live ATC adalah hubungan antara scenario authoring, source/provenance per event, replay branch, dan instructor debrief. Teknologi surveillance/runway alert itu sendiri telah memiliki preseden industri, jadi FlowLens tidak boleh menyebut dirinya yang pertama mendeteksi runway conflict.

### B. Perbaikan fitur

| Fitur | Nilai nyata yang mungkin | Keputusan | Bukti/guardrail |
|---|---|---|---|
| Aircraft/vehicle map | Membantu membaca pergerakan jika geometry dan positions benar | **Prioritaskan untuk simulator saja** | Label synthetic/source, timestamp, orientation/coordinate correctness, entity identity, view freshness. |
| Time-to-conflict | Menghubungkan timing aircraft/vehicle | **Prioritaskan sebagai rentang simulasi** | Hitung dari asumsi yang eksplisit; tampilkan min–max/uncertainty dan data age; bukan probability tanpa model/validasi. |
| Runway occupancy | Menyatakan runway occupied/clear/crossing | **Prioritaskan sebagai state latihan** | Bedakan physical occupancy, observer estimate, dan clearance state; jangan auto-mark runway clear. |
| Clearance state | Menunjukkan instruction yang diketik/di-author dalam skenario | **Prioritaskan; human-authored first** | Jangan infer clearance dari tracking saja; message/transcript harus verified untuk ground truth. |
| Readback mismatch | Mengidentifikasi perbedaan clearance/readback | **Tunda automation; latihan manual dulu** | Audio quality, callsign/number recognition, false alarms dan human authority. |
| Communication timeline | Memberi sequence pesan/event | **Prioritaskan untuk synthetic/verified text** | Simpan speaker/source/time/verification status; hindari klaim rekaman ATC otomatis. |
| Alert explanation | Menjelaskan rule dan event yang memicu marker | **Prioritaskan** | Cantumkan “karena aturan simulasi X dengan asumsi Y”; jangan gunakan severity yang seolah probabilitas real. |
| Data-quality indicator | Menandai stale/missing/synthetic source | **Prioritas tinggi** | Gunakan status jelas (valid, stale, missing, synthetic, unverified); threshold operational perlu disetujui mitra. |
| Replay/branching | Memutar timeline dan membandingkan alternatif latihan | **Prioritas tertinggi bersama scenario authoring** | Preserve original scenario, event order, seed dan source provenance. |
| Workload/task complexity | Menunjukkan jumlah tugas/event pada skenario | **Ubah nama dan tunda klaim human workload** | Eksperimental task-complexity; bandingkan dengan instrument subjektif dan review trainer. |
| Scenario authoring | Memvariasikan visibility, clearance, traffic dan vehicle timing | **Prioritaskan setelah satu baseline scenario benar** | Instructor review; prevent generated procedure from appearing authoritative. |
| Instructor dashboard | Mengendalikan pause/seek/branch dan mencatat debrief | **Prioritaskan** | Persetujuan trainer; tidak memberi rating formal peserta otomatis. |
| Event bookmark | Mencatat decision point untuk debrief | **Prioritaskan** | Timestamp konsisten dan user-generated notes terpisah dari system events. |
| Report generator | Mengekspor replay/evidence list | **MVP sederhana/manual** | Watermark simulated/data source; jangan label investigation report atau safety finding tanpa review. |
| AI scenario generation | Mempercepat authoring skenario latihan | **Eksperimen nanti** | Generate draft only; instructor validates rules/phrases/geometry before use. |
| Prediction/recommendation | Menyarankan action atau sequence | **Tunda/hapus dari MVP** | Perlu safety case, accepted operational semantics dan data/validation yang belum ada. |

### C. Perbaikan penggunaan AI

| Metode | Penggunaan yang masuk akal | Hal yang harus dihindari |
|---|---|---|
| Speech-to-text | Offline transcript draft pada audio berlisensi/consented untuk training debrief; proposal edit oleh instructor. | Menjadi official clearance source atau mengeluarkan warning live dari transcript yang belum diverifikasi. |
| NLP/entity extraction | Candidate callsign/runway/number tagging pada synthetic/consented transcript. | Menetapkan clearance state tanpa confirmation; otomatis menganggap negation/conditional phrase benar. |
| Anomaly detection | Analisis dataset simulator yang labels dan boundaries-nya didefinisikan. | Klaim menemukan hazard operasional yang tidak terlihat oleh controller tanpa false-negative study. |
| Prediction | Rentang ETA berbasis deterministic kinematics di training; uncertainty ditampilkan. | Precise landing/vehicle-clear estimates di live operation tanpa kinerja, sensor latency dan validation evidence. |
| Recommendation | Candidate scenario/debrief questions untuk instruktur. | Memerintah hold/go-around/crossing, memberi clearance atau menentukan severity secara otoritatif. |
| Scenario generation | Draft variation dari vetted parameter range; human instructor approve sebelum dimainkan. | AI mengarang phraseology/SOP yang tidak sesuai unit atau menerbitkan scenario tanpa review domain. |
| Core conflict rule | Deterministic rules, geometry/time interval calculation dan rule trace. | Opaque model output untuk safety reasoning; output probabilistik tanpa calibrated evidence. |

**[FAKTA]** NASA menjelaskan NASA-TLX sebagai subjective multi-dimensional rating dengan enam subscale. EUROCONTROL CAPAN menggunakan task list/task weights dan active controller participation untuk simulation workload/capacity assessment. Dua pendekatan tersebut menunjukkan workload evaluation memerlukan human/task data, bukan hanya satu operational count. [NASA-TLX](https://www.nasa.gov/human-systems-integration-division/nasa-task-load-index-tlx/), [EUROCONTROL CAPAN](https://www.eurocontrol.int/methodology/capacity-analysis-methodology)

### D. Fallback saat data/integrasi tidak tersedia

| Kondisi | Fallback yang aman | Label UI/laporan |
|---|---|---|
| Tidak ada radar | Synthetic tracks untuk simulator; manual time-stamped replay entry untuk studi | “Simulated observation” atau “manual annotation”; no live track claim. |
| Tidak ada surface surveillance | Instructor memasukkan movement state dalam training; batasi scenario pada apa yang diketahui | “Surface position unobserved/unverified”; jangan emit alert dari target yang tidak terlihat. |
| Tidak ada voice transcript | Manual typed event annotation atau synthetic phraseology reviewed | “No audio/transcript evidence”; jangan infer readback. |
| Kendaraan tanpa transponder/AVL | Manual position report atau scenario script; gunakan last known position hanya pada replay dengan data age terlihat | “Position unknown/stale”; no guessed precise vehicle position. |
| Data tidak real-time | Ubah mode ke replay/asynchronous debrief | “Historical/delayed”; suppress live-risk semantics. |
| Tidak ada sistem bandara yang bisa diintegrasikan | File-based import atau synthetic data pada offline simulator | “Standalone simulation”; tidak menampilkan logo/status system source seolah tersambung. |
| Internet tidak stabil | Local LAN/offline scenario package dan local clock/event queue | Sebut latency internal simulator, bukan real-time outside environment. |
| Tidak ada akses data sensitif | Synthetic/public data yang lisensinya sesuai, de-identification, atau scenario authored | “Synthetic/public-permitted”; jangan menyiratkan hubungan dengan event aktual. |
| Identity mismatch | Pertahankan ID sumber sebagai unknown, tunjukkan conflict flag, minta instructor verification | Hindari auto-merge callsign/ICAO24 atau vehicle id. |
| Source stale/dropout | Tandai stale/degraded, bekukan prediction atau tampilkan interval melebar sesuai studi | Tidak meneruskan nilai terakhir sebagai current truth. |
| Cuaca tidak tersedia | Gunakan scene parameter manual/synthetic atau hide weather-dependent features | “Weather unavailable”; jangan memakai METAR lama seolah current. |
| Tidak ada approval untuk operation data | Tetap di training/research sandbox | “Not operational use”; no export to control position. |

## 13. Fitur yang diprioritaskan, ditunda, atau dihapus

### Lima fitur paling layak dikembangkan

| Prioritas | Fitur | Mengapa layak |
|---|---|---|
| 1 | Replay timeline dengan event source dan timestamp | Nilainya bisa diuji tanpa live feed; mendukung debrief dan penelusuran sumber. |
| 2 | Scenario authoring dan instructor control | Memungkinkan skenario reproducible dan variasi terkontrol untuk pilot training. |
| 3 | Synthetic aircraft/vehicle map + runway geometry | Memperjelas spatial/temporal relation dalam simulator tanpa menyiratkan surveillance nyata. |
| 4 | Deterministic conflict window + explanation + assumptions | Mendemonstrasikan logika transparan dan mudah di-review; tampilkan rentang/asumsi. |
| 5 | Data-quality / stale / synthetic indicator | Mengajarkan batas observability dan mencegah demo overconfidence. |

### Lima fitur yang sebaiknya ditunda

1. Automated real-time voice transcription/readback mismatch.
2. Live aircraft/vehicle tracking melalui integrasi ATC atau aggregator public.
3. Workload score untuk controller atau fatigue indicator.
4. Airport operations dashboard untuk active runway/dispatch decisions.
5. AI recommendations, runway sequencing optimization dan operational ATC integration.

### Fitur yang perlu dihapus dari klaim MVP

- Hapus klaim “mencegah collision/accident” atau “mengurangi incident” sebelum ada bukti hasil terukur.
- Hapus “high risk” jika hanya berdasarkan angka overlap synthetic; ganti “rule triggered in this simulated scenario”.
- Hapus label “workload score” yang memberi kesan mental-workload measurement; ubah menjadi task-complexity indicator experimental.
- Hapus “live ATC dashboard/integrated data” bila tidak ada authorized live feed.
- Hapus “AI understands/validates clearance” sampai performance per critical field diuji pada authorized in-domain data dan manusia tetap mengesahkan status.

## 14. Roadmap MVP sampai pilot

| Tahap | Fitur/data/pengguna | Validasi dan indikator sukses | Partner/risiko | Klaim yang belum boleh dibuat |
|---|---|---|---|---|
| 1. Hackathon MVP | Offline simulation; satu fictional airport layout; seeded aircraft/vehicle movement; clearance/event authored; deterministic interval logic; replay. Pengguna: tim dan juri demo. | Scenario repeatability, rule trace, timeline completeness, data quality labels, correct reset/seek. Bila ada trainer, review face validity. | Tidak memerlukan data live; risiko utama ialah simulasi menyerupai prosedur aktual padahal belum divalidasi. | No live ATC, no operational accuracy, no collision-prevention, no workload reduction. |
| 2. Training/replay pilot | Skenario authoring, instructor console, replay/branch, bookmark, debrief report; manual verified events; peserta/instruktur di simulator training. | Usability, event comprehension, rule transparency, debrief completeness, reported workload after scenario (mis. NASA-TLX). Bandingkan dengan baseline training tasks; sample/design dinyatakan. | ATC school/training center dan qualified trainer; perlu ethics/consent dan review scenario. | Tidak menyatakan training outcome berlaku untuk controller line ops atau mengurangi safety events. |
| 3. Pilot riset bersama | Tambah satu jenis authorized data (mis. simulator event log atau historical de-identified track); test data provenance, time alignment dan missingness. | Measure event retrieval/time, identification of missing data, explanation comprehension, false alert in curated ground truth, inter-rater agreement. | ANSP/airport/airline/research institution; data agreement, privacy, cyber dan access. | Tidak ada live decision-support atau generalisasi ke semua bandara. |
| 4. Airport ops support sandbox | Read-only status board untuk non-safety-critical operational awareness dengan data mitra; explicit data health. | User acceptance, stale/failure handling, interface reliability, cyber/security review, documented roles and degraded mode. | Airport ops + ANSP + IT/CNS + regulator consultation; risiko automation bias dan ambiguous authority. | Jangan mengeluarkan clearance, runway-clear state, alert safety-critical atau rekomendasi dispatch. |
| 5. Integrasi operasional potensial | Hanya jika use case diminta oleh ANSP/airport dan masuk approved system/change process; qualified data, interface, safety/human factors case. | Independent safety assessment, operational trials, human-in-loop validation, site acceptance, monitoring, periodic revalidation. | Authority, ANSP, airport, data owners, vendor and cybersecurity authority. | Tidak ada jadwal atau kepastian fase ini; no replacement controller/no guarantee. |

### Exit criteria yang disarankan

- **Hackathon → training pilot:** instructor domain reviewer dapat menjelaskan setiap rule, model uncertainty dan simulated data status; tidak ada clearance rule yang tidak ditinjau.
- **Training pilot → research pilot:** protocol, participants, measures, data rights, ground truth dan analysis predeclared; prototype di luar operational network.
- **Research → ops sandbox:** sponsor tertulis, interface ownership, security assessment, safety classification/regulatory advice, degraded mode dan user training disepakati.
- **Ops sandbox → operational proposal:** hanya setelah hasil evaluasi diterima oleh ANSP/authority dan semua assurance/change gates dipenuhi; ini bukan otomatis terjadi karena aplikasi bekerja di demo.

## 15. Risiko regulasi, keselamatan, cybersecurity, data dan adopsi

| Risiko | Dampak | Mitigasi yang disarankan |
|---|---|---|
| Automation bias / authority confusion | Pengguna menafsirkan marker sebagai clearance atau perintah sistem | Label simulator/advisory menonjol; jangan pakai warna/control convention seolah operational; controller tetap memutuskan. |
| False negative / false positive | Konflik luput atau alert noise mengganggu latihan/operasi | Ground truth dan uncertainty; evaluasi false-alert/miss pada curated scenarios; jangan pakai threshold arbitrary. |
| Stale/missing/mismatched tracks | Posisi visual meyakinkan padahal sudah tidak current | Data source/time/freshness; degrade/suppress alert; last known state tidak ditampilkan sebagai current. |
| Geometri/coordinate mismatch | Konflik dipetakan ke runway/taxiway yang salah | Fictional layout MVP; geodesy/units/version; partner validation untuk geometri asli. |
| Clearance state salah | UI berkonflik dengan instruction/controller | State hanya dari verified structured event atau manual instructor; separate observed movement and clearance. |
| Model uncertainty disembunyikan | ETA 42/58 detik diperlakukan presisi | Interval/assumptions; sensitivity analysis; tidak menampilkan high/critical tanpa kalibrasi. |
| Voice AI error | Runway/callsign/negation/number salah transcript | Offline candidate transcript, confidence+human verification, domain dataset, critical word testing. |
| Data rights/privacy/retention | Pelanggaran penggunaan, disclosure, personal data atau bukti investigation | Data agreement, purpose limitation, minimization/de-identification, retention/deletion, role-based access; review UU PDP/PP PSTE. [UU PDP](https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022), [PP 71/2019](https://peraturan.bpk.go.id/Details/122030/pp-no-71-tahun-2019?id=school) |
| Cybersecurity/OT network | Akses tidak sah atau gangguan sistem yang berhubungan dengan operasi | Prototype offline; no write interface; signed versioned import, least privilege, audit log, secure update, threat assessment. Live environment needs ANSP/airport review. |
| Regulatory classification unclear | Salah menganggap advisory/training tool otomatis bebas approval | Tentukan intended use dan intended function bersama Ditjen Hubud/ANSP sebelum field pilot; CASR Parts 170/172/171/139 and applicable standards reviewed. |
| Local procedure mismatch | Training mengajarkan tindakan yang bertentangan dengan SOP setempat | Scenario review oleh licensed/current instructor; version per site/procedure; keep fictional baseline labelled. |
| Workload score/stigma | Salah menilai individu/fatigue atau kinerja controller | Jangan simpan person ranking; rename task complexity; use subjective measures in consented study. |
| Vendor lock-in/interface mismatch | Integrasi mahal, unsupported atau hanya kompatibel satu ATM vendor | Modular adapters, documented schema/provenance, simulation adapter first, no commitment to proprietary data access. |
| Staffing/maintenance/connectivity variation | Tool tidak dapat dipakai di lokasi dengan kondisi berbeda | Offline/LAN mode for training; explicit bandwidth, power, support needs; site assessment before airport proposal. |
| Procurement/adoption burden | Tidak ada pemilik budget/use case atau butuh approval lebih besar dari manfaat | Start with trainer/research sponsor, evidence of workflow need, procurement discovery, clear implementation owner. |
| Liability/overclaim | Pitch dianggap janji keselamatan atau operasi siap pakai | Claim register, explicit stage/status, no accident-prevention promise, lawyer/regulatory review before marketing. |

**[FAKTA]** UU 27/2022 mengatur pemrosesan data pribadi dan kewajiban pengendali/prosesor; PP 71/2019 berlaku untuk penyelenggaraan sistem/transaksi elektronik. Klasifikasi metadata/voice/identity dan kewajiban tepat untuk FlowLens perlu dinilai menurut implementasi serta data yang diproses; laporan ini tidak menetapkan analisis hukum. [UU 27/2022](https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022), [PP 71/2019](https://peraturan.bpk.go.id/Details/122030/pp-no-71-tahun-2019?id=school)

## 16. Standar/regulasi yang patut dijadikan acuan

| Acuan | Relevansi | Batas pemakaian |
|---|---|---|
| UU No. 1 Tahun 2009 tentang Penerbangan | Payung hukum sistem penerbangan dan otoritas. | Perlu dibaca bersama peraturan terbaru dan opini authority/lawyer untuk intended use FlowLens. |
| CASR Part 170 / PM 65 Tahun 2017 sebagaimana diubah PM 10 Tahun 2022 | Peraturan lalu lintas penerbangan dan prosedur ATS Indonesia. | SOP lokal, LOA dan persyaratan unit tetap harus diperoleh dari pemilik; jangan mengarang operational state dari aturan umum. [JDIH PM 10/2022](https://jdih.dephub.go.id/peraturan/detail?data=3IMxkCe8aHLI1JCFrczIFY8cNscTorqfV4Dx4eRjLnqG4vQiLcKBjTM4JJhaePerlh4q9FBY8eNFc4koCXYvVDl58m5frhWQ9lU4ua5QCBaZlr9iiYnEv5bD5BWItzCydyxPALl0UxLo1cOHg05gV6Qnlp) |
| CASR Part 171 (aeronautical telecommunications) / Part 172 (ATS provider) | Sertifikasi/penyelenggaraan telecommunication dan ATS providers; relevan untuk sistem/interfaces yang masuk layanan. | Applicability FlowLens tergantung intended function, architecture dan authority determination; tidak diputuskan laporan ini. [JDIH CASR 171](https://jdih.dephub.go.id/api/media?data=KxWrYuMRxBSImTIqGCL3NY4Es35wWQZnR4KBpcgO1oTh4JFoceVhlMC8m6wbRK9pu08cP9rCrjdIG8m34lEjjAi04a9v82HBr9y4KC4c90BWJF5cuqPJm1cxJ9QuFxWr5EPiHHZ0H3iaBt9LkZRKhMOe02LXwcVAF3GZjJ0XotuXMQ20LrknjS9lWn02ReaUr7NiV949R9UN7JKTmEz8FM2eiGGeIRv0YDI869K9zC7Pr8dsq7) |
| CASR Part 139 aerodrome certification; MOS PKP-PK/airport rules | Airport operator, aerodrome movement areas, facility and emergency services. | Confirm current version and local aerodrome manual/ERP before modelling vehicle routes. |
| CASR Part 174; Peraturan BMKG No. 6/2024 dan keputusan/SOP METAR/TAF | Aeronautical meteorological services, responsibility and dissemination. | Public data page is not equivalent to operational interface or guaranteed API. [BMKG regulations](https://web-aviation.bmkg.go.id/web/regulasi) |
| ICAO Annex 10 Vol II, Annex 11, Annex 14 Vol I, Annex 19; Doc 4444 | Communication/phraseology, ATS, aerodrome operations, safety management. | Some ICAO publications are licensed; use official edition/effective amendment. |
| ICAO Doc 9870, Manual on Prevention of Runway Incursions | Readback/communication/runway-safety practices and incident learning. | Distinguish standards text, guidance and local implementation; verify latest effective provisions. |
| ICAO Doc 9830, A-SMGCS Manual | A-SMGCS functionality, implementation levels and performance concepts. | ICAO store lists first edition 2004; assess against current regional specs and local regulation. |
| ICAO Doc 9859, Safety Management Manual | Hazard/risk management and safety case process reference. | Does not itself certify FlowLens. |
| EUROCONTROL Spec-171, A-SMGCS services; ASTERIX CAT011 | Surface surveillance/safety/routing/guidance service and data exchange examples. | Standard/interface not a right to consume local operational data. [Spec-171](https://www.eurocontrol.int/publication/eurocontrol-specification-smgcs-services), [CAT011](https://www.eurocontrol.int/publication/cat011-eurocontrol-specification-surveillance-data-exchange-part-8-category-011) |
| FAA JO 7110.65; FAA VMAT guidance; AC 150/5220-26 | U.S. procedural examples and vehicle surface-surveillance context. | Comparative only; not Indonesia procedure/regulation. |
| EASA ATM/ANS ground equipment Regulation (EU) 2023/1768 and remote tower GM | Intended function, conformity assessment, remote ATS/human factors benchmark. | European regulation does not apply automatically in Indonesia. |
| UU 27/2022 Pelindungan Data Pribadi; PP 71/2019 PSTE | Personal-data/electronic-system processing review. | Legal interpretation for voice/callsign/user study depends facts, roles and deployment. |
| NASA-TLX and EUROCONTROL CAPAN | Human-factors/workload evaluation methods for research and simulation. | Methods must be fit to question; not operational controller competence certification. |

## 17. Pertanyaan untuk wawancara dan observasi

### Ditjen Hubud / regulator

1. Intended use mana yang membedakan training simulator, replay tool, airport awareness dan ATS/ATM equipment?
2. Jika read-only advisory mengolah radar/clearance dan tampil di ruang control, proses safety assessment, approval, equipment certification atau change notification apa yang berlaku?
3. Regulasi mana yang menjadi current governing text untuk ATS, surveillance, CNS, aerodrome, data sharing dan remote ATS?
4. Apakah ada inventory publik atau forum resmi untuk status A-SMGCS/RIMCAS/surface radar/vehicle transponder per lokasi?

### AirNav / ANSP / controller

5. Untuk unit sasaran, siapa mengendalikan aircraft dan kendaraan pada tiap taxiway/runway crossing dan titik transfer APP–Tower–Ground? Berikan SOP/LOA yang boleh dipakai untuk simulasi.
6. Sistem apa yang benar-benar terpasang dan active-used pada posisi target: radar/ADS-B/MLAT, surface radar, e-strip, STCA, A-SMGCS/RMCA, RWSL, CPDLC, weather overlay?
7. Track/status apa yang dapat diekspor, dengan timestamp, retention, schema, refresh rate, availability, missing/stale behavior dan izin penggunaan seperti apa?
8. Bagaimana operasi saat low visibility, vehicle inspection, emergency ARFF, communications failure, surveillance dropout, wrong identity dan radio congestion?
9. Voice recording/transcript siapa kustodiannya; siapa berhak akses; retention, disclosure, security marking dan chain-of-custody apa yang berlaku?
10. Apakah controller melihat gap context tertentu yang belum tertangani oleh display/safety net saat ini? Minta demonstrasi workflow, bukan hanya opini.

### Airport ops / ARFF / ground crew / airline

11. Kendaraan mana yang memiliki AVL, vehicle transponder atau dispatch/GPS; apakah track dibagi ke ATC/tower; bagaimana status kendaraan yang tidak terpantau?
12. Apa workflow request/approval/release untuk runway inspection, emergency movement, work-in-progress dan clearing the runway?
13. Apakah status runway dari operations center sama dengan status yang dipakai tower? Siapa menyatakan runway open/closed/available?
14. Data AODB/flight plan/turnaround/taxi movement apa yang dapat dibagikan dan melalui agreement apa?

### Trainer/safety office/investigator

15. Skenario apa yang aman/relevan untuk training; tindakan atau phraseology apa yang tidak boleh disimulasikan generik?
16. Bagaimana trainer menilai kompetensi dan debrief saat ini; artefak apa yang bernilai: transcript, event marker, replay branch, instructor note?
17. Apakah indikator “task complexity” membantu instructor atau menciptakan rating yang misleading? Instrumen workload subjektif apa yang dipakai?
18. Raw track, audio, event logs atau incident reports mana yang boleh direplay; apa treatment data personal/investigasi?

### Validasi adoption/data

19. Siapa product owner dan budget owner; siapa system integrator dan authority yang menerima hasil?
20. Minimum latency/availability/fallback/accuracy yang diterima untuk training/research tool versus non-critical ops display?
21. Apa label data yang harus dipakai untuk synthetic, stale, manually entered, historical, advisory dan verified?
22. Outcome pilot yang layak: event comprehension, sequence recall, time-to-locate evidence, instructor workload, false alert perception, user trust atau skor lain?

## 18. Evidence register dan sumber internal

Tanggal akses sumber di bawah adalah 30 September 2026, kecuali bila tanggal dokumen dinyatakan terpisah. Sumber resmi dibedakan dari first-party provider/country reports; jumlah/coverage selalu mengikuti cakupan geografis dan tanggal sumber.

### Register sumber eksternal

| ID | Sumber, tanggal/waktu | Kegunaan dan batas |
|---|---|---|
| E01 | [Laporan Tahunan Ditjen Perhubungan Udara 2024](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf), diterbitkan 2025, bagian surveillance/ATSA | Sumber utama Indonesia untuk 50 ADS-B units, listed sectors/towers dan dua ATSA; angka berhenti di 2024. |
| E02 | [AirNav: New JATSC/New ATMAS](https://www.airnavindonesia.co.id/berita-dan-siaran-pers/kunjungi-airnavindonesia-presiden-icao-tinjau-langsung-fasilitas-new-jatsc/), 11 Sep 2026 | First-party description New ATMAS dan rencana modernisasi bertahap; tidak memetakan semua lokasi aktif atau akses feed pihak ketiga. |
| E03 | [AIM Indonesia](https://aimindonesia.kemenhub.go.id/login), diperiksa 30 Sep 2026 | Update AIP/NOTAM portal; akses lanjutan meminta login, syarat API/reuse tidak jelas dari landing page. |
| E04 | [KNKT: Indonesia Air Asia/Batik Air, Adisutjipto runway incursion final report](https://knkt.go.id/Repo/Files/Laporan/Penerbangan/2013/PK-AXG%20%26%20PK-LBH%20Final%20Report.pdf), occurrence 20 Nov 2013/report 2014 | Kasus lokal; mengidentifikasi isu handoff, taxi clearance dan koordinasi. Bukan evidence prevalensi masa kini. |
| E05 | [Ditjen Hubud PM 10 Tahun 2022](https://jdih.dephub.go.id/peraturan/detail?data=3IMxkCe8aHLI1JCFrczIFY8cNscTorqfV4Dx4eRjLnqG4vQiLcKBjTM4JJhaePerlh4q9FBY8eNFc4koCXYvVDl58m5frhWQ9lU4ua5QCBaZlr9iiYnEv5bD5BWItzCydyxPALl0UxLo1cOHg05gV6Qnlp), effective/status as listed JDIH | Amendment CASR Part 170 / Air Traffic Rules. |
| E06 | [Ditjen Hubud KP 308 Tahun 2015, MOS CASR 170-01 surveillance](https://jdih.dephub.go.id/peraturan/detail?data=03fjuhbqhUcIztwYTYnXl98VzqB1j4bQs8cPAnsr1Eg849beMr9GaqX4J9OUTVvTrG8QiOor7oteL8Ql1Ag1DpjP8cMMK8J4W2i48eZnM4z9BJ57lKG9Bop2w3fIZApAKhE1ECBkiOdGQ49FUwaPmIZzRK), JDIH menyatakan berlaku saat diperiksa | Indonesian surveillance service technical reference; verify later amendments with regulator. |
| E07 | [BMKG Daftar Informasi Publik](https://ppid.bmkg.go.id/daftar-informasi-publik), diperiksa 30 Sep 2026 | Public item, custodian, form/update interval for aviation METAR/TAF/SIGMET. |
| E08 | [BMKG Aviation Information System](https://web-aviation.bmkg.go.id/), diperiksa 30 Sep 2026 | Public aeronautical weather products plus uncertainty/currentness disclaimer. |
| E09 | [BMKG aviation regulations](https://web-aviation.bmkg.go.id/web/regulasi), updated list | CASR Part 174 references, BMKG No. 6/2024 and 2025 SOP/decision for TAF/METAR. |
| E10 | [UU No. 27 Tahun 2022 Pelindungan Data Pribadi](https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022) | Current listed law; data-processing framework, no product-specific legal opinion. |
| E11 | [PP No. 71 Tahun 2019 Penyelenggaraan Sistem dan Transaksi Elektronik](https://peraturan.bpk.go.id/Details/122030/pp-no-71-tahun-2019?id=school) | Listed status berlaku; electronic system obligations need implementation-specific assessment. |
| E12 | [KNKT Subkomite Penerbangan](https://www.knkt.go.id/subkomite/penerbangan) | Investigation mandate and Annex 13 context. |
| E13 | [FAA ADS-B Out/ADS-B In](https://www.faa.gov/about/office_org/headquarters_offices/avs/offices/afx/afs/afs400/afs410/ads-b) | Technical aircraft broadcast description; U.S. regulatory context. |
| E14 | [FAA ADS-B airspace/equipage rules](https://www.faa.gov/air_traffic/technology/equipadsb/research/airspace) | Rule in U.S.-defined airspace, not Indonesia. |
| E15 | [FAA ASSC](https://www.faa.gov/air_traffic/technology/adsb/atc/assc) | ASDE-X 35 and ASSC site count/capabilities as described by FAA; last updated 2024. |
| E16 | [FAA Runway Status Lights](https://www.faa.gov/air_traffic/technology/rwsl/index.cfm?print=go) | 20 operational U.S. airports, RWSL role and clearance boundary. |
| E17 | [FAA Vehicle Movement Area Transponders/SAI](https://www.faa.gov/airports/runway_safety/airfield_drivers/enhancing-surface-safety-guide-vehicle-movement-area) | VMAT role and SAI installed/planned to 220 through 2028; U.S. only. |
| E18 | [FAA STDDS](https://www.faa.gov/air_traffic/technology/swim/stdds) | FAA service distributes data from 400+ systems/200+ airports, 38 TRACONs; updated March 2024 page. |
| E19 | [FAA Getting Access to SWIM](https://www.faa.gov/air_traffic/technology/swim/products/get_connected) | Access/registration/request distinction. |
| E20 | [FAA TFDM Status/Timeline](https://www.faa.gov/air_traffic/technology/tfdm/timeline) | Paper-strip context and implementation through 2028 per FAA page. |
| E21 | [FAA Data Comm](https://www.faa.gov/air_traffic/technology/DataComm) | Data link functions and coverage caveats. |
| E22 | [EUROCONTROL A-SMGCS service](https://www.eurocontrol.int/service/advanced-surface-movement-guidance-and-control-system) | Modular surveillance, airport safety support, routing/guidance capability. |
| E23 | [EUROCONTROL Spec-171](https://www.eurocontrol.int/publication/eurocontrol-specification-smgcs-services), 22 Apr 2020 | Service specification and local-decision language. |
| E24 | [EUROCONTROL CAT011 ASTERIX](https://www.eurocontrol.int/publication/cat011-eurocontrol-specification-surveillance-data-exchange-part-8-category-011), 11 May 2020 | A-SMGCS surveillance/flight plan/alert/holdbar data message format; not data license. |
| E25 | [ICAO Doc 9870](https://www.icao.int/safety/RunwaySafety/Documents/ICAO_manual_prev_RI.pdf) | Readback, communication and runway-incursion prevention guidance. |
| E26 | [ICAO A-SMGCS Doc 9830 Store listing](https://store.icao.int/en/advance-surface-movement-guidance-and-control-systems-a-smgcs-manual-doc-9830), 1st ed. 2004 | Official description/version and licensed-access status. |
| E27 | [ICAO GANP ASBU remote ATS](https://ganpportal.icao.int/asbu?blocks=b1) | Remote ATS enablers include operational approval/certification requirements. |
| E28 | [EUROCONTROL MUAC CPDLC](https://www.eurocontrol.int/service/controller-pilot-datalink-communications-our-maastricht-uac) | Site-specific deployment, share and primary-versus-secondary channel. |
| E29 | [LFV Remote Tower Services](https://lfv.se/en/services/airport-services/remote-tower-services) | Sweden approval 2014 and 2015 operational service example. |
| E30 | [EASA Remote Tower GM](https://www.easa.europa.eu/en/document-library/acceptable-means-of-compliance-and-guidance-material/group/remote-tower-operations) | Regulatory guidance list/editions for remote ATS. |
| E31 | [EASA ATM/ANS ground-equipment FAQ](https://www.easa.europa.eu/en/the-agency/faqs/air-traffic-management-air-navigation-services-atmans-ground-equipment) | Intended-function-based conformity and remote tower performance gaps (EU context). |
| E32 | [NTSB Austin DCA23FA149 final investigation](https://www.ntsb.gov/investigations/Pages/DCA23FA149.aspx), event 4 Feb 2023 | Final facts/findings/recommendations; not FlowLens efficacy. |
| E33 | [NTSB LaGuardia DCA26MA161](https://www.ntsb.gov/investigations/Pages/DCA26MA161.aspx), event 22 Mar 2026; preliminary page updated 23 Apr 2026 | Accident facts and investigation ongoing at date checked; preliminary and subject to change. |
| E34 | [ATCO2 corpora and licenses](https://atco2.org/data) | Airport/language-specific ATC speech data; license differs by subset. |
| E35 | [NASA ASR data requirements paper](https://ntrs.nasa.gov/api/citations/20240014494/downloads/AIAA2025%20-%20Data%20Req%20for%20ASR%20for%20ATCo%20-%20Abstract.pdf) | ASR research across public/private ATC datasets; not Indonesian operational validation. |
| E36 | [NASA Task Load Index](https://www.nasa.gov/human-systems-integration-division/nasa-task-load-index-tlx/) | Subjective multi-scale workload tool. |
| E37 | [EUROCONTROL CAPAN](https://www.eurocontrol.int/methodology/capacity-analysis-methodology) | Simulation-based workload/capacity method with local task list and controller participation. |
| E38 | [NASA ASRS Database](https://asrs.arc.nasa.gov/search/database.html) | Voluntary confidential reports, exported data caveat and explicit non-validation warning. |
| E39 | [FAA Terminal ATC Procedures](https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_7.html) | Example of U.S. taxi/runway crossing rules; comparative only. |
| E40 | [EUROCONTROL OpenSky terms](https://opensky-network.org/about/terms-of-use) | Non-profit education/research license; written permission for commercial and operational use. |

### Sumber internal utama

- [Master Research ATC/ATM](../General-Information/atc-atm-master-research-and-solution.md)
- [Workflow, komunikasi, visualisasi](../General-Information/atc-atm-workflow-communication-visualization.md)
- [Visualisasi teknologi ATC](../General-Information/atc-technology-visualization.md)
- [Riset workload ATC](../General-Information/atc-workload-research.md)
- [Riset Aerospace & Defense](../General-Information/boeing-build-aerospace-defense-research.md)
- [ATC FlowLens Knowledge Review](ATC_FlowLens_Knowledge_Review.md) dan PDF padanannya
- [Rancangan Slide MVP](ATC_FlowLens_Rancangan_Slide_MVP.md)
- [Rencana Teknis MVP](ATC_FlowLens_Rencana_Teknis_MVP.md) dan PDF padanannya
- Proposal ID/EN, pitch deck draft ID/EN, seluruh HTML/PDF/PPTX deck dan asset visual pada folder Proposal

**[INFERENSI]** Dokumen internal berulang kali memakai isi pitch yang sama, sehingga jumlah dokumen tidak menambah jumlah bukti independen. Sumber external yang dipakai oleh riset internal juga tidak otomatis valid untuk deployment Indonesia; klaim technology deployment dan statistics ditelusuri ulang ke sumber resmi pada register di atas.

## Kesimpulan wajib

### 1. Kalimat positioning FlowLens paling aman

**ATC FlowLens adalah simulator dan alat replay untuk menjelaskan hubungan gerak, instruksi, serta waktu pada skenario runway; ia membantu latihan/debrief manusia, tidak mengeluarkan clearance, tidak menggantikan controller, dan belum divalidasi untuk operasi ATC nyata.**

### 2. Lima fakta lapangan paling penting

1. [FAKTA] Indonesia memiliki ADS-B surveillance di area tertentu; laporan resmi 2024 menyebut 50 unit fasilitas.
2. [FAKTA] DJPU melaporkan dua fasilitas ATSA dengan surveillance, komunikasi/recording, weather dan ATC simulator.
3. [FAKTA] AirNav mengumumkan New ATMAS/JATSC dengan radar+ADS-B, STCA/APW/APM dan datalink/AIM/ATFM/AMHS/AIDC functions.
4. [FAKTA] Surface safety technologies A-SMGCS/ASDE-X/ASSC/RWSL dan vehicle transponders memiliki preseden global, tetapi coverage per lokasi berbeda dan tidak boleh diasumsikan merata.
5. [FAKTA] Voice/readback dan manusia tetap merupakan bagian penting dari clearance safety loop; datalink dan safety nets tidak mengalihkan kewenangan ATC.

### 3. Lima asumsi FlowLens yang harus diuji

1. [ASUMSI] Training instructors/peserta membutuhkan scenario replay terintegrasi seperti yang diusulkan.
2. [ASUMSI] Event timeline dan explanation memperbaiki pemahaman dibanding simulator/debrief baseline.
3. [ASUMSI] Data model synthetic FlowLens cukup mewakili aircraft, vehicle, clearance dan runway state untuk tujuan latihan yang dipilih.
4. [ASUMSI] Task-complexity indicator membantu trainer tanpa dianggap sebagai mental workload measurement.
5. [ASUMSI] Institusi bersedia menyediakan simulator/log/rekaman yang tepat dengan hak dan perlindungan data yang jelas.

### 4. Lima fitur paling layak dikembangkan

1. Replay timeline dengan event source, timestamp, seed dan branch.
2. Scenario authoring serta instructor controls.
3. Synthetic aircraft/vehicle map dengan geometri eksplisit.
4. Deterministic conflict-window explanation dengan assumptions/uncertainty.
5. Data-quality, stale/missing, manual dan synthetic markers.

### 5. Lima fitur yang sebaiknya ditunda

1. Automated live voice transcription/readback mismatch.
2. Live track feed integration dari ATC/surveillance.
3. Controller workload/fatigue scoring.
4. Airport operations dashboard yang berdampak ke runway decisions.
5. AI recommendation, sequencing optimization, safety-critical alert dan operational ATC integration.

### 6. Lima risiko terbesar jika FlowLens dipaksakan sebagai sistem operasional

1. False confidence atau automation bias dari track/clearance/state yang salah.
2. Alert miss/false alarm dan alert fatigue.
3. Stale/missing data, timestamp mismatch dan identity confusion.
4. Penggunaan data sensitif tanpa izin, perlindungan atau retention yang benar.
5. Tidak memenuhi local procedure, human-factors, regulator, cybersecurity dan safety-assurance requirements.

### 7. Rekomendasi posisi produk

Posisikan FlowLens sebagai **training simulator + replay/safety-learning tool** terlebih dahulu. Jalankan pilot bersama ATC training center/qualified instructor. Safety analytics dapat menyusul dengan event data yang disetujui. Airport operations support tetap sandbox/read-only; real-time ATC integration hanya mungkin melalui project formal dengan ANSP, airport operator, regulator, data owners dan approval yang sesuai.

**Kesimpulan:** fokus FlowLens sebaiknya membantu latihan dan rekonstruksi skenario dengan data yang benar-benar dipahami, bukan menjanjikan surveillance baru. Pilih bukti dan prosedur per fasilitas sebelum menyebut teknologi “sudah digunakan”, dan sebut keterbatasan data sebagai bagian dari desain produk.
