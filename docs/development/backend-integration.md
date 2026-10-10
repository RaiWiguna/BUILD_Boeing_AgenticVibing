# Integrasi lokal A/B

10 Oktober 2026, `feat/backend`, input `3917b1614be90e990419ab85edbef1d74e6bc155`.
Candidate hasil pekerjaan adalah commit pembawa dokumen ini:
`git log -1 --format=%H -- docs/development/backend-integration.md`.

Composition root `flowlens.integration.create_integrated_host` dipakai launcher
`flowlens.api.serve`. API A tetap satu pemilik SQLite; B memperoleh repository
melalui UOW yang memeriksa context/grant/revision/current rights. Worker audio B
menggunakan HTTP, tanpa database. Frozen wire DTO/ports/schema contracts1.0.0
serta 18 migration A dan empat migration B sebelumnya dipertahankan.
`analysis.0005` menambahkan ledger projection publik dan sealed private intent
submission; total 23 migrations. Inventory exact tabel B dipakai retention dan
maintenance; unknown tables/ledger tetap ditolak.

## Menjalankan

Python3.12, `uv sync --locked`, FFmpeg/ffprobe9 tersedia. Gunakan direktori privat
absolut, tanpa symlink, terpisah untuk database/import/raw/artifact/journal. Journal
harus berada di luar roots yang direstore. Jangan membuka dua API writer atau
maintenance saat API aktif. Konfigurasi mengikuti [operability](operability.md)
dan [recovery](recovery.md).

```sh
# Bootstrap sekali sebelum API; password diminta lewat terminal, tidak lewat argv.
.venv/bin/python -m flowlens.cli.bootstrap_admin --integrated \
  --database /absolute/private/db/state.sqlite --login administrator

# Set FLOWLENS_DB_PATH ke database di atas dan seluruh roots privat berikut.
# FLOWLENS_PROFILE=development, FLOWLENS_API_WORKERS=1
# FLOWLENS_IMPORT_STAGING_PATH, FLOWLENS_RAW_ASSETS_PATH,
# FLOWLENS_ARTIFACT_STAGING_PATH, FLOWLENS_RETENTION_JOURNAL_PATH
.venv/bin/python -m flowlens.api.serve
```

Login/change-password, import preview/metadata/commit, grants dan source rights
mengikuti [authentication](authentication.md), [authorization](authorization.md),
[import](import-commit.md), serta [durable jobs](durable-jobs.md). Browser session
cookie tetap wajib; mutations memerlukan Origin/CSRF. Status integrasi terautentikasi
ada pada `GET /api/v1/integration-status`. Local platform `/ready` dapat200 setelah
storage/coordinator sehat; response ini tidak mengesahkan provider atau G-BE.
Production profile tetap ditolak. Tanpa database, host scaffold tetap tersedia.

Stage AUDIO memakai config `flowlens.integration.audio.AUDIO_CONFIG`, hak local,
satu leased source asset, reservation0 dan policy `integration-audio-1`.
Buat run AUDIO melalui endpoint jobs A, provision worker dan simpan token `wrk_`
di file owner-only600 di luar repo. WorkerConfig JSON owner-only600 berisi worker_id
UUID dan scratch_root absolut canonical yang sudah ada, mode700 tanpa symlink. AudioLimits default harus
cocok dengan config server (maksimum input per asset60menit/dua kanal/512MiB;
chunk50detik/overlap1detik/PCM16mono16kHz). Ini limits source, bukan pengukuran
kapasitas gabungan baru.

```sh
.venv/bin/python -m flowlens.workers.audio --api http://127.0.0.1:8000 \
  --config /absolute/private/worker-config.json \
  --token-file /absolute/private/worker-token --once
```

API internal memakai Bearer worker scoped. Lease/context/heartbeat/cancel,
range download, artifact upload dan result receipt tetap endpoint A. Binding baru
`POST /internal/analysis/audio-input` memeriksa active AUDIO lease, source rights,
clock/gaps dan config. Provenance JSON privat diverifikasi terhadap job/attempt,
input/config/source hashes, clock, chunks, rates/channel/ranges dan artifacts yang
benar-benar diperiksa A. Invalid result tidak mempromosikan artifacts.

## Alur analysis tanpa provider

