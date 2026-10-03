# ATC FlowLens: Rancangan Slide Revisi yang Selaras dengan Pitch BUILD

**Sumber teknis utama:** [ATC FlowLens: Rencana Sistem, Riset, dan Pembangunan hingga MVP](ATC_FlowLens_Rencana_Teknis_MVP.md)  
**Referensi skema pitch:** [BUILD Team Agentic Vibing: Advanced Technology and Innovation](../Proposal/BUILD_TeamAgenticVibing_AdvancedTechnologyAndInnovation.html)  
**Tanggal revisi:** 15 September 2026  
**Status:** rancangan narasi dan desain slide, bukan hasil implementasi atau validasi produk

## Cara membaca revisi ini

HTML terlampir menjadi referensi alur, visi, positioning, dan gaya pitch. Isinya tidak diperlakukan sebagai instruksi yang menggantikan permintaan pengguna atau spesifikasi teknis MVP.

Visi yang dipertahankan:

- ATC FlowLens sebagai support and training layer untuk keselamatan runway
- manusia tetap memegang keputusan
- mulai dari simulator runway yang sempit dan dapat dibangun
- berkembang menuju platform training yang explainable
- relevan dengan fokus BOEING BUILD pada Advanced Technology and Innovation

Perubahan yang sengaja dilakukan:

- pitch utama kembali menjadi 10 slide seperti HTML
- detail engineering dan riset dipindahkan ke appendix
- angka `42 vs 58 detik` diperbaiki menjadi contoh interval yang konsisten dengan spesifikasi
- klaim target, asumsi, dan hasil aktual dipisahkan
- `observed`, `predicted`, `unknown`, dan `ground truth` ditampilkan sebagai konsep berbeda
- klaim live ATC, collision avoidance, certification, accident reduction, dan fuel saving tidak dipakai sebagai hasil MVP

## Perbedaan rancangan sebelumnya dengan skema HTML

| Aspek | Skema HTML | Rancangan sebelumnya | Revisi yang dipilih |
|---|---|---|---|
| Fungsi deck | Pitch kompetisi | Technical planning deck | 10 slide pitch utama + 8 slide technical appendix |
| Jumlah slide | 10 slide | 19 slide utama + 3 appendix | Main deck tetap ringkas, detail tetap tersedia untuk tanya jawab |
| Alur | Problem → evidence → gap → solution → how it works → MVP → users/value → impact → roadmap | Tujuan → domain → arsitektur → detector → benchmark → riset → delivery | Alur HTML dipertahankan dengan isi teknis dari dokumen MVP |
| Audiens | Juri BUILD dan reviewer umum | Reviewer engineering dan riset | Juri mendapat story, reviewer mendapat appendix |
| Gaya | Dark/light alternating, grid biru, aviation blue, metric blocks, cards | Technical Blueprint charcoal, warm white, cyan, amber | Kembali ke gaya HTML: navy, blue, cyan, ice, amber, red, green |
| Tipografi | Montserrat, IBM Plex Sans, IBM Plex Mono | Inter/Aptos dan mono | Ikuti HTML agar identitas visual tetap konsisten |
| Product framing | Support and training layer | Local simulation training tool | Keduanya digabung: local-first training layer dengan explainable evidence |
| Contoh teknis | `42 s` touchdown, `58 s` vehicle clear, `16 s` overlap | `44,69 s` threshold ETA dan `13,31 s` ilustrasi overlap | Gunakan angka revisi dari dokumen teknis dan tandai sebagai ilustrasi |
| Evidence | 345, 391, 12, DFW/BOS/ORD, beberapa kasus eksternal | Register E01–E14 dengan status dan batas | Pertahankan 345, 362, 391, 12. Hapus atau verifikasi ulang klaim yang belum ada di register |
| Workload | Workload scoring disebut sebagai fitur | Complexity indicator diberi batas eksperimen | Gunakan istilah `task complexity indicator`, bukan workload model tervalidasi |
| Roadmap | Simulator → communication intelligence → training analytics | Technical MVP → lab pilot → partner research → operational development | Roadmap HTML dipertahankan, tetapi gate teknis dan status riset dibuat eksplisit |

## Sistem visual yang dipertahankan dari HTML

**Format:** 16:9 widescreen. Untuk versi HTML, kanvas efektif dirancang sekitar 1440 × 810 px.

