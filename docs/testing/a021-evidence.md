# A02.1 — Accounts, Argon2id dan bootstrap/reset/deactivation

Tanggal: 9 Oktober 2026, Asia/Jakarta. A02.1 **done**, A02/Phase 2.2 in_progress; A02.2 planned. Input commit c36cf04; candidate working tree, belum commit/push. Contract 1.0.0 tetap.

Deliverables: `auth/accounts.py`, `cli/bootstrap_admin.py`, migration platform.0004, host lifespan account service, `tests/platform/test_accounts.py`, manifest/lock dan [account workflow](../development/account-lifecycle.md). Tidak membuat public auth endpoints/cookies.

## Performed checks

Python 3.12.14/macOS arm64, temp SQLite/private test secret files; real Argon2 parameters.

| Command / cakupan | Result |
| --- | --- |
| Initial account suite before implementation/dependency | 12 missing-feature/dependency failures |
| Race admin credential mutation / missing host account service before fix | 2 RED failures reproduced; fixed without removing assertions |
| `.venv/bin/pytest tests/platform -q` | 88 PASS (71 prior + 17 account cases) |
| `.venv/bin/pytest tests/contracts --track A -q` | 66 PASS |
| `.venv/bin/pytest tests/contracts --track B -q` | 66 PASS |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS, shared schema/OpenAPI unchanged |
| `.venv/bin/ruff check backend tests scripts` / format check | PASS; format 32 files |
| `.venv/bin/mypy` | PASS, 22 source files |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues |
| `.venv/bin/uv add 'argon2-cffi>=25.1,<26'`, `uv lock --check` | PASS, locked install/manifest consistent |
| `.venv/bin/pip-audit --local` | No known vulnerabilities; unpublished project itself skipped |
| `.venv/bin/uv build --out-dir artifacts/reports/a021-dist` | PASS, sdist/wheel |
| CLI private file bootstrap/retry/failure subprocess tests | PASS; no password output; insecure file rejected before creating DB |
| Local documentation links/fences/whitespace and scoped secret patterns | PASS |

Dependency resolution: argon2-cffi 25.1.0, argon2-cffi-bindings 26.1.0, cffi 2.1.1, pycparser 3.1; hashes in uv.lock. [Official API](https://argon2-cffi.readthedocs.io/en/stable/api.html) checked before integration. Tests use 64 MiB/time=3/parallelism=4 real hashing, no cheap test-only substitute.

Root cause found during migration: SQLite ALTER TABLE with CHECK emits authorizer SQLITE_PRAGMA `quick_check` on the altered table. Minimal in-memory reproduction identified this read-only operation; allow it while retaining existing negative transaction/PRAGMA tests. Upgrade test preserves prior account IDs without granting admin.

Account tests cover once-only/concurrent bootstrap, safe public view, actual hash verification/random salts, bad login/password bounds, duplicate canonical login, active admin checks, forced change, previous password rejection, credential version revocation, deactivation/restart, last-admin guard, wrong/missing/corrupt credentials, hashing outside write transactions, audit/marker rollback, concurrent credential change, private CLI permission/no output and host lifecycle. All bootstrap DBs and passwords are synthetic/disposable.

## Limits / next

- Internal service actor IDs are trusted server input; no browser-facing admin/auth route exists yet. Credential snapshot revocation is proven; actual opaque sessions/cookies/idle+absolute expiry/logout/rate limits and forced-change transport remain A02.2.
- Domain grants, CSRF, worker principals, grant-driven stream termination remain A03/A07. Admin flag alone does not grant truth/domain access; no replay grants created by bootstrap.
- Password params tested locally, not VM benchmark. Clean wheel install/cross-platform and hosted CI not run; dependency audit cannot audit unpublished application source. Scoped patterns/Bandit not a full security audit; Gitleaks unavailable.
- No real user/bootstrap secret or developer DB modified. No provider calls, frontend/container/deploy, persistent runtime, commit/push. Ignored build artifacts remain a021-dist. All gates remain not_started.
- Next A02.2: login/logout, cookie sessions, forced-change flow, expiry/revocation and rate limiting.
