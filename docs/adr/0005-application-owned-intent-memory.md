# ADR 0005 — Application-owned intent memory and bounded stateless inference

Status: accepted architecture; local standalone implementation verified separately.
Tanggal: 9 Oktober 2026.

## Context

Frozen contracts1.0.0 do not express action/condition/negation quote slots, complete
provider provenance, nullable usage totals, transcript dependency records or private
memory invalidations. ProviderAdapter.extract cannot carry trusted identity aliases,
tool orchestration, authority attestations or the caller's transaction. Provider
conversation history cannot serve as reproducible operational memory.

## Decision

Use private typed Candidate/Provenance/AcceptedEvent/Invalidation records without
changing generated schemas. Structured LOOKUP proposals and final EXTRACT requests
are separate, stateless Developer Interactions requests. No provider native tools,
background execution, previous_interaction_id, unrestricted browsing or execution
are enabled. Only six frozen ToolRequest names are forwarded through ContextReader.
Tool responses and transcripts remain untrusted data. No thought traces or opaque
continuation steps are persisted; this workflow has no native function continuation
requiring their resubmission.

GeminiConfig pins model/API/SDK/prompt/config versions and hard bounds. Explicit
credential and bound operator approvals precede Google client creation. A public
HTTPX transport wrapper enforces one actual HTTP send per application reservation
and bounds response streaming. This is necessary because pinned google-genai2.29.0
mutates HttpRetryOptions(attempts=0) to1 before Interactions interprets it as retries.
Application retries reserve independently and never switch provider/model.

MemoryService validates scope, exact quotes, lexical support, identity aliases and
server-attested role. Association retains competing alternatives. AcceptanceAccess
must verify lease/attempt/cancellation/deadline/revision/rights/config and authenticated
worker candidate/provenance binding inside the caller UOW, even for duplicates.
No default or real permissive authority implementation is provided.

analysis.0003 owns analysis_memory_ledger, with run/revision foreign keys and an
append-only repository. Caller supplies connection, transaction and commit. Memory,
evidence, audit and ledger notices share that transaction. Errors require rollback
of the caller UOW. Providers/workers never open this SQLite database.

TranscriptMemoryBinding consumes the existing TranscriptLifecycle and its dependency
index in the same UOW. Correction/reanalysis appends invalidations with explicit
caller-supplied event/availability clocks; replay as-of is not invented as historical
availability. Recompute remains explicit. Reducer/projections preserve independent
instruction/readback/report/movement/reviewer dimensions and versioned open loops.
Matching speech can close a communication obligation with known coverage; it cannot
establish physical movement compliance or runway occupancy.

## Alternatives and consequences

Expanding frozen DTOs was rejected without contract reconciliation. Putting private
payloads in text/reason/Usage fields was rejected. Provider-hosted conversation memory
and native execution tools would add state and authority that cannot be replayed from
the application ledger. Exact lexical support deliberately abstains on unconfigured
phonetic aliases, uncertain roles and competing targets; benchmark calibration remains
necessary. The association120000ms window is a versioned synthetic engineering bound,
not an ATC response deadline. Loop timers have no invented universal deadline.

Sync frozen ports cannot forcibly terminate uncooperative IO threads. Injected adapters
must implement bounded, read-only, thread-safe IO and scoped availability checks. The
orchestrator discards late results and checks cancellation before/after provider/tool
work. Evidence lacks availability metadata on the wire: authoritative EvidenceService
resolution must check it against server context; unknown/unavailable support fails
closed. Physical observations and reviewer decisions remain separate evidence domains.

## Validation and follow-up

[B04 evidence](../testing/b04-evidence.md) records semantic/security/reconstruction,
rollback/restart/purge, import isolation and actual SDK HTTP-MOCK tests. Mock authority
exists only in testing. Real model/API account smoke and audited held-out semantics
remain open; published support is distinct from account access. store=false does not
mean zero retention under all provider terms.

Real composition must reconcile private artifact provenance/ACL/TTL/promotion,
durable authority/receipts/job result hashes, source-role/alias/coverage attestations,
and public MemoryEvent/OpenLoop/Snapshot projection adapters. Registration installs
no HTTP route or job handler. Readiness remains false; no backend/frontend/delivery
gate is advanced by standalone acceptance.
