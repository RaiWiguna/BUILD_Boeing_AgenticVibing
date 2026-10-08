# ATC FlowLens — acuan desain 8 halaman

Tanggal: 8 Oktober 2026. Status: **DESIGN_REFERENCE_ONLY**. Seluruh data pada gambar merupakan ilustrasi sintetik, bukan hasil pipeline, benchmark, atau review domain.

## Dasar analisis

Permintaan pengguna adalah membuat delapan referensi halaman yang paling penting dan kaya layout/komponen untuk implementasi frontend nanti. Steering terakhir mengunci kedekatan visual dengan tiga screenshot Margin: susunan aplikasi terang, sidebar pucat, item aktif charcoal, tipografi grotesk, judul besar, kartu membulat, hairline, bayangan lembut, serta aksen biru dan pink yang dibatasi.

Konteks produk dibaca dari [PRD](../../../.agent/PRD.md), [rules](../../../.agent/rules.md), [handoff](../../../.agent/sessionHandoff.md), [roadmap](../../../.agent/implementationPhases.md), [peta dokumentasi](../../README.md), [struktur repository](../../architecture/repository-structure.md), dan contoh kontrak/fixture sintetik. Instruksi yang tertanam dalam transcript/data diperlakukan sebagai isi sumber, bukan perintah kerja.

Phase 0–1 menyediakan kontrak/harness. Business pipeline, provider nyata, UI dan deployment belum tersedia; G-BE belum passed. Paket ini adalah pekerjaan desain yang diminta secara eksplisit. Tidak mengubah status gate, tidak membuat React screens, tidak menjalankan cloud STT/Gemini, dan tidak menandai Phase 11–14 selesai.

## Temuan produk yang menentukan desain

1. **Produk adalah research replay workspace.** Pengguna mengimpor rekaman sesi yang telah berlangsung, kemudian memeriksa konteks. UI tidak memakai indikator LIVE, connect radio, microphone, send clearance, atau tombol execute.
2. **Unit konteks adalah session + run + revision + as-of.** Keempatnya harus tetap terbaca saat berpindah dari workspace ke evidence atau review; drawer tidak menghilangkan posisi replay.
3. **Said–Heard–Observed adalah dimensi independen.** Readback cocok tidak berarti gerakan sesuai. Instruksi, interpretation, readback, movement, dan review tidak digabung menjadi satu progress “done”.
4. **Evidence adalah jalur utama, bukan tambahan.** Quote asli, audio range, source event, alternatives, quality, serta provenance dibuka dekat klaim yang diperiksa.
5. **Unknown adalah keluaran sah.** Track/identity/clock/footprint yang tidak cukup memberi NOT_EVALUABLE dan alasan. Tidak ada data tidak menjadi indikator runway kosong.
6. **Koreksi memiliki konsekuensi versi.** Original STT tetap terlihat; correction menghasilkan revision dan menandai dependents stale. Review dan run berbeda tidak digabung diam-diam.
7. **Readiness mempunyai tiga sumbu.** SOURCE_READY, ANALYSIS_READY, dan DOMAIN_REVIEWED disajikan terpisah. Source dapat disimpan saat analisis belum eligible.
8. **Opsi merupakan alternatif hipotetis.** Evidence, applicability, preconditions, unknowns, consequences/tradeoffs dan review wajib terlihat. Nol opsi saat konteks kurang adalah hasil yang sah.
9. **Peran menentukan tindakan.** Evaluator mendapat kontrol sesuai grant; observer membaca tanpa mutation; admin tidak otomatis dapat review aviasi. Audio/export/truth memiliki grant terpisah.
10. **As-known dan debrief berbeda.** As-known menyaring available time; debrief dapat menampilkan correction belakangan dengan label. Replay offset tidak dicampur dengan tanggal/waktu dinding.

