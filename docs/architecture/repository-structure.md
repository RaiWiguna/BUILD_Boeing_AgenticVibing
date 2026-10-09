# Struktur Repository ATC FlowLens

Tanggal: 9 Oktober 2026. Status: **A01–A06 tersedia dan standalone platform acceptance selesai; B/provider/domain pipeline, A07.1–A07.2 replay/checkpoints/controls tersedia; A07.3–A10, frontend/deployment belum diimplementasikan**. Tree di bawah adalah snapshot scaffold7 Oktober; source terkini dirujuk melalui [A04](../testing/a04-evidence.md), [A05](../testing/a05-evidence.md) dan [A06](../testing/a06-evidence.md).

## Dasar penempatan

PRD membagi alur utama menjadi import sumber, clock/replay, observasi/geometri, audio/jobs, STT, intent/association, memory/findings, advisory, review, serta debrief/export. Struktur berikut memberi tempat untuk setiap responsibility tersebut, sekaligus menjaga evaluator truth dan private runtime data terpisah.

Backend memakai satu package `flowlens` dengan modul responsibility, tanpa menambah service boundary yang tidak dibutuhkan v1. Frontend memakai feature folders sesuai journeys pengguna. Kontrak wire/generated artifacts, tests/fixtures, evaluator materials, dokumentasi, dan delivery tooling berada pada area tersendiri.

Scaffold dibuat sekaligus untuk memperjelas tujuan penempatan. Implementasi tetap berurutan: **backend lengkap → frontend lengkap → containerization → local/single-VM deployment**. Keberadaan folder frontend/deploy/workflows tidak memulai track tersebut atau menutup gate.

## Tree lengkap

`.git/` tidak ditampilkan. `.gitkeep` berukuran nol mempertahankan folder kosong di Git; hapus ketika folder sudah mempunyai file sebenarnya. Snapshot ini menjelaskan layout awal; inventory implementasi terkini dan manifest/toolchain ada pada phase evidence/workflows.

