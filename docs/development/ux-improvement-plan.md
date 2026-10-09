# Rencana perbaikan UX frontend FlowLens (MOCK track)

Tanggal: 9 Oktober 2026. Status: **UX-1 s.d. UX-5 diimplementasikan (9 Oktober 2026), belum commit** — lihat §8. Basis: branch `feat/fe-init` (commit `dc2134c`), adapter MOCK. Rujukan: [PRD §6, §11, §12, §17.3, §23](../../.agent/PRD.md), [rencana frontend](frontend-implementation-plan.md), [desain referensi](../design/2026-10-08-flowlens/README.md), [evidence MOCK](../testing/frontend-mock-evidence.md).

Guardrail tetap berlaku untuk semua perubahan: tanpa jalur clearance/execute/send/LIVE; Said–Heard–Observed terpisah; Unknown/NOT_EVALUABLE tidak hijau; As-known tidak membocorkan informasi masa depan; review append-only dengan reason wajib dan awal tanpa pilihan; label SYNTHETIC/MOCK selalu terlihat.

## 1. Cakupan dan metode

| Aspek | Yang diperiksa |
| --- | --- |
| Layar | Login, Sessions, Import, pemilih sesi (`/choose/*`), Workspace, evidence drawer, Memory (object, runway), Review (Transcript, Findings, Options), Debrief + Export, Metrics, Ask, Settings account, Help, command palette, notifikasi |
| Viewport | 1440×900 (screenshot full page per layar), ditambah hasil QA M3 sebelumnya di 1280×720, 1024×768, 390×844 |
| Peran | Evaluator (alur utama); Observer dan Admin dari journeys M3 |
| Sumber | Kode `frontend/src`, PRD, comps 01–08, aplikasi berjalan di dev server |
| Tidak dicakup | Skill domain `better-*` (accessibility, layout, writing, typography, colors, ui) tidak terpasang, jadi tidak ada review per domain formal. Uji screen reader nyata dan kontras terukur per state belum dilakukan |

## 2. Peta alur saat ini

```
Login ─► Sessions (pilih baris → rail detail → "Open workspace")
            │
            ├─► Workspace (as-of default = available time finding ATTENTION pertama, mis. 05:22, As-known)
            │      ├─ kartu attention → evidence drawer (URL ?evidence=)
            │      └─ "Review all" → Review
            ├─► Review: Transcript | Findings | Options  (mewarisi t + mode dari URL)
            ├─► Debrief (journal · summary · export)
            └─► Analyze: Memory · Metrics (P1) · Ask (P1)
Sidebar Workspace/Review/Debrief tanpa sesi aktif → /choose/* ("Choose a session first" → kembali ke Sessions)
```

Model mentalnya benar (sesi → replay → review → debrief), tetapi ada tiga masalah struktural:

1. **Konteks sesi tidak terlihat di navigasi.** Sidebar tidak menunjukkan sesi mana yang aktif, dan item sesi tanpa konteks berakhir di halaman buntu.
2. **Satu "as-of" dipakai untuk dua tujuan berbeda.** Waktu replay (Workspace) dan lensa review (Review, Ask) memakai parameter `t`/`mode` yang sama. Akibatnya, reviewer diam-diam melihat subset data.
3. **Loop kerja inti (review temuan satu per satu) belum dioptimalkan.** Tidak ada progres, tidak ada "berikutnya", dan form keputusan berada di bawah lipatan layar.

## 3. Temuan (urut dampak)

Severity: **HIGH** = memblokir tugas, menyesatkan, atau menyembunyikan konten/kontrol. **MEDIUM** = mengganggu pemahaman, efisiensi, atau konsistensi. **LOW** = polish terbatas.