**Palet:**

- Navy `#061A3A` untuk cover, closing, dan slide gelap
- Blue `#0033A0` untuk judul, garis, dan primary accent
- Blue 2 `#0B5CAB` untuk secondary accent
- Cyan `#39A8FF` untuk observed track, data flow, dan highlight
- Sky `#DCECFF` untuk teks ringan dan bidang biru muda
- Ice `#F5FAFF` untuk slide terang
- Line `#C9DBF2` untuk tabel dan diagram
- Green `#16865E` untuk state yang valid atau resolved
- Amber `#D99000` untuk advisory, warning, dan asumsi
- Red `#C83B32` untuk critical dan batas risiko

**Tipografi:** Montserrat untuk judul dan label uppercase; IBM Plex Sans untuk isi; IBM Plex Mono untuk rule ID, field, endpoint, timestamp, dan formula.

**Komposisi:** gunakan border tipis, grid halus, garis koordinat, metric blocks, table rows, dan square-corner cards seperti HTML. Cover dan closing memakai latar navy. Slide teknis memakai latar ice dengan diagram yang dapat diedit. Hindari foto stok yang tidak menambah pemahaman.

**Aturan isi:** judul langsung menyebut subjek atau insight. Isi memakai frasa pendek. Sumber eksternal tampil pada slide bila penting, lalu diulang dalam speaker notes. Semua angka yang belum diukur diberi badge `TARGET`, `ASSUMPTION`, atau `ILLUSTRATIVE`.

## Struktur deck yang direkomendasikan

### Slide 1: ATC FlowLens

**Layout:** Cover gelap seperti HTML. Judul besar di kiri, visual konflik runway di kanan, grid koordinat biru tipis di latar.

**Message:** ATC FlowLens adalah layer training dan decision support yang membuat risiko runway lebih cepat terlihat dalam skenario terkontrol.

**Copy utama:**

- `ATC FlowLens`
- `Explainable runway safety training and decision support`
- `Helping air traffic teams see runway risk earlier in controlled training scenarios`
- `Team: Agentic Vibing`
- `Focus: Advanced Technology and Innovation`
- `Positioning: ATC support and training layer`

**Visual:** Gunakan `assets/slide1_runway_conflict_reference.png` dari skema HTML bila aset tersedia. Visual menampilkan aircraft pada final, ARFF vehicle pada crossing, runway 09/27, dan satu garis interval waktu.

**Speaker notes:** Jelaskan bahwa deck ini membahas rencana MVP. Produk belum menjadi sistem ATC live, sistem collision avoidance tersertifikasi, atau hasil validasi trainer/peserta.

**Source note:** Dokumen teknis §1.1–1.3 dan §2.3. Visual mengikuti HTML slide 1.

**Perubahan dari HTML:** positioning tetap. Kalimat pembuka dipersempit ke `controlled training scenarios` agar tidak terdengar seperti hasil operasional.

**QA:** Cover tetap minimal. Jangan menampilkan angka benchmark, statistik insiden, atau daftar fitur panjang.

### Slide 2: A runway conflict forms when context is read separately

**Layout:** Slide terang dengan judul besar, subtitle, lalu tiga kolom seperti HTML slide 2.

**Message:** Risiko tidak muncul hanya karena banyak aircraft. Risiko meningkat saat movement, clearance, communication, visibility, vehicle activity, dan waktu harus dibaca bersamaan.

**Content blocks:**

1. **What the controller is tracking**  
   Aircraft pada approach, landing, departure, taxi, vehicle surface movement, runway state, crossing request, clearance, readback, komunikasi, visibility context, dan koordinasi.

2. **Where workload becomes risk**  
   Informasi tersebar pada track, event komunikasi, status clearance, memori kerja, dan asumsi prosedur. Ketika margin waktu pendek, perubahan kecil pada observed state dapat mengubah interpretasi.

3. **The gap FlowLens focuses on**  
   Aircraft dan vehicle dapat memakai physical runway yang sama ketika clearance, movement, dan timing tidak dibaca sebagai satu hubungan.

**Bottom quote:** `The system supports the controller. It does not replace the controller.`

**Speaker notes:** Hindari klaim bahwa FlowLens dapat membaca kondisi mental controller dari jumlah traffic. Dokumen teknis hanya mendefinisikan indikator kompleksitas tugas sebagai konteks eksperimen.

