# Frozen backend baseline 1.0.0

Tanggal: 8 Oktober 2026. Phase 1 menyediakan contracts/harness, bukan implementation A/B atau G-BE. Domain/SDK/storage dipisahkan melalui Protocol ports.

## Ownership

| Boundary | A | B |
| --- | --- | --- |
| API/composition/auth | Host, actor/grants, safe HTTP/WS/media transport | Registration routes/services milik analisis |
| Persistence | Transaction factory, migration runner; platform_* accounts/grants/sources/assets/replay/runs/jobs/attempts/evidence/audit/artifacts/receipts/events | analysis_* transcripts/revisions/intent/association/memory/loops/findings/options/briefs/queries/reviews/journal |
| Audio | Raw private store/range access/derivative promotion | Decode/resample/chunk/time mapping |
| Jobs | Lease/status/deadline/budget/rights/idempotent accepted-result coordinator | Worker executor/client/stage handlers/domain validation |
| Geometry/findings | Numeric observations/eligibility/uncertainty/rule versions/source alerts | Instruction applicability, association, semantic finding assembly |
| Evidence | Scoped registry/hash/range/permission validation dalam transaksi | Bukti dan semantic support untuk setiap factual result |
| Review | Authorization/transactions/audit infrastructure | Revision/correction/decisions/stale dependencies/reanalysis |
| Report/retention | Artifact promotion/download/expiry/purge coordination/tombstones | JSON/CSV/HTML renderer/redaction/escaping dan sensitive-data inventory/purge handler |
| Ops | Provider profile admin, health/ready, usage aggregation, disk/backup | Provider checks/sanitized diagnostics/readiness |

## Shared interfaces

`backend/flowlens/contracts/ports.py`: SourceReader, ContextReader, GeometryReader, AssetAccess, JobClient, EvidenceService, Repository, UnitOfWork, TransactionFactory, AnalysisModule, ArtifactLifecycle, ProviderAdapter, AnalysisRepository. Concrete implementations boleh menambahkan internals; public signatures berubah hanya dengan contract version/compatibility decision.

RequestContext selalu dibangun server dari actor/grants dan job/run/source revision. Worker/model/browser tidak menentukan capabilities/scope sendiri. Context JSON di examples hanya fixture, bukan trusted context ingestion endpoint aplikasi. Tools hanya enam read-only lookups; ToolRequest tidak mempunyai field role/session/run/as-of/SQL/HTTP/filesystem/command.

## Migration and repository contract

MigrationSpec memuat unique owner-scoped ID, owner A/B, depends_on dan SQL. Urutan topological deterministic; duplicate, missing dependency dan cycle ditolak. ModuleRegistration mendaftarkan routes/services/repositories/migrations/job_handlers/snapshot_reader/purge_handler/readiness/config_keys/inventory_namespaces.

Namespace migrations target `platform.0001`, `analysis.0001`; B initial migration dapat bergantung pada platform reference schemas. Standalone harness memasang reference tables minimal, tidak mematikan foreign keys. SQLiteHarness v1→v2 membuktikan fresh/upgrade reference behavior dan mempertahankan session/attempt IDs; ini bukan historical application archive migration. Real namespace migrations/runner milik A/B dibangun pada Phase 2/7.

Repositories append-only memakai session/run/revision dan UUID. Unique keys minimal meliputi `(session_id, attempt_id)` untuk result/receipt, `(namespace, id)` untuk reference repository, serta composite FK scoped references. Real cross-package FK dan unique constraints mengikuti registry ini; A/B mengirim schema manifest sebelum Phase 10. Expected version dan input hash diperiksa coordinator/domain service; schema bukan pengganti authorization/semantics.

## Atomic accepted result

1. B memvalidasi kandidat + semantic evidence; A memeriksa actor/lease/job/input revision/config hash/rights/deadline/budget.
2. Gunakan satu UnitOfWork milik API. Append domain state/evidence/audit/receipt/event sequence dalam transaksi sama.
3. Commit berhasil sebelum callback publication. Rollback membatalkan seluruh writes dan callback.
4. Same attempt + normalized payload → receipt yang sama; changed payload → IDEMPOTENCY_CONFLICT. Expired/cancelled/stale/revoked tidak menerima hasil baru.
5. Publication gagal setelah commit tidak membalik state durable; transport melakukan resync dari persisted sequence. Provider billing tidak dijamin exactly-once.

SQLiteTransactionFactory dan SQLiteHarness berada di `flowlens.testing`, berlabel MOCK dan hanya untuk disposable test/reference databases. Tidak boleh dipilih production; mereka bukan package A. Tidak ada worker/SDK/replay lock yang digunakan foundation.

## Clock, quality and wire

UUID stable; source IDs tetap namespace terpisah. UTC RFC3339 untuk recorded_at; session relative nonnegative integer ms untuk event/available/as-of/ranges. Clock offset signed; unknown alignment menghasilkan None. Event time berbeda dari available time; AS_KNOWN menolak unknown/future availability, DEBRIEF masih dibatasi event/as-of dan berlabel.

Strict Pydantic, extra forbidden, finite numbers, positive ordered ranges, nested evidence same session/run/revision, nullable confidence tanpa angka buatan. Critical slots null harus punya unknown reason. Geometry ineligible membawa NOT_EVALUABLE/reason/unknown occupancy. Raw transcript dan corrections tidak digabung; accepted events/reducer menyimpan version dan dependency hashes.

Breaking changes → major contract version dan adapter/checks, additive backwards-compatible changes → minor, safe fixes → patch. Paket pengusul menjalankan both-track contract tests; reconciliation lintas implementasi tetap Phase 10. Frozen version awal 1.0.0, belum release production.
