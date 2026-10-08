# Rencana Implementasi Frontend ATC FlowLens (MOCK track)

| Atribut | Nilai |
| --- | --- |
| Tanggal | 8 Oktober 2026 |
| Status dokumen | **Diimplementasikan sebagai MOCK track** (Milestone 1–3) — evidence dan batasan: [frontend MOCK evidence](../testing/frontend-mock-evidence.md); G-FE tetap `blocked`. QA M3 (9 Okt) dan panduan pengembang: [frontend MOCK](frontend-mock.md) |
| Branch kerja | `feat/fe-init` |
| Scope | Seluruh frontend v1 (P0 + P1 yang disetujui) dengan **mock data**, berjalan hanya di stack frontend |
| Acuan visual | Tiga screenshot Margin (Overview, Job detail, Forecast) + [paket desain 8 halaman](../design/2026-10-08-flowlens/README.md) dan [tokens.json](../design/2026-10-08-flowlens/tokens.json) |
| Acuan kontrak | [PRD](../../.agent/PRD.md) §5, §7, §11–§24, §35; [contracts/json-schema/public](../../contracts/json-schema/public) (contract 1.0.0) |
| Label data | Semua data `SYNTHETIC` + `MOCK`; `model_version: "MOCK"`; `NOT_DOMAIN_VALIDATED` |

---

## 1. Keputusan yang dikunci untuk rencana ini

Keputusan berikut berasal dari instruksi eksplisit pengguna pada 8 Oktober 2026. Instruksi pengguna berlaku di atas aturan proyek ([rules](../../.agent/rules.md) §0), tetapi deviasinya dicatat agar tidak hilang.

| # | Keputusan | Deviasi dari dokumen aktif | Tindak lanjut |
| --- | --- | --- | --- |
| D-1 | Frontend dibangun sekarang **tanpa menunggu G-BE**; Phase 11–13 ditandai `in_progress` | Roadmap §1/§7 dan rules §4.3 mewajibkan G-BE dulu | Update roadmap + handoff saat M1 dimulai. **G-FE tetap `blocked`** sampai integrasi backend nyata; Phase 14 hanya dapat menjalankan journeys MOCK |
| D-2 | Seluruh data dari **mock adapter in-process**, tanpa backend/provider call | PRD §25.5: mocks tidak menggantikan full-stack | Mock adapter berada di belakang port `ApiClient` agar dapat diganti `HttpApiClient` tanpa mengubah screens |
| D-3 | Audio **visual-only**: clock replay, waveform, playhead dan range bergerak, **tanpa output suara** | PRD §12.2 menargetkan audio nyata | Tidak ada file audio di bundle/`public/` (sesuai rules §4.3). Kontrol audio diberi label "Visual replay · audio not loaded (MOCK)" |
| D-4 | Scope tambahan: **Login + Settings/admin**, **Contextual query (P1, FR-14)**, **Communication metrics (P1, FR-15)**, **Role switcher demo** | P1 tidak wajib untuk P0 | P1 diberi badge `P1 · Experimental`; metrics diberi disclaimer "not a workload diagnosis" |
| D-5 | UI **English**, **light theme** saja, desain mengikuti referensi dengan perhatian detail | PRD §5.3 menetapkan UI Bahasa Indonesia; comps berbahasa Indonesia | Update PRD §5.3/§23.2 (contoh copy) pada M1 task 0. Token tetap disusun agar dark mode dapat ditambahkan nanti |

Yang **tidak** berubah: batas kewenangan (tidak ada execute/send clearance), Said–Heard–Observed terpisah, evidence wajib, unknown sebagai hasil sah, review append-only, isolasi truth evaluator, dan label SYNTHETIC/MOCK yang selalu terlihat.

---

## 2. Analisis konteks — invariant produk yang wajib ditegakkan UI

Bagian ini menerjemahkan PRD dan design README menjadi aturan UI yang dapat diuji. Setiap screen di §6 merujuk kode guardrail ini.

| Kode | Invariant | Bentuk di UI | Sumber |
| --- | --- | --- | --- |
| G-01 | Replay offline, bukan operasi aktif | Tidak ada kata/indikator "LIVE", connect radio, microphone. Chip tetap "Replay offline" | PRD §3.3, §12.1 |
| G-02 | Tidak ada jalur clearance/command | Tidak ada tombol Execute/Send/Apply pada opsi. Copy-guard test memindai kata terlarang | FR-11, AC-11 |
| G-03 | Said / Heard / Observed terpisah | Tiga baris independen; tidak ada progress linear `SAID→HEARD→DONE` | PRD §16.1 |
| G-04 | Lima dimensi state memory independen | Interpretation, Instruction, Readback, Movement, Reviewer ditampilkan sebagai kolom/badge terpisah | PRD §16.1 |
| G-05 | Unknown adalah hasil sah | `NOT_EVALUABLE`, `AMBIGUOUS`, `MISSING` selalu dengan alasan; tidak pernah hijau | PRD §10, §17.1 |
| G-06 | Ketiadaan finding ≠ aman | Empty state: "No findings at this as-of. This does not mean the runway is clear." | PRD §23.2 |
| G-07 | As-known vs Debrief | Mode tampil di header; AS_KNOWN hanya menampilkan item dengan `available_time_ms ≤ asOf`. Penyaringan dilakukan di mock "server", bukan di komponen | PRD §12.3 |
| G-08 | Evidence dapat dibuka dari setiap klaim | Setiap finding/option/brief item/memory row punya `EvidenceChip`; drawer tidak mereset clock | FR-10, AC-10/13 |
| G-09 | Raw STT immutable | Hipotesis STT asli read-only; koreksi pada field terpisah dengan reason → revision baru; dependents ditandai stale | FR-12, AC-03/12 |
| G-10 | Review append-only, mulai kosong, alasan wajib | Radio awal `null`; Save disabled dengan alasan tertulis; menampilkan revision + "Append-only" | PRD §17.3, tokens.rules |
| G-11 | Acknowledgment ≠ konfirmasi | Footnote "Acknowledgment does not confirm a finding." | PRD §17.3 |
| G-12 | Tiga sumbu readiness | `SOURCE_READY`, `ANALYSIS_READY`, `DOMAIN_REVIEWED` tidak digabung menjadi satu indikator hijau | PRD §12.1 |
| G-13 | Permission ≠ UI hiding | Access denied ditampilkan sebagai state eksplisit (bukan empty). Mock adapter mengembalikan `ACCESS_DENIED` seperti server | FR-16, AC-14 |
| G-14 | Status tidak hanya warna | Icon + teks + (bila perlu) pola hatch; legend observed solid / predicted dashed / missing | PRD §23.4 |
| G-15 | Tidak ada autoplay, tidak ada siren/auto-focus | Playback hanya oleh user; attention rail tidak merebut fokus | PRD §17.3, §23.4 |
| G-16 | Provider outage tidak memalsukan hasil | Cached results tetap terbaca; analisis/brief/opsi baru berstatus unavailable | FR-17, AC-15 |
| G-17 | Connection lost membatasi mutation | Banner "Reconnecting…/Resyncing", semua review mutation disabled sampai resync | PRD §22.3 |
| G-18 | Opsi = alternatif hipotesis | Evaluation question, preconditions, unknowns, tradeoffs "Hypothesis", applicability `LAB_ONLY`; nol opsi valid (`INSUFFICIENT_CONTEXT`) | FR-11 |
| G-19 | Label data selalu terlihat | `SYNTHETIC`, `MOCK DATA`, `Replay offline`, `Not domain reviewed` di header konteks | Rules §4.3, §9 |
| G-20 | Tidak ada secret/path privat di browser | Settings hanya metadata provider (tanpa key); tidak ada filesystem path | PRD §27.4 |

