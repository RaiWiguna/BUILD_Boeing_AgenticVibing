# Private import staging dan preview — A04.1

Tanggal: 9 Oktober 2026. Profile host `imports-1`, shared contracts/ports tetap 1.0.0. Preview memeriksa bytes dan menghasilkan metadata/remediation; tidak membuat replay session, source, asset, job atau analysis run. Manifest/rights/clock normalization kini tersedia melalui [A04.2 metadata workflow](import-metadata.md); commit/promotion/source reader menunggu A04.3.

## Mengaktifkan service lokal

Set `FLOWLENS_DB_PATH` dan `FLOWLENS_IMPORT_STAGING_PATH` pada launcher [backend foundation](backend-foundation.md). Contoh path yang di-ignore:

```sh
FLOWLENS_DB_PATH=data/db/flowlens.sqlite3 \
FLOWLENS_IMPORT_STAGING_PATH=data/scratch/imports \
.venv/bin/python -m flowlens.cli.serve
```

Staging harus directory lokal terpisah dari directory DB, owner-only (0700), tanpa symlink pada path/ancestors. Service membuat root bila belum ada, tanpa melonggarkan permissions root yang sudah ada. Files opaque UUID memakai 0600; nama input hanya metadata ASCII, maksimum128 karakter. Exclusive POSIX lock berlaku sepanjang lifespan. Tanpa konfigurasi staging, import endpoints503; `/ready` tetap503/HOST_ONLY meskipun preview aktif. Account/bootstrap/login mengikuti [authentication](authentication.md).

## HTTP dan authority

`POST /api/v1/imports` menerima multipart file parts bernama `audio`, `events`, `tracks`. Required `Idempotency-Key`: ASCII1–128 karakter `[A-Za-z0-9_.:-]`. Cookie human aktif, exact Origin dan CSRF wajib menurut [transport policy](transport-policy.md). Pembuat draft harus admin aktif; evaluator tidak memiliki global import grant pada baseline ini. Admin lain tetap tidak dapat membaca draft milik orang lain. Authority diperiksa saat mulai, saat finalisasi, dan saat GET; logout/reset/expiry dapat menggagalkan upload sebelum finalisasi.

Response201 adalah `ImportPreview`: draft ID, expiry, file IDs/names/profile/hash/size, audio channels/sample rate/frames/duration, sidecar row counts, `tracks_present`, `clock_alignment=UNKNOWN`, `layout_status=UNKNOWN`, `rights_status=UNDECLARED`, dan issues. Accepted preview tetap `NEEDS_REMEDIATION`: rights declaration blocking; clock/layout gaps nonblocking untuk preview namun capability terkait belum tersedia. Tidak ada source payload, storage key/path, waveform atau truth dalam response.

`GET /api/v1/imports/{id}` membaca metadata untuk owner, memeriksa file private size/hash kembali dan menolak expired draft. Tidak ada media download atau commit endpoint. Invalid input422 `INVALID_IMPORT` dengan field/code/row aman; user bytes/path tidak direfleksikan. Correction: perbaiki file/profile sesuai issue lalu upload ulang dengan key baru; same key dengan payload berbeda409. Identical scoped retry mengembalikan preview semula dan membuang staging kandidat baru. Expired receipt tetap ditolak termasuk retry POST. Ini receipt draft, bukan content dedup atau import commit A04.3. Semua response/error API `no-store`.

## Versioned input profiles

| Role / profile | Accepted input |
| --- | --- |
| audio / canonical-audio-wav-1 | RIFF/WAVE lengkap; PCM_U8/16/24/32, FLOAT/DOUBLE; full decode, finite samples |
| audio / canonical-audio-flac-1 | FLAC dengan STREAMINFO valid; full decode dan exact reported frame count |
| events / canonical-events-json-1 | Canonical frozen SourceEvent1.0.0 object atau array; TRACK harus memakai role tracks |
| events / canonical-events-jsonl-1 | Satu canonical SourceEvent per nonblank UTF-8 line |
| tracks / canonical-tracks-json-1 | Canonical frozen Track1.0.0 object atau array |
| tracks / canonical-tracks-csv-1 | Seluruh kolom Track selain optional schema_version, plus explicit `units=m`; UUID/enums/time fields canonical, numeric casts eksplisit, optional IDs/available_time dapat blank |

