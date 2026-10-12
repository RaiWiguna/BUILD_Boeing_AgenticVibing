# TartanAviation ADS-B: feasibility map dan runway/taxi view

Tanggal pemeriksaan: 11 Oktober 2026. Status: **RESEARCH_ONLY / NOT_DOMAIN_VALIDATED**. Analisis source dan subset selesai; adapter, UI, domain validation, dan integrasi belum diimplementasikan. Penelitian tidak mengubah gate aplikasi.

## Keputusan yang didukung evidence

**Feasible untuk replay titik/lintasan geografis dan konteks approach/departure. Feasible bersyarat untuk preview gerak permukaan yang parsial. Belum cukup untuk taxi view lengkap, taxi-route conformance, hold-short crossing, atau runway occupancy/clearance yang dapat diandalkan.**

Frontend saat ini dapat menjadi fondasi visual, tetapi tidak langsung menerima corpus ini. Ia memakai geometri fiktif, satu runway horizontal, koordinat meter, dan proyeksi skematik. Data KAGC memerlukan layout nyata, konversi koordinat, clock mapping, dan penanganan coverage/uncertainty. Aircraft yang airborne di atas runway tidak boleh ditampilkan sebagai runway occupied hanya karena proyeksi 2D berpotongan dengan polygon.

**50 audio tanggal 10–11 September 2022 belum dapat dipasangkan dengan raw ADS-B dari bucket yang diperiksa.** Arsip KAGC 2022 hanya memiliki member Januari–Agustus. Untuk demo multimodal, pilihan yang masuk akal adalah kandidat audio pada tanggal overlap, misalnya 27 atau 30 Agustus, atau meminta missing subset dari publisher. Audio September tetap berguna untuk Said–Heard, dengan movement NOT_EVALUABLE.

| Kebutuhan | Feasibility | Batas yang menentukan |
| --- | --- | --- |
| Map titik dan observed trail | Ya, melalui adapter | Raw Lat/Lon tersedia; dedup, outlier, clock, gap dan stale wajib ditangani |
| Approach/departure context | Ya, parsial | Pertahankan altitude dan identitas; tidak semua nearby aircraft beroperasi di KAGC |
| Overlay titik pada layout runway/taxiway nyata | Ya secara visual | Layout/CRS/valid-period diperlukan; overlay tidak otomatis membuktikan ground movement |
| Preview potongan taxi kandidat | Bersyarat | Ada low-speed points dekat airport; perlu pemeriksaan layout, sequence dan validasi manusia |
| Rekonstruksi taxi route lengkap | Tidak didukung subset ini | Coverage permukaan tidak authoritative dan kontinuitas pendek/bercelah |
| Hold-short crossing / runway clear / occupancy footprint | NOT_EVALUABLE untuk evidence ini | OnGround tidak disimpan, dimensions/integrity tidak tersedia, ground association belum tervalidasi |
| Replay terhubung dengan 50 audio September | Belum | Raw paired dates tidak tersedia pada listing/ZIP yang diperiksa |

## Metode dan sumber

Semua eksplorasi corpus, request listing/ZIP Range, ekstraksi dan analisis CSV dilakukan melalui SSH ke research VM (`$VM`, host tidak dicatat di repo). Raw CSV/TXT tetap di VM `/home/deploy/flowlens-research/tartan/adsb-research/`. Metadata, ringkasan dan derivative near-airport points disalin kembali melalui SCP ke ignored `outputs/tartan-research/adsb/`; tidak ada full annual ZIP atau audio tambahan diunduh.