---

## 3. Arah desain — adaptasi referensi Margin ke FlowLens

### 3.1 Apa yang diambil dari referensi

| Elemen Margin | Pengamatan detail | Adaptasi FlowLens |
| --- | --- | --- |
| Shell | Canvas abu sangat terang; sidebar menyatu dengan canvas (tanpa border); konten di kartu putih | Sama. Sidebar 224 px, collapse ke rail 72 px (tombol panel di kanan logo) |
| Nav aktif | Pill charcoal `#2B2D31`, teks putih, radius 12, bayangan lembut di bawah | Sama, untuk Sessions/Workspace/Review/Debrief |
| Group label "Analyze" | Caption abu kecil di atas grup kedua | Grup "Analyze": Memory, Metrics (P1), Ask (P1) |
| Bottom nav | Notifications (badge oranye bulat), Settings, Help, kartu user (avatar + nama + "Owner · …" + `…`) | Notifications (badge jumlah job/export/review), Settings, Help, kartu user "Name · Evaluator · Research workspace" + menu role switcher |
| Search | Input putih radius 12, ikon search, chip `⌘K` | Command palette (cmdk): sessions, entities (FLN214), findings, evidence refs, routes |
| Judul halaman | Sangat besar (~42–44 px), weight 500, tracking rapat | `Sessions`, `Workspace`, `Review`, `Debrief`, `Settings`; context subtitle di bawahnya |
| Header controls | Pill putih dengan ikon (date range, branch, Export); segmented dengan track abu dan pill putih aktif | Segmented `As-known / Debrief`, run selector pill, as-of clock pill, connection pill, "Cached results" pill |
| Kartu | Radius ~24, padding lega, hairline, bayangan hampir tak terlihat; tombol `…` lingkaran bergaris | Sama (token `card`, `more-button`) |
| KPI besar | Angka 72–80 px, weight 500, tracking -0.04em; delta pill putih dengan segitiga berwarna | Hanya di tempat yang bermakna: Debrief metrics (P1), Sessions KPI strip versi kecil. Tidak membuat "dashboard penuh chart" (PRD §23.1) |
| Hatched bars | Garis diagonal untuk estimate/planned/target; solid untuk actual; pink-hatched untuk loss | **Bahasa visual inti**: hatched biru = predicted/expected, solid biru = observed/actual, pink-hatched = discrepancy, abu-hatched = gap/NOT_EVALUABLE/missing coverage |
| Waterfall "Why it is under target" | Bar bertingkat dengan connector putus-putus, label kanan `-1.6 pts · $7.7K` | Debrief "Where attention came from": breakdown findings per kategori (count + entities), bukan skor keselamatan |
| Bar chart 12 minggu + tooltip pill | Bar hatched, bar terakhir solid, garis target putus-putus, tooltip pill putih | Metrics P1: occupied audio time per menit replay; bar as-of solid; garis referensi = rule profile (berlabel LAB_RULE) |
| "Estimate vs actual" rows | Label + sub-label, dua bar bertumpuk (hatched estimate, solid actual, pink overrun), `$640 → $1,060  +$420` | **Slot comparison** di Evidence/Finding: Callsign, Runway, Action, Condition, Negation — `Said "two seven" → Heard "zero nine"  Mismatch`; `On plan` → `Matched` |
| Result card + slider dua titik | Nilai besar, delta pill, slider dengan marker actual/estimated | Finding context: **Event time vs Available time** pada mini-track replay (marker event 05:19, available 05:22, as-of 05:22) |
| "Where the $860 went" | List bar pink proporsional | Memory: "What is still open" per kategori open loop |
| "What happened" timeline horizontal | Dot berwarna (biru normal, pink loss) + tanggal + judul + deskripsi | Object memory "What happened": Instruction → Readback candidate → Discrepancy → Correction → Review |
| "Margin noticed" callout | Kartu amber pucat, ikon sparkle, teks + tombol putih | `Coverage notice` / `Source quality gap` callout dengan tombol "View validation details" |
| "Pattern found" gradient card | Mesh gradient biru→peach, angka besar putih, CTA putih | Dipakai **satu kali** di Debrief sebagai "Key item to review" (evidence-linked, label `AI interpretation · MOCK`, CTA "Review finding"). Tidak dipakai sebagai promosi (design README) |
| Forecast toggle cards | Kartu dengan ikon tile, toggle, angka hijau, progress hatched | **Tidak** dipakai untuk opsi (opsi bukan intervention tiles). Pola toggle-card dipakai di Export options dan Settings provider profiles |
| Breadcrumb + status pill | `Jobs > #5819`, pill "• At risk" | `Workspace / Memory`, pill `• Not evaluable`, `• Mismatch` |
| "Needs you" list | Ikon dalam lingkaran tinted, judul + sub, chevron | Sessions "Needs checking" rail dan Workspace attention items |

