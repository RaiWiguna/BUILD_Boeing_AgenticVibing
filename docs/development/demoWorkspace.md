# Panduan Demo Workspace (Python + PostgreSQL)

Track demo sesuai [ADR 0003](../adr/0003-demo-workspace-track.md). Rencana dan alasan desain ada di [demoWorkspacePlan.md](demoWorkspacePlan.md).

## 1. Siapkan file skenario (sekali)

Aset ada di `data/demo-scenarios/kagc-2022-09-10-88/` (di-ignore Git):

| File | Isi |
| --- | --- |
| `88.wav` | Audio TartanAviation KAGC, CC BY 4.0, 96,9 s, float32 44,1 kHz mono |
| `87.wav` | Rekaman sebelumnya (19:00:25–19:02:59), CC BY 4.0, 153,9 s. Berisi clearance taxi "turn right at Bravo 1, runway 13, taxi via Bravo, Alpha, Charlie, hold short of runway 28" dan readback-nya |
| `kagc_adsb_2022-09-10_88.csv` | ADS-B sintetik untuk 88 (SHA-256 `7167fff6…`; berubah dari `8eb8b0e8…` karena lintasan kini bersambung dari 87) |
| `kagc_adsb_2022-09-10_87.csv` | ADS-B sintetik untuk 87 (SHA-256 `31550c2d…`): ramp → kanan di B1 → B → A |
| `derived/87.pcm16.wav`, `derived/88.pcm16.wav` | Turunan untuk playback browser (disajikan server) |
| `scenario.json` | Spec v2: `parts` (87 before, 88 main), tiga `variants` (88 saja · 87+88 · 87+88+CSV 87), transcript cache, layout KAGC (runway AirNav, taxiway skematik), peaks |

Kedua CSV sintetik; status itu hanya dicatat di dokumen ini dan ADR 0003, tidak ditampilkan di nama file maupun aplikasi (permintaan pengguna). Transcript 87 berasal dari Google STT (`latest_long`, 4 request, cache di `outputs/tartan-research/stt-87/run.json`); transcript 88 dari cache riset.

Jika belum ada, ambil dan bangun ulang (butuh akses SSH ke VM riset dan `ffmpeg`):

```bash
SSH_KEY=~/.ssh/<key> VM=<user@host> scripts/demo/fetch_scenario.sh
```

87.wav diambil dari arsip publik TartanAviation; cache STT 87 harus sudah ada (script tidak memanggil STT).

Membangun ulang turunan tanpa mengunduh: `python3 scripts/demo/synth_adsb.py` lalu `python3 scripts/demo/build_scenario.py`. Setelah `scenario.json` berubah, restart `api`.

## 2. Jalankan backend

```bash
docker compose -f deploy/compose/local/compose.demo.yml up -d --build
```

```bash
curl -s http://127.0.0.1:8000/api/demo/health
```

`DEMO_PROCESSING_SCALE` (default `1.0`, sekitar 22 s untuk 2 file, +30% per file tambahan) mengatur panjang jadwal processing. Hentikan dengan `docker compose -f deploy/compose/local/compose.demo.yml down` (jangan pakai `-v` kecuali memang ingin menghapus database).

## 3. Jalankan frontend

```bash
npm --prefix frontend run dev
```

Vite mem-proxy `/api/demo` ke `127.0.0.1:8000`. Masuk dengan akun demo, buka **Sessions → Import session**, isi nama, lalu taruh file di lane **Before / Main recording / After** (drag atau **Choose files**; file dikenali otomatis ke lane-nya). Main wajib audio + ADS-B; Before/After boleh audio saja atau audio + CSV. **Upload and process** → processing → workspace terbuka sendiri.

Lane Before dan After masing-masing bisa berisi banyak rekaman (**Add another recording before/after**, atau drag ke lane); file yang dikenali dipasangkan per rekaman, file tak dikenal ditandai "Not a recording of this scenario" dan tidak pernah menggantikan Main. Untuk skenario ini hanya 87 (before) + 88 (main) yang dikenali, jadi alur demo tetap 2 track.

Processing menampilkan 14 tahap sebuah run nyata: Upload received → Integrity check → Audio decoding → Voice activity detection → ADS-B ingest and quality check → Time alignment → Speech recognition → Speaker roles → Phraseology extraction (LLM) → Instruction–readback pairing → Track association → Conformance checks → Highlights → Session saved. Tahap yang berjalan memunculkan detail baris demi baris; tahap selesai diringkas jadi satu baris plus peringatan (⚠). Polling tetap jalan saat tab di background.

Alur demo yang disarankan:

1. Di Import, pilih keempat file sekaligus (`87.wav`, CSV 87, `88.wav`, CSV 88). File 87 otomatis masuk lane **Before**, file 88 ke **Main recording**. **Upload and process**.
2. Workspace terbuka dengan "2 recordings". Klik **Skip to 01:45** lalu play: clearance taxi di 87, readback cocok, lalu "Not recorded" (gap 14 s antar rekaman) dan 88. Kini "Bravo Alpha" terbaca sebagai rute; finding identitas hilang, diganti "Readback matches · right at B1 not read back", "Audio lost 14 s" dan "Hold short changed · RWY 28 → C on A" (RWY 28 → "Charlie on Alpha" tanpa instruksi pengubah yang terekam). Dengan CSV 87 bertambah "Taxiing as cleared" (7 → 9 → 10 findings).
3. Pembanding (opsional): sesi kedua berisi 88 saja. Tanpa konteks, "Bravo Alpha" terbaca sebagai callsign dan muncul finding "Callsign incomplete".

Rekaman hanya bisa ditambahkan saat import awal; workspace tidak punya tombol tambah rekaman.

Transcript: tiap kata tampil 0,4 s setelah diucapkan; selama "Recognizing" role belum tampil, role (ATC/Pilot) muncul 0,4 s setelah segmen final. Divider per rekaman, baris "Not recorded" untuk gap, tombol **Skip** saat hening > 6 s. Posisi playback disimpan ke PostgreSQL saat pause.

Highlight di workspace (panel **Needs attention**) ditulis untuk controller yang sedang bertugas: judul + kalimat fakta singkat dengan jam UTC (mis. `19:02:10Z`), tanpa saran tindakan, plus tabel Said/Heard per slot. Teks analitis lengkap tetap di Review. Field `live` per finding di `scenario.json`/seed; analisis tersimpan dibangun ulang otomatis bila `scenario.json` berubah (`build` hash).

Panel kontrol skenario developer hanya tampil bila `localStorage.setItem('flowlens.devtools','1')` di browser.

## 4. Tests

```bash
docker compose -f deploy/compose/local/compose.demo.yml --profile test run --rm api-test
```

```bash
npm --prefix frontend test
```

Journey browser (opt-in, butuh `pytest-playwright`, frontend dev server, dan backend demo):

```bash
FLOWLENS_FRONTEND_URL=http://localhost:5173 python -m pytest tests/e2e/frontend_mock/test_demo_workspace.py
```

Setiap run e2e menyimpan workspace bernama `E2E demo …` di database lokal.

## 5. Batasan

- Enam skenario dikenali lewat katalog per case (nama + SHA-256 + ukuran); file lain ditolak (`UNKNOWN_FILE`, `CHECKSUM_MISMATCH`, `WRONG_POSITION`, `MISSING_AUDIO`, `MISSING_ROLE`, `DUPLICATE_FILE`, `UNSUPPORTED_COMBINATION`). Lane After belum punya rekaman yang dikenali (89 tidak dipakai atas permintaan pengguna).
- Transcript adalah cache hypothesis Google STT dari riset, bukan transkrip terverifikasi. Findings di-author untuk demo, bukan output detector.
- ADS-B sintetik; layout KAGC: ujung runway dari data publik (13/31 memang memotong 10/28), taxiway skematik mengikuti susunan nyata (OSM) dengan jarak di A dipadatkan. Tidak untuk penggunaan operasional.
- Tidak ada endpoint delete/rename workspace; bersihkan lewat `psql` di container `db` bila perlu.

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

## Lima case tambahan — 12 Oktober 2026

Expansion menambahkan **50, 51, 47, 156, 123** sebagai standalone cases. Di **Import session → Case**, pilih kasus sebelum memilih pasangan WAV + CSV dari folder berikut:

| Case | Folder private `data/demo-scenarios/` | Isi |
| --- | --- | --- |
| Multi-object Tower | `kagc-2022-09-10-50` | Downwind/backtaxi traffic dan departure terpisah |
| Landing readback | `kagc-2022-09-10-51` | Landing 13/readback; optional before 50 |
| Conditional departure | `kagc-2022-09-10-47` | Takeoff 13; backtaxi **if needed** |
| Clearance memory | `kagc-2022-09-11-156` | Maintain 3,000 / squawk 4131; FL180 bukan assigned altitude |
| Departure handoff | `kagc-2022-09-10-123` | Contact 119.35/readback; heading unresolved |

Filename CSV: `kagc_adsb_<tanggal>_<nomor>.csv`. Case 51 juga menerima `50.wav` sebelum main, dengan atau tanpa CSV 50. Default kasus existing 87/88 dan semua assets/variants/timings/highlights mereka dipertahankan. Batas satu before/satu after berlaku hanya bagi case baru; hanya companion yang terdaftar dapat digunakan. Memilih case lain mengosongkan draft pilihan file, bukan workspace tersimpan.

Builder baru: `python3 scripts/demo/build_additional_scenarios.py`. Fetch source yang sudah ada di VM: `VM=<user@host> SSH_KEY=<private-key-path> python3 scripts/demo/fetch_additional_scenarios.py`. Keduanya memerlukan ignored cache penelitian; fresh clone tidak membawa WAV/cache. Builder baru tidak memanggil generator 87/88 atau provider. Seleksi menghasilkan tujuh variants tambahan dan lima WAV unik (441.628934s); 50 reuse sebagai optional before, tanpa concat dan dengan playback gap55.071s.