```text
BUILD_Boeing_AgenticVibing/
├── .agent/
│   ├── PRD.md
│   ├── implementationPhases.md
│   ├── rules.md
│   └── sessionHandoff.md
├── .github/
│   └── workflows/
│       └── .gitkeep
├── artifacts/
│   ├── coverage/
│   │   └── .gitkeep
│   ├── exports/
│   │   └── .gitkeep
│   ├── playwright/
│   │   └── .gitkeep
│   └── reports/
│       └── .gitkeep
├── backend/
│   └── flowlens/
│       ├── advisory/
│       │   └── .gitkeep
│       ├── api/
│       │   ├── dependencies/
│       │   │   └── .gitkeep
│       │   ├── routes/
│       │   │   └── .gitkeep
│       │   └── schemas/
│       │       └── .gitkeep
│       ├── assets/
│       │   └── .gitkeep
│       ├── association/
│       │   └── .gitkeep
│       ├── audio/
│       │   └── .gitkeep
│       ├── audit/
│       │   └── .gitkeep
│       ├── auth/
│       │   └── .gitkeep
│       ├── briefs/
│       │   └── .gitkeep
│       ├── cli/
│       │   └── .gitkeep
│       ├── clocks/
│       │   └── .gitkeep
│       ├── contracts/
│       │   ├── internal/
│       │   │   └── .gitkeep
│       │   └── public/
│       │       └── .gitkeep
│       ├── core/
│       │   └── .gitkeep
│       ├── evidence/
│       │   └── .gitkeep
│       ├── exports/
│       │   └── .gitkeep
│       ├── geometry/
│       │   └── .gitkeep
│       ├── imports/
│       │   └── .gitkeep
│       ├── intent/
│       │   └── .gitkeep
│       ├── jobs/
│       │   └── .gitkeep
│       ├── loops/
│       │   └── .gitkeep
│       ├── memory/
│       │   └── .gitkeep
│       ├── ops/
│       │   └── .gitkeep
│       ├── permissions/
│       │   └── .gitkeep
│       ├── prompts/
│       │   ├── association/
│       │   │   └── .gitkeep
│       │   ├── brief/
│       │   │   └── .gitkeep
│       │   ├── intent/
│       │   │   └── .gitkeep
│       │   ├── options/
│       │   │   └── .gitkeep
│       │   └── query/
│       │       └── .gitkeep
│       ├── providers/
│       │   ├── gemini/
│       │   │   └── .gitkeep
│       │   └── stt/
│       │       └── .gitkeep
│       ├── queries/
│       │   └── .gitkeep
│       ├── replay/
│       │   └── .gitkeep
│       ├── review/
│       │   └── .gitkeep
│       ├── rules/
│       │   └── .gitkeep
│       ├── sources/
│       │   └── .gitkeep
│       ├── storage/
│       │   └── sqlite/
│       │       └── migrations/
│       │           └── .gitkeep
│       └── workers/
│           ├── analysis/
│           │   └── .gitkeep
│           └── audio/
│               └── .gitkeep
├── contracts/
│   ├── examples/
│   │   └── .gitkeep
│   ├── json-schema/
│   │   └── .gitkeep
│   └── openapi/
│       └── .gitkeep
├── data/
│   ├── assets/
│   │   ├── derived/
│   │   │   └── .gitkeep
│   │   └── raw/
│   │       └── .gitkeep
│   ├── backups/
│   │   └── .gitkeep
│   ├── db/
│   │   └── .gitkeep
│   ├── exports/
│   │   └── .gitkeep
│   ├── logs/
│   │   └── .gitkeep
│   ├── scratch/
│   │   └── .gitkeep
│   └── secrets/
│       └── .gitkeep
├── deploy/
│   ├── caddy/
│   │   └── .gitkeep
│   ├── compose/
│   │   ├── local/
│   │   │   └── .gitkeep
│   │   └── vm/
│   │       └── .gitkeep
│   ├── config/
│   │   └── .gitkeep
│   └── docker/
│       ├── backend/
│       │   └── .gitkeep
│       └── frontend/
│           └── .gitkeep
├── docs/
│   ├── adr/
│   │   └── 0001-modular-repository-layout.md
│   ├── api/
│   │   └── .gitkeep
│   ├── architecture/
│   │   └── repository-structure.md
│   ├── data/
│   │   └── .gitkeep
│   ├── development/
│   │   └── .gitkeep
│   ├── evaluation/
│   │   └── .gitkeep
│   ├── operations/
│   │   └── .gitkeep
│   ├── product/
│   │   └── .gitkeep
│   ├── releases/
│   │   └── .gitkeep
│   ├── security/
│   │   └── .gitkeep
│   ├── testing/
│   │   └── .gitkeep
│   └── README.md
├── evaluation/
│   ├── benchmarks/
│   │   └── .gitkeep
│   ├── fixtures/
│   │   ├── labels/
│   │   │   └── .gitkeep
│   │   └── oracles/
│   │       └── .gitkeep
│   ├── protocols/
│   │   └── .gitkeep
│   └── reports/
│       └── .gitkeep
├── frontend/
│   ├── public/
│   │   └── .gitkeep
│   ├── src/
│   │   ├── api/
│   │   │   ├── adapters/
│   │   │   │   └── .gitkeep
│   │   │   └── generated/
│   │   │       └── .gitkeep
│   │   ├── app/
│   │   │   ├── providers/
│   │   │   │   └── .gitkeep
│   │   │   └── routing/
│   │   │       └── .gitkeep
│   │   ├── assets/
│   │   │   ├── icons/
│   │   │   │   └── .gitkeep
│   │   │   └── images/
│   │   │       └── .gitkeep
│   │   ├── components/
│   │   │   ├── domain/
│   │   │   │   └── .gitkeep
│   │   │   ├── layout/
│   │   │   │   └── .gitkeep
│   │   │   └── ui/
│   │   │       └── .gitkeep
│   │   ├── features/
│   │   │   ├── advisory/
│   │   │   │   └── .gitkeep
│   │   │   ├── auth/
│   │   │   │   └── .gitkeep
│   │   │   ├── debrief/
│   │   │   │   └── .gitkeep
│   │   │   ├── evidence/
│   │   │   │   └── .gitkeep
│   │   │   ├── findings/
│   │   │   │   └── .gitkeep
│   │   │   ├── imports/
│   │   │   │   └── .gitkeep
│   │   │   ├── memory/
│   │   │   │   └── .gitkeep
│   │   │   ├── queries/
│   │   │   │   └── .gitkeep
│   │   │   ├── replay/
│   │   │   │   └── .gitkeep
│   │   │   ├── review/
│   │   │   │   └── .gitkeep
│   │   │   ├── sessions/
│   │   │   │   └── .gitkeep
│   │   │   ├── settings/
│   │   │   │   └── .gitkeep
│   │   │   └── transcripts/
│   │   │       └── .gitkeep
│   │   ├── hooks/
│   │   │   └── .gitkeep
│   │   ├── lib/
│   │   │   └── .gitkeep
│   │   ├── styles/
│   │   │   └── .gitkeep
│   │   └── types/
│   │       └── .gitkeep
│   └── tests/
│       ├── components/
│       │   └── .gitkeep
│       └── unit/
│           └── .gitkeep
├── scripts/
│   ├── benchmark/
│   │   └── .gitkeep
│   ├── contracts/
│   │   └── .gitkeep
│   ├── dev/
│   │   └── .gitkeep
│   ├── fixtures/
│   │   └── .gitkeep
│   ├── ops/
│   │   └── .gitkeep
│   ├── release/
│   │   └── .gitkeep
│   └── validation/
│       └── .gitkeep
├── tests/
│   ├── contracts/
│   │   └── .gitkeep
│   ├── e2e/
│   │   └── .gitkeep
│   ├── fixtures/
│   │   ├── audio/
│   │   │   └── .gitkeep
│   │   ├── events/
│   │   │   └── .gitkeep
│   │   ├── layouts/
│   │   │   └── .gitkeep
│   │   ├── manifests/
│   │   │   └── .gitkeep
│   │   └── provider-responses/
│   │       └── .gitkeep
│   ├── integration/
│   │   └── .gitkeep
│   ├── migrations/
│   │   └── .gitkeep
│   ├── performance/
│   │   └── .gitkeep
│   ├── recovery/
│   │   └── .gitkeep
│   ├── security/
│   │   └── .gitkeep
│   └── unit/
│       └── .gitkeep
├── .gitignore
└── README.md
```

