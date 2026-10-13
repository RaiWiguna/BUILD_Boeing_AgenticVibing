# Session Handoff — ATC FlowLens

| Atribut | Nilai |
| --- | --- |
| Tanggal pembaruan handoff | 13 Oktober 2026 (Asia/Jakarta), dokumentasi attention dan delivery branch |
| Objective terkini | Lima case demo tambahan diimplementasikan dan diverifikasi lokal; skenario 87/88 tetap dibekukan |
| Status | Demo workspace selesai dan terverifikasi lokal (track demo, ADR 0003). Riset transkrip/ADS-B tetap RESEARCH_ONLY / NOT_DOMAIN_VALIDATED. Foundation contract 1.0.0 tidak berubah |
| Candidate | Baseline e325f7e; expansion dikirim pada branch `feat/fe-init` sesuai instruksi pengguna; candidate SHA tersedia melalui `git log` |
| Next focus | Gunakan Import → Case untuk 50/51/47/156/123; before50 opsional bagi51. Rebuild Docker bersih setelah DNS tersedia; source critical slots tetap unreviewed |
| Gate | Riset corpus tidak mengubah G-BE/G-FE/G-DELIVERY; G-FE tetap blocked pada track MOCK |

## Deliverables dan decisions foundation — historis 8 Oktober 2026

FR/AC audit, offline/provider/P1 scope, external dependencies, ownership/transaction/migration policy, evaluation protocol/oracles/actual synthetic fixtures, independent A/B packets, ADR 0002. Python 3.12/root pyproject/uv.lock; strict Pydantic models/ports/errors; ModuleRegistration; schema generation/drift; disposable constrained SQLite/UOW; fake platform/analysis and CLI/API MOCK harness.

Mulai dari [developer workflow](../docs/development/backend-foundation.md), [A/B packets](../docs/development/backend-packets.md), [shared contracts](../docs/api/shared-contracts.md), dan [evidence record](../docs/testing/phase01-evidence.md). Baseline memakai default Q-01 offline replay dan Q-02 Gemini Developer API; P1 query/metrics tetap scheduled. Target model/API belum verified, tidak diganti.

A/B tidak mengimpor internals pihak lain. Host API memiliki transaksi/DB writer; worker tidak membuka DB. Shared inputs ada di tests/fixtures dan contracts/examples; evaluator truth/labels/oracles terpisah di evaluation. MOCK profiles tidak boleh production. Real implementations baru di-composition pada Phase 10 setelah kedua packet acceptance selesai.

## Performed checks foundation — historis 8 Oktober 2026

66 shared contract tests PASS pada masing-masing track A dan B; CLI both tracks provider_calls=0; lint/format/mypy, schema drift, constrained fresh/upgrade/FK/rollback/receipt tests, source distribution/wheel build dan independent clean wheel install PASS. Bandit 0 issues, pip-audit no known dependency vulnerabilities (unpublished project skipped), scoped secret patterns/document links/fences/tables/whitespace checked. Detailed commands, versions, outputs and limits: evidence record.

## Limitations / external dependencies foundation — historis 8 Oktober 2026

Foundation bukan production API atau G-BE. Historical archive migration, auth/grants, actual import/replay/geometry, worker/SDK/provider adapters dan domain pipeline belum diimplementasikan. Real STT/Gemini model/API/account/region/quota/budget belum tersedia/verified; no provider smoke. TTS script NOT_GOLD (audit pronunciation/time pending), NOT_DOMAIN_VALIDATED; no held-out/domain/operational benchmark. Real source rights/partner/reviewer/VM/domain/backup operator tidak diasumsikan tersedia.

## Runtime / cleanup foundation — historis 8 Oktober 2026

Tidak ada server/worker/container persisten dimulai. Disposable DB/clean install tempdir ditutup/dihapus. Local .venv dan ignored artifacts/reports tetap tersedia untuk developer/evidence. Tidak ada cloud inference, provisioning, commit/push, merge atau deployment pada task ini.

## Next action foundation — konteks historis

A/B dapat mulai dari frozen baseline 1.0.0 dan menjalankan pytest --track A/B mandiri. Reconcile/version perubahan breaking sebelum Phase 10; credential/model readiness sebelum real smoke. Frontend tetap menunggu G-BE; container/deployment menunggu gate sesudahnya.

## Acuan desain frontend — 8 Oktober 2026

Permintaan desain pengguna menghasilkan [8 referensi halaman](../docs/design/2026-10-08-flowlens/README.md), galeri lokal, token usulan, prompt dan manifest. Visual mengikuti screenshot pengguna dan disesuaikan dengan research replay, evidence/review, unknowns, serta Said–Heard–Observed. Data ilustratif SYNTHETIC; status DESIGN_REFERENCE_ONLY. Tidak ada implementasi React, pipeline/provider call, atau perubahan gate/roadmap. Gunakan spesifikasi semantics/state bersama PRD ketika frontend dimulai setelah G-BE.

## Frontend MOCK track — 8 Oktober 2026

Atas keputusan pengguna, frontend penuh diimplementasikan di `frontend/` memakai mock data in-browser (Phase 11–13 `in_progress (MOCK)`; G-FE tetap `blocked`). Seluruh layar comp 01–08 plus Login/role switcher, Metrics dan Ask (P1), Settings (account + admin) dan Help tersedia; audio visual-only, UI English light theme. Data layer memakai port `ApiClient` dengan `MockApiClient`; integrasi nanti cukup mengganti adapter di `ApiProvider`.

Checks: typecheck, ESLint, contract type drift, copy guard (85 files), Vitest 41 tests (unit mock engine, component journeys, axe per route), build dengan route code-splitting, scan audio/secret/path pada `dist`, serta 15 Python Playwright MOCK journeys PASS. Detail, cakupan yang belum otomatis, dan batasan: [frontend MOCK evidence](../docs/testing/frontend-mock-evidence.md).

M3 QA (9 Oktober): 15 MOCK journeys (termasuk import, E2E-01–05, connection lost, keyboard) lulus terhadap `vite preview`; axe per route (20 route) tanpa pelanggaran serious/critical; sweep console 77 route bersih; tanpa overflow horizontal di 390/720/1024 px. Delapan bug UI/mock ditemukan dan diperbaiki (seleksi transcript setelah revisi, label run duplikat, sidebar 1280×720, path NaN, fokus evidence drawer, tiga temuan axe, overflow ponsel). Panduan: [frontend MOCK developer guide](../docs/development/frontend-mock.md).

UX pass (9 Oktober, sore): fase UX-1 s.d. UX-5 dari [rencana UX](../docs/development/ux-improvement-plan.md) diimplementasikan beserta pass desain/kepadatan (keputusan D-1 s.d. D-4). Vitest 48 PASS, 15 journeys PASS, typecheck/lint/copy/type-drift/build bersih, sweep overflow/console bersih. Deviasi: Workspace 1280×720 menampilkan 2 strip + isyarat scroll.

Next: tambahkan `pytest-playwright` via `uv add --dev pytest-playwright` (uv tidak tersedia di sesi ini); walkthrough keyboard-only penuh dan uji screen reader nyata; ganti adapter MOCK ke HTTP setelah G-BE `passed`. Belum commit/push.

## Memory riset TartanAviation — 11 Oktober 2026

### Scope dan keputusan pengguna

Pengguna meminta eksplorasi TartanAviation, subset kecil dahulu, cek transkrip bawaan, lalu Google STT bila tidak tersedia. Scope kemudian dipertegas **hanya analisis transkrip**, tanpa implementasi aplikasi. Pilot tiga file diperluas menjadi **20 file total**, lalu pengguna meminta **30 file tambahan**, sehingga sekarang **50 WAV unik**. Semua source exploration/download dan transkripsi dilakukan **melalui SSH ke research VM** (host tidak dicatat di repo; tanyakan pengguna). Jangan berpindah ke download dataset lokal atau menambah file/provider calls otomatis hanya karena helper tersedia.

Permintaan terbaru: simpan memory lengkap ini dahulu, kemudian analisis mendalam ADS-B dan feasibility untuk map/runway/taxi view seperti frontend sekarang. Analisis/data sampling berizin; belum ada instruksi integrasi aplikasi, perubahan kontrak, deployment atau penggunaan operasional.

### SSH dan lokasi runtime

- Chat bootstrap yang sudah dibaca: `Create SSH bootstrap script`, thread `01a12b38-1bb3-7f92-8d88-45091c3433d2`, host `local`. Jika perlu mengandalkan isi chat pada konteks baru, panggil `read_thread` kembali.
- Login teruji: user `deploy` pada research VM, port 22, `BatchMode=yes`, `IdentitiesOnly=yes`. Host dan key disimpan di luar repo.
- Private key: path lokal milik pengguna, tidak dicatat di repo. Jangan menyalin atau mencetak isi private key.
- Host key telah diterima pada koneksi pertama; gunakan known_hosts yang sudah ada. User deploy memiliki sudo; tidak ada perubahan SSH/firewall/bootstrap dilakukan dalam riset ini.
- VM research root: `/home/deploy/flowlens-research/tartan/` (parent research private). Python 3.10.12; utility `ffmpeg` dan `python3-venv` dipasang untuk analisis. Ini bukan runtime Python 3.12 aplikasi atau deployment aplikasi.
- Upstream shallow clone: `upstream/`, SHA **4065f5bb11c3d8e557dcaf20a56469e6b0738714**. Metadata website/Zenodo/listing/inventory disimpan di research root.
- Metadata VM yang diperiksa: GCP project `flowlens-511308`; attached account `659807574503-compute@developer.gserviceaccount.com`. Metadata scopes yang terlihat tidak mencakup Cloud STT/cloud-platform. Akses SDK/API V2 belum diuji atau dikonfigurasi; jangan menganggap attached identity siap STT.

