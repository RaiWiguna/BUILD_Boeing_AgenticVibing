# B02.2 — isolated AUDIO worker evidence

Tanggal: 9 Oktober 2026; branch `feat/backend-rai`; existing B01/B02.1 work dan semua
untracked user folders dipertahankan. Tidak stage/commit/push/merge/reset/clean.
Python3.12.15 dari `.venv/Scripts/`. Frozen contracts1.0.0, generated schemas,
analysis.0001, pyproject.toml dan uv.lock tidak berubah. Readiness false.

Status: **B02.2/Phase6.4 done untuk acceptance mandiri dengan MOCK platform ports**.
Ini bukan bukti real internal API/authentication, durable coordinator/promotion,
OS sandbox atau real A/B composition. Parent Phase6/9, Paket B dan gates tetap terbuka.
Prasyarat [B02.1 real acceptance](b021-evidence.md) ditutup sebelum implementasi.

## Source dan executable

- `backend/flowlens/workers/audio/models.py`: strict/frozen WorkerConfig,
  internal AudioInput dan InputAccess; safe WorkerOutcome.
- `worker.py`: AudioWorker.run_once/serve, LeaseGuard, bounded download/upload,
  controlled prepare_audio, typed result/receipt checks dan cleanup.
- `backend/flowlens/testing/audio_worker.py`: explicit MOCK scoped platform ports,
  staging/receipt reference dan standalone process executable. Tidak memakai SQLite.
- `tests/analysis/test_audio_worker.py`: deterministic port negatives, actual Python
  subprocess controls/process harness, real FFmpeg execution terpisah.
- `audio/process.py`, `tools.py`, `preparation.py`: optional cancellation event,
  50ms process poll/kill/wait/pipe draining; bounded interruptible hashes, input-copy
  dan chunk checkpoints. Default B02.1 entrypoints tetap compatible.

Entrypoints:

```powershell
.venv/Scripts/python.exe -m flowlens.testing.audio_worker
.venv/Scripts/python.exe -m flowlens.testing.audio_worker --real
.venv/Scripts/python.exe -m flowlens.testing.audio_worker --scenario cancel
.venv/Scripts/python.exe -m flowlens.testing.audio_worker --scenario deadline
.venv/Scripts/python.exe -m flowlens.testing.audio_worker --scenario shutdown
.venv/Scripts/python.exe -m flowlens.testing.audio_worker --scenario heartbeat-failure
.venv/Scripts/python.exe -m flowlens.testing.audio_worker --scenario timeout
```

Use process-local PATH dari B02.1 evidence untuk --real. Library composition:
`AudioWorker(config, jobs:JobClient, assets:AssetAccess, inputs:InputAccess,
tools:AudioTools, shutdown:Event, now:Callable).run_once()` atau `.serve()` dalam
dedicated process. Tidak memasang production CLI transport atau handler kosong.
Executable MOCK memasang SIGINT/SIGTERM handler; shutdown test memakai actual
signal.raise_signal di proses harness. External Windows TerminateProcess adalah
hard kill, bukan graceful signal, dan tidak diklaim memberi immediate cleanup.

## Internal adapter dan frozen contract gaps

JobLease hanya membawa asset_ids, bukan size/source/clock/gaps/rights/RequestContext.
InputAccess.resolve adalah **internal injected binding**, bukan endpoint/wire DTO
baru. Platform adapter wajib membangun authorized minimum context dengan exact
session/run/revision/input hash, worker actor dan capability worker+audio saja;
job/attempt/lease/config hash, satu asset tanpa fixture_path, size, local permission,
source ID/clock/source-relative gaps. Worker memeriksa binding dan effective
AudioLimits digest sebelum download. Input hash tetap hash revision platform;
asset checksum diperiksa tersendiri, tidak diasumsikan sama dengan revision hash.

JobResult belum mempunyai AUDIO-specific failure atau cancellation code. Processing
failure yang eligible memakai existing FAILED/INVALID_AI_OUTPUT dengan kosong
outputs/evidence/artifacts; safe WorkerOutcome memberi local reason code.
Cancelled/expired/lost-lease/shutdown tidak dikirim sebagai successful/partial atau
FAILED dengan fabricated code; attempt coordinator menentukan terminal status.
Receipt pada FAILED adalah acknowledgment, tidak dianggap accepted domain output.
Audio COMPLETE memiliki artifacts tanpa transcript/domain outputs.