Hasil pencarian ui-ux-pro-max awal memberi pattern marketing dan palette yang tidak cocok; hasil tersebut tidak dipersist. Retry enterprise operations memberi minimalism/Swiss, Inter dan neutral charcoal yang cocok. Pattern landing page dan gold accent tetap tidak digunakan. Keputusan warna/layout berasal dari screenshot dan PRD; pedoman keyboard, contrast, label, focus dan motion digunakan sebagai persyaratan implementasi mendatang.

## Mengapa delapan halaman ini

| Halaman | Pentingnya | Keragaman komponen dan layout | Kontrak utama |
| --- | --- | --- | --- |
| 01 Katalog Sesi | Entry point dan pemilihan sumber/run | Summary strip, filter, tabs, table, selection rail, readiness, notices | FR-01/02/16/17; AC-01/02/14/15 |
| 02 Import & Readiness | Menentukan kelayakan sebelum pemrosesan | Stepper, file inventory, upload, manifest preview, permission matrix, remediation, readiness card | FR-01/03/16; AC-01/03/14 |
| 03 Replay Workspace | Pusat pemahaman sesi | Situation canvas, memory strips, attention rail, multi-channel waveform, seek/speed/follow | FR-02/06/08/09/10/17; AC-02/06/08/09/10/15/20 |
| 04 Memori Objek & Runway | Menjelaskan keadaan yang sedang berlaku | Independent state rows, quoted slots, object/runway tabs, context history, open loops, provenance | FR-05/06/08/10; AC-05/06/08/10 |
| 05 Transcript & Association | Memperbaiki interpretasi dan pairing | Transcript table, selected inspector, original hypothesis, alternatives, correction form, range audio | FR-03/04/05/12; AC-03/04/05/12 |
| 06 Temuan & Evidence | Menilai klaim berdasarkan sumber | Queue/detail/docked drawer, side-by-side quotes, waveform, source-alert distinction, review form | FR-07/09/10/12; AC-07/09/10/12 |
| 07 Kandidat Opsi | Evaluasi alternatif tanpa authority leakage | Option rail, evidence dossier, eligibility, preconditions/unknowns, ratings/reason, insufficient context | FR-11/12; AC-11/12 |
| 08 Debrief & Export | Menyusun hasil dan membagikan laporan berizin | Version selector, journal, evidence-linked brief, unresolved gaps, format controls, redaction/expiry | FR-13/16; AC-13/14 |

Login dan settings tetap P0, tetapi tidak masuk delapan comp karena delapan ini memberi coverage terluas atas core research journey. Halaman admin tetap harus dirancang saat Phase 13.4, memakai shell/tokens yang sama untuk users/grants, provider readiness, jobs/budget/disk/audit/retention. P1 contextual query dan communication metrics tidak ditampilkan sebagai feature selesai.

## Arah brand dan hubungan dengan referensi

**Nama:** ATC FlowLens, dengan wordmark ringkas FlowLens pada sidebar. **Audiens:** evaluator/instruktur, controller-review, observer riset. **Janji produk:** konteks komunikasi dapat diperiksa melalui bukti.

Metafora brand adalah lens yang memusatkan perhatian pada jalur komunikasi dan observation yang tetap terpisah. Glyph biru monoline pada gambar merupakan eksplorasi identitas, belum logo final/official. Gunakan mark yang konsisten pada seluruh comp; asset produksi nanti dibuat sebagai SVG yang crisp, bukan raster crop dari mockup.

Yang dipertahankan dari referensi: app surface, nav aktif charcoal, judul normal/medium, ruang putih, card edges, controls bertonal, hairline, rounded badges, icon outline, dan penggunaan biru/pink yang ekonomis. Yang diadaptasi: finance KPI menjadi readiness; finance charts menjadi source timelines/situation/evidence; job detail menjadi object dossier; forecast interventions menjadi hypothetical-option review.

