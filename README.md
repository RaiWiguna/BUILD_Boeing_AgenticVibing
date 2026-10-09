# ATC FlowLens

Workspace untuk membangun replay offline berbukti bagi review komunikasi dan kondisi runway oleh evaluator Tower/Ground.

**Status saat ini (9 Oktober 2026):** Phase 0–1 dan Paket A A01/Phase 2.1 selesai (host, SQLite/UOW dan audited historical conversion). A02/accounts+HTTP auth juga selesai; Phase 2.1/2.2 done, next A03.1 grants/RequestContext. Dependency lock/contracts 1.0.0 tetap. Domain grants/business pipeline, provider adapters nyata, frontend dan deployment belum tersedia. G-BE belum passed; baseline bukan validasi domain/operasional.

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
