# Frontend MOCK track — evidence record

Tanggal: 8–9 Oktober 2026. Status: **Milestone 1–3 diimplementasikan sebagai MOCK track** (Phase 11–13 `in_progress (MOCK)`). Candidate: working tree branch `feat/fe-init`, belum commit/push. G-FE tetap `blocked` — evidence ini **bukan** full-stack evidence dan tidak menggantikan journeys terhadap backend nyata.

Semua data `SYNTHETIC` + `MOCK`, dilayani adapter in-browser (`frontend/src/api/adapters/mock`). Tidak ada backend, provider call, file audio, atau secret di bundle. Rencana: [frontend implementation plan](../development/frontend-implementation-plan.md).

## Cakupan yang diimplementasikan

| Area | Route | Acuan desain |
| --- | --- | --- |
| Login + demo role switcher | `/login`, user menu | — |
| Sessions catalogue, import | `/sessions`, `/sessions/import` | comp 01–02 |
| Replay workspace (situation canvas, memory strips, attention rail, timeline visual-only) | `/s/:sid/workspace` | comp 03 |
| Operational memory (object / runway) | `/s/:sid/memory/*` | comp 04 |
| Transcript & association, Findings + evidence, Option candidates | `/s/:sid/review/*` | comp 05–07 |
| Evidence drawer (`?evidence=`), review append-only | semua layar sesi | comp 06 |
| Debrief: journal, brief revisions, spotlight, export | `/s/:sid/debrief` | comp 08 |
| Communication metrics (P1 · Experimental) | `/s/:sid/metrics` | Margin KPI/waterfall |
| Ask (P1, read-only contextual query) | `/s/:sid/ask` | — |
| Settings: account (semua role); users, session access, providers, jobs & budget, storage, audit, retention (admin) | `/settings/*` | — |
| Help: legend, finding categories, provenance, glossary, keyboard | `/help` (`#provenance`, `#finding-categories`) | — |

Guardrails yang ditegakkan di UI + mock authz: Said/Heard/Observed terpisah; Unknown/NOT_EVALUABLE tidak pernah hijau; As-known hanya menampilkan item dengan `available_time_ms ≤ as-of` (filter di mock "server"); review/pairing/correction/brief append-only dengan reason wajib dan awal tanpa pilihan; opsi tanpa jalur execute/send; provider outage dan insufficient context tidak menghasilkan konten palsu; pertanyaan "runway clear/safe" dijawab Unknown tanpa evidence; export selalu membawa provenance, audio export nonaktif, CSV formula-safe; label SYNTHETIC/MOCK selalu terlihat; mobile read-only.

## Performed checks

Environment: macOS arm64, Node 22.23.2, npm 10.9.8 (`package-lock.json`). Python journeys: venv sementara di scratchpad (pytest 9.1.1, pytest-playwright 0.9.0, playwright 1.63.0, channel Chrome lokal) — **tidak** mengubah `pyproject.toml`/`uv.lock` karena `uv` tidak tersedia di mesin ini.

| Command/cakupan | Result |
| --- | --- |
| `npm run typecheck` | PASS |
| `npx eslint .` (termasuk aturan: features tidak mengimpor adapters) | PASS |
| `npm run check:types` (generated contracts vs `contracts/`) | PASS — up to date |
| `npm run check:copy` (no execute/send clearance, no LIVE, no runway safe/clear claim) | PASS — 85 files |
| `npx vitest run` | PASS — 41 tests / 4 files (unit, component journeys, axe per route) |
| `npm run build` | PASS — route-level code splitting; entry chunk 476 kB (141 kB gzip), tanpa chunk > 500 kB |
| `dist/` scan: file audio | 0 file |
| `src/` + `dist/` scan: API key pattern / absolute local path | 0 match |
| `pytest tests/e2e/frontend_mock --browser-channel chrome` terhadap `vite preview` (`:4173`, build produksi) | PASS — 15 MOCK journeys |
| Same suite tanpa server (`:4999`) | 15 skipped (skip bersih, tidak memblokir suite backend) |
| Sweep console 77 route (6 sesi × workspace/memory/review/debrief/metrics/ask, settings admin) | 0 console error / page error |
| Overflow horizontal 390×844, 720×450 (≈ zoom 200 % dari 1440×900), 1024×768 — 19 route | 0 overflow |

