# Rencana lima rekaman demo tambahan dan highlight kasus

Tanggal: 12 Oktober 2026 (Asia/Jakarta). Baseline source: `e325f7e`, branch demo yang sudah tersedia. Status **IMPLEMENTED_LOCAL_DEMO / NOT_DOMAIN_VALIDATED**. Bagian 1–10 menyimpan rencana dan batas; completion record di bagian 11 menjelaskan implementasi serta hasil checks. Skenario 87/88 tidak berubah.

## 1. Scope dan batas yang dikunci

- **87 dan 88 tidak disentuh.** Jangan mengubah WAV/derivatives, CSV, scenario.json, authored transcript/findings/reminders, geometry, variant keys, IDs, timings atau workspace tersimpan kedua rekaman. Jangan menjalankan generator existing yang meregenerasi mereka.
- Interpretasi kerja “tracks”: lima rekaman audio/case demo tambahan, bukan lima objek map. Klarifikasi istilah telah diajukan; bila pengguna mengartikan lain, revisi scope sebelum code dependent. Pilihan di bawah membatasi bahkan physical source menjadi **lima WAV unik baru**.
- Lima main candidates: **50, 51, 47, 156, 123**. Semuanya standalone. Untuk 51, 50 boleh menjadi **satu before** opsional. Tidak ada after yang dibutuhkan untuk selection ini. Batas setiap sesi baru: 0–1 before + 1 main + 0–1 after; maksimal tiga rekaman, enam audio/CSV files jika seluruhnya berpasangan.
- “Baru” berarti baru masuk katalog demo; source WAV dan cache STT sudah ada pada riset. Tidak membutuhkan fresh STT/Gemini calls atau download corpus besar. Menambah lima case akan menghasilkan enam skenario demo bersama skenario 88 existing; tujuh seed in-browser lama merupakan katalog terpisah dan tetap dipertahankan.
- Pengguna meminta analisis dan full plan to implement. Pemilihan ini adalah rekomendasi implementasi, belum klaim lima kasus sudah tersedia di UI. Jumlah “hingga lima” merupakan ceiling, bukan alasan memaksakan kandidat yang tidak lulus audit.

Acuan: [PRD](../../.agent/PRD.md) §9–17/23/34, [rules](../../.agent/rules.md), [handoff](../../.agent/sessionHandoff.md), [ADR demo 0003](../adr/0003-demo-workspace-track.md), [panduan demo](demoWorkspace.md). Keputusan demo yang sudah dicatat pada ADR (PostgreSQL terpisah, cached authored pipeline, tanpa open-loop UI, kata muncul +0.4s/role sesudah final, gaya highlight fakta live, UI tanpa label mock/synthetic) tidak dibuka ulang oleh expansion. Data provenance dan batas research tetap dicatat dalam manifest/dokumen. Ini offline demo, bukan feed ATC aktif.

## 2. Hasil inspeksi source saat ini

| Area | Ada di source | Dampak expansion |
| --- | --- | --- |
| `Registry` | Memuat semua `*/scenario.json` v2 | Registry directory sudah mendukung lebih dari satu skenario |
| File recognition | `by_file_name()` mengembalikan match pertama; filename tidak scoped | 50 akan menjadi main pada satu case dan before pada 51; lookup global tidak cukup |
| `/api/demo/scenarios` | `expected_files` dan daftar file flatten tanpa scenario ID | Frontend memerlukan katalog per case; preserve payload legacy untuk 87/88 |
| `RecordingSlots` | Auto-position berdasarkan `.find(name)`; first main digunakan pada error copy; banyak before/after | Banyak main dapat saling menggantikan; perlu matching per case dan caps per case baru |
| `check_set()` | Main audio + CSV wajib; companion CSV membutuhkan companion audio | New standalone berarti satu WAV + satu authored CSV, bukan audio-only import baru |
| `accept()` | Menolak files lintas scenario, duplicates dan checksum mismatch | Pertahankan guards; identifikasi scenario sebelum menentukan part/position |
| DB/workspace | Sudah menyimpan scenario_id, variant, cursor | Tidak perlu DB engine baru atau generic schema redesign |
| Analysis build | Invalidasi berdasarkan hash scenario.json | Jangan menyentuh build/hash skenario 88; perubahan case baru tidak boleh rebuild workspace 87/88 |
| `AttentionRail` | `live.attention`, slot table/facts, `until/resolved`, reminders, linger 30s | Isi case authored dapat memakai UI yang ada; tidak perlu redesign rail |
| Playback | Audio element master clock, multiple parts + explicit gaps | Context 50→51 harus mempertahankan actual offset dan recording boundaries |

