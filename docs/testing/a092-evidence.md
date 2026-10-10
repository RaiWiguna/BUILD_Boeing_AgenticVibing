# A09.2 — local operability dan provider metadata

Tanggal9 Oktober2026. Input `22e72b331249858576c0fcebca27eb12ee2184b1`, clean sebelum unit, branch feat/backend-aben. Real A SQLite/private storage/auth/jobs/HTTP dan fake frozen ProviderAdapter/AnalysisModule; tidak ada actual cloud SDK/network/inference, production source, deployment atau persistent service.

## Acceptance tersedia di source

- `ops/health.py` actual private roots/disk/write/fsync probes, DB checksum/quick_check/rollback-write, coordinator ledger identity/invariants, journal integrity. Configured local host ready200; missing/fault/corrupt/disk-low unready503. Cloud unavailable tidak memblokir actual cached snapshot. Local readiness dan integration/provider/domain status terpisah.
- Safe release manifest actual code/migration/installed dependency versions plus explicitly operator-declared/unrecorded source/lock hashes; tidak ada secret/path dump. Default development still HOST_ONLY/incomplete; all release gates not_started.
- Typed JSON logs: generated HTTP correlation/status/header latency, durable attempt IDs/stage/hashes/ledger charge; no body/query/header/token/exception/transcript. Dedicated launcher INFO sink actual subprocess-tested, no duplicate configure handlers/SDK verbosity. Rollback/duplicate result not logged as additional commit; telemetry failure cannot invalidate accepted commit.
- Immutable versioned admin provider profiles/options, idempotency/expected revision/audit transaction, safe metadata constraints and credential-signature rejection; registered adapter binding equality; fake checks MOCK/provider_verifiedfalse. Live revocation/config race after callback denied; callback executes outside DB lock. Raw exception/mutated output rejected without persistence/leak. Profiles survive schema16->17 upgrade and owner reopen; old historical configuration hashes stable.
- Scoped/admin usage budget ledger totals, unknown provider cost retained null despite conservative charging, duplicate result one attempt, stage/job counters, queue/lease age, revoked capability/invariant denial. Per-channel breakdown is unavailable in frozen Usage and explicitly labelled, never invented. No provider invoice/domain/evaluator metric certification.

## Performed checks

Final685 platform PASS (143.21s),28 scoped PASS (9.23s),66 contracts each A/B PASS, Ruff110/mypy72/contract drift/Bandit -ll/lock/build PASS. Scoped tests cover profile version/check/idempotency/history, unsafe metadata, fake/error/mutated diagnostics, options mismatch, config race/admin revoke, audit rollback, upgrade/reopen; DB/private roots/disk/write/journal probes; true local-ready/fake unavailable/release-safe/native host cleanup; actual cached snapshot under outage; unknown reservations/usage, invariants/scope, transactional log emission, actual JSON sink; admin/CSRF/strict-body/duplicate/size/no-store API and body/query sanitization.

All16 historical migration definitions AST-identical to input HEAD; only0017 appended for immutable profiles/checks/ops metadata and attempt timing. Frozen contracts1.0.0 and lock unchanged. Diff/source reviewed before local conventional commit. Bandit -ll retains only the existing low decoder findings and validated-schema B608 exclusions from A09.1, not a certification.

Available scan24 staged files/0 matches is scoped staged-full-file known signatures, not entropy/history: PEM/Google/AWS/GitHub/Slack. Dedicated gitleaks/trufflehog/git-secrets absent. Report ignored at `artifacts/reports/a092-secret-scan.json`; private/test DB/log/runtime bytes not staged.

A09.3 consistent backup/restore/maintenance remains next; A09 parent not complete. No push/merge/amend/destructive Git/B/Phase10/frontend/deployment. Workflow/limits: [operability](../development/operability.md).
