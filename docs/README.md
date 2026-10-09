# Peta Dokumentasi ATC FlowLens

Tanggal: 9 Oktober 2026. Foundation Phase 0–1, host/persistence/legacy conversion A01 selesai; A02/accounts+HTTP auth tersedia; next A03.1 grants/context. Paket B B01/B02 standalone acceptance selesai; B03 adapter/transcript lifecycle tersedia dengan deterministic acceptance, tetapi real smoke/benchmark dan reconciliation masih terbuka. Readiness false; full business pipeline belum tersedia. Dokumen lama tidak dipulihkan sebagai spesifikasi aktif, dan instruksi AGENTS.md sebelumnya tidak berlaku.

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
- [Rencana eksekusi Paket A per sesi](development/package-a-execution.md): A01/A02 done, next A03.1; [evidence host](testing/a011-evidence.md) dan [persistence](testing/a012-evidence.md).
- [Rencana eksekusi Paket B](development/package-b-execution.md): B01/B02 done dalam scope standalone, B03 partial/in_progress, B04–B06 planned; [evidence B01](testing/b01-evidence.md), [B02.1](testing/b021-evidence.md), [B02.2](testing/b022-evidence.md), dan [B03](testing/b03-evidence.md).
- [Evaluation protocol](../evaluation/protocols/baseline.md) dan [checks/evidence](testing/phase01-evidence.md).

## Area dokumentasi

HTTP auth/cookies: [workflow](development/authentication.md) dan [evidence A02.2](testing/a022-evidence.md).

Account lifecycle: [workflow](development/account-lifecycle.md) dan [evidence A02.1](testing/a021-evidence.md).

Paket A A01 juga menyediakan [historical compatibility guide](development/legacy-compatibility.md) dan [evidence A01.3](testing/a013-evidence.md).

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