Source acuan: [registry](../../backend/flowlens_demo/scenarios.py), [upload/API](../../backend/flowlens_demo/app.py), [import lanes](../../frontend/src/features/imports/RecordingSlots.tsx), [demo port](../../frontend/src/api/demo.ts), [attention](../../frontend/src/features/workspace/AttentionRail.tsx). Generator existing [build_scenario.py](../../scripts/demo/build_scenario.py) hardcoded 87/88; jangan mengedit atau memanggilnya untuk expansion ini. [fetch_scenario.sh](../../scripts/demo/fetch_scenario.sh) juga fokus 87/88 dan memuat path download 87 lokal; **jangan pakai script tersebut untuk mengambil case baru**, sesuai instruksi semua eksplorasi source melalui SSH.

## 3. Evidence dan selection

Cached runs/metadata diperiksa kembali lewat SSH VM riset. Tidak ada raw audio baru diunduh, tidak ada provider call, tidak mendengarkan/menyatakan audit manusia selesai. Ignored evidence: `outputs/tartan-research/mock-case-candidates.json` (run path, immutable source SHA, decoded duration, metadata dan word offsets); salinan penelitian juga di VM. Source archive semua kandidat: `kagc/2022/9/09-10-22_audio.zip`.

| Case / main | Durasi decoded | Source metadata start | Momen utama relatif WAV | Fungsi berbeda |
| --- | ---: | --- | --- | --- |
| C1 — 50 | 64.932 s | 10 Sep 15:09:10.399481 | 8.8–24.5; 25.5–31.7 | Multi-object Tower: downwind, backtaxi traffic, takeoff aircraft lain |
| C2 — 51 | 88.930 s | 10 Sep 15:11:10.402367 | 54.4–65.3; 74.8–85.2 | Landing instruction/readback dan pemisahan turnout objek lain |
| C3 — 47 | 100.955 s | 10 Sep 14:42:52.453970 | 12.6–28.7 | Ready/holding-short report → takeoff + conditional backtaxi |
| C4 — 156 | 77.898 s | **11 Sep** 01:19:30.240168 | 27.9–35.8; 59.4–71.0 | Clearance memory: assigned altitude versus future expectation, squawk |
| C5 — 123 | 108.914 s | 10 Sep 22:32:44.177204 | 40.1–49.6; 100.0–106.2 | Handoff frequency readback dan unrelated later transmission |

Total lima WAV: **441.628934 s (7m21.629s)**. Itu jumlah unique source duration, bukan jumlah durasi seluruh possible sessions karena 50 bisa direuse sebagai before. Source timestamp di tabel naive; UTC adalah interpretasi demo yang harus dicatat, bukan timezone source yang sudah terverifikasi. Folder 09-10 tidak berarti setiap rekaman tanggal 10 September.

Selection mempertahankan variasi fungsi: multi-object context, landing, conditional departure, clearance slots, frequency handoff. `24.wav` (touch-and-go) adalah reserve pertama bila C1/50 tidak lolos audit. `15.wav` (short approach) reserve berikutnya; approval phrase STT lebih rusak. Tidak menambahkan mereka sebagai WAV keenam/ketujuh pada scope ini. Kandidat tidak dipilih semata-mata agar ada banyak mismatch atau warning.

### Standalone dan before/after

Standalone berarti inti contoh dapat dipahami dari rekaman main dengan unknown yang terlihat; bukan klaim semua histori instruksi lengkap. Setiap case memulai dengan memory yang berasal dari source clip, bukan mengimpor state tersembunyi dari episode lain. Hanya 51 mendapat optional before 50, karena tanggal/frekuensi dan sequential context relevan; kemiripan suffix Quebec masih **candidate association**, bukan identity terbukti.

Metadata 50 end `15:10:15.420189`, 51 start `15:11:10.402367`: end-to-start gap **54.982178 s**. Namun source-start offset 51 relatif 50 adalah **120.002886 s**. Dengan decoded 50 duration 64.931995 s, gap playback source-start-aligned adalah **55.070891 s**. Jangan menyamakan dua angka itu atau concatenate audio tanpa gap. Pembulatan wire ms harus deterministik; simpan raw metadata dan residual timing uncertainty. Skema offset harus memakai source starts dan actual derivative sample counts.

