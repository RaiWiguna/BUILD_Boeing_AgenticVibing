# ADR 0003 — Controlled local audio preparation

Status: accepted design; implementation checks recorded separately. Tanggal: 9 Oktober 2026.

## Context

Raw audio harus immutable; setiap derivative mempertahankan hubungan channel,
sample boundaries, source clock dan unknown alignment. Decoder adalah proses
eksternal yang menerima file tidak tepercaya. Worker tidak memiliki database atau
raw inventory unrestricted; platform tetap memiliki authorization dan promotion.

## Decision

Paket B menyediakan pure frame planner, local immutable records, fixed FFmpeg/
ffprobe adapter dan context-managed private scratch preparation dalam `audio/`.
Source adalah authorized local file di trusted private root; salinan terbatas dan
terverifikasi hash menjadi satu-satunya decoder input. Root scratch terpisah dari
raw root, dengan generated filenames dan exclusive creation. Tidak menerima URL,
playlist, arbitrary command/filter, evaluator truth atau provider payload.

Self-contained WAV/FLAC/MP3/AIFF dibatasi magic bytes, format/protocol whitelist,
single audio stream, finite consistent duration/rate/channels dan zero media start
timestamp. Nonzero start/discontinuous media membutuhkan mapping adapter lanjutan,
bukan dinormalisasi diam-diam. PCM16 decoded mempertahankan urutan channel;
chunks mono memakai indeks channel zero-based tanpa inferensi identitas pembicara.

Planner memakai half-open frame boundaries. Source gaps di-round keluar ke output
sample grid dan memutus coverage. Overlap hanya terjadi dalam coverage segment.
Clock offset/uncertainty/version dipertahankan; null tetap unknown. Chunk capacity
adalah minimum 50 detik dan kapasitas byte WAV efektif; header dan overlap ikut
jumlah byte total. Default 16 kHz/mono per chunk, configurable dalam bounds lokal.

Subprocess langsung memakai argument list, shell false, stdin DEVNULL, bounded
stdout streaming, discarded stderr, wall timeout, kill/wait dan joined drain threads.
Satu thread decoder dan maximum single allocation 64 MiB membatasi resource awal;
ini bukan OS total-memory quota. Semua error memakai safe codes. Preparation hanya
yield setelah semua output/hash/accounting valid; context exit menghapus scratch.
Tidak ada accepted-result promotion, registration handler atau worker lifecycle.

## Rationale dan alternatives

Full PCM scratch membuat frame accounting dan pemisahan channel deterministik,
tanpa codec seek berbeda per chunk. Direct per-chunk compressed seeking lebih hemat
disk tetapi memerlukan validasi decoder delay/seek yang lebih luas. Unrestricted
FFmpeg input/filter ditolak karena memperluas akses file/network/command. DB access
di executor bertentangan dengan ownership API. Streaming cloud tidak dibutuhkan
untuk preparation offline ini.

## Consequences, risks dan validation

Full PCM plus overlap derivative memakai disk yang dihitung dalam output budget;
input snapshot menambah paling banyak satu input-size budget. Trusted caller harus
menyediakan root privat dengan ACL yang benar (Windows ACL tidak dibuat adapter).
Checks path/hash bukan sandbox terhadap hostile concurrent filesystem owner.
Metadata memakai exact frame/rate pairs; millisecond float adalah tampilan rasio,
source frame bounds adalah enclosing bounds setelah resampling.

Frozen contracts1.0.0 tidak berubah. Real B02.1 smoke kini lulus menggunakan
verified local FFmpeg9.0.2; [evidence](../testing/b021-evidence.md) merekam versions,
checksums/accounting. Transcript overlap dedup tetap B03.

## Worker boundary clarification — 9 Oktober 2026

Isolated AudioWorker memakai frozen JobClient/AssetAccess; internal InputAccess
yang disuntikkan trusted composition membawa minimal authorized metadata yang belum
ada pada JobLease. Tidak menambah wire field ataupun raw inventory access. Monitor
thread heartbeat/cancellation/deadline selama processing menghentikan FFmpeg melalui
Event; snapshot/hash/chunk loops mempunyai checkpoints. Artifact stream ditutup pada
consumer exception sebelum scratch cleanup. Platform tetap menentukan result commit,
authorization, attempt retry, staged TTL cleanup dan derivative promotion.

Full provenance dikirim sebagai private JSON_REPORT artifact dengan capability audio
dan versioned transform; frozen derivative DTO memberi enclosing integer-ms ranges,
report memberi exact frame/rate/channel/clock pairs. Failed audio eligible memakai
existing FAILED/INVALID_AI_OUTPUT; cancelled/expired/lost-lease tidak dipetakan ke
success atau failure enum yang diarang. Result response ambiguity hanya resend exact
candidate sekali; restart memerlukan coordinator fresh attempt/lease.

Default worker lease clock epoch ms berbeda dari replay as-of; injectable adapter clock
dan anchored monotonic watchdog mencegah backward wall clock memperpanjang lease.
Bounded/thread-safe/authenticated adapters wajib sebelum real integration karena sync
ports tidak dapat membatalkan implementation yang hang. MOCK executable tidak membuktikan
internal API authentication/durable promotion/OS sandbox/crash supervisor. Wire input
endpoint/version decision tetap future reconciliation bila production binding tidak
dapat dipenuhi adapter internal. [B02.2 evidence](../testing/b022-evidence.md) memberi
standalone acceptance/limits; readiness tetap false dan handlers tidak didaftarkan.