### 3.2 Token desain final (perluasan tokens.json)

Token disimpan sebagai CSS variables di `frontend/src/styles/tokens.css` dan dipetakan ke Tailwind v4 `@theme`. Nilai berasal dari tokens.json; tambahan ditandai **(+)**.

| Token | Nilai | Pemakaian |
| --- | --- | --- |
| `--canvas` | `#F5F6F7` | Background aplikasi + sidebar |
| `--canvas-outer` (+) | `#ECEDEF` | Bingkai luar pada layar ≥1600 px (app perimeter radius 28, opsional) |
| `--surface` | `#FFFFFF` | Kartu, drawer, input |
| `--surface-sunken` (+) | `#F7F8F9` | Inner group/quote block di dalam kartu |
| `--text` / `--text-secondary` / `--text-tertiary` (+) | `#191B20` / `#616975` / `#8A919C` | Tertiary hanya untuk teks ≥14 px non-esensial; dicek kontrasnya |
| `--hairline` / `--control-boundary` | `#E4E7EB` / `#7E8999` | Divider; batas input |
| `--action` / `--on-action` | `#303237` / `#FFFFFF` | Nav aktif, satu primary button per konteks |
| `--data` / `--data-tint` | `#2563EB` / `#EAF1FF` | Selection, evidence link, observed, waveform aktif |
| `--discrepancy` / tint | `#B82B69` / `#FCEAF2` | Mismatch, ATTENTION |
| `--notice` / tint | `#96610B` / `#FFF4DE` | NOTICE, UNDETERMINED, gap |
| `--ready` / tint | `#167B46` / `#EAF7EF` | Source ready / ALLOWED saja |
| `--muted` / tint | `#596273` / `#EEF0F3` | NOT_EVALUABLE, archived, unavailable |
| `--badge` (+) | `#EA6A1F` | Badge jumlah notifikasi (seperti Margin) |
| `--focus` | `#2563EB` | Focus ring 2 px + offset 2 px |
| `--hatch-*` (+) | `repeating-linear-gradient(135deg, color 0 2px, transparent 2px 5px)` | Varian data/discrepancy/muted |
| `--shadow-card` | `0 2px 8px rgba(25,27,32,.025)` + hairline | Kartu |
| `--shadow-pop` (+) | `0 8px 24px rgba(25,27,32,.08)` | Popover, tooltip pill, delta pill |
| `--shadow-action` | `0 4px 10px rgba(25,27,32,.12)` | Nav aktif, primary button |
| Radius | card 24 · drawer 24 · input/button 12 · pill 999 · tile 12 | |
| Motion | hover 140 ms · sheet 200 ms · `prefers-reduced-motion` mematikan transisi non-esensial | |

**Tipografi:** Inter Variable (via `@fontsource-variable/inter`, self-hosted; tidak memuat Google Fonts saat runtime) dengan `font-feature-settings: "cv11", "ss01"`; `tabular-nums` untuk semua waktu/angka. Skala: page title 42/1.1/500/-0.035em (32 px pada <1280); KPI display 72/1/500/-0.04em; section 21/1.3/600; body 16/1.5; table 14/1.45; caption 13/1.45; quote 17/1.5. Callsign dan quote tidak pernah di-ellipsis (wrap).

**Grid:** baseline 1440×900; main padding 28; gutter 20; card padding 24; control height 44 (compact 36 untuk table toolbar); icon 18–20 stroke 1.75 (lucide).

### 3.3 Detail mikro yang dijaga (checklist "attention to detail")

- Bayangan hanya pada kartu, popover dan elemen aktif; tidak pada setiap inner group.
- Satu primary (charcoal) button per konteks; aksi lain tonal/outline.
- Disabled control selalu disertai alasan yang terlihat (bukan hanya opacity) — misalnya "Choose a decision and write a reason before saving."
- Chip evidence (`E-12`, `F-03`) memakai ikon jenis (waveform untuk audio, dokumen untuk event/finding) dan dapat difokus keyboard.
- Quote kritis memakai highlight slot: biru untuk instruksi, pink untuk mismatch, dengan `<mark>` + teks status untuk screen reader.
- Angka waktu: offset replay `05:22.0` (tabular), wall-clock hanya dengan zona waktu eksplisit "8 Oct 2026, 14:20:00 UTC".
- Hairline row divider tidak sampai tepi kartu (inset 24) seperti Margin.
- Tooltip chart berupa pill putih dengan `--shadow-pop`.
- Hover state: background `--surface-sunken`; selected row: `--data-tint` + left rule 3 px biru.
- Focus ring konsisten di semua kontrol, termasuk chip, tab, segmented, radio, slider handle.
- Empty/error/partial states memakai ilustrasi ikon tile 40 px + judul + penjelasan + satu aksi.

---

## 4. Arsitektur frontend

### 4.1 Stack

| Lapisan | Pilihan | Catatan |
| --- | --- | --- |
| Build | Vite + React + TypeScript (strict) | Package manager **npm** + `frontend/package-lock.json` (rules §4.3). Versi di-resolve saat install dan dikunci oleh lockfile; tidak mengarang pin |
| Styling | Tailwind CSS v4 (`@tailwindcss/vite`) + CSS variables tokens | Tanpa style ad hoc untuk state kualitas — semua via komponen domain |
| Komponen | shadcn/ui (Radix) — Button, Card, Badge, Tabs, Table, Sheet, Dialog, Tooltip, Command, Form, Select, Progress, Toast (sonner), RadioGroup, Switch, Popover, DropdownMenu, ScrollArea, Separator, Skeleton, Slider, ToggleGroup, Breadcrumb, Avatar, Chart | Di-restyle sesuai token |
| Ikon | lucide-react | Outline, stroke konsisten |
| Routing | React Router (data router) | URL menyimpan session, run, mode, as-of, selected item, evidence |
| Server cache | TanStack Query | Query keys scoped session/run/revision/as-of (rules §4.6) |
| State lokal | Zustand (replay clock, UI prefs, mock control) | Tidak menyimpan data server |
| Form | react-hook-form + zod | Validasi reason/decision; error inline |
| List panjang | @tanstack/react-virtual | Transcript, audit log |
| Chart P1 | shadcn Chart (Recharts) dengan SVG pattern hatch | Waveform, timeline, situation canvas tetap custom SVG |
| Type kontrak | `json-schema-to-typescript` dari `contracts/json-schema/public` → `src/api/generated/` | Script `gen:types` + `check:types` (drift) |
| Test | Vitest + Testing Library + vitest-axe (unit/component); **Python Playwright** untuk journeys (rules §4.2) | Playwright memerlukan `uv add --dev pytest-playwright` → perubahan `pyproject.toml`/`uv.lock` dicatat |

