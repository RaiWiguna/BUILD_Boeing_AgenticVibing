# ATC Controller Workload Research

Tanggal penyusunan: 31 Mei 2026  
Konteks: BOEING BUILD Hackathon - Aerospace & Defense  
Fokus: controller workload, runway safety, airport surface movement, decision support system, dan peluang solusi digital aviation.

## Ringkasan Eksekutif

Air Traffic Control (ATC) adalah sistem manusia-teknologi yang bertugas menjaga keselamatan dan kelancaran lalu lintas udara. Salah satu risiko terbesar dalam operasi ATC adalah **controller workload**, yaitu beban kognitif dan operasional yang harus ditangani controller ketika mengelola pesawat, kendaraan bandara, runway, cuaca, komunikasi, dan situasi darurat secara bersamaan.

Topik ini sangat relevan dengan tema hackathon **Aerospace & Defense**, terutama pada subtopik:

- **Digital Aviation Solution**
- **Advanced Technology and Innovation**
- **IoT and Connectivity**
- **Social Impact**
- **Sustainability**, jika dikaitkan dengan pengurangan delay, holding, go-around, dan fuel burn

Problem yang paling kuat untuk hackathon adalah membangun sistem pendukung keputusan yang membantu ATC mendeteksi potensi konflik secara real-time, khususnya antara pesawat dan kendaraan di runway, tanpa mengambil alih otoritas manusia.

## 1. Apa Itu ATC dan Controller Workload

### 1.1 Definisi ATC

ATC atau **Air Traffic Control** adalah layanan yang mengatur pergerakan pesawat di udara dan di area bandara agar tetap aman, teratur, dan efisien. Dalam konteks lebih luas, ATC adalah bagian dari **ATM / Air Traffic Management**, yaitu sistem yang mengelola flow lalu lintas udara, ruang udara, runway, prosedur, komunikasi, navigasi, surveillance, dan koordinasi lintas wilayah.

ATC bertugas untuk:

- menjaga separation antar pesawat
- memberi clearance takeoff dan landing
- mengatur taxiing pesawat di darat
- mengatur runway crossing
- menangani pesawat emergency
- mengatur urutan arrival dan departure
- memantau cuaca
- mengoordinasikan handoff antar sektor
- berkomunikasi dengan pilot dan kendaraan bandara
- menjaga runway tetap aman dari konflik

### 1.2 Definisi Controller Workload

**Controller workload** adalah total beban kerja mental, komunikasi, visual, koordinasi, dan pengambilan keputusan yang dialami air traffic controller ketika menjalankan tugasnya.

Workload tidak hanya ditentukan oleh jumlah pesawat. Workload juga dipengaruhi oleh kompleksitas situasi. Satu situasi dengan sedikit pesawat dapat menjadi sangat berat jika ada cuaca buruk, emergency, komunikasi padat, runway crossing, atau sistem yang tidak lengkap.

### 1.3 Jenis Workload pada ATC

#### Cognitive Workload

Beban berpikir untuk memahami situasi, memprediksi pergerakan pesawat, menjaga separation, dan memilih instruksi yang tepat.

#### Communication Workload

Beban komunikasi radio dengan pilot, kendaraan ground, controller lain, supervisor, dan unit bandara.

#### Visual Workload

Beban memantau radar, layar surface movement, electronic flight strip, peta bandara, cuaca, runway, dan visual out-the-window dari tower.

#### Coordination Workload

Beban koordinasi antar posisi kerja seperti tower, ground, approach, area control, apron, airport operation, dan emergency response.

#### Decision Workload

Beban membuat keputusan dalam waktu singkat, khususnya saat konflik, runway incursion, go-around, rejected takeoff, atau emergency.

## 2. Mengapa Workload ATC Bisa Tinggi

### 2.1 Traffic Density

Semakin banyak pesawat di satu sektor atau terminal area, semakin tinggi kebutuhan monitoring, komunikasi, sequencing, dan separation. Namun jumlah pesawat bukan satu-satunya faktor. Dua sektor dengan jumlah pesawat sama dapat memiliki workload berbeda jika kompleksitas rute, altitude, speed, dan crossing point berbeda.

### 2.2 Airspace Complexity

Workload meningkat ketika ruang udara memiliki banyak:

