# ATC FlowLens

Workspace untuk membangun replay offline berbukti bagi review komunikasi dan kondisi runway oleh evaluator Tower/Ground.

**Status saat ini (9 Oktober 2026):** baseline Phase0–1 dan Paket A A01–A06 selesai untuk scope platform mandiri. Import commit/source reader, private audio/evidence, durable jobs dan atomic accepted results tersedia. A06 diuji dengan AnalysisModule fake melalui frozen ports; A07.1 observed replay/checkpoints tersedia ([evidence](docs/testing/a071-evidence.md)); controls/REST/WS A07.2–A07.3, B/provider pipeline nyata, geometri A08, ops A09, frontend dan deployment belum tersedia. Contract1.0.0 tetap, current platform migrations0013. Final444 platform tests +66 contracts masing-masing A/B, lint/type/schema/build PASS. Readiness HOST_ONLY503; semua release gates not_started, belum validasi domain/operasional.

Stack target: React, TypeScript, Vite, shadcn/ui; Python, FastAPI, Pydantic; Google Speech-to-Text dan Gemini 3.8 Flash; SQLite; Docker Compose lokal/single VM.

Mulai dari:

- [Foundation workflow](docs/development/backend-foundation.md), [A/B packets](docs/development/backend-packets.md), dan [baseline evidence](docs/testing/phase01-evidence.md).
- [Paket A per unit sesi](docs/development/package-a-execution.md) dan [evidence A01.1](docs/testing/a011-evidence.md).
- [Evidence persistence A01.2](docs/testing/a012-evidence.md).

- [PRD](.agent/PRD.md): requirement produk dan acceptance.
- [Implementation phases](.agent/implementationPhases.md): backend lengkap → frontend lengkap → containerization → deployment.
- [Rules](.agent/rules.md) dan [handoff](.agent/sessionHandoff.md): aturan kerja dan konteks terkini.
- [Peta dokumentasi](docs/README.md).
- [Struktur repository](docs/architecture/repository-structure.md): tree lengkap, ownership, dan boundary.
- [ADR struktur modular](docs/adr/0001-modular-repository-layout.md): keputusan penempatan modul dan artefak.

Controller tetap memegang keputusan dan kewenangan clearance. V1 tidak menghubungkan production feed/audio atau menerbitkan instruksi operasional. Baseline sintetik diberi label yang sesuai; data nyata dan transfer cloud memerlukan hak penggunaan yang mencukupi.

Storage privat berada di `data/`; output sementara berada di `artifacts/`. Git hanya menyimpan `.gitkeep` pada kedua area tersebut. Test fixtures yang masuk Git harus sintetik/non-sensitif dan memiliki hak penggunaan yang sesuai.

Private import preview A04.1: [workflow](docs/development/import-preview.md) dan [evidence](docs/testing/a041-evidence.md). Preview belum melakukan domain commit/provider transfer.

Import metadata A04.2: [workflow](docs/development/import-metadata.md) dan [evidence](docs/testing/a042-evidence.md). Metadata PREPARED adalah draft; explicit publication tersedia melalui A04.3.

A04 completed: [import commit workflow](docs/development/import-commit.md), [phase evidence](docs/testing/a04-evidence.md).

A05 [private assets/evidence](docs/development/private-assets-evidence.md) dan A06 [durable jobs/coordinator](docs/development/durable-jobs.md) `done`; [A06 evidence](docs/testing/a06-evidence.md). Scope permintaan selesai; A07 belum dimulai.
