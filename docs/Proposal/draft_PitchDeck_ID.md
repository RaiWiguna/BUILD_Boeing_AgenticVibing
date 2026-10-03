# Draft Pitch Deck ATC FlowLens

Tujuan dokumen: Draft ini berisi rancangan lengkap untuk pitch deck maksimal 10 slide dalam konteks BUILD Indonesia. Deck diposisikan sebagai proposal hackathon, bukan sekadar presentasi produk. Isinya harus menjelaskan masalah, bukti pendukung, solusi, MVP, dampak, relevansi bisnis, dan kesesuaian dengan BUILD Indonesia.

Rekomendasi jumlah slide: **maksimal 10 slide**  
Project: **ATC FlowLens**  
Tema: **Aerospace & Defense**  
Primary focus area: **Advanced Technology and Innovation**  
Relevansi sekunder: **Social Impact dan Sustainability**

---

## Apakah Deck Perlu Lebih Banyak Data?

Ya. Pitch deck akan lebih kuat jika menggunakan data dan referensi yang cukup untuk menunjukkan bahwa ATC FlowLens dibuat berdasarkan masalah keselamatan penerbangan yang nyata, bukan hanya asumsi atau spekulasi. Namun, deck juga tidak boleh berubah menjadi paper riset. Slide utama sebaiknya memakai evidence yang singkat dan kuat, sedangkan data detail dapat ditempatkan sebagai appendix atau backup slides.

Deck sebaiknya memuat empat jenis evidence:

1. **Evidence dari kasus nyata**  
   Contoh runway incursion, konflik pesawat-kendaraan, low visibility, dan controller workload.

2. **Evidence operasional**  
   Penjelasan mengapa workload ATC bisa tinggi: traffic, runway crossing, komunikasi, cuaca, kendaraan bandara, dan monitoring banyak display.

3. **Evidence teknologi yang sudah ada**  
   Sistem ATC/ATM saat ini sudah mencakup radar, ADS-B, A-SMGCS, RIMCAS, STCA, electronic flight strips, CPDLC, dan SWIM. Ini membantu memposisikan ATC FlowLens sebagai support layer dan training layer, bukan pengganti sistem ATC tersertifikasi.

4. **Evidence dampak bisnis dan operasional**  
   Solusi dapat mendukung efisiensi training, safety awareness, post-event review, runway flow, dan potensi pengurangan delay atau go-around yang tidak perlu di masa depan.

Business impact perlu dimasukkan karena BUILD Indonesia adalah program hackathon dan inovasi. Juri kemungkinan tidak hanya menilai kreativitas teknis, tetapi juga value praktis, feasibility, jalur adopsi, dan dampaknya. Sisi bisnis tidak perlu terlalu kompleks, tetapi harus menjawab:

- Siapa pengguna solusinya?
- Mengapa mereka membutuhkan solusi ini?
- Value apa yang diberikan?
- Mengapa MVP-nya realistis?
- Bagaimana solusi ini bisa berkembang setelah hackathon?

---

# Struktur Pitch Deck per Slide

## Slide 1 - Cover

### Judul Slide
**ATC FlowLens**

### Subtitle
**Explainable Runway Safety and ATC Decision-Support Dashboard**

### Isi Slide
- BUILD Indonesia Hackathon
- Theme: Aerospace & Defense
- Focus Area: Advanced Technology and Innovation
- Nama tim
- Anggota tim

### Catatan Presentasi
ATC FlowLens adalah dashboard runway safety dan decision-support untuk operasi Air Traffic Control. Solusi ini membantu tim air traffic melihat pergerakan pesawat, aktivitas kendaraan ground, status clearance, timeline komunikasi, dan risiko workload dalam satu tampilan operasional.

### Arahan Visual
Gunakan visual yang terinspirasi dari runway bandara atau tower control. Hindari tampilan yang terlalu futuristik. Deck sebaiknya terasa kredibel, spesifik untuk aviation, dan operasional.

---

## Slide 2 - Problem: Runway Operations Are Time-Critical

