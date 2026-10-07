# Peta Dokumentasi ATC FlowLens

Tanggal: 7 Oktober 2026. Tree saat ini adalah scaffold setelah reset repository. Dokumen lama tidak dipulihkan sebagai spesifikasi aktif, dan instruksi AGENTS.md sebelumnya tidak berlaku.

## Kontrak dan konteks kerja

| Dokumen | Peran |
| --- | --- |
| [PRD](../.agent/PRD.md) | Kontrak produk/stack/fitur/data/API/acceptance yang berdiri sendiri |
| [Rules](../.agent/rules.md) | Aturan engineering dan verifikasi pada tree terkini |
| [Implementation phases](../.agent/implementationPhases.md) | Sequencing, dependencies, status, dan gate; bukan bukti implementasi |
| [Handoff](../.agent/sessionHandoff.md) | Keadaan repository, hasil pekerjaan, blockers, dan next action |
| [Repository structure](architecture/repository-structure.md) | Tree folder lengkap, responsibility, boundary, dan kapan diisi |
| [ADR modular layout](adr/0001-modular-repository-layout.md) | Keputusan arsitektur struktur repository |

## Area dokumentasi

| Folder | Isi yang dituju |
| --- | --- |
| `architecture/` | Boundary, dependency, state ownership, clocks, storage, dan diagram |
| `adr/` | Keputusan arsitektur tahan lama, dengan status dan validation plan |
| `product/` | Penjelasan fitur, scenario, usability, dan requirement detail yang melengkapi PRD |
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