**Source note:** Dokumen teknis §2.2 dan §2.4. HTML slide 2 dipakai sebagai acuan framing.

**Perubahan dari HTML:** alur dan framing dipertahankan. Istilah `workload` diberi konteks agar tidak menjadi klaim diagnosis.

**QA:** Jangan memakai judul `many aircraft` sebagai akar masalah. Fokuskan judul pada hubungan context dan timing.

### Slide 3: Safety data shows why this context matters

**Layout:** Slide evidence dengan empat metric blocks dan tabel kasus seperti HTML slide 3.

**Message:** Runway incursion adalah masalah keselamatan nyata. FlowLens menggunakan konteks tersebut untuk merancang skenario training, bukan untuk mengklaim bahwa produk sudah mengurangi insiden.

**Metric blocks:**

- `345` — Core 30 FAA runway incursions, FY2024
- `362` — Core 30 FAA runway incursions, FY2023
- `391` — rata-rata tahunan Core 30, FY2017–FY2019
- `12` — bandara Core 30 yang berada di atas tingkat pra-pandemi pada FY2024

**Case table:**

| Kasus | Relevansi untuk FlowLens |
|---|---|
| Austin-Bergstrom, kejadian 4 Februari 2023 | Timing departure/arrival, awareness, fog, dan training low visibility menjadi konteks skenario |
| LaGuardia, kejadian 22 Maret 2026, informasi preliminary | Aircraft–vehicle conflict dan kualitas vehicle awareness menjadi konteks hazard |
| A-SMGCS, RMCA, CATC, dan conformance monitoring | Menjadi preseden domain untuk surveillance dan conflict awareness, bukan bukti efektivitas FlowLens |

**Speaker notes:** Angka `345`, `362`, `391`, dan `12` berasal dari cakupan Core 30 FAA. Jangan menjumlahkan angka dari sumber berbeda. Kasus LaGuardia tetap diberi label preliminary sesuai register evidence. Sumber kasus digunakan untuk hazard context, bukan untuk mengatakan FlowLens dapat mencegah kasus tersebut.

**Source note:** E01–E05 pada dokumen teknis §3.1. Link FAA FY2024, NTSB Austin, NTSB LaGuardia, dan EUROCONTROL A-SMGCS dicantumkan pada notes.

**Perubahan dari HTML:** angka DFW/BOS/ORD dan kasus LATAM tidak dimasukkan sebagai default karena belum tercantum dalam register evidence teknis yang sedang dipakai. Keduanya hanya boleh dikembalikan jika evidence register diperbarui.

**QA:** Setiap metric block memuat cakupan, periode, dan source. Jangan menggunakan kata `proves` untuk menyimpulkan efektivitas produk.

### Slide 4: Existing tools still leave a context gap

**Layout:** Layout gap dua sisi seperti HTML slide 4. Kiri berisi dua blok, kanan diagram tiga tahap.

**Message:** Teknologi surveillance dan safety net sudah memiliki preseden. FlowLens diposisikan sebagai layer training, explanation, dan replay yang bekerja pada skenario lokal.

**Kiri, what ATC already has:**

- Surveillance dan surface awareness
- A-SMGCS, RMCA/CATC, conformance monitoring
- Electronic strips, communication records, dan prosedur koordinasi
- Sumber data yang berbeda kualitas dan cakupannya

**Kiri, why the training gap remains:**

- Peserta perlu menghubungkan clearance dengan physical movement
- Delay, stale track, dropout, dan response delay mengubah kualitas informasi
- Alert tanpa evidence sulit dipakai untuk debriefing

**Kanan, where FlowLens fits:**

`Signals in the scenario` → `FlowLens: occupancy, evidence, replay` → `Human remains in command`

**Speaker notes:** Jangan menyatakan bahwa FlowLens adalah sistem pertama yang mendeteksi conflict. Deteksi, tracking, dan clearance integration sudah memiliki preseden. Pembeda yang diuji adalah evidence linkage, replay, authoring eksperimen, dan training measurement.

**Source note:** Dokumen teknis §3.2–3.3, §6.4, dan E05–E07.

**Perubahan dari HTML:** klaim soal biaya atau kompleksitas infrastruktur live diubah menjadi batas MVP yang lebih terukur. FlowLens tidak mengasumsikan akses radar, radio, atau feed operasional.