## Backend: modular monolith

| Area | Responsibility dan batas |
| --- | --- |
| `backend/flowlens/core/` | Config, IDs, safe errors, context dan primitives lintas modul; hindari menjadi tempat semua business logic |
| `api/routes/`, `api/schemas/`, `api/dependencies/` | HTTP/WS entrypoints, transport schemas dan dependency injection; routes tidak menjadi direct SQL/provider orchestration |
| `auth/`, `permissions/` | Account/session lifecycle, grants, object capability, CSRF dan worker identity |
| `imports/`, `sources/` | Preview/remediation/atomic commit, provenance, permissions, source kind/version dan coverage |
| `assets/`, `audio/` | Private asset metadata/access, range responses, controlled decoding/chunking dan derivative time mapping |
| `replay/`, `clocks/` | Event/reducer/checkpoints, as-known/debrief, clock mappings, controls dan state reconstruction |
| `jobs/` | Durable lease/attempt/budget/deadline/heartbeat/retry/result-commit coordinator |
| `providers/stt/`, `providers/gemini/` | SDK adapters dan versioned request/response mapping; provider-specific payload tidak menjadi public API |
| `intent/`, `association/` | Typed semantic candidates, critical slots, entity/relationship alternatives dan acceptance validation |
| `memory/`, `loops/` | Accepted events/projections, instruction/readback/movement/reviewer dimensions dan matching loop closure |
| `rules/`, `geometry/` | Deterministic observed-only checks, footprint/occupancy/separation, applicability dan alert lifecycle |
| `evidence/`, `review/` | Scoped evidence resolution, quotes/ranges/hashes, append-only human corrections/decisions |
| `advisory/`, `briefs/`, `queries/` | Options/brief/read-only questions, preconditions/unknowns/evidence; tidak ada execute-clearance path |
| `exports/`, `audit/`, `ops/` | Redacted report export, administrative trace, health/readiness/usage/cost/disk/recovery |
| `storage/sqlite/`, `storage/sqlite/migrations/` | API-owned repositories, transactions, schema upgrade dan consistent snapshots; bukan package worker |
| `contracts/public/`, `contracts/internal/` | Versioned Pydantic DTOs untuk public views dan worker protocols; transport schemas reuse DTOs yang sesuai |
| `workers/audio/`, `workers/analysis/` | Separate-process execution untuk audio/STT/analysis; lease/input/result melalui internal API |
| `prompts/intent/association/options/brief/query/` | Templates, output/schema policy dan non-secret version metadata; tidak menyimpan raw participant transcript |
| `cli/` | Bootstrap/migration/maintenance/recovery entrypoints saat diimplementasikan; bukan AI tools |

Nama module bukan kewajiban memecah aplikasi menjadi service baru. Subpackage tambahan hanya dibuat saat responsibility memang membesar. `__init__.py`, contract-only app factory, standalone harness CLI dan root `pyproject.toml`/`uv.lock` kini tersedia pada foundation. Business API/worker entrypoints tetap owner phases A/B.

### Dependency dan authority