### Unit (Vitest, `tests/unit`)

Mock engine: as-known vs debrief availability; correction tidak bocor ke as-known memory 05:22; finding markers as-known tidak memuat F-07; idempotency; `expectedVersion` conflict; mutation ditolak saat connection lost; provider outage — cached readable, brief baru ditolak; opsi tanpa command payload + VEH03 insufficient; brief revision append; export CSV membawa provenance header dan cell formula-safe; pertanyaan runway clear → `INSUFFICIENT_CONTEXT` tanpa item. Time formatter/parser.

### Component (Testing Library + vitest-axe, `tests/components`)

Mount routes asli (`createMemoryRouter(routes)`) di atas adapter MOCK:

1. Finding review: tiga pilihan awal kosong, Save `aria-disabled`, reason wajib, simpan → "Revision 1 · You", form reset; axe tanpa violation.
2. Debrief: label "AI interpretation · Mock", provenance switch checked + locked, audio export off + disabled; axe tanpa violation.
3. Ask: jawaban Unknown tanpa tombol evidence.
4. Non-admin `/settings/users` → "Access restricted", tabel tidak dimuat.

5. Axe per route (`tests/components/a11y.test.tsx`): 13 route evaluator + 7 route admin tanpa pelanggaran `serious`/`critical`.

Catatan: rule axe `color-contrast` dan `region` dinonaktifkan di jsdom (layout/warna tidak dihitung); kontras diperiksa via token + inspeksi visual.

### MOCK journeys (Python Playwright, `tests/e2e/frontend_mock`)

| Journey | Yang dibuktikan |
| --- | --- |
| Sessions | Label SYNTHETIC terlihat |
| As-known vs Debrief | As-known 05:20 menyembunyikan F-03 (available 05:22); Debrief menampilkannya |
| Finding review | Awal kosong, reason wajib, append-only (Revision 1 · You) |
| Observer | Review read-only, tanpa tombol Save |
| Debrief export | PREPARING → Ready + Download; audio disabled; provenance checked |
| Tablet 1024×768 | Workspace render |
| Import | Sample bundle → preview → izin cloud audio wajib basis → Save session tanpa provider call → analisis diblokir dengan alasan (profil provider Not verified) |
| E2E-01 | Koreksi transcript menyimpan revisi, STT asli tetap, hasil turunan stale, re-analyse membuat Run #04 tanpa mengganti run aktif; memory Debrief menampilkan CORRECTED dan riwayat discrepancy |
| E2E-02 | Open loop "Report clear awaited" tetap terbuka; gap audio 09:30–10:10 sebagai coverage |
| E2E-03 | Divergence candidate + source alert terpisah; switch Stale tracks → NOT_EVALUABLE |
| E2E-04 | Sesi audio-only: tanpa track, analisis partial; provider outage → brief baru ditolak, brief tersimpan tetap terbaca |
| E2E-05 | Rating opsi awal kosong + reason wajib + revision; ganti role ke Observer → "Rating is read-only" |
| Connection lost | Banner putus koneksi, simpan di-pause tanpa antrean, pulih saat switch dimatikan |
| Keyboard | Space play/pause; Enter membuka evidence drawer, Escape menutup, fokus kembali ke tombol pemicu |

Flag Mock control disimpan di memori, jadi journeys menyalakannya setelah page load terakhir.

### Bug yang ditemukan dan diperbaiki pada M3 QA (9 Oktober)