Tidak memakai foto pesawat, scenery, gradient promosi atau chart dekoratif. Materi domain sudah datang dari waveform, source traces, evidence rails, dan layout runway fiktif. Aturan marketing pada imagegen-frontend-web disesuaikan dengan permintaan eksplisit aplikasi padat komponen: satu gambar horizontal per **halaman**, seluruhnya native app screen, tanpa device frame atau collage. Brandkit digunakan untuk strategi, metafora dan konsistensi identitas; tidak menambah board kesembilan.

## Sistem visual

| Token/peran | Nilai usulan | Pemakaian |
| --- | --- | --- |
| Canvas | #F5F6F7 | Background aplikasi |
| Surface | #FFFFFF | Card, drawer, input |
| Sidebar | #F4F5F6 | Navigation shell |
| Text primary | #191B20 | Heading dan isi utama |
| Text secondary | #616975 | Metadata yang tetap terbaca |
| Hairline | #E4E7EB | Divider dekoratif; bukan satu-satunya batas kontrol |
| Control boundary | #7E8999 | Batas input/control ketika diperlukan |
| Primary action | #303237 / putih | Satu aksi utama per konteks |
| Selected/data | #2563EB / #EAF1FF | Selection, evidence links, waveform |
| Discrepancy | #B82B69 / #FCEAF2 | Slot mismatch dan ATTENTION, dengan teks |
| Gap/notice | #96610B / #FFF4DE | Missing context, permission unknown, NOTICE |
| Source ready | #167B46 / #EAF7EF | Hanya sumber/readiness terverifikasi |
| Muted state | #596273 / #EEF0F3 | NOT_EVALUABLE, archived, unavailable |

Font: Inter atau equivalent refined grotesk. Heading utama 40–44 px / 1.1 / weight 500 / tracking -0.035em. Section heading 20–22 px / 1.3 / 500–600. Body 16 px / 1.5 / 400. Compact table 14 px / 1.45; caption 13 px / 1.45. Critical quotes 16–18 px; timestamps tabular-nums. Tidak memakai monospace pada seluruh heading.

Radius: card 24 px; drawer 24 px; button/input 12 px; compact pill 999 px; app perimeter presentational 28 px. App perimeter tidak diwajibkan saat aplikasi fullscreen. Border 1 px; shadow card sangat ringan; selected nav sedikit lebih terasa. Hindari shadow pada setiap inner group.

Grid desktop: baseline 1440×900; sidebar 224 px; main padding 28 px; gutter 20 px; card padding 24 px. Rhythm 4/8/12/16/20/24/32/40. Buttons/input tinggi 44 px; icon 18–20 px dengan stroke konsisten. Klik icon tetap diberi hit area memadai. Page title dapat dipadatkan menjadi 32 px pada viewport kecil.

Semua values merupakan **design proposals**, bukan pengukuran screenshot atau klaim accessibility pass. [tokens.json](tokens.json) menyimpan nilai untuk handoff Phase 11. Kontras tokens diperiksa secara numerik; screenshots tetap harus diuji ulang ketika menjadi UI.

## Shell dan navigasi

Navigation utama tetap lima area PRD: Sesi, Workspace, Review, Debrief, Pengaturan. Empat area kerja ada pada kelompok utama; Pengaturan di bawah bersama Bantuan. Tiga jenis review menjadi contextual tabs Transcript / Temuan / Opsi, bukan tiga menu utama tambahan. Import berada di Sesi; Memori berada di Workspace.

Header session-scoped memuat session name, source label, replay mode, selected run/input revision dan as-of. Connection dan analysis state dibedakan: “Terhubung” mengacu server; “Hasil tersimpan” mengacu artifact cache. Koneksi provider tidak disimpulkan dari kedua label ini.

Tampilan akun “Evaluator” pada comps adalah ilustrasi peran, bukan login nyata. Production memakai nama akun dan effective session grant. Source kind serta domain-review label diambil dari data backend.

## Spesifikasi per halaman