### Pesan Utama Slide
Air traffic controller harus membuat keputusan cepat sambil memantau banyak elemen bergerak dalam waktu bersamaan.

### Isi Slide
Controller perlu memantau:

- pesawat yang approach, landing, departure, atau taxi
- status runway aktif
- kendaraan bandara dan permintaan runway crossing
- cuaca dan visibility
- komunikasi radio dan readback
- flight strip dan status clearance
- koordinasi dengan ground, tower, approach, airport operations, dan emergency units

### Kalimat Kunci
**Ketika informasi tersebar di beberapa display, komunikasi voice, dan ingatan manusia, risiko konflik runway menjadi lebih sulit dikenali lebih awal.**

### Catatan Presentasi
Masalahnya bukan hanya jumlah pesawat. Workload dapat meningkat cepat ketika low visibility, kendaraan emergency, radio congestion, runway crossing, dan arrival sequencing terjadi bersamaan. Dalam kondisi seperti itu, controller harus menghubungkan timing pesawat, pergerakan kendaraan, dan status clearance dalam hitungan detik.

### Visual yang Disarankan
Diagram sederhana yang menunjukkan banyak sumber informasi masuk ke satu controller:

- aircraft track
- vehicle track
- radio call
- flight strip
- weather
- runway status

---

## Slide 3 - Evidence: Runway Conflict Is a Real Safety Issue

### Pesan Utama Slide
Konflik runway dan insiden terkait workload pernah terjadi dalam operasi nyata.

### Isi Slide
Gunakan 3 contoh kasus singkat:

| Kasus | Apa yang Terjadi | Relevansi untuk ATC FlowLens |
|---|---|---|
| LATAM Peru Flight 2213, Lima, 2022 | Pesawat bertabrakan dengan fire truck di runway saat takeoff roll. | Menunjukkan risiko konflik pesawat-kendaraan dan pergerakan kendaraan emergency dekat runway aktif. |
| Austin-Bergstrom, 2023 | Pesawat departure diberi clearance di runway saat pesawat lain berada di final approach dalam kondisi dense fog. | Menunjukkan bagaimana low visibility dan runway status awareness dapat mengurangi margin keselamatan. |
| LaGuardia, 2026 preliminary report/news | Fire truck runway crossing terjadi dekat dengan pesawat landing dalam high-workload environment. | Menunjukkan pentingnya time-to-conflict dan workload awareness. |

### Catatan Penting
Untuk kasus yang masih dalam investigasi, jangan menyimpulkan penyebab final. Gunakan kata seperti "preliminary information" atau "reported as a high-workload environment."

### Catatan Presentasi
Kasus-kasus tersebut menunjukkan pola umum: masalah runway safety jarang berasal dari satu faktor saja. Biasanya ada kombinasi tekanan waktu, komunikasi, pergerakan kendaraan, visibility, workload, dan shared awareness yang belum cukup kuat.

### Visual yang Disarankan
Visual timeline:

Aircraft on final/takeoff + vehicle entering/crossing runway = conflict window.

---

## Slide 4 - Gap: Current Systems Help, but Information Can Still Be Fragmented

### Pesan Utama Slide
ATC sudah memiliki teknologi penting, tetapi tantangannya adalah menghubungkan informasi tersebut menjadi satu gambaran operasional yang jelas.

### Isi Slide
Teknologi yang sudah ada:

- Radar / ADS-B / MLAT
- Surface surveillance
- Electronic flight strips
- A-SMGCS / RIMCAS / ASDE-X
- STCA / MTCD
- CPDLC / Data Comm
- SWIM dan flight data systems

### Gap yang Perlu Ditekankan
- Tidak semua bandara memiliki level surface surveillance dan conflict alerting yang sama.
- Voice communication masih banyak digunakan, terutama dalam operasi tower dan ground.
- Controller sering perlu menghubungkan status runway, clearance, timing pesawat, dan pergerakan kendaraan dari beberapa sumber terpisah.
- Alert akan lebih berguna jika explainable dan terhubung dengan timeline kejadian.