Declared MIME harus sesuai extension/profile atau `application/octet-stream`; content magic/container/schema tetap diperiksa. WAV RF64/ZIP/compressed audio/unknown sidecar columns atau formats ditolak. JSON duplicate keys, NaN/Infinity/overflow floats, duplicate record IDs, malformed rows, private/truth DTOs dan impossible >signed64 millisecond fields ditolak. Error sidecar membawa row number bila diketahui. Profile hanya memvalidasi input canonical; tidak menebak timezone, IDs, units, alignment, coverage atau layout. Missing tracks tetap absent; valid rows belum menunjukkan paired alignment/coverage.

## Batas resource dan recovery

Default service limits: file2GiB, aggregate4GiB, sidecar64MiB, whole JSON8MiB, audio2jam/file, rate8–192kHz, maksimal2 channels total (hingga2 audio parts),1 events,1 tracks,4 files,200k rows/sidecar. File size dapat menjadi batas yang lebih kecil daripada duration pada encoding/rate tertentu. Ada4 concurrent upload slots,100 drafts global/16 per-owner; retry existing key mendapat kandidat sementara terbatas slots. Limits adalah engineering baseline yang dapat diinjeksi dengan ImportLimits; environment limit tuning belum tersedia. Bukan hasil performance/capacity benchmark.

Custom multipart parser mengirim bytes langsung ke private fd, tanpa framework global temp spooling. Body dibatasi total+1MiB framing, headers8/part dan2KiB/header, whole-request timeout600s. SHA-256 streaming, optional part header `X-Content-SHA256` lowercase hex64, file fsync dan hash ulang sesudah inspection. Traversal termasuk raw Windows paths ditolak sebelum multipart compatibility parser menghapus path.

Audio decode memakai subprocess dengan fixed argv/pass_fds, no shell, environment minimal tanpa host secrets, CPU/wall timeout60s dan buffer8192 frames. WAV chunks dibatasi128 dan16MiB per non-data chunk; FLAC metadata128 blocks/16MiB total. Non-Darwin child mencoba RLIMIT_AS512MiB. Supported macOS runtime menolak memory rlimit, sehingga hard memory ceiling tidak tersedia di sana; byte/metadata/frame/buffer/CPU/wall controls tetap berlaku. Subprocess ini bukan sandbox filesystem/network. Decode throughput/full-size input dan Linux memory-limit behavior belum dibenchmark/diverifikasi. [SoundFile documentation](https://python-soundfile.readthedocs.io/en/latest/index.html) menjelaskan buffer decode API; versions aktual dicatat pada evidence.

platform.0008 hanya menyimpan owner/key digest/fingerprint/status/expiry/preview draft. Startup dengan exclusive lock membersihkan interrupted UPLOADING, expired drafts dan canonical UUID orphan dirs; accepted valid previews bertahan restart. Runtime GET expiry tidak menghapus files; reclaim TTL saat restart, continuous retention maintenance belum tersedia. Failed uploads dibuang, tidak menjadi sesi half-readable. Raw accepted bytes tidak ditransformasi. File fsync bukan klaim transaksi atomik DB+FS atau directory promotion durability; recovery/promotion/commit fault handling lengkap milik A04.3. Jangan menghapus root/lock ketika service aktif.

[Evidence A04.1](../testing/a041-evidence.md) dan [ADR](../adr/0003-private-import-staging.md). No provider transfer, real B integration, frontend atau deployment.

A04.2 menambahkan metadata revision/current GET projection dan immutable POST/GET metadata. Field UNKNOWN/UNDECLARED di atas menjelaskan initial upload receipt; current preview memakai declaration terbaru, dengan rights DECLARED terpisah dari ALLOWED. Tidak ada domain commit.