### Dataset, rights dan cara download

Publisher: https://theairlab.org/tartanaviation/ dan https://github.com/castacks/TartanAviation. Halaman dataset menyatakan CC BY 4.0; code repo BSD 3-Clause. Atribusi penulis ada pada report. Zenodo `10.5281/zenodo.14699102` mengarsipkan software, bukan seluruh audio/transkrip. Research permission dalam run adalah otorisasi pengguna + attribution publisher untuk hasil privat; **belum menjadi permission profile import aplikasi atau persetujuan redistribusi audio**.

Repository/publisher, bucket listing dan central directory tiga ZIP diperiksa: KBTP 2020-11-02, KAGC 2022-09-10, KAGC 2023-02-01. ZIP yang diperiksa hanya mempunyai directory/WAV/TXT. Seluruh 13 TXT sample KBTP dan sidecar 50 WAV KAGC memuat timing, bukan ucapan. Tidak ditemukan transkrip bawaan pada sumber yang diperiksa; bukan pembuktian semua turunan dataset di internet tidak punya transkrip.

Sample resmi audio KBTP berukuran sekitar 314 MB compressed dan 13 WAV, kurang cocok untuk fokus Tower/Ground dibanding KAGC. Semua 50 WAV yang dipakai berasal dari **`kagc/2022/9/09-10-22_audio.zip`**, arsip **1.206.610.256 bytes**. Exact path memakai bulan `9`; downloader upstream memakai zero-padding sehingga path `.../09/...` bisa 404. `kagc/2023/2/...` juga memakai bulan tanpa padding. Gunakan listing nyata, bukan menebak path.

Akses bucket menggunakan public Swift URL di upstream downloader, tanpa credential. Helper memakai HEAD/HTTP Range dengan ETag/If-Match, validasi 206/Content-Range, CRC dan decoded size, explicit selected members, bounded transfer; **tidak ada fallback full ZIP download**. Raw source immutable; TXT dan hashes terarsipkan. Seleksi tambahan berdasarkan compressed size terkecil berikutnya; **bias ke potongan pendek dari satu arsip, bukan representatif atau held-out benchmark**.

### Volume dan hasil nyata

| Cakupan | Jumlah file | Audio decoded | Segment berteks | Source transfer |
| --- | ---: | ---: | ---: | ---: |
| Awal | 20 | 1.397,441744 s / 23:17,4 | 32 | 60.414.093 bytes |
| Tambahan terakhir | 30 | 3.392,592674 s / 56:32,6 | 91 | 150.073.793 bytes |
| Total | **50 unik** | **4.790,034418 s / 1:19:50,0** | **123** | **210.487.886 bytes** |

Total **120 chunk source unik selesai**, **327 hasil provider dengan alternative kosong**. `127.wav`, `113.wav`, `169.wav` tidak menghasilkan segment berteks. Alternative kosong/no text bukan bukti tidak ada ucapan, radio diam, tidak ada readback, atau tidak ada clearance. Total transfer mencakup ZIP index dan sidecar; tidak mengunduh ZIP penuh. Tidak ada ADS-B/video/geometry diunduh selama tugas transkrip terdahulu.

### Konfigurasi STT, credential dan failure

Google STT penelitian memakai **V1 REST**, `latest_long`, `en-US`, mono PCM16 16 kHz, word offsets, automatic punctuation. Source WAV mono float32 44,1 kHz. Silence dipertahankan; chunk maksimal 50 s, tanpa overlap. Max dua request provider bersamaan. Hints callsign tidak ditambahkan. API key diberikan pengguna di chat dan dikirim ke proses lewat stdin; **nilainya tidak disimpan dalam handoff, source, artefak atau Git**. Jangan mencetak key/log header atau menganggap credential masih tersedia di environment pada sesi baru.

Preflight tanpa audio menunjukkan key dapat mencapai V1. Ini eksperimen terpisah, **target SDK `google-cloud-speech`/API V2 aplikasi tidak berubah**. Produksi/provider V2, quota/budget/region/recognizer dan kualitas domain belum verified.

Pilot pertama gagal parsing alternative kosong; respons lengkap dipakai kembali tanpa request audio duplikat. Pada ekspansi 20, satu batch terhenti karena non-JSON HTTP error; tiga respons lengkap direuse dan batch diselesaikan dalam output baru. Ekspansi **30 tambahan seluruh tujuh batch selesai attempt pertama**, tanpa retry STT. Helper recovery menyimpan run baru dan cached provider responses, bukan menimpa raw source.

Satu pass perbandingan **hanya tiga file pilot** memakai `latest_short` +9 dB gain derivative: menghasilkan satu segment, gagal memperbaiki kelengkapan, sehingga tidak diperluas. Source tidak diubah. Model dan gain berubah bersamaan; bukan eksperimen yang mengisolasi penyebab. Pass perbandingan bukan tambahan file/source atau bagian 120 chunk unik final.

### Shortlist terbaru dan batas interpretasi

| Prioritas / kebutuhan | File / rentang relatif WAV | Isi yang menarik | Hal yang wajib diperiksa |
| --- | --- | --- | --- |
| Ground route revision | **88.wav 0–70 s**, inti **40–70 s** | Opposite-direction taxi traffic; change of plans; Alpha/Golf; crossing/hold-short; readback panjang | Runway di sisi Said rusak, angka di Heard belum mengisi kata Said; jangan menyatakan match/mismatch otomatis. Callsign/speaker/condition belum verified |
| Landing/readback | **51.wav 50–86 s** | Departure-roll context; runway 13 clear to land; kemungkinan readback; turnout untuk objek lain | Jangan kaitkan seluruh turnout ke pesawat landing; report gerakan bukan track |
| Multi-object Tower | **50.wav 6–37 s** | Midfield left downwind, runway 13, Duchess/backtaxi, takeoff ke objek lain | Jangan menyatukan suffix Quebec dengan Alpha |
| Request → landing | **15.wav 18–38 s** | Short-approach request dan kemungkinan approval/landing clearance | `of April`/`tournaments approve` salah-dengar kandidat, bukan qualifier yang diterima |
| Readiness → takeoff | **47.wav 9–33 s** | Holding short/ready, takeoff runway 13, backtaxi if needed | Callsign/condition belum pasti; tidak ada readback utuh |
| Clearance memory | **156.wav 24–75 s**, inti **56–74 s** | Standby, route/departure, maintain 3,000, FL180/10 min, squawk 4131 | STT literal **Except**, bukan expect; future expectation belum accepted. Route/callsign rusak |
| Taxi + outbound | **22.wav 44–84 s** | Alpha 3/parking; Manassas/Allegheny 9; maintain 3,000/squawk 7402; instruksi ke Archer/Golf | Boundary 50 s, identity 651, dan `Correct` bukan full readback/closure |
| Handoff | **123.wav 36–53 s** | Contact departure 119.35 dan pengulangan frequency | Heading/callsign ambiguous; exchange 100–106 s berpotensi untuk objek lain |
| Alternatif | **116.wav 47–74 s**; **24.wav 83–98 s**; **44.wav 0–10 s** | Landing runway 10; touch-and-go runway 13; report turning final/will report | Touch-and-go bukan full-stop; acknowledgment bukan completion |

Cadangan cohort awal: `71.wav` 0–50 s (line up/wait → takeoff candidate), `55.wav` 15–30 s (turn/contact ground), `96.wav` 24–41 s (turn/taxi), `76.wav` 12–29 s (landing exchange). Tidak ada human listening/domain validation pada tasks transkrip.

`50.wav` metadata start 2022-09-10 15:09:10.399481, end 15:10:15.420189; `51.wav` start 15:11:10.402367. Ada **gap 54,982 detik** yang wajib dipertahankan. Kemiripan suffix Quebec hanya kandidat association, bukan flight continuity terbukti. Kemiripan Archer/Golf/Cardinal/Hotel antarfile juga tidak cukup untuk merge identity.

Source timezone belum verified; beberapa TXT tanggal 11 September meski folder 09-10. TXT duration sekitar 0,05–0,08 s lebih panjang daripada decoded WAV pada contoh yang diperiksa. Event time/available time/processing time tetap dipisah. Cloud STT available-at adalah waktu analisis 2026, bukan waktu radio 2022. Jangan memakai corrected STT/as-of hasil 2026 sebagai tersedia historis saat replay 2022.

Status semua transkrip **STT_HYPOTHESIS / NOT_DOMAIN_VALIDATED**. Belum ada reference manusia, WER, critical-slot accuracy, correct-pairing score, speaker attribution authoritative, atau klaim manfaat operasional. Tanpa paired track/geometry, movement conformance tetap **NOT_EVALUABLE**. Clearance/ucapan vacated/takeoff tidak membuktikan observed movement.