### Kalimat Kunci
**ATC FlowLens tidak dirancang untuk menggantikan sistem ATC tersertifikasi. Solusi ini adalah support, simulation, dan training layer yang membuat risiko runway lebih mudah dipahami.**

### Catatan Presentasi
Ide ini realistis karena tidak mengklaim mengotomatisasi ATC atau mengambil alih otoritas controller. Fokusnya adalah mendukung awareness, training, dan post-event review.

### Visual yang Disarankan
Layout dua kolom:

Kiri: Existing systems  
Kanan: Remaining gap  
Bawah: ATC FlowLens sebagai explainable support layer

---

## Slide 5 - Solution: ATC FlowLens

### Pesan Utama Slide
ATC FlowLens menyatukan pergerakan runway, status clearance, aktivitas kendaraan, komunikasi, dan risiko workload ke dalam satu dashboard.

### Definisi Utama
**ATC FlowLens adalah dashboard runway safety dan decision-support yang membantu tim air traffic mendeteksi risiko konflik runway, memahami workload controller, dan meninjau kejadian melalui timeline yang explainable.**

### Fitur Inti
- Runway occupancy monitoring
- Aircraft and vehicle tracking
- Clearance state engine
- Time-to-conflict calculation
- Explainable conflict alert
- Communication timeline
- Workload indicator
- Replay mode untuk training dan review

### Catatan Presentasi
Nilai utamanya adalah clarity. Sistem tidak hanya menampilkan alert, tetapi juga menjelaskan alasan alert muncul: pesawat mana, kendaraan mana, status clearance apa, estimasi waktu berapa, dan risiko overlap runway seperti apa.

### Visual yang Disarankan
Konsep mockup dashboard:

- kiri: airport map
- tengah: arrival/runway sequence
- kanan: alerts dan communication timeline
- atas: workload score

---

## Slide 6 - How It Works

### Pesan Utama Slide
Sistem mengubah data operasional simulasi menjadi insight risiko runway yang jelas.

### Input
- posisi, speed, phase, dan runway pesawat
- posisi, speed, status, dan route kendaraan
- layout runway dan taxiway
- status clearance
- communication log
- status weather dan visibility

### Processing
- runway occupancy model
- clearance state engine
- time-to-conflict calculation
- workload scoring
- severity classification
- alert explanation generator

### Output
- runway map dashboard
- conflict alert
- alasan di balik alert
- kategori recommended action
- workload indicator
- replay timeline

### Contoh Rule
```text
IF aircraft.status = "cleared_to_land"
AND aircraft.distance_to_threshold < 2 NM
AND vehicle.status = "cleared_to_cross"
AND vehicle.runway = aircraft.runway
AND vehicle_clear_time > aircraft_touchdown_time
THEN trigger HIGH runway conflict alert
```

### Catatan Presentasi
Untuk MVP hackathon, sistem dapat menggunakan data JSON simulasi. Ini membuat solusi feasible tanpa menggunakan data ATC asli yang sensitif, tetapi tetap menunjukkan logika dan value operasionalnya.

### Visual yang Disarankan
Diagram sederhana:

Inputs -> Processing Engine -> Dashboard and Alerts

---

## Slide 7 - MVP Scope and Demo Plan

### Pesan Utama Slide
MVP realistis untuk hackathon karena menggunakan simulasi, rule-based logic, dan skenario runway yang fokus.

### Komponen MVP
- satu layout bandara simulasi dengan runway dan taxiway
- tiga sampai lima pesawat simulasi
- satu atau dua kendaraan bandara
- clearance dan communication logs
- status weather atau visibility
- rule-based conflict detection
- time-to-conflict alerting
- workload scoring
- replay mode

### Skenario Demo
Contoh skenario:

1. Aircraft BAW123 berada di final approach dan cleared to land.
2. Vehicle ARFF-2 meminta atau menerima runway crossing clearance.
3. Sistem menghitung estimasi aircraft touchdown time dan vehicle runway clear time.
4. Konflik terdeteksi karena kendaraan berpotensi masih berada di runway saat pesawat tiba.
5. ATC FlowLens menampilkan alert, explanation, workload state, dan replay timeline.