Default packages baru:

- C1: main 50 audio + CSV saja.
- C2: main 51 audio + CSV; opsional before 50 audio, atau before 50 audio + CSV. Tidak ada after.
- C3/C4/C5: main audio + CSV saja.

Total **tujuh prepared variants baru**: empat single variants dan tiga variants C2. Variants existing 87/88 tidak diubah. Tidak perlu mengaktifkan semua combinations teoritis atau menambah after tanpa kebutuhan evidence.

## 4. Analisis kasus dan highlight yang direncanakan

Semua wording di bawah adalah **candidate UI copy**, bukan kutipan official transcript atau hasil detector. Copy English mengikuti UI; dokumen Indonesia. Unknown slots tetap unknown sampai critical-span audio diperiksa. Timeline trigger baru dihitung dari final supporting words + latency demo; setiap card menyimpan segment/word ranges serta entity/part scope. Tidak tampil lebih awal karena mengetahui jadwal authored berikutnya.

### C1 — 50: Multi-object Tower sequence

**Evidence:** 8.8–19.3 s berisi kandidat enter midfield left downwind runway 13, disertai informasi Duchess perlu backtaxi. 20.4–24.5 kandidat respons downwind. 25.5–31.7 adalah takeoff clearance kepada identifier berakhir Alpha, berbeda dari kandidat Quebec sebelumnya. 0.1–2.1 dan respons terakhir terpotong.

**Model case:** minimal dua distinct entities: `… Quebec` sebagai downwind candidate dan `… Alpha` sebagai departure candidate. Duchess pertama kali menjadi traffic reference, bukan otomatis entity dengan proven position/callsign. Jangan memberikan full registration atau aircraft type dari suffix saja.

| Area | Candidate wording | Syarat / lifecycle |
| --- | --- | --- |
| Keep in mind · INTENT | `… Quebec · Midfield left downwind RWY 13` | Setelah instruction lengkap tersedia; `Was` hanya bila memang ada revision pada source |
| Keep in mind · TRAFFIC | `RWY 13 · Duchess backtaxi advised` | ATC traffic statement; tidak menjadikannya actual runway occupancy |
| Needs attention · INFO | `RWY 13 · Downwind read back` | Tabel Said/Heard action + runway; callsign candidate harus tetap visible/ambiguous |
| Needs attention · INFO | `… Alpha · Takeoff clearance RWY 13` | Association terpisah; tidak menutup memory Quebec |

**Map authored:** distinct arrival-pattern dan departure tracks pada layout KAGC existing read-only, dengan window dan IDs berbeda. Track altitude/airborne state perlu dikonsepkan sebagai pattern context; jangan menyajikan aircraft di atas runway sebagai footprint occupancy. Bila existing view tidak dapat membedakan airborne context, tampilkan centre-point context/memory dan disable ground conformance untuk entity tersebut. Tidak memadatkan taxiways atau mengubah layout untuk mengejar timing.

**Review-only:** clipped fragments, callsign alternatives, wind dan phrase backtaxi rusak. Tidak membuat “wrong runway” atau physical conflict karena slot kurang jelas. Bila pasangan downwind belum dapat dibuktikan, ganti card dengan instruction fact; jangan menampilkan full MATCHED.

### C2 — 51: Landing clearance/readback

**Evidence:** 54.4–60.3 s ATC melaporkan aircraft lain pada departure roll. Clearance runway 13 berlanjut 61.0–62.2 s; kandidat readback 62.9–65.3 s mengulang runway/action. 74.8–85.2 s membahas turnout kepada `… Alpha`, bukan otomatis pesawat Quebec yang landing.

| Area | Candidate wording | Syarat / lifecycle |
| --- | --- | --- |
| Keep in mind · LIMIT | `… Quebec · Cleared to land RWY 13` | Clearance dari ATC; physical landing belum dibuktikan |
| Keep in mind · TRAFFIC | `RWY 13 · Departure roll reported` | Report sumber voice; tidak membuat posisi “observed” |
| Needs attention · INFO | `RWY 13 · Landing clearance read back` | Compare runway/action; whole clearance MATCHED hanya jika identity/correspondence cukup |
| Separate memory | `… Alpha · South turnout approved` | New entity association, setelah audit literal turnout/heading; jangan merge landing |