- crossing route
- altitude change
- speed restriction
- restricted airspace
- military airspace
- holding pattern
- multiple runway operation
- mixed aircraft performance

### 2.3 Cuaca Buruk

Cuaca seperti thunderstorm, fog, low visibility, wind shear, turbulence, dan volcanic ash dapat menyebabkan rerouting, delay, holding, go-around, atau runway configuration change. Ini membuat controller harus menyesuaikan flow secara cepat.

### 2.4 Komunikasi Radio Padat

ATC masih sangat bergantung pada voice communication. Ketika frekuensi padat, risiko meningkat:

- instruksi tidak terdengar
- readback salah
- blocked transmission
- pilot/controller salah memahami clearance
- controller terlambat memberi instruksi

### 2.5 Runway dan Ground Movement

Di area bandara, controller harus memantau pesawat yang landing, pesawat yang takeoff, pesawat taxi, kendaraan ground, kendaraan pemadam, runway inspection, dan crossing request. Risiko tinggi muncul ketika kendaraan atau pesawat masuk runway aktif tanpa clearance yang tepat.

### 2.6 Staffing dan Fatigue

Short staffing, shift malam, overtime, dan waktu istirahat yang kurang dapat menurunkan alertness dan situational awareness. FAA menerbitkan laporan fatigue risk untuk operasi air traffic, dan isu staffing controller menjadi perhatian besar di Amerika Serikat.

### 2.7 Sistem yang Tidak Lengkap

Tidak semua bandara memiliki surface surveillance dan runway conflict alert system canggih. Jika tower tidak memiliki alat seperti ASDE-X, ASSC, A-SMGCS, atau RIMCAS, controller harus lebih bergantung pada visual observation dan komunikasi radio.

## 3. Teknologi ATC Saat Ini

### 3.1 Surveillance Technology

#### Primary Radar

Primary radar mendeteksi objek dengan pantulan sinyal radar. Kelebihannya adalah dapat mendeteksi objek tanpa transponder. Kekurangannya adalah informasi identitas dan altitude tidak sekaya secondary radar.

#### Secondary Surveillance Radar / Mode S

Secondary radar bekerja dengan transponder pesawat. Sistem ini dapat memberikan identitas, altitude, dan data lain dari pesawat.

#### ADS-B

**Automatic Dependent Surveillance-Broadcast** memungkinkan pesawat memancarkan posisi berbasis GPS, altitude, speed, dan identitas. ADS-B menjadi fondasi penting modernisasi surveillance karena lebih presisi dan dapat mendukung coverage yang lebih luas.

#### MLAT / Multilateration

MLAT menentukan posisi pesawat atau kendaraan dengan menghitung perbedaan waktu penerimaan sinyal transponder di beberapa receiver.

#### Surface Surveillance

Surface surveillance digunakan untuk memantau pergerakan pesawat dan kendaraan di runway, taxiway, dan apron. Ini penting untuk mencegah runway incursion.

### 3.2 Airport Surface Safety Technology

#### ASDE-X

**Airport Surface Detection Equipment, Model X** adalah sistem yang digunakan FAA untuk membantu controller mendeteksi potensi konflik di runway dan taxiway. ASDE-X menggabungkan data radar, multilateration, ADS-B, dan input lain untuk menampilkan posisi pesawat serta kendaraan di permukaan bandara.

#### ASSC

**Airport Surface Surveillance Capability** adalah sistem surface surveillance generasi lanjutan yang membantu meningkatkan situational awareness pada area bandara.

#### A-SMGCS

**Advanced Surface Movement Guidance and Control System** adalah konsep/sistem yang banyak digunakan dalam konteks ICAO dan EUROCONTROL. A-SMGCS membantu surveillance, routing, guidance, dan control untuk pesawat dan kendaraan di permukaan bandara.

#### RIMCAS / RMCA

**Runway Incursion Monitoring and Conflict Alert System** atau **Runway Monitoring and Conflict Alert** adalah safety net yang memberi alert ketika sistem mendeteksi potensi runway incursion atau konflik di runway.

#### Runway Status Lights

Runway Status Lights adalah sistem lampu otomatis yang memberi sinyal langsung kepada pilot atau driver kendaraan bahwa runway tidak aman untuk dimasuki atau digunakan.

#### Vehicle Movement Area Transponder

