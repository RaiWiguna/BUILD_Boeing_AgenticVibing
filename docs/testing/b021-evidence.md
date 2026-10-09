# B02.1 — controlled audio processing evidence

Tanggal: 9 Oktober 2026. Branch `feat/backend-rai`; base SHA
`cdb2b9dae3d16c22a524b8a05b2e5583cc48e0d0` + existing uncommitted B01 dan B02.1.
Tidak commit/push/merge. **B02.1 / Phase 6.2 done untuk controlled local audio:
real FFmpeg acceptance kini terbukti, 57 tests PASS tanpa skip.** Paket B dan
parent/gates tetap terbuka. Rekam pemeriksaan sebelum binary tersedia di bawah
adalah historical evidence; hasil terkini ada pada bagian real acceptance.

## Audit dan implementasi

Baseline sebelum edit source: `.venv/Scripts/python.exe -m pytest tests/analysis
tests/contracts --track B -q` → **87 passed** (21 B01 + 66 contracts). Existing
changes `.agent/`, harness, docs, untracked analysis/tests, docs/pitch, tests/browser
dan tmp dipertahankan. Python 3.12.15 di `.venv/Scripts/python.exe`; manifest/uv.lock
tidak berubah. Rules/PRD, roadmap/handoff, execution/evidence, architecture/ADR,
contracts/ports/registration, actual analysis/harness/tests/fixtures diaudit.

- `backend/flowlens/audio/models.py`: local strict frozen configuration, probe,
  frame/chunk plan, result provenance. Tidak menambah frozen wire DTO.
- `planning.py:plan_chunks`: deterministic size/sample planning, per-channel,
  final short chunk, intentional overlap, gap coverage dan source/session mapping.
- `tools.py:AudioTools.discover/probe/decode`: version discovery, bounded JSON,
  single audio stream, format/rate/channel/duration/start consistency dan fixed args.
- `process.py:run_bounded`: shell false, stdin closed, stdout cap, stderr discard,
  wall timeout, kill/wait, joined pipe drains; process errors tidak echo private data.
- `preparation.py:prepare_audio`: authorized file/roots dari caller, hash-verified
  bounded snapshot, magic checks, decode accounting, exclusive mono WAV chunks,
  metadata dan context cleanup. Tidak menerima source manifest/evaluator labels.
- `tests/analysis/test_audio.py`: pure tests, explicit MOCK decode, actual local
  Python subprocess limit tests, dan separate real FFmpeg smoke dengan skip reason.
- [ADR 0003](../adr/0003-controlled-local-audio.md) mencatat keputusan/batas media.

Entry point publik lokal `flowlens.audio:prepare_audio` adalah context manager;
hasil `PreparedAudio.directory` hanya valid di dalam context. Caller mengonsumsi
`metadata.chunks[*].filename` di directory tersebut dan metadata sebelum exit.
`AudioTools.discover()` mencari PATH atau menerima explicit trusted executable
paths; tidak menerima executable/filter dari source/job payload. Tidak ada CLI,
job handler, DB, migration, real A/B composition atau automatic promotion baru.

## Config dan limits

`AudioLimits` default: input512MiB; duration3600s/file; channels≤2;
input8–192kHz; output16kHz; chunk≤50000ms; overlap1000ms; mono PCM16 WAV;
max chunk9,999,999 bytes termasuk 44-byte header; max512 chunks;
max output512MiB (decoded PCM + seluruh WAV termasuk overlap/header);
probe timeout10s; decode timeout120s. User-set lower limits didukung; validation
mencegah overlap≥effective capacity. Hard configurable upper bounds di source.
Max single FFmpeg allocation64MiB dan decoder threads1. Snapshot input menambah
disk hingga max input bytes; output budget bukan total scratch-volume quota.

Input512MiB/channels2/duration mengikuti PRD §5.2 (60 menit/file, hingga2jam audio
lintas channel); session aggregate import quota tetap platform, bukan executor ini.
Chunk baseline mengikuti roadmap/PRD, **bukan provider quota terverifikasi**.
Chunk/output/count/time/allocation adalah initial engineering limits; belum capacity
benchmark. Metadata mencatat source ID/asset ID/hash before-after, probe format,
decoded frame count/hash, rate/width/channel, config/hash/version, tool versions,
chunk hash/size/local and derivative frames, enclosing source frames/source ms,
session ms/null, clock/version/uncertainty, source gaps dan overlap per segment.

