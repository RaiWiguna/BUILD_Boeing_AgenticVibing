# Bahan Penyampaian kepada Mentor

## Riset kondisi operasional ATC dan rencana pengembangan ATC FlowLens

- **Tanggal acuan riset:** 30 September 2026
- **Tujuan dokumen:** naskah lisan, penjelasan istilah teknologi, persiapan tanya jawab, dan arahan pengembangan.
- **Peran dokumen:** materi komunikasi untuk mentor, bukan spesifikasi software atau inventaris status source terkini.

Dokumen ini merangkum [Laporan Riset Kondisi Operasional ATC dan Kelayakan ATC FlowLens](ATC_FlowLens_Operational_Reality_Research.md). Klaim tentang sistem nyata ditautkan ke sumber publiknya. Contoh angka pada demo FlowLens tetap berstatus simulasi. Ketiadaan bukti publik tidak boleh dibaca sebagai bukti bahwa suatu sistem tidak ada. Untuk status source repository, lihat [Status Implementasi](../IMPLEMENTATION_STATUS.md).

## 1. Pesan utama

**Posisi yang disarankan:** ATC FlowLens adalah simulator dan alat replay untuk membantu latihan dan debrief skenario runway. Sistem menampilkan hubungan antara pergerakan, instruksi, dan waktu berdasarkan data simulasi atau data berizin. FlowLens tidak mengeluarkan clearance, tidak menggantikan controller, dan belum divalidasi untuk operasi ATC nyata.

**Status dalam briefing per 30 September 2026:** konsep dan MVP simulasi. Brief ini bukan audit source code. Belum ada bukti di dalamnya bahwa FlowLens telah digunakan, diuji oleh controller, disertifikasi, atau terhubung ke sistem ATC nyata.

**Arah pengembangan:** mulai dari simulasi offline yang dapat dijelaskan; validasi bersama instruktur; riset dengan data mitra yang berizin; sandbox read-only bila ada kebutuhan dan sponsor; integrasi operasional hanya sebagai kemungkinan jangka panjang setelah persetujuan serta safety case yang sesuai.

## 2. Naskah lisan untuk mentor

*Durasi sekitar empat menit. Teks sumber dalam kurung siku menjadi catatan presenter dan tidak wajib dibacakan.*

Selamat pagi/siang, Pak/Bu. Kami ingin menyampaikan hasil riset kondisi operasional ATC dan bagaimana temuan tersebut memengaruhi arah pengembangan ATC FlowLens.

Tujuan riset ini adalah memastikan FlowLens dirancang berdasarkan kondisi dan batas nyata di lapangan, bukan asumsi bahwa semua bandara menggunakan teknologi, prosedur, dan akses data yang sama. Riset kami mencakup dokumen internal dan sumber publik sampai 30 September 2026. Untuk tahap ini, FlowLens masih merupakan konsep dan MVP simulasi. Kami belum mengklaim bahwa produk ini telah digunakan, diuji, disertifikasi, atau terhubung dengan operasi ATC nyata.