**QA:** Diagram harus menunjukkan support layer, bukan replacement layer.

### Slide 5: FlowLens turns runway context into one explainable view

**Layout:** Slide solution dengan enam cards seperti HTML slide 5, tetapi dikelompokkan menjadi tiga pasangan.

**Message:** FlowLens menghubungkan operational signals ke satu tampilan yang dapat dijelaskan, direplay, dan diukur.

**Capability pairs:**

1. **Runway awareness**
   - Observed occupancy dan runway state
   - Predicted occupancy intervals, physical runway 09/27, dan data quality

2. **Explainable alerting**
   - Clearance/request/readback/physical state terpisah
   - Rule, object, time, evidence event, model version, assumption, dan limit

3. **Training and debriefing**
   - Tower-ground coordination, bookmarks, recognition markers, dan assessment
   - Replay source yang immutable, branch alternatif, dan export research

**Feature strip:** `Map` | `Alert evidence` | `Communication timeline` | `Task complexity indicator` | `Replay`

**Speaker notes:** Complexity indicator adalah indikator kompleksitas tugas eksperimen. Jangan menyebutnya sebagai workload model tervalidasi. Communication intelligence seperti ASR dan parsing radio berada di fase setelah inti MVP.

**Source note:** Dokumen teknis §2.3–2.5, §10.4, §11.1–11.4, dan §12.1.

**Perubahan dari HTML:** enam fitur dipertahankan secara konsep. `Clear runway` diubah menjadi observed/predicted/unknown occupancy agar tidak bermakna sebagai clearance operasional.

**QA:** Jangan menambah fitur yang tidak memiliki owner atau test di dokumen MVP.

### Slide 6: The engine finds the conflict window from observed state

**Layout:** Slide teknis utama mengikuti HTML slide 6: timeline lima langkah di atas, dua technical cards di bawah, satu rule card di bagian akhir.

**Message:** Mesin deterministik menggabungkan footprint, route, groundspeed, clearance, dan observation quality untuk menghitung interval penggunaan runway.

**Five-step story:**

1. **Aircraft observed on final**  
   Contoh: BAW123 berada 1,8 NM dari threshold, observed groundspeed 145 kt, clearance `LAND` untuk runway direction 27.

2. **Vehicle observed on crossing route**  
   ARFF-2 bergerak pada crossing route dan memiliki observed speed serta footprint.

3. **Timing and geometry check**  
   Threshold ETA reference: `44,69 s`. Vehicle full exit reference: `58 s`.

4. **Interval overlap**  
   Jika aircraft occupancy `[44,69; 100] s` dan vehicle occupancy `[0; 58] s`, overlap ilustratif adalah `13,31 s`.

5. **Evidence alert**  
   Dashboard menunjukkan rule, object IDs, interval, source event, clearance, data quality, assumption, dan limit.

**Example rule card:**

```text
IF predicted aircraft occupancy overlaps predicted vehicle occupancy
ON the same physical runway
THEN create the relevant occupancy alert
WITH evidence, quality, and model version.
```

**Speaker notes:** Angka `44,69 s` adalah ETA reference menuju threshold dengan 1,8 NM dan 145 kt, bukan constant touchdown time. `13,31 s` adalah ilustrasi interval, bukan benchmark output. Threshold ETA, protection entry, full exit, overlap, dan collision time adalah konsep berbeda.

**Source note:** Dokumen teknis §9.1–9.7.

**Perubahan dari HTML:** `42 s`, `16 s`, dan rule yang mensyaratkan clearance tertentu dihapus. Alert occupancy tidak mensyaratkan `CROSS_RUNWAY` clearance karena unauthorized presence tetap dinilai dari track.

**QA:** Tampilkan badge `ILLUSTRATIVE`. Jangan gunakan judul `before it becomes obvious` sebagai hasil terukur.

### Slide 7: The MVP proves the safety logic without live ATC data

**Layout:** Slide MVP dengan tiga cards dan tabel `Build now` versus `Later`, mengikuti HTML slide 7.

**Message:** Scope yang kecil membuat technical MVP dapat dibangun, diulang, diuji, dan dipasang pada lab tanpa dependensi live.

**Three cards:**

- **What we build now**  
  Satu layout sintetik, satu physical runway dengan dua arah, 3–5 aircraft, 1–2 vehicle, structured clearance/communication, route and footprint model, rule engine, evidence alert, replay, dan LAN sync.