Ranges half-open, channel zero-based dan tidak menyimpulkan speaker identity.
Gaps diterima sebagai explicit source-relative frame ranges (bukan otomatis
menafsirkan Coverage.gaps yang clock-nya belum diadaptasi). Sample yang bersinggungan
dengan gap dikecualikan lewat outward rounding. Full-gap source menghasilkan
zero eligible chunks dengan metadata gaps, bukan hasil speech. Tidak mengisi gaps
dengan observation palsu. Time mapping exact direkonstruksi dari frame/rate pairs;
float milliseconds hanya representasi rasio. Nonzero media timestamps ditolak.

## Historical tools, fixtures dan commands sebelum provision binary

Windows / PowerShell, CPython3.12.15. `Get-Command ffmpeg,ffprobe` tidak menemukan
binary; pemeriksaan common local/WinGet/Programs/tools serta filenames dalam
`.codex` tidak menemukan keduanya. **FFmpeg/ffprobe version: unavailable**;
tidak mengunduh/menginstal binary, tidak mengklaim versi mock sebagai versi host.

Fixture immutable SHA-256 (tidak diregenerasi):

- `tests/fixtures/audio/hold-short.wav`:
  `cf3baa73bc59e37ddbd16e99e8a5f7493c22057d01c02b4030585b88486ba044`.
- `tests/fixtures/audio/silence.wav`:
  `643f8a8dc8bd9c19225afffad2becfec5426180b3749cb208abdf1a6c8354efc`.
- `tests/fixtures/manifests/synthetic-audio.json` dan `contracts/examples/`
  tetap application fixtures; evaluator labels/oracles tidak di-load runtime.

Commands dari workspace; tools berikut memakai `.venv/Scripts/`:

| Command | Actual result |
| --- | --- |
| `python -m pytest tests/analysis/test_audio.py -q` | 55 passed / 2 skipped; skipped adalah real binary smoke hold-short resample8k dan silence16k |
| `python -m pytest tests/analysis tests/contracts --track B -q` | 142 passed / 2 skipped (55 audio +21 B01 +66 contracts) |
| `python -m flowlens.testing --track B` | PASS MOCK/provider_calls0/disposable-cleaned |
| `python -m flowlens.testing.analysis` | PASS B01 MOCK/readiness false/provider_calls0/disposable-cleaned |
| `ruff check backend tests scripts` | PASS |
| `ruff format --check backend tests scripts` | PASS |
| `mypy backend/flowlens/audio backend/flowlens/analysis backend/flowlens/testing/analysis.py` | PASS 12 files, native Windows |
| `mypy --platform linux` | PASS 36 backend files |
| `mypy` | 7 unchanged POSIX API errors A: database.py/bootstrap_admin.py; no B errors |
| `python -m flowlens.contracts.generate --check` | PASS, frozen schema drift absent |
| `bandit -r backend/flowlens -ll` | PASS, zero issues all severities; 2 justified subprocess import/call suppressions with shell disabled |
| `pip-audit --local` | PASS, no known vulnerabilities; unpublished project itself skipped |
| `uv build --out-dir artifacts/reports/b021-dist` | PASS sdist + wheel; host uv0.12.23, project Python3.12 |
| `git diff --check` | PASS |

Final source changes were rechecked where affected. Native A portability failure is
the documented pre-existing baseline; A internals were not changed. Track A not
rerun separately because shared baseline was untouched in this session; track B
suite includes both standalone CLI tests. No clean-wheel-install claim.

## Historical acceptance dan updated disposition

Proven without audio binaries: independent expected chunk boundaries/final short
chunk/effective size/overlap; known/null clock and resample gap rounding; MOCK mono
materialization preserves stereo channels/PCM/sample counts; raw before-after hash;
bad source hash/magic/metadata/size/path/network/relative/hardlink/raw-scratch alias;
malformed/nonfinite/inconsistent probe; fixed arguments/protocol/container whitelist;
missing binary and sanitized version discovery; actual Python subprocess timeout,
failure, output overflow, large stderr drain and exclusive target preservation;
MOCK probe/decode/truncation/duration mismatch/raw mutation/disk write failures;
scratch cleanup on failure/success/consumer exception; AST runtime import allowlist.

Mandatory real acceptance yang sebelumnya pending **telah lulus** pada sesi
lanjutan 9 Oktober 2026: actual ffprobe inspection + FFmpeg decode/resample,
rate/format/channel/frame accounting, mapping, hashes dan cleanup. Historical
mock PCM copy dan Python subprocess tetap tidak dianggap real audio decode.