Dalam profile `test` saja, config `flowlens.integration.engine.CONFIG` mengaktifkan
STT/INTENT/FINDINGS/BRIEF dengan model `MOCK`. Profile development menolak lease
analysis tersebut karena provider belum dikonfigurasi; AUDIO tetap dapat berjalan.
Tidak ada worker palsu otomatis yang menghasilkan transkripsi di development.
Fixture acceptance menggunakan real API/SQLite dan logic B, dengan normalized
transcript/candidate sintetik. Reproduksi seluruh alur:

```sh
.venv/bin/python -m pytest tests/platform/test_integration.py -q
```

STT JobResult normalized memakai frozen TranscriptSegment. Private intent dikirim
ke `POST /internal/analysis/intents`, codec `intent-submission-1`, berisi JobResult,
satu Candidate B dan Provenance. Payload immutable per attempt; API memeriksa
projection/evidence/lexical grounding dan authority lalu coordinator memberikan
receipt atomik. Tidak ada text field untuk menyelundupkan private payload.
`POST /internal/analysis/prepare` menerima active frozen JobLease FINDINGS/BRIEF,
menjalankan reducer/assembler/render B dan mengembalikan output frozen yang harus
sama ketika di-commit melalui `/internal/jobs/{job_id}/results`.

Worker mode DEBRIEF dibekukan pada server StagePolicy dan fingerprint; client tidak
bisa memilih mode atau truth capability. Ini memungkinkan unknown available_time
untuk batch offline; human AS_KNOWN tetap menyembunyikannya. Speaker/model role
bukan identitas authoritative: mapping belum tersedia dipertahankan UNKNOWN dan
coverage false. Private critical slots/provenance tetap lengkap pada B ledger;
public projection hanya memuat field frozen yang kompatibel.

Human records/snapshot memakai run/revision/as-of/mode dan evidence A. Advisory
routes berada di `/api/v1/sessions/{session_id}/analysis-runs/{run_id}/advisory`:
GET inventory; POST `/{document_id}/reviews`; GET `/{document_id}/report` dengan
format JSON/CSV/HTML. Review membutuhkan grant review, expected_version dan
Idempotency-Key; actor ditentukan server. Ekspor membutuhkan grant export dan
source rights pada manifest serta policy terbaru; body tidak dapat menaikkan izin.
B ReportRenderer mengerjakan escaping/redaction. Attachment CSP sandbox/no-store
bersifat ephemeral; tidak membuat durable EXPORT job atau report artifact baru.
Review tidak mengubah clearance atau fakta source.

## Registrations dan batas

[Manifest](backend-integration.json) memuat routes, input/source hashes, migrations,
repository/table inventory dan checks. Snapshot B terpasang pada Replay A; purge
menghapus semua row session kedua paket berdasarkan inventory exact. Backup/restore
mengenali catalog gabungan, tetap local private unencrypted dan memakai current
external tombstone. Restore mematikan credential/active jobs lama; review ulang
akun/grants sebelum promotion.

Google STT dan Gemini **NOT_CONFIGURED/NOT_VERIFIED**; credential/API key tidak
dimasukkan, cloud calls0. Source adapter SDK B tetap tersedia dari pekerjaan
sebelumnya, namun account/profile/worker binding nyata, provider smoke dan benchmark
kualitas harus dikerjakan ketika akses tersedia. Memasukkan key saja belum menjadi
bukti pipeline provider berjalan. Raw STT/correction private B tables sudah
registered; ingest SDK raw dan correction/reanalysis route ke host belum diekspos
oleh slice normalized acceptance ini. Worker hanya menerima normalized frozen
transcript pada batas A. QueryAnswer/Option generation, durable EXPORT stage,
source-alert/geometry signal bridge ke B Inputs dan authoritative speaker mapping
belum diekspos oleh routes integration ini; tidak ada placeholder yang mengaku
menjalankannya. A geometry/rules/replay dan B standalone implementations tetap ada.

S01–S12/domain/held-out/provider timing/capacity gabungan belum mendapat acceptance
baru dari test alur ini. Benchmark A10 historical berlaku pada candidate A, tidak
diubah menjadi benchmark gabungan. G-BE `not_started`; Phase10 penuh belum selesai.
Tidak ada frontend/container/deployment atau operational validation. Next: pasang
approved provider profile dan worker transport raw, mapping/source-signal/query-option
adapters, jalankan full scenario/quality/capacity serta contract/client freeze dalam
pekerjaan G-BE yang terpisah. Tidak memerlukan perubahan frozen contracts diam-diam.
