# Shared contracts 1.0.0

Canonical source: Pydantic models dalam `backend/flowlens/contracts/models.py`; ports dalam `ports.py`. Public JSON Schema ada di `contracts/json-schema/public`, internal schema di `contracts/json-schema/internal`. Valid/invalid examples berada di `contracts/examples`. Base64/key/private path/provider SDK types tidak menjadi wire fields.

## Generation and clients

`python -m flowlens.contracts.generate` menghasilkan deterministic JSON Schema dan `contracts/openapi/baseline.json`; `--check` menolak drift. OpenAPI baseline adalah harness schema exchange, dengan operasi MOCK validate dan readiness false. Ini belum OpenAPI final business endpoints `/api/v1`.

Paket A/B memakai Pydantic schemas yang sama. A mendaftarkan real public DTOs di host routes dan B melalui module registration. Pada Phase 10, composition nyata menghasilkan OpenAPI final; generator TypeScript dipilih/dipin sebelum client freeze dan output ditempatkan di `frontend/src/api/generated`. Generated client bukan hand-written duplicate DTOs. Tidak memasang npm/frontend runtime pada Phase 1; strategi generation/client dan drift sudah ditetapkan, client final menunggu endpoint nyata.

Wire names baseline memakai snake_case sesuai field Pydantic. Contoh TypeScript camelCase pada PRD adalah conceptual views; final generated client mengikuti OpenAPI, tanpa DTO duplikat. Compatibility casing historis dipetakan oleh A bila routes lama dipertahankan.

## DTO registry

SourceManifest/Permissions/Coverage/ClockMapping/Asset, SourceEvent/Track, Evidence, GeometryResult; TranscriptSegment/CriticalSlot/Intent/Association; MemoryEvent/OpenLoop/Finding/Option/Review/Brief/QueryAnswer; AnalysisRun/Usage; RequestContext/JobLease/JobResult/CommitReceipt/ArtifactSubmission/ToolRequest; Snapshot/StreamEvent/PlaybackState/JobProgress/SourceQualityChanged/ResyncRequired.

Strict Python mode memerlukan native UUID/datetime; JSON mode menerima UUID string dan UTC datetime. Null tetap unknown, bukan zero/empty string. DTOs memeriksa local structural/reference consistency; evidence services/domain validators masih wajib memeriksa source span/hash/actual support dan permission.

JobResult memuat outputs typed (termasuk OpenLoop dan QueryAnswer), evidence, derivative/report artifact submissions dan usage. Semua nested outputs/artifacts berbagi session/run/revision; FAILED tidak membawa accepted outputs/artifacts.

## Error policy

Response `code`, safe message, field_issues (locations only), request_id UUID, recovery_hint. Jangan echo input, SQL, provider exceptions, prompt atau credentials. Codes mengikuti PRD §22.3 ditambah baseline INVALID_INPUT, LEASE_EXPIRED, JOB_CANCELLED.

| Kelompok | HTTP target | Recovery |
| --- | --- | --- |
| AUTH_REQUIRED | 401 | Authenticate |
| ACCESS_DENIED / rights | 403 | Obtain correct grant/permission |
| invalid input/import/AI/range | 422 | Correct input or inspect evidence |
| version/idempotency/revision/lease/cancel | 409 | Reload revision/job/receipt |
| provider unavailable | 503 | Retry eligible job; cached replay remains |
| provider quota / budget | 429 | Check configured limits |
| evidence unavailable | 404 | Inspect scope/retention |

Harness uses safe handlers; authentication/cookie/CSRF/internal transport implementation remains Phase 2/6. Successful schema validation is not authority, semantic acceptance or provider success.

Canonical Track metric frame clarified by A08.1: local XY, heading0+X/90+Y counterclockwise, matching frozen aligned-X fixtures and audited historical atan2 convention. Geographic/compass sources require an explicit tested adapter; shared1.0.0 payload/schema unchanged. [Geometry workflow](../development/geometry.md).