| # | Sev | Temuan | Bukti | Dampak ke pengguna |
| --- | --- | --- | --- | --- |
| U-01 | HIGH | Jumlah temuan tidak konsisten antar layar. Rail Sessions menulis "5 open findings", tetapi link-nya membuka Findings dalam As-known 05:22 yang hanya menampilkan 3. Transcript menyembunyikan 11 segmen | `features/sessions/SessionsPage.tsx:374-378` (link tanpa `mode`); default as-of di `api/adapters/mock/engine.ts:443-446`; `hooks/useSessionScope.ts:41-51` | Reviewer mengira sudah meninjau semua, padahal 2 temuan tersembunyi. Ini menyesatkan |
| U-02 | HIGH | Di Workspace 1440×900, timeline yang sticky menutupi memory strips. Hanya ±80 px strip pertama yang terlihat, sedangkan FLN402/VEH03 tertutup. Di 1280×720 lebih parah | `features/workspace/WorkspacePage.tsx:139` (`md:sticky md:bottom-3`); screenshot `02_workspace` | Area "Memory", satu dari tiga area inti PRD §11, praktis tersembunyi |
| U-03 | HIGH | Command palette: item objek menuju `/s/:sid/memory/object/:id`, padahal route-nya `memory/:entityId`, sehingga hasilnya 404. Navigasi palette juga membuang `run`/`mode`/`t`, dan placeholder menjanjikan "findings" yang tidak ada | `components/layout/CommandPalette.tsx:33, 41-43, 61`; `app/routing/routes.tsx:53` | Link rusak; run/as-of berpindah diam-diam (bertentangan dengan PRD §12.2 "perubahan run harus explicit") |
| U-04 | HIGH | Sidebar tidak menampilkan sesi aktif. Workspace/Review/Debrief tanpa sesi menuju halaman buntu yang hanya berisi tombol kembali | `components/layout/Sidebar.tsx:55-66`; `features/sessions/SessionsPage.tsx:457-462` | Orientasi hilang ("saya sedang di sesi apa?"); satu klik terbuang |
| U-05 | MEDIUM | Loop review tidak efisien: tidak ada progres ("2/5 reviewed"), tidak ada simpan-lalu-lanjut, tidak ada filter default "Unreviewed", dan tidak ada shortcut keyboard keputusan | `features/evidence/FindingReviewForm.tsx:77-78`; `features/review/FindingsPage.tsx` | Tugas utama evaluator butuh banyak klik dan scroll per temuan |
| U-06 | MEDIUM | Form keputusan Findings berada di bawah lipatan layar (y ≈ 1160 di 1440×900), di bawah slot table dan provenance | screenshot `06_findings`; `features/evidence/EvidencePanel.tsx` (urutan blok) | Aksi utama tidak terlihat tanpa scroll |
| U-07 | MEDIUM | Deep link hilang: "Needs checking" dan notifikasi hanya memilih sesi atau halaman, tidak membuka item yang disebut (mis. F-03). Kartu attention di Workspace tidak punya aksi "Review this finding" | `features/sessions/SessionsPage.tsx:441`; `components/layout/NotificationsPopover.tsx:41` | Pengguna mencari ulang item yang sudah ditunjuk sistem |
| U-08 | MEDIUM | Header halaman sesi tidak konsisten. Memory punya breadcrumb, halaman lain tidak. Lokasi mode toggle berbeda-beda, dan Debrief/Metrics tidak punya toggle tetapi membawa `t` | `features/memory/MemoryPage.tsx`, `features/review/ReviewLayout.tsx:45`, `features/debrief/DebriefPage.tsx`, `features/workspace/SessionPageHeader.tsx` | Pola navigasi harus dipelajari ulang di tiap layar |
| U-09 | MEDIUM | Konten di scroller internal tanpa isyarat. Journal Debrief terpotong di tengah kalimat tanpa fade/"show more"; tabel transcript juga | `features/debrief/DebriefPage.tsx:129`; `features/review/TranscriptPage.tsx` (tabel `max-h`) | Item journal terlewat |
| U-10 | MEDIUM | Teks dipotong tanpa akses ke nilai penuh: memory strip ("A320 · De…", "Footprint not available (centre…") | `features/workspace/MemoryStrips.tsx:64-68` | Alasan NOT_EVALUABLE, informasi penting, tidak terbaca |
| U-11 | MEDIUM | Debrief tiga kolom: journal sempit (±250 px, teks pecah per 3 kata). Export permanen mengambil satu kolom padahal aksinya sekunder | screenshot `08_debrief`; `features/debrief/DebriefPage.tsx:399` | Ringkasan, yang merupakan konten utama, terdesak |
| U-12 | MEDIUM | Draf hilang tanpa peringatan: reason review/rating/koreksi tidak dijaga saat pindah halaman | `features/evidence/FindingReviewForm.tsx`, `features/review/OptionsPage.tsx`, `features/review/TranscriptPage.tsx` | Kehilangan tulisan (risiko data) |
| U-13 | LOW | Copy berulang: "AI findings and source alerts are recorded separately" muncul 2–3× di satu layar | `features/review/ReviewLayout.tsx:14`, `features/review/FindingsPage.tsx:135`, `features/evidence/EvidencePanel.tsx:325` | Noise |
| U-14 | LOW | Kolom "Analysis" di Sessions mencampur lifecycle ("Archived") dengan status analisis | `features/sessions/SessionsPage.tsx` (StatusCell) | Ambigu |
| U-15 | LOW | Import mem-prefill nama "Audio-only · Tower" (sama dengan sesi yang sudah ada) sebelum file dipilih. Tombol Mock mengambang menutupi konten kanan bawah | `features/imports/ImportPage.tsx:170`; `app/devtools/MockControlPanel.tsx:77` | Nama duplikat; overlap visual (dev-only) |