Hold-short tetap synthetic NOT_GOLD/NOT_DOMAIN_VALIDATED. Tidak mengklaim WER,
critical-slot accuracy, pronunciation audit, transcript dedup atau operasi nyata.
No provider calls, cloud transfer, real data, frontend, Docker/deployment atau
process persistent. Tempdirs/subprocesses task cleaned; ignored build output
`artifacts/reports/b021-dist` ditinggalkan untuk inspeksi; original user folders
dan dua legacy failed-B01 tempdirs tidak disentuh.

Windows privacy ACL diwarisi dari trusted private roots; adapter tidak menyediakan
OS sandbox/total memory quota atau proteksi terhadap hostile filesystem owner.
Worker isolation/lease/heartbeat/cancel/retry/restart dan artifact submission kini
dibuktikan secara mandiri pada [B02.2 evidence](b022-evidence.md), melalui frozen
JobClient/AssetAccess dan MOCK platform. Real authenticated API tetap belum tersedia.
Readiness false; frozen contracts1.0.0, analysis.0001, config b01-1 tetap.
Phase6.2 done; Paket B, Phase6/9, G-BE/G-FE/G-DELIVERY belum ditutup.

## Real acceptance — 9 Oktober 2026

Baseline sebelum source edit sesi lanjutan: Python3.12.15,
`pytest tests/analysis tests/contracts --track B -q` →142 PASS/2 SKIP.
Tidak menemukan CLI binary lokal. Build Windows Gyan ditautkan oleh
[FFmpeg official download](https://www.ffmpeg.org/download.html); pinned download:
[GyanD release9.0.2](https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.7z).
Publisher checksum diperoleh dari
[Gyan SHA-256](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.7z.sha256).
Archive checksum cocok sebelum extraction:
`4705843ccaaf54257c16ad90f3e952ece33c17df964ecf7bfdbb0f49c7171077`.

Local tool root: `artifacts/reports/b022-tools/ffmpeg-9.0.2-essentials_build/bin/`
(ignored, workspace lokal; bukan PATH global). FFmpeg dan ffprobe actual version
`9.0.2-essentials_build-www.gyan.dev`.

| Binary | SHA-256 |
| --- | --- |
| ffmpeg.exe | `3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec` |
| ffprobe.exe | `f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52` |

Reproduction di PowerShell, workspace root:

```powershell
$toolRoot = Join-Path $PWD 'artifacts/reports/b022-tools'
New-Item -ItemType Directory -Force $toolRoot | Out-Null
curl.exe -fL https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.7z -o "$toolRoot/ffmpeg.7z"
$archiveHash = (Get-FileHash "$toolRoot/ffmpeg.7z" -Algorithm SHA256).Hash.ToLowerInvariant()
if ($archiveHash -ne '4705843ccaaf54257c16ad90f3e952ece33c17df964ecf7bfdbb0f49c7171077') { throw 'Archive checksum mismatch' }
tar -xf "$toolRoot/ffmpeg.7z" -C $toolRoot
$env:PATH = "$PWD/artifacts/reports/b022-tools/ffmpeg-9.0.2-essentials_build/bin;$env:PATH"
.venv/Scripts/python.exe -m pytest tests/analysis/test_audio.py -q
```

Actual result: **57 PASS**, tidak skipped. Kedua fixture tetap immutable:

| Fixture | Raw PCM | Real derivative | Independent chunk boundaries (frames) |
| --- | --- | --- | --- |
| hold-short.wav | PCM16 mono16kHz,128343frames,8021.4375ms | mono PCM16/8kHz,64172frames,8021.5ms | [0,24000),[20000,44000),[40000,64000),[60000,64172) |
| silence.wav | PCM16 mono16kHz,16000frames,1000ms | mono PCM16/16kHz,16000frames | [0,16000) |

Tests memeriksa ffprobe wav/pcm_s16le/rate/channel, ceiling resample sample count,
WAV headers/channel/sample width/frame counts, output checksum/bytes, raw hash
before/after, channel0, source/session mapping dan final boundaries. Scratch kosong
setelah context exit. Chunk3s/overlap500ms dipakai untuk smoke ini. Frame rounding
pada hold-short memberi enclosing source end128344; raw128343 tidak dimodifikasi.
Hold-short tetap synthetic NOT_GOLD/NOT_DOMAIN_VALIDATED; tanpa WER/domain claim.

B02.2 menambahkan optional cancellation event pada bounded subprocess serta
checkpoints pada snapshot/hash/chunk loops. Consumer yang gagal menutup iterator
secara eksplisit sebelum cleanup. Actual FFmpeg cancellation juga diuji terpisah
di worker suite; schema, waveform, manifest dan lock tidak diregenerasi.
Final combined checks dan limitations terbaru ada di [B02.2](b022-evidence.md).