Full exact frame/rate/channel/clock/source/config/tool provenance dikirim sebagai
private JSON_REPORT artifact dengan required_capability audio; derivative metadata
di frozen ArtifactSubmission tetap hash/size/source/transform/ranges. Integer ms
ranges adalah outward enclosing source-relative/local-chunk bounds; exact pairs
tersimpan di provenance. Unknown session clock tetap null. Report memuat IDs/hashes
dan generated chunk filenames, tanpa private absolute path/audio/transcript/credentials.
Platform wajib mengenali transform `audio-worker-provenance-1` dan tidak memperlakukan
report ini sebagai user export. Ini keputusan adapter compatible, bukan schema change.

Default lease clock adalah Unix epoch milliseconds, tidak memakai replay as_of.
Clock dapat disuntikkan platform adapter; backward wall adjustment tidak memperpanjang
lease karena watchdog mengambil max dengan anchored monotonic progress. Server tetap
authoritative atas expiry/revocation. Future A transport harus reconcile epoch/clock
skew dan binding/permission/provenance semantic policy sebelum real composition.

Frozen synchronous ports tidak membawa cancellation/timeout parameter. Adapter
wajib menyediakan bounded calls (timeout ≤heartbeat interval), thread safety untuk
monitor dan main executor, limit response bytes, scoped auth serta credential
rotation. Hanging/malicious in-process port implementation tidak dapat diputus oleh
worker ini; OS process sandbox/hard-kill/crash supervisor dan auth transport belum
tersedia. MOCK tidak membuktikan hal tersebut.

## Lifecycle, limits, retry/restart

Initial lease validated; control monitor polling≤50ms mengirim heartbeat berkala
selama download/processing/submission, memeriksa cancellation/expiry/deadline,
menolak mutation pada lease identity/scope/stage/hash/owner/deadline atau expiry
yang mundur. Failure control membatalkan tool melalui Event. Main executor
checkpoints memastikan hasil parsial tidak menjadi COMPLETE. Final eligible
result dikirim lewat JobClient.result; receipt scope/job/attempt/hash diperiksa.
Platform masih wajib atomic authority check saat commit untuk race sesudah poll.

Download memakai half-open bounded AssetAccess ranges dan exact lengths+SHA256.
Scratch hanya per-attempt private roots; FFmpeg menerima snapshot tersendiri.
Artifact submit iterator menghitung length/hash dan wajib dikonsumsi penuh,
mengembalikan artifact ID yang sama; iterator selalu close bahkan consumer gagal.
Data remote yang sudah staged sebelum abort hanya dapat dipurge oleh platform
via TTL/lease cleanup: frozen AssetAccess tidak mempunyai delete/abort method.
Worker menghapus local scratch, tidak mengklaim menghapus remote staging.

Default heartbeat1s (0.05–10s), download/upload block64KiB (1KiB–1MiB), input binding
serialization≤512KiB, gaps≤4096, provenance≤2MiB (hard cap8MiB), lifetime≤100attempts
(hard cap10000). AudioLimits defaults dari B02.1; decoded PCM+chunks memakai output
budget. Total scratch bound≤2×input budget+audio output budget+metadata; default
sekitar1.5GiB+2MiB. Ini file accounting, bukan total OS memory/CPU quota. ACL Windows
diwarisi dari operator-provisioned trusted root; POSIX private directories0700.

Worker tidak meminta retry job sendiri. Same attempt delivery dalam process yang
sama ditolak; coordinator memberikan fresh attempt/lease untuk retry/restart.
Generated artifact IDs deterministik per attempt dan berubah pada fresh attempt;
fresh temp directory tidak membaca artifacts/scratch lama. Crash cleanup/recovery
dan terminal attempt policy milik platform. Ambiguous result response boleh resend
**exact same in-memory JobResult maksimal sekali**, tanpa prepare/upload ulang.
Same payload→same receipt, changed payload→conflict di MOCK reference. Unconfirmed
response tidak dilaporkan accepted. Lost response sesudah server commit mungkin
memerlukan coordinator lookup/reconciliation sesudah restart; tidak ada durable
worker result spool atau exactly-once provider-billing claim.

## Acceptance dan hasil

