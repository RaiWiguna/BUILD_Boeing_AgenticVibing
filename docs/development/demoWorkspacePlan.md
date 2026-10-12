# Rencana Implementasi — Demo Workspace Session (MOCK, backend Python + PostgreSQL)

| Atribut | Nilai |
| --- | --- |
| Tanggal | 12 Oktober 2026 |
| Status | DIIMPLEMENTASIKAN lokal 12 Oktober 2026 — lihat [panduan](demoWorkspace.md), [ADR 0003](../adr/0003-demo-workspace-track.md) dan §10 untuk perbedaan dari rencana |
| Label data | Audio `PUBLIC_CORPUS` (TartanAviation KAGC, CC BY 4.0) · transkrip `STT_HYPOTHESIS` (cached, tanpa provider call baru) · ADS-B `SYNTHETIC` · findings `MOCK` · seluruhnya `NOT_DOMAIN_VALIDATED` |
| Keputusan pengguna | Import tanpa source kind; dua file (ADS-B + audio); satu skenario; backend Python + PostgreSQL via Docker Compose lokal; playback audio nyata; hapus open loop dari seluruh UI; integrasi hybrid dengan sesi MOCK lama; ADS-B sintetik yang dikalibrasi dari analisis ADS-B nyata dan diselaraskan dengan audio |

## 1. Konflik dengan kontrak yang berlaku (dicatat, bukan diblokir)

Instruksi eksplisit pengguna berlaku di atas rules. Konflik berikut dicatat pada ADR `docs/adr/0003-demo-workspace-track.md` dengan scope **demo track**, bukan perubahan kontrak v1:

| Kontrak | Konflik | Penanganan |
| --- | --- | --- |
| Rules §4.2/§4.3: SQLite, tanpa PostgreSQL default | Demo memakai PostgreSQL | Hanya untuk demo service `flowlens_demo`; foundation `backend/flowlens` dan contract 1.0.0 tidak disentuh |
| PRD FR-01: import menyimpan `source_kind` | UI import tanpa source kind | Server menetapkan `source_kind`/permission/provenance dari manifest skenario; tidak ditanyakan ke pengguna |
| Phases: G-BE sebelum frontend | Frontend memanggil backend demo sebelum G-BE | Demo track paralel; G-BE/G-FE tetap `blocked` |
| Decision D-3: audio visual-only | Audio diputar nyata | Hanya untuk sesi backend; sesi MOCK lama tetap visual-only |
| Rules §4.4: tidak mencampur track dan audio beda hari | ADS-B tidak tersedia untuk 10 Sep 2022 | ADS-B **sintetik** berlabel jelas; Observed diberi badge `SYNTHETIC`; tidak diklaim sebagai pasangan nyata |

## 2. Skenario: `88.wav` — revisi rute taxi KAGC

Sumber: `kagc/2022/9/09-10-22_audio.zip` → `88.wav`, 96,906 s, SHA-256 `8c114b9f37e8ef0ca35735e4aea89634db1ec9040a397cdc3d679ce981fde7a3`, metadata start `2022-09-10 19:03:13.318769` (timezone belum diverifikasi). Transkrip STT V1 `latest_long` sudah ada (7 segment, word offsets):

| Offset | STT (hypothesis) | Peran dalam demo |
| --- | --- | --- |
| 0,0–5,8 | There's going to be a opposite direction, a Cessna going eastbound on Alpha to Charlie. | Traffic information (ATC) |
| 7,5–12,6 | Roger. So Bravo Alpha then hold short of Charlie on Alpha. | Kandidat respons/route confirmation |
| 29,7 | One. (conf 0,16) | Kualitas rendah / gap transkripsi |
| 43,0–49,9 | Archer one first seven, golf change of plans. Again, roam one. Three. Continue taxing via. They're on. | Revisi instruksi (change of plans) |
| 50,0–53,5 | Will join Alpha turn right on golf. | Route baru (melintasi chunk boundary 50 s) |
| 53,9–57,5 | Across from way to a golf and hold short. Runway one three | Crossing (rusak) + hold short 13 |
| 58,3–65,3 | One, three the Bravo Alpha right turn on golf. Cross Runway, 28 hole short, rolling rolling three on golf 147, golf. | Kandidat readback |

### 2.1 File yang disiapkan di project folder

`data/demo-scenarios/kagc-2022-09-10-88/` (ignored oleh `/data/**`, tidak masuk Git):