Standalone cukup untuk core landing exchange. Dengan before 50, UI menunjukkan downwind context **candidate** dengan gap; instruction atau response dalam gap tidak direka. Header, event offsets, table Said/Heard dan evidence audio harus shift konsisten. Mode without before tidak menganggap “previous instruction” tersedia.

**Map authored:** arrival aircraft dan departure aircraft berbeda. Animation dapat menggambarkan authored approach/departure, tetapi tidak menghasilkan card “runway clear”, safe separation atau actual landing completion. Resolve hanya memakai explicit applicable authored fixture event atau reviewed voice evidence; provenance voice vs generated movement tetap terpisah.

### C3 — 47: Readiness → conditional takeoff

**Evidence:** 12.6–20.7 s kandidat `… Uniform` melaporkan holding short runway 13 at Golf dan ready. 23.3–28.7 s kandidat ATC takeoff clearance runway 13 serta backtaxi approved **if needed**. Tidak ada full takeoff readback dalam cache.

| Area | Candidate wording | Syarat / lifecycle |
| --- | --- | --- |
| Keep in mind · INTENT | `… Uniform · Ready at Golf, RWY 13` | Pilot report, tidak menjadikannya observed position |
| Keep in mind · LIMIT | `RWY 13 · Takeoff cleared; backtaxi if needed` | Kondisi tetap attached; bukan unconditional instruction to backtaxi |
| Needs attention · INFO | `RWY 13 · Conditional backtaxi approved` | Fact table: Takeoff / Backtaxi condition / Readback not present in this clip |

**Case objective:** dapat menampilkan instruction baru walaupun readback belum ada. Tidak menciptakan discrepancy karena readback absent; tidak menghidupkan kembali open-loop UI atau menganggap pilot gagal readback. “Holding short” voice sebelum clearance juga tidak berarti departure sesudah clearance merupakan violation.

**Map authored:** start at Golf/13 sebagai deliberate fixture assumption (bukan position dari voice). Timeline memberi plausible controlled progression; jangan inject runway incursion untuk menambah drama. Conditional backtaxi tidak wajib dijalankan pada semua fixture variant. Callsign `430 Uniform` vs `43… Uniform` perlu audit sebelum identity penuh diterima.

### C4 — 156: Clearance altitude, expectation dan squawk

**Evidence:** standby kepada kandidat Julia Charlie 27.9–30.6 s; takeoff kepada Kilo Alpha 32.4–35.8 s adalah entity lain. Clearance panjang 59.4–71.0 s mencakup maintain 3,000, departure as filed, literal STT **Except flight level 180**, ten minutes after departure, squawk 4131. Destination/route/callsign dan kata Expect belum verified.

| Area | Candidate wording | Syarat / lifecycle |
| --- | --- | --- |
| Keep in mind · LIMIT | `… Julia Charlie · Maintain 3,000 ft` | Jangan mengganti assigned altitude menjadi FL180 |
| Keep in mind · INTENT | `Squawk 4131` | Source clearance slot, bukan bukti transponder benar-benar sudah diset |
| Needs attention · INFO | `Clearance issued · 3,000 ft / 4131` | Fact table hanya supported slots; tidak menampilkan full readback match |
| Review-only pending interpretation | `FL180 · wording before level unresolved` | `live.attention=false`; bukan card noise/unreadable di rail |

Sesudah audio audit bila memang **expect FL180 10 minutes after departure** terdengar, expectation menjadi memory terpisah dari **assigned 3,000**. Jangan membuat automatic countdown dari timestamp clearance sebagai actual departure time. Readback clearance lengkap tidak ada; `No readback in stored clip` adalah coverage fact, bukan violation.

**Map authored:** dua entity terpisah untuk departure Kilo Alpha dan ground clearance Julia Charlie. Jangan membuat altitude divergence detector baru hanya untuk clip ini; wire Track saat ini tidak menyediakan altitude conformance lengkap. Type/registration tidak dipaksakan dari STT rusak. Timestamp case **11 September** dipertahankan.

### C5 — 123: Handoff frequency dan isolation exchange

