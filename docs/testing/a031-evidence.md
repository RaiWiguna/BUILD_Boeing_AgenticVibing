# A03.1 — Grants, trusted RequestContext dan worker principal

Tanggal: 9 Oktober 2026, Asia/Jakarta. Input cdb2b9d; candidate working tree belum commit/push. A03.1 done; A03/Phase 2.3 in_progress, next A03.2. Contract 1.0.0/dependency lock unchanged; platform.0006 ditambahkan tanpa mengubah checksum migrations sebelumnya.

Deliverables: auth/permissions.py, same-UOW Sessions.authenticate, host live authorization guard, guarded platform/injected repositories/events/audit, schema grants/state/worker scopes/allowlists/context receipts/audit, tests/platform/test_permissions.py dan [workflow/boundaries](../development/authorization.md).

## Performed checks

Python 3.12.14/macOS arm64; real SQLite/Argon2, deterministic clock dan synthetic disposable accounts/assets. Tidak ada akun/data nyata diubah.

| Check | Result |
| --- | --- |
| Initial tests before implementation | RED: module permissions belum tersedia (collection failure) |
| Audio export/general export negative regression | RED: missing general export check reproduced; fixed, assertion preserved |
| `.venv/bin/pytest tests/platform -q` | 148 PASS: 110 prior + 38 authorization cases |
| `.venv/bin/pytest tests/contracts --track A -q` | 66 PASS |
| `.venv/bin/pytest tests/contracts --track B -q` | 66 PASS |
| `.venv/bin/ruff check backend tests scripts` | PASS |
| `.venv/bin/ruff format backend tests` | PASS, 36 files unchanged pada final input |
| `.venv/bin/mypy` | PASS, 25 source files |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues |
| `.venv/bin/uv build --out-dir artifacts/reports/a031-dist` | PASS, sdist/wheel |
| Ruff format check backend/tests/scripts | PASS, 37 files |
| Changed documentation local links/fences dan `git diff --check` | PASS |

Coverage: admin without domain grant, separate read/audio/export/truth/analysis/review, evaluator+DEBRIEF truth, cross-session/run/principal denial, exact source/revision/hash, forged/mutated context proof, source revision changes, live revoke/expiry/logout/reset checks on repository use, context TTL/backwards clock, restart receipts/revocation, explicit worker sources/assets, worker token digest/SecretStr, scope/principal revoke/expiry, local/cloud/export/audio_export rights changes, malformed/missing/mismatched manifest, private path absence, missing replay state, old nullable grants fail closed, .0005→.0006 upgrade/FK integrity, injected repository guard, domain/event rollback, atomic grant+audit failure.

## Limits dan cleanup

- Service/SQLite authorization foundation dan TestClient host lifecycle terbukti. Tidak ada domain HTTP/grant management/worker endpoints baru; generic Origin/CSRF/WS/principal dependencies dan public serializers berikutnya A03.2.
- Context TTL lima menit perlu refresh untuk request/job lanjutan. As-of/mode authority terbukti; event availability filtering/reducers, historical stale-run readers dan actual WS disconnection tetap A07. Current foundation rejects stale input/run scope.
- Source/asset policy method terbukti, actual range/export/download routes tetap A05/A09. Worker scope bukan lease atau izin accepted result; deadline/cancellation/budget/rights coordinator tetap A06. Audit ditulis atomik, append-only/version/idempotency enforcement tetap A03.3.
- Direct Database/raw SQL adalah trusted infrastructure. Host guard wajib untuk domain repository boundary; handler tidak menerima RequestContext dari client dan source handler harus memanggil source-rights checks. No provider calls atau B integration.
- Tidak ada live HTTP subprocess baru untuk unit ini (tidak ada route baru), UI/TLS VM/operational validation/full security/load audit. Dependency audit tidak diulang karena lock unchanged. Bandit bukan secret/dependency scan; Gitleaks unavailable.
- Disposable fixtures/database owners/TestClient ditutup; tidak ada persistent server/worker/container. Ignored build artifacts a031-dist tersedia. Tidak ada commit/push/merge/deploy. G-BE/G-FE/G-DELIVERY tetap not_started.
