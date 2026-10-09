# Paket B — rencana eksekusi dan acceptance

Tanggal 9 Oktober 2026; branch `feat/backend-rai`; frozen contracts `1.0.0`.
Audit awal pada `cdb2b9dae3d16c22a524b8a05b2e5583cc48e0d0`: contracts,
ModuleRegistration dan MOCK reference harness tersedia; belum ada implementation
analysis, audio worker atau provider adapter. Paket A tetap independen.

| Unit | Fase resmi | Pekerjaan / dependency lokal | Source dan tests | Acceptance / status awal |
| --- | --- | --- | --- | --- |
| B01 | Fondasi sesudah Phase 1, bagian persistence/registration 7.3 | Config immutable, migration B, repository scoped, transaction ports; hanya shared baseline | `backend/flowlens/analysis/`, `backend/flowlens/testing/analysis.py`, `tests/analysis/` | Done untuk fondasi: 21 tests + shared A/B; batas Windows typecheck A tercatat dalam evidence |
| B02.1 | 6.2 | Controlled decode/resample/chunk/time mapping; sesudah B01 | `audio/`, `tests/analysis/test_audio.py` | done: 57 PASS termasuk real FFmpeg9.0.2 hold-short8k/silence16k; hashes/accounting/mapping/cleanup |
| B02.2 | 6.4 | Isolated worker melalui JobClient/AssetAccess; sesudah B02.1 acceptance | `workers/audio/`, `testing/audio_worker.py`; worker tests | done untuk acceptance mandiri: 74 PASS MOCK ports/actual subprocess/real FFmpeg; real authenticated API belum tersedia |
| B03 | 7.1–7.4, sisa 7.3 | STT V2, hypotheses/timing/quality/dedup, append-only correction/evidence/stale; sesudah B02 | `providers/stt/`, analysis transcript repositories; provider/transcript tests | in_progress: adapter/lifecycle standalone MOCK acceptance; real profile/smoke, audited benchmark, worker/artifact reconciliation terbuka |
| B04 | 8.1–8.5 | Gemini structured intent, bounded tools, association, reducer/open loops; sesudah B03 | `providers/gemini/`, `intent/`, `association/`, `memory/`, `loops/`; semantic/security/reconstruction tests | Ambiguity/negation/cancel/evidence/injection/error plus real smoke; planned |
| B05 | 9.1–9.3 / 9.5, bagian B 9.4 / 9.6 | Findings/options/review/reanalysis/journal/brief/report, query/metrics disposition, diagnostics/retention; sesudah B04 | `advisory/`, `review/`, `briefs/`, `exports/`, `queries/`, analysis persistence; renderer/security/failure tests | Scoped evidence, append-only/stale, redaction/HTML/formula escaping, no command execution; planned |
| B06 | Acceptance mandiri §6.3, prasyarat Phase 10 | Seluruh B01–B05; fake platform shared suite, package security/recovery/semantic tests, separate real-provider evidence | `tests/contracts/`, package suites, `docs/testing/`, manifest | Entrypoints/routes/migrations/config/dependencies/handlers/versions/SHA/checks/limits; planned |

## Pelaksanaan B02.1 — Phase 6.2

Pure `plan_chunks`, local strict `AudioLimits`/metadata, `AudioTools.discover/probe/decode`
dan context manager `prepare_audio` tersedia di `backend/flowlens/audio/`.
Input authorized lokal dari caller disalin ke private scratch setelah hash checks;
ffprobe/FFmpeg menerima fixed argument lists, file/container whitelist, output cap,
timeout/kill/wait dan safe errors. Source/raw tidak menjadi output target.
Chunk mono PCM16 mempertahankan channel index, frame/source/session mapping,
unknown alignment, coverage gaps dan intentional overlap. Limits/usage/provenance,
commands dan real acceptance: [evidence B02.1](../testing/b021-evidence.md).
Desain: [ADR 0003](../adr/0003-controlled-local-audio.md).

Default16kHz, ≤50s/chunk, <10MB termasuk WAV header; overlap1s ikut total output
budget. Input512MiB, ≤3600s, ≤2channels/192kHz; output budget512MiB, ≤512chunks,
probe10s/decode120s. Ini engineering baseline, bukan provider quota terverifikasi.
Local records tidak mengubah frozen DTOs1.0.0. Executor tidak menerima labels/oracles,
tidak membuka DB dan tidak mendaftarkan handler/promotion/pipeline readiness.

