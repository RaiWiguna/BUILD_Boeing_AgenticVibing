# Manifest dan handoff integrasi Paket A

10 Oktober 2026, branch `feat/backend-aben`. A10.1 commit **eb5205b33cab76b991eea08ca671acd4431c83b3**, prerequisite **1f88f38971f1e171fd2421aa8647424e429e26f1**. [Machine manifest](package-a-manifest.json) dihasilkan dari source aktual:134 source/contract/config hashes,66 route/method pairs termasuk WS/HEAD,18 immutable migrations dan62 actual fresh-SQLite tables. [Acceptance evidence](../testing/a101-evidence.md) dan [pengukuran](../testing/a101-benchmark.json) adalah input, bukan klaim provider/domain.

Candidate handoff final adalah commit yang membawa manifest, termasuk perbaikan reservation routes lazy FastAPI pada A10.2. Self-reference commit tidak ditulis sebagai SHA tebakan dalam manifest; resolve identitas immutable dengan:

```sh
git log -1 --format=%H -- docs/development/package-a-manifest.json
.venv/bin/python scripts/checks/package_a_manifest.py --check
```

Manifest mengikat bytes aktual melalui source_sha256; checker merekonstruksi inventory dari current source dan menolak drift. SHA final juga dilaporkan pada hasil sesi. A10.2 memasukkan fix host route guard dan5 regression cases, lalu memisahkan recheck authority dari pembacaan source records yang tidak diperlukan pada context/public projection sesudah rekonfirmasi timing gagal517ms. Recheck grant/worker/revision/rights dan reconstruction validation tetap berjalan. Kontrak1.0.0/lock/migrations dan workload/threshold tidak diubah. [Final audit/check record](../testing/a10-completion-audit.md).

## Menjalankan A tanpa B

Dari root repository, gunakan Python3.12 dan environment locked. Setup mengikuti [foundation](backend-foundation.md): `.venv/bin/uv sync --locked` sesudah virtualenv/runtime tersedia. Runtime project version0.1.0; full resolved runtime/dev versions dan lock SHA ada di manifest. Google STT/Gemini SDK adapters/worker executable belum merupakan runtime A; `soundfile` dipakai untuk inspection input, `Shapely` untuk kernel deterministik.

Bootstrap admin sebelum API mengambil owner lock; input password melalui terminal tersembunyi, tanpa default password, argument password, atau secret file yang masuk Git:

```sh
umask 077
mkdir -p data/package-a/db
.venv/bin/python -m flowlens.cli.bootstrap_admin \
  --database data/package-a/db/flowlens.sqlite3 --login administrator

FLOWLENS_PROFILE=development \
FLOWLENS_DB_PATH=data/package-a/db/flowlens.sqlite3 \
FLOWLENS_IMPORT_STAGING_PATH=data/package-a/imports \
FLOWLENS_RAW_ASSETS_PATH=data/package-a/raw \
FLOWLENS_ARTIFACT_STAGING_PATH=data/package-a/artifacts \
FLOWLENS_RETENTION_JOURNAL_PATH=data/package-a/current-journal \
.venv/bin/python -m flowlens.api.serve
```

Host default `127.0.0.1:8000`, satu API writer, no reload, access payload logs disabled, forwarded headers disabled, WS frame1024bytes. Ctrl-C menghentikan runtime yang dibuat operator. Paths adalah contoh root privat yang di-ignore, bukan data yang diprovision oleh handoff ini. Semua root lokal terpisah dan owner-only, tanpa symlink pada path/ancestors; gunakan canonical path. Journal adalah **directory ledger/head** di luar DB/raw/imports/artifacts serta restore targets, bukan file SQLite. DB/ownership lock dipegang API; maintenance/bootstrap tidak berjalan bersama owner API. Production profile, non-loopback bind dan workers>1 ditolak; jangan mengatasi gate dengan mengubah config validation.

Expected native results pada konfigurasi ini: `/health`200 alive/development; `/release.json`200 metadata aman/provider_verifiedfalse; `/openapi.json`200 memuat actual routes; `/ready`503 LOCAL_PLATFORM/HOST_ONLY karena coordinator belum configured; catalogue tanpa cookie401. Test executable [package_a_startup.py](../../scripts/checks/package_a_startup.py) menjalankan pola launcher tersebut pada disposable canonical paths/native HTTP lalu menghentikan own subprocess. Bootstrap memilih private credential dan tidak dipaksa mengganti password; akun created/reset dengan temporary credential wajib password change melalui `/api/v1/auth/password`. Gunakan exact Origin dan CSRF session untuk mutations. Admin tidak otomatis memiliki session/audio/export/truth grants. Account management, session grants dan worker provisioning tersedia sebagai trusted Python services pada app.state; tidak ada public users/grants/provisioning HTTP endpoint atau CLI tambahan yang diasumsikan tersedia. Import dan grant workflow: [authentication](authentication.md), [authorization](authorization.md), [import commit](import-commit.md), [media/evidence](private-assets-evidence.md).