- **Why it is buildable**  
  Data sintetik memiliki seed, version, dan assumptions. Server lokal memusatkan clock dan state. Internet, radar, radio operasional, dan vehicle hardware tidak diperlukan saat latihan.

- **Why it creates training value**  
  Instruktur dapat menjalankan skenario yang dapat diulang. Peserta berlatih tower-ground coordination. Instruktur dapat menghubungkan decision, alert, dan timeline saat debriefing.

**Build now versus later:**

| Layer | Build now | Later, only after the appropriate gate |
|---|---|---|
| Data | Synthetic scenario JSON dan observed stream | Authorized offline dataset atau site-specific adapter |
| Logic | Footprint, route/time intervals, R01–R06, evidence | Richer model, AI communication study, multi-runway |
| Interface | Map, runway board, alerts, timeline, replay | Training lab integration dan analytics lanjutan |

**Speaker notes:** `MVP teknis` berbeda dari `pilot tervalidasi`. P1 seperti branch, complexity, assessment, dan baseline menjadi target rilis delapan minggu. Jika jalur enam minggu dipilih, fitur tersebut dapat ditunda, tetapi evidence, replay dasar, observed-only boundary, dan unknown/stale handling tetap wajib.

**Source note:** Dokumen teknis §5.1–5.3, §18.5–18.6, dan §20.2.

**Perubahan dari HTML:** scope dipertegas dengan 09/27, observed-only boundary, evidence, quality handling, dan release gates.

**QA:** Hindari label `live ATC prototype`, `certified`, atau `collision prevention`.

### Slide 8: The first adoption path is training and safety review

**Layout:** Slide users and value seperti HTML slide 8. Kiri berisi target users dan adoption path. Kanan berisi empat metric blocks.

**Message:** Entry point yang paling realistis adalah training, replay, dan safety readiness, sebelum integrasi data operasional.

**Who feels the problem:**

- ATC training centers dan aviation academies
- Airport safety teams dan airport operations
- Tower-ground training roles
- ARFF atau emergency vehicle training context
- Research evaluator yang memerlukan provenance dan denominator

**Adoption path:**

1. Local training and simulation tool
2. Safety briefing dan scenario replay
3. Research collaboration dengan trainer atau aviation school
4. Offline partner research dengan data yang diizinkan
5. Operational development hanya melalui requirements, assurance, dan approval tersendiri

**Value blocks:**

- **Training:** skenario aircraft–vehicle yang repeatable dan dapat dibahas
- **Review:** timeline clearance, track, alert, dan response yang tersambung
- **Readiness:** latihan koordinasi tower, ground, dan emergency vehicle
- **Expansion:** AI communication study, richer analytics, dan simulator integration setelah gate data/protocol

**Speaker notes:** Tidak ada klaim willingness to pay, procurement feasibility, atau dukungan ANSP/Boeing di dokumen sumber. Riset pasar dan akses partner masih pekerjaan berikutnya.

**Source note:** Dokumen teknis §4.1, §19.3, §19.5–19.6.

**Perubahan dari HTML:** adoption path tetap. `future certified decision-support exploration` diberi label sebagai tahap terpisah, bukan kelanjutan otomatis dari MVP.

**QA:** Gunakan kata `potential` atau `future` untuk expansion. Jangan menyajikan adoption sebagai traction aktual.

### Slide 9: BUILD alignment comes from practical, explainable safety technology

**Layout:** Impact table seperti HTML slide 9, lalu tiga cards untuk alignment.

**Message:** FlowLens cocok dengan BUILD karena mengubah teknologi deterministik, geometri, data quality, dan replay menjadi training support yang dapat diperiksa.

**Impact table:**

| Area | Nilai yang direncanakan | Status klaim |
|---|---|---|
| Runway safety | Membantu peserta melihat hubungan aircraft, vehicle, clearance, dan timing dalam skenario | Technical target |
| Training and review | Membuat skenario dan timeline lebih mudah dijelaskan | Technical target, human benefit belum terbukti |
| Workload awareness | Memberi indikator kompleksitas tugas berdasarkan traffic, communication, pending tasks, crossing, visibility, dan emergency context | Experimental indicator |
| Operational flow | Menjadi dasar studi lanjutan tentang delay, go-around, dan duration | Tidak ada fuel-saving claim pada MVP |