### Artefak, helper dan reproducibility

Local research root: `/Users/khalfanishaquille/Documents/GitHub/BUILD_Boeing_AgenticVibing/outputs/tartan-research/` (**di-ignore, tidak masuk Git**). Handoff ini menyimpan keputusan/evidence ringkas agar masih dipahami tanpa artefak privat; jangan menganggap `outputs/` tersedia pada clone baru.

- [Analisis final 50 file](../outputs/tartan-research/transcriptAnalysis50.md), [katalog raw text/offsets](../outputs/tartan-research/transcriptCatalog50.md), [JSON 50](../outputs/tartan-research/transcripts50.json), [CSV ringkasan](../outputs/tartan-research/transcripts50.csv).
- [Metadata/results tujuh batch +30](../outputs/tartan-research/plus30-results.json), [analisis 20](../outputs/tartan-research/transcriptAnalysis20.md), [analisis pilot](../outputs/tartan-research/transcriptAnalysis.md).
- `sample-manifest.json`, `expanded/manifest-{1,2}.json`, `original-stt/run.json`, `expanded/group-{1,2,3}/run.json`, `comparison-stt/run.json`: source inventory/ETag/SHA/TXT, full raw word timing dan configs.
- Ignored helper `tools/`: `tartan_sample.py`, `tartan_transcribe.py`, `tartan_transcribe_gain.py`, `expand_transcripts.py`, `expand30.py`, `collect_plus30.py`, `build_analysis20.py`, `build_analysis50.py`. Ini alat riset privat, bukan adapter aplikasi/tested production code.
- VM WAV/TXT: `kagc-pilot/`, `kagc-expansion-{1,2}/`, `kagc-plus30-01/` sampai `kagc-plus30-07/`. Raw provider JSON: `stt-pilot-*`, `stt-expansion-1/`, `stt-expansion-2-retry/`, `stt-expansion-3/`, `stt-plus30-*-attempt-1/`. Failed/older runs tetap dipertahankan untuk audit.
- VM selection/inventory: `kbtp-inventory.json`, `09-10-22_audio.zip.inventory.json`, `02-01-23_audio.zip.inventory.json`, `expansion-selection.json`, `expansion30-selection.json`, `expansion30-groups.json`, `expansion30-status.json`.

Checks final: 30 tambahan/50 total non-duplicate source hashes, manifest/source SHA matching, 120 contiguous source-chunk mappings dan bounded word offsets, 50 CSV rows, report links, absence API-key pattern pada artefak, permission file lokal 0600, dan `git diff --check` PASS. Checks ini memverifikasi integritas/metadata, bukan kebenaran ucapan. Source aplikasi tidak berubah; untracked `.claude/` sudah ada dan tidak disentuh.

Semua job riset terdahulu selesai; tidak ada server/worker/container/background process ditinggalkan. Utility/data/artefak privat dipertahankan. Tidak ada commit/push/merge/deploy atau perubahan gate.

### Rencana awal ADS-B — historis, sudah dieksekusi 11 Oktober 2026

Paragraf berikut merekam rencana sebelum eksplorasi; hasil dan next action terkini ada pada bagian hasil ADS-B dan checkpoint 12 Oktober.

Eksplorasi lewat SSH. Utamakan KAGC 2022-09-10/11 yang dapat disejajarkan dengan source audio, bukan sample resmi KBTP 2022 yang beda airport. Inspeksi ZIP directory/metadata dahulu dan unduh subset CSV kecil. Audit raw vs processed schema, coordinate/time units/reference, identity/callsign, sample cadence/gaps, posisi dekat runway/apron/taxiway, on-ground flags/coverage dan alignment audio. Baca frontend map/situation DTO/renderer yang sebenarnya. Kesimpulan harus memisahkan feasible geographic replay dari reliable surface occupancy/taxi routing/conformance. Tidak otomatis mengubah MOCK map atau mengklaim raw ADS-B memiliki seluruh ground vehicles/surface movements.


## Hasil eksplorasi ADS-B — 11 Oktober 2026

Laporan lengkap: [feasibility map/runway/taxi view](../docs/data/tartanAdsbFeasibility.md). Ini hasil riset, bukan implementasi adapter/UI atau persetujuan perubahan kontrak. Semua source request, ekstraksi dan analisis CSV dilakukan lewat SSH VM yang sama.

**Kesimpulan:** geographic point/trajectory replay dan approach/departure context feasible melalui raw adapter; partial surface preview bersyarat. Full taxi route, hold-short crossing, runway occupied/clear dan footprint conformance belum didukung evidence ini. Jangan menganggap low-speed atau overlap 2D dengan runway sebagai observed ground movement. Pertahankan movement NOT_EVALUABLE ketika alignment/ground/footprint/layout tidak cukup.

### Availability dan sampling

- Public ADS-B bucket listing diperiksa. `kagc/raw/2021.zip` 38,015,073 bytes / 39 CSV; `kagc/raw/2022.zip` 236,594,743 bytes / 245 CSV pada 240 folder tanggal Januari–Agustus, 16 empty members; `kagc/processed.zip` 262,019,001 bytes / 27,416 TXT.
- **Tidak ada member KAGC raw 10–11 September 2022** pada inventories yang diperiksa. Tidak dapat memasangkan 50 audio existing dengan data tanggal lain. Paper collection berakhir Februari 2023, tetapi raw bucket saat pemeriksaan tidak menyediakan KAGC 2023. Jangan menyimpulkan publisher tidak memiliki missing data.
- `OneDrive-2024-06-21.zip` 1,969,681,563 bytes berisi sembilan nested annual/processed/weather ZIP dengan ukuran sama dengan objek terpisah; hanya inventory luar diperiksa, tidak mengunduh full ZIP atau memverifikasi hash semua nested payload. Tidak ada raw KAGC 2023 pada inventory luar.
- Diekstrak hanya **dua CSV** `08-27-22/1.csv` (23,953,408 decoded bytes, SHA `e2b4475b05f10c25bf78a7db64ebfd8ee3a62f8024e2a88cd9b86a1c07fa00e2`) dan `08-30-22/1.csv` (18,796,544 bytes, SHA `dcac0d857749d3daa145b4259acd28b186ce4bf0bcba1a467723633daf009455`), plus `processed/1.txt`, `100.txt`, `1000.txt`.
- Successful member collection passes transfer 4,779,251 payload bytes termasuk ZIP directories; bukan total seluruh investigation requests/retries. HTTP Range strict 206/ETag, decoded-size/CRC/SHA checks, no full annual archive fallback. Method 9 Deflate64 pada raw: VM `p7zip-full` dipasang, tiny selected-member ZIP reconstructed untuk decode. Processed method 8.
- Audio listing existing juga menyediakan 27/30 Agustus; **tidak ada audio tambahan diunduh atau STT call** pada task ADS-B ini. Itu kandidat next sampling bila demo multimodal dipilih.

### Schema, quality, time dan identity

13 raw columns: ID, Time, Date, Altitude, Speed, Heading, Lat, Lon, Age, Range, Bearing, Tail, AltisGNSS. ID adalah decimal `Icao_addr` (contoh 10924421 → A6B185); Tail berisi campuran registration/flight callsign/alias/empty, bukan registration authoritative. Effective-time aliases dan per-flight episode association diperlukan; jangan merge STT hanya berdasarkan suffix.

Date/Time actual **list-string**, bukan format yang diasumsikan processor. Gunakan parser aman tanpa eval; pertahankan source string. Recorder menghapus `Z` dari timestamp dan memakai utcnow untuk Age, mendukung interpretasi UTC raw. Folder memakai date.today dan CSV melintasi UTC-date berikutnya. Exact audio/raw cross-source offset/drift belum diverifikasi. `source timestamp + Age` hanya receipt/poll approximation, bukan authoritative available time. Debrief dahulu; as-known eligibility perlu policy/uncertainty, jangan fabricated historic availability.

Unit acuan paper: Lat/Lon degrees, altitude ft MSL dengan AltisGNSS provenance, speed knots, heading derajat (receiver Track), Range km, Age seconds. Convert ke metric derivative; altitude bukan AGL, heading bukan body heading authoritative. Raw dimensions, ground flag, integrity/accuracy fields tidak tersedia. Gunakan Lat/Lon untuk CRS, bukan hardcoded KBTP Range/Bearing transform.

| Ukuran | 27 Agustus | 30 Agustus |
| --- | ---: | ---: |
| CSV records | 166,736 | 130,372 |
| Usable position rows | 165,945 | 129,783 |
| Position tanpa kinematics | 1,203 | 1,447 |
| Complete numeric rows | 164,742 | 128,336 |
| Empty / truncated-final records | 790 / 1 | 588 / 1 |
| Unique complete ID+timestamp | 60,453 | 48,138 |
| Repeated complete rows | 104,289 (63.3%) | 80,198 (62.5%) |
| ICAO IDs complete subset | 246 | 223 |
| Age median / p95 (seconds) | 3.88 / 49.98 | 3.05 / 49.79 |
| Dedup cadence median / p95 (seconds) | 1 / 6 | 1 / 5 |
| Gaps >60s per ID | 532 | 357 |
| Unique complete points Range ≤2km | 3,049 | 1,656 |
| Nearby speed ≤20kt points / IDs | 292 / 12 | 75 / 9 |