Kendaraan bandara dapat dipasangi transponder agar terlihat di sistem surface surveillance. Ini penting untuk kendaraan pemadam, inspection vehicle, maintenance vehicle, dan airport operation vehicle.

### 3.3 Decision Support Technology

#### STCA

**Short-Term Conflict Alert** memberi peringatan jika dua pesawat berpotensi kehilangan separation dalam waktu dekat.

#### MTCD

**Medium-Term Conflict Detection** membantu mendeteksi konflik beberapa menit ke depan berdasarkan trajectory.

#### Arrival Manager

Arrival Manager membantu mengurutkan pesawat yang akan mendarat agar flow lebih stabil dan efisien.

#### Departure Manager

Departure Manager membantu mengatur urutan pesawat yang akan berangkat.

#### Traffic Flow Management

Traffic Flow Management mengatur flow lalu lintas udara di level regional atau nasional agar kapasitas sektor dan bandara tidak overload.

#### Time-Based Flow Management

Time-Based Flow Management mengatur pesawat berdasarkan target waktu di titik tertentu sepanjang trajectory.

### 3.4 Digital Modernization

#### CPDLC / Data Comm

**Controller-Pilot Data Link Communication** memungkinkan instruksi tertentu dikirim secara digital berbasis teks, sehingga dapat mengurangi beban voice communication.

#### SWIM

**System Wide Information Management** adalah backbone data sharing untuk operasi ATM modern. SWIM memungkinkan data operasional seperti flight plan, weather, airport status, dan traffic flow dibagikan antar sistem.

#### PBN / RNAV / RNP

**Performance Based Navigation** memungkinkan rute lebih presisi berdasarkan kapabilitas navigasi pesawat. RNAV dan RNP membantu pesawat mengikuti jalur yang lebih efisien dan konsisten.

#### Trajectory Based Operations

Trajectory Based Operations mengelola penerbangan berdasarkan trajectory 4D: posisi lateral, altitude, dan waktu. Tujuannya adalah menggeser ATC dari reaktif menjadi lebih strategis dan prediktif.

#### Remote / Digital Tower

Remote tower memakai kamera, sensor, microphone, dan display digital untuk mengontrol bandara dari lokasi remote. Teknologi ini dapat membantu bandara kecil atau wilayah terpencil, tetapi tetap membutuhkan human factors dan safety assessment yang kuat.

#### AI dan Machine Learning

AI saat ini banyak diteliti untuk:

- conflict prediction
- workload estimation
- speech recognition ATC
- anomaly detection
- runway incursion prediction
- traffic flow optimization
- weather-aware routing
- decision recommendation

Namun dalam ATC, AI harus explainable, traceable, dan tidak boleh mengganggu otoritas controller.

## 4. Bagaimana Industri ATC Dijalankan di Dunia

### Level 1: ICAO / Global Standard

ICAO atau **International Civil Aviation Organization** membuat standar dan rekomendasi global untuk penerbangan sipil. ICAO tidak mengontrol pesawat secara langsung, tetapi menjadi dasar harmonisasi global.

Peran ICAO:

- standar air traffic services
- phraseology
- separation minima
- runway safety
- human performance
- fatigue management
- safety management system
- global air navigation plan
- framework modernisasi ATM

### Level 2: Regulator Nasional

Setiap negara memiliki regulator penerbangan sipil yang mengawasi keselamatan dan kepatuhan.

Contoh:

- Amerika Serikat: FAA
- Eropa: EASA untuk aviation safety regulation
- Indonesia: Direktorat Jenderal Perhubungan Udara
- Australia: CASA
- Kanada: Transport Canada

Regulator bertugas:

- menetapkan aturan nasional
- sertifikasi operator dan fasilitas
- oversight terhadap ANSP
- investigasi dan enforcement
- lisensi personel
- audit safety

### Level 3: ANSP / Air Navigation Service Provider

ANSP adalah organisasi yang menjalankan layanan navigasi udara. ANSP mengoperasikan controller, radar, komunikasi, prosedur, tower, dan sistem ATM.

Contoh ANSP:

- AirNav Indonesia
- FAA Air Traffic Organization
- NATS, Inggris
- DFS, Jerman
- ENAIRE, Spanyol
- NAV CANADA
- Airservices Australia
- DSNA, Prancis

