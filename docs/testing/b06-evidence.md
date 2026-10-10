# B06 — acceptance lokal Paket B

Tanggal 9 Oktober 2026 (Asia/Jakarta). Status **in_progress**: engineering dan
acceptance lokal MOCK tersedia; acceptance eksternal dan integrasi nyata belum
terbukti. Research output **NOT_DOMAIN_VALIDATED**. Parent phases, Phase10,
G-BE/G-FE/G-DELIVERY tidak ditutup atau dimulai oleh pekerjaan ini.

## Git, baseline, dan scope sesi

Branch aktual `feat/backend-rai`; HEAD dan upstream `origin/feat/backend-rai`:
`da279281f1698197df1efef569f578adb1610cef`. Candidate berupa working tree di atas
SHA tersebut, bukan commit baru. Audit `git status --short`, branch, HEAD/upstream,
`git diff --stat`, tracked/untracked paths dan source dilakukan sebelum edit.
Awal sesi: 10 tracked files berubah, 989 insertions/107 deletions; B03/D3/evaluator,
B04, B05 serta docs/pitch/, tests/browser/, tmp/ sudah ada dan dipertahankan.
Tidak reset/clean/stage/commit/push/merge/ganti branch.

Input audit: rules, PRD (authority/data/provider/acceptance), roadmap/handoff,
packet execution, frozen models/ports/registrations/shared suites, evidence
[B01](b01-evidence.md), [B02.1](b021-evidence.md), [B02.2](b022-evidence.md),
[B03](b03-evidence.md), [B04](b04-evidence.md), [B05](b05-evidence.md), actual
migrations/repositories/bindings/workers/provider/export/retention source dan tests.
Hasil dokumen historis tidak dihitung sebagai hasil sesi ini.

Baseline sebelum source edit, Python3.12.15 `.venv/Scripts/python.exe`, uv0.12.23:
`uv run --locked --python .venv/Scripts/python.exe python -m pytest tests/analysis
tests/contracts --track B -q` → **666 PASS, tanpa skip,65.73s**.
FFmpeg9.0.2 ditambahkan hanya pada PATH proses; fixture tidak diregenerasi.

File source baru hanya `backend/flowlens/testing/acceptance.py` dan
`tests/analysis/test_acceptance.py`. Pembaruan docs: evidence ini, roadmap,
handoff dan kedua packet documents. Tidak ada edit source A, perilaku B01–B05,
frozen contracts1.0.0, manifest dependency, uv.lock, evaluator atau fixtures.

## Entrypoints dan manifest aktual

`python -m flowlens.testing.acceptance` menjalankan local cross-module checks dan
sembilan standalone commands. Tambahkan `--suite` untuk seluruh tests/analysis +
contracts track B, lalu contracts track A secara berurutan. `--output PATH`
menyimpan JSON; hasil command gagal/timeout menghasilkan status failed/exit1.
Tanpa `--suite`, field suite adalah NOT_RUN; local pass tidak mengklaim suite pass.
Runner sengaja repo-local: memerlukan checkout tests/contracts/scripts, bukan
janji executable acceptance dari installed wheel tanpa source tree.

JSON berisi actual registration manifest (services, repositories, inventory,
config keys, migration owner/dependencies/SQL hash), runtime/dependency versions,
source/input/lock hashes, exit code, duration dan tail stdout/stderr tiap command.
Local report: `artifacts/reports/b06/acceptance.json` (ignored).
Console copy: `artifacts/reports/b06-console.json` (ignored).

| Unit | Entrypoint source | Registration / integration hooks |
| --- | --- | --- |
| B01 | `flowlens.analysis:register_analysis` | analysis; configuration repository/inventory/purge/config keys |
| B02.1 | `flowlens.audio:prepare_audio`, `AudioTools.discover` | controlled local executor; tanpa module routes/handlers |
| B02.2 | `flowlens.workers.audio.worker:AudioWorker` | injected InputAccess/JobClient/AssetAccess; worker tidak membuka DB |
| B03 | `flowlens.analysis.transcripts:register_transcripts`; `flowlens.providers.stt.execution:execute_attempt`; `flowlens.bindings.stt:PrivateTranscriptIngest` | analysis_transcripts; 4 private transcript namespaces; caller UOW/authority |
| B04 | `flowlens.memory.service:register_memory`; `flowlens.providers.gemini.adapter:GeminiExecutor`; `flowlens.bindings.intent_memory:TranscriptMemoryBinding` | intent_memory; accepted memory ledger/reducers/loops, caller UOW |
| B05 | `flowlens.advisory.service:register_advisory`; `flowlens.advisory.exports:ReportRenderer` | advisory; document/review/invalidation inventory/purge |
| B06 | `flowlens.testing.acceptance:local_checks`, `manifest`, `main` | test composition only; tidak mendaftarkan route/job handler |