**Evidence:** 40.1–44.0 s contact departure 119.35 kepada kandidat Cardinal/936; 45.1–49.6 s respons mengulang 119.35 dengan identity/heading rusak. Pertukaran frequency change 100.0–106.2 s berpotensi objek lain.

| Area | Candidate wording | Syarat / lifecycle |
| --- | --- | --- |
| Keep in mind · INTENT | `… 936 · Contact departure 119.35` | Instruction memory; label identity tetap candidate |
| Needs attention · INFO | `119.35 · Frequency read back` | Tabel slot frequency saja; MATCHED frequency bukan whole-transmission MATCHED |
| Separate memory item | `Frequency change approved · separate transmission` | Entity unknown bila belum identified; tidak merge dengan 936 |

Heading tidak ditampilkan sebagai angka tertentu dari phrase “heading into 00”. Readback frequency tidak membuktikan pilot sudah membuat contact ke departure; tidak otomatis resolve dengan wording “handoff completed”. UI selesai memutar audio pun bukan bukti contact selesai.

**Map authored:** departure centre point bergerak keluar dari airport context. Posisi last-known/stale jelas; tidak menghilangkan unknown aircraft untuk menyatakan traffic clear. Tidak mengarang turn untuk menyesuaikan heading yang belum terbaca.

## 5. Kontrak highlight dan perhatian

Gunakan komponen yang ada, dengan dua lapisan yang berbeda:

- **Keep in mind:** facts yang masih berlaku—route/action, clearance limit, conditional permission, traffic advised, frequency, squawk. Step berikutnya hanya mengganti yang terkait; displayed `Was` dan Done mengikuti evidence, bukan akhir clip atau jadwal yang diketahui lebih dulu.
- **Needs attention:** supported discrepancy jika benar-benar ada, atau noteworthy fact dengan priority INFO/NOTICE. Positive readback boleh INFO; jangan menjadikannya ATTENTION. Lima case tidak diwajibkan masing-masing memiliki hazard, mismatch atau minimal jumlah alert.

Rencana 1–2 key cards/case, bukan setiap segment menjadi card. Condition/unknown dikemas dalam fact/slot row. Lost/unreadable transmissions tetap transcript/timeline/Review dengan `live.attention=false`, mengikuti keputusan user. Tidak menambahkan saran tindakan, auto-clearance, open loop panel, atau auto-focus yang merebut playback.

Case fact cards memakai `live.facts`; comparison memakai Said/Heard per-slot (`MATCHED`, `MISMATCH`, `MISSING`, `AMBIGUOUS`). Callsign frequency/altitude/squawk bukan kategori slot DSL yang sekarang hanya CALLSIGN/RUNWAY/ACTION/CONDITION/NEGATION: gunakan **fact rows** untuk frequency/altitude/squawk, atau tambah typed optional display extension pada demo saja. Jangan menyelundupkan frequency sebagai RUNWAY slot atau mengubah frozen generated contract tanpa version review.

Waktu source/event, delay demo, processing time dan actual STT available-at 2026 terpisah. Word lag 0.4s dan role sesudah final tetap; finding available setelah supporting utterance selesai. `until/resolved` untuk card non-readback harus mereferensikan actual authored event/explicit voice evidence, bukan sekadar timer global. Linger 30s dipertahankan. Context/condition mismatch tidak boleh auto-resolved hanya karena posisi keluar polygon.

UI mengikuti skill `ui-ux-pro-max`: query targeted status information menemukan guideline **Color Only**, relevan untuk rail. Gunakan teks/icon/table untuk state selain warna, focus/keyboard Listen/View evidence, dan tidak membacakan UTC tick setiap 100ms ke screen reader. Palette dan layout existing dipertahankan; tidak membutuhkan design-system baru.

## 6. Data dan build strategy

### Assets baru

Rencanakan lima package `data/demo-scenarios/kagc-2022-09-10-{50,51,47,123}/` dan **`kagc-2022-09-11-156/`**, ignored. Masing-masing memuat immutable WAV, original TXT metadata, derived PCM16, waveform peaks, authored CSV raw-schema, scenario.json v2 dan provenance/checksum manifest. C2 mempunyai optional part50 dengan same source SHA seperti standalone C1.