**Three alignment cards:**

- **Advanced Technology and Innovation:** deterministic conflict detection, geometry, interval prediction, evidence, WebSocket LAN sync, dan replay
- **Social impact:** training yang lebih terstruktur untuk situasi yang melibatkan passenger aircraft, crews, ground staff, dan emergency units
- **Sustainability path:** operational flow atau fuel impact hanya boleh dinilai dengan baseline aircraft performance, intervention effect, dan validation terpisah

**Speaker notes:** Safety benefit dan fuel benefit tidak selalu searah. Go-around yang tepat dapat menjadi tindakan keselamatan. Tujuan MVP bukan mengurangi semua go-around.

**Source note:** Dokumen teknis §11.1, §19.3–19.4, §20.4 dan HTML slide 9.

**Perubahan dari HTML:** alignment BUILD dipertahankan. Klaim `reduce avoidable go-arounds` dan `fuel burn` diturunkan menjadi research path karena belum memiliki model atau hasil validasi.

**QA:** Bedakan `expected value`, `target`, dan `measured impact`. Jangan tampilkan future benefit sebagai actual impact.

### Slide 10: Start narrow, validate in the lab, grow carefully

**Layout:** Closing dark slide seperti HTML slide 10. Tiga phase cards di tengah, ask dan closing thought di bawah.

**Message:** FlowLens bergerak dari technical MVP yang terukur menuju lab pilot dan research collaboration, dengan gate yang jelas pada setiap tahap.

**Three phases:**

1. **Phase 1: Technical MVP, 6–8 weeks**  
   Synthetic runway, observed movement, geometry/time engine, R01–R06, evidence, LAN training session, replay, exports, canonical tests, benchmark, dan install guide.

2. **Phase 2: Lab pilot**  
   Trainer review, frozen protocol, participant access, paired baseline versus FlowLens, comprehension, recognition time, decision quality, replay debriefing, dan raw unweighted NASA-TLX.

3. **Phase 3: Partner research**  
   Offline data adapter, time alignment, quality audit, AI communication study pada corpus berlisensi, atau read-only shadow mode. Operational development tetap memerlukan proyek dan assurance terpisah.

**Ask to BUILD:**

- trainer/domain reviewer untuk SOP, phraseology, dan rubric
- mentorship untuk technical verification dan safety-critical product discipline
- akses untuk lab pilot dan research protocol
- feedback untuk membekukan 12 canonical scenarios

**Closing thought:** `ATC FlowLens gives teams a clearer lens on runway flow, evidence, and conflict risk while humans remain in command.`

**Speaker notes:** Tutup dengan status jujur: technical MVP adalah target pembangunan. Trainer review dan participant study menjadi `NOT_DONE` bila belum tersedia. Human benefit tetap `UNPROVEN` sampai evidence terkumpul.

**Source note:** Dokumen teknis §16.7, §17.7, §18.8, §19.5–19.6, dan §20.3–20.5.

**Perubahan dari HTML:** tiga phase tetap, tetapi phase 1 dan phase 2 diberi gate teknis serta research readiness. `Future certified support` tidak dipresentasikan sebagai outcome otomatis.

**QA:** Closing harus meninggalkan satu ask yang jelas. Jangan menutup dengan klaim `ready for live ATC`.

## Technical appendix

Appendix mengikuti gaya visual HTML, tetapi lebih teknis. Gunakan nomor `A1/08` sampai `A8/08` dan jangan memasukkan semuanya ke alur pitch utama kecuali juri meminta detail.

### Appendix A1: The detector sees only delivered observations

**Layout:** Trust-boundary diagram.

**Message:** Detector dan participant UI hanya memakai data yang sudah delivered pada simulation time tersebut.

**Diagram:**

```text
Private scenario + seed
        ↓
Truth simulator
        ↓
Sampling + delay + noise + dropout
        ↓
Validated observed events
        ↓
Observed state engine
        ↓
Prediction + rules + evidence
        ↓
Authorized dashboard / replay
```

**Private only:** future actions, true trajectory, queued samples, RNG state, ground-truth labels.  
**Participant-visible:** delivered tracks, applicable clearance, alert evidence, data quality, authorized snapshot.  
**Unknown:** stale track, missing coverage, moving object without known route.

**Source note:** Dokumen teknis §6.1–6.4, §7.7, §9.1, §10.5.