Cadence/near counts memakai complete numeric subset; position-only rows tetap harus dipertahankan dalam future adapter. Unique positions termasuk partial 60,990 / 48,783; same-timestamp position conflicts 1 / 10 groups; kinematic-state conflicts 2 / 15. Dedup last-row-wins dalam helper adalah diagnostic selection, bukan approved adapter policy. Repeated row Age tidak menandakan measurement baru. Maximum gaps dapat berupa aircraft reappearance, bukan global outage. Range maksimum 151/1290km, speed maksimum 1688/475kt; outliers/scope perlu screening derivative tanpa mengubah raw.

Ada low-speed near-airport sequences kandidat: 27 Agustus N43AL 57s/57 points, N728AM 57s/51 points; 30 Agustus N534ME 19s/16 points (segment split gap>5s, speed≤20kt, Range≤2km). Ini heuristik riset, **bukan taxi labels**. Recorder upstream ADS-B dan audio-trigger memfilter `OnGround == False`; published CSV tidak menyimpan flag dan actual low-speed bisa berasal dari receiver/build/transition/field carry-over. Penyebab belum diverifikasi; jangan klaim semua published rows airborne atau semua low-speed ground.

### Processed dan frontend

Published sample TXT comma-delimited tujuh kolom tanpa header + blank lines; 375/1037/9 nonempty rows. Relative float-string Frame, ID, x/y/z km dan wind m/s; absolute time/Tail/Age/interpolation provenance hilang. Source processor memakai space delimiter/date formatted/hardcoded KBTP; build mismatch belum resolved. Processor dedup mengabaikan timestamp, interpolasi setiap detik limit60, dan boundary-row drop branch ditemukan. Audit script tidak membuktikan seluruh published data dibuat oleh script itu. **Raw adapter direkomendasikan**, bukan langsung import processed sebagai observed track.

Frontend `SituationCanvas.tsx` memakai fictional metric schematic: hanya runways[0], horizontal rectangle, ky hingga 2x kx, viewport berdasarkan drawn geometry, marker last-series point dan heading default0, trail menyambung points tanpa segment-gap semantics. KAGC memiliki runway 10/28 dan13/31, bukan mock09/27. Actual georeferenced layout/hold-line/taxiway graph dengan valid period2022 belum tersedia; operator current specs bukan historical surveyed geometry. UI perlu general polygons, equal-aspect geographic mode, altitude/airborne/unknown-ground semantics, segmented trails, source-age eligibility, neutral unknown-heading marker dan footprint=false.

Strict shared Track mewajibkan positive length/width, heading dan speed. Raw tidak dapat memenuhi itu secara jujur tanpa tambahan source; reconcile/version point-observation contract sebelum real adapter. Jangan dummy aircraft dimensions atau flatten airborne track menjadi surface occupancy. View TrackSeries dan LayoutView masih PROPOSED_CONTRACT. Import awal prediction empty, bukan processed interpolation atau fabricated prediction.

### Artefak dan next action

VM `/home/deploy/flowlens-research/tartan/adsb-research/`: raw dua CSV, tiga processed TXT, inventories, paper.html, bucket-list.txt, manifest, analysis/quality-extra/processed-summary JSON dan near-airport derivatives. Lokal ignored `outputs/tartan-research/adsb/`: JSON evidence/inventories/derivatives disalin lewat SCP; raw CSV/TXT tetap di VM. Helpers ignored `tools/adsb_{sample,collect,analyze,extra}.py`, salinan VM research root. Utility/data dipertahankan; tidak ada background worker/server.

Next proposal: (1) reconcile point-observation contract, (2) raw adapter + quality report dan geographic map, (3) paired audio bounded window pada overlap August dengan timing/identity review, (4) reviewed surface preview, (5) occupancy/conformance hanya dengan coverage/footprint/layout sufficient. Rencana ini belum implementasi dan bukan acceptance tests yang sudah dijalankan. Tidak ada commit/push/deploy, source frontend/backend tidak berubah, gates unchanged. Keputusan implementasi berikutnya menunggu diskusi pengguna.

Performed checks final ADS-B: lima extracted source file sizes/SHA matching manifest di VM PASS; successful-transfer totals dan partial/complete/dedup row-count reconciliation PASS; link dokumen dan credential-pattern check PASS; `git diff --check` PASS. File evidence lokal/VM private mode0600. `docs/README.md` menautkan laporan; laporan diminta dibuka pada panel Codex (tool returned queued). Tidak menjalankan ulang application tests karena hanya dokumentasi/research helpers yang berubah; hasil ini bukan georeferencing/domain/UI validation.


## Checkpoint handoff lengkap — 12 Oktober 2026

Permintaan terbaru pengguna hanya **update lengkap session handoff**. Pembaruan ini mengonsolidasikan hasil yang sudah diperiksa pada 11 Oktober; tidak melakukan request dataset, login/health check VM baru, transkripsi, provider call atau implementasi aplikasi. Status VM/credential/source availability di atas adalah hasil pemeriksaan terdahulu, bukan pemeriksaan ulang 12 Oktober. Performed checks foundation/frontend juga tetap historis dan tidak dijalankan ulang pada checkpoint ini.

### Status akhir yang perlu dibawa ke sesi berikutnya

| Area | Sudah selesai | Belum selesai |
| --- | --- | --- |
| Transkrip | 50 source WAV unik, 123 STT text segments, 120 source chunks; laporan, katalog, manifests dan shortlist | Human listening/gold, critical-slot accuracy, authoritative identity/speaker, domain validation |
| ADS-B | Inventori KAGC/outer bundle, dua CSV + tiga processed samples, integritas source dan statistik quality | Adapter aplikasi, tested CRS transform, historical layout, validated ground classification, multimodal alignment |
| Feasibility frontend | Audit renderer/DTO/strict Track dan laporan dengan rencana bertahap | Perubahan shared contract, real data API, map/taxi UI integration atau UI tests untuk data nyata |
| Delivery | Dokumen riset dan memory tersimpan pada working tree | Commit/push/PR/deploy; gate aplikasi tidak berubah |

**Rekomendasi map replay belum menjadi keputusan implementasi pengguna.** Tidak ada pilihan final mengenai geographic-only versus surface preview, tanggal demo baru, sumber layout 2022, atau perubahan contract yang telah disetujui. Jangan memulai code integration atas dasar kata feasible saja. Jika pengguna meminta implementasi berikutnya, lanjutkan sesuai scope instruksi terbaru dan sequencing/gate repository yang berlaku, tanpa membuat approval tambahan untuk pekerjaan rutin yang memang sudah diizinkan.

### Jalur lanjut dan acceptance yang masih direncanakan

1. Mulai diskusi dari [laporan ADS-B](../docs/data/tartanAdsbFeasibility.md), [PRD §9–10](PRD.md), [rules](rules.md), [phases](implementationPhases.md), [shared contracts](../docs/api/shared-contracts.md), dan source frontend/Track yang ditautkan pada laporan. Pertahankan target stack dan frontend MOCK sampai real integration diotorisasi.
2. Tentukan apakah demo tetap memakai 50 audio September (Said–Heard, Observed NOT_EVALUABLE), atau beralih ke satu window audio Agustus yang overlap ADS-B. Pilihan Agustus baru berupa proposal; tidak ada WAV/STT tambahan untuk tanggal tersebut. Jangan mencampur audio dan track dari hari berbeda.
3. Reconcile point-observation contract sebelum importer: nullable/unknown dimensions, kinematics, ground status dan measurement integrity harus dapat direpresentasikan. Jangan menggunakan fabricated dimensions/heading/speed agar strict Track lolos.
4. Implementasi map yang diusulkan dimulai dari raw immutable + quality derivative + metric CRS dan segmented trail. Pertahankan altitude/datum dan source age; predicted tetap kosong sampai ada model/provenance yang layak. Layout perlu kedua runway KAGC dan valid period source.
5. Acceptance belum dilakukan: parser lintas UTC-date; known-control-point/unit transform; partial position preservation; repeated measurement tidak refresh freshness; conflict variants/identity tidak auto-merge; gaps tidak solid observed trail; unavailable heading tidak menjadi north; future points tidak bocor ke as-known; unknown ground/footprint tidak menghasilkan surface/occupancy verdict.
6. Surface preview hanya setelah sequence/layout/clock/identity review. Occupancy, crossing dan taxi-route conformance memerlukan evidence tambahan; full taxi view tidak dijanjikan oleh dua hari sampel.

### Peta evidence untuk melanjutkan tanpa mengunduh ulang