- API/service composition memiliki state dan satu SQLite writer.
- Worker boleh memakai contracts, provider adapters, audio processing, serta read-only context ports; worker tidak mengimpor database writer, membuka SQLite, atau me-mount seluruh private raw store.
- Rules/geometri hanya menerima observations yang eligible dan public layout/config; tidak mengimpor evaluator labels, private future schedule, atau provider state.
- Candidate AI melewati schema dan semantic/evidence checks sebelum accepted commit.
- Evaluator scoring membaca accepted outputs melalui authorized export/view; produksi tidak mengimpor `evaluation/`.

Ini boundary target. Folder terpisah belum membuktikan import restrictions, authorization, transactionality, atau truth isolation; semuanya membutuhkan tests saat source tersedia.

## Frontend: features dan shared UI

| Area | Responsibility |
| --- | --- |
| `frontend/public/` | Static assets publik; tidak untuk audio privat, exports, keys, atau evaluator truth |
| `src/app/providers/`, `src/app/routing/` | App composition, auth/capability routing dan TanStack Query context |
| `src/api/generated/` | Generated client/types dari OpenAPI backend; jangan mengedit output untuk mengubah kontrak |
| `src/api/adapters/` | REST/WS wrapper, scoped cache invalidation, snapshot/resync dan typed error mapping |
| `src/components/ui/` | shadcn/ui primitives yang mengikuti tokens dan accessibility conventions |
| `src/components/layout/` | Shell, navigation dan responsive workspace layout |
| `src/components/domain/` | Shared timeline, audio/evidence controls, memory strip dan situation primitives |
| `src/features/` | Auth, sessions, import, replay, transcripts, memory, findings, evidence, review, advisory, queries, debrief dan settings |
| `src/hooks/`, `src/lib/` | Utilities lintas fitur; logic hanya dipindahkan ke sini bila digunakan bersama |
| `src/styles/` | Tailwind setup, tokens dan global styles |
| `src/types/` | View/UI-only models; jangan menggandakan API wire types |
| `src/assets/icons/`, `src/assets/images/` | Build-time public assets yang haknya mencukupi |
| `frontend/tests/unit/`, `frontend/tests/components/` | Frontend unit/component coverage saat harness diprovision |

Feature folder dapat berisi components/hooks/state bila memang diperlukan; scaffold tidak membuat tiga subfolder kosong berulang untuk setiap fitur. Query adalah P1 dan hanya diimplementasikan sesuai disposition roadmap. Frontend mengambil data lewat API/WS, tidak membuka storage/backend secrets atau membuat business authority pengganti.

## Contracts, tests, dan evaluation

| Area | Penggunaan |
| --- | --- |
| `contracts/openapi/` | Generated/versioned REST wire schema dan drift artifacts yang aman |
| `contracts/json-schema/` | Generated/versioned import/worker/AI output schemas; Pydantic tetap authority |
| `contracts/examples/` | Sanitized synthetic valid/invalid examples, tanpa credential atau source privat |
| `tests/unit/` | Backend domain/service/reducer/rule unit tests |
| `tests/contracts/` | Pydantic/OpenAPI/provider/worker protocol validation dan drift |
| `tests/integration/` | Actual API/SQLite/worker flows pada disposable runtime |
| `tests/e2e/` | Python Playwright journeys setelah backend/frontend tersedia |
| `tests/security/` | Permission/truth/tool/media boundaries, injection dan secret exposure negative cases |
| `tests/performance/` | Reproducible replay/provider/commit/UI capacity measurements sesuai tahap |
| `tests/migrations/`, `tests/recovery/` | Fresh/upgrade, restart/lease/durability/backup/restore scenarios |
| `tests/fixtures/` | Synthetic/non-sensitive manifests, events, waveform, layout dan stub provider responses |
| `evaluation/fixtures/labels/`, `evaluation/fixtures/oracles/` | Evaluator-only expected outcomes/independent truth; tidak menjadi source produksi atau AI context |
| `evaluation/protocols/`, `evaluation/benchmarks/` | Rubric, cohort/split policy, metric definition dan scoring harness |
| `evaluation/reports/` | Local restricted outputs; payload default di-ignore, publish hanya ringkasan yang direview dan boleh dibagikan |

Fixtures yang masuk Git bukan tempat raw public-corpus/partner data. Corpus dapat diakses publik tetapi belum tentu boleh direpackage atau dikirim ke cloud. Keys/raw audio nyata, participant truth, dan source-specific permissions tetap private. Memisahkan folder tidak mengubah hak data atau grant runtime.

## Docs, ADR, scripts, dan delivery

`docs/README.md` menjelaskan fungsi architecture, adr, product, api, data, evaluation, development, operations, security, testing, dan releases. `.agent/` menyimpan kontrak, operating rules, roadmap, serta handoff; dokumen tersebut tidak disalin menjadi spesifikasi kedua pada `docs/product/`.