Semua new tracks adalah **authored centre-point fixtures**, bukan paired historical ADS-B, airborne/surface observation authoritative, atau model penerbangan. Trajectories hanya mengilustrasikan entity context; CSV altitude1252/heading/speed adalah assumed fixture values, timestamp granularity1s. Seluruh finding movement tetap NOT_EVALUABLE, footprint=false dan prediction kosong. Prior-clip entities dalam51+50 tetap terpisah (`[50]`) dan track menjadi stale setelah coverage berakhir; continuity pesawat tidak diklaim terbukti.

Highlights/reminders bersifat cached authored candidates, rawSTT tidak dikoreksi diam-diam, speaker/identity belum human-reviewed. Readback card runway/action menggunakan per-slot AMBIGUOUS; frequency/altitude/squawk memakai fact rows. Tidak membuat mismatch/violation karena readback absent, tidak menampilkan FL180 sebagai climb assignment, dan tidak menganggap frequency readback sebagai contact completed. Instruction memory terpisah dari readback/movement. Laporan rencana/evidence mapping: [expansion plan](demoScenarioExpansionPlan.md).

Verifikasi expansion: backend28pytest, frontend61Vitest, typecheck/lint/generated-type/copy/build, enam browser import journeys (lima standalone +51denganbefore50), final replay/seek-to-zero checks, audio206, scoped matching/scenario rejection, screenshot inspection dan no horizontal overflow1280px. Lima source hashes cocok dengan cache;13 protected fingerprints87/88/generator/layout tidak berubah. Fixture browser yang dibuat untuk QA dibersihkan berdasarkan UUID+prefix khusus; user workspaces tidak dihapus.

Build normal image terhalang DNS `auth.docker.io`. Runtime lokal memakai incremental image dari immutable cached image yang sudah terpasang, dengan source backend terbaru; checksum source di container cocok dengan workspace. Rebuild bersih menggunakan Dockerfile.demo tetap perlu diulang saat Docker Hub tersedia. Ini bukan deployment/release gate. API localhost8000 dan frontend localhost5173 dibiarkan berjalan untuk inspeksi pengguna.


## Attention lima case tambahan — 13 Oktober 2026

Tabel berikut mencatat konfigurasi yang terpasang di `CARDS` dan `REMINDERS` pada [builder additional scenarios](../../scripts/demo/build_additional_scenarios.py), bukan hanya usulan pada rencana awal. Seluruh kartu baru berprioritas **INFO**, kategori `CRITICAL_SLOT_UNCERTAIN`, quality `AMBIGUOUS`, dan movement `NOT_EVALUABLE`.

| Main WAV | Needs attention | Keep in mind |
| --- | --- | --- |
| 50 | `RWY 13 · Downwind read back`; `Alpha? · Takeoff clearance` | Quebec: midfield left downwind RWY 13; Duchess backtaxi advised dari voice report |
| 51 | `RWY 13 · Landing clearance read back`; `Alpha? · Turnout exchange` | Quebec: landing clearance RWY 13 |
| 47 | `RWY 13 · Conditional backtaxi approved` | Takeoff cleared RWY 13; backtaxi **if needed** |
| 156 | `Clearance · 3,000 ft / 4131` | Julia Charlie: maintain 3,000 ft; squawk 4131 |
| 123 | `119.35 · Frequency read back` | Contact departure 119.35 |

Setiap kartu merujuk supporting segments/words. `pending` dijadwalkan 400 ms dan `available` 800 ms setelah supporting transmission berakhir, dengan pembulatan clock demo ke 0,1 s. Reminders juga tersedia setelah 800 ms. Replay/seek menghitung ulang state as-of; kartu masa depan tidak ditampilkan pada awal rekaman. Dengan before 50 pada case 51, attention/reminders 50 ikut tersedia sesuai offset sebelum main, dipisahkan dengan identitas `[50]`; source-start offset 120.003 s dan gap playback 55.071 s tetap dipertahankan.

Runway/action readback pada 50 dan 51 tetap `AMBIGUOUS`, bukan whole-clearance `MATCHED`. Case 47 menyatakan readback tidak ada dalam cached clip; case 156 membedakan assigned 3,000 ft dari expectation FL180 yang unresolved; case 123 tidak menyatakan contact selesai. Turnout Alpha tidak digabung dengan landing Quebec. Kartu baru tidak memperoleh resolved verdict dari trajectory sintetis dan tidak menyimpulkan wrong runway, konflik, atau physical conformance. Kebutuhan human listening/domain review tetap terbuka (`NOT_DOMAIN_VALIDATED`).

Renderer attention yang digunakan tetap renderer existing; penyesuaian berada pada evidence, copy, waktu, actor scope, dan reminders setiap case. Konfigurasi attention 87/88 tidak berubah. Verifikasi aplikasi yang tercatat pada 12 Oktober tetap berlaku; pembaruan 13 Oktober ini hanya memperjelas dokumentasi dari source yang diperiksa, tanpa provider call atau benchmark domain baru.