- Dokumen utama versionable: [handoff ini](sessionHandoff.md), [analisis feasibility ADS-B](../docs/data/tartanAdsbFeasibility.md), [index dokumentasi](../docs/README.md). Transkrip/provider JSON/raw assets tetap ignored/private.
- Analisis transkrip: `outputs/tartan-research/transcriptAnalysis50.md`, `transcriptCatalog50.md`, `transcripts50.json`, `transcripts50.csv`; gunakan manifests untuk exact source path/hash/chunk offsets.
- ADS-B provenance: `outputs/tartan-research/adsb/sample-manifest.json` untuk lima member extracted dan transfer/ETag; `kagc_raw_2021.zip.json`, `kagc_raw_2022.zip.json`, `kagc_processed.zip.json`, `OneDrive-2024-06-21.zip.json` untuk inventory.
- Statistik: `analysis.json` memakai complete numeric rows; `quality-extra.json` membedakan empty/truncated/position-only dan position conflicts; `processed-summary.json` memuat schema actual. `08-27-22-near.json` dan `08-30-22-near.json` adalah diagnostic derivatives, bukan accepted source Track atau ground truth.
- Source CSV/TXT berada pada VM research root; source code upstream dipin pada SHA di atas. Helper ADS-B melakukan request/extraction bila dijalankan ulang: **jangan rerun collector hanya untuk membaca hasil existing**. Untuk diskusi cukup baca laporan/JSON; eksplorasi source baru tetap melalui SSH.
- Bila membuka kembali chat bootstrap, gunakan `read_thread` untuk thread/host yang dicatat sebelum mengandalkan isinya. Gunakan private key path existing; jangan menaruh credential ke handoff/Git atau mengasumsikan Google key masih aktif/tersedia.

Working-tree terakhir yang diamati: `.agent/sessionHandoff.md` dan `docs/README.md` modified, `docs/data/tartanAdsbFeasibility.md` untracked (dokumen baru yang belum di-commit), `.claude/` untracked sudah ada dan tidak disentuh. `outputs/tartan-research/` ignored; clone baru tidak membawa evidence tersebut. Tidak ada runtime baru dimulai atau dihentikan pada checkpoint ini.

## Frontend runtime dan Safari login — 12 Oktober 2026

Atas permintaan pengguna, frontend Vite dev server lokal dimulai dari `frontend/` dengan `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`. Ready pada `http://127.0.0.1:5173/`; exec session `16694` dipertahankan untuk inspeksi pengguna. Ini MOCK development runtime, bukan VM deployment/production. Pernyataan cleanup/no-server sebelumnya bersifat historis; server ini sekarang sengaja dibiarkan berjalan. Hentikan hanya process milik task ini melalui Ctrl-C pada session tersebut bila diminta/tidak lagi diperlukan; jangan kill proses global.

Safari dibuka dan login memakai kartu demo **Evaluator** (`evaluator@flowlens.test`, Dana Whitfield). UI berhasil berpindah ke `/sessions` dan menampilkan daftar tujuh sesi serta akun Evaluator; login diverifikasi lewat accessibility state dan screenshot. Tidak menyimpan credential pada browser atau mengubah source/frontend data. Tidak ada dataset/provider call pada tindakan ini; data tetap SYNTHETIC/MOCK.


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

## Demo workspace (MOCK) — 12 Oktober 2026

Keputusan pengguna: import tanpa source kind; dua file (audio + ADS-B); satu skenario terbaik (`88.wav`, revisi rute taxi KAGC); ADS-B sintetik yang dikalibrasi dari ADS-B nyata Agustus 2022 dan diselaraskan ke audio; open loop dihapus dari seluruh UI; integrasi hybrid dengan 7 sesi MOCK. Konflik dengan rules (PostgreSQL, tanpa source kind, frontend memanggil backend sebelum G-BE, audio nyata vs D-3, ADS-B sintetik) dicatat di [ADR 0003](../docs/adr/0003-demo-workspace-track.md).

### Deliverables

- Backend `backend/flowlens_demo/` (FastAPI + psycopg3), Compose `deploy/compose/local/compose.demo.yml`, Dockerfile `deploy/docker/backend/Dockerfile.demo`, init SQL test DB.
- Script `scripts/demo/` (layout KAGC ilustratif, sintesis ADS-B, build skenario, fetch). Aset di `data/demo-scenarios/kagc-2022-09-10-88/` (ignored).
- Frontend: port `src/api/demo.ts`, adapter `src/api/adapters/demo/`, engine `registerExternal`, import page baru, `AudioEngine` (audio = master clock), `LiveTranscript`, kartu findings pending/New, canvas geometri bandara, Sessions hybrid (badge, processing, offline), Review segment memutar audio nyata. Open loop dihapus dari types/seed/engine/UI.
- Docs: [panduan](../docs/development/demoWorkspace.md), [rencana](../docs/development/demoWorkspacePlan.md) §10, ADR 0003, docs index.

### Checks

Backend 16 pytest lulus (Compose profile `test`); ruff check/format dan mypy bersih. Frontend typecheck, lint, check:types, check:copy, 55 vitest (7 baru untuk bridge/timing/range), build lulus. Playwright 16 journey lulus dengan Chrome lokal (2 journey demo baru: upload → processing → workspace tersimpan → play → transcript + finding; tolak file tak dikenal). Verifikasi browser manual: auto-open setelah processing, toast "Workspace saved", kata muncul selaras audio, kartu "Analysing…" lalu finding "New", listen-to-evidence berhenti di akhir rentang, posisi pause tersimpan di PostgreSQL, Review/Memory/Debrief tanpa error.

### Runtime / cleanup

Dibiarkan berjalan: OrbStack; stack Compose `flowlens-demo` (`db`, `api` di 127.0.0.1:8000); Vite dev server di localhost:5173 (sesi sebelumnya). Hentikan dengan `docker compose -f deploy/compose/local/compose.demo.yml down` (tanpa `-v`). Workspace hasil test sudah dihapus dari DB. Venv Playwright sementara hanya di scratchpad sesi. Tidak ada credential provider dipakai atau disimpan; API key yang sempat dikirim pengguna tidak ditulis ke file mana pun dan sebaiknya di-rotate.

### Batasan

Satu skenario; transcript = cached STT hypothesis; findings authored (bukan detector); ADS-B sintetik (label SYNTHETIC dihapus dari nama file dan UI demo atas permintaan pengguna; CSV kini `kagc_adsb_2022-09-10_88.csv`, findings 7, F-01 dihapus); layout ILLUSTRATIVE; tidak ada delete/rename workspace; polling React Query berhenti saat tab tersembunyi (refresh saat tab aktif lagi). Track ini tidak menutup G-BE/G-FE/G-DELIVERY.


## Demo workspace: rekaman sebelum/sesudah — 12 Oktober 2026

Keputusan pengguna: tanpa concat file; rekaman (audio dan CSV) ditambahkan sebelum/sesudah rekaman main lewat lane Before/Main/After di Import awal (tombol **Add recording** di workspace sempat dibuat lalu dihapus atas koreksi pengguna; endpoint backend tetap ada); hanya 87.wav untuk sesi ini; transcript 87 via Google STT; lag kata 0,4 s dan role tampil 0,4 s setelah final; seluruh label MOCK/SYNTHETIC/simulation dan teks arsitektur dihapus dari UI (pengecualian rules.md dicatat di [ADR 0003](../docs/adr/0003-demo-workspace-track.md)).

- Data: `87.wav` (sha `34f18913…`, dari arsip publik), `kagc_adsb_2022-09-10_87.csv` (sha `31550c2d…`), CSV 88 berubah ke sha `7167fff6…` (lintasan bersambung dari 87). `scenario.json` v2 dengan `parts` dan 3 `variants` (7 / 9 / 10 findings). Cache STT di `outputs/tartan-research/stt-87/` (4 request; dipindai, tidak berisi key).
- Isi 87: clearance "turn right at Bravo 1, runway 13, taxi via Bravo, Alpha, Charlie, hold short of runway 28" + readback. Akibatnya "Bravo Alpha" di 88 = rute; hold short berubah ke "Charlie on Alpha" tanpa instruksi pengubah yang terekam (gap 14 s ditampilkan "Not recorded").
- Backend: upload multi-file dengan `positions`, `POST /workspaces/{id}/files`, `GET /audio/{part}`, migrasi upgrade (`variant`, `part`). Frontend: `RecordingSlots` (file dipilih sebelum daftar skenario termuat ditempatkan setelah termuat), `AudioEngine` multi-rekaman, `LiveTranscript` (divider, gap, Skip). Panel kontrol skenario hanya bila `localStorage['flowlens.devtools']='1'`. `components/domain/labels.tsx` dihapus.
- Checks: backend 20 pytest, ruff/mypy bersih; frontend tsc, eslint, 55 vitest, check:copy, build lulus; Playwright 17/17 lulus (2x berturut-turut). Verifikasi browser manual: kata bertahap, "Recognizing" tanpa role lalu role muncul, readback "Matches", Skip dan gap tampil. Workspace preview/E2E dihapus; tersisa "KAGC - 1" milik pengguna (ter-upgrade).
- Keamanan: API key Google yang dikirim pengguna hanya dipakai lewat env inline untuk 4 request STT, tidak ditulis ke file/log/git; sebaiknya di-rotate. Tidak ada commit/push.

## Highlight bahasa live ATC — 12 Oktober 2026

