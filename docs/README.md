# Peta Dokumentasi ATC FlowLens

Tanggal: 8 Oktober 2026. Tree reset sudah dilengkapi foundation Phase 0–1; implementation A/B belum dimulai. Dokumen lama tidak dipulihkan sebagai spesifikasi aktif, dan instruksi AGENTS.md sebelumnya tidak berlaku.

## Kontrak dan konteks kerja

| Dokumen | Peran |
| --- | --- |
| [PRD](../.agent/PRD.md) | Kontrak produk/stack/fitur/data/API/acceptance yang berdiri sendiri |
| [Rules](../.agent/rules.md) | Aturan engineering dan verifikasi pada tree terkini |
| [Implementation phases](../.agent/implementationPhases.md) | Sequencing, dependencies, status, dan gate; bukan bukti implementasi |
| [Handoff](../.agent/sessionHandoff.md) | Keadaan repository, hasil pekerjaan, blockers, dan next action |
| [Repository structure](architecture/repository-structure.md) | Tree folder lengkap, responsibility, boundary, dan kapan diisi |
| [ADR modular layout](adr/0001-modular-repository-layout.md) | Keputusan arsitektur struktur repository |

## Baseline Phase 0–1

- [Audit requirements/source](product/requirement-audit.md) dan [scope/dependencies](product/baseline-scope.md).
- [Backend baseline](architecture/backend-baseline.md) dan [ADR 0002](adr/0002-frozen-backend-contracts.md).
- [Shared contracts](api/shared-contracts.md), [developer workflow](development/backend-foundation.md), dan [A/B packets](development/backend-packets.md).
- [Evaluation protocol](../evaluation/protocols/baseline.md) dan [checks/evidence](testing/phase01-evidence.md).

## Acuan desain frontend

[Delapan referensi halaman ATC FlowLens](design/2026-10-08-flowlens/README.md) menyediakan analisis UX, gambar horizontal per halaman, galeri, token usulan, dan prompt generasi. Statusnya DESIGN_REFERENCE_ONLY; tidak mengubah sequencing backend-first atau menyatakan frontend/gate telah selesai.

## Frontend MOCK track

Frontend penuh tersedia di `frontend/` dengan adapter MOCK in-browser (Phase 11–13 `in_progress (MOCK)`; G-FE tetap `blocked`). Lihat [rencana implementasi](development/frontend-implementation-plan.md), [panduan pengembang dan penggantian adapter ke HTTP](development/frontend-mock.md), [evidence MOCK](testing/frontend-mock-evidence.md), dan [skrip demo](demo/frontend-mock-demo.md).

## Area dokumentasi

| Folder | Isi yang dituju |
| --- | --- |
| `architecture/` | Boundary, dependency, state ownership, clocks, storage, dan diagram |
| `adr/` | Keputusan arsitektur tahan lama, dengan status dan validation plan |
| `product/` | Penjelasan fitur, scenario, usability, dan requirement detail yang melengkapi PRD |
| `design/` | Referensi visual, analisis UX, token usulan, dan handoff desain; bukan implementasi frontend |
| `api/` | REST/WS/internal API, errors, authentication, dan client compatibility |
| `data/` | Import profiles, provenance, source rights, clocks, coverage, retention |
| `evaluation/` | Protocol, metrics, split/cohorts, reviewer rubric, dan limitations |
| `development/` | Setup, toolchain, developer workflows dan module conventions |
| `operations/` | Local/VM runbooks, jobs, monitoring, backup/restore dan recovery |
| `security/` | Auth/data/tool boundaries, access policy dan scoped assurance work |
| `testing/` | Test strategy, oracle/fixture conventions, acceptance dan evidence |
| `releases/` | Release manifest, migration/promotion/rollback notes dan performed checks |

Folder yang belum memiliki isi hanya berisi `.gitkeep`. Jangan menganggap keberadaan folder sebagai deliverable yang selesai. Generated OpenAPI/JSON Schema diletakkan pada `contracts/`, sedangkan penjelasan kontraknya di `docs/api/`.

## Ketepatan status

Bedakan planned, source tersedia, build berhasil, berjalan, tests lulus, provider benchmark, domain review, dan operational validation. Angka target pada PRD bukan hasil pengukuran. Dokumen historis dapat dibaca dari Git bila diperlukan, tetapi tidak otomatis menjadi aturan aktif atau file yang harus direstore.