### Prioritas Build Hackathon
Bangun dengan urutan:

1. simulation data model
2. runway map visualization
3. clearance state engine
4. conflict detection dan time-to-conflict
5. alert explanation
6. workload score
7. replay mode

### Catatan Presentasi
Scope ini kuat karena cukup sempit untuk dibangun, tetapi cukup lengkap untuk menunjukkan ide. Solusi tidak bergantung pada data aviation live dan fokus pada safety story yang jelas.

---

## Slide 8 - Target Users and Business Impact

### Pesan Utama Slide
Jalur adopsi awal yang paling realistis adalah training, simulation, dan safety awareness sebelum integrasi operasional nyata.

### Target Users
- tower controllers
- ground controllers
- approach controllers
- airport operation centers
- airport rescue and firefighting units
- ATC training centers
- aviation safety investigators

### Initial Market Positioning
**Platform simulation, training, dan runway safety awareness untuk bandara, sekolah penerbangan, Air Navigation Service Provider, dan tim operasi bandara.**

### Business / Operational Value
- meningkatkan kualitas training untuk skenario konflik runway
- mengurangi waktu untuk menjelaskan timeline insiden yang kompleks
- mendukung safety briefing dan after-action review
- membantu tim bandara memahami risiko pesawat-kendaraan
- menjadi entry point yang lebih rendah risiko sebelum masuk ke sistem operasional tersertifikasi
- membuka jalur pengembangan modul seperti speech-to-text, readback mismatch detection, dan workload analytics yang lebih kaya

### Mengapa Business Impact Penting
Walaupun MVP dimulai sebagai simulation tool, solusi ini tetap dapat menciptakan value untuk aviation education, safety training, dan operational readiness. Ini membuat solusi lebih realistis dibanding tool yang langsung mencoba menggantikan infrastruktur ATC tersertifikasi.

### Catatan Presentasi
Pasar awal yang realistis bukan operasi ATC live. Sertifikasi untuk sistem ATC operasional sangat ketat dan kompleks. Produk training dan simulation memiliki jalur adopsi yang lebih praktis sambil tetap menyelesaikan kebutuhan safety yang nyata.

---

## Slide 9 - Expected Impact and BUILD Indonesia Alignment

### Pesan Utama Slide
ATC FlowLens selaras dengan BUILD Indonesia karena menerapkan advanced technology pada tantangan keselamatan aerospace yang nyata.

### Expected Impact
- membantu pengguna mengenali risiko konflik runway lebih awal
- meningkatkan pemahaman interaksi pesawat dan kendaraan
- mendukung controller workload awareness
- membuat skenario training lebih mudah dijelaskan dan diputar ulang
- membantu safety team meninjau near-miss atau simulated incident
- berpotensi mengurangi go-around, taxi delay, holding, dan fuel burn yang tidak perlu pada versi operasional masa depan

### BUILD Indonesia Alignment
**Theme: Aerospace & Defense**  
Solusi membahas runway safety, workload air traffic control, dan kesiapan operasional bandara.

**Primary Focus Area: Advanced Technology and Innovation**  
Solusi menggunakan digital decision support, simulated tracking, conflict prediction, workload scoring, dan explainable alerting.

**Secondary Relevance: Social Impact and Sustainability**  
Operasi runway yang lebih aman melindungi penumpang, kru, ground staff, dan emergency units. Flow yang lebih baik juga dapat mendukung pengurangan delay dan fuel waste.

### Catatan Presentasi
Slide ini harus menghubungkan ide produk dengan kriteria hackathon. Tujuannya menunjukkan bahwa ide ini tidak hanya menarik secara teknis, tetapi juga relevan dengan ekosistem aviation Indonesia dan arah inovasi BUILD.

---

## Slide 10 - Roadmap and Closing

### Pesan Utama Slide
ATC FlowLens dimulai sebagai MVP hackathon yang feasible dan dapat berkembang menjadi platform aviation safety training yang lebih luas.

### Roadmap

