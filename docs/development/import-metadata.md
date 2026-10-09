# Import metadata, rights dan normalization — A04.2

Tanggal: 9 Oktober 2026. Profile `source-metadata-1`, envelope `prepared-import-1`, clock adapter `clock-normalization-1`. Shared contracts/ports1.0.0 dan dependency lock tidak berubah. Ini kelanjutan [private staging A04.1](import-preview.md), belum domain commit/source reader A04.3.

## API dan revisi

Setelah upload, owner admin aktif mengirim JSON ke `POST /api/v1/imports/{id}/metadata`. Body mempunyai `expected_revision` (0 untuk pertama) dan `declaration`. Cookie/Origin/CSRF serta `Idempotency-Key` ASCII1–128 mengikuti upload policy. Body maksimal1MiB, receive timeout60s; file parsing/hashing memakai batas A04.1. `GET /api/v1/imports/{id}/metadata` membaca revisi terbaru, optional `?revision=1` untuk histori. OpenAPI host memuat schema Declaration/PreparedImport dan request body; bukan perubahan shared generated contracts.

POST201 menghasilkan envelope dengan declaration original, file bindings, hashes, normalized layout/identities/sidecar summaries, provisional frozen SourceManifest bila hak lokal dan retention diketahui, serta issues. `PREPARED` hanya kesiapan metadata untuk langkah commit; tidak menunjukkan session READY, analysis readiness atau validasi domain. Local eligibility tidak membutuhkan cloud permission atau alignment lengkap. Local denied/undetermined atau retention unknown → `NEEDS_REMEDIATION`, `manifest=null`, blocking issues. Semua output tetap `NOT_DOMAIN_VALIDATED` pada manifest.

Setiap koreksi menghasilkan immutable revision baru; maksimal64 revisions/draft. Same scoped key/request/expected_revision mengembalikan receipt pertama, termasuk setelah revisi berikutnya; changed payload409 `IDEMPOTENCY_CONFLICT`, stale new key409 `VERSION_CONFLICT`. Human authority/owner/expiry serta staged hash diperiksa sebelum receipt. GET import preview kini menampilkan `metadata_revision`, rights `DECLARED`, alignment `KNOWN/UNKNOWN`, layout `DECLARED/UNKNOWN` dan issues revisi terbaru. Receipt POST upload tetap inspection snapshot pertama; GET adalah current view. `DECLARED` tidak sama dengan `ALLOWED`.

platform.0009 menyimpan draft/revision/actor/key digest/request hash/content hash/server UTC time/envelope dalam satu UOW. Update/direct delete/replacement ditolak SQL triggers. Draft expiry cleanup menghapus metadata melalui FK cascade; ini journal scratch yang mengikuti TTL draft, bukan durable committed-source audit atau forensic log. Valid metadata bertahan restart; upgrade0008→0009 mempertahankan files/preview. No replay sessions/source/assets/jobs/runs dibuat.

## Declaration yang eksplisit

| Field | Semantik |
| --- | --- |
| source_kind/label/owner/identifier | SYNTHETIC, ROLEPLAY, PUBLIC_CORPUS atau PARTNER_REPLAY; ownership/identifier deklaratif, bukan bukti izin mitra |
| dataset/version/subset | Optional provenance; public corpus wajib dataset/version; tidak mengunduh sumber |
| rights | Local, cloud_audio, cloud_context, reviewer, export, audio_export masing-masing ALLOWED/DENIED/UNDETERMINED; basis wajib |
| retention | FIXED_DAYS dengan explicit days1–36500 dan basis, atau UNDETERMINED tanpa days; tidak ada inferred/default/indefinite policy pada profile ini |
| files | Tepat seluruh staged file IDs/SHA; per-file clock; audio channel labels sesuai decoded count, sidecar channels kosong |
| coverage | Vehicles/speaker_identity nullable, gaps dalam explicit session milliseconds; non-null claims/gaps memerlukan basis; gaps tidak boleh overlap |
| identities | Source entity ID, full callsign/aliases, effective session TimeRange, staged evidence file/source_event_ids; entity UUID hasil normalization dibatasi import namespace |
| layout | Explicit LOCAL_CARTESIAN m/ft, version, positive validity TimeRange, uncertainty, runway polygon vertices tanpa repeated closure, named hold-line pairs |

Track/audio presence diambil dari staged facts. Absence tidak diisi `vehicles=false`, speaker known, runway clear atau clock0. Vehicles=true tanpa tracks ditolak; speaker_identity=true ditolak `SPEAKER_MAPPING_REQUIRED` karena canonical profile ini belum mempunyai speaker evidence adapter. Callsign mapping bukan speaker/pilot identity, dan radio channel bukan diarization proof. Nonblocking gaps tidak menghalangi local preparation, tetapi paired status tetap NOT_EVALUABLE.

## Rights dan kompatibilitas 1.0.0

