# Research Subtopik Aerospace & Defense - BOEING BUILD Hackathon

Tanggal penyusunan: 31 Mei 2026  
Fokus: aerospace & defense, dengan penekanan pada solusi sipil, keselamatan, keberlanjutan, operasional, logistik, dan kesiapsiagaan. Untuk area defense, dokumen ini sengaja diarahkan ke use case non-ofensif seperti situational awareness, resiliensi, maintenance, supply chain, pelatihan, dan emergency response.

## Ringkasan Eksekutif

Industri aerospace & defense saat ini berada pada fase tekanan sekaligus peluang besar. Permintaan perjalanan udara kembali kuat, backlog pesawat tinggi, defense spending meningkat di banyak negara, dan teknologi seperti AI, IoT, digital twin, drone, advanced materials, serta sustainable aviation fuel (SAF) makin penting. Namun, industri juga menghadapi bottleneck besar: keterbatasan supply chain, kekurangan tenaga ahli, biaya manufaktur tinggi, tuntutan keselamatan dan sertifikasi yang ketat, risiko cybersecurity, serta tekanan dekarbonisasi.

Untuk hackathon, area yang paling realistis biasanya bukan membuat teknologi pesawat penuh dari nol, tetapi membuat lapisan digital yang membantu keputusan: dashboard, early warning system, optimizer, simulator, carbon calculator, drone coordination tool, maintenance intelligence, supplier risk scoring, atau training platform.

## 1. Advanced Technology and Innovation

### 1.1 IoT and Connectivity

#### Kondisi Saat Ini

Aerospace modern semakin terkoneksi. Pesawat, hanggar, fasilitas maintenance, bandara, drone, kendaraan ground support, dan komponen produksi dapat dipantau memakai sensor, edge device, cloud platform, dan jaringan komunikasi. Dalam pesawat, konektivitas juga berkembang untuk cabin system, operational data, predictive maintenance, dan inflight connectivity.

Di sisi industri, konektivitas menjadi dasar untuk digital transformation. Deloitte menyebut sektor aerospace & defense sedang mempercepat penggunaan teknologi digital dan AI untuk mengatasi masalah lama seperti supply chain visibility, workforce, dan produktivitas. Di sisi teknis, riset terbaru juga membahas 5G, satelit LEO, dan direct-to-device connectivity untuk mendukung komunikasi, navigasi, surveillance, dan operasi UAV.

#### Permasalahan yang Ada

- Data tersebar di banyak sistem: sensor, maintenance log, flight data, ERP, supplier system, dan dokumen teknis sering tidak saling terhubung.
- Cybersecurity meningkat risikonya karena modern aviation memakai cloud, operational technology, IoT, perangkat mobile, dan traditional IT secara bersamaan.
- Latensi dan reliabilitas koneksi masih menjadi tantangan untuk operasi kritis.
- Integrasi antar vendor sulit karena standar, format data, dan kepemilikan data berbeda.
- Untuk Indonesia, tantangan tambahan adalah konektivitas antarpulau, daerah terpencil, dan kondisi infrastruktur yang tidak merata.

#### Research yang Ada

- Riset connected aircraft cabin menyoroti konflik antara manfaat kolaborasi data IoT dan risiko privasi penumpang, intellectual property vendor, serta kepatuhan regulasi.
- Riset 5G berbasis satelit LEO untuk pesawat mengevaluasi strategi konektivitas berkelanjutan selama penerbangan.
- Riset direct-to-device untuk Communication, Navigation, and Surveillance (CNS) membahas bagaimana 5G dapat mendukung ATM dan UAS Traffic Management.
- ICAO dan materi aviation cybersecurity menekankan bahwa konektivitas memperluas attack surface, sehingga risk management harus mencakup IT, OT, IoT, cloud, dan mobile systems.

#### Opsi Ide Solusi

1. **Aircraft/Drone Health IoT Dashboard**  
   Dashboard yang mengumpulkan sensor suhu, getaran, tekanan, jam operasi, dan status baterai/mesin untuk memprediksi risiko kerusakan.

2. **Smart Hangar Asset Tracker**  
   Sistem pelacakan alat maintenance, komponen, dan teknisi menggunakan QR/RFID/BLE untuk mengurangi kehilangan alat dan mempercepat inspeksi.

3. **Connectivity Risk Monitor**  
   Aplikasi yang menilai reliabilitas koneksi untuk operasi drone atau ground support berdasarkan lokasi, cuaca, kepadatan jaringan, dan histori gangguan.

4. **Aviation IoT Cyber Risk Checklist Tool**  
   Tool sederhana untuk memetakan perangkat IoT, tingkat risiko, kepemilikan data, dan rekomendasi keamanan.

### 1.2 Future Factories: Robotics and Automation

#### Kondisi Saat Ini