Keempat actual B registrations memakai contract1.0.0, MOCK marker, readiness false,
tanpa routes/job handlers/snapshot reader. Manifest menolak namespace collision,
inventory mismatch, wrong version, readiness true dan placeholder hooks.
Registry production menolak MOCK. B02 tidak diberi registrasi fiktif.

Migration order: MOCK reference `platform.0001` → `analysis.0001` → `.0002` →
`.0003` → `.0004`, owner B untuk keempat analysis migrations. Factory B menerima
caller connection dan guard, bukan membuka DB sendiri. Fresh DB/repeated restart,
B01 → B05 upgrade, FK enabled/check dan preservation konfigurasi/parent IDs diuji.
Migration runner adalah reference MOCK, bukan runner production Paket A.

Config tetap memakai `AnalysisConfig`, `AudioLimits`, `WorkerConfig`, `STTConfig`,
`GeminiConfig`; strict bounds dan approval/checkpoint/reservation ports existing
dipertahankan. Dependency/versions follow unchanged pyproject.toml/uv.lock:
Google speech2.41.0, google-genai2.29.0, Pydantic2.13.5, FastAPI0.142.4,
pytest9.1.1; SQLite3.53.1. Model Gemini target tetap gemini-3.8-flash;
STT mock-project/model settings pada fixture bukan effective cloud approval.

## Acceptance coverage dan batas oracle

Sepuluh tests B06 baru mencakup combined UOW, upgrade/restart, manifest negatives,
production MOCK rejection/collision, runner timeout/nonzero propagation dan suite
selection. `local_checks` memakai AdvisoryReferenceTransactions, actual B services,
FakePlatform dan explicit MOCK authority/client pada disposable DB tunggal:

- config + raw transcript + advisory ditulis pada UOW sama, memory dipurge pada
  transaksi tersebut; omitted commit dan injected failure setelah writes membatalkan
  semuanya, termasuk reference evidence/audit/events;
- publication baru melihat config durable sesudah commit; fresh transaction factory
  membaca state config/transcript/memory/advisory tanpa provider conversation state;
- duplicate raw exact payload idempotent; duplicate setelah cancellation ditolak
  dengan JOB_CANCELLED; reverse registration purge menjaga platform parent rows;
- readiness dan absence placeholder hooks diuji sebagai boundary, bukan success
  handler kosong. Tempdir dibersihkan sesudah connection/client ditutup.

Local raw fixture tidak menjadi transcript yang menghasilkan memory fixture B04.
Ini cross-module UOW acceptance dengan fixture terpisah, bukan satu audio-to-report
pipeline. Existing `test_existing_transcript_lifecycle_to_memory_and_reanalysis`
memberi acceptance binding B03→B04 secara terpisah; tidak menaikkan integrated readiness.

Runner menyertakan seluruh existing tests berikut sebagai executable acceptance,
tanpa menyalin atau melemahkan thresholds/assertions:

| Area | Executable evidence |
| --- | --- |
| Scope/auth/rollback/FK/closed UOW | test_foundation.py, test_transcripts.py, test_intent_memory.py, test_advisory.py, contracts/test_ports.py |
| Worker cancellation/lease/deadline/retry/stale/late/partial consumer | test_audio_worker.py, test_stt_boundary.py, test_stt.py; standalone worker + private bridge |
| Idempotency/receipts/changed payload/restart | contracts/test_transactions.py (reference coordinator); test_stt_boundary.py/test_transcripts.py/test_intent_memory.py/test_advisory.py (actual B services) |
| Quote/hash/range/revision/as-of/unknown availability | contracts/test_ports.py; transcript, intent_memory, advisory negatives |
| Said/Heard/Observed, missing geometry/coverage, ambiguity/negation/correction | test_intent_memory.py and test_advisory.py; synthetic independent assertions, bukan benchmark domain |
| Provider schema/refusal/malformed/tool injection/budget/timeout/late result | test_stt.py/test_stt_boundary.py/test_intent_memory.py/test_advisory.py; HTTP/SDK mocked |
| Export rights/text redaction/HTML escaping/CSV formulas/no audio URL | test_advisory.py export tests pada JSON/CSV/HTML |
| Purge ownership/scoped inventory/partial purge failure rollback | test_advisory.py retention tests dan combined B06 reverse purge |
| Import isolation, no worker SQLite/A internals, no runtime evaluator truth | contracts/test_handoff.py dan package boundary subprocess/AST tests |