### 4.2 Boundary data — port, adapter, dan mock "server"

```text
Screens/features ──► hooks (useSessionQuery, useFindings…) ──► ApiClient (port, typed)
                                                              ├─► MockApiClient  (sekarang)
                                                              └─► HttpApiClient  (setelah G-BE; stub)
StreamClient (port) ──► MockStream (sequence, snapshot, resync, disconnect injection)
```

- **`ApiClient`** (`src/api/client.ts`) mencerminkan endpoint PRD §22.2 (sessions, imports, sources, analysis-runs, jobs, snapshot, playback, transcripts, corrections, memory, associations, findings, options, reviews, briefs, queries, evidence, exports, archive, admin users/grants/provider-profiles/audit, auth). Signature memakai type generated (snake_case wire) dan `ApiError` bertipe dengan kode PRD §22.3.
- **`MockApiClient`** (`src/api/adapters/mock/`) mensimulasikan **perilaku server**: as-of filtering, authorization per grant/role, idempotency key store, `expectedVersion` conflicts, append-only reviews, stale marking setelah correction, job progress, export lifecycle, error injection. Logika ini sengaja diisolasi di adapter (bukan di komponen) agar tidak menjadi "business rule di browser" ketika backend nyata masuk (roadmap §1).
- **Latency** acak 120–450 ms (konfigurabel) agar loading/skeleton states benar-benar teruji.
- **Field non-kontrak** (mis. label pendek `E-12`, nama tampilan) disimpan di `display` map adapter; screen tidak boleh bergantung pada field yang tidak ada di kontrak tanpa fallback. Gap kontrak dicatat di §9.
- **Persistensi mock:** state in-memory per tab; reset via Mock Control. Tidak memakai localStorage untuk data domain (hanya preferensi UI seperti sidebar collapsed).

### 4.3 Query keys dan URL state

```ts
qk.session(sessionId)
qk.run(sessionId, runId)
qk.snapshot(sessionId, runId, revision, mode, asOfBucket)   // bucket 100 ms
qk.findings(sessionId, runId, revision, mode, asOfBucket, filters)
qk.transcript(sessionId, runId, revision)
qk.evidence(sessionId, runId, evidenceId)
```

URL: `/s/:sessionId/workspace?run=<id>&mode=as_known&t=322000&entity=<id>&evidence=<id>`. Ganti role/akun → `queryClient.clear()` (Phase 11 acceptance). Tidak ada token/secret di URL.

### 4.4 Peta route

| Route | Screen | Comp |
| --- | --- | --- |
| `/login` | Login | baru |
| `/sessions` | Session catalogue + detail rail (`?selected=`) | 01 |
| `/sessions/import` | Import wizard (`?step=source|preview|analysis`) | 02 |
| `/s/:sid/workspace` | Replay workspace | 03 |
| `/s/:sid/memory/object/:entityId` · `/s/:sid/memory/runway/:runwayId` | Operational memory | 04 |
| `/s/:sid/review/transcript` | Transcript & association | 05 |
| `/s/:sid/review/findings/:findingId?` | Findings & evidence | 06 |
| `/s/:sid/review/options/:optionId?` | Candidate options | 07 |
| `/s/:sid/debrief` | Journal, brief, export, metrics tab (P1) | 08 |
| `/s/:sid/ask` | Contextual query (P1) | baru |
| `/settings/{users,grants,providers,jobs,storage,audit,retention}` | Admin/operator | baru |
| `/help` | Help & legend (status, pola, glossary) | baru |
| `*` | Not found / error boundary | baru |

Nav "Workspace/Review/Debrief" tanpa sesi terpilih → sesi terakhir yang dibuka; jika tidak ada → empty state "Choose a session" dengan link ke catalogue. Evidence drawer dikendalikan `?evidence=` sehingga tetap di posisi replay dan fokus kembali ke trigger saat ditutup.

### 4.5 Struktur folder (mengisi scaffold yang ada)

```text
frontend/
├── index.html · package.json · package-lock.json · vite.config.ts · tsconfig*.json · components.json · eslint.config.js
├── src/
│   ├── app/            main.tsx, App.tsx, providers/ (Query, Router, Toaster, Tooltip), routing/ (routes, guards, errorBoundary)
│   ├── api/            client.ts, errors.ts, queryKeys.ts, stream.ts, generated/ (json-schema types)
│   │   └── adapters/   mock/ (db.ts, engine/, seed/, scenarios.ts, latency.ts, stream.ts) · http/ (stub)
│   ├── components/
│   │   ├── ui/         shadcn (restyled)
│   │   ├── layout/     AppShell, Sidebar, PageHeader, ContextHeader, CommandPalette, NotificationsPopover, UserMenu, MockControlPanel
│   │   └── domain/     StatusBadge, QualityBadge, ReadinessAxis, EvidenceChip, QuoteBlock, SlotComparison, HatchedBar,
│   │                   DeltaPill, IconTile, KpiStrip, SegmentedControl, Waveform, TimelineBand, SituationCanvas,
│   │                   MemoryStrip, StateDimensionRow, OpenLoopItem, FindingCard, CalloutCard, SpotlightCard,
│   │                   EmptyState, ErrorState, AccessDenied, StaleBanner, ConnectionBanner, DataLabels
│   ├── features/       auth, sessions, imports, replay, memory, transcripts, findings, advisory, evidence,
│   │                   review, debrief, queries, settings (+ metrics di debrief)
│   ├── hooks/ · lib/ (time format, cn, keyboard, a11y announce) · styles/ (tokens.css, globals.css) · types/
└── tests/              unit/, components/
tests/e2e/frontend_mock/  (Python Playwright journeys MOCK)
```