| File | Isi | Cara dibuat |
| --- | --- | --- |
| `88.wav` | Raw source immutable (float32 44,1 kHz) | SCP dari VM `kagc-plus30-05/09-10-22_audio/88.wav`, verifikasi SHA |
| `derived/88.pcm16.wav` | Derivative untuk browser (PCM16 mono) — raw tetap utuh | `ffmpeg` lokal |
| `kagc_adsb_2022-09-10_88.csv` | ADS-B sintetik skema raw Tartan 13 kolom | `scripts/demo/synth_adsb.py` |
| `scenario.json` | Manifest + transcript words + entities + layout + findings + waveform peaks | `scripts/demo/build_scenario.py` |

Versioned (masuk Git): `scripts/demo/*.py`, `backend/flowlens_demo/scenarios/kagc88.spec.json` (spesifikasi findings/entities/layout yang di-author, mereferensikan segment ID, bukan audio). `scripts/demo/fetch_scenario.sh` mengulangi SCP + build agar clone baru dapat menyiapkan aset.

Deteksi: upload dicocokkan berdasarkan **nama file** (`88.wav`, `kagc_adsb_2022-09-10_88.csv`) lalu SHA-256 dihitung server dan dibandingkan dengan manifest. Nama tidak dikenal → `INVALID_IMPORT` “No demo scenario is registered for this file (MOCK backend)”. Nama cocok tetapi checksum beda → ditolak dengan kode stabil. File upload hanya di-hash lalu dibuang; server memakai salinan kanonis skenario (tidak menduplikasi audio).

## 3. ADS-B sintetik — analisis dulu, lalu sintesis

1. **Kalibrasi dari data nyata** (`outputs/tartan-research/adsb/analysis.json`, `quality-extra.json`, `08-27-22-near.json`, `08-30-22-near.json`): distribusi cadence (median 1 s, p95 5–6 s), Age (median 3–4 s, p95 ~50 s), rasio row berulang (~63%), position-only rows (~1%), empty/truncated row, format list-string Date/Time, campuran Tail, profil speed taxi ≤20 kt dari sequence N43AL/N728AM/N534ME. Hasil kalibrasi disimpan sebagai `calibration.json` (statistik saja, tanpa raw rows).
2. **Geometri KAGC ilustratif**: runway 10/28 dan 13/31, taxiway Alpha/Bravo/Charlie/Golf digitasi kasar dari airport diagram publik → `layout` lat/lon + local metric frame. Label `ILLUSTRATIVE_NOT_SURVEYED`, valid period tidak diketahui.
3. **Sintesis selaras audio** (`clock = metadata start 88.wav`, offset 0, uncertainty dicatat):
   - Objek A “Archer 147G” (ICAO sintetik, Tail campuran `N147G`/kosong): taxi di Alpha, berhenti dekat Charlie (0–43 s), setelah 52 s join Alpha → belok kanan Golf → melintasi runway 10/28 (~70–78 s) → berhenti sebelum hold line 13 (~88 s).
   - Objek B “Cessna eastbound”: bergerak berlawanan arah di Alpha menuju Charlie (0–35 s).
   - Noise posisi realistis, cadence/Age/duplikasi mengikuti kalibrasi, beberapa row position-only, satu gap >5 s agar trail tersegmentasi.
4. Validator: parse ulang dengan parser yang sama dengan backend; cek statistik sintetik berada dalam rentang kalibrasi; titik berada dalam bounds layout.

## 4. Backend `backend/flowlens_demo` (FastAPI + PostgreSQL)

Package terpisah dari foundation. Dependency tambahan di extra `demo` (`psycopg[binary]`, `python-multipart`, `numpy`), dijalankan di image Python 3.12 (host tidak memiliki 3.12/uv).

### 4.1 Skema DB (SQL migration sederhana, dijalankan saat startup)

| Tabel | Kolom utama |
| --- | --- |
| `workspaces` | id, name (unique, case-insensitive), scenario_id, status `PROCESSING/READY/FAILED`, duration_ms, created_at, processing_started_at, ready_at, label `MOCK` |
| `workspace_files` | workspace_id, role `AUDIO/ADSB`, original_name, size_bytes, sha256, detected (format/channels/rate/rows/ids) |
| `processing_steps` | workspace_id, key, label, order, planned_ms, status, detail_json |
| `transcript_segments` | workspace_id, seg_id, channel, start_ms, end_ms, available_ms, text, confidence, words_json, origin `STT_HYPOTHESIS` |
| `findings` | workspace_id, finding_id, category, priority, title, statement, event_ms, available_ms, pending_from_ms, evidence_json, slots_json, entity, provenance_json, status |
| `track_points` | workspace_id, entity_id, t_ms, x, y, lat, lon, speed_kt, heading, age_s, partial |
| `playback_state` | workspace_id, cursor_ms, updated_at |