Shared contract track B tetap memakai reference platform/FakeAnalysis sesuai
frozen suite; pass shared suite bukan bukti seluruh private B services memenuhi
public AnalysisModule/ProviderAdapter secara end-to-end. B06 menambahkan actual
registrations/UOW di samping suite itu. Evaluator truth tetap evaluator/tests;
runtime tidak membaca labels, private schedule atau evaluation outputs.

## Reproduksi dan hasil aktual

Dari workspace root PowerShell; tidak mengubah global PATH:

```powershell
$env:PATH = "$PWD/artifacts/reports/b022-tools/ffmpeg-9.0.2-essentials_build/bin;$env:PATH"
uv run --locked --python .venv/Scripts/python.exe python -m flowlens.testing.acceptance --suite --output artifacts/reports/b06/acceptance.json
.venv/Scripts/ruff.exe check backend tests scripts
.venv/Scripts/ruff.exe format --check backend tests scripts
.venv/Scripts/mypy.exe backend/flowlens/analysis backend/flowlens/audio backend/flowlens/workers backend/flowlens/providers backend/flowlens/bindings backend/flowlens/intent backend/flowlens/association backend/flowlens/memory backend/flowlens/loops backend/flowlens/advisory backend/flowlens/testing/analysis.py backend/flowlens/testing/audio_worker.py backend/flowlens/testing/stt.py backend/flowlens/testing/transcripts.py backend/flowlens/testing/stt_worker.py backend/flowlens/testing/intent_memory.py backend/flowlens/testing/advisory.py backend/flowlens/testing/acceptance.py
.venv/Scripts/mypy.exe --platform linux
.venv/Scripts/mypy.exe
.venv/Scripts/mypy.exe scripts/stt_scoring.py
.venv/Scripts/python.exe -m flowlens.contracts.generate --check
.venv/Scripts/bandit.exe -r backend/flowlens -l
.venv/Scripts/python.exe -m pip_audit --local
uv build --python .venv/Scripts/python.exe --out-dir artifacts/reports/b06-dist
git diff --check
```

| Check sesi ini | Hasil aktual |
| --- | --- |
| Baseline sebelum source edit | 666 PASS, no skips,65.73s |
| B06 focused | 10 PASS,1.83s |
| Runner pertama --suite | PASS: 676 B tests/contracts B, no skips,50.27s;66 contracts A,4.34s |
| Sembilan standalone commands | Semua PASS, exit0: shared B, analysis, audio_worker MOCK, audio_worker --real, stt, transcripts, stt_worker, intent_memory, advisory |
| Ruff lint/format | PASS;110 files formatted |
| Native scoped B mypy | PASS61 files; focused acceptance module PASS setelah query literal |
| Linux-target backend mypy | PASS85 files; static target saja, bukan Linux runtime |
| Full native Windows mypy | FAIL:7 existing POSIX errors A pada database.py/bootstrap_admin.py;85 files checked |
| Evaluator scorer mypy | PASS1 file |
| Schema/OpenAPI drift | PASS; frozen contracts unchanged |
| Bandit | Initial FAIL1 medium B608 pada query count harness; diganti fixed literal SQL. Final PASS0 issues seluruh severities; existing transcript_store nosec warnings tetap |
| Dependency audit | PASS no known vulnerabilities; unpublished atc-flowlens sendiri tidak tersedia di PyPI/skipped |
| Build | PASS sdist/wheel, refreshed setelah SQL literal; ignored b06-dist, bukan clean-install smoke |
| Final runner setelah SQL literal | PASS:676 B tests/contracts B, no skips,49.18s;66 contracts A,4.57s;9 standalones PASS |
| Final whitespace | git diff --check PASS; file baru diperiksa terpisah karena untracked tidak dicakup git diff |

