# ADR 0004 — Private STT provenance and transcript lifecycle

Date: 9 October 2026. Status: accepted for standalone Package B implementation;
real platform transport/promotion reconciliation remains Phase 10 work.

Frozen contracts 1.0.0 expose TranscriptSegment with integer, nonnegative session
ranges and Evidence, but no raw alternatives, words, nullable session alignment,
chunk clock/provenance, correction counter, or downstream dependency index.
ProviderAdapter.transcribe(context, lease, audio) cannot bind B02 metadata/rights
or return this provenance. JobResult has no dedicated typed raw-record slot;
its existing artifacts list can reference a private JSON_REPORT (see continuation).

Use private immutable records in analysis.transcript_records, an explicit
AuthorizedChunk binding and STTExecutor in providers/stt. Preserve deterministic
protobuf response bytes, config and B02 preparation metadata privately; never put
them into TranscriptSegment.reason, Evidence.quote, Usage, or browser ledger payloads.
Workers import record models only. Lazy analysis registration preserves the existing
public entrypoint while avoiding an eager SQLite writer import in the provider.

SDK DTOs remain in the adapter. GoogleClient uses explicit credentials and an
explicit bounded grpc.aio channel, not implicit ADC lookup, automatic endpoint
selection or SDK automatic retries. Config requires project/region/endpoint/model/
locale/recognizer. Platform approval binds its hash to verified compatibility,
API/identity/billing and disabled data logging. This is an injected attestation,
not proof the real cloud project is ready. Model/region selection for tests is MOCK.

STTExecutor requires a bounded authoritative checkpoint and budget reservation
callback before every RPC attempt. Coordinator still owns durable job state,
heartbeat, cancellation/revocation, pricing, retries across attempts and final
accepted-result authorization. Async task cancellation requests transport cancel;
it does not promise server work/billing was reversed. Synchronous callbacks and
injected coroutine clients must be bounded/cooperative.

Raw local/source/session word offsets are separate. Unknown session alignment is
stored internally; public projection is unavailable rather than inventing a session
timestamp. Missing word offsets use an explicitly marked enclosing chunk range.
Nanoseconds express protobuf representation, not measured alignment accuracy.
Fractional frame conversion encloses by floor/ceil, followed by outward wire ms.
Confidence zero is the documented protobuf unset sentinel; quality remains
AMBIGUOUS and availability/speaker identity remain unknown.

Canonical provider words merge only exact text and exact source timings inside
actual overlap, with matching scope/source/config/channel/coverage. Each word keeps
all raw hypothesis/word references. Near matches and unknown timings stay separate
and ambiguous. Public segment projection retains original hypothesis text and
punctuation; it is not a silently rewritten deduplicated transcript. The canonical
provider-word view and the current human revision view have distinct entrypoints.
Jitter tolerance or automatic semantic boundary merging needs audited evidence.

analysis.0002 depends on unchanged analysis.0001 and adds private raw/revision/
dependency/change tables with platform parent FKs. Separate register_transcripts
keeps the B01 registration/migration digest intact. SQLite factories accept caller
connection/guard; services use caller UOW exclusively. Authority validates raw
candidate/active job/config/artifact/response binding inside that UOW. This callback
must not be replaced by a permissive function in real composition. No STT job
handler, accepted coordinator or HTTP route is registered at this stage.

Correction counter is internal and distinct from frozen input revision. Platform
owns future input-revision/run transitions. Corrections append a segment, actor,
original/previous reference, evidence, safe audit/event and invalidation; current
view selects latest counter. Old raw/segments remain resolvable. Dependencies store
their complete transcript lineage and derive stale state from newer corrections
or reanalysis invalidation. Future B04/B05 services must register their lineage;
no unimplemented reducers/projections are claimed to update automatically.

Evidence ranges are session-scoped in this lifecycle; audio links separately return
the original chunk/source asset/hash/channel/source range/session range/uncertainty.
Platform owns actual authorized range download, grant revocation and retention.
Reanalysis records invalidation of the old run; caller creates a new run/revision,
never overwrites old output. Purge removes B private records only; platform retains
ownership of evidence/ledger/audit retention and artifact TTL.

Readiness stays false. Real GCP compatibility/smoke, audited pronunciation/alignment
benchmark and transport/promotion reconciliation remain open. Frozen DTOs, ports
and generated schemas are unchanged. No real A/B composition or gate advancement.

## Standalone private artifact binding — 9 October 2026 continuation

Accepted for independent B03.D3, without waiting for real Package A composition.
Use frozen AssetAccess download/submit and ArtifactSubmission JSON_REPORT, with
audio capability, source_asset_id bound to the authorized derivative chunk and
`stt-private-provenance-1` transform. Deterministic attempt/chunk ID, canonical bytes,
SHA256 and <=8MiB are required. Full raw records remain private artifact content;
no words/config/provider payload in text, reason, evidence quote or Usage.

`providers/stt/execution.py` owns single-attempt acquisition/RPC/submission through
injected ports, bounded64KiB ranges, whole-attempt watchdog, checksums, checkpoints
and per-RPC reservation. It creates no disk files; caller owns executor closure and
heartbeat. Sync adapters must be bounded/cooperative. Generator closure and complete
consumption are required. Platform owns partial uploads/staged TTL/promotion; frozen
AssetAccess has no cleanup/abort method. A crash cannot guarantee exactly-once billing.

`bindings/stt.py` is an API-side standalone adapter around TranscriptLifecycle;
it does not change pure analysis import rules or worker import permissions.
AcceptanceAccess loads immutable scoped staged content and resolves authoritative
active attempt/lease/input/config/rights in the same caller UOW, including duplicates.
The validator reconstructs the entire candidate from original protobuf and trusted
B02 metadata/audio; transformed hypotheses/words/times/config cannot be accepted.
This is response consistency validation, not a Google-origin cryptographic signature.
An authenticated trusted worker and immutable platform staging are required in real
composition. Empty/permissive authority callbacks are forbidden there.

Exact replay preserves first API recorded_at, raw and original segment IDs; cancelled,
expired, changed-input or fresh-attempt old submissions cannot add accepted state.
Fresh attempts get distinct raw/artifact IDs; the existing chunk/revision uniqueness
rejects a second accepted raw. Caller owns commit, job receipt and publication; no
STT job handler or HTTP endpoint is registered in this standalone unit.

No contract version change is required for opaque JSON_REPORT references in
JobResult.artifacts. Phase10 reconciles authenticated port adapters, private artifact
ACL/inventory/download/TTL/promotion, transform manifest negotiation, candidate outputs/
usage/output hash, durable job state/receipt and atomic accepted handler wiring.
ProviderAdapter's typed return and unknown-clock public transcript/correction revision
gaps remain; a typed breaking extension needs explicit version reconciliation.
Phase10 remains a separate integration acceptance, not a circular B03.D3 dependency.

Standalone D3 deterministic acceptance is complete. Real cloud profile/smoke and
audited waveform/critical-slot/alignment evaluation remain B03 obligations; neither
MOCK private boundary nor actual FFmpeg plumbing satisfies them. Readiness false,
frozen1.0.0 and parent phases/gates unchanged. Details: [B03 evidence](../testing/b03-evidence.md).