**Phase 1 - Hackathon MVP**
- simulated runway map
- aircraft and vehicle movement
- clearance log
- time-to-conflict alert
- workload indicator
- replay timeline

**Phase 2 - Enhanced Prototype**
- speech-to-text untuk komunikasi bergaya ATC
- readback mismatch detection
- scenario generator yang lebih baik
- workload model yang lebih matang
- dukungan multi-runway

**Phase 3 - Future Vision**
- integrasi dengan dataset airport operation
- training simulator untuk koordinasi tower/ground
- safety analytics dashboard
- jalur riset menuju certified decision-support use

### Closing Line
**ATC FlowLens helps air traffic teams see runway risk before it becomes a runway incident.**

### Catatan Presentasi
Akhiri dengan pesan yang percaya diri tetapi tetap hati-hati: solusi ini tidak menggantikan controller; solusi ini membantu mereka berlatih, meninjau, dan memahami risiko runway lebih cepat.

---

# Appendix Data dan Supporting Material

Appendix digunakan sebagai bahan backup untuk Q&A, tidak harus masuk ke 10 slide utama.

## Appendix A - Referensi Kasus Nyata

| Incident | Date | Summary | Why It Matters |
|---|---:|---|---|
| LATAM Peru Flight 2213 | 18 Nov 2022 | Airbus A320neo bertabrakan dengan fire truck di runway saat takeoff roll di Lima. | Contoh kuat konflik runway antara pesawat dan kendaraan. |
| Austin-Bergstrom runway incursion | 4 Feb 2023 | Southwest aircraft diberi clearance takeoff saat FedEx aircraft berada di final approach dalam dense fog; FedEx melakukan go-around. | Menunjukkan masalah low visibility dan runway status awareness. |
| Linate Airport disaster | 8 Oct 2001 | Runway incursion dalam kondisi fog menyebabkan tabrakan antara Cessna dan SAS MD-87. | Menunjukkan risiko sistemik runway safety yang melibatkan visibility, prosedur, dan surveillance. |
| Uberlingen mid-air collision | 1 Jul 2002 | Collision yang melibatkan workload, system maintenance, dan conflict alert issues. | Menunjukkan pentingnya workload, safety nets, dan human-machine interface. |
| LaGuardia fire truck runway conflict | 22 Mar 2026 | Preliminary reports menyebut fire truck crossing dekat dengan landing aircraft dalam high-workload environment. | Contoh terbaru terkait runway crossing, workload, dan time pressure. |

Saran wording dalam deck: "These cases are used as safety context, not as claims that ATC FlowLens would have prevented them."

## Appendix B - Faktor Workload ATC

| Workload Factor | Example | Relevance |
|---|---|---|
| Traffic density | multiple arrivals and departures | meningkatkan monitoring dan communication load |
| Weather | fog, thunderstorm, wind shift | mengurangi visibility dan mengubah runway flow |
| Radio congestion | blocked transmission, repeated readback | meningkatkan communication workload |
| Runway crossing | aircraft atau vehicle crossing active runway | menciptakan risiko yang sensitif terhadap waktu |
| Emergency vehicle movement | fire truck, inspection vehicle | membutuhkan koordinasi cepat |
| Multiple displays | radar, surface map, strip, weather | meningkatkan visual dan cognitive load |
| Staffing/fatigue | short staffing, night shift | memengaruhi attention dan response time |

## Appendix C - Existing Technology Landscape

| Technology | Function | Relationship to ATC FlowLens |
|---|---|---|
| Radar | aircraft detection and tracking | possible future data source |
| ADS-B | aircraft position broadcast | possible simulation or public-data source |
| MLAT | position estimation from transponder signals | mendukung surveillance context |
| Surface surveillance | monitors runway/taxiway movement | core concept reference |
| Electronic flight strip | tracks flight and clearance information | terkait dengan clearance state engine |
| A-SMGCS | surface movement guidance and control | existing advanced surface safety system |
| RIMCAS/RMCA | runway incursion/conflict alert | existing safety net reference |
| STCA/MTCD | short/medium-term aircraft conflict detection | conflict prediction reference |
| CPDLC/Data Comm | digital ATC communication | future communication input |
| SWIM | aviation data sharing framework | future integration reference |