| Temuan | Perbaikan |
| --- | --- |
| Setelah koreksi transcript disimpan, panel segmen kosong ("Select a segment") dan koreksi kedua akan memakai ID revisi (NOT_FOUND) | Seleksi dan write memakai ID segmen asli (`original.id`); revisi tetap terhubung |
| Re-analyse memberi label `#03` (duplikat run aktif) | Nomor run = label tertinggi + 1 |
| 1280×720: tombol akun sidebar keluar layar | Varian `short` (max-height 820px) merapatkan sidebar; sidebar dapat di-scroll |
| SVG path `NaN` saat objek diam (titik track berulang) | Titik berurutan yang identik dibuang sebelum membuat path |
| Fokus tidak kembali ke pemicu setelah evidence drawer ditutup | Fokus dipulihkan di `onCloseAutoFocus` setelah focus trap dilepas |
| axe: `nested-interactive` (range editor di dalam slider timeline), `aria-valid-attr-value` (tab Sessions tanpa panel), `definition-list` (link di dalam `dl`) | Range editor dipindah menjadi sibling slider; tab mengontrol `#session-table`; link dibungkus `dt`/`dd` |
| Overflow horizontal di ponsel: teks `sr-only` di tabel lolos dari kontainer scroll; grid tanpa kolom dasar mengikuti min-content; header Review dan stepper Import tidak membungkus | Kontainer scroll `relative`; grid responsif mendapat `grid-cols-1` dasar; header membungkus; label step non-aktif hanya untuk screen reader di ponsel |
| Smooth scroll JS mengabaikan reduced motion | `behavior` mengikuti `prefers-reduced-motion` |
| Fixture login journeys tidak meng-encode `next`, sehingga `t`/`segment` hilang | `next` di-encode; tunggu redirect keluar dari `/login` |

### Visual (browser pane, 1440×900 kecuali disebut)

Dibandingkan side-by-side dengan comps: 03 workspace, 04 memory, 05 transcript (baris AMBIGUOUS terpilih otomatis di-scroll ke tengah tabel), 06 findings + evidence, 07 options, 08 debrief (rev 2 dan rev 1 stale). Metrics, Ask, Settings (evaluator + admin), Help diperiksa. Responsive: mobile 375×812 (top bar + navigation sheet, timeline tidak sticky, axis label tidak bertumpuk, write controls diganti catatan read-only), tablet 768×1024 (sidebar rail, kolom bertumpuk). 9 Oktober: dicek ulang 1280×720 (sidebar rapat, tombol akun terlihat, range editor timeline) dan 390×844 (Sessions, Import, Findings) setelah perbaikan overflow.

## Limitations

- MOCK track saja: tidak ada HTTP adapter/backend nyata; G-FE `blocked` sampai G-BE `passed`.
- Audio visual-only; tidak ada playback.
- `pytest-playwright` belum ditambahkan ke `pyproject.toml`/`uv.lock` (jalankan `uv add --dev pytest-playwright` di mesin dengan `uv`, lalu `uv run playwright install chromium` atau gunakan `--browser-channel chrome`).
- Accessibility: axe otomatis per route, journey keyboard (replay + evidence drawer), overflow pada zoom 200 % dan reduced motion (CSS + JS scroll) sudah dicek. Belum dilakukan: walkthrough keyboard-only penuh untuk setiap layar, uji screen reader nyata (VoiceOver/NVDA), dan kontras yang diukur di browser untuk semua state.
- Suite pytest backend tidak dijalankan pada sesi ini (tidak ada `.venv`/`uv` di mesin); journeys frontend tetap opt-in dan skip bila Playwright atau server tidak tersedia.
- Waktu "last sign-in" akun demo statis dari seed.

## Runtime / cleanup

Dev server Vite (`frontend-mock`, port 5173) dan `vite preview` (`frontend-preview`, port 4173; konfigurasi di `.claude/launch.json`) dipakai untuk verifikasi. Venv Playwright sementara berada di scratchpad sesi, bukan di repo. Folder debug test sementara dihapus. Tidak ada commit/push.