---

## 5. Dataset mock (SYNTHETIC)

Seed disusun di `src/api/adapters/mock/seed/` sebagai TypeScript yang **memenuhi type generated** (snake_case, UUID, `source_hash` 64-hex, `model_version: "MOCK"`). Layout memakai geometri `tests/fixtures/layouts/fictional-runway.json` (FICTIONAL_LOCAL_XY, meter) yang diperluas dengan taxiway A/B sebagai data dekoratif berlabel. Generated examples **bukan** gold evaluation labels.

| Sesi | Status | Cerita yang dibuktikan | State khusus |
| --- | --- | --- | --- |
| S1 Runway 27 · Readback (18:40) | COMPLETED, Run #03 rev 2 (+ Run #02 rev 1) | **E2E-01**, **E2E-05**; comps 03–08 | FLN214 centre-point tanpa footprint → NOT_EVALUABLE; FLN402 consistent; VEH03 track missing; audio gap 13:20–14:05; correction E-14 05:24; brief rev 1 stale + rev 2 |
| S2 Hold short · Vehicle (12:15) | COMPLETED | **E2E-03** | Readback MATCHED, footprint lengkap → DIVERGENCE_CANDIDATE dengan evidence geometri; toggle "stale track" → NOT_EVALUABLE |
| S3 Report clear · Open loop (21:08) | COMPLETED | **E2E-02** | Loop REPORT_EXPECTED tetap OPEN meski objek lain bicara; coverage gap → uncertainty, bukan "pilot ignored" |
| S4 Audio-only · Tower (14:30) | PARTIAL | **E2E-04** | STT sukses, Gemini unavailable; tanpa track/layout; situation diganti object/runway context + coverage; opsi/brief baru unavailable |
| S5 Callsign ambiguity (09:22) | COMPLETED | AC-05 | Interleaved FLN214/FLN241, shortened callsign, correction salah target; associations AMBIGUOUS dengan alternatives |
| S6 Provider outage (16:05) | ARCHIVED | AC-15 | Read-only, cached replay, analisis baru diblokir |
| S7 Draft import (14:30) | SOURCE_READY, belum dianalisis | AC-01 | Cloud audio UNDETERMINED → "Start analysis" disabled; track missing nonblocking |

Entitas lain: users (Evaluator, Controller-review, Observer, Admin, Truth-grant evaluator), grants per sesi, provider profiles (Google STT `chirp_3` candidate · Gemini `gemini-3.8-flash` — status "Not verified", tanpa key), jobs (succeeded/failed/retry_wait), budget, disk usage (62%; skenario 84%/91%), audit log ~120 entri, exports (ready/expired/revoked), notifications.

**Mock Control Panel** (dev-only, tombol mengambang berlabel `MOCK`, juga di user menu): role switcher; skenario `provider_outage`, `connection_lost`, `resync_required`, `version_conflict` (review berikutnya), `access_denied_audio`, `empty_catalogue`, `disk_high_water`, `session_expired`; latency slider; reset data.

---

## 6. Milestones

Setiap milestone diakhiri dengan checks yang benar-benar dijalankan dan dicatat (rules §5.2). Tidak ada status `done` tanpa evidence.

### Milestone 1 — Foundation, design system, shell, data layer, Sessions & Import

**Cakupan roadmap:** Phase 11.1–11.4 (versi MOCK) + 12.1. **Hasil:** aplikasi dapat dijalankan (`npm run dev`), shell lengkap, login + role, catalogue dan import wizard end-to-end dengan mock.

| # | Pekerjaan | Detail |
| --- | --- | --- |
| 1.0 | Administrasi | Update `implementationPhases.md` (Phase 11–13 `in_progress`, catatan D-1…D-5, G-FE `blocked`), handoff, PRD §5.3/§23.2 (UI English) |
| 1.1 | Scaffold | Vite React TS strict, path alias `@/`, ESLint + typescript-eslint, Prettier, Tailwind v4, `shadcn init`, Inter self-hosted, scripts `dev/build/typecheck/preview/lint/test/gen:types/check:types/check:copy` |
| 1.2 | Tokens & primitives | `tokens.css`, `@theme` mapping, restyle shadcn (Button varian primary/tonal/outline/ghost, Card, Badge, Tabs underline + segmented, Input dengan ⌘K chip, Table, Sheet 24 radius, Tooltip pill) |
| 1.3 | Komponen domain dasar | StatusBadge (semua enum kontrak → icon+label+tone), QualityBadge, ReadinessAxis, DataLabels (`SYNTHETIC`, `MOCK DATA`, `Replay offline`, `Not domain reviewed`), EvidenceChip, IconTile, DeltaPill, HatchedBar, KpiStrip, CalloutCard, EmptyState/ErrorState/AccessDenied/StaleBanner/ConnectionBanner, Skeletons |
| 1.4 | App shell | Sidebar (logo FlowLens SVG, collapse 224↔72 dengan tooltip, nav groups, Notifications badge, Settings, Help, user card + menu), PageHeader, ContextHeader (session · run · mode · as-of · connection · cached), CommandPalette (⌘K), skip link, error boundary per route |
| 1.5 | Data layer | Generated types, `ApiClient` port, `ApiError` (kode PRD §22.3 + recovery hint), `MockApiClient` + seed S1–S7, query keys, mutation helper (Idempotency-Key + expectedVersion), `MockStream` (sequence, snapshot, resync), cache clear saat ganti role |
| 1.6 | Auth & guards | Login (email/password mock, error "Invalid credentials", rate-limit message, session expired → re-login dengan pesan "Committed reviews are kept"), capability-aware guards, role switcher |
| 1.7 | Sessions catalogue (comp 01) | KPI strip 4 item (Total, Source ready, Partial analysis, Not domain reviewed), tabs All/Active/Archived dengan count, search + status filter, table (Session, Source, Duration, Analysis, Updated ↓, `…` menu), selected row (tint + left rule), detail rail (3 readiness axes, channels, track & layout, run · revision, open findings, "Open workspace" primary, mini layout preview berlabel "Illustrative data · fictional layout"), "Needs checking" rail. States: empty, access denied, partial, archived read-only |
| 1.8 | Import wizard (comp 02) | Stepper 3 langkah. **Source:** dropzone + file picker (WAV/FLAC/JSON/JSONL/CSV), source kind. **Preview & permissions:** file inventory (type chip dari validasi, channels, decoded duration, mini waveform/layout thumb, checksum), strip clock/offset/layout/checksum, disclosure metadata lanjutan (timezone, uncertainty, units, identity mapping, retention), permission matrix 6 baris (local read, cloud audio, cloud transcript/context, reviewer access, report export, audio export) dengan ALLOWED/DENIED/UNDETERMINED (icon+label+penjelasan), remediation errors (file/field/row/kode + "Fix manifest"), readiness rail (Source ready / Analysis blocked / Domain review not done, callout "Track not available"), analysis profile card ("Not verified"), Save session (enabled) & Start analysis (disabled + alasan). **Analysis:** estimasi volume request, konfirmasi eksplisit, progress job via stream, hasil PARTIAL/FAILED |
| 1.9 | Notifications & Help | Popover notifikasi (job selesai, export ready/expired, review conflict); Help: legend status, pola hatch, glossary Said/Heard/Observed |