### 4.2 Processing (MOCK, comprehensive, restart-safe)

Pada upload: langkah nyata dan murah dikerjakan langsung (hash, header WAV, parse CSV + statistik kualitas). Langkah “berat” disimulasikan dengan jadwal deterministik yang dihitung dari `processing_started_at` (tanpa background worker; status diturunkan saat dibaca, sehingga restart tidak merusak state). Total ±15 s:

1. Upload diterima & checksum diverifikasi (nyata)
2. Audio diperiksa: durasi, sample rate, channel (nyata)
3. ADS-B diparse: rows, ICAO IDs, cadence, Age, position-only, duplikasi (nyata pada CSV sintetik)
4. Clock alignment: offset dari metadata, uncertainty (MOCK, dijelaskan)
5. Waveform & derivative audio (nyata/precomputed)
6. Transcription: “replaying cached STT hypothesis — no provider call” dengan progres per chunk 0–50 s / 50–96,9 s
7. Intent & association (MOCK)
8. Findings rules (MOCK)
9. Workspace disimpan → status `READY` (data skenario disalin ke tabel per-workspace)

### 4.3 Endpoint (`/api/demo`, Vite proxy)

| Method | Path | Fungsi |
| --- | --- | --- |
| POST | `/workspaces` | multipart `name`, `files[]` → 201 workspace atau error ber-kode (unknown file, role kurang/ganda, checksum, nama duplikat, ukuran) |
| GET | `/workspaces` · `/workspaces/{id}` | Daftar & detail termasuk steps |
| GET | `/workspaces/{id}/timeline` | Transcript (words), findings (pending/available), tracks, layout, entities, markers, gaps |
| GET | `/workspaces/{id}/audio` | Derivative audio dengan HTTP Range (206) |
| GET | `/workspaces/{id}/waveform` | Peaks |
| PUT | `/workspaces/{id}/playback` | Simpan posisi terakhir |
| GET | `/health` | Liveness + DB check |

Batas upload, path sanitization, dan tanpa logging transcript/audio tetap berlaku.

### 4.4 Docker Compose lokal

`deploy/compose/local/compose.demo.yml`: service `db` (`postgres:16.x-alpine` pinned, volume bernama, healthcheck) dan `api` (`deploy/docker/backend/Dockerfile.demo`, mount read-only `data/demo-scenarios`, port 8000 hanya ke `127.0.0.1`). Credential via `.env.demo` (ignored) + `.env.demo.example`. Frontend tetap `vite dev` di host dengan proxy `/api/demo` → `127.0.0.1:8000`. Prasyarat: OrbStack/Docker daemon berjalan (saat diperiksa belum berjalan).

## 5. Frontend

### 5.1 Integrasi hybrid

- `src/api/adapters/http/demo.ts`: client fetch/XHR untuk endpoint demo.
- `CompositeApiClient`: id sesi berprefiks `ws_` diarahkan ke HTTP untuk `getSession`, `getWaveforms`, `getSnapshot`, `getTranscript`, `listFindings`, `getEvidence`; method lain melempar `NOT_AVAILABLE_IN_DEMO` → state “Not available for demo workspaces” (Memory, Debrief, Ask, Options, Metrics).
- Sessions list menggabungkan workspace backend (badge `MOCK · Backend`, status Processing/Ready) dengan 7 sesi MOCK lama. Backend tidak berjalan → callout “Demo backend not reachable” tanpa merusak sesi MOCK.

### 5.2 Import baru (tanpa source kind)

Langkah: **Files** → **Processing** → membuka workspace otomatis.
- Files: nama workspace (wajib, cek duplikat), dua slot (Audio · ADS-B) + dropzone yang mengenali peran dari ekstensi; upload multipart dengan progres byte nyata (XHR).
- Processing: daftar 9 langkah dengan status, progress bar, detail nyata (contoh “96.9 s · mono · 44.1 kHz”, “1 2xx rows · 2 ICAO IDs · cadence median 1 s · SYNTHETIC”), label MOCK per langkah simulasi, polling 500 ms. Sesudah `READY` → toast “Workspace saved” → navigasi ke workspace.
- Wizard MOCK lama (source kind, sample bundle, permission step) dihapus; permission/provenance ditampilkan read-only di ringkasan processing.

### 5.3 Workspace: audio, transcript, findings