Manufaktur aerospace sangat kompleks karena komponen harus presisi, ringan, kuat, traceable, dan memenuhi standar keselamatan tinggi. Industri mulai mempercepat smart manufacturing, robotics, AI quality inspection, digital work instruction, additive manufacturing, dan digital twin pabrik.

Tekanan utama datang dari kebutuhan meningkatkan produksi pesawat dan defense platform, sementara supply chain dan tenaga kerja masih terbatas. Laporan industri menyebut digital maturity di aerospace & defense meningkat pada 2024-2025 karena kompleksitas program, production ramp-up, fleet readiness, dan operational resilience.

#### Permasalahan yang Ada

- Human error di assembly dan quality inspection dapat berdampak besar.
- Inspeksi manual memakan waktu dan sulit diskalakan.
- Kekurangan tenaga ahli manufaktur dan teknisi.
- Robotik dan otomasi sulit diterapkan karena variasi komponen aerospace sangat tinggi.
- Sertifikasi proses manufaktur aerospace ketat, sehingga solusi baru perlu explainable dan traceable.

#### Research yang Ada

- Digital twin untuk maintenance dan operasi pesawat berkembang sebagai cara menyatukan data struktural, fungsional, behavioral, monitoring, lifecycle, dan environmental.
- Computer vision banyak diteliti untuk non-destructive inspection, defect detection, dan quality control material komposit.
- Additive manufacturing untuk aerospace diteliti karena dapat membuat komponen ringan dan kompleks, tetapi masih menghadapi tantangan certification, repeatability, dan material qualification.
- Robotics pada aerospace factory banyak diarahkan untuk drilling, riveting, composite layup, inspection, dan human-robot collaboration.

#### Opsi Ide Solusi

1. **Computer Vision Defect Detector**  
   Model visual untuk mendeteksi goresan, retak, delaminasi, atau ketidaksesuaian pada komponen simulasi.

2. **Digital Work Instruction for Technicians**  
   Aplikasi step-by-step assembly/inspection dengan checklist, foto bukti, dan validation rule.

3. **Factory Bottleneck Simulator**  
   Simulasi alur produksi untuk menemukan bottleneck mesin, tenaga kerja, atau komponen.

4. **Robotic Inspection Planner**  
   Tool yang menentukan rute inspeksi robot/drone kecil di hanggar atau pabrik berdasarkan prioritas risiko.

### 1.3 Digital Aviation Solution

#### Kondisi Saat Ini

Digital aviation mencakup flight operations, maintenance, crew scheduling, safety analytics, route optimization, customer operations, document management, dan decision support. Operator penerbangan membutuhkan data real-time untuk menekan delay, meningkatkan utilisasi pesawat, mengurangi fuel burn, dan menjaga keselamatan.

Riset digital twin dan predictive maintenance menjadi salah satu area paling aktif. Sistem ini menjanjikan keputusan maintenance yang lebih presisi, bukan hanya berbasis jadwal tetap.

#### Permasalahan yang Ada

- Delay dan gangguan operasional sering berasal dari kombinasi cuaca, maintenance, crew, gate, dan aircraft rotation.
- Maintenance tradisional bisa terlalu dini atau terlambat.
- Data keselamatan dan operasional sering sulit dianalisis lintas departemen.
- Banyak proses masih berbasis dokumen manual atau spreadsheet.
- Regulasi menuntut audit trail dan keandalan tinggi.

#### Research yang Ada

- Digital twin-based aircraft maintenance scheduling meneliti cara memakai representasi digital pesawat untuk menentukan jadwal maintenance lebih adaptif.
- Digital twin-based IVHM (Integrated Vehicle Health Management) menyoroti tantangan kurangnya run-to-failure data, ketidakpastian prediksi, dan gap antara desain dan maintenance.
- Riset AI predictive maintenance untuk aircraft systems membahas machine learning, fault prediction, dan digital twin sebagai pendekatan utama.
- Digital training twins diteliti untuk menghubungkan data maintenance dengan pelatihan teknisi.

#### Opsi Ide Solusi

1. **Predictive Maintenance MVP**  
   Menggunakan dataset sensor dummy untuk memprediksi Remaining Useful Life (RUL) komponen.

2. **Flight Delay Root-Cause Dashboard**  
   Dashboard yang menggabungkan faktor cuaca, aircraft rotation, maintenance, dan gate untuk menjelaskan penyebab delay.

3. **Fuel Efficiency Route Advisor**  
   Tool rekomendasi rute/altitude sederhana berdasarkan jarak, cuaca, dan estimasi fuel burn.

4. **Digital Aircraft Logbook**  
   Sistem pencatatan maintenance dan inspeksi berbasis role, timestamp, dan audit trail.

### 1.4 Supply Chain Intelligence