### 01 — Katalog Sesi

[Comp](images/01-sessions.png). Layout: main header → strip metadata → table 70% dan detail rail 30%. Table diutamakan dibanding grid kartu agar 100 metadata sesi tetap dapat dipindai.

Selected row diberi pale-blue background, left blue rule dan selected semantics. Filter status/search/tab mengubah list tanpa mengganti session aktif secara implisit. Klik nama/select memilih detail; “Buka workspace” menjadi navigasi explicit ke chosen run. Tidak memilih run terbaru diam-diam bila pengguna telah memilih run lain.

Sumbu sumber/analisis/domain-review tetap terpisah. Counts adalah jumlah ilustratif, bukan accuracy atau score safety. Format tanggal produksi mengikuti locale dan timezone sumber yang jelas; tanggal pada comp katalog adalah contoh bebas, bukan status repository.

States: tidak ada sesi → “Import sesi pertama”; permission denied → alasan akses; partial → coverage yang belum dianalisis; provider unavailable → arsip tetap bisa dibuka; archived → read-only. Notice rail memberi link langsung ke sesi yang perlu remediation.

### 02 — Import & Readiness

[Comp](images/02-import-readiness.png). Layout: stepper di atas; structured preview 67% dan readiness rail 33%. Preview bukan cloud analysis.

Source inventory menampilkan file asli, detected type, channel labels, decoded duration, checksum dan validation result. Tombol tambah file mempunyai file-picker sebagai alternatif drag. Metadata tambahan memakai disclosure agar source clock, offset/uncertainty, units, layout version, identity mapping dan retention tidak membanjiri first fold.

Permission matrix minimal: local read, cloud audio, cloud transcript/context, reviewer access, report export dan audio export. Screenshot menampilkan subset; detail permission wajib melengkapi reviewer access. ALLOWED/DENIED/UNDETERMINED memakai label, icon dan penjelasan.

State yang dipilih: source dapat disimpan, cloud audio UNDETERMINED, track missing nonblocking, profile belum verified. “Simpan sesi” enabled sesuai local permission; “Mulai analisis” disabled dengan blocker terdekat. Pada source committed eligible, action analisis membuka review volume/request dan profil sebelum explicit submission.

Blocking validation menampilkan file/field/row/kode dan recovery. Nonblocking missing track mematikan movement conformance. Extension/type pada UI produksi harus berasal dari validation; contoh generated comp menunjukkan ground.wav/FLAC, gunakan ground.flac bila tipe FLAC agar label tidak bertentangan.

### 03 — Replay Workspace

[Comp](images/03-replay-workspace.png). Layout: 68% situation + memory, 32% attention, bottom timeline 150–170 px. Header tetap memperlihatkan clock/mode/run.

Situation view adalah schematic dari layout berversi. Observed solid, predicted dashed dengan label/eligibility, uncertainty bukan coordinates palsu. Kendaraan missing muncul dalam notice tanpa marker posisi. Gambar runway hanya ilustrasi arsitektur layar; geometri produksi berasal dari layout fixture/server, tidak dijiplak dari raster.

FLN214 pada contoh punya centre-point trace, tetapi footprint belum tersedia: gerakan NOT_EVALUABLE. Objek lain dapat punya eligibility berbeda. Readback discrepancy mempunyai kedua quote evidence. Open-loop notice berbunyi “belum teramati pada coverage tersimpan”, bukan klaim respons tidak pernah terjadi.

Memory strip mempertahankan instruction/readback/movement/source age sebagai kolom independen. Klik strip membuka object detail; “Lihat bukti” membuka drawer tanpa reset clock. Attention filter menangani entity/runway/category/status; tidak auto-focus/siren.

Player: pause/play, prev/next event, seek dengan numeric input atau event list, 0.5×/1×/2×, follow leader/local. Tower dan Ground memakai clock sama. Gap diarsir dan diberi label; evidence range mempunyai handles plus tombol/numeric controls. Seek tidak memanggil provider.