Source code diperiksa pada [upstream TartanAviation](https://github.com/castacks/TartanAviation/tree/4065f5bb11c3d8e557dcaf20a56469e6b0738714/adsb), SHA `4065f5bb11c3d8e557dcaf20a56469e6b0738714`. [Paper penulis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11926361/) menjadi acuan definisi field/unit, bukan jaminan bahwa build arsip identik dengan script GitHub. Publisher: [TartanAviation](https://theairlab.org/tartanaviation/); atribusi Patrikar et al., *Image, speech, and ADS-B trajectory datasets for terminal airspace operations*. Label lisensi dataset pada publisher CC BY 4.0; code BSD 3-Clause. Source permission/retention/import tetap perlu dicatat dalam manifest aplikasi.

Inspeksi HEAD, ETag dan central directory dilakukan sebelum pemilihan member. Server mendukung HTTP 206; helper menolak full-download fallback. Ekstraksi menggunakan batas decoded 64 MiB/member dan CRC, size serta SHA-256. Raw ZIP memakai **Deflate64 (method 9)**, sehingga utility `p7zip-full` dipasang pada VM; tiny ZIP berisi hanya member terpilih direkonstruksi untuk decoding. Processed memakai deflate biasa. Utility ini bukan dependency aplikasi.

### Inventory yang benar-benar diperiksa

| Arsip | Ukuran source | Inventory |
| --- | ---: | --- |
| `kagc/raw/2021.zip` | 38,015,073 bytes | 39 CSV harian, 31 Oktober–31 Desember; tidak semua tanggal ada |
| `kagc/raw/2022.zip` | 236,594,743 bytes | 245 CSV pada 240 folder tanggal; Januari–31 Agustus; 16 member berukuran nol; September tidak ada |
| `kagc/processed.zip` | 262,019,001 bytes | 27,416 TXT; nama sequence tanpa tanggal/source mapping |
| `OneDrive-2024-06-21.zip` | 1,969,681,563 bytes | 9 nested archive, termasuk annual/processed/weather yang sama ukuran; tidak ada tambahan raw KAGC 2023 pada inventory luar |

Bucket list juga menyediakan KBTP 2020/2021/2022, processed dan weather. Sample resmi downloader adalah **KBTP 2022**, sehingga tidak dipakai sebagai pasangan KAGC. Inventory luar OneDrive bukan bukti hash payload setiap nested ZIP identik; tidak mengekstrak 1.97 GB untuk memverifikasi itu.

Paper menyebut rentang collection KAGC sampai Februari 2023; objek raw yang terlihat tidak menyediakan rentang akhir tersebut. Kesimpulan ini terbatas pada objek publik yang diperiksa, bukan klaim publisher tidak memiliki data September atau 2023. Processed yang kehilangan tanggal juga tidak membuktikan overlap tertentu.

Member yang diekstrak: `08-27-22/1.csv`, `08-30-22/1.csv`, `processed/1.txt`, `processed/100.txt`, `processed/1000.txt`. Successful extraction passes mentransfer **4,779,251 bytes**, termasuk central directories dan payload HTTP Range (tidak termasuk HTTP headers); bukan total seluruh request investigasi/retry. Dua CSV decoded total **42,749,952 bytes**. Manifest lokal menyimpan source hashes dan ETags; file source tidak diubah.

## Raw schema, timestamp dan units

CSV memiliki 13 kolom:

`ID, Time, Date, Altitude, Speed, Heading, Lat, Lon, Age, Range, Bearing, Tail, AltisGNSS`

| Field | Makna dan penggunaan |
| --- | --- |
| `ID` | Recorder mengambil `Icao_addr`; CSV menyimpan integer decimal. Contoh `10924421` → ICAO hex `A6B185`. Jadikan source identity per sesi, bukan callsign verbal |
| `Date`, `Time` | Sampel aktual berupa list string: `['2022','8','27']`, `['6','2','21']`; parse terstruktur, jangan `eval`. Script processor mengharapkan date/time formatted sehingga tidak langsung kompatibel |
| `Lat`, `Lon` | Decimal degrees; gunakan sebagai basis WGS84 georeferencing setelah validasi CRS terhadap source. Tidak perlu bergantung pada Range/Bearing reference yang belum dibekukan |
| `Altitude` | Feet, paper menyebut MSL; `AltisGNSS` membedakan measurement source. Jangan dianggap AGL/height-above-runway; altitude 0 dan nilai di bawah elevation ditemukan |
| `Speed` | Knots sesuai paper; konversi m/s = knots × 0.514444…; beberapa row kosong dan ada outlier |
| `Heading` | Derajat dari receiver `Track`; arah gerak tidak otomatis body orientation, khususnya pada low speed. Missing heading jangan diisi 0 sebagai pengamatan |
| `Age` | Detik sejak last observation; banyak repeated state sampai hampir 60 detik. Row CSV baru tidak berarti posisi baru |
| `Range`, `Bearing` | km dan derajat relatif north. Referensi inferensi sampel sekitar 40.35132, −79.92398; ini diagnosis perkiraan, bukan airport/layout calibration |
| `Tail` | Dalam CSV mencampur registration, flight callsign, alias dan nilai kosong; satu ICAO ID bisa berubah label sepanjang hari |
| `AltisGNSS` | Boolean string; kedua nilai muncul. Pertahankan provenance measurement dan jangan menyamakan semua altitude datum |

Recorder membuang suffix `Z` dari receiver timestamp dan menghitung Age dengan `datetime.utcnow()`. Ini mendukung interpretasi UTC untuk raw, meskipun suffix hilang dalam CSV. Filename/folder memakai `date.today()`: satu file harian memang melintasi tanggal UTC berikutnya. Jangan menetapkan seluruh row tanggal dari folder. Audio metadata naive masih memerlukan audit clock recording build yang sesuai; kesamaan code upstream bukan bukti offset/drift nol pada semua source.

`t_source + Age` bisa menjadi perkiraan waktu poll/write yang berguna untuk diagnosis. CSV tidak menyimpan authoritative received time atau availability historis tiap item. Jangan mengisi `available_time_ms` sebagai fakta tepat dari nilai perkiraan ini. Mulai dengan **debrief replay**; as-known replay hanya setelah eligibility policy, uncertainty dan mapping diselesaikan sesuai PRD §10.

## Pengukuran dua hari KAGC

Angka cadence/near-airport berikut dihitung pada row dengan position, altitude, speed, heading dan Age lengkap numerik, kemudian dedup `(ID, timestamp)`. Ini diagnostic selection, bukan seluruh posisi yang sah. Posisi dengan speed/heading kosong tetap berguna untuk titik dan harus dipertahankan sebagai partial observations pada adapter nanti.

| Ukuran | 27 Agustus 2022 | 30 Agustus 2022 |
| --- | ---: | ---: |
| CSV data records | 166,736 | 130,372 |
| Usable position rows sebelum dedup | 165,945 | 129,783 |
| Position rows tanpa speed/heading | 1,203 | 1,447 |
| Complete numeric rows | 164,742 | 128,336 |
| Empty records | 790 | 588 |
| Truncated final record | 1 | 1 |
| Unique `(ID, timestamp)` posisi, termasuk partial | 60,990 | 48,783 |
| Unique complete numeric messages | 60,453 | 48,138 |
| Repeated complete rows | 104,289 (63.3%) | 80,198 (62.5%) |
| ICAO IDs pada complete subset | 246 | 223 |
| ID dengan beberapa Tail labels | 58 | 99 |
| Source timestamp span UTC | 27 Aug 06:02:21–28 Aug 02:58:13 | 30 Aug 06:00:03–31 Aug 02:59:59 |
| Raw Age median / p95 | 3.88 / 49.98 s | 3.05 / 49.79 s |
| Raw Age >30 s | 28,561 rows | 21,502 rows |
| Dedup cadence median / p95 | 1 / 6 s | 1 / 5 s |
| Inter-message gaps >60 s per ID | 532 | 357 |
| Unique complete points Range ≤2 km | 3,049 / 59 IDs | 1,656 / 40 IDs |
| Di subset dekat, speed ≤20 knots | 292 points / 12 IDs | 75 points / 9 IDs |

Gap maksimum 66,792 / 59,259 detik termasuk aircraft yang keluar lalu muncul lagi; bukan otomatis receiver outage sepanjang durasi itu. Same-timestamp **position conflicts** terdeteksi 1 / 10 kelompok pada usable-position subset. Kinematics-state conflicts berbeda: 2 / 15 kelompok. Jangan dedup dengan last-row-wins tanpa mempertahankan conflicting variants/provenance. Untuk repeat identik, earliest receipt candidate dan refresh Age perlu dibedakan dari measurement update.

Nilai range raw mencapai 151 km / 1,290 km; speed maksimum 1,688 / 475 knots. Row range ekstrem perlu diperiksa, dan speed 1,688 adalah outlier yang tidak boleh masuk prediction tanpa review. Tidak semua aircraft raw merupakan terminal traffic KAGC. Terapkan validasi fisik/jump checks dan scope filter pada derivative, dengan raw immutable; angka radius/altitude bukan ground-truth classifier.

### Apakah ada data taxi sama sekali?

Ada **indikasi parsial**, sehingga menyatakan “tidak ada ground-like points sama sekali” juga tidak tepat. Pada 27 Agustus, sequence low-speed dekat receiver antara lain `N43AL` 57 detik/57 distinct messages dan `N728AM` 57 detik/51 messages; 30 Agustus yang terpanjang pada filter serupa `N534ME` 19 detik/16 messages. Sequence dibagi ketika source gap >5 s. Batas speed ≤20 knots dan Range ≤2 km hanya heuristik penelitian; bukan definisi taxi atau freshness acceptance.

Namun [recorder upstream](https://github.com/castacks/TartanAviation/blob/4065f5bb11c3d8e557dcaf20a56469e6b0738714/adsb/recording/run_recorder.py) dan [audio-trigger recorder](https://github.com/castacks/TartanAviation/blob/4065f5bb11c3d8e557dcaf20a56469e6b0738714/audio/recording/run_adsb_audio.py) hanya menerima `Position_valid == True` dan `OnGround == False`. CSV tidak menyimpan ground flag. Sampel low-speed dapat terjadi karena build berbeda, receiver classification, state/field carry-over atau transisi landing/takeoff; belum ditentukan penyebabnya. Tidak dapat menyimpulkan bahwa seluruh published row pasti airborne atau bahwa low-speed pasti taxi.

Altitude sumber kadang nol atau lebih rendah dari elevation airport; GNSS/barometric reference, weather, dan quality belum dikalibrasi. Paper tidak menyediakan accuracy/integrity field pada 13-column schema ini. Centre-point trace yang tampak melewati runway tidak membuktikan physical crossing/footprint clearance. Ground vehicles dan pesawat tanpa coverage tidak dapat direkonstruksi dari ucapan.

## Mengapa processed bukan pilihan import utama

Tiga file diperiksa benar-benar berisi **7 kolom comma-delimited tanpa header**, dengan blank lines: Frame, ID, x, y, z, Headwind, Crosswind sesuai paper. Ukuran contoh 375/1,037/9 nonempty rows; Frame berupa float-string seperti `38977.0`. Tidak ada absolute date/time, Tail, Age, original sample IDs, integrity, footprint atau observed/interpolated flag.

[Script process.py](https://github.com/castacks/TartanAviation/blob/4065f5bb11c3d8e557dcaf20a56469e6b0738714/adsb/process.py) yang tersedia:

- Menghapus duplikasi menggunakan Range + Bearing + ID tanpa timestamp; stationary observations yang valid dapat hilang.
- Mengasumsikan date/time formatted yang berbeda dari raw CSV actual list-string.
- Memakai [transform hardcoded KBTP](https://github.com/castacks/TartanAviation/blob/4065f5bb11c3d8e557dcaf20a56469e6b0738714/adsb/utils.py); jangan digunakan untuk KAGC.
- Mengubah posisi/altitude ke km; frontend meminta meter. Interpolasi setiap detik hingga `limit=60` menghasilkan derived points yang tidak diberi label observed/interpolated.
- Menghapus absolute wall-clock dan menyimpan Frame relatif. Writer source memakai space delimiter, sedangkan sample published memakai comma; build/provenance mismatch belum diselesaikan.
- Saat gap global >1 s, membuka file baru tanpa menulis current row pada branch tersebut; boundary row dapat hilang jika script ini dipakai.

Ini audit **script yang tersedia**, bukan bukti script tersebut menghasilkan setiap published TXT. Jangan mengklaim seluruh processed corrupt, menganggap transform sudah benar, atau menampilkan interpolated positions sebagai observed truth. Raw Lat/Lon dan timestamp lebih sesuai sebagai source import yang dapat diaudit.

## Kecocokan dengan frontend yang sebenarnya

Source diperiksa: [SituationCanvas](../../frontend/src/features/workspace/SituationCanvas.tsx), [frontend view DTO](../../frontend/src/api/types.ts), [MOCK world/series](../../frontend/src/api/adapters/mock/world.ts), [Track contract](../../backend/flowlens/contracts/models.py).

| Source saat ini | Implikasi untuk data nyata |
| --- | --- |
| `LayoutView.units = 'm'`, TrackSeries `{t,x,y}` | Lat/Lon harus dikonversi ke satu local metric CRS; source CRS/origin dan layout harus sama |
| `Layout()` hanya menggunakan `layout.runways[0]`, menggambar rectangle horizontal | Belum mendukung dua runway berorientasi berbeda atau polygon general |
| Projection `ky` dapat meregang sampai 2× `kx`; vertical fit berdasarkan drawn layout | Tampilan skematik dapat distorsi heading/distance; tracks approach bisa terpotong. Geographic mode perlu equal aspect dan track-aware viewport |
| `Marker` mengambil last point series; `Trail` memfilter ≤asOf tetapi menyambung semua points | Adapter/snapshot harus melakukan eligibility filtering; trail perlu segment boundaries agar tidak menyambung missing intervals |
| Plane heading default 0 jika Track tidak ada | Missing direction butuh neutral marker/unknown label; jangan menyatakan heading north |
| Footprint false dan POINT_ONLY/MISSING/STALE tersedia | Semantics unknown sudah membantu, tetapi asal measurement/interpolation, altitude, integrity dan gaps perlu view representation |
| Predicted trail terpisah | Raw import awal harus `predicted=[]`; corpus trajectory bukan prediction product yang sudah tervalidasi |
| Strict Track mewajibkan positive length/width, heading dan speed | Raw tidak menyediakan dimensions dan kadang kehilangan kinematics. Belum dapat membuat valid Track jujur hanya dengan mapper; reconcile/version contract point observations lebih dahulu |

[Informasi operator airport](https://flypittsburgh.com/allegheny-county-airport/pilot-resources/aeronautical-information/) mengonfirmasi KAGC memiliki runway **10/28 dan 13/31**, berbeda dari MOCK 09/27. Sumber itu adalah informasi current, bukan surveyed geometry dengan valid-period 2022. Diperlukan airport diagram/layout georeferenced untuk tahun source, runway polygon, taxiway graph, hold-line positions dan uncertainty. Dataset ADS-B tidak menyediakan airport geometry. Diagram visual saja bukan otomatis geometri berakurasi cukup untuk crossing detector.

## Rencana implementasi yang direkomendasikan — belum dijalankan

1. **Reconcile kontrak observation.** Pertahankan dimensions/heading/speed/ground-state/accuracy yang unknown sebagai unknown; jangan dummy dimensions untuk lolos Pydantic. Definisikan point observations, segmented trail, altitude/datum, raw-row provenance, event/availability uncertainty dan layout reference. Reconcile view DTO yang masih PROPOSED_CONTRACT sebelum real integration.
2. **Raw adapter dan quality report.** Parse list-string dengan parser aman, simpan exact source timestamp/string, convert knots/feet secara eksplisit, preserve partial-position rows, detect malformed/truncated rows, conflict variants, repetition dan outliers. ID ICAO adalah anchor per-session; Tail aliases punya effective time dan evidence. STT association tetap kandidat sampai review.
3. **Map replay dahulu.** WGS84 → local ENU atau projected CRS yang dipilih untuk KAGC dengan origin/version terdokumentasi. Plot centre points, source age, altitude dan missing intervals; equal aspect, pan/zoom/fit, semua runway menggunakan polygons. Projection, heading dan unit conversion harus diverifikasi dengan known control points. Tidak interpolasi melewati gap sebagai observation dan tidak menggunakan future point saat as-known replay.
4. **Cari pasangan audio yang overlap.** Inventori audio sudah memiliki 27/30 Agustus; belum diunduh/transkrip. Pilih satu bounded window setelah inspeksi metadata, bukan mengambil banyak audio. Validasi UTC offset/drift dan uncertainty, lalu review callsign/correspondence. Jangan memindahkan September transcript ke August track atau menganggap registration sama berarti flight episode sama.
5. **Surface preview setelah review.** Tinjau contoh low-speed sequences bersama layout 2022; beri label PARTIAL/POINT_ONLY dan status ground kandidat. Kembangkan footprint/conformance hanya bila source lain, reviewed dimensions, ground classification, timing dan layout evidence memenuhi requirement.

Acceptance sebelum integrasi: parser mempertahankan timestamps lintas UTC-date; exact unit/control-point transform; ambiguous/conflicting identities tidak auto-merge; repeated rows tidak memulihkan freshness; gap tidak menjadi solid observed trail; posisi tanpa kinematics tetap dapat direpresentasikan; missing footprint tidak menghasilkan occupancy verdict; airborne/unknown-ground tidak diberi surface clearance; playback eligibility tidak membocorkan future observations. Ini rencana verifikasi, **bukan tests yang sudah lulus**.

## Evidence, cakupan dan performed checks

Ignored evidence: `outputs/tartan-research/adsb/{sample-manifest,analysis,quality-extra,processed-summary}.json`, inventories annual/processed/OneDrive, serta near-airport derivative points. Helper riset: `outputs/tartan-research/tools/adsb_{sample,collect,analyze,extra}.py`. Evidence privat tidak tersedia otomatis pada clone baru; jangan membuat runtime aplikasi bergantung pada path tersebut.

Performed: central-directory inventory, exact bounded member extraction, CRC/decoded-size checks, SHA-256, safe timestamp parsing, row counts/partial fields, distinct messages/conflicts, cadence/Age, identity labels, heuristic near-airport/low-speed sequences, published processed schema, source code/contract/renderer inspection. Dua hari bukan census seluruh corpus; belum ada human/domain review, calibrated ground classification, layout digitization, real adapter validation, provider benchmark, UI integration test atau operational validation. Source frontend/backend tidak diubah.


## Cross-check overlap audio–ADS-B KAGC — 12 Oktober 2026

Perbandingan dilakukan melalui SSH terhadap inventories yang telah disimpan pada riset 11 Oktober, tanpa download source baru/provider call. Listing audio mengabaikan prefix request, sehingga wajib filter exact `kagc/` agar tanggal KBTP tidak terhitung. Direct daily KAGC audio ZIP: 399 tanggal (31 Oktober 2021–17 Februari 2023). Raw ADS-B nonempty-date intersection dengan direct daily audio: **218 tanggal unik**, terdiri dari **21 pada 2021** dan **197 pada 2022**.

| Bulan | Tanggal direct daily audio + nonempty ADS-B |
| --- | ---: |
| Oktober 2021 | 1 |
| November 2021 | 6 |
| Desember 2021 | 14 |
| Januari 2022 | 16 |
| Februari 2022 | 18 |
| Maret 2022 | 20 |
| April 2022 | 29 |
| Mei 2022 | 29 |
| Juni 2022 | 29 |
| Juli 2022 | 28 |
| Agustus 2022 | 28 |

Agustus overlap: 1–17, 19–28, dan 30. Tanggal 18, 29, 31 memiliki raw ADS-B hanya empty member. Dua source CSV yang sudah dianalisis 27/30 Agustus termasuk overlap; audio kedua tanggal masih belum diunduh/transkrip. September 10/11 tetap tidak memiliki paired raw pada inventori ADS-B yang diperiksa.

218 adalah **archive-date availability**, bukan verified timestamp/callsign pairing atau count usable multimodal sessions. Direct daily audio saja dihitung; consolidated `Raw/kagc/...` ZIP dalam listing tidak diinspeksi untuk cross-check ini, sehingga tanggal yang tidak mempunyai direct daily ZIP belum membuktikan audio absent pada semua bundles. KBTP raw 2020/2021/2022 tersedia di bucket, tetapi exact audio overlap KBTP belum dihitung.

Evidence lengkap per tanggal, exact audio archive key dan ADS-B member/size: ignored `outputs/tartan-research/adsb/audio-overlap.json`, salinan VM `adsb-research/audio-overlap.json`. Checks 218 unique dates, exact airport filtering, nonempty-member selection PASS. Tidak ada adapter/UI/data integration berubah.