#### Kondisi Saat Ini

Supply chain aerospace masih menjadi salah satu hambatan terbesar industri. IATA melaporkan bottleneck aerospace supply chain tetap membatasi pertumbuhan maskapai, dengan aircraft availability sebagai salah satu constraint utama. IATA juga menyebut lebih dari 5.000 pesawat berada dalam storage untuk berbagai alasan, walaupun industri kekurangan pesawat baru. Studi IATA dan Oliver Wyman memperkirakan biaya bottleneck supply chain untuk airline industry melebihi USD 11 miliar pada 2025.

McKinsey juga mencatat OEM dan supplier kesulitan mendapatkan komponen seperti semikonduktor, casting, forging, serta material tertentu. Aerospace memiliki supply chain multi-tier yang kompleks, sering kali bergantung pada supplier terbatas untuk komponen kritis.

#### Permasalahan yang Ada

- Lead time komponen pesawat panjang dan sulit diprediksi.
- Keterbatasan visibility beyond tier-1 supplier.
- Risiko counterfeit parts dan kualitas material.
- Supplier kecil dapat menjadi single point of failure.
- Geopolitik, tarif, konflik, dan shortage tenaga kerja mempengaruhi pengiriman.
- Permintaan aftermarket dan produksi baru bisa bersaing untuk komponen yang sama.

#### Research yang Ada

- Laporan McKinsey dan Deloitte menekankan perlunya supply chain visibility, regional sourcing, procurement modernization, dan AI-enabled planning.
- IATA menyoroti aircraft availability dan bottleneck parts sebagai biaya besar bagi airline.
- Riset supply chain intelligence banyak mengarah ke risk scoring, demand forecasting, supplier network mapping, anomaly detection, dan digital thread.

#### Opsi Ide Solusi

1. **Supplier Risk Scoring Dashboard**  
   Menilai supplier berdasarkan lead time, lokasi, histori keterlambatan, criticality part, dan risiko geopolitik/cuaca.

2. **Spare Parts Inventory Optimizer**  
   Rekomendasi stok minimum untuk komponen kritis berdasarkan failure rate dan lead time.

3. **Counterfeit Parts Traceability Tool**  
   Sistem QR/blockchain-light untuk mencatat asal komponen, sertifikat, inspeksi, dan perpindahan.

4. **Aerospace Procurement Early Warning**  
   Early warning untuk komponen yang berpotensi terlambat dan alternatif supplier.

## 2. Social Impact

### 2.1 Community and Public Welfare

#### Kondisi Saat Ini

Teknologi aerospace dapat mendukung kesejahteraan publik melalui pemetaan bencana, search and rescue, distribusi bantuan, monitoring infrastruktur, konektivitas wilayah terpencil, dan disaster response. Drone, satelit, geospatial AI, dan komunikasi udara menjadi tools penting.

Indonesia sangat relevan untuk area ini karena kondisi geografis kepulauan, risiko bencana alam, daerah terpencil, dan kebutuhan distribusi logistik yang cepat.

#### Permasalahan yang Ada

- Daerah bencana sering sulit diakses karena jalan rusak, banjir, longsor, atau gempa.
- Data lapangan sering terlambat dan tidak lengkap.
- Koordinasi antar lembaga bisa lambat.
- Prioritas bantuan sulit ditentukan secara objektif.
- Operasi drone perlu memperhatikan izin, keselamatan, cuaca, baterai, dan no-fly zone.

#### Research yang Ada

- Review UAV-ground vehicle collaborative delivery menunjukkan emergency response mulai bergerak dari single-drone use case ke sistem kolaboratif multi-modal.
- Riset UAV untuk healthcare dan emergency services menunjukkan drone dapat meningkatkan response time untuk AED, darah, obat, dan search and rescue.
- Urban Air Mobility research membahas komunikasi, manajemen lalu lintas udara, keselamatan, dan sustainability sebagai syarat skala besar.

#### Opsi Ide Solusi

1. **Disaster Drone Mapping Dashboard**  
   Mengolah foto udara menjadi peta area terdampak, titik pengungsian, jalan terputus, dan prioritas bantuan.

2. **Aid Prioritization Engine**  
   Sistem scoring kebutuhan bantuan berdasarkan jumlah penduduk, akses jalan, jarak, tingkat kerusakan, dan stok logistik.

3. **SAR Mission Planner**  
   Perencana rute drone untuk search and rescue berdasarkan area, baterai, cuaca, dan probabilitas lokasi korban.

4. **Public Infrastructure Monitoring**  
   Deteksi kerusakan jembatan, jalan, tanggul, atau atap bangunan dari citra drone.

### 2.2 Medical Aid / Devices

#### Kondisi Saat Ini