Tidak mengambil ADS-B Agustus sebagai observation September. New CSV dibuat sebagai authored demo dataset, dikalibrasi secara umum dari research yang ada; doc/provenance menandai asal generated, bukan paired historical ADS-B. Preserve per-asset source kinds (PUBLIC_CORPUS audio, STT_HYPOTHESIS transcript, SYNTHETIC track, AUTHORED_FINDING). Tidak memasukkan WAV/corpus text/private credentials ke Git atau frontend public bundle.

Jangan reuse new CSV ketika beda episode/callsign hanya karena suffix serupa. Collision part ID `50` antarskenario harus scoped; global entity/evidence IDs memakai scenario namespace. Authored waypoints mempunyai constraints seperti max speed, geometry continuity, gap/stale states, date rollover; label physics assumed tidak menjadi hasil evaluasi domain. Tidak mengubah layout `kagc-2`, protected CSV atau events85.7/90.7/92.7 pada 88.

### Builder yang terpisah

Tambah entrypoint baru yang membangun **hanya lima cases**, bukan refactor generator 87/88. Usulan:

- `scripts/demo/build_additional_scenarios.py`: whitelist IDs, cached STT input, validated manifests, deterministic variants.
- `scripts/demo/synth_additional_adsb.py`: independent per-case trajectory specs dengan stable seed dan event provenance.
- `scripts/demo/additional_cases/`: authored case definitions/evidence mappings dipisahkan dari IO/media helpers bila kompleksitas membutuhkan.
- `scripts/demo/fetch_additional_scenarios.sh`: SCP lima existing WAV/TXT melalui SSH; SHA verification; no provider calls. Config host/key tetap environment di luar repo. Jangan memanggil fetch_scenario.sh atau mengekstrak audio langsung di host lokal.

Read-only reuse `kagc_layout.py`, shared parser dan media/variant helpers boleh; jangan memindahkan/mengubah fungsi builder87/88. Builder gagal jika selected IDs memasukkan 87/88 atau target path keluar whitelist. Write derived/CSV/scenario assets ke new directories secara atomic; tidak overwrite different source WAV hash. Audio51 full source dipertahankan; source50 reuse tidak dibuat concat file.

## 7. Registry/import changes yang diperlukan

1. **Additive catalogue.** Extend `/api/demo/scenarios` dengan optional `scenarios: [{id,title,main_part,files,limits}]`, file metadata termasuk `scenario_id`, part/position/role dan checksum/size. Existing `expected_files/files` tetap tersedia untuk compatibility. Catalogue bukan endpoint generic local filesystem.
2. **Resolve scoped scenario.** Upload menerima optional `scenario_id`. Jika diberikan, file validation scoped di registry tersebut. Tanpa ID, infer hanya jika entire main/file set mempunyai exactly one eligible scenario; ambiguity ditolak dengan pilihan case. Jangan memilih first filename match, terutama 50 yang eligible sebagai main dan before.
3. **Per-case lanes.** New import catalogue selection (atau inference dari unique main) menghasilkan `known` files per case. Main case tidak boleh diganti diam-diam saat drop audio main kedua. Reject/recovery “Choose a case” atau “These files belong to different cases”; existing checksum/position/duplicate/cross-scenario guards dipertahankan.
4. **New limits scoped.** New manifest limits before1/after1, max3 recordings/max6 paired files. Disable add buttons atau tampilkan error inline saat batas tercapai; server juga enforce. Defaults existing88 tetap legacy; **jangan mengurangi max global atau mengubah existing87/88 import** atas nama scope new cases.
5. **Supported parts only.** C2 menerima before50; kasus lain tidak punya companion. Jangan menerima arbitrary chronological file sebagai before/after tanpa defined manifest/evidence variant. Tidak menambah tombol Add recording di workspace.
6. **Preserve storage.** Registry get/build per scenario; seeding katalog tidak otomatis membuat atau menghapus workspace pengguna. DB schema dapat tetap karena scenario_id/variant tersedia. ID/build/cursor/session user tidak di-reset. Analyse stored case baru hanya ketika build case tersebut berubah.

Perubahan demo port/client bersifat additive; shared `contracts.ts` tidak berubah untuk scene expansion. New API fields boleh optional pada demo-specific types, client/fixture tetap kompatibel. Jangan mengubah settings/users, provider, authentication atau production backend untuk task ini.

## 8. Urutan implementasi dan exit checks