Yang sudah baik dan dipertahankan: tiga sumbu readiness di Sessions, evidence drawer yang tidak menggeser replay, pemisahan Said/Heard/Observed, kartu Insufficient context, label eksperimental P1, state degradasi (outage/offline) dari M3.

## 4. Prinsip target

1. **Satu sesi aktif, selalu terlihat.** Sesi dan run menjadi konteks navigasi; pindah sesi atau run hanya lewat aksi eksplisit.
2. **Pisahkan "waktu replay" dan "lensa review".** Workspace adalah alat replay (As-known default di as-of cerita). Review, Debrief, Ask, dan Metrics default ke **seluruh sesi (Debrief lens)**, dengan As-known sebagai lensa opsional yang menyatakan berapa item disembunyikan dan memberi tombol untuk menampilkan semuanya.
3. **Setiap penunjuk adalah pintu.** Item yang disebut sistem (attention, needs checking, notifikasi, palette, chip evidence) membuka item itu sendiri di konteks yang benar.
4. **Loop review dalam satu layar.** Antrean dengan progres, evidence, dan keputusan terlihat bersamaan; simpan lalu lanjut ke item berikutnya.
5. **Viewport adalah anggaran.** Pada desktop, workspace memakai layout aplikasi setinggi viewport dengan scroll per panel, bukan halaman panjang dengan overlay sticky.

## 5. Rencana implementasi

Lima fase berurutan. Setiap fase ditutup dengan check nyata dan update evidence (rules §5.2). Perkiraan ukuran: S < ½ hari, M ½–1 hari, L 1–2 hari.

### Fase UX-1 — Navigasi, konteks sesi, dan lensa (fondasi)

| # | Pekerjaan | Detail | File utama | Ukuran |
| --- | --- | --- | --- | --- |
| 1.1 | Session switcher di sidebar | Blok "Current session" di bawah Sessions: judul, run, label SYNTHETIC; popover berisi daftar sesi terbaru dan link "All sessions". Item sesi dikelompokkan di bawahnya. Tanpa sesi: grup menampilkan "No session open" dan tombol "Choose session" yang membuka popover yang sama | `components/layout/Sidebar.tsx`, baru `components/layout/SessionSwitcher.tsx`, `hooks/useSessionScope.ts` (`lastSession`) | M |
| 1.2 | Ganti `/choose/*` | Halaman pemilih berisi daftar sesi (kartu ringkas + readiness), lalu langsung ke area yang diminta. Hapus dead end | `features/sessions/SessionsPage.tsx:457` | S |
| 1.3 | Model lensa | `mode` default per area: Workspace = As-known di as-of cerita; Review/Debrief/Ask/Metrics = Debrief di akhir sesi. `t` replay dan lensa review disimpan terpisah (`t` untuk replay; review memakai `lens=as-known&t=` hanya bila dipilih). Banner As-known di Review: "Showing what was known at 05:22 · 2 findings and 11 segments became available later · Show full session" | `hooks/useSessionScope.ts`, `features/review/ReviewLayout.tsx`, `features/queries/AskPage.tsx`, `features/debrief/*`, engine `default_as_of_ms` | L |
| 1.4 | Link yang membawa konteks | Semua link antar layar (rail Sessions, menu baris, palette, sidebar, spotlight Debrief) membawa `run` dan lensa yang benar. Helper tunggal `sessionHref(area, {sid, run, lens, t, focus})` | baru `lib/links.ts`; pemakai di Sessions, Sidebar, CommandPalette, DebriefPage, AttentionRail | M |
| 1.5 | Perbaiki command palette | Route objek yang benar; grup Findings (label, judul, callsign) dan Transcript (kutipan) untuk sesi aktif; tidak membuang `run`/lensa; item terakhir dibuka | `components/layout/CommandPalette.tsx` | M |
| 1.6 | Header halaman sesi seragam | Satu komponen `SessionPageHeader`: breadcrumb `Sessions › {session} › {area}`, judul, strip konteks (run, lensa, as-of, label), dan slot aksi kanan. Toggle lensa selalu di posisi yang sama | `features/workspace/SessionPageHeader.tsx`, semua halaman sesi | M |

