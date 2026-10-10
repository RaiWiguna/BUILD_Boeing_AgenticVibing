# A07.1 — Deterministic observed replay evidence

Tanggal 9 Oktober 2026. Input HEAD `21457f3d8a9d88b7ce90d400bce259bf09ee073b`, branch `feat/backend-aben`, working tree bersih. Goal persisten A07.1–A09.3; tiap unit acceptance/checks/evidence/local commit, tanpa A10/push/merge/amend. [Workflow](../development/replay.md).

## Entry verification A01–A06

Source host/config, real SQLite UOW/migrations/legacy converter, accounts/sessions, grants/transport/serializers, mutations, import/source/clock, assets/evidence dan jobs inspected dengan evidence masing-masing. Rerun sebelum edit: `python -m pytest tests/platform -q` 425 PASS (80.68s); shared contracts --track A/B 66 PASS each; Ruff check/format63, mypy44, schema drift, Bandit -ll0 medium/high PASS. Tidak hanya menggunakan status handoff.

A06.1: coordinator create/lease/heartbeat/recover/cancel/inspect dan tests nyata menguji restart/process-exit, expiry/deadline, dua claimant, bounded retry/concurrency/budget release, minimal worker scope serta revoked auth/rights. A06.2: result memeriksa current rights/revision/config/run/deadline/budget, memvalidasi di luar lock dan recheck dalam UOW; accept/evidence/audit/receipt/event atomik, duplicate receipt immutable, late/stale result denied, rollback fault boundaries serta postcommit publication failure durable. Test jobs60 termasuk subprocess exit91/92 dan race kedua result kembali PASS dalam baseline425. A06 memenuhi standalone acceptance; bukan real B/provider atau exactly-once billing.

## Deliverables dan acceptance

- `replay/snapshots.py`: observed ordering/reducer, exact-ID dedup/conflict, AS_KNOWN/DEBRIEF filtering, input/version/run/mode/sequence-bound checkpoints dan callback concurrency recheck.
- Host composition dari satu frozen snapshot reader; real A source, fake B test hanya via port.
- `platform.0013`: derived snapshots/checksum, original001–012 unchanged. Existing A06 upgrade test mengikuti jumlah migration aktual sambil mempertahankan semua history/checksum assertions.
- 19 replay cases: hand-written independent event/available-time oracle di99/100/199/200/300/500/40000ms, unknown availability, permutation/same-time ordering, duplicate/conflict, revision/cross-session/copied-invalid denial, track header/wire stability dan preserved source geometry, quality/empty, full rebuild/checkpoint equivalence, backward seek, actual SQLite owner reopen, source immutable, revoke/rights, cache corruption, concurrent publication conflict, nested fake finding/future denial, unbacked source injection denial, reducer version isolation, host lifespan composition/cleanup.

Initial19 cases ditambahkan bertahap sebelum implementasi perilakunya: missing replay RED; Track-vs-header wire mismatch RED, host composition RED, unbacked fake source event RED. Corrected test setup DB directory isolation/reviewer field; assertions tetap menegakkan target. No checks/acceptance weakened.

## Checks final

Scoped replay19 + prior upgrade1:20 PASS. Full platform444 PASS (82.10s); contracts66 each A/B PASS; Ruff check/format65 PASS; mypy45 PASS; shared schema drift PASS; Bandit -ll0 medium/high (2 existing LOW native subprocess findings), tanpa suppressions. Build `.venv/bin/uv build --out-dir artifacts/reports/a071-dist` sdist/wheel PASS; AST comparison12 prior migration SQL unchanged/current13. `uv` pada PATH tidak tersedia; executable repo `.venv/bin/uv` digunakan. No persistent runtime.

Synthetic/disposable source WAV/events/SQLite/TestClient, fake B. Contract1.0.0/lock unchanged; reducer observed-replay-1; migrations13. No live provider/domain validation, capacity claim, real WS/controls atau archive compatibility reader; A07.2–A07.3 belum dilakukan. Runtime test owners/clients selesai; no persistent API/worker/server/deployment. Readiness503/gates not_started; parent phases B tetap tidak selesai.

Diff source/tests/docs reviewed; `git diff --cached --check` dan Markdown links/fences PASS. Dedicated gitleaks/trufflehog/git-secrets tidak tersedia. Scoped known-secret signature scan14 staged candidate files:0 matches; metadata ignored `artifacts/reports/a071-secret-scan.json`. Cakupan terbatas, bukan history/entropy/dedicated scan. Stage hanya14 related files; tidak menyertakan runtime/private data/secrets.

Local conventional commit: `1d48791ab19c567aa88a6439b53e585bb0f30e1b` — `feat(replay): add deterministic observed snapshots and checkpoints`; clean after commit, no push/merge/amend.