Health/readiness tidak mengklaim G-BE. Python composition yang menyediakan coordinator dan semua dependencies dapat menghasilkan readiness200 LOCAL_PLATFORM; provider_verified/integration_gate tetap explicit dan tidak berubah menjadi production certification. Default host tidak menyuntikkan fake B; fake hanya acceptance test profile.

## Config, routes dan migrations yang benar-benar tersedia

`config_environment_to_field` dan defaults pada machine manifest diambil langsung dari AST `HostSettings.from_environment` dan typed settings. Supported fields: FLOWLENS_PROFILE/HOST/PORT/API_WORKERS/ORIGIN/DB_PATH/IMPORT_STAGING_PATH/RAW_ASSETS_PATH/ARTIFACT_STAGING_PATH/RETENTION_JOURNAL_PATH/MINIMUM_FREE_BYTES/RELEASE_SHA/LOCK_SHA256. Unknown FLOWLENS_* ditolak. WEB_CONCURRENCY/UVICORN_WORKERS hanya1. Origin HTTP hanya loopback/localhost; HTTPS origin untuk configured authentication berbeda dari menyediakan TLS deployment. Release SHA/lock hash optional declared identifiers; absent dilabel unrecorded. Jangan menyalin daftar target env cloud/secret-file PRD§31.4 sebagai config host yang sudah berjalan; B adapter configuration perlu loader/integrasi sendiri.