Drone medical delivery menjadi salah satu use case aerospace dengan dampak sosial jelas. Teknologi ini dapat membawa darah, vaksin, obat, AED, sampel lab, atau alat kecil ke wilayah terpencil dan lokasi darurat. Riset 2025 menunjukkan UAV medical delivery berpotensi mengurangi response time dibanding kendaraan darat, terutama ketika akses jalan buruk.

Untuk Indonesia, peluangnya kuat pada pulau kecil, wilayah pegunungan, daerah bencana, dan distribusi darah/obat ke fasilitas kesehatan yang sulit dijangkau.

#### Permasalahan yang Ada

- Keterbatasan payload dan jarak tempuh drone.
- Cuaca tropis, angin, hujan, kelembapan, dan suhu dapat mempengaruhi kualitas muatan medis.
- Diperlukan cold chain untuk vaksin, darah, atau sampel tertentu.
- Regulasi penerbangan drone dan integrasi dengan airspace masih kompleks.
- Biaya awal, operasi, maintenance, dan acceptance dari tenaga medis menjadi tantangan.

#### Research yang Ada

- Riset Frontiers in Public Health tentang drone emergency medical delivery membahas dynamic airspace allocation dan optimasi multi-objective.
- Studi penerimaan tenaga medis terhadap drone delivery menyoroti faktor biaya, safety, policy support, kematangan teknologi, dan manajemen operasi.
- Review medical drones dari perspektif flight dynamics, guidance, navigation, and control menyoroti tantangan vibrasi, suhu, tekanan, dan kelembapan terhadap kualitas suplai medis.
- Riset blood delivery dengan drone menunjukkan kebutuhan model prioritas dinamis dan resiliensi saat demand berubah.

#### Opsi Ide Solusi

1. **Medical Drone Route Optimizer**  
   Menentukan rute tercepat dan aman untuk pengiriman darah/obat berdasarkan jarak, cuaca, baterai, dan urgency.

2. **Cold Chain Payload Monitor**  
   Sensor suhu dan kelembapan untuk memastikan obat/vaksin tetap aman selama penerbangan.

3. **Emergency AED Drone Dispatcher**  
   Simulasi dispatch drone AED ke pasien cardiac arrest dengan estimasi waktu tiba.

4. **Medical Drone Feasibility Calculator**  
   Tool untuk membandingkan biaya, waktu, dan emisi antara pengiriman darat dan drone.

### 2.3 Education and Skill Development

#### Kondisi Saat Ini

Aerospace & defense menghadapi shortage tenaga ahli. McKinsey dan AIA menyebut talent shortages dan attrition rate menjadi ancaman bagi pertumbuhan industri A&D, meskipun industri tumbuh kuat. Kebutuhan skill baru mencakup AI, data analytics, cybersecurity, digital manufacturing, maintenance digital twin, robotics, materials, dan systems engineering.

Pelatihan aerospace mahal karena membutuhkan alat, simulator, komponen asli, instruktur tersertifikasi, dan prosedur keselamatan.

#### Permasalahan yang Ada

- Kurikulum sering tertinggal dari perkembangan teknologi industri.
- Akses pelatihan aerospace tidak merata.
- Training hands-on mahal dan sulit dilakukan tanpa fasilitas khusus.
- Transfer knowledge dari senior technician ke junior tidak selalu terdokumentasi.
- Sertifikasi dan compliance membuat proses belajar harus akurat dan traceable.

#### Research yang Ada

- Digital twin-based maintenance training ecosystem diteliti untuk mensimulasikan prosedur maintenance dan diagnosis.
- Digital training twins menunjukkan gap antara potensi teknologi digital twin dan implementasi nyata dalam competence-based training.
- AR/VR training di aerospace banyak diteliti untuk mengurangi risiko, biaya, dan kebutuhan physical equipment.

#### Opsi Ide Solusi

1. **AR Aircraft Maintenance Trainer**  
   Simulasi prosedur inspeksi komponen pesawat dengan checklist dan scoring.

2. **AI Tutor for Aerospace Basics**  
   Tutor belajar aerodinamika, safety procedure, maintenance, dan material dengan quiz adaptif.

3. **Technician Skill Passport**  
   Platform pencatatan kompetensi, training, sertifikat, dan readiness teknisi.

4. **Digital Twin Training Scenario Generator**  
   Generator skenario kerusakan komponen untuk latihan diagnosis.

### 2.4 Urban / Rural Development

#### Kondisi Saat Ini

Aerospace technology dapat membantu pembangunan urban dan rural melalui pemetaan wilayah, monitoring infrastruktur, konektivitas, transportasi udara ringan, dan logistik ke daerah sulit. Drone dan citra satelit menjadi solusi murah untuk mapping, precision planning, dan monitoring.

Di Indonesia, relevansinya sangat tinggi karena banyak wilayah kepulauan, rural, dan rawan bencana yang membutuhkan data spasial dan logistik cepat.

