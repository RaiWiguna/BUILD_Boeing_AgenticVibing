# ADR 0002 — Shared contracts and independent backend harnesses

Status: accepted for Phase 0–1 execution. Tanggal: 8 Oktober 2026.

Context: aplikasi direset; A/B harus bekerja independen setelah baseline, tanpa source dependency lintas paket dan tanpa integration slice sebelum Phase 10.

Decision: root pyproject/uv.lock, Python 3.12, canonical strict Pydantic contract version 1.0.0, SDK-independent Protocol ports dan version-checked ModuleRegistration. Domain/service code tidak mengimpor SDK/host storage internals. Harness MOCK memakai constrained disposable SQLite reference schemas; production settings menolak baseline/mock composition. Migration registration dependency ordering deterministic; cross-package constraints tidak dimatikan untuk tests. Public/internal schemas dihasilkan dari Pydantic; final OpenAPI/TS client menunggu actual composition.

Consequence: fixtures, reference schemas dan contract behavior dapat digunakan A/B sebelum real implementations. Contract/fake pass hanya foundation acceptance; provider smoke, geometry/domain correctness dan integration tetap wajib pada owner phases/10. Breaking contract perubahan memerlukan versioned reconciliation/adapter. SQLite harness bukan production job/persistence engine.

Validation: shared suite both tracks, strict/negative examples, scope/as-of/evidence checks, atomic rollback/receipt/publication, fresh/upgrade reference schema, module/migration registration, schema drift, lint/type/build/dependency scans. Real A/B migrations and provider SDK compatibility are verified later.