| Actual route group | Pemilik dan authority |
| --- | --- |
| health/ready/release/OpenAPI/docs | Host, sanitized dependency/release metadata; bukan provider/domain readiness |
| /api/v1/auth/* | Human cookie/expiry/rotation/password; mutation Origin+CSRF |
| /api/v1/imports/{id}/metadata/commit | Admin draft owner, explicit rights/clock/retention/import commit |
| sessions, sources, history, snapshot, playback, legacy-history | Live session/object grants; server-built time/view/run context, durable controls/idempotency |
| /api/v1/sessions/{session_id}/stream | Native typed WS, Origin/cookie/live grants, sequence/snapshot/resync; global32/per-account4 concurrent connections |
| assets/{id}/audio | Current audio grant/rights; validated bounded Range/HEAD/ETag; chunk authority rechecked |
| geometry/rules/alerts/indicators | Source-observed, evidence-linked versioned lab rules; UNKNOWN/NOT_EVALUABLE preserved |
| analysis-runs, inspect/cancel, session usage | Coordinator must be explicitly composed; grants, revision/deadline/budget/idempotency |
| artifacts/inventory/download | Current scope/export/audio-export permission, expiry/hash; no B report renderer |
| admin provider-profiles/checks/history, disk, usage, ops/session audit, purge | Active admin plus required object grants; adapter diagnostics explicit mock/unavailable; purge preview/resume/tombstones |
| /internal/jobs/*, assets audio, artifacts PUT | Worker bearer/server scope only; browser cookies/Origin forbidden; public edge isolation remains delivery obligation |

Exact paths/methods berasal dari effective FastAPI matching inventory, dengan OpenAPI path coverage assertion. Module routes yang membayangi included HTTP/WS host paths ditolak, termasuk nested prefixes;5tests membuktikan collision rejection dan distinct nested path diperbolehkan. Guard menggunakan effective_candidates pada **locked FastAPI**; dependency update harus menjalankan ulang tests, bukan menganggap internal representation tetap sama. Final OpenAPI composition/generated frontend client freeze masih Phase10; frozen baseline `contracts/openapi/baseline.json` tetap MOCK exchange schema.

Schema order: platform.0001→platform.0018, owner A, checksum/dependencies exact di manifest. Default startup melakukan transactional fresh/upgrade sesuai applied ledger; checksum mismatch, unknown ledger/unversioned DB/downgrade ditolak. Historical profile `legacy-2660222-archive-1` melalui `.venv/bin/python -m flowlens.cli.migrate_archive --source ... --target ...`, read-only source/separate target, original IDs/events/frame/command preservation dan private quarantine; tidak mengonversi old operator keys menjadi auth. [Compatibility](legacy-compatibility.md). Tidak ada migration baru pada A10.1/A10.2, seluruh18source definitions unchanged dari prerequisite.

Import ceilings final:512MiB/file,2GiB/session,2labelled channels,120channel-minutes total; rate8–192kHz/finite full decode,200krows per sidecar,64MiB sidecar/whole-JSON8MiB,4files,4uploadslots,100draftglobal/16ownerdefault,TTL24h. Benchmark mengatur owner-drafts100 melalui `ImportLimits`, tidak mengubah byte/duration ceilings. Archive metadata100sesi berbeda dari draft quota; default bukan janji100unfinished uploads per account.

## Frozen ports dan wiring yang wajib dilakukan B/composition

Canonical [ports](../../backend/flowlens/contracts/ports.py) dan [version policy](../api/shared-contracts.md) tetap1.0.0. A menyediakan actual SourceReader(Sources), GeometryReader(Occupancy), AssetAccess(Assets), EvidenceService(EvidenceRegistry), TransactionFactory/UnitOfWork(Database), JobClient(WorkerJobs melalui coordinator/internal transport), ArtifactLifecycle(Artifacts). Source/event/availability/time/raw immutability, rights, context dan accepted state tetap authority A. Model output/schema validation tidak menggantikan semantic/evidence authorization. B tidak membuka atau me-mount SQLite dan tidak mengimpor internal A; remote transport adapters milik worker/composition memakai frozen interfaces.

Default registered B handlers/repositories/routes/migrations/snapshot/purge **kosong**, bukan business placeholder yang dianggap available. Host menerima explicit constructor arguments `modules`, `mutation_operations`, `analysis_module`, `context_reader`, `job_policies`, `provider_adapters`, `repository_factories`; exact signature/registration/policy fields ada pada manifest.

1. Serahkan ModuleRegistration contract1.0.0 dengan unique routes/name/migration IDs dan dependencies, actual analysis repository factories untuk analysis.* serta output→namespace mapping. Host mengonsumsi **routes/migrations/snapshot/purge/inventory**. Fields `services`, `repositories`, `job_handlers`, `readiness`, `config_keys` adalah descriptors; host tidak otomatis memasangnya dari module. Composition harus menerjemahkan descriptors ke trusted host arguments/policies/adapters, serta menyediakan state-aware service binding pada lifecycle yang sesuai.
2. Pasang **AnalysisModule bersama StagePolicy** untuk setiap AUDIO/STT/INTENT/ASSOCIATION/MEMORY/FINDINGS/BRIEF/QUERY/EXPORT stage yang disediakan. Policies membawa version, rights, outputs, handler, ready, reservation, RunConfig(model/API/SDK/prompt/reducer/rule), concurrency/lease/retry. `AnalysisModule.validate` berjalan di luar DB lock; accepted write menggunakan **StagePolicy.handler**, bukan automatic dispatch `ModuleRegistration.job_handlers` atau `AnalysisModule.accept`. Bind handler tersebut ke B's registered accept function. Handler menerima A-owned UOW dan tidak commit/rollback sendiri; coordinator memegang atomic domain/evidence/audit/receipt/event/budget commit.
3. Pasang **satu** module.snapshot_reader atau AnalysisModule.snapshot; keduanya sekaligus ditolak. Callback scoped by context, tanpa provider call pada seek; source events B diverifikasi terhadap actual observed source. ContextReader menyediakan bounded read-only lookup dan rules context; tidak mempercayai actor/session/role/as-of yang ditentukan model.
4. Daftarkan inventory_namespaces analysis.* unik dan purge_handler. Callback host dipetakan melalui namespace **pertama**; jika beberapa namespace, callback wajib menghapus seluruh inventory module sesuai registered declaration. Unknown/unregistered inventory menolak purge. A mengelola source/artifact bytes, tombstones dan retry coordinator; B menyediakan transcript/memory/findings/options/reviews/brief/query/report/provider scratch inventory dan removal behavior. Provider prompt/raw text/derived/export data tidak boleh tertinggal sebagai undeclared namespace/table.
5. Daftarkan provider adapters di Providers melalui AdapterBinding GOOGLE_STT/GEMINI serta real worker transport/credentials yang eligible. Fake adapters hanya test profile, tidak menjadi fallback provider failure. Actual release profile/model/SDK/locale/region/quota/rights/budget dan smoke evidence wajib diserahkan B. Target PRD Gemini `gemini-3.8-flash` belum verified; jangan mengganti model diam-diam.
6. Reconcile **maintenance/restore composition**: current standalone CLI membuka A migration manifest saja dan menolak unknown B ledger. Python Maintenance/Snapshots menerima callbacks, tetapi tidak otomatis memuat B schema/repository factories. Phase10 harus menyediakan verified B-aware maintenance composition/entrypoint dan menguji registered inventory/table catalog, purge, consistent backup/isolated restore/current tombstones sebelum mengklaim integrated recovery. Ini deliverable entry/reconciliation nyata, bukan capability yang sudah dibuktikan oleh A fake callbacks.

A10 manifest tidak melakukan wiring real B tersebut. Migration namespaces/transactions dan actual B table inventory harus diaudit ulang; extension cannot use arbitrary SQL/table purge declaration sebagai pengganti frozen record namespace.

## Sensitive-data inventory, retention dan local recovery

Machine manifest mempunyai sensitive_inventory dan actual tables/source paths. Raw audio/sidecars immutable, draft uploads, derivative/report assets, evidence quotes, source rights/provenance, transcript candidates/accepted results di DB, account password hashes, session/worker token digests, grants/revisions/usage/audit/receipts/checkpoints adalah privat. Raw token hanya cookie/worker provisioning response sesuai scope; opaque asset IDs bukan permission. API serializers menolak truth/private/evaluator source; current log fields IDs/status/timing/usage/hashes, tanpa audio/transcript/prompt/key/header/URL. Provider credentials tidak ada dalam manifest/release/backup.

Retention coordinator memblokir akses expired source/artifact dan memproses purge retry; current journal ledger/head berada di luar restored roots. Backup tetap **LOCAL_PRIVATE_UNENCRYPTED**, mencakup sensitive DB/assets dan curated release/config metadata. Tombstones/expiry disesuaikan sebelum restored archive bisa dibaca; old auth/worker credentials dan active jobs dibatalkan, completed history/grants/revisions/evidence/checkpoints tetap tersedia. Account/grant snapshot point-in-time membutuhkan review operator sebelum promotion. Background scheduler/off-host encrypted delivery dan instantaneous deletion semua salinan belum tersedia.

[Recovery runbook](recovery.md) menyediakan actual commands check/backup/verify/restore/prune/cleanup. Jalankan ketika own API stopped, gunakan target baru, current journal independen, trusted manifest hash, root privat. CLI help/actual crash/restart/WAL/hash/ENOSPC/retention tests tersedia; tidak melakukan destructive reset pada DB developer/shared. Code rollback tidak membalik schema; shared VM RPO24h/RTO4h/off-host operator tetap external delivery dependency.

## Commands, hasil dan entry menuju Phase10

[A10.1 result record](../testing/a101-evidence.md) mencatat full715tests + separate measured capacity, contracts66/track, lint/format/mypy78/drift/lock/build/security/dependency checks. [A10 final audit](../testing/a10-completion-audit.md) mencatat checks A10.2, final commit/source reconciliation, fresh native startup, scans dan benchmark reconfirmation. Reproduksi:

```sh
.venv/bin/python scripts/checks/package_a_manifest.py --check
.venv/bin/python scripts/checks/package_a_startup.py
.venv/bin/pytest tests/platform -q
FLOWLENS_RUN_CAPACITY=1 FLOWLENS_CAPACITY_REPORT=artifacts/reports/a102-benchmark.json \
  .venv/bin/pytest tests/platform/test_acceptance_capacity.py -q
.venv/bin/pytest tests/contracts --track A -q
.venv/bin/pytest tests/contracts --track B -q
.venv/bin/ruff check backend tests scripts
.venv/bin/ruff format --check backend tests scripts
.venv/bin/mypy
.venv/bin/python -m flowlens.contracts.generate --check
.venv/bin/bandit -r backend/flowlens -ll
.venv/bin/pip-audit --local
.venv/bin/uv lock --check
.venv/bin/uv build --out-dir artifacts/reports/a102-dist
.venv/bin/python scripts/checks/scan_secrets.py --report artifacts/reports/a102-tracked-secrets.json
.venv/bin/python scripts/checks/scan_secrets.py --staged --report artifacts/reports/a102-staged-secrets.json
git diff --check
```

Bukti platform timing/capacity final terbatas pada synthetic profile yang tercatat:20objects,60min replay/60s sample cadence,100metadata sessions dan2×60min PCM16/16kHz mono audio. ASGI request percentile bukan LAN/browser measure, bukan VM4vCPU/8GiB atau1Hz track throughput. Rerun final integration dengan B real, dependency/hardware/provider config dan source cohorts efektif; jangan menganggap narrow p95 margin sebagai SLA.

**Paket A selesai secara mandiri setelah kedua commit dan final audit; Phase10 belum selesai dan G-BE tetap not_started.** Next action konkret: terima B candidate+acceptance+contract1.0.0+registration/schema/config/inventory manifest+real synthetic STT/Gemini smoke, reconcile wiring/recovery di atas, lalu jalankan Phase10.1 actual API/SQLite/worker composition dan integrated negative/failure/canonical scenarios, provider/domain/held-out/timing profiling serta final OpenAPI/client freeze sesuai gate. Tanpa B candidate/credentials/budget/source rights/model/locale/region/account evidence, provider integration menunggu input tersebut; pekerjaan mandiri Paket A tetap dapat selesai.

Source A **available**, tests/build **PASS**, platform baseline **measured**; real B composition **not_started**, provider verified **NO**, expert/domain **NOT_DOMAIN_VALIDATED**, operational validation **NO**. UI/container/deployment/off-host restore rehearsal belum dikerjakan; tidak ada push/merge/amend/deployment atau provider call oleh handoff ini.