#### Permasalahan yang Ada

- Pemetaan manual mahal dan memakan waktu.
- Infrastruktur rural sulit dimonitor secara rutin.
- Pengiriman barang penting ke wilayah terpencil sering lambat.
- Data perencanaan wilayah sering tidak real-time.
- Drone operation di area publik perlu manajemen keselamatan dan izin.

#### Research yang Ada

- Urban Air Mobility review menekankan komunikasi, traffic management, sustainability, dan safety sebagai fondasi.
- UAV emergency logistics research menunjukkan potensi integrasi drone dan kendaraan darat untuk wilayah yang sebagian aksesnya masih bisa dilalui.
- Geospatial AI berkembang untuk klasifikasi lahan, deteksi perubahan, dan monitoring infrastruktur.

#### Opsi Ide Solusi

1. **Rural Infrastructure Drone Survey**  
   Aplikasi untuk mencatat kondisi jalan, jembatan, sekolah, puskesmas, dan jaringan listrik dari citra drone.

2. **Air Logistics Feasibility Map**  
   Peta rekomendasi rute logistik udara kecil untuk daerah terpencil.

3. **Village Development Geospatial Dashboard**  
   Dashboard pemetaan kebutuhan fasilitas publik berbasis citra udara dan data demografi.

4. **Drone Operation Permit Helper**  
   Tool edukatif yang membantu operator memahami zona risiko dan checklist keselamatan.

## 3. Sustainability

### 3.1 Sustainable Aviation Fuel (SAF)

#### Kondisi Saat Ini

SAF dianggap sebagai salah satu pilar utama dekarbonisasi aviation karena pesawat jarak menengah-jauh masih sulit digantikan oleh baterai atau hidrogen dalam waktu dekat. ICAO dan IATA sama-sama menempatkan SAF sebagai bagian penting menuju net-zero aviation 2050.

Namun, produksi SAF global masih sangat kecil dibanding kebutuhan jet fuel. IATA memperkirakan produksi SAF 2025 hanya sekitar 0,6% dari total konsumsi jet fuel, naik menjadi sekitar 0,8% pada tahun berikutnya. World Economic Forum juga menekankan perlunya aksi cepat untuk mencapai target pengurangan carbon intensity jet fuel 5% pada 2030 dan net-zero international aviation pada 2050.

Di Indonesia, Pertamina/Kilang Pertamina Internasional mulai mengembangkan SAF berbasis used cooking oil (UCO). Pada 2025, Pertamina melakukan lifting/delivery batch awal SAF dari Cilacap untuk rute Jakarta-Denpasar oleh Pelita Air. Ini menunjukkan Indonesia mulai masuk ke ekosistem SAF, meskipun skalanya masih awal.

#### Permasalahan yang Ada

- SAF masih lebih mahal daripada jet fuel konvensional.
- Produksi dan feedstock terbatas.
- Supply chain feedstock harus diverifikasi agar benar-benar sustainable.
- Risiko greenwashing jika lifecycle emission tidak dihitung dengan benar.
- Infrastruktur blending, distribusi, sertifikasi, dan traceability masih berkembang.
- Untuk Indonesia, feedstock seperti used cooking oil, palm derivative, dan biomass perlu governance ketat agar tidak memicu masalah lahan, pangan, atau deforestasi.

#### Research yang Ada

- IATA membuat global feedstock assessment untuk melihat potensi SAF menuju 2050.
- ICAO mengembangkan framework dan roadmap untuk SAF, lower carbon aviation fuels, dan clean energy.
- IRENA membahas peluang SAF di Asia Tenggara, termasuk feedstock dan jalur produksi.
- Riset SAF 2025 menyoroti pathway seperti HEFA, Alcohol-to-Jet, Fischer-Tropsch, e-SAF, serta tantangan biaya dan ketersediaan.

#### Opsi Ide Solusi

1. **SAF Supply Chain Traceability Tool**  
   Melacak feedstock dari sumber, pengumpulan, pemrosesan, sertifikasi, hingga airline.

2. **Flight SAF Blend Optimizer**  
   Menghitung komposisi SAF optimal berdasarkan rute, availability, biaya, dan target emisi.

3. **SAF Lifecycle Emission Calculator**  
   Kalkulator emisi lifecycle berdasarkan jenis feedstock dan pathway produksi.

4. **Used Cooking Oil Collection Map**  
   Peta potensi pengumpulan minyak jelantah untuk SAF di wilayah urban.

### 3.2 Sustainability and Advanced Materials

#### Kondisi Saat Ini

Aerospace selalu membutuhkan material yang ringan, kuat, tahan panas, tahan korosi, dan aman. Material komposit, titanium, aluminum-lithium alloy, ceramic matrix composite, dan material hasil additive manufacturing menjadi penting untuk efisiensi fuel dan performa.