ADR disimpan sebagai `docs/adr/NNNN-kebab-case-title.md`. Nomor `0001` pada tree baru adalah keputusan modular layout; ADR historis sebelum reset tidak dipulihkan otomatis. Accepted architecture decision berbeda dari implemented/verified capability.

| Area | Isi yang dituju dan kapan dibuat |
| --- | --- |
| `scripts/dev/` | Developer setup/runtime helpers ketika backend foundation tersedia |
| `scripts/validation/` | Shared check entrypoints sesuai tooling yang benar-benar diprovision |
| `scripts/contracts/` | Schema/client generation dan drift checks pada backend contract stage |
| `scripts/fixtures/`, `scripts/benchmark/` | Synthetic fixture generation dan controlled evaluation orchestration |
| `scripts/ops/`, `scripts/release/` | Backup/restore/migration/promotion helpers ketika delivery siap |
| `.github/workflows/` | CI definitions setelah checks tersedia; `.gitkeep` bukan workflow executable |
| `deploy/docker/backend/`, `deploy/docker/frontend/` | Python/worker dan static frontend image build definitions setelah G-FE |
| `deploy/compose/local/`, `deploy/compose/vm/` | Local/vm overrides; base Compose diletakkan pada `deploy/compose/` saat implementasi |
| `deploy/caddy/` | Same-origin static/API/WS/audio proxy, TLS VM dan internal-route denial |
| `deploy/config/` | Validated metadata/config examples tanpa secrets |

Tidak ada Dockerfile, Compose YAML, Caddyfile, shell script stub, dependency manifest, atau CI job yang dibuat pada tugas scaffold ini. Cloud calls dan deployment juga tidak dijalankan.

## Private runtime dan generated outputs

| Folder | Isi privat/sementara yang dituju |
| --- | --- |
| `data/db/` | SQLite database/WAL/snapshots pada API owner |
| `data/assets/raw/` | Immutable raw sources/audio dengan opaque storage keys |
| `data/assets/derived/` | Normalized audio/chunks dengan source hash/time mapping |
| `data/exports/` | Scoped/expiring report dan audio export |
| `data/scratch/` | Bounded worker temporary files |
| `data/backups/` | Local consistent backup staging; bukan pengganti off-host backup |
| `data/logs/` | Restricted sanitized operational logs |
| `data/secrets/` | Local secret files, restrictive permission, tidak masuk Git |
| `artifacts/coverage/`, `artifacts/playwright/`, `artifacts/reports/`, `artifacts/exports/` | Generated test/debug outputs; bukan evidence domain yang sudah disahkan |

`.gitignore` mengecualikan payload `data/**`, `artifacts/**`, dan `evaluation/reports/**` sambil memperbolehkan direktori serta `.gitkeep`. Env/credential files, dependency caches, frontend build output, dan Python caches juga di-ignore. Pengecualian `.env.example` hanya untuk contoh tersanitasi saat nanti dibutuhkan.

Compose volumes dan secret provisioning final ditentukan pada delivery stage; direktori lokal ini belum berarti container me-mount atau membagikan semuanya. Worker tidak mendapat DB/raw volume unrestricted. Ignore Git juga bukan permission atau encryption runtime.

## Status dan langkah berikutnya

Struktur folder, README/map, ADR layout, serta konteks setelah reset tersedia. Semua fase implementasi tetap planned dan G-BE/G-FE/G-DELIVERY belum dijalankan.

Langkah berikutnya adalah Phase 0.1: petakan kontrak/scaffold ke requirement, tetapkan build-new/reuse disposition, fixture/independent-oracle plan dan external dependencies. Backend foundation selanjutnya menyediakan actual package/config/contracts/tests. Frontend dan packaging menunggu gate masing-masing.

Implementasi imports saat ini (A04.1): `staging.py` mengelola private owner-scoped draft, `inspection.py` memeriksa native audio/canonical sidecars, dan `routes.py` streaming multipart/preview. Rights/clock/identity/layout preparation A04.2 tersedia pada sources/metadata.py, clocks/normalization.py dan imports/{metadata,normalization}.py; source reader/atomic commit masih A04.3. [Workflow](../development/import-preview.md).

[Import metadata workflow](../development/import-metadata.md) menjelaskan granular envelope dan conservative frozen-contract projection sebelum domain commit.

A06 menempatkan platform-owned scheduler/internal routes di jobs/, tanpa mengimpor internals B. Typed domain repositories memakai injected analysis.* factories; storage private assets/evidence tersedia sejak A04/A05. [Workflow](../development/durable-jobs.md).