Baseline sebelum edits: combined analysis/contractsB142 PASS/2 SKIP. Trusted tool
provision dan B02.1 real57 PASS dilakukan sebelum B02.2 source ditambahkan.
Fixture hashes/tool origin/version/archive/binary checksums: B02.1 evidence.

Proven cases: separate executable PID/launcher ancestry; heartbeats saat decoder
aktif; no runtime SQLite/A/evaluation import (AST+actual subprocess module inventory);
strict bounded config; session/run/revision/input/config/stage/job/attempt/lease/owner/
asset negatives; bounded exact ranges/checksum; per-channel artifact/provenance;
cancel/deadline/expiry/shutdown before/during/after processing; lost lease/control
failure; timeout/process failure tanpa partial success; client/partial-consumer
failure cleanup; cancelled/late/stale results rejected; bad receipt/unconfirmed
response; duplicate receipt/changed payload conflict; retry fresh attempt tidak
memakai cancelled staging; input/output/chunk/metadata/attempt caps; backwards clock;
actual Python child kill/reap dan actual FFmpeg cancellation; real fixture hashes.

Initial test run menemukan test scratch berbagi autouse contract fixture directory
serta Windows venv launcher PID intermediate. Test memakai dedicated scratch dan
assert ancestry PID yang nyata. Consumer failure kemudian menemukan file generator
tertahan traceback di Windows; explicit iterator.close memperbaiki cleanup.
Mypy Generator annotation dan MOCK assert security finding juga diperbaiki.
Final results di bawah menggantikan intermediate failures, tanpa melemahkan assertions.

| Command (tools dari .venv/Scripts) | Actual result |
| --- | --- |
| pytest tests/analysis/test_audio.py -q | 57 PASS, real fixtures included |
| pytest tests/analysis/test_audio.py tests/analysis/test_audio_worker.py -q | 131 PASS: audio57 + worker74, MOCK/subprocess/real separated in tests |
| pytest tests/analysis tests/contracts --track B -q | 218 PASS, no SKIP |
| pytest tests/analysis/test_foundation.py -q | 21 B01 regression PASS (included combined) |
| python -m flowlens.testing --track B | PASS MOCK/provider_calls0/disposable-cleaned |
| python -m flowlens.testing.analysis | PASS B01 MOCK/readiness false/disposable-cleaned |
| python -m flowlens.testing.audio_worker | PASS separate process MOCK, heartbeat during processing, clean |
| python -m flowlens.testing.audio_worker --real | PASS MOCK ports+REAL FFmpeg, clean |
| Separate process cancel/deadline/shutdown/heartbeat-failure/timeout scenarios | PASS accepted0/clean/no forbidden runtime imports |
| ruff check backend tests scripts; ruff format --check backend tests scripts | PASS |
| mypy audio/workers/analysis/testing analysis+audio_worker | PASS17 files native Windows |
| mypy --platform linux | PASS41 backend files |
| mypy (whole native Windows) | 7 existing POSIX A errors; no B errors |
| python -m flowlens.contracts.generate --check | PASS no frozen schema drift |
| bandit -r backend/flowlens -l | PASS zero all-severity findings; 2 existing fixed-subprocess suppressions |
| pip-audit --local | No known vulnerabilities; unpublished atc-flowlens skipped |
| uv build --python .venv/Scripts/python.exe --out-dir artifacts/reports/b022-dist | PASS sdist+wheel, uv0.12.23 |
| git diff --check | PASS |

Track A suite tidak diperlukan karena frozen shared baseline tidak diubah; contractsB
juga menjalankan both-track standalone CLI cases. Linux target mypy adalah static
check, bukan Linux runtime test. No clean wheel install/production transport/real
platform endpoint/domain review/provider benchmark claim. Tidak menjalankan paid
Google STT/Gemini, cloud transfer, frontend, Docker/Compose atau deployment.

Semua task subprocess/monitor threads/scratch selesai; tidak ada persistent daemon.
Ignored verified toolchain archive/binaries dan b022-dist tersedia untuk inspection;
user folders dan historical B01 failed tempdirs tidak disentuh. hold-short tetap
synthetic NOT_GOLD/NOT_DOMAIN_VALIDATED, tanpa WER/critical-slot/pronunciation claim.
Overlap dedup tetap B03. Next unit **B03 — Google STT V2 dan transcript lifecycle**;
region/model/SDK/quota/credential/budget/rights adalah external prerequisites.