Native Windows errors: O_NOFOLLOW (3), flock/LOCK_EX/LOCK_NB (3), geteuid (1).
Ini tujuh error Paket A yang sudah tercatat sebelum B06; tidak diperbaiki dengan
edit A atau suppress typecheck. Tidak ada failure/skip pytest baseline baru.
Initial Ruff import-order dan scoped mypy optional purge callable pada source B06
baru diperbaiki, bukan dinyatakan sebagai baseline A. Final report/hash dan build
sudah diperbarui sesudah perubahan SQL literal; tidak ada source edit setelahnya.

Tidak menjalankan real smoke, empirical benchmark, domain review, production host,
real A/B API transport, Linux runtime, capacity/backup/restore release rehearsal,
frontend/browser, Compose/deploy, Phase10 atau release gates. Restart di atas adalah
disposable SQLite reopen, bukan crash/power-loss atau production restore guarantee.
Tidak ada server/daemon/container ditinggalkan; task subprocesses selesai.

## External acceptance dan contract gaps

**B03_EXTERNAL_ACCEPTANCE_PENDING**: STT_ACCOUNT_LOGIN_REQUIRED,
AUDITED_BENCHMARK_PENDING. **B04_EXTERNAL_ACCEPTANCE_PENDING**:
GEMINI_ACCOUNT_ACCESS_UNVERIFIED, REAL_GEMINI_SMOKE_PENDING,
AUDITED_SEMANTIC_BENCHMARK_PENDING. **GEMINI_EXTERNAL_ACCEPTANCE_PENDING** tetap
terlihat. B03/B04/B05/B06 tetap in_progress; B01/B02 local acceptance dipertahankan.

Real STT calls **0**, real Gemini calls **0**, real smoke **NOT_RUN**; benchmark
eksternal **BLOCKED**, metrics **null**, integrated pipeline readiness **false**.
B06 local_checks memakai1 MOCK advisory call; nested standalones/suite memakai
MOCK masing-masing (B04 CLI2/B05 CLI3), bukan satu angka total benchmark atau RPC
nyata. Tidak mencari credential, melakukan cloud login/provisioning atau mengganti
provider/model; default diagnostics memakai preflight tanpa credential lookup.

| Gap/blocker | Owner | Evidence / next action |
| --- | --- | --- |
| STT_ACCOUNT_LOGIN_REQUIRED | User/cloud operator | Approved identity/project/API/recognizer/model/locale/region/quota/rights/budget dan authorization; synthetic real smoke berizin |
| AUDITED_BENCHMARK_PENDING B03 | Annotation/evaluation lead | Audited waveforms/critical-slot/timing labels, independent held-out splits, protocol/thresholds dan real output receipts; run existing scorer |
| GEMINI_ACCOUNT_ACCESS_UNVERIFIED / REAL_GEMINI_SMOKE_PENDING / GEMINI_EXTERNAL_ACCEPTANCE_PENDING | User/cloud operator | Approved identity/key/target model/API/terms/quota/rights/budget; authorized real structured/timeout compatibility smoke |
| AUDITED_SEMANTIC_BENCHMARK_PENDING dan B05 domain acceptance | Evaluation/domain lead | Audited held-out intent/association/loop/finding/abstention/relevance labels, real outputs, domain review briefs/options |
| Evidence wire tidak membawa availability; server roles/aliases/coverage/geometry/rights belum nyata | Platform + analysis owners | Authoritative scoped/as-of adapters; jangan menganggap FakePlatform sebagai authorization production |
| Private transcript/memory/document/review/provenance tidak lengkap pada frozen ProviderAdapter/JobResult/AnalysisRepository | Platform + analysis owners | Explicit public projection dan private artifact codec reconciliation; version decision jika diperlukan; tidak menyelundupkan private data ke text/Usage |
| Durable attempts/receipts/budgets/cancellation, artifact ACL/TTL/promotion/cleanup dan worker reconciliation | Platform + analysis owners, Phase10 terpisah | Actual coordinator/internal API/result handler dan cross-package atomic/recovery evidence; belum diimplementasikan B06 |