### Appendix A2: One physical runway, two directions, explicit geometry

**Layout:** Annotated runway map dengan dimensi.

**Content:**

- runway `3.000 m × 45 m`
- protection area `x = 0–3.000`, `y = −75…+75`
- vehicle crossing `x = 1.500`
- hold lines `y = −95` dan `+95`
- parallel taxi route `y ≈ −160`
- physical runway ID yang sama untuk `09` dan `27`
- synthetic coordinate system dalam meter

**Caveat:** Geometri tersebut adalah geometri latihan. Bukan separation minimum atau standar bandara.

**Source note:** Dokumen teknis §7.3–7.4 dan §19.2.

### Appendix A3: Occupancy interval and uncertainty model

**Layout:** Formula kiri, interval chart kanan.

**Content:**

```text
ETA threshold = remaining approach distance / observed groundspeed
ETA full exit = remaining route distance until the whole footprint exits / observed speed
overlap = max(0, min(A.exit, B.exit) − max(A.entry, B.entry))
```

- Footprint dihitung sampai seluruh body keluar dari area
- Route distance dipakai untuk prediksi
- Speed < `0,05 m/s` dianggap stopped
- Stopped di protection menghasilkan `exit unknown`
- Nominal prediction memakai assumed range `±5 m` dan speed fraction `±10%`
- Buffer advisory `10 s` bukan separation minimum
- Tidak ada confidence percentage tanpa kalibrasi

**Source note:** Dokumen teknis §9.1–9.7.

### Appendix A4: Rule library and alert lifecycle

**Layout:** Rule table di kiri, lifecycle state machine di kanan.

**Rules:**

| Rule | Fungsi |
|---|---|
| R01 | Arrival occupancy |
| R02 | Departure occupancy |
| R03 | Hold violation |
| R04 | Clearance inconsistency |
| R05 | Closed runway use |
| R06 | Tracking degraded |

**Severity:** `ADVISORY`, `WARNING`, `CRITICAL`, dan `DATA_DEGRADED` sebagai dua dimensi risk level versus data quality.

**Lifecycle:** active → evidence update → acknowledged → quality degraded atau updated → resolved setelah kondisi aman stabil 3 detik dengan data memadai.

**Source note:** Dokumen teknis §10.1–10.4.

### Appendix A5: Role-based dashboard and LAN deployment

**Layout:** Left browser role map, right dashboard wireframe.

**Roles:** instructor, tower, ground, observer, evaluator.  
**Deployment:** satu local server, beberapa browser dalam LAN, SQLite di disk server.  
**Dashboard areas:** session header, map, runway board, alert panel, evidence detail, communication timeline, complexity indicator, instructor/review controls.

**State rules:** WebSocket reconnect meminta snapshot baru. Last-known state dibekukan ketika koneksi putus. Command scope berasal dari seat token, bukan dropdown role.

**Source note:** Dokumen teknis §4.1–4.2, §12.1–12.4, §13.6–13.7.

### Appendix A6: Persistence, replay, and branch provenance

**Layout:** Source session di atas, branch session di bawah.

**Content:**

- Public event log dan public frames
- Private checkpoints setiap 5 detik
- Archive memakai rule/version historis
- Source training dibekukan setelah ended/interrupted
- Branch menyimpan parent session ID, frame time, intervention, revision, dan evidence ancestry
- Re-analysis dengan rule baru menjadi output terpisah
- Storage failure mem-pause sesi dan tidak memberi status “saved” sebelum commit

**Source note:** Dokumen teknis §14.1–14.5.

### Appendix A7: Canonical tests, benchmark, and performance targets

**Layout:** Kiri canonical scenarios, kanan 100-run composition, footer performance target.

**Canonical coverage:** S02 overlap, S03 stopped vehicle, S05 crossing without clearance, S07 cancellation before exit, S08 delayed go-around, S10 dropout, S12 replay/reconnect.

**100-run plan:** 40 conflict, 40 safe, 10 delay/noise stress, 10 dropout/unknown route.

**Target release:**

- evidence completeness `100%` pada alert relevan
- detector `p95 < 50 ms`
- browser delivery/render `p95 < 500 ms`
- antar-browser clock `< 500 ms`
- reconnect recovery `≤ 3 s`
- endurance `30 menit`
- nominal recall `≥95%` pada adequate-observation conflict stratum
- safe-run false warning `≤5%`