| Tahap | Pekerjaan | Exit yang diperlukan |
| --- | --- | --- |
| E0 · Protect baseline | Record protected asset/source/build checksums, legacy API shape dan existing replay signature tanpa modify | Protected87/88 fingerprints tersimpan di ignored evidence; saved workspace/cursor tidak berubah |
| E1 · Case packets | Audit critical spans kelima cached recordings, identify candidates, word/event/evidence ranges, source-date/gap mapping | Setiap live card mempunyai supporting evidence; unsupported cards disembunyikan/revised; human audit dilaporkan sebagai status terpisah |
| E2 · Assets/build | Fetch bounded existing source melalui SSH, new media/CSV/manifests, seven new variants | SHA/size/sample duration, deterministic IDs, refs within range dan date156/gapC2 benar; no protected writes |
| E3 · Registry/API | Add scoped catalogue/resolution, per-new-case limits, compatibility | Main50 vs before50 disambiguation, duplicate/unknown/checksum/cross-case/wrong-position rejection; legacy smoke PASS |
| E4 · Import/client | Scenario selection/inference, scoped RecordingSlots, 0/1 side caps | Drop five main files tidak overwrite; mixed cases tidak accepted; before50 pasangan51 benar |
| E5 · Workspace/highlights | Populate new spec/live/reminders/facts; reuse existing player/rail | Causal appearances, isolation entities, no fabricated mismatch, correct range audio, seek reconstruction |
| E6 · QA/handoff | Tests on disposable workspace/database, browser replay/import, preserve legacy | Semua new acceptance + protected legacy checks; current user workspaces untouched; docs/exact evidence updated |

Tests yang bermakna untuk implementasi nanti:

- **Catalogue/scoping:** same50 bytes eligible dua case, main50alone selects C1, 50+51 selects explicit C2, 50before without51 rejected; accidental mixed-case not accepted. Five main filenames dalam satu drop tidak menggantikan state tanpa pemberitahuan.
- **Caps:** fourth recording atau second before/after rejected untuk new manifests di frontend dan server, optional CSV withoutaudio rejected; sixfiles valid bila manifest memang mendefinisikan before/main/after. Existing88 behavior remains unchanged.
- **Time:** main51 offset120.002886s di composed context; decoded-gap residual; no readback/highlight appears sebelum wordsfinal+delay; rewind mengembalikan state yang sesuai. UTC-date rollover156 preserved, tidak force metadata ke10Sep.
- **Case semantics:** Quebec/Alpha berbeda, voice departure-roll ≠ observed occupancy, “if needed” bukan unconditional, 3,000 assigned ≠ FL180 expected, 119.35 matched ≠ whole heading/callsign matched/contact completed.
- **Evidence:** Listen memainkan part/range yang tepat; global timeline selection di50/51 mengarah ke source-local offsets; UUID/evidence/source hash tidak silang case. Separate slot/fact UI tetap keyboard-readable.
- **Protected regression:** compare 87/88 raw/derived/CSV/scenario hashes, spec/build/variant keys, timelines, card text/count/reminders, phase processing, canonical geometry dan IDs. Browse existing workspace read-only; tidak reprocess/delete/rename user session atau regenerateprotected fixtures.
- **Browser:** semua lima standalone imports (temporary test workspaces), C2 beforeaudio variant dan beforeaudio+CSV variant, pause/seek/resume, persisted cursor, audio HTTP206, no console/overflow1280×720/1440×900. Smoke legacy session87/88 dan seedcatalog.

Commands sesuai suites yang tersedia: Compose demo profile `test` untuk pytest pada `_test`, ruff/typechecks yang relevan, frontend `typecheck/lint/test/check:types/check:copy/build`, Python Playwright demo journeys. Tests aplikasi ini **belum dijalankan pada rencana ini**, karena source aplikasi belum berubah. Existing counts21pytest/58vitest/17journeys pada handoff adalah historical evidence, bukan hasil expansion.

## 9. Risiko konkret dan keputusan engineering

