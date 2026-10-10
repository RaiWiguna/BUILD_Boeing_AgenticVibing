# Paket B — compatibility matrix menuju kontrak1.0.0

9 Oktober 2026. Audit source, bukan implementasi Phase10. Frozen DTOs/ports dan
Paket A tidak berubah. Semua registrations B tetap readiness=false, tanpa routes,
job handlers atau accepted snapshot reader. `tests/analysis/test_local_tooling.py`
menambah executable negative compatibility checks memakai injected/fake ports.

Kategori: **representable** = bentuk field dapat diwakili sekarang, bukan adapter
production sudah ada; **authority adapter** = keputusan platform yang wajib
disediakan; **version decision** = semantic/codec/public-contract reconciliation;
**Phase10** = real transport/composition/atomic integration setelah gate mandiri.

| Private B input/output atau concern | Public1.0.0 / port | Kategori dan keputusan yang masih diperlukan |
| --- | --- | --- |
| RawTranscript protobuf, hypotheses/word offsets, B02 chunk preparation, provider config | TranscriptSegment + Evidence hanya proyeksi primary text/range; AssetAccess JSON_REPORT dapat membawa artifact privat | Sebagian representable; private codec/hash/profile/source clocks membutuhkan authority adapter. Raw record bukan public transcript payload |
| Unknown session clock | Public TranscriptSegment mewajibkan session ms | Existing `transcript_projection.project` mengembalikan kosong bila session_range unknown; jangan membuat timestamps. Version decision jika public view source-relative dibutuhkan |
| Known clock tetapi historical availability tidak diketahui | Timed.available_time_ms nullable; Evidence tidak mempunyai availability | Representable unknown pada segment; evidence eligibility/as-of wajib authoritative adapter, bukan event time atau recorded_at yang dianggap available time |
| Word/source-nanosecond uncertainty dan exact-overlap reference graph | Public millisecond enclosures + Evidence spans | Sebagian representable; lossless raw/word provenance membutuhkan private codec/version decision; jangan menyisipkan JSON provenance ke reason/text |
| QuoteSlot callsign/runway | CriticalSlot | Representable field-for-field via deliberate serializer; executable JSON roundtrip tersedia. Accepted public Intent projection belum dipasang |
| Candidate candidate_version/segment_id/role/condition and negation QuoteSlot | Intent memakai segment_ids/role_candidate, condition text/negation bool | Memerlukan explicit projection; full direct validation ditolak. Uncertainty/alternatives/support negation dan condition tidak lossless: version decision atau private evidence codec diperlukan |
| AcceptedEvent + Link status/match/dependency/invalidation | Intent/Association/MemoryEvent/OpenLoop | Sebagian enum/evidence representable; target/source ID reconciliation, private ACCEPTED status mapping dan revision/timing harus diputuskan adapter owner |
| Projection.report/applicability/coverage/stale/closing-evidence | MemoryEvent tidak membawa semua dimensi ini; OpenLoop membawa coverage/closure | Version decision untuk complete public semantics; jangan meratakan Said/Heard/Observed atau report menjadi physical movement |
| Controller/Pilot role, callsign aliases/entity identity | ContextReader/SourceReader dan AcceptanceAccess | Authority adapter dari source server yang eligible; model/diarization bukan authority. MockAuthority bukan production policy |
| Channel coverage, geometry/clock/freshness/rule applicability | GeometryReader, GeometryResult, private Signal/ComparisonEligibility | Authority adapter wajib; NOT_EVALUABLE/unknown occupancy dipertahankan. No inferred runway-clear dari missing data |
| Findings version/status/said/heard/observed/evidence and source severity | Public Finding mempunyai bentuk berbeda dari private advisory Finding | Sebagian representable; explicit accepted projection/version decision diperlukan untuk field yang hilang dan status/priority mapping |
| Document sections/options/facts/input_digest/model provenance | Public Brief/Option/QueryAnswer tidak membawa seluruh private document | Full Document bukan JobResult output valid (executable negative check). Explicit summaries/projections + private report artifact codec/version decision; bukan string tunnel |
| Private Review/Entry stream/version/dependency/invalidation/journal | Public Review dan Timed DTOs | Sebagian representable; subject/document IDs, optimistic version, stale/reanalysis dan historical visibility memerlukan explicit adapters/version decision |
| Provenance request/response/config/schema/prompt hashes, SDK/API/model, per-attempt usage | ProviderProfile/AnalysisRun/Usage/JobResult | Usage hanya counters typed, bukan private record carrier. Profile tidak mengikat seluruh provenance; codec/version decision diperlukan |
| JSON/CSV/HTML renderer output + checksum/size/expiry/capability | ArtifactSubmission / AssetAccess | Descriptor representable dan existing renderer menghasilkan descriptor. ACL/per-source report rights/recipient redaction/TTL/promotion/download authorization perlu authority adapter |
| Staged private artifacts abort/delete/revoke/expiry/promotion | AssetAccess tidak menyediakan abort/delete/promotion; ArtifactLifecycle terpisah | Platform authority/lifecycle; version reconciliation bila transport membutuhkan operasi tambahan. Tidak ada cleanup remote yang diklaim oleh B |
| Durable attempts/lease/heartbeat/deadline/cancellation/reservation | JobClient/JobLease + injected execution checkpoints | Bentuk dasar representable; actual durable authority/clock/budget/rights/revision checks setiap step dan duplicate submission milik platform |
| Accepted duplicate result, changed payload, stale/late/cancelled response | JobResult/CommitReceipt + caller UnitOfWork | Standalone reference negative checks tersedia; real output hash/attempt/idempotency/receipt scope dan atomic publication tetap Phase10 |
| Worker input chunk bindings, private STT submission/ingest | InputAccess/ChunkAccess/AcceptanceAccess; frozen AssetAccess/JobClient | Private binding schema bukan frozen wire API. Authoritative authenticated transport + codec reconciliation dan atomic handler tetap Phase10; worker tidak membuka DB |
| Snapshot/REST/WS/query/job handlers and coordinator | AnalysisModule/AnalysisRepository/public Snapshot | Phase10; actual B registrations tidak mengklaim implementasi penuh public interfaces. Contract/reference suite PASS bukan integrated composition |

## Evidence dan next actions

Existing tests sudah menguji as-of/unknown availability, cancellation saat duplicate,
scope/revision/quote/hash/roles/coverage, rejection geometry yang tidak eligible,
append-only/reanalysis/review/export ACL/redaction dan receipt reference semantics.
Tidak menduplikasi tests itu. Tests tambahan hanya memverifikasi gap yang belum
diuji eksplisit: QuoteSlot→CriticalSlot shape, private Candidate bukan public Intent,
actual private Document bukan frozen JobResult output. Mereka tidak memasang
serializer production, permissive authority, HTTP route atau placeholder handler.

Platform + analysis owners perlu menyetujui field-level public projections dan
private artifact codec registry; catat field yang hilang serta version decision
sebelum menulis transport. Berikutnya owner platform menyediakan authority ports
untuk evidence availability/identity/role/coverage/geometry/current rights dan
artifact lifecycle; Phase10 owner kemudian memasang coordinator/attempt/receipts
dengan caller UOW, auth/timeouts dan recovery acceptance. Frozen text/reason/Usage
tidak boleh menjadi saluran tersembunyi bagi private records atau evaluator truth.

External B03/B04/B05 semantic/domain acceptance tetap terpisah dari matrix ini.
Tidak ada claim bahwa target public projections, authoritative platform adapters
atau real integrated pipeline sudah berjalan. Integrated readiness **false**.