**Status label:** Semua angka adalah `TARGET` sampai report pengujian aktual tersedia.

**Source note:** Dokumen teknis §15.1–15.7 dan §16.1–16.6.

### Appendix A8: Research protocol, limits, and public claims

**Layout:** Dua kolom. Kiri research protocol, kanan claims boundary.

**Research protocol:**

- 2–3 trainer dan 6–10 peserta ATC sebagai target formatif
- within-participant paired scenario dengan counterbalanced order
- baseline versus FlowLens pada input dan timing yang setara
- recognition time, comprehension, decision quality, timeline reconstruction, interaction errors, dan raw unweighted NASA-TLX
- trainer review dan participant access menjadi gate sebelum human benefit claim

**Claims boundary:**

- Sah setelah evidence: controlled runway scenarios, defined-risk detection, evidence explanation, replay support
- Belum sah dari MVP: mencegah kecelakaan, siap ATC live, certified, mengurangi accident rate, atau menghemat fuel
- Jika belum ada trainer/peserta: `TRAINER REVIEW: NOT_DONE`, `PARTICIPANT STUDY: NOT_DONE`, `HUMAN BENEFIT: UNPROVEN`

**Source note:** Dokumen teknis §17.1–17.7, §19.2–19.6, dan §20.3–20.5.

## Mapping HTML ke deck revisi

| HTML | Deck revisi | Perlakuan |
|---|---|---|
| 01 Cover | Slide 1 | Dipertahankan. Subtitle dipersempit ke controlled training scenarios |
| 02 The Problem | Slide 2 | Dipertahankan. Workload diberi batas interpretasi |
| 03 Evidence | Slide 3 | Metric blocks dipertahankan. Angka/kasus diselaraskan dengan evidence register |
| 04 The Gap | Slide 4 | Dipertahankan. FlowLens diposisikan sebagai training/explanation layer |
| 05 The Solution | Slide 5 | Dipertahankan. Occupancy dan evidence dibuat lebih presisi |
| 06 How It Works | Slide 6 | Diperbarui secara teknis. `42/58/16` diganti `44,69/58/13,31` sebagai ilustrasi |
| 07 MVP | Slide 7 | Dipertahankan. Scope, LAN, observed-only, dan gates ditambahkan |
| 08 Users & Value | Slide 8 | Dipertahankan. Adoption path dibuat sesuai tahap riset |
| 09 Impact | Slide 9 | Dipertahankan. Sustainability dan workload diberi label target/experimental |
| 10 Roadmap | Slide 10 | Dipertahankan. Technical release dan research readiness dipisahkan |

## Rekomendasi penggunaan

- Gunakan slide 1–10 untuk pitch kompetisi utama.
- Gunakan A1–A4 ketika juri menanyakan detector, geometry, atau alert evidence.
- Gunakan A5–A8 ketika juri menanyakan deployment, reproducibility, benchmark, atau validation.
- Jika durasi hanya 5 menit, prioritaskan slide 1, 2, 3, 5, 6, 7, 9, dan 10.
- Jangan menambahkan seluruh detail teknis ke main deck karena akan menghilangkan ritme pitch HTML.

## Checklist final produksi

- [ ] Main deck tetap 10 slide dan footer mengikuti format HTML `01/10` sampai `10/10`.
- [ ] Cover dan closing memakai navy. Slide tengah mengikuti light ice-blue system.
- [ ] Font menggunakan Montserrat, IBM Plex Sans, dan IBM Plex Mono atau fallback yang konsisten.
- [ ] Semua metric eksternal memiliki cakupan, periode, dan source.
- [ ] Contoh S02 diberi label `ILLUSTRATIVE`, bukan benchmark.
- [ ] `Observed`, `predicted`, `unknown`, dan `ground truth` tidak dicampur.
- [ ] Complexity indicator tidak disebut sebagai workload model tervalidasi.
- [ ] G5 research readiness tidak disamakan dengan G6 technical release.
- [ ] Tidak ada klaim `collision avoidance`, `live ATC`, `certified`, `accident reduction`, atau `fuel saving` sebagai hasil MVP.
- [ ] Semua diagram, tabel, dan chart tetap editable ketika dipindahkan ke PowerPoint.
- [ ] Tidak ada teks isi di bawah 17 pt pada output final.