Keputusan pengguna: highlight di workspace ditulis seolah dibaca controller saat bertugas (fakta saja, tanpa saran tindakan; jam UTC; tabel Said vs Heard per slot); cakupan semua sesi tetapi hanya layar Workspace dan Sessions; hapus "Illustrative layout", "not an operational chart", label fictional/synthetic di kedua layar.

- Data: field `live {title,text}` per finding (`FindingSpec.live`, `FindingView.live`/`slots`), diisi untuk 8 finding seed dan semua finding 3 variant KAGC (`build_scenario.py`, waktu dari `recordedAt` dibulatkan detik). Statement analitis untuk Review/Debrief tidak berubah.
- UI: `AttentionRail` (judul/teks live, tabel Said/Heard, jam UTC via `formatUtcAt`, "N active · HH:MM:SSZ", "Checking latest transmission…", "Nothing flagged … Not a safety confirmation.", tombol "Listen"/"View evidence"); badge layout dihapus; caption layout "KAGC"/"Scale in metres"; kartu Sessions memakai caption layout.
- Backend: `scenario.json` diberi hash `build`; analisis tersimpan dengan build lain dibangun ulang saat dibaca (test baru). KAGC - 1/KAGC - 2 milik pengguna ikut ter-update.
- Checks: backend 21 pytest, ruff bersih; frontend tsc, eslint, 55 vitest, check:copy, build; Playwright 17/17. Verifikasi browser KAGC - 2 dan Runway 27. Tidak ada commit.

## Import multi-rekaman dan processing realistis — 12 Oktober 2026

- Import: lane Before/After memegang banyak rekaman (`Slots = { before: Group[]; main; after: Group[] }`), pairing audio↔CSV per part, file dikenal ditempatkan dulu, file tak dikenal tak pernah menimpa Main (jadi rekaman After). Backend `MAX_FILES` 6 → 20. Alur demo tetap 2 track (87 + 88).
- Processing: 14 tahap realistis (VAD, speech recognition per chunk, speaker roles, phraseology LLM, pairing, track association, conformance, highlights) dengan detail dari data skenario; field `mock` dihapus dari respons; `summary` per tahap (1 baris + ⚠); polling di background.
- OrbStack sempat mati (mesin restart) dan dinyalakan ulang; venv Playwright di scratchpad dibuat ulang.
- Checks: backend 21 pytest, ruff bersih; frontend tsc, eslint, 58 vitest (3 baru slot), check:copy, build; Playwright 17/17. Tidak ada commit.

## Workspace live view — 12 Oktober 2026

- Transcript: tinggi satu transmisi (96 px, tetap scrollable, autoscroll ke terbaru); tombol Skip pindah ke header transcript. Needs attention mengisi sisa tinggi.
- Needs attention: pill "New" dihapus; kartu "Checking latest transmission…" dihapus, diganti indikator persisten "Checking" (spinner) di header rail selama playback (gambaran polling setelah tiap chunk). Audio lost, transmission/crossing unreadable dan quality gap tidak masuk highlight (`live.attention = false`); tetap ada di Review, transcript ("Not recorded") dan timeline. Langkah processing "Highlights" menghitung yang tampil saja.
- Jam di header kini timestamp UTC berjalan (`19:04:02Z`), bukan durasi playback.
- Transcript/findings: "one first seven" dikoreksi menjadi "one four seven" (salah dengar STT untuk 147) di `build_scenario.py`.
- Checks: backend 21 pytest, ruff; frontend tsc, eslint, 58 vitest, check:copy, build; Playwright 17/17. Tidak ada commit.

## Metadata audio sebelum 88.wav — 12 Oktober 2026

Atas permintaan pengguna, sidecar 86/87/88/89 diperiksa melalui SSH HTTP Range pada archive KAGC 2022-09-10 yang sama; tidak mengunduh WAV baru atau memanggil STT. 85.wav/85.txt tidak ditemukan dalam inventory. Times berikut adalah naive source metadata tanggal 2022-09-10, timezone masih unverified:

| File | Start | End | Selisih start−end sebelumnya yang diperiksa |
| --- | --- | --- | ---: |
| 86.wav | 18:56:39.328447 | 19:00:10.306602 | — |
| 87.wav | 19:00:25.311830 | 19:02:59.274421 | 15.005228 s |
| 88.wav | 19:03:13.318769 | 19:04:50.271897 | 14.044348 s |
| 89.wav | 19:06:53.310895 | 19:16:22.313509 | 123.038998 s |

87.wav tersedia sebelum 88.wav, metadata span 153.962591s dan compressed payload 6,825,293 bytes. 86.wav juga tersedia lebih awal, span 210.978155s. Isi ucapan keduanya belum diperiksa pada tindakan ini; metadata tidak membuktikan flight identity, conversation continuity atau adanya instruksi taxi tertentu. Jangan menutup gap 14.044348s antara 87 dan88 sebagai silence/continuous recording tanpa source coverage. 88 decoded duration via ffprobe 96.905986s, metadata end−start 96.953128s (difference 0.047142s); source metadata bukan sample-exact audio endpoint.

Evidence local ignored `outputs/tartan-research/88-preceding-metadata.json`, VM `audio88-metadata/88-preceding-metadata.json` dan empat TXT sidecars; source ETag, metadata SHA/size/inventory tercatat. Successful pass payload 89,148 bytes termasuk ZIP directory. Sebelumnya satu pass berhenti ketika 85.txt tidak ditemukan; tidak ada full ZIP fallback. ADS-B September tetap belum tersedia; pertanyaan audio sebelum 88 tidak mengatasi blocker paired track.

## Layout KAGC: runway dan taxiway — 12 Oktober 2026

- Runway tetap dari koordinat AirNav. 13/31 memang memotong 10/28 (~125 m timur ARP; OSM juga memberi node bersama di titik itu).
- Taxiway dibuat ulang (`scripts/demo/kagc_layout.py`, `LAYOUT_VERSION = "kagc-2"`), semua dalam meter lokal:
  - A sejajar di selatan 10/28; memotong 13/31 hanya di antara dua hold line (HL-A13W/E).
  - B/B1 dipindah ke barat 13/31 (x=170), tidak lagi di bawah runway.
  - C dari ramp ke hold line 28 (HL-C28); G di barat C, menyeberang 28, berakhir di tepi 13/31 di belakang HL-G13.
  - HL-AC (hold short C on A) di timur C.
- Jarak C→G di A dipadatkan dibanding diagram nyata (≈410 m), supaya penyeberangan 28 terjadi sebelum rekaman 88 berakhir.
- `synth_adsb.py` mengikuti geometri baru. Event: enter 85.7 s, exit 90.7 s, stop 92.7 s; titik berhenti tetap ~8 m utara tepi 10/28 dan ~25 m sebelum HL-G13.
- Label skenario "ILLUSTRATIVE layout" diganti menjadi "SCHEMATIC taxiways".
- Verifikasi: backend 21 passed, ruff bersih, Playwright 17/17.
- Verifikasi: backend 21 passed, ruff bersih, Playwright 17/17.

## Attention: Keep in mind dan item non-readback — 12 Oktober 2026

- **Keep in mind** (bagian atas rail "Needs attention"): item yang perlu diingat, dari `spec.reminders` (`build_scenario.py`), dihitung per as-of oleh `remindersAt` (engine) dan dikirim lewat `WorkspaceSnapshot.reminders`.
  - R1 `LIMIT`: batas izin N147G; step baru menggantikan step lama ("Was: …"). Dengan 87: hold short RWY 28 at C → hold short RWY 13 on G. Tanpa 87: "Limit not heard" → hold short RWY 13 on G.
  - R2 `TRAFFIC`: traffic yang diberitahukan (Cessna opposite direction on A); Done saat Cessna keluar dari A (dari ADS-B).
  - R3 `INTENT`: pernyataan pilot "hold short C on A"; Done saat change of plans.
  - Item Done tampil satu baris redup selama 30 s (live/as-known), lalu hilang.
- **A3** "Opposite direction on A · Cessna" (ATTENTION, baru): jarak 451 m saat traffic call, resolved saat Cessna keluar dari A (closest 40 m). Fakta dari `traffic_events()` di `synth_adsb.py`.
- **A1** "On RWY 10/28 · crossing not confirmed" (ATTENTION, menggantikan INFO "Crossing RWY 10/28 on G"): muncul saat masuk strip 10/28, resolved saat keluar.
- `live.until`/`live.resolved`: kartu berubah menjadi "Resolved · …" dan memudar 30 s setelahnya. `live.facts`: tabel fakta (Position / Instruction / Readback / ATC confirm, atau jarak traffic) untuk item non-readback.
- Kategori A3 memakai `MOVEMENT_DIVERGENCE` karena enum kontrak belum punya kategori traffic.
- Jumlah finding: 88 saja 8, 87+88 dengan ADS-B 87 11 (tests diperbarui). Verifikasi: backend 21 passed, ruff bersih, tsc/eslint/vitest 58/check:copy/build OK, Playwright 17/17.

## Ringkasan akhir sesi — 12 Oktober 2026

Konsolidasi seluruh pekerjaan sesi ini. Detail per fitur ada di bagian bertanggal di atas dan di [demoWorkspace.md](../docs/development/demoWorkspace.md).

