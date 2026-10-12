# Demo Workspace Track dengan Backend Python + PostgreSQL

| Atribut | Nilai |
| --- | --- |
| Status keputusan | Accepted — track demo, bukan G-BE |
| Tanggal | 12 Oktober 2026 |
| Status implementasi | Diimplementasikan lokal; tests lulus (lihat [panduan](../development/demoWorkspace.md)); tidak di-deploy |
| Ruang lingkup | Satu skenario: TartanAviation KAGC `88.wav` (main) + `87.wav` opsional sebelumnya, masing-masing dengan ADS-B sintetik |

## Context

Pengguna meminta demo yang bisa diputar ujung ke ujung: import sesi tanpa memilih source kind, dua file (audio dan ADS-B), processing yang terlihat lengkap, workspace tersimpan dengan nama dari pengguna, audio yang benar-benar diputar, transcript yang muncul bertahap dengan delay alami, findings yang muncul selama playback, tanpa open loop, dan backend Python + PostgreSQL lewat Docker Compose lokal.

Permintaan ini bertentangan dengan beberapa aturan aktif:

1. PRD/rules menetapkan SQLite single-writer; demo memakai PostgreSQL.
2. FR-01 mewajibkan source kind saat import; demo menurunkannya dari skenario yang dikenali.
3. Frontend belum boleh memanggil backend sebelum G-BE; demo memanggil `/api/demo`.
4. Keputusan D-3 (replay visual-only, tanpa audio); demo memutar audio nyata.
5. Tidak ada ADS-B KAGC pada hari rekaman 88.wav; demo memakai CSV sintetik yang dikalibrasi pada data Agustus 2022 dan diselaraskan ke narasi audio.

## Decision

Bangun **track demo terpisah** yang tidak menggantikan kontrak produk:

- Package `backend/flowlens_demo/` (FastAPI + psycopg3, SQL biasa) terpisah dari `backend/flowlens/`. Ia hanya menyimpan workspace bernama, mengenali file berdasarkan nama + SHA-256 + ukuran, menjalankan jadwal processing MOCK yang deterministik dan restart-safe (diturunkan dari waktu sejak `processing_started_at`, tanpa worker), lalu menyajikan analisis yang sudah disiapkan dan audio dengan HTTP Range.
- Compose `deploy/compose/local/compose.demo.yml` (project `flowlens-demo`): `db` PostgreSQL 16 tanpa port publik, `api` di `127.0.0.1:8000`, profile `test` untuk pytest pada database `_test`.
- Frontend memakai **hybrid client**: sesi MOCK seed tetap in-browser; workspace READY dari backend didaftarkan ke engine MOCK dengan UUID backend, sehingga Workspace/Memory/Review/Debrief membaca lewat port `ApiClient` yang sama. Layar memakai port `DemoPort` (`useDemo()`), bukan import adapter.
- Audio element menjadi master clock replay untuk workspace demo. Sesi MOCK tetap visual-only (D-3 tetap berlaku untuk mereka).
- Open loop dihapus dari seluruh UI dan data MOCK sesuai permintaan pengguna. Kontrak generated (`contracts.ts`) tidak diubah.

## Rationale and Alternatives

Menulis demo ke `backend/flowlens` akan mencampur SQLite/contract gate dengan Postgres dan data authored, sehingga ditolak. Membuat ulang seluruh layar sesi untuk HTTP juga ditolak karena besar dan menduplikasi logika as-of; mendaftarkan spec ke engine MOCK memberi semua layar dengan perubahan kecil. Upload yang diproses ulang secara nyata (STT/Gemini) ditolak: demo harus berjalan offline, deterministik, dan tanpa provider call.

## Implementation Details and Consequences

- **Pengecualian rules.md (label provenance di UI).** Atas permintaan pengguna (12 Oktober 2026), label MOCK, SYNTHETIC, simulation dan teks penjelas arsitektur/operasional dihapus dari seluruh UI (sesi seed maupun demo), mengikuti skill concise-ui-typography. Yang dipertahankan: disclosure wajib (AI interpretation, "Automatic · unreviewed" pada transcript, "not an operational chart" pada layout, Unknown/Not recorded). Status sebenarnya tetap: audio PUBLIC_CORPUS, transcript STT hypothesis, ADS-B sintetik, layout ilustratif, findings authored (bukan detector), NOT_DOMAIN_VALIDATED — dicatat hanya di ADR ini dan panduan demo. Source kind SYNTHETIC tetap ada di data/kontrak, hanya tidak dirender.
- Panel kontrol skenario developer disembunyikan kecuali `localStorage['flowlens.devtools'] === '1'` (dipakai Playwright).
- **Multi-recording.** Skenario v2 punya `parts` (87 before, 88 main) dan `variants` per kombinasi file. Rekaman sebelum/sesudah hanya ditambahkan saat import awal: lane Before/Main/After (field `positions`). Endpoint backend `POST /api/demo/workspaces/{id}/files` (tambah ke workspace yang ada) tetap ada dan teruji, tetapi tidak dipakai UI atas keputusan pengguna. Gap antar rekaman (14 s) dirender sebagai "Not recorded", tidak pernah diisi. Audio per rekaman disajikan lewat `GET /audio/{part}`; frontend memakai satu elemen audio per rekaman dengan rekaman aktif sebagai master clock. Transcript 87 berasal dari Google STT (4 request, key hanya lewat env sementara, tidak disimpan).
- Workspace dan Sessions tidak lagi menampilkan "Illustrative layout", "not an operational chart" atau label fictional (permintaan pengguna 12 Oktober 2026); layout KAGC tetap skematik dan layout seed tetap fiktif — dicatat di sini saja. Highlight memakai bahasa operasional (field `live`, fakta saja, jam UTC) tanpa mengubah statement analitis di Review/Debrief.
- Transcript tampil per kata dengan lag 0,4 s; role pembicara tampil 0,4 s setelah segmen final.
- File upload dibuang setelah dicek; server memakai aset kanonik di `data/demo-scenarios/` (di-ignore Git, diambil lewat `scripts/demo/fetch_scenario.sh`).
- Tidak ada credential provider yang dibutuhkan atau disimpan.
- Konsekuensi: track ini harus dihapus atau dimigrasikan saat G-BE menyediakan adapter HTTP sungguhan. Ia tidak menutup G-BE, G-FE, atau G-DELIVERY, dan tidak mengklaim kesiapan operasional.


## Expansion terpisah — 12 Oktober 2026

Demo catalogue diperluas dengan lima main recordings (50, 51, 47, 156, 123), standalone; 50 eligible sebagai satu before untuk 51. New-only builders/fixtures, scoped scenario selection, per-case side limits dan additive catalogue API digunakan. Shared production contract/database/provider policy tidak berubah. Existing 87/88 assets, build, variants, timing dan findings tidak diregenerasi atau diubah. Case baru memakai cached hypotheses dan authored centre-point tracks, tanpa provider call; physical conformance tetap NOT_EVALUABLE. Detail/evidence: [completion record expansion](../development/demoScenarioExpansionPlan.md) dan [panduan](../development/demoWorkspace.md). Ini local demo, bukan G-BE/G-FE atau domain validation.