**Acceptance M1:**
- `npm run typecheck`, `npm run build`, `npm run lint`, `npm run test` lulus; `check:types` tidak ada drift terhadap contracts 1.0.0.
- Ganti role membersihkan cache; observer tidak melihat tombol import dan mendapat `AccessDenied` (bukan empty) saat membuka route terlarang langsung via URL.
- Tiga readiness axes tidak pernah digabung; label SYNTHETIC/MOCK terlihat pada semua sesi.
- Import: "Start analysis" disabled dengan alasan saat cloud audio UNDETERMINED; preview tidak memicu job; save session berhasil.
- Visual check 1440×900 dan 1280×720 untuk catalogue/import dibandingkan comps 01–02.

### Milestone 2 — Replay workspace, situation, operational memory

**Cakupan roadmap:** Phase 12.2–12.4. **Hasil:** workspace comp 03 dan memory comp 04 berfungsi penuh dengan replay visual-only.

| # | Pekerjaan | Detail |
| --- | --- | --- |
| 2.1 | Replay clock | Store Zustand berbasis `requestAnimationFrame` (bukan setInterval), play/pause, seek (drag + input numerik `mm:ss.s` + event list), step prev/next event, speed 0.5×/1×/2×, ended state ("Replay from start" / "Step to event"), follow leader vs local view (leader disimulasikan), keyboard: Space play/pause, ←/→ step event, Shift+←/→ ±5 s, `[`/`]` speed — tidak aktif saat fokus di input. Label "Visual replay · audio not loaded (MOCK)" |
| 2.2 | Context header | Judul sesi, `SYNTHETIC`, `Replay offline`, segmented As-known/Debrief, run selector (tidak auto-switch ke run terbaru; perubahan run ditampilkan eksplisit), as-of clock pill, connection pill (Connected/Reconnecting/Resyncing), "Cached results" pill |
| 2.3 | Snapshot binding | Query snapshot per `asOfBucket`; seek tidak membuat job/provider call (assert di mock: counter job tetap); mode AS_KNOWN menyembunyikan correction 05:24 saat as-of 05:22 |
| 2.4 | Situation canvas | SVG dari layout (runway polygon, hold line + label, taxiway, threshold 09/27), objek: observed solid trace, predicted dashed berlabel eligibility, centre-point-only marker dengan catatan "Footprint not available", stale trace memudar + age, missing object hanya di notice (tanpa marker), legend, caption "Fictional layout · meters · not an operational chart", hover/fokus marker → tooltip + select entity. Varian audio-only: daftar objek/runway context + coverage panel (bukan peta kosong) |
| 2.5 | Memory strips | Baris per objek: ikon jenis, callsign + tipe, Instruction, Readback, Movement (+alasan), Source age, "View evidence"; selected state; klik → object memory |
| 2.6 | Attention rail | Tabs Findings / Open loops dengan count; kartu tinted per prioritas (ATTENTION pink, NOTICE amber, INFO biru) dengan icon tile, waktu, quote, "Listen to evidence"/"View details"; filter entity/runway/category/status; "Review all" → Review; tanpa auto-focus |
| 2.7 | Timeline band | Waveform multi-channel (Tower/Ground) dari peaks sintetis deterministik, event markers, playhead, gap diarsir + label "Audio gap", evidence range dengan handle drag **dan** input numerik start/end, label range `05:12 – 05:19` |
| 2.8 | Object memory (comp 04) | Breadcrumb, judul callsign + chips (SYNTHETIC, mode), tabs Object/Runway. **Active context:** Said·Instruction, Heard·Readback candidate, Observed·Movement — masing-masing quote/alasan, status lifecycle, evidence link, Interpretation & Reviewer terpisah. **What happened** horizontal (gaya Margin) + **Context history** vertikal (as-of filtered, caption "Changes after as-of are hidden"). Runway card (ilustrasi konteks, "not actual position", Coverage partial pill), **Still open** (open loops + timer profile "Lab timer profile v1"), **Provenance** (input revision, reducer version, evidence count), mini player |
| 2.9 | Runway tab | Objek terkait, instruksi aktif, occupancy intervals bila eligible (S2), open loops, source ages, coverage gaps; tidak ada pernyataan "runway clear" |
| 2.10 | Stream & resync | Simulasi disconnect → banner, mutation disabled, last-known time; reconnect → snapshot + cursor; event duplikat/gap tidak menggandakan state (unit test reducer stream) |