### Produk (demo workspace)

| Area | Keputusan / hasil |
| --- | --- |
| Import | Rekaman tambahan hanya lewat Import awal (lane Before / Main / After, multi-rekaman per lane). Alur demo tetap 2 track: 87 (before) + 88 (main), masing-masing audio + CSV ADS-B. Tombol Add recording di workspace dihapus |
| Processing | 14 tahap realistis (upload … speech recognition … phraseology (LLM) … highlights … save), ±22 s, tanpa menyebut simulasi; detail per tahap dari data varian; ringkasan + ⚠ saat selesai |
| Bahasa highlight | Gaya live ATC: fakta saja, jam UTC, tabel Said vs Heard. Audio hilang / transmisi tidak terbaca tidak masuk attention (tetap di transcript/timeline) |
| Rail "Needs attention" | Pill "New" dihapus; indikator **Checking** persisten di header rail selama playback; kartu bisa **Resolved** (`live.until`) lalu memudar 30 s; tabel fakta (`live.facts`) untuk item non-readback |
| Attention baru | A1 "On RWY 10/28 · crossing not confirmed" (menggantikan INFO crossing), A3 "Opposite direction on A · Cessna" (fakta dari `traffic_events()`) |
| Keep in mind | R1 batas izin (step menggantikan step, "Was: …"), R2 traffic advised, R3 intent pilot. Data `spec.reminders` → `remindersAt` (engine) → `WorkspaceSnapshot.reminders`; tampil di atas kartu attention |
| Transcript & header | Transcript satu bubble tinggi, scrollable; jam header = UTC berjalan (`formatUtcAt`); "one first seven" → "one four seven" |
| Peta KAGC | Runway AirNav tetap (13/31 memang memotong 10/28). Taxiway dibangun ulang mengikuti susunan OSM (A sejajar selatan 10/28, B/B1 di barat 13/31, C ke hold 28, G di barat C ke tepi 13/31); jarak C→G dipadatkan agar penyeberangan 28 terjadi dalam rekaman. Hold line + labelnya **tidak digambar** di peta KAGC (data tetap ada). `LAYOUT_VERSION = "kagc-2"` |
| UI lain | Banner "N item … hidden in As-known" di bawah peta dihapus; tipografi "illustrative/not operational" dihapus dari Workspace/Sessions; akun demo Evaluator berganti nama menjadi **Khalfani Shaquille** (`acct:khalfani`, email tetap `evaluator@flowlens.test`) |
| Data | CSV ADS-B diregenerasi untuk layout baru: 87 sha `02c32712…`, 88 sha `5ad92fe9…`. Event: masuk 10/28 85,7 s, keluar 90,7 s, berhenti 92,7 s (audio 88). Jumlah finding: 88 saja 8, 87+88+ADS-B 87 11. Label skenario "SCHEMATIC taxiways" |

### Momen krusial demo (sesi 87 + 88, durasi 04:25)

Skip ke 01:45 → clearance + readback (Keep in mind 01:58, Said vs Heard 02:10) → lompat ke 02:46 → traffic call + A3 (02:49) → hold short changed (03:03) → route revised (03:40) dan Keep in mind berganti ke RWY 13 on G (03:46) → readback adds cross 28 (03:56) → **A1 masuk RWY 10/28 (04:15, resolved 04:19)** → holding short 13 (04:23). Sesi 88 saja: kurangi 02:48.

### Materi pitch (di `outputs/architecture/`, ignored Git)

- `flowlens-ambient-intelligence.html/.png`: pipeline Sources → Ingest → Speech → Understanding → Correlation → Highlights (nama komponen teknis, tanpa nama provider). Judul slide yang disarankan: "System Architecture".
- `flowlens-dataset.html/.png` + `assets/kagc-station.png`: slide TartanAviation (Speech 3,374 h, Trajectory 63M reports / 661 hari, Vision tidak dipakai; atribusi Patrikar et al., CC BY 4.0). Catatan: ADS-B untuk rekaman demo adalah sintetik (raw KAGC hanya sampai Agustus 2022).
- `outputs/brand/`: favicon SVG/PNG dan mark transparan.
- Teks bisnis yang disepakati: 3 keunggulan vs teknologi existing (transkripsi khusus ATC; AI membaca instruksi; highlight ATC voice + ADS-B vs ASDE-X/A-SMGCS yang hanya posisi). GTM: Pilot Project (live trial di Juanda bersama AirNav Indonesia, advisory) → batch Tender → Multi-Airport Deployment per batch. TAM USD 4,6–8,9 M (Credence 2024 / GMI 2023), SAM 73 tower AirNav × harga lisensi, SOM 5–10 bandara; **harga USD 100k/bandara/tahun masih asumsi**, jumlah tower dari profil CANSO 2020 perlu dicek ulang.

### Checks terakhir

Backend 21 pytest (Compose profile `test`), ruff check/format bersih. Frontend tsc, eslint, 58 vitest, check:copy, build lulus. Playwright 17/17 (sebelum penghapusan hold line dan banner; perubahan itu diverifikasi dengan tsc/eslint/vitest dan browser).

### Runtime saat sesi berakhir

OrbStack + stack Compose `flowlens-demo` (`db`, `api` 127.0.0.1:8000) dan Vite dev server (preview `frontend-mock`, 5173) masih berjalan. Semua sesi lama dihapus atas permintaan pengguna; yang ada sekarang dibuat pengguna: "KAGC - Taxi", "KAGC - 12 Oct". Perubahan skenario butuh `python3 scripts/demo/synth_adsb.py && python3 scripts/demo/build_scenario.py` lalu `docker restart flowlens-demo-api-1` (analisis tersimpan otomatis dibangun ulang karena hash `build` berubah).

### Keamanan

- API key Google yang sempat dikirim pengguna tidak ditulis ke file mana pun; sarankan rotasi.
- Host research VM dan path private key **tidak** dicatat di repo. `scripts/demo/fetch_scenario.sh` sekarang mewajibkan `VM=<user@host>` dan `SSH_KEY=<path>` dari environment.
- `.claude/launch.json` tetap untracked.



## Rencana lima case demo tambahan — 12 Oktober 2026

Permintaan terbaru: baca ulang konteks dan lakukan analisis mendalam/full plan menambah hingga lima tracks, standalone atau maksimal satu before dan satu after. Steering eksplisit: **jangan sentuh 87/88**. Hasil: [demoScenarioExpansionPlan.md](../docs/development/demoScenarioExpansionPlan.md), status ANALYSIS_COMPLETE / IMPLEMENTATION_PLANNED. Source aplikasi, assets, CSV, scenario/build/variant/timing/highlight 87/88, layout, stored workspace, runtime dan gate tidak diubah.

Interpretasi kerja “tracks” adalah rekaman/case demo; klarifikasi audio-case versus map-objects sudah diajukan, belum dijawab eksplisit. Plan membatasi physical source ke lima WAV baru: **50, 51, 47, 156, 123**. Semuanya standalone; 50 juga eligible sebagai satu before pada 51. Tidak membutuhkan after. Hasil target: lima cases baru, enam skenario demo total bersama existing 88; tujuh seed sessions lama tetap terpisah. 24 (touch-and-go) dan 15 (short-approach) adalah reserve, bukan WAV keenam/ketujuh.

| Case | Demo value dan highlight candidate |
| --- | --- |
| 50 | Multi-object Tower; downwind 13 + Duchess backtaxi advised; departure Alpha terpisah dari arrival Quebec |
| 51 | Landing 13/readback; departure-roll voice report; turnout Alpha tidak merge landing Quebec; optional before 50 |
| 47 | Ready/holding-short report → takeoff 13 dengan backtaxi **if needed**; tidak membuat readback/mismatch yang tidak terekam |
| 156 | Maintain 3,000/squawk 4131; assigned altitude terpisah dari future expectation FL180 yang belum reviewed; source date 11 September |
| 123 | Contact 119.35/readback frequency; heading/callsign ambiguous; separate later exchange tidak otomatis menutup contact |

Total unique source duration **441.628934 s**. Cached transcript words dan metadata diperiksa lewat SSH, tanpa raw download baru/provider call. Ignored evidence: `outputs/tartan-research/mock-case-candidates.json` (10 kandidat dibandingkan, selected 5). Human listening/domain review belum dilakukan pada sesi planning; candidate card copy bukan accepted detector output. Sebelum implementasi card, audit critical spans dan preserve per-slot uncertainty. Tidak mewajibkan hazard/mismatch tiap kasus; positive facts INFO dan standing memory tetap bernilai. Noise/unreadable tetap di Review/transcript, `live.attention=false`; open-loop UI tidak ditambah.

Blocker teknis yang ditemukan di source: registry `by_file_name()` first global match dan RecordingSlots `.find(name)`/first main. 50 dipakai sebagai main case 50 dan before case 51; perlu optional `scenario_id`, additive per-case catalogue/files/limits, matching entire file-set dan scoped validation. Case baru cap before 1/after 1/max 3 recordings; defaults/import legacy 87/88 tetap. Ada tujuh variants baru (C2 tiga, empat case lain masing-masing satu); variants existing tidak diubah. Gunakan new-only builders/fetch scripts, jangan invoke/refactor existing build_scenario.py, synth_adsb.py atau fetch_scenario.sh yang menarget 87/88. Asset source melalui SSH; provenance cloud/source kinds tetap tercatat walaupun label UI demo dihapus sesuai keputusan terdahulu.

