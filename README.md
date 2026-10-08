# ATC FlowLens

Workspace untuk membangun replay offline berbukti bagi review komunikasi dan kondisi runway oleh evaluator Tower/Ground.

**Status saat ini (8 Oktober 2026):** Phase 0–1 selesai: Python foundation, dependency lock, shared contracts 1.0.0, fixtures, generated schemas/OpenAPI dan standalone MOCK harness/tests tersedia. Paket bisnis A/B, provider adapters nyata, frontend, Dockerfiles/Compose dan deployment belum diimplementasikan. G-BE belum passed; baseline bukan validasi domain/operasional.

Stack target: React, TypeScript, Vite, shadcn/ui; Python, FastAPI, Pydantic; Google Speech-to-Text dan Gemini 3.8 Flash; SQLite; Docker Compose lokal/single VM.

Mulai dari:

- [Foundation workflow](docs/development/backend-foundation.md), [A/B packets](docs/development/backend-packets.md), dan [baseline evidence](docs/testing/phase01-evidence.md).

- [PRD](.agent/PRD.md): requirement produk dan acceptance.
- [Implementation phases](.agent/implementationPhases.md): backend lengkap → frontend lengkap → containerization → deployment.
- [Rules](.agent/rules.md) dan [handoff](.agent/sessionHandoff.md): aturan kerja dan konteks terkini.
- [Peta dokumentasi](docs/README.md).
- [Struktur repository](docs/architecture/repository-structure.md): tree lengkap, ownership, dan boundary.
- [ADR struktur modular](docs/adr/0001-modular-repository-layout.md): keputusan penempatan modul dan artefak.

Controller tetap memegang keputusan dan kewenangan clearance. V1 tidak menghubungkan production feed/audio atau menerbitkan instruksi operasional. Baseline sintetik diberi label yang sesuai; data nyata dan transfer cloud memerlukan hak penggunaan yang mencukupi.

Storage privat berada di `data/`; output sementara berada di `artifacts/`. Git hanya menyimpan `.gitkeep` pada kedua area tersebut. Test fixtures yang masuk Git harus sintetik/non-sensitif dan memiliki hak penggunaan yang sesuai.