`ImportMetadata.require_right(token, draft_id, action)` melakukan fresh owner/authority/file checks dan membaca metadata terbaru. Historical envelope `require_right` hanya memeriksa declaration tersebut; jangan memakainya untuk current authorization. Semua actions memerlukan local ALLOWED serta fixed retention; audio export memerlukan export dan audio_export sekaligus. Unknown fail closed. Tests membuktikan cloud_audio ALLOWED tidak memberikan cloud_context/export, dan revisi denial memblok preflight meskipun receipt lama masih dapat dibaca sebagai histori. Tidak ada provider call atau worker/lease integration di unit ini; actual dispatch/result gates tetap A06.

Frozen Permissions hanya mempunyai satu cloud flag, sehingga projection `cloud=true` memerlukan kedua cloud categories ALLOWED. Frozen local read juga memerlukan reviewer ALLOWED agar source projection tidak memberikan akses reviewer yang ditolak; owner local preparation tetap terpisah. Full envelope harus dipertahankan oleh commit/source owner berikutnya, bukan diganti dengan projection yang kehilangan granular rights/provenance. Individual session/raw-audio/export grants tetap terpisah dari source rights.

## Clock, identity dan units

UNKNOWN mapping menyimpan offset/uncertainty/drift null. Declared offset/linear memerlukan offset, uncertainty, method, basis dan reviewer; linear memakai drift ppm eksplisit dalam ±1000 profile bound. Per-source relative time menggunakan Decimal dengan nearest-ms half-up: `source_ms + offset + source_ms * drift_ppm / 1_000_000`. Signed64 overflow atau normalized negative time ditolak, tidak dipotong ke0. Source timestamps/recorded_at/available time dipertahankan; unknown historical available time tetap null. No processing-time substitution. Ini declared calibration, bukan validasi alignment fisik.

Standalone wall-time adapter `source_timestamp_ms(raw, timezone, utc_origin, fold=...)` memakai IANA timezone, exact millisecond precision dan UTC origin. Explicit offset harus sesuai declared timezone; ambiguous DST perlu fold eksplisit, nonexistent local time ditolak. Canonical staged JSON/JSONL/CSV sudah membawa relative ms dan UTC recorded_at; profile ini tidak menerima arbitrary wall-time columns atau menebak source adapters. Original timezone dan per-file mapping disimpan dalam declaration. Frozen ClockMapping tidak mewakili drift: linear mapping diproyeksikan sebagai unknown, sementara full mapping tetap tersedia di envelope; cross-source consumers wajib memakai adapter penuh.

Sidecar inspection menggunakan parser strict A04.1 yang sama, lalu streaming normalization metadata: raw IDs/times/hash/recorded_at tetap tersedia pada helper, stable import-scoped record/entity UUIDs, min/max normalized times, null availability/identity/layout counts dan digest. Incoming analysis-run scope, mixed session/revision atau per-file source/hash, duplicate source_event_id, missing/conflicting identity evidence serta track/layout version mismatch ditolak. Mapping hanya diterapkan ketika event time berada dalam effective interval; ambiguous overlapping callsign/aliases ditolak. Current summaries tidak memasukkan source text atau menjadi worker/domain records.

Local layout feet→m memakai explicit0.3048 factor untuk coordinates/uncertainty/hold lines; declaration raw tidak berubah. Canonical tracks sudah metres, tidak dikonversi ulang. Unknown units, lat/lon/other CRS, degenerate/self-intersecting polygons dan invalid hold lines ditolak; geographic projection belum tersedia. Geometry calculations/footprint conformance tetap unit geometri owner. `paired_status=METADATA_COMPLETE` berarti clock/layout/identity metadata tersedia untuk records, bukan EVALUATED atau safety verdict; uncertainty thresholds, coverage sufficiency, stale tracks dan domain checks belum dilakukan.

## Integrity, errors dan limits

Content hash berasal dari canonical sorted staged file facts tanpa opaque file IDs; declaration hash dari canonical JSON declaration; manifest hash mencakup seluruh normalized envelope, reserved IDs, revision dan server declaration time. Hashes diverifikasi pada round-trip. Hash bukan legal consent atau cryptographic attestation terhadap privileged database/file replacement. Source/session IDs hanya reserved UUIDs; belum ada corresponding domain rows.

Invalid metadata422 mempunyai bounded safe field/code issues (hingga8), termasuk UNKNOWN_UNITS/INVALID_CLOCK/INVALID_HASH/UNSUPPORTED_COORDINATE_SYSTEM; values/path/exception context tidak direfleksikan. Sidecar errors mempertahankan role/row bila diketahui. Source-specific read/finalize/receipt checks menolak revoked/expired/tampered draft. Normalization limits:4 files,1000 entity mappings,32 aliases/evidence references per mapping,128 polygon vertices,32 hold lines,256 gaps,200k rows/sidecar,64 revisions. Ini profile engineering bounds; full-size throughput/parent memory/concurrent metadata capacity belum dibenchmark. Staging/native decoder limitations A04.1 tetap berlaku.

[Evidence A04.2](../testing/a042-evidence.md). Next A04.3 harus menerapkan full envelope ke immutable committed sources, promotion/dedup/conflict, source ports dan fault recovery; jangan membuka media/provider/worker input dari draft ini.