Temuan pertama, ekosistem ATC Indonesia sudah memakai teknologi digital dan surveillance pada layanan serta fasilitas tertentu. Laporan Ditjen Perhubungan Udara tahun 2024 mencatat 50 unit ADS-B dan dua fasilitas cadangan ATSA di Budiarto dan Sultan Hasanuddin. AirNav juga mengumumkan New ATMAS di New JATSC dengan sejumlah fungsi surveillance, komunikasi data, dan safety net. Bukti tersebut berlaku untuk sistem dan lokasi yang disebut sumber; bukti itu tidak membuktikan bahwa seluruh bandara mempunyai cakupan atau fasilitas permukaan yang sama. [Laporan Tahunan DJPU 2024](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf) · [AirNav: New JATSC/New ATMAS](https://www.airnavindonesia.co.id/berita-dan-siaran-pers/kunjungi-airnavindonesia-presiden-icao-tinjau-langsung-fasilitas-new-jatsc/)

Temuan kedua, beberapa sistem keselamatan permukaan sudah menjadi contoh implementasi di lokasi tertentu di luar negeri. FAA melaporkan ASDE-X di 35 bandara dan RWSL di 20 bandara. FAA juga menyebut program Surface Awareness Initiative dengan sasaran hingga 220 bandara bertower pada 2028; angka itu adalah sasaran program, bukan jumlah sistem yang sudah beroperasi. Pembanding global ini membantu memahami arah teknologi, tetapi tidak dapat dianggap sebagai gambaran deployment di Indonesia. [FAA ASSC/ASDE-X](https://www.faa.gov/air_traffic/technology/adsb/atc/assc) · [FAA RWSL](https://www.faa.gov/air_traffic/technology/rwsl/index.cfm?print=go) · [FAA Surface Awareness Initiative](https://www.faa.gov/airports/runway_safety/airfield_drivers/enhancing-surface-safety-guide-vehicle-movement-area)

Temuan ketiga, akses data adalah persoalan tersendiri. Track pesawat, data flight plan, clearance, rekaman radio, status runway, dan posisi kendaraan dapat berada pada pemilik serta sistem yang berbeda. Keberadaan informasi atau teknologi tidak otomatis memberi FlowLens izin untuk mengambil, menyimpan, atau menggunakannya. Karena itu, demo kami perlu membedakan data sintetis, data historis, data manual, dan data operasional yang benar-benar diotorisasi.

Berdasarkan temuan tersebut, posisi produk yang paling realistis sekarang adalah simulator dan alat replay untuk latihan serta debrief. FlowLens dapat menunjukkan urutan event, menghubungkan pergerakan dengan instruksi yang ditulis atau diverifikasi, dan membantu instruktur meninjau skenario. Sistem tidak mengeluarkan clearance dan keputusan keselamatan tetap berada pada manusia.

Kami juga ingin memperjelas contoh demo: skenario BAW123 dan ARFF-2 di RWY 27, termasuk touchdown 42 detik, kendaraan clear 58 detik, dan overlap 16 detik, adalah simulasi. Angka itu bukan data operasi bandara atau performa sensor nyata. Label seperti “high risk” belum menjadi tingkat risiko operasional yang tervalidasi. Untuk demo, kami akan menjelaskan pemicu event sebagai aturan simulasi beserta asumsi yang digunakan.

Alur pengembangan yang kami usulkan memiliki lima tahap. Pertama, MVP offline dengan satu layout fiktif, pergerakan sintetis, event yang ditentukan, dan replay yang dapat diulang. Kedua, pilot latihan bersama instruktur untuk meninjau kebenaran skenario dan kegunaan debrief. Ketiga, pilot riset yang memakai satu jenis data mitra yang diizinkan, misalnya log simulator atau track historis yang dide-identifikasi. Keempat, bila ada sponsor dan kebutuhan nyata, kami dapat mengevaluasi sandbox read-only untuk informasi non-safety-critical. Kelima, integrasi operasional hanya menjadi kemungkinan setelah melalui persetujuan, evaluasi keselamatan, faktor manusia, keamanan, dan proses perubahan yang berlaku.

Untuk MVP, kami mengusulkan lima prioritas: timeline replay dengan sumber dan timestamp; scenario authoring dan kendali instruktur; peta sintetis pesawat, kendaraan, dan runway; jendela konflik simulasi yang menjelaskan asumsi; serta penanda data sintetis, hilang, atau kedaluwarsa. Kami menunda transkripsi suara otomatis secara langsung, live tracking, skor workload controller, rekomendasi AI, dan dashboard yang memengaruhi keputusan runway.

Kami ingin meminta arahan mentor mengenai empat hal: apakah fokus latihan dan debrief tepat untuk tahap awal; siapa instruktur atau mitra domain yang sebaiknya dilibatkan; ukuran keberhasilan apa yang perlu kami tetapkan untuk pilot; dan persyaratan izin serta tata kelola apa yang perlu disiapkan sebelum menggunakan data mitra.

Kesimpulan kami, FlowLens sebaiknya berkembang secara bertahap: mulai dari simulasi yang transparan, divalidasi bersama instruktur, kemudian diuji dalam riset dengan data berizin. Dengan begitu, kami dapat menguji manfaat produk tanpa menyamakan demonstrasi dengan sistem ATC operasional.

## 3. Makna dan kegunaan teknologi yang dibahas

### A. Surveillance dan otomasi ATM

#### ADS-B — Automatic Dependent Surveillance-Broadcast

Pesawat menentukan posisi menggunakan sistem navigasinya lalu menyiarkan identitas dan data posisi/gerak melalui radio. Berguna untuk surveillance ketika pesawat dan penerima berada dalam cakupan yang sesuai. ADS-B pesawat bukan bukti bahwa kendaraan runway ikut terpantau, dan data ADS-B bukan clearance ATC.

#### Radar primer dan SSR/MSSR

Radar primer mendeteksi pantulan energi dari objek; SSR (Secondary Surveillance Radar) meminta jawaban transponder pesawat; MSSR (Monopulse Secondary Surveillance Radar) adalah bentuk SSR dengan teknik pengukuran sudut yang lebih baik. Sistem ini mendukung pengawasan dan pemisahan lalu lintas udara. Cakupan radar udara tidak otomatis menjadi surveillance permukaan runway.

#### ATSA — Air Traffic Situational Awareness

Fasilitas/sistem situational awareness untuk mendukung pemantauan lalu lintas udara. Dalam laporan DJPU 2024, istilah ini merujuk pada fasilitas cadangan tertentu yang mencakup surveillance, komunikasi, display/rekaman, cuaca, dan simulator. Bukti dua fasilitas ATSA yang disebut tidak sama dengan inventaris seluruh bandara atau bukti pengawasan kendaraan runway secara nasional. [DJPU 2024](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf)

#### ATM dan ATC

ATM (Air Traffic Management) adalah pengelolaan layanan lalu lintas udara yang lebih luas, termasuk koordinasi, kapasitas, informasi, dan aliran trafik. ATC (Air Traffic Control) adalah layanan pengendalian lalu lintas udara melalui instruksi dan pemisahan sesuai tanggung jawab yang berlaku. Keduanya terkait, tetapi istilahnya tidak saling menggantikan.

#### ATMAS — Air Traffic Management Automation System

Nama sistem otomasi ATM yang digunakan AirNav dalam pengumuman New JATSC/New ATMAS. Fungsinya menggabungkan sejumlah layanan dan subsistem ATM. Pengumuman New ATMAS membuktikan kapabilitas yang diumumkan untuk konteks JATSC, bukan akses feed untuk FlowLens atau status penerapan fungsi yang sama pada setiap lokasi. [AirNav](https://www.airnavindonesia.co.id/berita-dan-siaran-pers/kunjungi-airnavindonesia-presiden-icao-tinjau-langsung-fasilitas-new-jatsc/)

#### ADS-C — Automatic Dependent Surveillance-Contract

Surveillance berbasis laporan posisi pesawat yang dikirim sesuai kontrak pelaporan melalui data link. Berguna terutama pada konteks layanan/rute yang mendukungnya; berbeda dari ADS-B yang menyiarkan informasi secara broadcast. ADS-C bukan sensor posisi kendaraan di runway.

#### CPDLC — Controller-Pilot Data Link Communications

Pertukaran pesan digital antara controller dan pilot untuk jenis komunikasi yang sesuai. Dapat mengurangi sebagian komunikasi suara rutin pada layanan yang mendukungnya, tetapi tidak menggantikan seluruh komunikasi suara taktis. Status dukungan bergantung pada sistem, wilayah, pesawat, dan prosedur. [EUROCONTROL MUAC CPDLC](https://www.eurocontrol.int/service/controller-pilot-datalink-communications-our-maastricht-uac)

#### STCA — Short-Term Conflict Alert

Peringatan otomatis mengenai potensi konflik pemisahan jangka pendek pada lalu lintas udara, berdasarkan data dan logika sistem. STCA adalah safety net untuk konteks surveillance udara; namanya tidak berarti ia memantau kendaraan atau clearance runway.

#### APW — Area Proximity Warning

Peringatan ketika lintasan pesawat diperkirakan mendekati atau memasuki area yang ditetapkan, misalnya area terbatas. Kegunaan, batas area, input data, dan respons ditentukan oleh konfigurasi serta prosedur sistem setempat.

#### APM — Approach Path Monitor

Pemantauan lintasan pendekatan untuk membantu mengidentifikasi kondisi lintasan yang menyimpang dari parameter yang ditetapkan. Ini terkait pemantauan approach, bukan pengganti instruksi controller atau sistem deteksi konflik runway FlowLens.

#### AIM — Aeronautical Information Management

Pengelolaan dan distribusi informasi aeronautika resmi, seperti AIP dan NOTAM, dalam format dan siklus publikasi yang berlaku. Berguna untuk memahami prosedur, fasilitas, serta perubahan yang dipublikasikan. Informasi AIM tidak otomatis menjadi status runway secara langsung per detik.

#### ATFM — Air Traffic Flow Management

Pengelolaan aliran lalu lintas udara agar permintaan trafik lebih selaras dengan kapasitas yang tersedia, misalnya melalui pengaturan slot atau waktu keberangkatan. ATFM berskala flow/capacity; bukan sistem penentu clearance kendaraan di permukaan.

#### AMHS — ATS Message Handling System

Sistem pertukaran pesan aeronautika untuk komunikasi layanan lalu lintas udara. Mendukung pengiriman pesan antarfasilitas. Keberadaan AMHS tidak berarti antarmuka datanya terbuka untuk aplikasi pihak ketiga.

#### AIDC — ATS Interfacility Data Communication

Pertukaran data koordinasi antar fasilitas ATS, misalnya koordinasi penerbangan antarunit. Berguna untuk koordinasi digital; tidak sama dengan feed posisi permukaan atau izin penggunaan data oleh FlowLens.

### B. Surface movement dan keselamatan runway

#### A-SMGCS — Advanced Surface Movement Guidance and Control System

Sistem modular untuk surveillance dan pengelolaan pergerakan pesawat/kendaraan di area bandara. Bergantung pada implementasi, modulnya dapat mencakup identifikasi/track, dukungan keselamatan, routing, atau guidance. Tingkat implementasi diputuskan per lokasi; nama A-SMGCS tidak menjamin setiap fungsi tersedia di semua bandara. [EUROCONTROL A-SMGCS](https://www.eurocontrol.int/service/advanced-surface-movement-guidance-and-control-system)

#### ASDE-X — Airport Surface Detection Equipment, Model X

Sistem FAA untuk mendeteksi dan melacak pergerakan permukaan dengan menggabungkan beberapa sumber surveillance. Berguna untuk situational awareness permukaan pada lokasi yang dilengkapi. FAA melaporkan ASDE-X di 35 bandara; angka itu hanya berlaku untuk konteks FAA yang dirujuk. [FAA ASSC/ASDE-X](https://www.faa.gov/air_traffic/technology/adsb/atc/assc)

#### ASSC — Airport Surface Surveillance Capability

Kapabilitas surveillance permukaan yang digunakan FAA di lokasi tertentu sebagai bagian dari peningkatan kesadaran situasi permukaan. ASSC dan ASDE-X adalah implementasi FAA; keduanya bukan bukti bahwa sistem serupa terpasang atau dapat diakses di bandara Indonesia. [FAA ASSC](https://www.faa.gov/air_traffic/technology/adsb/atc/assc)

#### RWSL — Runway Status Lights

Lampu keselamatan otomatis di bandara tertentu yang memberi isyarat visual kepada pilot atau pengemudi kendaraan berdasarkan surveillance dan logika sistem. RWSL bukan clearance dan tidak menggantikan instruksi ATC; pengguna tetap mengikuti prosedur. FAA melaporkan RWSL di 20 bandara pada halaman yang dirujuk. [FAA RWSL](https://www.faa.gov/air_traffic/technology/rwsl/index.cfm?print=go)

#### SAI — Surface Awareness Initiative

Program FAA untuk memperluas situational awareness permukaan di bandara bertower. Sasaran hingga 220 bandara pada 2028 adalah target pemasangan program sebagaimana dilaporkan, bukan jumlah sistem yang sudah seluruhnya aktif. [FAA SAI](https://www.faa.gov/airports/runway_safety/airfield_drivers/enhancing-surface-safety-guide-vehicle-movement-area)

#### RIMCAS — Runway Incursion Monitoring and Conflict Alert System

Nama yang digunakan untuk sistem pemantauan runway incursion dan peringatan konflik pada implementasi tertentu. Kegunaan dan integrasinya bergantung pada sensor, konfigurasi lokal, serta prosedur. Laporan riset tidak menemukan bukti publik yang memadai untuk membuat inventaris deployment nasional Indonesia.

#### E-strip dan FDP — electronic flight strip / Flight Data Processing

E-strip adalah representasi digital data penerbangan/kemajuan penanganan yang dapat menggantikan atau melengkapi strip kertas. FDP mengolah data penerbangan dan dapat mendukung fungsi ATM. Field dan penggunaan tiap sistem bersifat khusus; status e-strip per unit di Indonesia belum terverifikasi dalam sumber publik yang diperiksa.

#### Surveillance permukaan, runway occupancy, dan clearance state

Surveillance permukaan memperkirakan atau melacak objek di area movement berdasarkan sumber sensor. Runway occupancy adalah status fisik/operasional runway; clearance state adalah status instruksi/izin yang diberikan melalui prosedur. Ketiganya berkaitan tetapi tidak identik: posisi track saja tidak membuktikan clearance, dan tampilan simulasi tidak membuktikan runway nyata clear.

### C. Komunikasi, data, dan informasi operasi

#### VHF/UHF dan perekam suara

VHF dan UHF adalah pita frekuensi radio yang digunakan untuk komunikasi penerbangan dan komunikasi operasional tertentu. Perekam suara membantu dokumentasi atau review sesuai otorisasi dan kebijakan. Rekaman dapat sensitif; akses, penyimpanan, penggunaan, dan transkripsi memerlukan izin serta aturan yang jelas.

#### SWIM — System Wide Information Management

Arsitektur/pendekatan berbagi layanan dan informasi ATM antar pihak melalui service yang terkelola. SWIM bukan sinonim “semua data terbuka”; autentikasi, registrasi, jenis layanan, syarat penggunaan, dan otorisasi tetap berlaku. [FAA SWIM access](https://www.faa.gov/air_traffic/technology/swim/products/get_connected)

#### STDDS — System Wide Information Management Terminal Data Distribution System

Layanan distribusi data terminal FAA bagi pelanggan/subscriber yang memenuhi aturan akses. Berguna sebagai contoh bagaimana data dapat dibagikan secara terkendali. Angka sistem dan bandara pada STDDS tidak menggambarkan akses data Indonesia atau lisensi komersial otomatis. [FAA STDDS](https://www.faa.gov/air_traffic/technology/swim/stdds)

#### GPS dan AVL — Automatic Vehicle Location

GPS menyediakan posisi berbasis satelit; AVL mengacu pada sistem pelacakan lokasi kendaraan/fleet, yang dapat memakai GPS dan komunikasi data. Berguna untuk operasi armada jika dipasang, aktif, dan dibagikan. Posisi GPS tidak otomatis berarti kendaraan memiliki izin runway atau dapat dilihat controller.

#### Transponder kendaraan

Perangkat identifikasi/pemancar pada kendaraan yang dapat membantu sistem surveillance mengenali atau melacak kendaraan jika sistem bandara mendukungnya. Keberadaan transponder harus diverifikasi per armada dan lokasi; GPS ponsel atau AVL internal tidak setara dengan track resmi yang tersedia untuk ATC.

#### METAR/SPECI, TAF, dan SIGMET

METAR adalah laporan cuaca aerodrome rutin; SPECI adalah laporan khusus saat kondisi memerlukan; TAF adalah prakiraan aerodrome; SIGMET memberi informasi fenomena cuaca yang signifikan bagi penerbangan. Berguna untuk konteks operasi atau skenario latihan, dengan timestamp, masa berlaku, dan sumber yang jelas. Produk cuaca bukan pengganti surveillance permukaan.

#### AIP dan NOTAM

AIP adalah publikasi informasi aeronautika resmi; NOTAM menyampaikan informasi perubahan atau kondisi yang relevan bagi operasi penerbangan. Keduanya penting untuk prosedur dan konteks skenario. NOTAM tidak dengan sendirinya menjadi sensor occupancy runway real-time; periksa tanggal efektif dan sumber resmi.

### D. Teknologi analitik dan pengujian FlowLens

#### ASR/STT — Automatic Speech Recognition / Speech-to-Text

Teknologi untuk mengubah audio menjadi teks. Pada FlowLens, penggunaan awal yang lebih aman adalah membuat draft transkrip offline untuk bahan review instruktur. Hasilnya perlu diverifikasi manusia dan tidak boleh dianggap sebagai clearance resmi.

#### NLP — Natural Language Processing

Metode komputasi untuk mengolah teks, misalnya mencari callsign atau menandai istilah pada transkrip. Dapat membantu pengindeksan bahan latihan, tetapi belum layak menetapkan clearance atau makna instruksi kritis tanpa verifikasi manusia.

#### Rule deterministik, conflict window, dan replay

Rule deterministik menghitung keluaran dengan aturan eksplisit yang dapat diperiksa. Conflict window adalah rentang waktu simulasi ketika dua lintasan/asumsi memenuhi kondisi konflik yang telah ditentukan; bukan probabilitas kecelakaan. Replay memutar ulang event beserta timestamp dan sumbernya agar instruktur dapat meninjau skenario yang sama.

#### Data quality: synthetic, missing, stale, dan unverified

Penanda ini menjelaskan kualitas atau asal informasi: synthetic berarti dibuat untuk simulasi; missing berarti nilai tidak tersedia; stale berarti sudah terlalu lama untuk dianggap terkini; unverified berarti belum dikonfirmasi. Penanda harus terlihat agar pengguna tidak mengira simulasi atau data lama sebagai keadaan operasi saat ini.

### E. Istilah lain dalam inventaris teknologi riset

#### MLAT/WAM — Multilateration / Wide Area Multilateration

Teknik menentukan posisi dari perbedaan waktu tibanya sinyal transponder pada beberapa sensor yang lokasinya diketahui. MLAT/WAM dapat menjadi sumber surveillance pesawat atau target yang memancarkan sinyal, bergantung pada desain sistem. Akurasi dan cakupan harus dinilai per lokasi; ketersediaan global tidak membuktikan deployment Indonesia.

#### SMR — Surface Movement Radar

Radar yang dipakai untuk mendeteksi target di permukaan bandara. Dapat mendukung pengawasan pergerakan di taxiway/runway, tetapi hasilnya bergantung pada clutter, geometri, blind zone, identifikasi target, dan integrasi ke display. Tidak ada inventaris publik nasional yang cukup untuk menyatakan cakupan SMR tiap bandara Indonesia.

#### S-SMGCS — Surveillance Surface Movement Guidance and Control System

Istilah untuk fungsi surveillance surface movement yang lebih dasar dalam keluarga SMGCS; A-SMGCS dapat menambah fungsi seperti safety support, routing, dan guidance. Fungsi persisnya mengikuti definisi standar dan implementasi setempat, sehingga label sistem saja belum cukup untuk menyimpulkan fitur mana yang tersedia.

#### RMCA — Runway Monitoring and Conflict Alert

Fungsi dukungan keselamatan yang memonitor kondisi/konflik runway berdasarkan input surveillance dan keadaan yang dikonfigurasi. RMCA merupakan fungsi sistem yang terdefinisi, bukan satu sensor. FlowLens tidak boleh mengadopsi threshold atau menyatakan setara dengan fungsi RMCA tanpa validasi, prosedur, dan approval yang sesuai.

#### REL/THL — Runway Entrance Lights / Takeoff Hold Lights

REL memberi isyarat lampu pada titik masuk runway; THL memberi isyarat lampu terkait posisi takeoff/hold. Pada implementasi RWSL FAA, lampu ini memberi cue keselamatan otomatis dan bukan pengganti clearance ATC. Fungsi lampu dan konfigurasi setempat perlu dilihat pada dokumentasi resmi sistem.

#### VMAT — Vehicle Movement Area Transponder

Nama yang digunakan FAA untuk transponder kendaraan area pergerakan bandara dalam konteks program equipage tertentu. Perangkat ini dapat membantu identifikasi kendaraan pada display surface bila sistem penerima mendukungnya. Tidak semua kendaraan otomatis terlihat; posisi internal GPS/AVL tidak serta-merta menjadi track ATC.

#### MTCD — Medium-Term Conflict Detection

Fungsi otomasi ATM untuk memperkirakan potensi konflik lalu lintas dalam horizon menengah dengan memakai track dan data penerbangan/trajectory. Horizon serta aturan berbeda menurut sistem. Ini bukan padanan langsung bagi conflict window FlowLens yang menghitung skenario runway sintetis.

#### TFDM — Terminal Flight Data Manager

Program FAA untuk mengelola data penerbangan terminal dan mendukung peralihan workflow strip kertas ke workflow digital, termasuk pengelolaan permukaan tertentu. Ini contoh modernisasi FAA, bukan bukti bahwa electronic strip sudah diterapkan di seluruh lokasi atau di Indonesia. [FAA TFDM timeline](https://www.faa.gov/air_traffic/technology/tfdm/timeline)

#### TBFM — Time-Based Flow Management; TFMS — Traffic Flow Management System

TBFM mendukung pengaturan aliran kedatangan berdasarkan waktu dan kapasitas; TFMS adalah sistem FAA untuk fungsi flow management yang lebih luas. Keduanya berada pada ranah pengelolaan trafik/kapasitas, bukan pemantauan clearance kendaraan runway.

#### AMAN/DMAN — Arrival/Departure Manager

Tools untuk perencanaan atau pengurutan kedatangan (AMAN) dan keberangkatan (DMAN) agar penggunaan kapasitas lebih terkelola. Hasilnya bergantung pada data, konfigurasi, dan proses koordinasi. Deployment spesifik di Indonesia harus dikonfirmasi; FlowLens MVP bukan sequence optimizer.

#### PBN/RNAV/RNP/FMS

PBN (Performance-Based Navigation) adalah kerangka navigasi berbasis kinerja; RNAV (Area Navigation) dan RNP (Required Navigation Performance) adalah spesifikasi navigasi di dalam kerangka itu. FMS (Flight Management System) mengelola fungsi navigasi/perencanaan penerbangan pesawat. Informasi prosedur PBN tidak memberi FlowLens akses ke posisi atau data FMS pesawat.

#### GNSS/IRS — Global Navigation Satellite System / Inertial Reference System

GNSS adalah keluarga sistem navigasi satelit; IRS memperkirakan gerak/posisi menggunakan sensor inersial pesawat. Keduanya dapat menjadi input navigasi pesawat, tetapi kualitas posisi, integritas, dan cara data dibagikan bergantung pada sistem. FlowLens MVP memakai posisi yang dibuat untuk simulasi.

#### AWOS/RVR — Automatic Weather Observing System / Runway Visual Range

AWOS mengukur dan melaporkan unsur cuaca di aerodrome secara otomatis sesuai konfigurasi; RVR memperkirakan jarak pandang sepanjang runway untuk konteks operasi/penerbangan. Ketersediaan, interval, dan akses data berbeda per lokasi. Produk METAR/TAF juga memiliki timestamp serta masa berlaku dan bukan track permukaan.

#### Remote/digital tower

Konsep penyediaan layanan tower dari lokasi terpisah menggunakan kamera/sensor, jaringan, audio, dan display. Operasi membutuhkan desain sightline, latency/integrity, fallback, pelatihan, prosedur, serta persetujuan keselamatan. Kamera saja tidak membuat suatu lokasi menjadi remote tower; laporan riset tidak menemukan bukti publik deployment operasional di Indonesia.

#### AFTN, ASTERIX, dan CAT011

AFTN (Aeronautical Fixed Telecommunication Network) adalah jaringan pertukaran pesan aeronautika yang lebih lama/konvensional. ASTERIX adalah keluarga format pertukaran data surveillance; CAT011 adalah kategori ASTERIX untuk informasi surveillance permukaan tertentu. Adanya standar format tidak berarti FlowLens memiliki koneksi, data feed, atau izin penggunaan.

#### SWIFT — SWIM Flight Information Services

Layanan FAA untuk menemukan/mengakses layanan informasi penerbangan melalui kerangka SWIM dengan pendaftaran dan otorisasi. Ini contoh akses terkelola; “tersedia online” tidak otomatis berarti terbuka untuk penggunaan apa pun atau setara dengan data Indonesia.

#### FDR/CVR dan laporan keselamatan

FDR (Flight Data Recorder) merekam parameter penerbangan; CVR (Cockpit Voice Recorder) merekam audio cockpit. Keduanya merupakan sumber investigasi yang sangat sensitif dan aksesnya diatur; laporan investigasi publik tidak sama dengan raw recording. KNKT dan NASA ASRS adalah sumber laporan/lesson keselamatan, bukan sistem surveillance real-time.

## 4. Potensi pertanyaan mentor dan jawaban yang disarankan

| Potensi pertanyaan | Jawaban yang disarankan |
|---|---|
| Apa masalah yang diselesaikan FlowLens? | Kami menguji apakah replay skenario runway yang menghubungkan gerak, instruksi, dan timestamp membantu latihan serta debrief. Kami belum mengklaim bahwa FlowLens mengatasi masalah operasional nyata atau mengurangi insiden. |
| Mengapa tidak langsung membuat dashboard real-time? | Data dan otorisasi belum tersedia, sistem berbeda menurut lokasi, dan tampilan operasional dapat memengaruhi keputusan keselamatan. Simulasi offline memungkinkan kami menguji alur produk tanpa menyatakan sudah terintegrasi. |
| Apa bukti bahwa bandara Indonesia belum memiliki surface surveillance? | Kami tidak menyimpulkan bahwa sistem itu tidak ada. Temuan kami adalah bukti publik yang cukup untuk membuat inventaris deployment per bandara belum ditemukan. Perlu konfirmasi AirNav, pengelola bandara, dan pemilik sistem. |
| Bukankah ADS-B sudah memberi posisi pesawat? | ADS-B dapat mendukung surveillance pesawat dalam cakupan tertentu, tetapi bukan clearance dan tidak otomatis melacak kendaraan runway. Track pesawat saja juga tidak cukup untuk mengetahui seluruh keadaan runway. |
| Apakah FlowLens bisa mencegah runway incursion? | Belum ada bukti yang mendukung klaim itu. Saat ini kami hanya dapat menunjukkan aturan atau konflik dalam skenario simulasi; klaim pencegahan memerlukan studi dan evaluasi keselamatan yang jauh lebih kuat. |
| Dari mana angka overlap 16 detik pada demo? | Angka itu berasal dari parameter skenario sintetis BAW123/ARFF-2, bukan sensor, bandara, atau kejadian nyata. Kami akan memberi label simulasi dan menunjukkan cara hitung serta asumsi. |
| Apakah FlowLens menggunakan AI? | Penggunaan AI bukan syarat MVP. Prioritas saat ini adalah rule deterministik dan replay yang dapat dijelaskan. AI transkripsi atau ekstraksi teks hanya dapat dipertimbangkan sebagai draft offline setelah data berizin dan verifikasi instruktur tersedia. |
| Bagaimana membuktikan produk ini berguna? | Pada pilot latihan, kami dapat mengukur kelengkapan debrief, kemampuan peserta mengidentifikasi urutan event, pemahaman atas alasan suatu marker, usability, serta cara peserta mengenali data yang hilang atau sintetis. Metrik dan protokol perlu ditetapkan sebelum studi. |
| Bagaimana FlowLens mengukur workload controller? | MVP tidak mengukur beban mental controller. Kami dapat menghitung jumlah event atau interaksi sebagai indikator kompleksitas skenario, lalu mengukurnya terpisah dari penilaian workload yang tervalidasi dan partisipasi instruktur. |
| Data apa yang dibutuhkan untuk pilot pertama? | Untuk pilot latihan, kami dapat mulai dengan layout fiktif, event sintetis, dan instruktur. Bila riset memerlukan data historis, gunakan hanya data yang disetujui pemiliknya, dengan de-identifikasi, definisi ground truth, batas akses, dan retensi. |
| Bagaimana menghindari pengguna mengira marker adalah perintah ATC? | Beri label simulasi/advisory yang konsisten, jelaskan sumber dan status data, hindari bahasa clearance, dan pastikan semua output latihan ditinjau instruktur. Jangan tampilkan seolah-olah terhubung ke sistem resmi. |
| Siapa calon mitra awal yang paling masuk akal? | Instruktur ATC atau pusat pelatihan adalah mitra validasi pertama karena scope saat ini adalah latihan dan debrief. Setelah use case jelas, barulah minta masukan unit ANSP, pengelola bandara, dan pemilik data yang relevan. |
| Apa syarat sebelum membuat sandbox operasional? | Sponsor tertulis, use case non-safety-critical yang jelas, otorisasi data, pemilik interface, security review, mode degradasi, aturan akses/retensi, pelatihan pengguna, dan konsultasi regulator/ANSP yang relevan. |
| Apa yang akan dianggap sebagai keputusan untuk menghentikan atau mengubah arah? | Jika instruktur tidak melihat manfaat debrief, skenario sulit divalidasi, atau risiko salah tafsir tetap tinggi, kami akan mempersempit atau mengubah use case sebelum menambah integrasi. Kriteria ini sebaiknya disepakati sejak awal pilot. |

## 5. Rekomendasi pengembangan dan gerbang keputusan

### Tahap 1 — MVP simulasi offline

- Gunakan satu layout fiktif dan beri label simulasi pada peta, event, dan laporan.
- Bangun replay timeline, scenario authoring dasar, instruktur dapat pause/seek, serta seeded scenario agar hasil dapat diulang.
- Hitung conflict window memakai aturan transparan; tampilkan asumsi, timestamp, dan sumber setiap event.
- Tampilkan status data synthetic, missing, stale, atau unverified.
- Ganti label “high risk” dengan penjelasan seperti “aturan konflik simulasi terpenuhi” sampai ada validasi yang tepat.

**Gerbang ke tahap berikutnya:** instruktur domain dapat menelusuri setiap aturan; event timeline konsisten; tidak ada aturan clearance yang tidak ditinjau; pengguna paham bahwa data adalah simulasi.

### Tahap 2 — Pilot latihan dan debrief

- Libatkan instruktur ATC yang berpengalaman untuk meninjau skenario, istilah, geometri, dan aturan.
- Uji scenario authoring, kendali instruktur, replay/branching, bookmark event, dan laporan debrief.
- Ukur usability, pemahaman event, kelengkapan debrief, transparansi rule, dan reaksi pengguna terhadap indikator data.
- Jangan menyebut hasil pilot sebagai bukti pengurangan insiden atau peningkatan keselamatan operasional.

**Gerbang ke tahap berikutnya:** protokol, peserta, metrik, izin, dan cara menetapkan ground truth disepakati sebelum pengumpulan data.

### Tahap 3 — Pilot riset berbasis data berizin

- Tambahkan satu jenis data pada satu waktu, misalnya log simulator atau track historis yang telah dide-identifikasi.
- Buat kontrak data: tujuan penggunaan, hak akses, de-identifikasi, retensi, penghapusan, dan larangan redistribusi bila berlaku.
- Periksa sinkronisasi waktu, data hilang, konflik identitas, dan provenance.
- Ukur ketepatan penelusuran event terhadap ground truth yang telah ditetapkan; catat false alerts dan missed events pada skenario uji yang disusun.

**Gerbang ke tahap berikutnya:** sponsor, kepemilikan interface, penilaian keamanan, mode degradasi, serta klasifikasi dan batas fungsi disetujui.

### Tahap 4 — Sandbox read-only untuk dukungan non-safety-critical

- Hanya dilakukan jika ada sponsor dan kebutuhan dari pemilik operasi.
- Tampilkan sumber, timestamp, usia data, dan status degradasi dengan jelas.
- Hindari mengeluarkan clearance, status runway-clear otoritatif, atau rekomendasi dispatch.
- Uji penanganan stale data, kehilangan koneksi, hak akses, keamanan, dan interpretasi pengguna.

### Tahap 5 — Integrasi operasional sebagai kemungkinan bersyarat

- Tidak dijanjikan dalam roadmap waktu produk.
- Harus diminta dan dipimpin bersama ANSP/operator serta otoritas terkait.
- Memerlukan data dan interface berotorisasi, evaluasi independen, safety case, validasi faktor manusia, cybersecurity, proses persetujuan, fallback, monitoring, dan perubahan konfigurasi terkendali.
- Tidak ada klaim pengganti controller atau jaminan keselamatan.

## 6. Rekomendasi produk: prioritas, tunda, dan batas klaim

### Prioritaskan untuk MVP

1. Timeline replay dengan sumber data, timestamp, dan status verifikasi.
2. Scenario authoring dan instructor control.
3. Peta pesawat/kendaraan sintetis dengan geometri runway yang dinyatakan fiktif.
4. Conflict window deterministik yang menjelaskan rule, asumsi, dan rentangnya.
5. Penanda data quality: synthetic, missing, stale, dan unverified.

### Tunda sampai ada data dan mitra

1. Transkripsi radio langsung dan automated readback mismatch.
2. Live tracking pesawat/kendaraan melalui sistem ATC atau aggregator.
3. Skor workload/fatigue controller.
4. Dashboard yang memengaruhi status runway atau keputusan dispatch.
5. Rekomendasi AI, optimasi sequencing, dan integrasi operasional.

### Batas klaim yang harus dijaga

- Jangan menyatakan “mencegah kecelakaan/insiden” tanpa bukti terukur dan evaluasi yang sesuai.
- Jangan menyebut data FlowLens live/terintegrasi bila feed berotorisasi tidak benar-benar tersedia.
- Jangan menyebut “high risk” bila hanya berasal dari overlap skenario sintetis.
- Jangan menyebut indikator hitungan event sebagai pengukuran workload manusia.
- Jangan menyatakan AI memahami atau mengesahkan clearance.

## 7. Potensi AI FlowLens: peran, data, dan variabel

### Prinsip: AI membantu latihan; aturan simulasi tetap dapat diperiksa

Potensi AI FlowLens paling masuk akal sebagai **asisten untuk menyiapkan skenario dan meninjau bukti latihan**, bukan sebagai controller atau penentu clearance. Untuk menghitung posisi, waktu, geometri, runway occupancy dalam skenario, dan conflict window, gunakan aturan deterministik yang dapat ditelusuri. AI dapat membantu membuat draft atau menemukan bagian yang perlu ditinjau, tetapi instruktur tetap mengesahkan isi dan event.

AI bukan syarat agar MVP bernilai. Pembeda awal yang dapat dibuktikan adalah replay yang konsisten, data yang berprovenance, dan debrief yang mudah ditelusuri. Tambahkan AI hanya bila ia mengurangi pekerjaan tertentu tanpa membuat pengguna mengira output model sebagai fakta operasi.

### Use case AI yang realistis

| Use case | Data/variabel yang diperlukan | Keluaran yang layak | Batas penggunaan |
|---|---|---|---|
| Draft variasi skenario latihan | Template yang sudah disetujui; geometri runway/taxiway fiktif atau berizin; jumlah dan posisi awal pesawat/kendaraan; rute; kecepatan; visibility/cuaca; jenis event latihan; tingkat kompleksitas yang ditentukan instruktur | Draft parameter skenario baru dalam batas yang telah ditentukan | AI tidak mengarang SOP, phraseology otoritatif, atau clearance. Instruktur meninjau dan menyetujui sebelum skenario dimainkan. |
| Draft transkrip suara offline | Audio yang hak penggunaannya jelas; timestamp dan channel; bahasa, aksen, kualitas/noise; label speaker bila diketahui; contoh transkrip ground truth yang diverifikasi; konteks callsign hanya dari sumber yang disetujui | Teks kandidat dengan penanda bagian tidak jelas untuk dikoreksi manusia | Bukan clearance resmi; jangan dipakai live untuk mengeluarkan alert. Audio dan identitas dapat sensitif. |
| Ekstraksi kandidat event dari teks | Transkrip terverifikasi atau naskah sintetis; kamus phraseology yang ditinjau; event log/timestamp; peran speaker; konteks geometri dan track skenario | Kandidat callsign, runway/taxiway, jenis instruksi, readback, negasi, dan waktu event yang ditautkan ke teks sumber | AI mengusulkan tag; manusia mengesahkan. Jangan menyimpulkan izin runway hanya dari track atau teks otomatis. |
| Pencarian dan ringkasan debrief | Event log terverifikasi; instruksi dan readback yang telah diperiksa; aturan simulasi yang terpicu; timestamp; sumber/asal data; catatan instruktur | Ringkasan urutan event, tautan ke bukti, dan pertanyaan debrief untuk instruktur | Ringkasan harus menunjukkan sumber tiap klaim dan memisahkan fakta skenario dari interpretasi. Tidak menyatakan sebab-akibat keselamatan. |
| Analisis pola pada data latihan | Banyak sesi simulator yang berizin; event label/ground truth; versi skenario; data quality flags; identitas peserta yang diminimalkan atau dide-identifikasi | Pencarian pola kesalahan/urutan yang berulang untuk ditinjau instruktur | Tidak mendiagnosis kompetensi atau fatigue dan tidak digeneralisasi ke operasi nyata tanpa studi representatif. |
| Deteksi anomali dalam simulator | Track dan event sintetis/berizin; geometri; rule trace; label instruktur untuk kondisi normal dan variasi yang disengaja | Penanda “perlu ditinjau” dalam replay latihan | Gunakan sebagai bantuan eksplorasi, bukan alert operasional. Uji false positive dan missed event pada skenario yang sudah memiliki ground truth. |

### Data dan variabel yang dapat dipakai

Variabel dipilih sesuai pertanyaan yang hendak dijawab. FlowLens tidak perlu mengumpulkan semua jenis data sekaligus.

| Kelompok | Contoh field/variabel | Kegunaan untuk AI/analitik | Sumber yang disarankan pada tahap awal |
|---|---|---|---|
| Geometri dan layout | Runway/taxiway fiktif atau berizin; intersection; holding point; jarak; orientasi; area terlarang | Membatasi skenario, menghitung lintasan, dan memberi konteks event | Layout sintetis yang dibuat untuk demo; kemudian layout resmi hanya dengan izin |
| Keadaan pergerakan | ID anonim; posisi x/y; heading; speed; rute; status bergerak/berhenti; timestamp; interval update | Menjalankan replay dan menghitung jendela waktu secara deterministik | Track generator simulator dengan seed yang tercatat |
| Instruksi dan event | Jenis instruksi yang ditulis instruktur; runway/taxiway; waktu dikeluarkan/diulang/dikonfirmasi; peran speaker; event crossing/hold/takeoff; status verifikasi | Mengurutkan pesan dan movement serta membuat ground truth latihan | Event log buatan penulis skenario; selanjutnya log simulator berizin |
| Audio/teks | File audio; channel; bahasa/aksen; noise; transkrip; speaker role; frasa target; timestamp; bagian yang tidak pasti | Evaluasi ASR dan ekstraksi kandidat event | Audio sintetis atau rekaman yang consent dan hak penggunaannya telah disetujui; transkrip manual tervalidasi |
| Kondisi lingkungan | Visibility; wind; precipitation; runway condition bila relevan; timestamp dan validity | Membuat variasi latihan dan memberi konteks pada debrief | Parameter sintetis pada MVP; produk BMKG resmi hanya untuk riset jika penggunaan dan waktunya sesuai |
| Kompleksitas skenario | Jumlah target; jumlah event serentak; frekuensi komunikasi; jumlah task handoff; tingkat variasi | Memvariasikan latihan dan mengukur kompleksitas tugas skenario | Parameter yang ditentukan instruktur; sebut sebagai kompleksitas skenario, bukan workload mental controller |
| Kualitas/provenance | Synthetic/historical/manual/authorized; source ID; usia data; missing fields; clock offset; verifikasi; versi model/rule | Menolak atau menandai input yang tidak cukup, serta memungkinkan audit hasil | Simpan metadata bersama setiap event; jangan menimpa nilai mentah |
| Label/ground truth | Event benar; field transkrip; urutan; rule trigger; kategori latihan; koreksi instruktur | Melatih/menguji model dan menghitung kualitas keluaran | Label oleh instruktur/reviewer dengan definisi dan catatan perbedaan |

### Contoh alur data untuk satu skenario

1. Instruktur memilih template dan mengatur runway fiktif, traffic, kendaraan, visibility, serta event tujuan.
2. Simulator menghasilkan posisi, kecepatan, rute, dan timestamp sintetis. Semua data membawa `source=synthetic` dan ID skenario/seed.
3. Rule engine deterministik menghitung lintasan, occupancy latihan, dan conflict window dari parameter tersebut. Sistem menyimpan rule dan asumsi yang memicu hasil.
4. Bila tersedia dialog/audio latihan, ASR/NLP dapat membuat draft transkrip dan kandidat event. Setiap kandidat ditautkan ke waktu dan potongan sumber; instruktur mengoreksi sebelum menjadi ground truth.
5. AI debrief dapat menyusun ringkasan hanya dari event yang telah diverifikasi dan menyertakan rujukan ke event/timestamp. Instruktur menyunting atau menolak ringkasan.
6. Hasil evaluasi disimpan terpisah dari data mentah: misalnya koreksi transkrip, event yang terlewat, false alert, serta pemahaman peserta. Versi skenario, rule, dan model dicatat agar review dapat diulang.

Contoh variabel skenario: `scenario_id`, `layout_version`, `runway_id`, `aircraft_track`, `vehicle_track`, `speed`, `route`, `clearance_event_time`, `readback_event_time`, `visibility`, `source_type`, `data_age`, `verification_status`, dan `rule_trigger`. Ini contoh struktur data untuk rancangan, bukan klaim bahwa FlowLens saat ini telah menyimpan seluruh field tersebut.

### Tahapan penerapan AI yang disarankan

1. **MVP:** tanpa AI pada fungsi inti. Gunakan skenario terstruktur, event authoring manual, replay deterministik, dan provenance.
2. **Eksperimen authoring:** AI membuat variasi draft dari template yang dikunci; instruktur memvalidasi sebelum dipakai.
3. **Pilot latihan:** uji pencarian/ringkasan debrief yang hanya memakai event log terverifikasi dan selalu menautkan klaim ke sumbernya.
4. **Audio offline:** pertimbangkan ASR setelah ada data yang legal dan berizin, transkrip ground truth, pengujian bahasa/aksen/noise, serta alur koreksi manusia.
5. **Riset analitik:** anomaly detection atau pattern search hanya pada dataset berizin dengan label, protokol, dan ukuran error yang ditetapkan sebelumnya.
6. **Operasional live:** model AI untuk menafsirkan clearance atau memberi safety alert tidak direkomendasikan sebagai roadmap produk saat ini. Perlu use case yang diminta operator dan safety/approval process terpisah.

### Metrik dan guardrail evaluasi

- **Transkripsi:** ukur tingkat kesalahan kata dan, terutama, ketepatan field kritis seperti callsign, angka, runway, negasi, dan instruksi. Kesalahan kritis ditinjau terpisah dari kesalahan kata biasa.
- **Ekstraksi event:** ukur precision/recall terhadap label instruktur, timestamp error, event yang terlewat, dan kandidat keliru.
- **Ringkasan debrief:** audit apakah setiap klaim memiliki event/timestamp sumber, apakah model menambah fakta yang tidak ada, dan apakah instruktur dapat mengoreksinya.
- **Generasi skenario:** cek kepatuhan pada template/geometri/parameter; hitung draft yang ditolak atau perlu revisi oleh instruktur.
- **Robustness:** ulangi variasi traffic, noise, aksen, data hilang, clock offset, dan kondisi degraded yang relevan. Pisahkan hasil per jenis data dan skenario.
- **Penggunaan manusia:** amati apakah trainee/instruktur memahami label AI sebagai draft, apakah mereka dapat menemukan bukti, dan apakah ada automation bias.
- **Data governance:** catat izin, tujuan, masa simpan, akses, de-identifikasi, versi model, dan proses penghapusan sesuai kesepakatan mitra.

Jangan menetapkan target angka performa sebelum baseline, ukuran sampel, serta konsekuensi tiap jenis kesalahan disepakati dengan instruktur/domain reviewer. Skor confidence model juga jangan ditampilkan seolah probabilitas terkalibrasi kecuali kalibrasi tersebut sudah diuji.

### Jawaban singkat jika mentor bertanya “AI-nya melakukan apa?”

> Pada tahap awal, AI bukan pengambil keputusan ATC. Potensinya adalah membantu instruktur membuat variasi skenario, mencari event dalam log latihan, dan menyusun draft debrief yang setiap klaimnya merujuk ke event serta timestamp. Untuk posisi, konflik, dan urutan pergerakan, kami memakai perhitungan deterministik. Jika nanti mencoba transkripsi suara, hasilnya tetap draft offline yang diverifikasi manusia. Kami belum memakai AI untuk clearance, live alert, atau keputusan runway.

### Pertanyaan mentor yang khusus tentang AI

| Potensi pertanyaan | Jawaban yang disarankan |
|---|---|
| Mengapa produk ini membutuhkan AI? | AI bukan prasyarat MVP. Kami hanya akan mempertahankannya bila terbukti menghemat waktu authoring/review atau membantu pencarian bukti tanpa mengurangi keterlacakan. |
| Data apa yang akan dipakai melatih model? | Belum ada dataset operasional yang kami klaim tersedia. Tahap awal memakai skenario sintetis dan template reviewer. Audio/log nyata hanya dipakai jika ada persetujuan, hak penggunaan, label ground truth, dan batas retensi. |
| Bagaimana mencegah AI mengarang clearance? | Model tidak menetapkan clearance. Kami membatasi output menjadi kandidat/draft, menautkannya ke input, menampilkan status belum diverifikasi, dan mewajibkan persetujuan instruktur. |
| Apakah AI dapat memperkirakan risiko tabrakan? | Belum. Conflict window MVP adalah hasil rule simulasi yang deterministik, bukan probabilitas kecelakaan. Prediksi risiko butuh definisi label, data representatif, kalibrasi, dan evaluasi keselamatan. |
| Apakah model bisa membaca workload controller? | Tidak dari jumlah event saja. FlowLens dapat mengukur kompleksitas tugas skenario. Workload manusia harus dievaluasi dengan metode dan partisipasi operator yang sesuai, terpisah dari indikator otomatis. |
| Bagaimana mengukur keberhasilan AI? | Tetapkan ground truth dan metrik per use case: ketepatan field kritis, event terlewat/keliru, timestamp error, dukungan sumber pada ringkasan, tingkat koreksi instruktur, serta kemampuan pengguna mengenali draft AI. |

**Rekomendasi pilihan pertama:** uji pencarian/ringkasan debrief berbasis event simulator yang sudah diverifikasi, atau generator draft skenario berbasis template. Tunda AI suara karena kebutuhan audio ATC yang representatif, izin, noise, variasi aksen, dan risiko salah mengenali instruksi membuat validasinya lebih berat.

## 8. Rencana teknis pengembangan dan keluaran MVP

### Status teknis repositori saat ini

Bagian ini membedakan kode yang sudah ada dari pekerjaan yang masih diperlukan. Status diperiksa dari berkas proyek saat dokumen ini diperbarui; ini bukan hasil build atau uji aplikasi.

| Lapisan | Teknologi/bahasa | Status pada repositori |
|---|---|---|
| API dan simulator | Python 3.11+, FastAPI, Pydantic v2 | Sudah ada. API single-process menyediakan katalog skenario, sesi, command, snapshot, event, replay/review, assessment, dan report. |
| Geometri dan deteksi | Python, Shapely 2, rule deterministik | Sudah ada. `backend/detection.py` bekerja pada track observasi dan menghitung interval area runway sintetis serta kandidat alert. |
| Skenario dan gerak | Python, JSON, `random.Random(seed)` | Sudah ada. Katalog berisi 12 latihan; tiap durasi katalog saat ini 180 detik. Posisi dibuat oleh simulator sintetis. |
| Penyimpanan | SQLite | Sudah ada. Menyimpan metadata sesi, event, frame publik/privat, command, dan checkpoint untuk review/branch. |
| Antarmuka browser | TypeScript, React 19, Vite | Kerangka belum lengkap saat berkas diperiksa. `main.tsx` mengimpor `App`, tetapi `frontend/src/App.tsx` belum ada; `package.json`/lockfile juga belum mencantumkan dependency build Vite/TypeScript yang diperlukan. UI MVP harus dibangun dan dependency dikunci sebelum demo browser bisa dianggap siap. |
| AI/ML | Belum ada model atau framework ML di dependency runtime | Belum diimplementasikan. Algoritma inti saat ini berupa simulator dan rule deterministik; usulan AI di bagian sebelumnya merupakan kemungkinan bertahap, bukan fitur yang sudah tersedia. |

Rujukan modul: [models.py](../../backend/models.py), [simulator.py](../../backend/simulator.py), [detection.py](../../backend/detection.py), [session.py](../../backend/session.py), [storage.py](../../backend/storage.py), [app.py](../../backend/app.py), serta [frontend/package.json](../../frontend/package.json), [frontend/src/main.tsx](../../frontend/src/main.tsx), [frontend/src/api.ts](../../frontend/src/api.ts), dan [frontend/src/types.ts](../../frontend/src/types.ts).

### Bahasa dan pembagian tanggung jawab

- **Python** untuk domain model, simulator, aturan deteksi, API, arsip/replay, dan pembuatan laporan. Pydantic memvalidasi skema input/output API; Shapely menangani bentuk geometri 2D.
- **TypeScript + React** untuk dashboard browser, state sesi, peta/track, panel instruktur, timeline, serta laporan debrief. TypeScript types harus sejalan dengan kontrak Pydantic.
- **JSON** untuk katalog/template skenario, geometri latihan, seed, dan konfigurasi eksperimen yang terversi.
- **SQLite** untuk MVP lokal/satu writer. Jika kelak beberapa lokasi/kelas membutuhkan layanan bersama, keputusan basis data baru dilakukan berdasarkan kebutuhan konkurensi, backup, akses, dan retensi.
- **CSS/SVG/canvas** dapat digunakan untuk menggambar layout dan track fiktif di browser. Untuk MVP, peta 2D sederhana lebih mudah diperiksa daripada visual 3D.
- **Tidak ada kebutuhan AI untuk menghitung konflik pada MVP.** Hindari memasukkan model ML ke jalur hitung inti sebelum ada ground truth dan hasil validasi.

### Alur arsitektur satu sesi

1. Instruktur memilih skenario dan seed. API memvalidasi pilihan serta config menggunakan model Pydantic.
2. `Simulator` membuat keadaan internal (truth) dan menghasilkan observasi track tersintesis. Kode memisahkan keadaan simulator dari data observasi yang dipakai detector agar detector tidak membaca masa depan yang hanya diketahui simulator.
3. Simulator bergerak dalam tick 100 ms. Observasi track dibuat per 1.000 ms; konfigurasi dapat menambahkan delay dan noise sintetis. Timestamp observed dan received disimpan terpisah.
4. `Session` menggabungkan track observasi dengan clearance/event latihan, memanggil detektor, memperbarui alert, lalu merekam urutan event dan frame.
5. FastAPI melayani command/status melalui REST dan mengirim snapshot sesi melalui WebSocket. Implementasi lokal saat ini mengirim snapshot berkala sekitar 200 ms.
6. Frontend menampilkan data serta command sesuai role; instruktur membuka sesi/replay dan mengekspor hasil review. Tahap pembuatan UI browser ini masih perlu diselesaikan.

### Algoritma simulasi dan rule engine saat ini

1. **Pergerakan deterministik dengan seed.** `random.Random(seed)` membuat noise yang dapat diulang. Posisi setiap mobile digerakkan sepanjang waypoint berdasarkan speed dan tick simulasi. Skenario dapat menjadwalkan aksi seperti cancellation, go-around, atau kehilangan track.
2. **Koordinat lokal.** Layout saat ini memakai meter dalam coordinate system `LOCAL_METRES`, dengan satu resource fisik RWY-09/27, runway/taxiway, hold line, dan protected area sintetis. Dimensi ini adalah asumsi eksperimen, bukan standar atau geometri bandara nyata.
3. **Footprint dan area terlindungi.** Detector membentuk footprint persegi panjang tiap aircraft/vehicle sesuai panjang-lebar dan heading. Protected area diperluas menggunakan convex hull/Minkowski-sum pendekatan untuk memperhitungkan footprint objek, lalu rute dipotong terhadap area tersebut.
4. **Prediksi interval, bukan collision-time.** Dengan asumsi speed saat ini dan declared route berlanjut, detector menghitung waktu masuk/keluar terhadap area menggunakan jarak/speed dan mengoreksi usia observasi. Untuk dua objek, overlap interval dihitung sebagai `max(0, min(exit_A, exit_B) - max(entry_A, entry_B))`. Itu menunjukkan asumsi okupansi serentak pada geometri simulasi; bukan waktu tabrakan atau probabilitas kecelakaan.
5. **Rentang ketidakpastian.** Parameter eksperimen seperti error posisi, persentase error speed, buffer, usia track, dan horizon memperlebar rentang entry/exit. Track lebih lama dari 3 detik, track hilang, atau route yang tidak diketahui menandai data degraded; sistem tidak boleh menganggap runway clear hanya karena objek tidak terlihat.
6. **Rule yang dapat ditelusuri.** Contoh rule kode mencakup overlap kedatangan/keberangkatan, pelanggaran hold-short, penggunaan runway yang ditutup, izin runway simultan yang perlu diperiksa, sampel lintasan yang menyapu area, dan data track degraded. Setiap kandidat menyimpan rule version, event evidence, asumsi, usia track, metrik, dan waktu hitung.
7. **Indikator kompleksitas tugas.** `task_complexity` menggabungkan hitungan traffic, durasi komunikasi, task pending, aktivitas crossing, visibility rendah, dan emergency menggunakan bobot eksperimen. Kode sudah memberi label bahwa ini bukan diagnosis workload atau fatigue individu. Jangan menyebut skor ini sebagai workload controller tervalidasi.

Parameter awal yang tercantum di model eksperimen mencakup tick 100 ms, sampling 1.000 ms, horizon prediksi 120 detik, stale threshold 3.000 ms, buffer 10 detik, error posisi 5 m, dan error speed 10%. Ini adalah nilai default simulasi yang harus ditinjau; bukan spesifikasi sensor/alert operasional.

### Command, provenance, dan replay

- Kontrak command memuat `command_id` dan `expected_revision` untuk mengurangi command duplikat atau command berdasarkan state lama.
- Event dicatat dengan urutan ordinal, simulation time, audit UTC, aktor/role, objek, dan event evidence. Frame menyimpan snapshot; checkpoint privat dipisahkan dari frame publik.
- SQLite saat ini memakai tabel `sessions`, `events`, `frames`, dan `commands`. Saat proses restart, sesi yang tertinggal running ditandai interrupted dan tidak dijalankan ulang otomatis.
- Review membaca sesi arsip secara read-only; instruktur dapat menambahkan annotation dan membuat branch pada waktu tertentu. Seed serta versi engine/config membantu replay menjelaskan konfigurasi yang menghasilkan sesi.
- Role yang dikenali model mencakup instructor, tower, ground, dan observer. Ini role aplikasi training, bukan mekanisme otorisasi ATC operasional.

### Fase pengembangan teknis

| Fase | Pekerjaan teknis | Keluaran dan gerbang lanjut |
|---|---|---|
| 0. Lengkapi prototipe lokal | Buat `App.tsx`; deklarasikan dan kunci toolchain frontend yang dibutuhkan; petakan TypeScript types ke Pydantic; hubungkan login/session flow ke API dan WebSocket. Jangan hubungkan data live. | Browser app dapat dimulai lokal; endpoint health/skenario/session dapat dicapai; status incomplete UI ditutup. |
| 1. MVP demonstrasi end-to-end | Buat peta 2D sintetis, indikator source/data quality, panel role, playback/control, event timeline, alert explanation, dan status runway latihan; gunakan seed dan scenario catalogue. | Satu alur demo berulang dari pilih skenario sampai debrief; semua objek/event ditandai simulasi; rule dan asumsi dapat ditelusuri. |
| 2. Authoring dan review | Tambahkan edit parameter yang dibatasi template, pause/seek, branch, bookmark, anotasi instruktur, dan ekspor laporan. Kaitkan setiap temuan dengan event ID/timestamp. | Instruktur dapat menjalankan, meninjau, dan membandingkan skenario tanpa mengubah historical source session. |
| 3. Validasi latihan | Domain reviewer meninjau geometri, phraseology, clearance/event, dan rule trace; siapkan protokol, consent, ground truth, serta metrik sebelum studi pengguna. | Catatan validasi dan batas penggunaan; ukur event comprehension, kualitas debrief, usability, false/missed events dalam skenario uji. Tidak ada klaim penurunan insiden. |
| 4. AI offline opsional | Uji satu use case seperti skenario draft dari template atau pencarian/ringkasan dari log terverifikasi; model dibungkus dalam adapter terpisah; simpan versi model/prompt dan sumber. | Draft AI dapat diterima/dikoreksi instruktur, klaim punya evidence link, hasil error dicatat. AI tidak mengendalikan simulator atau menerbitkan clearance. |
| 5. Sandbox riset berbasis data mitra | Tambahkan adapter impor terbatas untuk satu format/data source berizin, pemetaan waktu/ID, access control, audit, retention, degraded mode, dan security review. | Sandbox read-only dan data source/status jelas. Perlu sponsor serta persetujuan sebelum data operasional digunakan. |
| 6. Integrasi operasional potensial | Baru dianalisis bila diminta organisasi berwenang; lakukan system safety assessment, human factors, security accreditation, interface/change control, fallback, monitoring, serta persetujuan regulator/ANSP. | Proposal terpisah berdasarkan site/use case. Bukan bagian dari MVP, bukan jaminan dapat disetujui, dan tidak ada tanggal yang dijanjikan. |

Fase adalah gerbang kemampuan, bukan janji tanggal. Jangan mulai fase selanjutnya hanya karena prototipe dapat ditampilkan; syarat data, review domain, bukti, dan sponsor harus dipenuhi.

### Keluaran MVP yang dapat ditunjukkan ke mentor/juri

**Produk demonstrasi:** aplikasi web lokal yang menjalankan satu skenario synthetic dari awal sampai replay/debrief. Backend dan rule engine pada repositori sudah menyediakan sebagian fondasi; antarmuka lengkap dan integrasi browser masih perlu dibuat.

**Isi demo yang direkomendasikan:**

1. **Peta latihan:** satu layout fiktif dengan RWY 09/27, taxiway/hold line, 5 aircraft dan 2 vehicle yang disimulasikan. Watermark “SIMULASI” selalu terlihat.
2. **Katalog latihan:** pilih dari 12 skenario 180 detik yang telah ada, misalnya overlap, safe crossing, stopped vehicle, hold violation, cancelled crossing, delayed go-around, reciprocal runway, atau track dropout.
3. **Kendali instruktur:** start/pause/end, playback speed, seek, branch/replay, clearance/event latihan, request/response, serta variasi visibility/emergency sesuai command yang tersedia.
4. **Timeline dan penjelasan:** pergerakan serta clearance/coordination/readback event, event ID, simulation time, observed/received time, rule yang terpicu, overlap/interval, asumsi speed-route, dan status track stale/missing.
5. **Panel peran:** tampilan latihan untuk tower/ground/observer dan kontrol instruktur. Panel tidak mengirim instruksi kepada operasi nyata.
6. **Review dan artefak:** replay sesi, bookmark/annotation instruktur, ringkasan event, dan ekspor JSON/CSV/HTML melalui API report yang telah ada.
7. **Satu demonstrasi repeatable:** seed, scenario ID, config, dan versi engine dicatat agar juri dapat mengulang hasil yang sama.

**Kriteria selesai MVP:** frontend terhubung ke backend lokal; skenario dapat dimainkan dan direplay; peta serta timeline konsisten dengan event; aturan dan bukti dapat ditelusuri; label simulasi/data quality terlihat; laporan dapat diekspor; tidak ada koneksi atau klaim live ATC.

**Bukan keluaran MVP:** voice ASR live, ADS-B/radar live feed, flight plan/clearance real, vehicle GPS mitra, AI menentukan clearance, severity risiko yang tervalidasi, controller workload score, operasi airport dashboard, sertifikasi, atau klaim pencegahan kecelakaan.

### Naskah singkat menjelaskan rencana teknis

> Secara teknis, backend FlowLens menggunakan Python dengan FastAPI. Simulator berjalan dengan seed agar skenario dapat diulang; Shapely menghitung geometri 2D dan rule engine memprediksi rentang okupansi runway dari track, rute, speed, usia data, dan buffer. State serta event disimpan ke SQLite untuk replay. Frontend yang akan kami lengkapi menggunakan React dan TypeScript, menerima snapshot melalui API/WebSocket, lalu menampilkan peta latihan, event timeline, dan penjelasan rule. MVP keluarannya adalah aplikasi web lokal berbasis skenario sintetis, instruktur dapat mengontrol sesi, memutar ulang hasil, dan mengekspor debrief. AI tidak berada di jalur clearance; jika dipakai nanti, AI hanya membantu draft skenario atau ringkasan dari event terverifikasi.

### Pertanyaan teknis untuk mentor

| Potensi pertanyaan | Jawaban/rekomendasi |
|---|---|
| Mengapa Python, FastAPI, dan Shapely? | Stack itu sudah digunakan backend repo: Python menangani model/simulasi/API, FastAPI memberi REST/WebSocket, dan Shapely menghitung bentuk/irisan geometri. Pertahankan dulu agar tim fokus menutup alur MVP. |
| Algoritmanya AI atau rule-based? | Deteksi inti sekarang rule-based dan deterministik. Untuk domain keselamatan simulasi, rule trace dan asumsi dapat diperiksa. AI bisa diuji terpisah untuk authoring/debrief setelah ada label dan review. |
| Apa arti overlap 16 detik? | Itu durasi interval okupansi sintetis yang diprediksi overlap pada geometri eksperimen. Bukan time-to-collision atau peluang kecelakaan. UI perlu menampilkan interval, sumber, error/buffer, dan asumsi. |
| Apakah peta dan ukuran sama dengan bandara tertentu? | Tidak. Kode menggunakan layout lokal sintetis satu RWY-09/27; dimensi protected area diberi catatan sebagai asumsi eksperimen. Layout bandara nyata baru boleh dipakai setelah verifikasi dan izin. |
| Sudah ada aplikasi browser lengkap? | Belum dapat dinyatakan siap berdasarkan berkas yang diperiksa: `main.tsx` mengimpor `App`, tetapi file `App.tsx` belum ada dan dependency build Vite belum tercantum. Tahap teknis pertama adalah melengkapi UI/toolchain dan menyambungkannya ke backend. |
| Apa yang membuat MVP selesai? | Satu skenario dapat dimainkan berulang, timeline konsisten, alert menjelaskan rule/evidence, data synthetic tampak jelas, instruktur dapat replay/debrief, dan laporan dapat diekspor. Semua masih lokal dan non-operasional. |

## 9. Hal yang sebaiknya diminta dari mentor

1. **Validasi scope:** apakah simulator training/replay/debrief merupakan titik awal yang tepat?
2. **Validasi pengguna:** apakah instruktur, trainee, safety office, atau peneliti menjadi pengguna pertama?
3. **Validasi skenario:** jenis situasi runway apa yang paling tepat untuk skenario demonstrasi, dan siapa yang berwenang meninjaunya?
4. **Validasi metrik:** ukuran apa yang cukup untuk menyebut pilot latihan berguna tanpa membuat klaim keselamatan berlebihan?
5. **Jalur mitra:** lembaga atau peran apa yang perlu didekati untuk memperoleh review domain dan, kemudian, data berizin?
6. **Persiapan data:** persetujuan, de-identifikasi, keamanan, retensi, dan penghapusan apa yang perlu menjadi syarat sebelum uji riset?
7. **Batas produk:** fitur mana yang harus dikeluarkan dari demo agar tidak disalahartikan sebagai clearance atau instruksi operasi?

## 10. Ringkasan satu menit

Kami menemukan bukti teknologi ATM dan surveillance di Indonesia pada lokasi serta layanan tertentu, tetapi bukti publik belum cukup untuk membuat inventaris nasional sistem pemantauan permukaan bandara atau memastikan akses pihak ketiga ke data operasional. Contoh internasional menunjukkan bahwa teknologi surface safety memang digunakan di lokasi tertentu, tetapi deployment luar negeri tidak dapat digeneralisasi ke Indonesia. Karena itu, posisi FlowLens saat ini adalah simulator dan alat replay untuk latihan serta debrief. Kami akan mengembangkan MVP offline, memvalidasinya bersama instruktur, melakukan riset dengan data berizin bila tersedia, dan baru mempertimbangkan sandbox atau integrasi setelah kebutuhan serta proses keselamatannya disetujui.

## Sumber utama

- [Laporan riset FlowLens](ATC_FlowLens_Operational_Reality_Research.md) — audit dokumen, klaim, aktor, teknologi, data, workflow, risiko, roadmap, dan evidence register.
- Bukti Indonesia: [Laporan Tahunan DJPU 2024](https://ppid.dephub.go.id/fileupload/informasi-berkala/20250924124656.LAPTAH_DJPU_2024_compressed.pdf) dan [pengumuman AirNav New JATSC/New ATMAS](https://www.airnavindonesia.co.id/berita-dan-siaran-pers/kunjungi-airnavindonesia-presiden-icao-tinjau-langsung-fasilitas-new-jatsc/).
- Benchmark teknologi permukaan: [FAA ASSC/ASDE-X](https://www.faa.gov/air_traffic/technology/adsb/atc/assc), [FAA RWSL](https://www.faa.gov/air_traffic/technology/rwsl/index.cfm?print=go), [FAA SAI](https://www.faa.gov/airports/runway_safety/airfield_drivers/enhancing-surface-safety-guide-vehicle-movement-area), dan [EUROCONTROL A-SMGCS](https://www.eurocontrol.int/service/advanced-surface-movement-guidance-and-control-system). Contoh ini tidak membuktikan deployment Indonesia.
- Data, komunikasi, dan AI: [FAA SWIM](https://www.faa.gov/air_traffic/technology/swim/products/get_connected), [ICAO Doc 9870](https://www.icao.int/safety/RunwaySafety/Documents/ICAO_manual_prev_RI.pdf), [KNKT Adisutjipto 2013](https://knkt.go.id/Repo/Files/Laporan/Penerbangan/2013/PK-AXG%20%26%20PK-LBH%20Final%20Report.pdf), [ATCO2](https://atco2.org/data), dan [riset speech NASA](https://ntrs.nasa.gov/citations/20240014494). Rujukan ini bukan izin penggunaan audio Indonesia.