**Acceptance UX-1:**
- Jumlah temuan di Sessions, Workspace, Review, Debrief, dan Metrics sama untuk lensa yang sama.
- Banner As-known menyebut jumlah item tersembunyi.
- Tidak ada link 404.
- Run/lensa tidak berubah tanpa aksi eksplisit.
- Sesi aktif terlihat di setiap layar sesi.

### Fase UX-2 — Layout Workspace

| # | Pekerjaan | Detail | File utama | Ukuran |
| --- | --- | --- | --- | --- |
| 2.1 | Layout setinggi viewport (≥ xl, tinggi ≥ 720) | Grid: header → [Situation \| Attention] → Memory strips → Timeline. Timeline menjadi baris grid, bukan overlay sticky. Memory dan Attention scroll internal dengan isyarat scroll (fade). Di bawah xl: susunan bertumpuk seperti sekarang, timeline tidak sticky | `features/workspace/WorkspacePage.tsx`, `features/replay/TimelineBand.tsx` | L |
| 2.2 | Timeline ringkas | Mode compact (1 lane gabungan + marker) sebagai default di viewport pendek (varian `short`); tombol expand ke 2 lane | `features/replay/TimelineBand.tsx` | M |
| 2.3 | Memory strip tanpa potongan informasi | Tipe/role pindah ke tooltip/subjudul pendek; alasan NOT_EVALUABLE dibungkus 2 baris dengan `title` + tooltip; kolom "Source age" ringkas | `features/workspace/MemoryStrips.tsx` | S |
| 2.4 | Aksi kartu attention | Klik kartu: pilih objek, sorot range di timeline, tanpa mengubah as-of. Tombol "Listen to evidence" tetap. Tambah "Review" yang membuka Review › Findings dengan item terpilih dan lensa Debrief | `features/workspace/AttentionRail.tsx` | S |
| 2.5 | Cluster status header | "Connected" dan "Cached results" digabung menjadi satu tombol status dengan popover (koneksi, sumber hasil, provider) | `features/workspace/SessionHeader.tsx` | S |

**Acceptance UX-2:**
- Di 1440×900 dan 1280×720, ketiga area (situation, memory, attention) dan timeline terlihat tanpa page scroll, dengan minimal 3 memory strip terlihat.
- Tidak ada teks status yang terpotong tanpa akses ke nilai penuh.

### Fase UX-3 — Loop review