**Acceptance M2:**
- Seek/step/speed konsisten; seek tidak menambah job (asserted).
- AS_KNOWN tidak membocorkan informasi future (test: as-of 05:22 → E-14 tidak ada; DEBRIEF → ada dengan label).
- NOT_EVALUABLE selalu dengan alasan; audio-only dan stale/missing track tidak terlihat sebagai monitoring lengkap.
- Evidence drawer stub (lengkap di M3) membuka tanpa mengubah clock.
- Resync tidak menggandakan item; mutation diblokir saat disconnected.
- Keyboard penuh untuk player dan strips; `aria-live` hanya untuk perubahan bermakna (bukan setiap tick).
- Visual check comp 03–04 pada 1440×900, 1280×720 (attention menjadi tab), tablet 1024 (panel bertab).

### Milestone 3 — Evidence, review, options, debrief, settings, P1, QA & polish

**Cakupan roadmap:** Phase 13.1–13.4 + bagian MOCK dari Phase 14. **Hasil:** semua journeys PRD E2E-01–05 dapat dijalankan pada UI mock; QA aksesibilitas/visual dilaporkan.

| # | Pekerjaan | Detail |
| --- | --- | --- |
| 3.1 | Evidence drawer (comp 06 kanan) | Sheet 440–480 px docked tanpa scrim di desktop, full-width di tablet. Header "Evidence · F-03", as-of + run, labels. Said/Heard cards berdampingan (ID, waktu, quote dengan slot highlight, channel, speaker "Candidate · FLN214", copy). **SlotComparison** (gaya estimate vs actual). Range player visual-only `0:00 / 0:07`. Tabs Audio/Event/Track. Association status bar. Disclosure "Alternatives & provenance" (model/prompt/rule/input versions, quote spans, source quality, applicability, review revision). Access denied audio → pesan pembatasan, bukan waveform kosong. Close → fokus kembali ke trigger |
| 3.2 | Findings review (comp 06) | Tabs Transcript/Findings/Options. Queue (ID · entity · waktu · judul · priority+status), detail (statement, category, priority, reviewer, movement, **source alert terpisah** "Source alert · Not available" + footnote "AI findings and source alerts are recorded separately", context: event vs available time slider, callsign, run). Review form: Confirm finding / Dismiss / Cannot be determined yet (awal kosong), reason wajib 0/500, Save disabled + alasan, "Revision 2 · Append-only", G-11 footnote. Version conflict dialog: pertahankan draft, tampilkan revision terbaru, pilihan reconcile |
| 3.3 | Transcript & association (comp 05) | Table virtualized (Time, Channel chip, Transcript, Association badge, `…`), search quote/callsign, channel filter, selected row. Inspector segmen T-13 dengan prev/next: **Original STT hypothesis** (read-only, help tooltip), association candidates (radio termasuk "Cannot be determined yet"), notice "Speaker identity not confirmed", **Transcript correction** field terpisah + reason; tombol simpan terpisah "Save pairing review" vs "Save transcript revision"; "Listen to evidence". Sukses → revision baru + banner "3 dependent results are stale" + "Reanalyze (new run)" dengan konfirmasi. Audio & evidence panel dengan range 05:16–05:19 (timer lokal offset cuplikan, total = durasi range) |
| 3.4 | Options review (comp 07) | Rail opsi (tenang), dossier: evaluation question, statement hipotesis, rationale, evidence chips, Preconditions (✓) vs Unknown (amber), Tradeoffs · Hypothesis, Applicability `LAB_ONLY`, versions. Evaluator form: Relevant / Not relevant / Unsupported by evidence / Cannot be determined yet (awal kosong), reason wajib, "Save rating", "Open evidence". Kartu **Insufficient context** (VEH03, nol opsi, "Needed: track and identity", aksi ke remediation). Observer: form diganti AccessDenied. Copy-guard: tidak ada Execute/Send/Apply |
| 3.5 | Debrief (comp 08) | Header: brief revision selector, "As-of replay 18:40", "Create brief revision" (membuat revision baru, bukan overwrite). **Journal** (vertikal, chip evidence, E-13 tetap "zero nine", E-14 correction). **Session summary**: Known situation, Context changes, Still open, Unknown & coverage, Findings, Review status — setiap item punya evidence chip; stale brief badge + link perubahan. **SpotlightCard** "Key item to review" (label AI interpretation · MOCK). **Export panel**: format HTML/CSV/JSON (segmented), Provenance (locked on), Include journal, Redact restricted evidence (wajib on bila grant membatasi), Include audio (disabled + alasan), callout "Report allowed · scope · expiry from profile", "Create export" → job states preparing/ready/failed/expired/revoked, download hanya saat ready. Provider outage: cached brief dapat dibaca/diexport, generate baru unavailable |
| 3.6 | Metrics (P1) | Tab di Debrief, badge `P1 · Experimental`: KPI kecil (measured active audio, open loops at as-of, object switches) dengan DeltaPill vs run sebelumnya; bar chart hatched occupied audio time per menit (as-of solid, garis referensi LAB_RULE); breakdown waterfall findings per kategori. Disclaimer: "Indicators are experimental, not a workload or fitness assessment. VAD not validated." |
| 3.7 | Ask (P1) | Panel tanya-jawab scoped: chip scope (session · run · as-of · context range read), contoh pertanyaan ("What is still pending for FLN214?"), jawaban template dengan evidence chips, jawaban "Unknown — not covered by this session" untuk di luar cakupan, permintaan ubah state → ditolak dengan arahan ke review endpoint. Riwayat per sesi/user (memori tab saja) |
| 3.8 | Settings (Phase 13.4) | Sub-nav: **Users** (list, status aktif/nonaktif, reset sementara — mock), **Grants** (per sesi: capability, audio, export, truth; revoke → stream terkait terputus), **Providers** (kartu toggle-style metadata: model ID, API/SDK version, region, status "Not verified", "Run readiness check" → hasil mock; tidak ada key), **Jobs & budget** (antrian, retry/cancel, usage, budget bar), **Storage** (disk bar hatched dengan threshold 80% warning/90% hold, inventory raw/derived/exports/scratch tanpa path), **Audit** (virtualized, filter actor/action/session/date), **Retention** (policy per sumber, purge request dengan preview inventory + alasan → audited). Non-admin: AccessDenied |
| 3.9 | Responsive | 1280×720: sidebar rail, attention/drawer sebagai tab/sheet; tablet: panel bertab, drawer full-width; mobile (≤640): catalogue/detail/brief **read-only**, workspace menampilkan "Open on desktop for full workspace" |
| 3.10 | QA & polish | Lihat §7. Perbaikan visual berdasarkan side-by-side dengan comps + referensi Margin |