Audio-only state mengganti map dengan object/runway context + coverage. Track stale memudarkan trace dengan age/alasan; tidak mempertahankan status gerakan lama sebagai hasil fresh. Reconnect memberi “Menyelaraskan ulang” dan snapshot/seq, tanpa duplicate review.

### 04 — Memori Objek & Runway

[Comp](images/04-operational-memory.png). Layout: context/history 60%, runway/open loops/provenance 40%. Comp ini menunjukkan state audio-only, berbeda dari workspace dengan point traces.

Said row: original quote, instruction lifecycle, evidence. Heard row: candidate quote, comparison slot/readback status, association quality. Observed row: missing position/alasan NOT_EVALUABLE; tidak menggunakan body “Supported” sebagai bukti kesesuaian fisik. Reviewer dimension independen.

Runway mini-diagram menunjukkan keterkaitan konteks, bukan lokasi aktual. Implementasi sebaiknya memakai list/link entities pada state audio-only agar marker konteks tidak disangka track. Caption wajib jelas. Tab Runway mengelompokkan object memory terkait, instructions, occupancy intervals bila eligible, open loops, source ages, dan coverage gaps.

History disaring as-of. Future correction 05:24 tidak muncul pada as-known 05:22. Debrief boleh menampilkannya dengan original/superseding relationship. Timer open-loop berasal dari LAB_RULE version, bukan universal threshold.

### 05 — Review Transcript & Association

[Comp](images/05-transcript-association.png). Layout: transcript list 63%, selected inspector 37%, waveform dalam konteks sama. Review mode DEBRIEF memungkinkan correction 05:24 terlihat.

Original STT tidak pernah menjadi textarea editable. Editable correction adalah field terpisah dengan revision/reason/evidence. Kandidat callsign/pairing tidak menjadi speaker identity authoritative. Speaker role dan addressee tetap field berbeda.

Radio alternatives termasuk unresolved. Pairing review dan text correction adalah mutation berbeda; production memberi label save khusus untuk perubahan yang dipilih. Form awal tidak otomatis mengonfirmasi pairing. “Simpan revisi” disabled sampai perubahan/alasan valid; comp menggambarkan posisi kontrol, bukan submit eligibility final.

Critical slots memiliki quote span, original spelling dan uncertainty. Provider confidence null ditampilkan sebagai tidak tersedia bila relevan; bukan persentase kepastian buatan. Audio range T-13 adalah 05:16–05:19; timer player lokal harus berlabel offset cuplikan dengan total sesuai range, jangan menyalin total 00:30 pada generated comp.

Correction success menampilkan revision baru dan affected results stale, dengan action reanalysis explicit. Version conflict mempertahankan draft, membuka newer revision dan memberi pilihan reconcile; tidak menimpa review pengguna lain.

### 06 — Temuan & Evidence

[Comp](images/06-findings-evidence.png). Layout: queue/detail 58% main area, docked evidence sheet 42%; no blocking scrim di desktop. Quotes berdampingan, masing-masing source/ID/time/range.

As-known 05:22 hanya menampilkan eligible finding available sampai posisi itu. F-03 event 05:19, available 05:22; kedua dimensi terlihat. Queue F-04 05:21, F-05 05:18. Label speaker di Heard adalah “Kandidat”, bukan identity confirmed.

Finding priority INFO/NOTICE/ATTENTION berbeda dari severity source alert. Source alert yang unavailable tetap diberi alasan, tidak dilebur menjadi narasi AI. Ack tidak mengonfirmasi validity atau menyelesaikan masalah.

Review form memulai dengan semua radio kosong. Reason wajib; save disabled sebelum decision/reason valid. Dismissal/correction tetap append-only. Tombol close mengembalikan focus ke trigger; clock dan selected entity tetap sama. Evidence access denied menampilkan pembatasan, bukan fake empty waveform.