| # | Pekerjaan | Detail | File utama | Ukuran |
| --- | --- | --- | --- | --- |
| 3.1 | Antrean dengan progres | Header antrean "2 of 5 reviewed" + progress bar; filter default "Needs review" (OPEN/UNDER_REVIEW) dengan opsi All; urut priority lalu waktu | `features/review/FindingsPage.tsx` | M |
| 3.2 | Panel keputusan selalu terlihat | Kolom evidence: ringkasan Said/Heard + slot compare di atas; detail (tabs Audio/Event/Track, provenance) dapat dilipat. Form keputusan menjadi panel sticky di bawah kolom kanan | `features/evidence/EvidencePanel.tsx`, `features/evidence/FindingReviewForm.tsx` | M |
| 3.3 | Save & next | Setelah simpan (append-only, jadi tanpa undo), tampilkan tombol "Next finding" yang menonjol dan opsi "Advance after saving" (default off, D-3). Form tetap reset ke kosong | `FindingReviewForm.tsx`, `FindingsPage.tsx`; pola sama di `OptionsPage.tsx` | M |
| 3.4 | Keyboard | `J`/`K` item berikutnya/sebelumnya, `1`/`2`/`3` memilih keputusan (tanpa auto-save), `⌘/Ctrl+Enter` simpan bila valid. Daftar shortcut di Help dan tooltip | Review pages, `features/settings/HelpPage.tsx` | S |
| 3.5 | Cross-link | Finding → "Open in transcript" (segmen terkait) dan "Open object memory"; segmen transcript → finding terkait; chip evidence konsisten | Review pages, `MemoryPage.tsx` | S |
| 3.6 | Transcript inspector | Dua form dipisah menjadi tab "Pairing" dan "Correction" dengan tombol simpan masing-masing selalu terlihat; tabel menandai segmen yang punya revisi atau review | `features/review/TranscriptPage.tsx` | M |
| 3.7 | Penjaga draf | Route blocker + `beforeunload` bila form review/rating/koreksi berisi teks belum disimpan; dialog "Discard draft?" | baru `hooks/useDraftGuard.ts`; tiga form | S |
| 3.8 | Rapikan copy | Satu kalimat "AI findings and source alerts are recorded separately" per layar (di blok Source alert) | `ReviewLayout.tsx:14`, `FindingsPage.tsx:135`, `EvidencePanel.tsx:325` | S |

**Acceptance UX-3:**
- Mereview 5 temuan bisa dilakukan tanpa mouse dan tanpa page scroll di 1440×900.
- Progres terlihat dan akurat.
- Draf tidak hilang tanpa konfirmasi.
- Form tetap awal kosong dengan reason wajib.

### Fase UX-4 — Debrief, Sessions, Import

| # | Pekerjaan | Detail | File utama | Ukuran |
| --- | --- | --- | --- | --- |
| 4.1 | Layout Debrief dua kolom | Kiri (lebar): Session summary. Kanan: Journal dengan fade + jumlah item tersisa. Export pindah ke sheet dari tombol header "Export report" (D-4) | `features/debrief/DebriefPage.tsx`, `ExportPanel.tsx` | M |
| 4.2 | Status review di Debrief | Bagian "Review status" menampilkan progres dan link "Continue reviewing" ke item belum direview | `DebriefPage.tsx` | S |
| 4.3 | Sessions: aksi baris | Klik judul atau Enter membuka workspace; klik area lain memilih (rail); tombol "Open" terlihat saat hover/fokus. Pisahkan kolom Lifecycle dari Analysis (atau badge Archived di judul) | `features/sessions/SessionsPage.tsx` | S |
| 4.4 | Lanjutkan pekerjaan | Kartu "Continue" di atas tabel: sesi terakhir, area terakhir, progres review | `SessionsPage.tsx`, `hooks/useSessionScope.ts` | S |
| 4.5 | Deep link | "Needs checking" dan notifikasi membuka item spesifik (finding/import/export) dengan lensa yang benar | `SessionsPage.tsx:441`, `NotificationsPopover.tsx`, engine notifikasi `href` | S |
| 4.6 | Import | Nama sesi kosong dengan placeholder; diturunkan dari file pertama bila kosong; validasi duplikat nama | `features/imports/ImportPage.tsx:170` | S |

**Acceptance UX-4:**
- Ringkasan Debrief menjadi area utama yang terbaca tanpa teks pecah per 3 kata.
- Semua penunjuk membuka item yang disebut.

### Fase UX-5 — State, polish, dan QA

| # | Pekerjaan | Detail | Ukuran |
| --- | --- | --- | --- |
| 5.1 | Isyarat scroll | Komponen `ScrollArea` dengan fade atas/bawah untuk journal, transcript, memory, attention | S |
| 5.2 | Panel Mock | Pindahkan pemicu ke footer sidebar (dev only) agar tidak menutupi konten; tetap berlabel MOCK | S |
| 5.3 | Pengujian | Update journeys Playwright (lensa, palette, save & next, draft guard, deep link); Vitest untuk `sessionHref` dan model lensa; axe per route; screenshot 1440×900, 1280×720, 1024×768, 390×844; sweep console dan overflow | M |
| 5.4 | Dokumen | Update skrip demo (alur baru), evidence, handoff, Help (shortcut) | S |