Tren sustainability mendorong material yang lebih ringan, tahan lama, mudah diperbaiki, dan memiliki lifecycle footprint lebih rendah. Namun, material aerospace harus melewati sertifikasi ketat.

#### Permasalahan yang Ada

- Material ringan sering mahal dan sulit diproduksi.
- Komposit sulit didaur ulang.
- Cacat kecil pada material dapat berdampak besar pada keselamatan.
- Traceability material harus sangat kuat.
- Supply material seperti titanium, forging, casting, dan semiconductor masih rentan shortage.

#### Research yang Ada

- Computer vision dan non-destructive testing untuk deteksi cacat komposit.
- Additive manufacturing untuk komponen ringan dan kompleks.
- Lifecycle assessment untuk material aerospace.
- AI material discovery untuk mencari komposisi material dengan trade-off terbaik antara kekuatan, berat, biaya, dan emisi.

#### Opsi Ide Solusi

1. **Material Selection Advisor**  
   Rekomendasi material berdasarkan berat, kekuatan, biaya, suhu kerja, dan sustainability score.

2. **Composite Defect Detection Demo**  
   Computer vision untuk mendeteksi retak/delaminasi dari gambar material.

3. **Material Lifecycle Passport**  
   Catatan digital asal material, proses produksi, inspeksi, perawatan, dan potensi recycling.

4. **Lightweighting Impact Calculator**  
   Menghitung dampak pengurangan berat terhadap fuel burn dan emisi.

### 3.3 Carbon Footprint Reduction

#### Kondisi Saat Ini

Aviation berkomitmen menuju net-zero carbon emissions pada 2050, tetapi jalannya sulit karena pertumbuhan demand penerbangan masih tinggi. Pengurangan emisi tidak hanya dari SAF, tetapi juga dari efisiensi operasional, route optimization, fleet renewal, air traffic management, airport energy, ground operations, dan carbon reporting.

Indonesia telah menyusun Action Plan to Reduce CO2 Emissions from Aviation 2025. Dokumen tersebut mencakup program efisiensi energi di bandara dan pemetaan/inventarisasi carbon footprint bandara.

#### Permasalahan yang Ada

- Data emisi tersebar di flight operation, fuel, maintenance, airport, dan ground support.
- Banyak organisasi belum punya carbon accounting yang otomatis dan audit-ready.
- Perhitungan emisi harus mempertimbangkan rute, jenis pesawat, fuel burn, load factor, ground operation, dan SAF blend.
- Pengurangan emisi sering bertabrakan dengan biaya dan keterbatasan operasional.

#### Research yang Ada

- ICAO dan CORSIA memberikan kerangka global untuk pengurangan dan pelaporan emisi aviation.
- EUROCONTROL dan SESAR menyoroti free-route airspace dan optimasi air traffic sebagai cara menghemat fuel.
- Studi carbon footprint aviation Indonesia, termasuk kasus Juanda International Airport, meneliti variabel rute, jarak, tipe pesawat, altitude, dan data dari banyak bandara.

#### Opsi Ide Solusi

1. **Aviation Carbon Footprint Dashboard**  
   Menghitung emisi per rute, pesawat, fuel, dan operasi bandara.

2. **Route Emission Optimizer**  
   Membandingkan beberapa rute berdasarkan jarak, cuaca, estimasi fuel burn, dan emisi.

3. **Airport Carbon Inventory Tool**  
   Tool untuk mencatat listrik, kendaraan ground support, HVAC, lighting, dan aktivitas operasional bandara.

4. **ESG Aviation Report Generator**  
   Membuat laporan ringkas emisi, tren, dan rekomendasi pengurangan.

### 3.4 Energy Optimization

#### Kondisi Saat Ini

Bandara, hanggar, pabrik aerospace, dan fasilitas defense mengonsumsi energi besar. Banyak fasilitas berjalan 24/7 dan memakai HVAC, lighting, mesin produksi, ground support equipment, charging system, data center, dan keamanan.

Energy optimization menjadi penting karena dapat langsung menurunkan biaya dan emisi tanpa menunggu teknologi pesawat baru. IoT, smart meter, AI forecasting, dan building management system dapat membantu.

#### Permasalahan yang Ada

- Konsumsi energi sulit dipantau granular per area atau mesin.
- Beban listrik fasilitas berubah berdasarkan jadwal penerbangan, maintenance, cuaca, dan produksi.
- HVAC sering menjadi salah satu beban terbesar.
- Peralatan lama tidak selalu punya sensor atau API.
- Optimasi harus tetap menjaga safety, comfort, dan compliance.

#### Research yang Ada