### Level 4: Area Control Center / En-route Control

Area Control Center mengatur pesawat saat berada di cruise altitude atau terbang antar wilayah. Fokusnya adalah separation di ruang udara luas, handoff antar sektor, traffic flow, dan konflik lintas rute.

Karakteristik:

- wilayah udara luas
- pesawat berkecepatan tinggi
- jarak separation besar
- banyak handoff
- koordinasi antar sektor dan negara

### Level 5: Approach / Terminal Control

Approach control mengatur pesawat yang sedang mendekati atau meninggalkan bandara. Ini adalah salah satu area dengan workload tinggi karena pesawat berubah altitude, speed, heading, dan sequence.

Karakteristik:

- traffic padat
- altitude berubah cepat
- sequencing arrival
- spacing untuk final approach
- banyak komunikasi dengan tower dan area control
- sensitif terhadap cuaca dan runway configuration

### Level 6: Tower Control

Tower control mengatur takeoff, landing, runway occupancy, runway crossing, dan traffic di sekitar bandara.

Karakteristik:

- keputusan dalam hitungan detik
- harus memantau runway aktif
- koordinasi dengan ground control
- interaksi dengan kendaraan bandara
- risiko runway incursion tinggi

### Level 7: Ground / Apron / Ramp Control

Ground control mengatur taxiway, pushback, crossing, dan pergerakan di darat. Apron/ramp control sering kali dikelola airport operator, tergantung negara dan bandara.

Karakteristik:

- banyak kendaraan dan pesawat bergerak lambat
- kompleksitas layout bandara
- risiko salah taxi route
- risiko masuk runway aktif
- komunikasi padat antara pilot, ground vehicle, dan apron unit

### Level 8: UTM / Drone Traffic Management

UTM atau **UAS Traffic Management** adalah sistem yang sedang berkembang untuk mengatur drone, eVTOL, advanced air mobility, dan operasi rendah-altitude.

Tantangan UTM:

- integrasi dengan ruang udara konvensional
- identifikasi drone
- geofencing
- detect-and-avoid
- route deconfliction
- emergency drone operation
- regulasi yang belum seragam antar negara

## 5. Kasus Akibat Workload, Task Saturation, atau Gagal Situational Awareness

### 5.1 LATAM Perú Flight 2213 - Lima, 18 November 2022

#### Ringkasan

LATAM Perú Flight 2213, Airbus A320neo, sedang melakukan takeoff roll di Jorge Chávez International Airport, Lima, Peru. Pada saat yang sama, beberapa kendaraan pemadam bandara sedang menjalankan latihan emergency response. Salah satu kendaraan masuk ke runway aktif dan bertabrakan dengan pesawat.

#### Dampak

- Pesawat rusak berat.
- Semua penumpang dan kru berhasil dievakuasi.
- Dua firefighter meninggal saat kejadian.
- Satu firefighter lain meninggal kemudian akibat luka.
- Puluhan penumpang mengalami cedera.

#### Faktor Masalah

Investigasi menyebut kendaraan rescue masuk runway tanpa explicit authorization dari tower. Kasus ini menunjukkan kegagalan koordinasi antara airport operator, rescue team, dan ATC.

Faktor yang relevan dengan workload:

- latihan emergency response dilakukan dekat operasi runway aktif
- koordinasi prosedur tidak cukup jelas
- clearance runway tidak dipahami seragam
- komunikasi antara unit ground dan tower tidak efektif
- sistem safety net tidak cukup mencegah incursion

#### Pelajaran

Runway safety membutuhkan integrasi antara clearance, tracking kendaraan, status runway, dan alert yang mudah dipahami. Fire truck atau kendaraan emergency harus terlihat jelas di sistem surface surveillance dan tidak boleh bergantung hanya pada asumsi prosedural.

### 5.2 LaGuardia Fire Truck Collision - New York, 22 Maret 2026

#### Ringkasan

Menurut laporan awal NTSB yang diberitakan AP, sebuah fire truck diberi clearance untuk menyeberangi runway saat pesawat Air Canada Express/Jazz sudah mendekati pendaratan di LaGuardia Airport. Clearance kepada fire truck diberikan hanya beberapa detik sebelum touchdown.

#### Catatan Penting