- Bukti STT tidak sempurna. Utamakan slot yang terdengar jelas; five-case target tidak membenarkan full callsign, expectation, turn heading atau mismatch yang direka. Source quotes/corrections tetap immutable/revisioned.
- 50 sebagai main/before adalah registry ambiguity nyata; selesaikan sebelum enable catalogue. Fitur memilih kasus kecil dan scoped lebih aman daripada mencoba heuristik filename global.
- Shared builder/layout dapat tidak sengaja meregenerasi88. Gunakan new-only whitelist builder, no protected targets, baseline hash comparison, dan tidak edit existinggenerator.
- Case156 tidak menuntut altitude detector baru dan case123 tidak menuntut radio-contact observation; Keep in mind memberikan nilai tanpa memaksakan physical findings yang unsupported.
- Kegunaan mock di map berasal dari controlled authored tracks, bukan research surface coverage. Dokumen mencatat asal data; user-facing copy existing tidak otomatis memberi otoritas operasi.
- Rebuild-on-read sekarang mutable terhadap latestcasehash. New files tidak boleh mengubah oldbuild; jangan auto-bump catalogueglobalversion sebagai per-caseanalysis input. Perubahan provenance pipeline baru memerlukan doc/ADR update secara scoped, bukan mengubah PRD prodstack.

Tidak ada blocker untuk perencanaan. Sebelum shipping cards, critical-span review dan scoped importer acceptance menjadi exit evidence teknis/data; tanpa review, card supportedness dibatasi. Tidak ada cloud/provider cost atau migration/deploy yang diperlukan untuk expansion cached demo ini.

## 10. Performed work sesi perencanaan

PRD/rules/handoff/ADR/current demo docs dan source registry/import/attention/spec diperiksa ulang. Cached case words/timestamps/metadata dibandingkan melalui SSH; tidak download raw baru, tidak provider call. Candidate evidence tersimpan ignored; data87/88, application source, runtime dan workspace pengguna tidak diubah. Baru dokumen rencana, index dan handoff yang diperbarui. Pemeriksaan dokumen/evidence dilaporkan pada handoff; tidak mengklaim implementation/tests/browser/domain review selesai.


## 11. Completion record — 12 Oktober 2026

Instruksi `proceed` mengotorisasi rekomendasi lima rekaman audio. Lima packages baru dan tujuh variants sudah dibangun; API catalogue sekarang mengenali enam skenario. UI Import mempunyai pilihan Case dan file matching scoped, dengan caps untuk kasus baru; legacy 87/88 tetap. WAV diambil melalui SSH dan cocok dengan cached SHA; raw STT immutable, annotations candidate, tanpa provider call.

New-only helpers: `build_additional_scenarios.py`, `fetch_additional_scenarios.py`, `synth_additional_adsb.py`. Semua case mempunyai controlled centre-point fixtures untuk konteks visual, bukan historical ADS-B atau flight physics. Ground/real altitude/footprint conformance tidak dibuktikan; seluruh finding movement NOT_EVALUABLE. Candidate labels dipadatkan (Quebec?, Alpha?, Uniform?, Julia Charlie?, Kilo Alpha?, 936?) agar map lebih terbaca. Prior-clip entity berlabel [50], tidak silent merge dengan main; track menjadi stale sesudah coverage berakhir. Reminder title tidak mengulang entity prefix. Turnout Alpha tidak menjadi landing instruction; readiness Uniform adalah REPORT, bukan readback; assigned 3,000 tetap terpisah dari FL180.

Checks: 28 backend pytest termasuk lima standalone/context/catalogue, 61 Vitest termasuk scope/limit/no-overwrite; typecheck/lint/generated-type/copy/build; Ruff format/check dan mypy untuk backend yang berubah. Enam browser imports melalui UI (lima standalone + 51 dengan before 50) memeriksa processing, registered workspace, cards/reminders, audio 206, serta no console errors. Final replay/seek-to-zero/no-future, overflow 1280×720 dan screenshot inspection dilakukan. Visual follow-up C51+before50 pada final copy/labels lulus. Seluruh 13 protected raw/derived/CSV/scenario/generator/layout fingerprints 87/88 tidak berubah. Enam matrix fixtures dan satu visual fixture milik QA dibersihkan melalui UUID + name prefix; user workspaces tidak dihapus.

Assets/cache/browser evidence private dan ignored. Case baru tersedia pada Import tanpa otomatis membuat workspace pengguna. Normal Docker build gagal DNS `auth.docker.io`; incremental runtime image dari immutable existing cache berhasil dan source checksum container cocok dengan workspace. Clean Docker Hub build belum verified. API localhost:8000 dan Vite localhost:5173 tetap berjalan; tidak commit/push/production deploy/gate change. Human/domain review tidak diklaim. Usage folder dan batas data: [demoWorkspace.md](demoWorkspace.md).