Frozen AssetAccess tidak menyediakan abort/delete, sehingga remote staging cleanup
tetap platform. Synchronous frozen ports memerlukan timeout/bounded implementation;
harness tidak membuktikan penghentian adapter production yang macet. Public snapshots,
REST routes/job handlers dan accepted projections tetap belum dipasang. Build/mock
contracts tidak menutup gap tersebut atau G-BE/G-FE/G-DELIVERY.

## Continuation — evaluator, package, capacity, compatibility (9 Oktober 2026)

Local continuation menutup gap tooling independen dari acceptance eksternal. Source
baru adalah `scripts/semantic_scoring.py`, `scripts/evaluation_semantic.py`,
`scripts/package_smoke.py`, `scripts/capacity_b.py`, fixture
`evaluation/fixtures/semantic-test-only.json`, protocol
`evaluation/protocols/semantic-evaluation.md`, matrix
`docs/development/package-b-compatibility.md`, serta tests
`tests/analysis/test_semantic_scoring.py` dan `test_local_tooling.py`.
Runtime/provider, frozen contracts1.0.0 dan Paket A tidak diubah. `pyproject.toml`
mengecualikan `docs/pitch`, `tests/browser`, dan `tmp` dari sdist.

Evaluator strict memvalidasi scope/session/run/revision/source/family/speaker/split,
annotation/prediction/evidence/provenance/reviewer, hashes, availability, required
evidence dan reviewer relevance. Duplicate IDs/JSON keys, cross-scope/future
evidence, split leakage, unsupported evidence, malformed/nonfinite input, missing
provenance, wrong relationship, premature/false closure dan TEST_ONLY pretending
real provider ditolak. Metrics descriptive memisahkan known/ambiguous/unknown,
missing/abstained, coverage, semantic exactness, wrong pairing, closure support,
finding precision/recall dan reviewer relevance. Thresholds `UNSET`, verdict `null`.
Default CLI **BLOCKED/metrics=null**; TEST_ONLY memakai MOCK/calls0 dan nested
external benchmark BLOCKED. Raw acquired mode memerlukan envelope/hash binding dan
`--raw-output`, belum dijalankan karena audited corpus/provider output tidak ada.
Actual evaluator+boundary tests **42 PASS**, Ruff/mypy/Bandit scoped PASS.

Clean-install smoke: wheel/sdist dibangun, locked requirements diekspor, venv
disposable di luar checkout dibuat, wheel dipasang dengan `python -I`, enam
standalone MOCK entrypoints berjalan dari site-packages, import/PYTHONPATH leak
tidak ditemukan, dan `uv pip check` PASS. Evaluator truth/fixtures tidak masuk wheel;
sdist mengecualikan untracked pitch/browser/tmp. Repo-local acceptance runner tetap
memerlukan source/tests dan sengaja terpisah.

Capacity: `scripts/capacity_b.py --execute --sizes 16 128 512 --repetitions 3
--seed 214` memakai generator `b-capacity-mock-1`, Windows11/Python3.12.15/
SQLite3.53.1, disposable storage dan window advisory maksimum8 event. Semua
reconstruction order, Said/Heard/Observed, no-false-closure, FK, output hash dan
cleanup invariant PASS. Median ms (16/128/512): append 7.427/30.553/124.557,
inventory 3.749/19.251/86.360, reconstruction 0.546/3.182/13.883, loops
0.835/5.652/24.791, brief MOCK 7.585/8.497/12.363. Peak Python tracemalloc
1.32/4.89/17.87MB; final DB 258048/724992/2314240 bytes. Synthetic baseline
only; targets UNSET, bukan operational capacity/provider latency/safety benefit.

WSL2 kernel tersedia, tetapi `docker-desktop` tidak memiliki Python/uv/FFmpeg dan
Docker daemon unavailable; Linux runtime **NOT_RUN**. `mypy --platform linux` adalah
static check saja. Compatibility matrix dan negative tests mencakup public
projection, evidence availability/as-of, alias/role/coverage/geometry authority,
artifact ACL/TTL/promotion, attempts/receipts/idempotency/cancellation dan Phase10
projection gaps. External B03/B04/B05 tetap pending, real calls0, smoke NOT_RUN,
benchmark BLOCKED/metrics null, integrated readiness false.
