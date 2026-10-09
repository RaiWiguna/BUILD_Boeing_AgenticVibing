# A04.2 — Manifest, granular rights, retention, coverage dan normalization

Tanggal: 9 Oktober 2026, Asia/Jakarta. Input cdb2b9d + uncommitted A03.1–A04.1. Rules, PRD9/10/rights, progress/handoff, execution dan source dibaca; prerequisite A04.1 verified35 tests PASS sebelum implementasi. Scope hanya A04.2; no A04.3/real B integration. Shared contracts/ports1.0.0 dan dependencies/lock unchanged; additive platform.0009.

## Deliverables dan acceptance

- sources/metadata.py: strict provenance/source owner/dataset, tri-state granular rights/basis, explicit retention, nullable coverage, effective evidenced entity mapping dan versioned local planar layout.
- clocks/normalization.py: versioned UNKNOWN/offset/linear mapping, declared uncertainty/reviewer/basis, Decimal drift transform/signed64 guard dan IANA UTC wall-time adapter dengan DST ambiguity/nonexistence refusal.
- imports/normalization.py: private strict canonical sidecar scan, raw timestamp/available/recorded/IDs preserved by helper, scoped UUIDs, validated evidence/scope/duplicate/layout, metadata-only hashes/counts/unknowns. inspection.py mengekstrak records iterator, rows count wrapper tetap parser yang sama. staging.py private bounded fd read, preview fields untuk metadata revision/current readiness.
- imports/metadata.py + platform.0009: immutable <=64 revisions, current owner/admin/file/expiry checks, expected revision/key receipt atomicity, reserved source/session IDs, full envelope/content/declaration hashes, conservative frozen SourceManifest projection dan live latest-rights preflight. Raw file bytes tidak ditransformasi; metadata preparation tidak membuat domain rows.
- imports/routes.py: bounded JSON POST/GET metadata/revision, schema/OpenAPI, safe field/code errors, current GET preview; inherited Origin/CSRF/no-store. First upload receipt remains stable inspection snapshot.
- [Workflow](../development/import-metadata.md), ADR elaboration/progress/handoff diperbarui. Granular source rights lebih lengkap daripada frozen bools; full envelope harus dibawa ke A04.3, bukan dihapus setelah projection.

29 cases di tests/platform/test_import_metadata.py: audio-only permitted local/no cloud, hash round-trip/forged declaration detection, unknown local/retention fail closed, granular transfer/export/reviewer isolation, latest denial after historical receipt, immutable revision/expected version/changed-key conflicts, concurrent same-key one receipt, commit fault rollback, owner/revocation/tamper refusal, SQL update/delete/replacement rejection dan TTL cascade, upgrade0008→0009 preserving preview/files, HTTP201/403/409/422/current preview/revision/no-store/safe field errors/OpenAPI/body cap, WAV metadata/file binding, nullable track/vehicles/speaker/alignment, paired track normalization/evidenced scope, raw-file preservation, layouts metre/feet/self-intersection, invalid/nonfinite clock fields, linear compatibility projection dan no manufactured available/processing time.

Independent clock/unit expectations: source1,000,000ms + offset2,000 +100ppm =1,002,100ms; fixture source track100/available200 +offset1,000 =1,100/1,200. Asia/Jakarta07:00:01.250 →UTC00:00:01.250 relative1,250ms. New York fall-back01:30 with fold0/1 →5,400,000/9,000,000ms relativeUTC04:00; spring02:30 rejected NONEXISTENT_TIME. Layout100ft=30.48m,10ft=3.048m,1ft uncertainty=0.3048m. Expected values bukan salinan implementation helper.

## Checks

Python3.12.14/macOS arm64, disposable SQLite/private dirs, synthetic account/data dan real native audio decode inherited A04.1. HTTP menggunakan TestClient; tidak menjalankan live network/provider smoke.

| Check | Result |
| --- | --- |
| Initial metadata/clock/layout tests | RED: modules/services absent; tests retained |
| Sidecar normalization regression | RED: summaries absent; explicit normalization added |
| Reviewer projection regression | RED: frozen local flag granted reviewer-denied source; conservative projection added |
| Self-intersection regression | RED: nonzero-area crossing polygon accepted; intersection guard added |
| Linear clock regression | RED: quality SUPPORTED with unrepresentable frozen clock; unknown projection/quality retained |
| Current preview regression | RED: metadata revision/declared rights absent from GET; current projection added |
| HTTP units remediation regression | RED: unknown units generic error; safe bounded stable field/code issues added |
| `.venv/bin/python -m pytest tests/platform -q` | PASS,341 (312 prior +29 new) |
| `.venv/bin/python -m pytest tests/contracts --track A -q` | PASS,66 |
| `.venv/bin/python -m pytest tests/contracts --track B -q` | PASS,66 |
| `.venv/bin/ruff check backend tests scripts` | PASS |
| `.venv/bin/ruff format --check backend tests scripts` | PASS,51 files |
| `.venv/bin/mypy` | PASS,35 source files |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS,0 medium/high;2 existing low subprocess B404/B603, no skips/suppressions |
| `.venv/bin/pip-audit --local` | PASS,no known Python dependency vulnerabilities; unpublished local app skipped |
| `.venv/bin/uv build --out-dir artifacts/reports/a042-dist` | PASS,sdist/wheel |
| Committed schema AST/HEAD checksum comparison | PASS,0001–0005 unchanged; current platform0001–0009 |
| Changed Markdown links/fences/whitespace + `git diff --check` | PASS,21 changed Markdown files |

## Scope, limitations dan cleanup

Profile validates canonical staged sidecars already using metres/relative ms/UTC recorded_at; standalone wall-time adapter is tested, arbitrary source wall-time/geographic/corpus adapters are not implemented. Layout/source labels/provenance/consent remain explicit declarations, not verified license/legal/domain evidence. Speaker coverage true needs a future evidence adapter and is rejected; unknown remains null. METADATA_COMPLETE is not geometric eligibility, actual alignment fidelity, domain review or operational validation. No certainty/vehicle absence inferred from missing data.

Frozen projection cannot represent category-specific cloud rights, reviewer isolation or linear drift fully; conservative flags/unknown preserve full envelope as authoritative draft metadata. Historical receipt is evidence of an old declaration, not current rights authority; service preflight loads latest. Actual source grant/media/export/provider/lease-result enforcement remains A04.3/A05/A06; preflight tests call no provider. Retention is declared fixed duration, not purge execution; source policy propagation to derivatives/export/backup remains later owners. Draft metadata expires with scratch TTL; no committed-source forensic audit claim.

No committed replay session/source/assets/jobs/runs, atomic FS promotion/dedup/source port reader, real B/Google/Gemini/frontend/deployment. Full resource maxima/throughput/Linux native memory limit/metadata concurrency capacity remain unverified; Darwin decoder limitations A04.1 apply. Gates G-BE/G-FE/G-DELIVERY remain not_started and readiness503/HOST_ONLY.

Disposable owners/UOWs/TestClient/thread pools/native subprocess closed; ignored a042-dist exists. No persistent runtime, real accounts/data migration, provider call, commit/push/merge/deploy. A04.2/Phase3.2–3.3 done; A04/Phase3 in_progress. Next only A04.3 commit/promotion/dedup/conflict and source reader through frozen ports.