- Smart building dan AI energy management menggunakan sensor occupancy, cuaca, jadwal operasi, dan tariff forecasting.
- Airport energy efficiency menjadi bagian dari action plan CO2 aviation Indonesia.
- Digital twin facility dapat mensimulasikan konsumsi energi dan efek perubahan setting HVAC/lighting.

#### Opsi Ide Solusi

1. **Smart Hangar Energy Dashboard**  
   Monitoring energi per zona hanggar, HVAC, lighting, dan equipment.

2. **AI Load Forecasting for Airport Facility**  
   Prediksi beban listrik berdasarkan cuaca, jadwal penerbangan, dan jam operasional.

3. **HVAC Optimization Recommender**  
   Rekomendasi setting HVAC berbasis occupancy dan suhu luar.

4. **Ground Support Equipment Electrification Planner**  
   Simulasi biaya, emisi, dan kebutuhan charging untuk mengganti GSE berbahan bakar fosil.

## Rekomendasi Ide Paling Kuat untuk Hackathon

### 1. Predictive Aircraft Maintenance Dashboard

**Bidang:** IoT, Digital Aviation, Future Factories  
**Masalah:** maintenance mahal, downtime tinggi, data sensor sulit dimanfaatkan.  
**Solusi:** dashboard yang membaca data sensor dan memprediksi risiko failure/RUL.  
**Kenapa kuat:** sangat aerospace-relevant, mudah dibuat MVP dengan data simulasi, dan punya dampak bisnis jelas.

### 2. SAF Lifecycle and Supply Chain Tracker

**Bidang:** SAF, Carbon Reduction, Supply Chain Intelligence  
**Masalah:** SAF mahal, supply terbatas, traceability feedstock penting.  
**Solusi:** platform untuk melacak feedstock SAF, menghitung lifecycle emission, dan memverifikasi sustainability claim.  
**Kenapa kuat:** relevan dengan tren global dan konteks Indonesia karena Pertamina mulai mengembangkan SAF berbasis used cooking oil.

### 3. Disaster Drone Mission Planner

**Bidang:** Social Impact, Community Welfare, Urban/Rural Development  
**Masalah:** area bencana sulit diakses, data lapangan terlambat.  
**Solusi:** tool perencanaan rute drone untuk pemetaan, distribusi bantuan, dan search and rescue.  
**Kenapa kuat:** dampak sosial tinggi, cocok untuk Indonesia, dan demonstrasinya bisa dibuat lewat peta + simulasi.

### 4. Aerospace Supplier Risk Monitor

**Bidang:** Supply Chain Intelligence  
**Masalah:** bottleneck komponen pesawat menyebabkan biaya besar dan keterlambatan.  
**Solusi:** dashboard risk scoring supplier dan early warning keterlambatan.  
**Kenapa kuat:** masalahnya nyata, datanya bisa disimulasikan, dan sangat relevan dengan laporan industri 2025.

### 5. Smart Hangar Energy and Asset Tracker

**Bidang:** IoT, Energy Optimization, Maintenance  
**Masalah:** hanggar boros energi dan aset maintenance sulit dilacak.  
**Solusi:** dashboard gabungan energi, aset, dan status equipment.  
**Kenapa kuat:** MVP sederhana, manfaat operasional jelas, dan tidak membutuhkan hardware nyata untuk demo awal.

## Matriks Prioritas Hackathon

| Ide | Dampak | Feasibility MVP | Kekuatan Pitch | Risiko |
|---|---:|---:|---:|---|
| Predictive Aircraft Maintenance Dashboard | Tinggi | Tinggi | Tinggi | Butuh data simulasi yang meyakinkan |
| SAF Lifecycle and Supply Chain Tracker | Tinggi | Sedang | Tinggi | Perhitungan emisi harus hati-hati |
| Disaster Drone Mission Planner | Tinggi | Tinggi | Tinggi | Perlu peta/routing yang jelas |
| Aerospace Supplier Risk Monitor | Sedang-Tinggi | Tinggi | Tinggi | Data supplier asli sulit didapat |
| Smart Hangar Energy and Asset Tracker | Sedang | Tinggi | Sedang | Terlihat kurang aerospace jika narasi lemah |
| AR/VR Maintenance Trainer | Sedang-Tinggi | Sedang | Tinggi | Implementasi 3D/AR bisa memakan waktu |
| Medical Drone Route Optimizer | Tinggi | Sedang | Tinggi | Regulasi dan safety harus dijelaskan |

## Sumber Rujukan