**Acceptance M3:**
- E2E-01–05 lulus sebagai **MOCK journeys** (Python Playwright) — dilaporkan terpisah dari G-FE.
- Setiap factual output (finding, option, brief item, memory row, query answer) membuka evidence berizin; access denied eksplisit.
- Correction tidak menimpa original STT; stale dependents dan version conflict punya recovery jelas.
- Observer/admin tanpa review grant tidak dapat melakukan review (UI + mock authz).
- Copy-guard lulus (tidak ada Execute/Send clearance/LIVE); opsi nol jalur eksekusi.
- Provider outage & insufficient context tidak menghasilkan fake content.
- Settings tidak menampilkan key/path privat.
- Axe tanpa pelanggaran serious/critical pada semua route; keyboard journeys lulus; reduced motion dihormati.

---

## 7. Strategi verifikasi

| Level | Alat | Cakupan |
| --- | --- | --- |
| Static | `tsc --noEmit`, ESLint, `check:types` (drift generated vs contracts), `check:copy` (grep kata terlarang di `src/`: `execute`, `send clearance`, `LIVE`, `runway clear`, `safe`) | Setiap milestone |
| Unit | Vitest | Formatter waktu/offset, query keys (scope lengkap), mock engine (as-of filtering, idempotency, expectedVersion conflict, append-only, stale marking, authz per role), stream reducer (gap/duplicate/resync), status mapping lengkap untuk semua enum kontrak |
| Component | Testing Library + vitest-axe | Review form (awal kosong, reason wajib, disabled reason), QuoteBlock slot highlight, StatusBadge icon+teks, EvidenceDrawer fokus kembali, Player keyboard, AccessDenied vs Empty |
| Journey (MOCK) | Python Playwright (`tests/e2e/frontend_mock/`) terhadap `vite preview` | Import → save; workspace seek/mode; transcript correction → stale; finding review; option review + observer denied; brief/export; provider outage; connection lost/resync; role switch cache clear; desktop/tablet viewport |
| Visual | Screenshot 1440×900, 1280×720, 1024×768, 390×844 | Dibandingkan dengan comps 01–08; dilaporkan terpisah dari assertion fungsional |
| Accessibility manual | Keyboard-only walkthrough, zoom 200%, kontras token, reduced motion | Checklist di evidence record |

Evidence dicatat di `docs/testing/frontend-mock-evidence.md` (dibuat saat M1) dengan command, hasil, dan batasan. Status yang dilaporkan dipisah: **ada di source → build berhasil → berjalan (mock) → tests lulus (mock)**. Tidak ada klaim integrasi backend, provider, atau domain review.

---

## 8. Update dokumen dan status per milestone

| Saat | Dokumen | Isi |
| --- | --- | --- |
| Awal M1 | `.agent/implementationPhases.md` | Phase 11–13 `in_progress` (MOCK frontend track, keputusan pengguna 8 Okt 2026); G-FE `blocked: requires G-BE + real API integration`; Phase 14 hanya MOCK journeys |
| Awal M1 | `.agent/PRD.md` §5.3, §23.2 | UI English (contoh copy diterjemahkan); keputusan pengguna tercatat |
| Akhir tiap milestone | `.agent/sessionHandoff.md` | Changed files, checks nyata, runtime yang ditinggalkan, next action |
| Akhir M3 | `docs/README.md`, `docs/development/` | Link ke rencana ini, panduan menjalankan frontend mock, cara mengganti adapter ke HTTP |

Commit hanya bila diminta pengguna; conventional commits per fitur (mis. `feat: add session catalogue with readiness axes`).

---

## 9. Risiko, gap kontrak, dan mitigasi

| Risiko/gap | Dampak | Mitigasi |
| --- | --- | --- |
| Mock engine menjadi "business logic" yang terbawa ke produksi | Duplikasi rule di browser (roadmap §1) | Engine hanya di `adapters/mock/`; lint rule melarang import `adapters/mock` dari `features/`/`components/`; dihapus saat `HttpApiClient` aktif |
| Kontrak 1.0.0 belum punya field tampilan (label pendek `E-12`, nama entitas, session list DTO, user/grant DTO, export job DTO) | Type generated tidak cukup untuk semua screen | Definisikan `src/api/viewTypes.ts` berlabel `PROPOSED_CONTRACT`; catat sebagai input reconcile kontrak sebelum Phase 10 (bukan perubahan kontrak sepihak) |
| UI English bertentangan dengan PRD §5.3 | Ketidakkonsistenan dokumen | Update PRD di M1 task 1.0 |
| Visual-only audio menyembunyikan isu browser audio/range | G-FE criteria audio belum teruji | Dicatat sebagai item terbuka G-FE; komponen player memakai interface `AudioSource` agar `<audio>` + range request dapat dipasang nanti |
| Hatch/gradient berlebihan menurunkan keterbacaan | Melanggar PRD §23.1 | Batas: satu SpotlightCard per halaman Debrief; hatch hanya bermakna (predicted/gap/discrepancy) dengan legend |
| Python Playwright menambah dev dependency backend | `uv.lock` berubah | Tambahkan via `uv add --dev pytest-playwright`, jalankan contract tests yang ada untuk memastikan tidak ada regresi |
| Font/CDN eksternal | Ketergantungan jaringan | Inter self-hosted via npm |
| Performa transcript/audit panjang dan canvas saat play | Jank pada 60 fps | Virtualisasi, memo per frame, canvas SVG hanya re-render layer objek; ukur di M3 |

---

## 10. Out of scope rencana ini

Integrasi API/WebSocket nyata, audio playback nyata, provider STT/Gemini, containerization/Caddy/Compose, deployment, dark mode, bilingual UI, five-browser shared replay nyata, domain review, dan penutupan G-FE. Semua tetap mengikuti roadmap setelah G-BE.