Real B02.1 acceptance kini done: toolchain Gyan9.0.2 terisolasi di ignored
`artifacts/reports/b022-tools/`, publisher archive checksum cocok, CLI versions dan
binary checksums tercatat di evidence. Tidak mengubah global PATH atau fixtures.
Next implementation unit sesudah B02.2 adalah B03 STT V2/transcript lifecycle.
Transcript overlap dedup adalah B03. Paket B, parent6/9 dan gates tetap terbuka.

## Pelaksanaan B01

Config foundation tervalidasi dan dibekukan per session/run/revision beserta
input/config hash. Satu tabel `analysis_configurations` cukup untuk unit awal;
tidak membuat tabel transcript/intent/review atau menerima JobResult fase berikutnya.
Repository factory menerima connection dan UOW guard dari composition melalui
registration; service hanya memakai TransactionFactory/UnitOfWork/Repository ports.
Tidak mengimpor storage/auth/jobs/API internal A.

Migration `analysis.0001` bergantung pada `platform.0001` dengan scoped FK ke
platform revisions/runs. Harness MOCK menyediakan reference schema minimal dan
disposable SQLite dengan FK aktif. Data parent harus disediakan platform, bukan
dibuat otomatis repository B. Config append, audit dan event berbagi UOW; caller
memegang commit serta publication sesudah commit. Provider calls tidak diperlukan.

Inventory/purge hanya mencakup configuration scope yang telah diimplementasikan.
Snapshot domain dan job handlers belum tersedia: registration tidak memasangnya;
AnalysisModule menolak validate/accept/snapshot dengan NOT_EVALUABLE. Readiness
selalu false sampai pipeline benar-benar tersedia. Tidak ada business routes.

Status akhir B01: source/build/standalone runtime/tests terbukti. B02.1 real acceptance
dan B02.2 standalone acceptance done; B03 in_progress; B04–B06 planned.
Entry point `flowlens.analysis:register_analysis(config, transactions)` mengembalikan
ModuleRegistration. Repository factory `(connection, guard)` tersedia melalui
`repositories["analysis.configuration"]`; platform composition belum dipasang.
Service configure/purge tidak melakukan commit; caller wajib memakai UOW yang sama
dan explicit commit. Inventory memakai TransactionFactory yang disuntikkan.
Config events adalah internal ledger metadata (bukan public StreamEvent atau DTO
observer). Tidak ada transcript/secret/provider payload. Purge menghapus tabel B
pada exact session/run/revision; ledger/audit platform mengikuti retention A.
Tidak ada snapshot domain maupun handlers yang mengembalikan sukses kosong.

`AnalysisRepository` untuk transcript/review/association/memory/findings/briefs
belum diimplementasikan; itu B03–B05. AnalysisModule signatures validate/accept/
snapshot/purge tetap mengikuti ports aktual; tiga operasi pipeline menolak
NOT_EVALUABLE sampai domain lifecycle tersedia. Accepted-result receipts dan
idempotency coordinator belum masuk B01; shared suite hanya membuktikan reference
behavior, bukan real accepted pipeline.

## External dependencies

B02: FFmpeg/ffprobe binary/version dan controlled execution limits. B03:
`google-cloud-speech`, GCP credential, V2 region/locale/model/recognizer compatibility,
quota/budget dan hak transfer input. B04: `google-genai`, akses target
`gemini-3.8-flash` dan Developer API Interactions yang diverifikasi sebelum digunakan;
tidak mengganti provider diam-diam. B03/B04 real smoke terpisah dari MOCK.
`hold-short.wav` synthetic NOT_GOLD sampai pronunciation/time-span audit; evaluator
labels/oracles tidak menjadi runtime input. Domain review, held-out benchmark dan
operational validation belum dilakukan.

## Verifikasi dan handoff

Baseline track B dijalankan sebelum edit source. Acceptance B01: disposable tests,
shared contracts A/B, baseline track B CLI serta B01 standalone CLI, Ruff/format,
mypy, generated schema drift, Bandit/dependency audit/build dan git diff --check.
Windows tidak mendukung host A yang mengimpor fcntl; tidak mengubah Paket A untuk
menutup batas platform tersebut. Bukti unit dan hasil aktual dicatat di
`docs/testing/b01-evidence.md` setelah pemeriksaan. B01 tidak menutup Phase 7.3
atau parent Phase 6/9, Paket B maupun G-BE/G-FE/G-DELIVERY.

Evidence: [B01](../testing/b01-evidence.md), [B02.1](../testing/b021-evidence.md),
[B02.2](../testing/b022-evidence.md). Readiness tetap false.

## Pelaksanaan B02.2 — Phase6.4