Alternatives/provenance disclosure memuat model/prompt/rule/input versions, quote spans, source quality, matching applicability dan review revision. Rationale singkat adalah penjelasan berbukti, bukan chain-of-thought.

### 07 — Kandidat Opsi

[Comp](images/07-options-review.png). Layout: quiet selection rail 22%, dossier 46%, evaluator form 32%. Dominant item adalah satu alternatif, bukan banyak intervention tiles.

Dossier mempunyai evaluation question, statement hipotetis, rationale/evidence, preconditions, unknowns, applicability, tradeoffs sebagai hipotesis, dan source versions. Tidak menampilkan skor “terbaik” atau tindakan kirim.

RELEVANT, NOT_RELEVANT, UNSUPPORTED, UNRESOLVED memakai label lokal. Semua awalnya unselected; alasan wajib; submit hanya menyimpan rating. Bukti dapat dibuka dengan grant. Radio selection tidak mengubah instruction atau memory.

VEH03 punya INSUFFICIENT_CONTEXT dan nol opsi. Action recovery mengarah source remediation/bukti yang dibutuhkan, bukan “buat opsi paksa”. Eligibility/permission bisa membatasi review meskipun opsi cached masih terbaca.

### 08 — Debrief & Export

[Comp](images/08-debrief-export.png). Layout: journal 27%, brief 44%, export 29%. Header memilih brief revision dan as-of replay, bukan waktu dinding.

Brief memisahkan known situation, active restrictions, perubahan konteks, open loops, findings, review status, unknown/coverage. Generated comp mengutamakan empat kelompok; production tetap menyertakan kelompok lain bila datanya ada. Setiap factual item punya scoped resolvable evidence.

Journal E-13 tetap “zero nine”; correction E-14 menyebut RWY27 dan tidak menimpa quote lama. Finding lama tetap dapat direview meski ada correction. Future correction hanya muncul di debrief sesuai selected revision.

Format HTML/CSV/JSON. Provenance locked on; redaction mandatory bila grant membatasi evidence, bukan toggle bebas untuk menghindari permission. Audio export terpisah dan disabled dengan alasan pada state ini. Scope run/revision dan expiry dari profil server; contoh 24 jam bukan keputusan retention global.

“Buat revisi brief” membuat artifact baru; stale brief diberi badge dan link ke perubahan sumber. Provider outage memperbolehkan reading/export eligible cached brief tanpa menghasilkan brief baru palsu. Export job states: preparing, ready, failed, expired, permission revoked; download hanya saat eligible.

## State dan interaction yang perlu dibangun nanti

| State | Lokasi utama | Copy/action yang disarankan |
| --- | --- | --- |
| Empty | Sessions/import | “Belum ada sesi” + Import sesi |
| Validating | Import | Per-file status; hindari satu spinner tanpa progress |
| Needs remediation | Import | Field/row/kode error + Perbaiki manifest |
| Processing / Partial | Session/workspace | Coverage hasil tersedia dan bagian belum selesai |
| Ambiguous callsign/slot | Transcript/evidence | Alternatives + Belum dapat dipastikan |
| Missing/stale track | Situation/memory | NOT_EVALUABLE + alasan/age; tidak green clear |
| AI unavailable | Workspace/options/brief | Hasil tersimpan tersedia; analisis baru terblokir |
| Stale derived result | Review/debrief | “Input telah berubah” + Lihat perubahan / Reanalisis |
| Conflict revision | Review | Pertahankan draft + Muat revisi terbaru |
| Connection lost/resync | Semua session view | Review mutation disabled; replay sesuai state server |
| Access denied/audio denied | Evidence/export | Jelaskan capability; jangan memuat konten tersembunyi |
| Expired login | Semua | Login ulang; committed review tetap tersimpan |
| Replay ended | Player | Posisi akhir + Replay dari awal / step ke event |
| Disk limit | Import/settings | Validation blocker + pengelolaan arsip sesuai grant |
| Export expired/revoked | Debrief | Alasan + Buat export baru bila permission cukup |