Timing context 50→51: metadata gap **54.982178 s**; source-start offset **120.002886 s**; decoded 50 duration **64.931995 s** → playback gap **55.070891 s**. Pertahankan residual/uncertainty; gap tidak dirapatkan/diisi hidden instructions. Slot DSL belum mempunyai FREQUENCY/ALTITUDE/SQUAWK; gunakan `live.facts` atau optional demo-specific typed extension, bukan memakai RUNWAY slot atau mengubah generated contract.

Urutan: E0 protected baseline → E1 case/evidence packets → E2 new-only assets/build → E3 scoped registry/API → E4 import client/caps → E5 authored highlight/reminder data → E6 disposable tests/browser/legacy regression. Detailed exit criteria, file map dan validation ada di laporan. Implementation dan application tests belum dijalankan untuk expansion; angka 21 pytest/58 Vitest/17 journeys tetap historical demo evidence. Tidak restart/delete/reprocess workspace pengguna; tidak commit/push/deploy. Plan memakai boundary ADR 0003, tidak mengubah production PRD atau G-BE/G-FE.

Performed checks planning: lima selected source SHA/duration cocok dengan cache 50; word offsets bounded; total duration terverifikasi; local document links/credential patterns/`git diff --check` PASS. Changed files hanya dokumen rencana, docs index dan handoff; `.claude/` tetap untracked dan tidak disentuh. Protected asset fingerprints dan application regression suites adalah acceptance rencana, belum diklaim PASS.


## Implementasi lima case tambahan — 12 Oktober 2026

Instruksi `proceed` melanjutkan [rencana expansion](../docs/development/demoScenarioExpansionPlan.md), dengan batas eksplisit **87/88 tidak disentuh**. Lima new cases (50/51/47/156/123) dan tujuh variants tersedia lokal; 51 menerima satu before 50 dengan/ tanpa CSV 50. Case lain standalone; tidak membutuhkan after. Raw sources diambil dari VM lewat SSH, lima SHA cocok dengan cache; tidak ada provider call atau transkripsi ulang.

Deliverables: three new-only helpers di `scripts/demo/` (fetch/build/synth additional scenarios), ignored five packages `data/demo-scenarios/kagc-2022-09-10-{50,51,47,123}` dan `kagc-2022-09-11-156`. Registry/catalogue/API memakai optional scenario_id dan full-file-set inference; source filename50 main versus before tidak memakai first global match. Frontend Import mempunyai Case selector, scoped filenames, no silent overwrite, caps satu before/after untuk new cases. Legacy 87/88 defaults dan variants tetap. Shared generated contracts tidak berubah. Usage: [demoWorkspace.md](../docs/development/demoWorkspace.md); demo boundary tetap ADR0003.

Data: cached raw STT tidak diubah; speaker/identity/intent annotations authored candidates. Readback candidate bukan whole-transmission MATCHED; slots AMBIGUOUS dan frequency/altitude/squawk memakai fact rows. Turnout Alpha terpisah dari landing; ready report bukan readback; maintain3,000 tidak diganti FL180; frequency readback tidak berarti contact completed. Instruction memory ACTIVE tetap mempunyai interpretation AMBIGUOUS. Keep in mind dan INFO highlights memakai evidence; tidak membuat hazard/mismatch demi jumlah cards. Prior-clip entities berlabel[50] dan terpisah dari main, track stale sesudah coverage berakhir; gap55.071s dipertahankan.

Seluruh case mempunyai authored centre-point map fixtures (SYNTHETIC), footprint=false, prediction kosong, movement findings NOT_EVALUABLE. CSV altitude/heading/speed merupakan assumed fixture values dengan timestamp granularity1s; tidak diklaim real paired September ADS-B, flight physics atau calibrated surface occupancy. Labels ringkas berakhiran? menandai identity candidate; tidak mengubah layout Kagc-2 atau data/flight events87/88. Source timezone masih unverified; UTC dipakai sebagai interpretation demo pada manifest. Human/domain review belum dilakukan.

Checks akhir: **28 backend pytest**, **61 Vitest**, typecheck/lint/check:types/check:copy/build PASS; Ruff format/check new scripts + backend, mypy backend changed files PASS. Browser: enam new import journeys (lima standalone +51before50), audio206, cards/reminders, registered workspace, console-error/overflow checks; final replay End→Home tidak membocorkan future highlights, source actors/stale/memory assertions; screenshot inspection termasuk visual follow-up C51+before50 pada1280×720. Existing legacy backend/unit suites termasuk dalam pass. Seluruh **13 protected fingerprints** raw/derived/CSV/scenario dan old generator/layout cocok baseline. Bukti private di `outputs/demo-expansion/`: baseline hashes, backend/frontend logs, browser-import-matrix/replay-matrix/final-browser-results, screenshots dan cleanup records.

Normal Compose image build terhenti DNS `auth.docker.io`. Local API dijalankan dengan incremental image dari immutable cached existing image; tidak mengubah Dockerfile.demo atau dependencies. Container app.py/scenarios.py SHA cocok source workspace. Clean Docker Hub build belum verified (catat limitation, bukan PASS). API localhost8000 dan Vite localhost5173 tetap berjalan; frontend dimulai ulang (exec session33664) karena5173 sebelumnya tidak aktif. Backend di-restart untuk reload new registry/assets; DB volume tidak dihapus.

QA hanya membuat tujuh temporary workspaces (enam matrix +satu visual), dibersihkan lewat validated UUID+`E2E expansion` prefix. User workspaces tidak dihapus/di-reprocess secara sengaja; assets/build87/88 unchanged. Browser processes test ditutup; ignored browser venv/evidence/fixtures dipertahankan. Tidak commit/push/deploy ke VM, tidak mengubah G-BE/G-FE/G-DELIVERY atau production stack. `.claude/` tetap untracked dan tidak disentuh.


## Dokumentasi attention dan delivery branch — 13 Oktober 2026

Per-case attention yang terpasang telah dicocokkan dengan `CARDS`/`REMINDERS` builder dan didokumentasikan pada [demoWorkspace.md](../docs/development/demoWorkspace.md#attention-lima-case-tambahan--13-oktober-2026): tujuh main-case INFO cards, dengan downwind/takeoff (50), landing/turnout (51), conditional backtaxi (47), altitude/squawk (156), dan frequency readback (123). Before 50 menambah konteksnya sendiri pada 51, tanpa merge identity atau menghapus gap. Timing pending +400 ms / available +800 ms berasal dari akhir supporting transmission; bukan provider latency terukur. Tidak ada edit attention 87/88 atau perubahan domain status.

Instruksi delivery mencakup update docs, commit implementation expansion beserta tests/scripts/docs, dan push ke branch aktif `feat/fe-init`. Private WAV/CSV/scenario packages, research cache dan browser evidence tetap ignored; `.claude/launch.json` bukan bagian task dan tidak di-stage. Fresh clone memerlukan cache/source privat sebagaimana panduan setup. Tidak ada merge, PR, deployment, atau perubahan gate. Angka test aplikasi merujuk verifikasi 12 Oktober; edit dokumentasi tidak menjalankan ulang seluruh suite. Delivery checks mencakup diff/whitespace, scoped credential patterns, link/fence dokumentasi, dan protected fingerprints. Hosted CI executable belum tersedia di `.github/workflows`; push bukan bukti CI/release lulus.

## Landing page dan deployment `flowlens.site` — 13 Oktober 2026

Permintaan: landing page mobile-first (pengenalan produk, gaya app + referensi Margin), tanpa tombol ke login; login di `/login-flow` dengan akun demo yang sama; deploy ke `flowlens.site` dengan Caddy + Compose dari clone branch ini di VM.

- Frontend: `src/features/landing/` (LandingPage, Reveal), rute `/` publik, `LOGIN_PATH` di `src/lib/links.ts`, `/login` redirect; screenshot workspace seed MOCK sebagai aset; meta SEO/OG. Inter/lucide dipertahankan agar konsisten dengan app; light-only sesuai D-5. Skill brandkit tidak dapat menghasilkan gambar (tidak ada tool image generation); prinsip "extend existing brand" diterapkan langsung.
- Deploy: `deploy/compose/vm/compose.yml`, `deploy/caddy/Caddyfile`, `deploy/docker/frontend/Dockerfile.edge`, `.dockerignore`. Docker 29.9 + Compose v5.6 dipasang di VM; clone `~/flowlens`; skenario disalin via rsync; `.env` acak dibuat di VM.
- Checks dan batasan: lihat [runbook](../docs/operations/vmDemoDeployment.md#verifikasi-13-oktober-2026). Playwright Python suite (e2e) tidak dijalankan ulang; conftest diubah ke `/login-flow`.
- Runtime ditinggalkan: stack `flowlens` di VM (sengaja, publik); Vite dev server lokal 5173 (preview `frontend-mock`). Gate G-BE/G-FE/G-DELIVERY tidak berubah.