- Deloitte, **2025 Aerospace and Defense Industry Outlook**: https://www.deloitte.com/us/en/insights/industry/aerospace-defense/aerospace-and-defense-industry-outlook/2025.html
- PwC, **Global aerospace & defense: Annual industry performance and outlook 2025**: https://www.pwc.com/us/en/industries/industrial-products/library/aerospace-defense-review-and-forecast.html
- IATA, **Aerospace Supply Chain Bottlenecks Continue to Constrain Airlines**: https://www.iata.org/en/pressroom/2025-releases/2025-12-09-02/
- McKinsey, **How severe is the aircraft shortage and what happens next?**: https://www.mckinsey.com/industries/travel/our-insights/how-severe-is-the-aircraft-shortage-and-what-happens-next
- McKinsey, **Addressing continued turbulence: The commercial-aerospace supply chain**: https://www.mckinsey.com/industries/aerospace-and-defense/our-insights/addressing-continued-turbulence-the-commercial-aerospace-supply-chain
- McKinsey, **Accelerating progress: Maximizing the return on talent in A&D**: https://www.mckinsey.com/industries/aerospace-and-defense/our-insights/accelerating-progress-maximizing-the-return-on-talent-in-a-and-d
- IATA, **Sustainable Aviation Fuel (SAF)**: https://www.iata.org/en/programs/sustainability/sustainable-aviation-fuels/
- IATA, **Global Feedstock Assessment for SAF Production Outlook to 2050**: https://www.iata.org/globalassets/iata/publications/sustainability/global-feedstock-assessment-for-saf-production-outlook-to-2050.pdf
- ICAO, **Environmental Report 2025**: https://www.icao.int/sites/default/files/environmental-protection/Documents/EnvironmentalReports/2025/Final-ENV-REPORT.pdf
- World Economic Forum, **Global Aviation Sustainability Outlook 2025**: https://www.weforum.org/publications/global-aviation-sustainability-outlook-2025/
- IRENA, **Sustainable Aviation Fuels in Southeast Asia**: https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2024/Dec/IRENA_Sustainable_aviation_fuel_Southeast_asia_2024.pdf
- Indonesia, **Action Plan to Reduce CO2 Emissions from Aviation 2025**: https://www.icao.int/sites/default/files/environmental-protection/Documents/ActionPlan/Indonesia-Action-Plan-2025-Final_published.pdf
- Hydrocarbon Engineering, **Kilang Pertamina delivers SAF**: https://www.hydrocarbonengineering.com/clean-fuels/13082025/kilang-pertamina-delivers-saf/
- SAF Investor, **Indonesia’s Pertamina delivers first batch of SAF**: https://www.safinvestor.com/news/148383/pertamina-saf/
- MDPI, **Ontology-Driven Digital Twin Framework for Aviation Maintenance and Operations**: https://www.mdpi.com/2227-7390/13/17/2817
- PHM Society, **Digital Twin-based IVHM for Predictive Maintenance**: https://papers.phmsociety.org/index.php/phmconf/article/view/4343
- MDPI, **Digital-Twin-Based Ecosystem for Aviation Maintenance Training**: https://www.mdpi.com/2078-2489/16/7/586
- MDPI, **Development of Digital Training Twins in the Aircraft Maintenance Ecosystem**: https://www.mdpi.com/1999-4893/18/7/411
- Frontiers in Public Health, **Multi-objective optimization model for dynamic airspace allocation of urban drones in medical emergency delivery**: https://www.frontiersin.org/articles/10.3389/fpubh.2025.1727647/full
- Frontiers in Public Health, **Study on medical professionals’ acceptance of and factors influencing drone delivery for medical supplies**: https://www.frontiersin.org/articles/10.3389/fpubh.2025.1571904
- MDPI Applied Sciences, **UAV-Ground Vehicle Collaborative Delivery in Emergency Response: A Review of Key Technologies and Future Trends**: https://www.mdpi.com/2076-3417/15/17/9803
- BMC Archives of Public Health, **Adopting drone technology for blood delivery**: https://archpublichealth.biomedcentral.com/articles/10.1186/s13690-025-01650-z
- arXiv, **A Systematic Literature Review of Unmanned Aerial Vehicles for Healthcare and Emergency Services**: https://arxiv.org/abs/2504.08834
- arXiv, **Urban Air Mobility: A Review of Recent Advances in Communication, Management, and Sustainability**: https://arxiv.org/abs/2510.18235
- arXiv, **Privacy-Preserving IoT in Connected Aircraft Cabin**: https://arxiv.org/abs/2511.15278
- arXiv, **Enabling Continuous 5G Connectivity in Aircraft through Low Earth Orbit Satellites**: https://arxiv.org/abs/2504.07262
- arXiv, **Direct-to-Device Connectivity for Integrated Communication, Navigation and Surveillance**: https://arxiv.org/abs/2603.11848
- ITS, **Analysis of Carbon Footprint in the Indonesian Aviation Industry, Case Study: Juanda International Airport**: https://scholar.its.ac.id/en/publications/analysis-of-carbon-footprint-in-the-indonesian-aviation-industry-/