- **Audio clock**: elemen `<audio>` menjadi master clock untuk sesi backend (rAF membaca `currentTime`); play/pause/seek/speed 0,5–2× (`playbackRate`, preserve pitch), state buffering/ended, volume/mute; badge “Visual replay · no audio” diganti kontrol volume. Posisi tersimpan ke backend saat pause (debounce).
- **Live transcript panel** (baru, di samping/di bawah Situation): kata muncul satu per satu pada `word.end + 300 ms` (interim, miring), segment menjadi final pada `segment.end + 900 ms` dengan confidence, speaker kandidat, label `STT hypothesis`; auto-scroll yang berhenti saat pengguna scroll; klik segment → seek. Kata confidence rendah ditandai. Seek mundur menyembunyikan lagi item yang belum available (as-known).
- **Findings progresif**: kartu “Analyzing…” muncul pada `pending_from_ms` (akhir ucapan pemicu), lalu kartu lengkap pada `available_ms` (±2–3 s kemudian) dengan animasi masuk. Kartu memuat statement, quote, slot table Said/Heard, entity candidate, data quality, label MOCK/SYNTHETIC, “Listen to evidence” (seek + play rentang). Rail diurutkan terbaru di atas; counter berubah; tanpa auto-focus/sirene (PRD §17.3).
- **Situation**: `SituationCanvas` diperluas untuk banyak runway poligon bebas, equal-aspect, taxiway berlabel, trail tersegmentasi pada gap, marker heading netral bila heading tidak ada, badge `SYNTHETIC · ILLUSTRATIVE LAYOUT`.
- **Timeline**: marker instruction/readback/finding mengikuti cursor; waveform dari backend.

### 5.4 Draft findings skenario (difinalisasi saat implementasi)

| # | Muncul (±) | Kategori / prioritas | Isi |
| --- | --- | --- | --- |
| F-01 | 8 s | Context · INFO | Traffic information: Cessna berlawanan arah di Alpha menuju Charlie; posisi Cessna (SYNTHETIC) tersedia |
| F-02 | 15 s | FND-01 · NOTICE | Respons “Bravo Alpha … hold short of Charlie on Alpha”: callsign hanya suffix → identity CANDIDATE |
| F-03 | 33 s | FND-06 · INFO | Segment conf 0,16 dan ±30 s tanpa teks: kemungkinan transmisi tidak tertranskripsi, bukan bukti radio diam |
| F-04 | 52 s | Revisi instruksi · ATTENTION | “Change of plans”: route sebelumnya (hold short Charlie) SUPERSEDED; callsign “Archer 147 Golf” vs “Bravo Alpha” perlu review |
| F-05 | 60 s | FND-01 · NOTICE | Instruksi crossing rusak (“Across from way…”); runway yang dilintasi tidak jelas; hold short 13 terbaca; boundary chunk 50 s |
| F-06 | 68 s | FND-02 · ATTENTION | Readback perlu review: Heard “cross runway 28” tidak terdengar jelas di Said; hold-short di Heard rusak (“…three”). Slot: action MATCHED, crossing AMBIGUOUS, hold-short AMBIGUOUS. **Bukan** mismatch pasti |
| F-07 | 80 s | FND-05 · INFO | Observed (SYNTHETIC): track melintasi 10/28 lalu berhenti sebelum hold line 13 — CONSISTENT candidate, dengan peringatan data sintetik |
| F-08 | 90 s | FND-06 · NOTICE | Data quality: ADS-B sintetik, layout ilustratif, timezone audio belum diverifikasi → conformance tidak tervalidasi |

## 6. Hapus open loop dari seluruh UI

Attention rail (tab + `LoopRow`), Memory object & Runway (bagian open loops), Debrief (section `OPEN_LOOPS` + brief), Metrics (kartu open loops), Sessions (copy), Help (glosarium), `lib/status.ts` (`LOOP_KIND_LABEL`, `STATUS.loop`, kategori), `components/ui/tabs.tsx` (contoh). Tipe contract `OpenLoop` dan data mock engine dibiarkan (kontrak beku) tetapi tidak dirender. Test Vitest dan `tests/e2e/frontend_mock` yang menyebut open loops diperbarui.

## 7. Urutan pekerjaan

1. ADR 0003 + rencana ini.
2. Siapkan aset: SCP `88.wav` + verifikasi SHA, derivative ffmpeg, kalibrasi ADS-B, `synth_adsb.py`, layout ilustratif, `build_scenario.py` → `scenario.json`.
3. Backend demo: skema, upload/deteksi, processing schedule, timeline/audio/waveform/playback, pytest.
4. Compose: Dockerfile, compose, env example; `docker compose up` + smoke.
5. Frontend: hapus open loop → HTTP adapter + composite → import baru → audio clock → live transcript → findings progresif → canvas multi-runway → sessions list hybrid.
6. Verifikasi dan dokumentasi (handoff, guide `docs/development/demoWorkspace.md`, demo script).