## 6. Keputusan pengguna (9 Oktober 2026)

| # | Keputusan | Pilihan |
| --- | --- | --- |
| D-1 | Lensa default Review/Ask/Metrics | **Seluruh sesi (Debrief)**; As-known opsional dengan banner jumlah item tersembunyi |
| D-2 | Workspace desktop | **Layout setinggi viewport** untuk ≥ xl dan tinggi ≥ 720 (scroll per panel, timeline sebagai baris grid); bertumpuk di bawahnya |
| D-3 | Setelah menyimpan review | **Tetap di item** dengan tombol "Next finding" yang menonjol; preferensi "Advance after saving" default off |
| D-4 | Export di Debrief | **Sheet** dari tombol header "Export report" |

## 7. Risiko

| Risiko | Mitigasi |
| --- | --- |
| Perubahan lensa menyentuh semua query (`queryKeys` memuat mode/as-of) | Helper tunggal di `useSessionScope`; unit test untuk setiap area; journeys As-known vs Debrief diperluas |
| Layout setinggi viewport mempersulit zoom 200 % | Hanya aktif di ≥ xl dan tinggi ≥ 720; di bawahnya kembali bertumpuk (sudah diuji tanpa overflow) |
| Shortcut keyboard bentrok dengan input teks dan replay (Space, panah) | Shortcut aktif hanya saat fokus tidak berada di field teks; tidak memakai Space/panah di Review |
| Regresi guardrail (as-known bocor, review terisi otomatis) | Journeys yang ada tetap wajib lulus; tambahkan assertion "form kosong setelah Next" |

## 8. Status implementasi (9 Oktober 2026)

Semua fase UX-1 s.d. UX-5 diimplementasikan di working tree `feat/fe-init` (belum commit), ditambah pass desain/kepadatan atas permintaan pengguna.

| Fase | Hasil |
| --- | --- |
| UX-1 | `lib/links.ts` (`sessionHref`, `lensAreaOf`, `areaFromPath`, `scopeFromParams`); lensa D-1 di `useSessionScope`; `SessionPageHeader` bersama; switcher sesi di sidebar; command palette dengan grup Findings/Objects/Transcript (404 memory diperbaiki); picker `/choose/:area` |
| UX-2 | Workspace setinggi viewport (varian `fit`), strip memory sebagai baris grid, timeline compact/expand, popover status koneksi |
| UX-3 | Filter Needs review + progres, J/K, 1/2/3, ⌘↵, tetap di item + Next (D-3), draft guard, cross-link transcript/memory, tab Correction/Pairing |
| UX-4 | Debrief dua kolom + Review status + export sheet (D-4); Sessions: judul membuka workspace, badge Archived terpisah, kartu Continue, deep link Needs checking dan notifikasi; Import: nama kosong dengan saran dari nama file dan validasi nama duplikat |
| UX-5 | `ScrollArea` dengan fade; panel Mock pindah ke footer sidebar; Vitest `links.test.ts`; test Debrief membuka sheet + axe pada sheet; dokumen ini, skrip demo, evidence dan handoff |
| Pass desain | Findings setinggi viewport (kolom scroll sendiri, form keputusan di bawah evidence, tidak lagi menutupi quote); header/tab lebih ringkas pada tinggi ≤ 820; tabel Sessions tanpa kolom Source (chip pindah ke baris konteks) dan tanggal tidak terpotong; strip KPI lebih rendah; grafik Metrics diskalakan ke data; journal Debrief memakai tinggi viewport; dropzone Import ringkas setelah ada file |

Deviasi yang diketahui: pada 1280×720 Workspace menampilkan 2 strip memory + isyarat scroll (target 3). Pada 1440×900 area quote di kolom evidence Findings sekitar 150 px karena form keputusan disematkan; pada tinggi ≤ 820 seluruh kolom evidence di-scroll sebagai satu kesatuan.