Investigasi masih berjalan, sehingga penyebab final belum boleh disimpulkan. Namun NTSB menyebut lingkungan operasi sebagai **heavy workload environment**.

#### Faktor Masalah yang Relevan

- hanya sedikit waktu antara clearance kendaraan dan touchdown pesawat
- controller harus memantau arrival, runway, dan kendaraan ground sekaligus
- runway crossing vehicle menciptakan konflik dengan landing aircraft
- situasi membutuhkan alert yang sangat cepat dan jelas

#### Pelajaran

Sistem pendukung ATC harus mampu memperingatkan controller ketika ada konflik antara aircraft cleared to land dan vehicle cleared to cross. Alert harus muncul sebelum time-to-conflict terlalu kecil.

### 5.3 Austin-Bergstrom Runway Incursion - 4 Februari 2023

#### Ringkasan

Southwest Airlines Boeing 737 mendapat clearance takeoff dari runway yang sama ketika FedEx Boeing 767 sedang final approach. Kondisi saat itu dense fog. FedEx melakukan go-around dan konflik berhasil dihindari.

#### Faktor Masalah

NTSB menyebut controller tidak dapat melihat Southwest di runway/taxiway karena kabut tebal. Tower juga tidak memiliki surface detection equipment untuk membantu memantau ground traffic.

#### Pelajaran

Low visibility dapat membuat tower kehilangan kemampuan visual. Tanpa surface detection equipment, controller harus mengandalkan radio dan prosedur, sehingga workload dan risiko meningkat.

### 5.4 Überlingen Mid-Air Collision - 1 Juli 2002

#### Ringkasan

Bashkirian Airlines Tu-154 dan DHL Boeing 757 bertabrakan di udara di wilayah Überlingen, Jerman. Kecelakaan menewaskan 71 orang.

#### Faktor Masalah

Investigasi menemukan beberapa faktor sistemik pada layanan ATC, termasuk controller yang menangani dua workstation, sistem yang sedang maintenance, dan conflict alert yang tidak efektif pada saat kritis.

#### Relevansi dengan Workload

Kasus ini sering dijadikan contoh bagaimana workload, staffing, maintenance sistem, dan prosedur yang ambigu dapat bergabung menjadi accident chain.

#### Pelajaran

ATC tidak boleh bergantung pada satu manusia yang menangani terlalu banyak fungsi kritis. Safety net harus resilient dan tetap bekerja saat sistem lain sedang maintenance.

### 5.5 Linate Airport Disaster - Milan, 8 Oktober 2001

#### Ringkasan

Dalam kondisi kabut tebal, sebuah Cessna masuk runway aktif dan bertabrakan dengan SAS MD-87 yang sedang takeoff di Bandara Linate, Italia.

#### Faktor Masalah

Bandara beroperasi tanpa ground radar yang berfungsi. Low visibility, signage/marking, prosedur, dan surface surveillance menjadi faktor penting dalam accident chain.

#### Pelajaran

Runway incursion bukan hanya kesalahan individu. Ini adalah masalah sistem: layout, signage, visibility, ground radar, komunikasi, dan prosedur harus saling mendukung.

## 6. Pola Umum dari Kasus-Kasus ATC Workload

Dari berbagai kasus, pola yang berulang adalah:

- controller harus mengambil keputusan dalam waktu sangat singkat
- informasi kritis tersebar di banyak sumber
- komunikasi radio dapat ambigu atau padat
- visibility rendah memperburuk situational awareness
- kendaraan ground sering menjadi risiko tinggi di runway
- sistem alert tidak selalu tersedia atau cukup cepat
- staffing dan fatigue dapat mempersempit margin keselamatan
- latihan emergency atau operasi non-rutin meningkatkan risiko
- prosedur bisa dipahami berbeda oleh unit berbeda

## 7. Peluang Solusi Hackathon

### 7.1 Problem Statement

Air traffic controller harus menjaga keselamatan runway dan separation di lingkungan yang kompleks, padat, dan sering berubah. Namun informasi tentang pesawat, kendaraan, clearance, cuaca, dan status runway sering tersebar di berbagai sistem. Dibutuhkan sistem pendukung keputusan yang dapat mendeteksi konflik secara real-time, menjelaskan alasan alert, dan memberi rekomendasi tanpa mengambil alih otoritas controller.