## Appendix D - Contoh Simulation Dataset

```json
{
  "aircraft": [
    {
      "callsign": "BAW123",
      "phase": "final",
      "runway": "27",
      "distance_nm": 1.8,
      "speed_kt": 145,
      "clearance": "cleared_to_land",
      "estimated_touchdown_sec": 42
    },
    {
      "callsign": "SIA456",
      "phase": "downwind",
      "runway": "27",
      "distance_nm": 9.8,
      "speed_kt": 180,
      "clearance": "continue_approach",
      "estimated_touchdown_sec": 260
    }
  ],
  "vehicles": [
    {
      "id": "ARFF2",
      "type": "fire_truck",
      "status": "cleared_to_cross",
      "runway": "27",
      "estimated_clear_time_sec": 58
    }
  ],
  "communications": [
    {
      "time": "18:42:11",
      "speaker": "Tower",
      "target": "BAW123",
      "message": "Cleared to land runway 27"
    },
    {
      "time": "18:42:18",
      "speaker": "Tower",
      "target": "ARFF2",
      "message": "Cross runway 27"
    }
  ],
  "weather": {
    "visibility": "low",
    "wind": "270/12",
    "condition": "fog"
  }
}
```

## Appendix E - Contoh Alert Output

```text
HIGH RUNWAY CONFLICT RISK

Aircraft: BAW123
Status: Cleared to land RWY 27
Estimated touchdown: 42 seconds

Vehicle: ARFF2
Status: Cleared to cross RWY 27
Estimated runway clear time: 58 seconds

Reason:
Vehicle clear time is later than aircraft touchdown time.
Predicted runway occupancy overlap: 16 seconds.

Suggested action category:
Hold vehicle / cancel crossing / consider go-around advisory if crossing has already started.
```

## Appendix F - Variabel Workload Score

Input workload scoring yang mungkin digunakan:

- active aircraft count
- active vehicle count
- radio calls in the last 5 minutes
- number of active clearances
- runway crossing requests
- low visibility or weather disruption
- active alerts
- emergency state
- runway configuration change

Ide scoring sederhana:

```text
workload_score =
  aircraft_count_weight
  + vehicle_count_weight
  + communication_load_weight
  + weather_risk_weight
  + active_alert_weight
  + emergency_weight
```

Level workload:

- Low: normal operation
- Medium: increased monitoring required
- High: multiple risk factors active
- Critical: conflict or emergency with limited reaction time

## Appendix G - Business Impact Framing

### Problem Owner
- airport operators
- ANSPs
- ATC training centers
- aviation academies
- airport safety teams

### Value Created
- pemahaman lebih cepat terhadap skenario runway yang kompleks
- training yang lebih baik untuk konflik pesawat-kendaraan
- incident replay dan explanation yang lebih mudah
- koordinasi yang lebih aman antara tower, ground, dan emergency units
- barrier yang lebih rendah untuk inovasi awal aviation safety melalui simulasi

### Adoption Path
1. training and simulation tool
2. safety briefing and scenario replay product
3. airport operation support prototype
4. research collaboration dengan ANSP atau sekolah penerbangan
5. eksplorasi masa depan menuju certified decision-support

### Possible Differentiation
ATC FlowLens berfokus pada explainability dan runway event timeline, bukan hanya alerting. Karena itu, solusi ini berguna untuk training, review, dan human understanding.

## Appendix H - Rekomendasi Tone Desain

Deck sebaiknya terasa:

- profesional
- spesifik untuk aviation
- jelas dan calm
- operasional, bukan terlalu futuristik
- percaya diri tetapi tidak berlebihan

Hindari klaim seperti:

- "automates ATC"
- "prevents all runway accidents"
- "replaces controllers"
- "real-time certified ATC system"

Gunakan wording yang lebih aman:

- "decision-support"
- "simulation-first"
- "training and safety awareness"
- "human-in-the-loop"
- "helps identify risk earlier"
- "supports clearer post-event review"