Toast sukses pendek melengkapi state lokal; error penting tetap inline. Loading tidak menyamar sebagai failure. Mutation tidak diantre offline; retry memperhatikan idempotency/expected revision dari server. Account/session switch harus menghapus cache scoped yang tidak eligible.

## Responsive, keyboard dan accessibility handoff

1440×900 adalah baseline. Pada 1280×720, sidebar collapse menjadi 72 px/rail, title mengecil, perhatian jadi tab/panel opsional, player tetap dapat diakses. Drawer memakai 440–480 px minimum bila cukup; pada narrow layout menjadi sheet dengan quote stack. Jangan mengecilkan semua font agar muat.

Tablet: panel situasi/memori/perhatian bertab; drawer full-width. Mobile: catalogue/detail/brief read-only; tidak memaksakan full workspace atau review editor. Semua layout menghormati 200% zoom dan tidak menutupi focused control.

Keyboard: skip link, nav, header controls, selected list/table, inspector, player; focus kembali ke trigger drawer. Arrow-key radio/tab semantics, Enter/Space activation, Escape close sesuai unsaved-draft flow. Play tidak autoplay. Timeline menyediakan controls selain drag; shortcuts ditampilkan bila enabled dan tidak mengambil alih input text.

Status tidak hanya warna: icon + text; pattern gap; solid/dashed trace dengan legend. Disabled controls memiliki reason, bukan opacity saja. Quotes critical tidak dipotong ellipsis; callsign/runway/negation dapat wrap secara wajar. Tooltip bukan satu-satunya sumber label.

Reduced motion menonaktifkan slide yang tidak perlu. Proposal motion: hover 120–160 ms; sheet 180–220 ms; state replacement pendek; tidak animate setiap replay tick. Screen reader hanya menerima perubahan status bermakna, bukan pengumuman clock per frame.

## Verifikasi paket dan batas acuan

Delapan final images diperiksa secara visual setelah generasi. Targeted edits memperbaiki future timestamps, kandidat attribution, review tanpa pilihan default, reason wajib, centre-point/footprint distinction, replay-vs-wall-clock, journal quote, dan provenance wajib. Gambar adalah raster konsep; microcopy, incidental dates/file labels, source roles, exact geometry, waveform amplitude dan counters harus memakai spesifikasi/DTO nyata saat implementation.

State di halaman berbeda merupakan contoh alternatif (full source, point-only, audio-only, ambiguous pairing, supported pairing), bukan screenshot dari satu run yang benar-benar berjalan. Evidence IDs pendek adalah label demonstrasi; implementasi memakai IDs kontrak scoped. Tidak boleh memasukkan generated examples sebagai gold evaluation labels.

Pemeriksaan yang dilakukan untuk deliverable: jumlah/dimensi/hash file, JSON validity, internal links, token text contrast, whitespace, dan inspeksi visual. Functional/browser accessibility, backend integration, real provider benchmark dan domain validation belum dijalankan karena task ini menghasilkan acuan desain.

## File paket

- [Galeri](index.html) — delapan referensi terpisah dalam satu navigasi lokal.
- [Token desain](tokens.json) — semantic token proposals.
- [Prompt generasi](prompts.json) — delapan prompt awal, refs dan continuity instructions.
- [Manifest](manifest.json) — final image filenames, hashes, dimensions, built-in generator dan corrective edit prompts.
- [Checklist pemeriksaan](verification.md) — performed checks dan batasnya.

Gunakan gambar untuk hierarchy/layout/style, dokumen ini untuk semantics/state/copy, dan kontrak backend/PRD untuk source-of-truth data serta authority. Paket ini tidak mengubah requirement atau status roadmap.