### 7.2 Usulan Solusi

**Explainable ATC Workload and Runway Conflict Assistant**

Sistem digital untuk membantu controller memantau runway, aircraft, ground vehicle, dan clearance secara real-time. Sistem memberi alert jika ada potensi konflik, menghitung time-to-conflict, dan menjelaskan alasan rekomendasi.

### 7.3 Fitur MVP

#### Runway Occupancy Monitor

Menampilkan status runway:

- clear
- occupied by aircraft
- occupied by vehicle
- crossing requested
- landing inbound
- takeoff roll
- emergency operation

#### Aircraft and Vehicle Tracking

Melacak posisi pesawat dan kendaraan di peta bandara simulasi.

#### Clearance State Engine

Menyimpan status clearance:

- cleared to land
- cleared for takeoff
- cleared to cross runway
- hold short
- line up and wait
- go around
- rejected takeoff

#### Conflict Prediction

Menghitung apakah aircraft dan vehicle akan berada pada runway yang sama dalam window waktu berbahaya.

#### Time-to-Conflict Alert

Contoh alert:

> Conflict predicted in 18 seconds: Vehicle ARFF-2 crossing RWY 04 while Aircraft AC8646 is cleared to land.

#### Explainable Recommendation

Sistem tidak hanya menampilkan alarm, tetapi menjelaskan:

- aircraft already cleared to land
- aircraft distance to threshold
- vehicle speed
- runway crossing incomplete
- estimated time-to-conflict
- severity level

#### Controller Workload Score

Mengestimasi workload berdasarkan:

- jumlah aircraft aktif
- jumlah vehicle aktif
- jumlah clearance dalam 5 menit terakhir
- jumlah radio calls
- cuaca
- visibility
- runway configuration
- emergency state

#### After-Action Replay

Replay timeline untuk training dan investigasi:

- kapan clearance diberikan
- kapan kendaraan masuk runway
- kapan pesawat mendekat
- kapan alert muncul
- apa rekomendasi sistem

### 7.4 Kenapa Solusi Ini Kuat untuk Hackathon

- Problem nyata dan berdampak langsung pada keselamatan.
- Ada kasus nyata yang mudah dijadikan latar belakang.
- MVP dapat dibuat dengan simulasi data tanpa integrasi ATC asli.
- Teknologi yang digunakan relevan: AI/rule engine, IoT tracking, dashboard, geospatial visualization, real-time alerting.
- Explainability membuat solusi lebih cocok untuk domain safety-critical.
- Bisa dikaitkan dengan sustainability karena mencegah go-around, delay, dan fuel burn.

## 8. Rancangan Arsitektur MVP

### 8.1 Input Data

- posisi pesawat
- posisi kendaraan
- runway geometry
- taxiway geometry
- flight phase
- clearance status
- speed dan heading
- weather/visibility
- airport operation status

### 8.2 Processing Layer

- rule-based conflict detection
- time-to-conflict calculation
- runway occupancy logic
- workload scoring
- severity classification
- recommendation generator

### 8.3 Output

- dashboard runway
- alert panel
- explanation panel
- recommended action
- timeline replay
- workload indicator

## 9. Contoh Rule Sederhana

```text
IF aircraft.status = "cleared_to_land"
AND aircraft.distance_to_threshold < 2 NM
AND vehicle.status = "cleared_to_cross"
AND vehicle.runway = aircraft.runway
AND estimated_vehicle_clear_time > estimated_aircraft_touchdown_time
THEN trigger HIGH severity runway conflict alert
```

```text
IF aircraft.status = "takeoff_roll"
AND vehicle.position intersects active_runway_protected_area
THEN trigger CRITICAL runway incursion alert
```

```text
IF controller.active_aircraft > threshold
AND radio_calls_last_5_min > threshold
AND visibility = "low"
THEN increase workload score
```

## 10. Risiko dan Batasan

### Safety-Critical Domain

Solusi hackathon tidak boleh diposisikan sebagai pengganti ATC. Solusi harus diposisikan sebagai decision-support dan training/simulation tool.

### Data Real ATC Sulit Diakses

Data real runway movement dan clearance sulit didapat karena sensitif. Untuk MVP, gunakan data simulasi, ADS-B publik untuk pesawat di udara, atau skenario replay.

### False Alarm