## 8. Verifikasi yang direncanakan

| Area | Checks |
| --- | --- |
| Aset | SHA raw = manifest; derivative durasi = raw ±10 ms; statistik ADS-B sintetik dalam rentang kalibrasi |
| Backend | ruff/mypy pada package demo; pytest terhadap Postgres disposable (compose project terpisah): deteksi nama/checksum, nama duplikat, file kurang/ganda, jadwal processing deterministik, restart di tengah processing, Range 206, timeline as-known |
| Frontend | typecheck, lint, copy guard, Vitest (reveal kata/segment per cursor, findings pending/available, seek mundur, audio clock store), build |
| Browser | Playwright: import → processing → workspace → play (autoplay flag) → transcript & findings muncul berurutan → seek → reload menyimpan posisi; screenshot; axe tanpa serious/critical; tidak ada open loop di UI |
| Compose | `config` valid, healthcheck, restart api tanpa kehilangan workspace |

## 9. Batasan yang tetap ditampilkan

Transkrip adalah hypothesis STT tanpa review manusia; findings di-author (MOCK), bukan output Gemini; ADS-B sintetik dan layout ilustratif sehingga Observed tidak membuktikan gerakan nyata; timezone dan alignment audio belum diverifikasi; tidak ada provider call baru; bukan validasi domain atau operasional.

## 10. Catatan implementasi (perbedaan dari rencana)

- Dependency demo ada di `backend/flowlens_demo/requirements*.txt` (image Docker), bukan extra `demo` di `pyproject.toml`; `uv.lock` tidak diubah. `numpy` tidak dipakai.
- Skema DB lebih sederhana: `processing_steps` diganti kolom jsonb `workspaces.step_details` (status langkah dihitung saat dibaca), dan `track_points` diganti salinan analisis di `workspaces.analysis` (jsonb) saat finalisasi. Tabel `transcript_segments`, `findings`, `workspace_files`, `playback_state` sesuai rencana.
- Frontend memakai port `DemoPort` (`src/api/demo.ts`, `useDemo()`) dan adapter `src/api/adapters/demo/` (client HTTP + hybrid client). Workspace READY didaftarkan ke engine MOCK dengan `registerExternal()` dan key spec unik per workspace.
- Transcript live: kata tampil 300 ms setelah selesai diucapkan; segmen final pada `end + latency` (900 ms). Findings: kartu "Analysing…" dari `pending` sampai `available`; finding baru ditandai "New" selama 5 s.
- Canvas situasi memakai mode geometri bandara saat layout memiliki `focus` (skala sama pada kedua sumbu, semua runway sebagai polygon, trail terputus pada gap feed > 5 s, heading dari data).
- Verifikasi: backend 16 pytest (Compose profile `test`), ruff/format/mypy bersih; frontend typecheck, lint, check:types, check:copy, 55 vitest, build; Playwright 16 journey (termasuk 2 journey demo baru) dengan Chrome lokal.


## 11. Pembaruan 12 Oktober 2026 — rekaman sebelum/sesudah

- Permintaan pengguna: tanpa concat file; rekaman (audio dan CSV) dapat ditambahkan sebelum/sesudah rekaman main lewat lane Before/After di Import awal (tombol tambah di workspace dihapus atas koreksi pengguna). Hanya 87.wav yang ditambahkan untuk sesi ini.
- Analisis 87.wav (Google STT): clearance taxi lengkap dan readback-nya terekam di 01:45–02:01; "Bravo Alpha" di 88 adalah rute, bukan callsign; hold short berubah dari RWY 28 ke "Charlie on Alpha" tanpa instruksi pengubah yang terekam (kemungkinan di gap 14 s).
- Transcript: lag kata 0,4 s (dari 300 ms); role tampil 0,4 s setelah final. §9 diganti: label MOCK/SYNTHETIC/simulation tidak lagi ditampilkan (pengecualian rules.md di ADR 0003).
- Verifikasi: backend 20 pytest; frontend typecheck, lint, check:copy, 55 vitest, build; Playwright 16 journey (journey demo: import 87+88 sekaligus → workspace 2 recordings → Skip → readback cocok, finding identitas tidak muncul; import 88 saja → finding identitas muncul).