`AudioWorker.run_once/serve` dalam dedicated process menerima frozen JobClient dan
AssetAccess plus internal InputAccess binding. Config strict/bounded, satu authorized
asset/context per lease, scope/revision/input/config/stage checks, bounded ranges/hash,
heartbeat selama processing, cancellation/deadline/lost lease/tool kill/reap,
artifact+private provenance submission dan typed JobResult/CommitReceipt tersedia.
`python -m flowlens.testing.audio_worker [--real]` adalah standalone executable MOCK;
--scenario cancel/deadline/shutdown/heartbeat-failure/timeout memberi process negatives.
No runtime DB/A/evaluator imports, no provider call atau real A/B composition.

Internal binding dibutuhkan karena JobLease tidak membawa metadata asset/clock/gaps/
permissions. Failure audio memakai existing FAILED/INVALID_AI_OUTPUT; cancelled/stale/
expired attempt tidak dikirim sebagai sukses. JSON_REPORT provenance memerlukan audio
capability; platform tetap memegang promotion, cleanup staged artifact dan accepted
state. Port adapters wajib bounded timeout/thread safety/auth; frozen sync ports tidak
dapat menghentikan adapter yang hang. Lease clock default epoch ms, injectable;
real A transport harus reconcile semantics/binding/provenance sebelum integration.

Same live attempt tidak diproses dua kali. Ambiguous result boleh resend exact candidate
sekali; fresh attempt/lease dari coordinator untuk retry/restart, tanpa reuse scratch/
cancelled staging. No exactly-once provider billing claim. No accepted-state handler
registered. Detail config/tool/fixture/check commands/actual results/limitations ada
di B02.2 evidence. Combined B218 PASS; B01 regression21 dan contractsB66 tetap PASS.
Native B17 files/full Linux-target41 mypy PASS; whole native Windows tetap7 errors A.
Next B03 tetap membutuhkan STT V2 access/config/quota/budget/rights dan real synthetic
smoke terpisah; overlap dedup, transcript correction/evidence/stale lifecycle belum ada.

## Pelaksanaan B03 — standalone adapter dan transcript lifecycle

Status **in_progress/partial**, bukan done. Dua subunit deterministic terbukti:

- B03.D1: strict explicit STTConfig/ProviderApproval/AuthorizedChunk, Google V2 SDK
  adapter dan cancellable bounded executor, full B02 metadata validation, raw response/
  hypothesis/word provenance, local/source/session timing, silence/partial/unknown
  clock handling, canonical exact-time overlap reconciliation dengan origin refs.
  Tidak memilih effective model/region atau memanggil provider nyata.
- B03.D2: analysis.0002 dan injected scoped repositories, append-only corrections
  dengan actor/counter/original/previous refs, latest revision view, transcript/audio
  evidence mapping, stale dependencies dan reanalysis invalidation. Caller UOW
  mengikat domain/evidence/audit/safe events dan memiliki commit/publication.

Source providers/stt/{models,adapter}.py dan analysis/transcript{_records,_projection,
_store,s}.py; separate register_transcripts menyediakan lifecycle/migrations/
factories/purge. B01 migration/export compatible; lazy registration mencegah SQLite
writer import melalui record models. Frozen1.0.0 unchanged; readiness false dan
STT accepted-result handlers/routes belum dipasang. Authority/checkpoint/budget
callbacks tetap wajib injected dari platform; permissive MOCK bukan implementation A.

Acceptance aktual: B03.D1 101tests dan D2 40tests PASS; combined analysis/contractsB
359 PASS/no skip, contractsA66 PASS; B/B01/worker/STT/transcript standalone PASS,
actual FFmpeg bridge terpisah dari MOCK SDK. Ruff/format, native B26-file mypy,
Linux-target50-file mypy, schema drift, Bandit/dependency audit/build/diff checks
tercatat pada [B03 evidence](../testing/b03-evidence.md).
[ADR0004](../adr/0004-private-transcript-provenance.md) mencatat private provenance,
unknown-clock wire limitation, conservative dedup dan correction-counter policy.

Next tetap B03 closure: operator-approved GCP credential/project/API/model/locale/
region/recognizer/features/quota/billing/logging/budget, real synthetic smoke,
audited pronunciation/critical-slot/timestamp benchmark dan worker/private artifact/
coordinator reconciliation. Real smoke0; present-only environment audit tidak
menemukan project/config/budget/credential atau standard ADC. Tidak mengklaim account
settings sudah diperiksa via authenticated API. No credential contents printed.
Phase7.1–7.4 dan PaketB tetap in_progress; B04 planned sampai prerequisites tertutup.
G-BE/G-FE/G-DELIVERY unchanged; no A/front-end/container/deployment work.