Terlalu banyak alert dapat menyebabkan alert fatigue. Sistem harus punya severity level dan explanation yang jelas.

### Human Factors

Interface tidak boleh membuat controller makin sibuk. UI harus singkat, jelas, dan tidak memaksa controller membaca banyak teks saat situasi kritis.

### Regulasi

ATC adalah domain yang sangat diatur. Implementasi nyata membutuhkan sertifikasi, validation, dan human-in-the-loop testing.

## 11. Positioning untuk Pitch

### Nama Ide

**RunwayShield AI**  
atau  
**ATC Guardian: Explainable Runway Conflict Assistant**

### One-Liner

An explainable decision-support system that helps air traffic controllers detect runway conflicts between aircraft and ground vehicles before they become accidents.

### Value Proposition

- meningkatkan situational awareness controller
- mengurangi risiko runway incursion
- membantu training ATC dan airport ground crew
- memberi alert yang explainable
- mendukung digital aviation safety

### Target Pengguna

- airport tower controller
- ground controller
- airport operation center
- rescue and firefighting unit
- ATC training center
- aviation safety investigator

### Demo Hackathon

Demo dapat berupa simulasi bandara dengan:

- satu runway
- aircraft inbound
- aircraft takeoff
- fire truck crossing
- clearance log
- alert engine
- workload indicator
- replay mode

## 12. Sumber Rujukan

- FAA, **Next Generation Air Transportation System (NextGen)**: https://www.faa.gov/nextgen/
- FAA, **NextGen Overview**: https://www.faa.gov/newsroom/nextgen
- FAA, **SWIM Program Overview**: https://www.faa.gov/air_traffic/technology/swim/overview
- FAA, **Enhancing Surface Safety: Vehicle Movement Area Transponders**: https://www.faa.gov/airports/runway_safety/airfield_drivers/enhancing-surface-safety-guide-vehicle-movement-area
- FAA, **Assessing Fatigue Risk in FAA Air Traffic Operations**: https://www.faa.gov/newsroom/media/Fatigue_Report.pdf
- EUROCONTROL, **Advanced Surface Movement Guidance and Control System**: https://www.eurocontrol.int/service/advanced-surface-movement-guidance-and-control-system
- EUROCONTROL, **Human Performance Neurometrics Toolbox for Highly Automated Systems Design**: https://www.eurocontrol.int/project/human-performance-neurometrics-toolbox-highly-automated-systems-design
- EUROCONTROL, **Task Load Generated by Frequent Sector Changes for Aircrews and Controllers**: https://www.eurocontrol.int/publication/task-load-generated-frequent-sector-changes-aircrews-and-controllers-state-art
- ICAO, **Human Performance**: https://www.icao.int/operational-safety/hp
- ICAO, **Global Air Navigation Plan**: https://www.icao.int/airnavigation/Pages/GANP-Resources.aspx
- SKYbrary, **ASDE-X**: https://skybrary.aero/index.php/articles/airport-surface-detection-equipment-model-x-asde-x
- SKYbrary, **A-SMGCS**: https://skybrary.aero/index.php/articles/advanced-surface-movement-guidance-control-system-smgcs
- SKYbrary, **RIMCAS**: https://skybrary.aero/index.php/articles/runway-incursion-monitoring-and-conflict-alert-system-rimcas
- NTSB, **Austin-Bergstrom Runway Incursion Investigation DCA23FA149**: https://www.ntsb.gov/investigations/pages/DCA23FA149.aspx
- AP News, **LaGuardia Fire Truck Collision Preliminary Information**: https://apnews.com/article/33073747e410c8d7bceab0ebc347d35f
- Aviation Safety Network, **LATAM Perú Flight 2213**: https://asn.flightsafety.org/database/record.php?id=20221118-1
- Aviation Accidents, **LATAM Peru Airbus A320N Flight LPE2213**: https://www.aviation-accidents.net/latam-peru-airbus-a320n-cc-bhb-flight-lpe2213/
- ScienceDirect, **The Überlingen accident: Macro-level safety lessons**: https://www.sciencedirect.com/science/article/pii/S0925753507001567
- University of Glasgow, **Modeling the Linate Runway Incursion**: https://www.dcs.gla.ac.uk/~johnson/papers/HCIAero2006/Linate.pdf
